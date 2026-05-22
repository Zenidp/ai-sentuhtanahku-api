from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google import genai
from google.genai import types
from groq import Groq
from cerebras.cloud.sdk import Cerebras
import os
import requests
from typing import List, Dict

app = FastAPI(title="API AI Sentuh Tanahku (Genius + Memory Mode)")

# --- KONFIGURASI ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
SAMBANOVA_API_KEY = os.getenv("SAMBANOVA_API_KEY")
NVIDIA_NIM_API_KEY = os.getenv("NVIDIA_NIM_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
SCALEWAY_API_KEY = os.getenv("SCALEWAY_API_KEY")

class ChatRequest(BaseModel):
    pesan: str
    session_id: str = "default"
    riwayat: List[Dict[str, str]] = []

@app.get("/")
def read_root():
    return {"status": "Sistem RAG Sentuh Tanahku (Genius + Memory Mode) Aktif!"}

# --- FUNGSI PER PROVIDER (semua terima prompt + model) ---

def try_cerebras(prompt: str, model: str) -> str:
    client = Cerebras(api_key=CEREBRAS_API_KEY)
    response = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model=model,
    )
    return response.choices[0].message.content

def try_groq(prompt: str, model: str) -> str:
    client = Groq(api_key=GROQ_API_KEY)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=2048,
    )
    return response.choices[0].message.content

def try_mistral(prompt: str, model: str) -> str:
    response = requests.post(
        "https://api.mistral.ai/v1/chat/completions",
        headers={"Authorization": f"Bearer {MISTRAL_API_KEY}", "Content-Type": "application/json"},
        json={"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 2048},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

def try_sambanova(prompt: str, model: str) -> str:
    response = requests.post(
        "https://api.sambanova.ai/v1/chat/completions",
        headers={"Authorization": f"Bearer {SAMBANOVA_API_KEY}", "Content-Type": "application/json"},
        json={"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 2048},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

def try_gemini(prompt: str, model: str) -> str:
    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(model=model, contents=prompt)
    return response.text

def try_cloudflare(prompt: str, model: str) -> str:
    url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/{model}"
    headers = {"Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}"}
    response = requests.post(url, headers=headers, json={"prompt": prompt}, timeout=30)
    response.raise_for_status()
    return response.json()["result"]["response"]

def try_nvidia(prompt: str, model: str) -> str:
    response = requests.post(
        "https://integrate.api.nvidia.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {NVIDIA_NIM_API_KEY}", "Content-Type": "application/json"},
        json={"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 2048},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

def try_openrouter(prompt: str, model: str) -> str:
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://ai-sentuhtanahku-ui.vercel.app",
            "X-Title": "Sentuh Tanahku AI",
        },
        json={"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 2048},
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    if "choices" not in data:
        raise Exception(f"Format respons tidak dikenal: {data}")
    return data["choices"][0]["message"]["content"]

def try_scaleway(prompt: str, model: str) -> str:
    response = requests.post(
        "https://api.scaleway.ai/v1/chat/completions",
        headers={"Authorization": f"Bearer {SCALEWAY_API_KEY}", "Content-Type": "application/json"},
        json={"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 2048},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

# --- FALLBACK CHAIN: urutan kualitas terbaik dulu lintas semua provider ---
# (provider, model, fn, has_key)
FALLBACK_CHAIN = [
    ("sambanova",  "DeepSeek-V3.1",                                          try_sambanova,  lambda: bool(SAMBANOVA_API_KEY)),                               # 671B
    ("cerebras",   "qwen-3-235b-a22b-instruct-2507",                         try_cerebras,   lambda: bool(CEREBRAS_API_KEY)),                                # 235B
    ("openrouter", "nousresearch/hermes-3-llama-3.1-405b:free",              try_openrouter, lambda: bool(OPENROUTER_API_KEY)),                              # 405B free
    ("openrouter", "openrouter/owl-alpha",                                   try_openrouter, lambda: bool(OPENROUTER_API_KEY)),                              # high-perf, 1M ctx, 1.2T token/week free
    ("nvidia",     "nvidia/nemotron-3-super-120b-a12b",                       try_nvidia,     lambda: bool(NVIDIA_NIM_API_KEY)),                              # 120B
    ("openrouter", "openai/gpt-oss-120b:free",                               try_openrouter, lambda: bool(OPENROUTER_API_KEY)),                              # 120B free
    ("openrouter", "nvidia/nemotron-3-super-120b-a12b:free",                 try_openrouter, lambda: bool(OPENROUTER_API_KEY)),                              # 120B free
    ("scaleway",   "qwen3-235b-a22b-instruct-2507",                          try_scaleway,   lambda: bool(SCALEWAY_API_KEY)),                                # 235B
    ("sambanova",  "gpt-oss-120b",                                           try_sambanova,  lambda: bool(SAMBANOVA_API_KEY)),                               # 120B
    ("cerebras",   "gpt-oss-120b",                                           try_cerebras,   lambda: bool(CEREBRAS_API_KEY)),                                # 120B
    ("scaleway",   "gpt-oss-120b",                                           try_scaleway,   lambda: bool(SCALEWAY_API_KEY)),                                # 120B
    ("sambanova",  "Meta-Llama-3.3-70B-Instruct",                            try_sambanova,  lambda: bool(SAMBANOVA_API_KEY)),                               # 70B
    ("groq",       "llama-3.3-70b-versatile",                                try_groq,       lambda: bool(GROQ_API_KEY)),                                    # 70B
    ("mistral",    "mistral-large-2411",                                     try_mistral,    lambda: bool(MISTRAL_API_KEY)),                                 # ~70B
    ("cloudflare", "@cf/meta/llama-3.3-70b-instruct-fp8-fast",               try_cloudflare, lambda: bool(CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN)),  # 70B quant
    ("nvidia",     "meta/llama-3.3-70b-instruct",                            try_nvidia,     lambda: bool(NVIDIA_NIM_API_KEY)),                              # 70B
    ("nvidia",     "nvidia/llama-3.3-nemotron-super-49b-v1",                 try_nvidia,     lambda: bool(NVIDIA_NIM_API_KEY)),                              # 49B
    ("openrouter", "meta-llama/llama-3.3-70b-instruct:free",                 try_openrouter, lambda: bool(OPENROUTER_API_KEY)),                              # 70B free
    ("scaleway",   "llama-3.3-70b-instruct",                                 try_scaleway,   lambda: bool(SCALEWAY_API_KEY)),                                # 70B
    ("openrouter", "deepseek/deepseek-v4-flash:free",                        try_openrouter, lambda: bool(OPENROUTER_API_KEY)),                              # large free
    ("mistral",    "mistral-medium-2505",                                    try_mistral,    lambda: bool(MISTRAL_API_KEY)),                                 # Medium
    ("cerebras",   "zai-glm-4.7",                                            try_cerebras,   lambda: bool(CEREBRAS_API_KEY)),                                # Preview
    ("groq",       "llama-3.1-8b-instant",                                   try_groq,       lambda: bool(GROQ_API_KEY)),                                    # 8B
    ("mistral",    "mistral-small-2506",                                     try_mistral,    lambda: bool(MISTRAL_API_KEY)),                                 # Small
    ("cerebras",   "llama3.1-8b",                                            try_cerebras,   lambda: bool(CEREBRAS_API_KEY)),                                # 8B
    ("nvidia",     "nvidia/llama-3.1-nemotron-nano-8b-v1",                   try_nvidia,     lambda: bool(NVIDIA_NIM_API_KEY)),                              # 8B
    ("cloudflare", "@cf/meta/llama-3.1-8b-instruct",                         try_cloudflare, lambda: bool(CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN)),  # 8B
    ("gemini",     "gemini-2.5-flash",                                       try_gemini,     lambda: bool(GEMINI_API_KEY)),                                  # quota kecil
    ("gemini",     "gemini-2.5-flash-lite",                                  try_gemini,     lambda: bool(GEMINI_API_KEY)),                                  # quota kecil
]

def generate_jawaban(prompt: str) -> tuple[str, str, str]:
    """Coba LLM satu per satu. Return (jawaban, provider, model)."""
    errors = []
    for provider, model, fn, has_key in FALLBACK_CHAIN:
        if not has_key():
            continue
        try:
            return fn(prompt, model), provider, model
        except Exception as e:
            print(f"[fallback] {provider}/{model} gagal: {e}")
            errors.append(f"{provider}/{model}: {e}")
    raise Exception("Semua LLM gagal. Detail: " + " | ".join(errors))

@app.get("/test-provider/{provider}/{model:path}")
def test_provider_model(provider: str, model: str):
    """Test satu model spesifik. Contoh: /test-provider/openrouter/meta-llama/llama-3.3-70b-instruct:free"""
    prompt = "Jawab singkat: apa itu hak tanggungan?"

    # Cari fungsi provider dari FALLBACK_CHAIN
    provider_fn = None
    provider_key_fn = None
    for prov, m, fn, has_key in FALLBACK_CHAIN:
        if prov == provider:
            provider_fn = fn
            provider_key_fn = has_key
            break

    if provider_fn is None:
        available = list(dict.fromkeys(p for p, m, fn, hk in FALLBACK_CHAIN))
        raise HTTPException(status_code=400, detail=f"Provider tidak dikenal. Pilihan: {available}")

    if not provider_key_fn():
        raise HTTPException(status_code=400, detail=f"API key untuk '{provider}' belum diset.")

    try:
        jawaban = provider_fn(prompt, model)
        return {"status": "success", "provider": provider, "model": model, "jawaban": jawaban}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"message": f"{provider}/{model} gagal.", "error": str(e)})

@app.get("/test-provider/{provider}")
def test_provider(provider: str):
    """Test semua model dari provider tertentu. Provider: sambanova, cerebras, groq, mistral, cloudflare, gemini, nvidia, openrouter, scaleway"""
    prompt = "Jawab singkat: apa itu hak tanggungan?"
    available = list(dict.fromkeys(p for p, m, fn, hk in FALLBACK_CHAIN))

    if provider not in available:
        raise HTTPException(status_code=400, detail=f"Provider tidak dikenal. Pilihan: {available}")

    errors = []
    for prov, model, fn, has_key in FALLBACK_CHAIN:
        if prov != provider:
            continue
        if not has_key():
            raise HTTPException(status_code=400, detail=f"API key untuk '{provider}' belum diset.")
        try:
            jawaban = fn(prompt, model)
            return {"status": "success", "provider": prov, "model": model, "jawaban": jawaban}
        except Exception as e:
            error_msg = f"{model}: {e}"
            print(f"[test] {prov}/{error_msg}")
            errors.append(error_msg)
            continue

    raise HTTPException(status_code=500, detail={"message": f"Semua model dari '{provider}' gagal.", "errors": errors})

@app.post("/api/chat")
def chat_endpoint(request: ChatRequest):
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise HTTPException(status_code=500, detail="Konfigurasi server belum lengkap (API Key hilang).")
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY belum diset (wajib untuk embedding).")

    try:
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)

        # 1. Embedding (selalu Gemini, 768 dim)
        emb_response = gemini_client.models.embed_content(
            model='gemini-embedding-001',
            contents=request.pesan,
            config=types.EmbedContentConfig(output_dimensionality=768)
        )
        query_vector = emb_response.embeddings[0].values

        # 2. Cari dokumen di Supabase
        rpc_url = f"{SUPABASE_URL}/rest/v1/rpc/match_bpn_knowledge"
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json"
        }
        db_response = requests.post(rpc_url, headers=headers, json={
            "query_embedding": query_vector,
            "match_threshold": 0.5,
            "match_count": 3
        })
        if db_response.status_code != 200:
            raise Exception(f"Error Supabase: {db_response.text}")
        documents = db_response.json()

        sumber_list = []
        if not documents:
            konteks_dokumen = "Tidak ditemukan dokumen SOP spesifik yang relevan."
        else:
            konteks_parts = []
            for doc in documents:
                metadata = doc.get('metadata', {})
                kategori = metadata.get('kategori_layanan', 'Layanan Umum BPN')
                referensi = metadata.get('referensi_hukum', 'SOP Internal')
                isi_konten = doc.get('content', '')
                sumber_list.append(f"{kategori} ({referensi})")
                konteks_parts.append(f"--- [Kategori: {kategori} | Dasar Hukum: {referensi}] ---\n{isi_konten}")
            konteks_dokumen = "\n\n".join(konteks_parts)
            sumber_list = list(set(sumber_list))

        # 3. Rangkai riwayat chat
        teks_riwayat = ""
        if request.riwayat:
            teks_riwayat = "\n--- RIWAYAT PERCAKAPAN SEBELUMNYA ---\n"
            for chat in request.riwayat[-4:]:
                pengirim = "User" if chat["role"] == "user" else "Senta"
                teks_riwayat += f"{pengirim}: {chat['content']}\n"
            teks_riwayat += "--------------------------------------\n"

        # 4. Generate jawaban
        prompt_sistem = f"""
        PERAN:
        Kamu adalah "Senta" (Sentuh Tanahku AI), asisten virtual dari BPN.
        Gaya bicaramu itu seperti teman sendiri (bestie) yang friendly, asik, santai, elegan, dan suka pakai emoji yang pas! ✨
        {teks_riwayat}

        DATA REFERENSI (HANYA JAWAB DARI SINI):
        {konteks_dokumen}

        ATURAN GAYA BICARA:
        1. Sapaan: Panggil user "Kak".
        2. Perhatikan [RIWAYAT PERCAKAPAN SEBELUMNYA]. Jika user merujuk ke obrolan sebelumnya, jawablah dengan nyambung berdasarkan riwayat tersebut. Jangan mengulangi sapaan seperti Halo/Hai jika sudah berada di tengah percakapan.
        3. Bahasa percakapan harus luwes, asik, dan elegan. Jangan kaku sama sekali.
        4. Wajib pakai emoji yang relevan.
        5. Pecah jawaban jadi paragraf atau poin-poin pendek agar nyaman dibaca.
        6. Sebutkan Dasar Hukum sekilas di akhir jawaban jika ada di referensi.

        JURUS "NGELES" ELEGAN:
        Jika jawaban TIDAK ADA di referensi sama sekali, DILARANG KERAS mengarang/halusinasi. Gunakan gaya ngeles yang elegan dan tetap asik.
        Contoh: "Duh maaf banget ya kak 🙏, kalau soal yang satu ini Senta belum dapet bocoran datanya dari pusat nih. Coba deh mampir ke loket BPN terdekat atau cek langsung di aplikasi Sentuh Tanahku! Ada hal lain yang bisa Senta bantu?"

        PERTANYAAN USER SAAT INI: {request.pesan}
        """

        jawaban, provider, model = generate_jawaban(prompt_sistem)

        return {
            "status": "success",
            "provider": provider,
            "model_used": model,
            "jawaban": jawaban,
            "sumber": sumber_list
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
