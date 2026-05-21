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

# Struktur untuk menerima riwayat obrolan
class ChatRequest(BaseModel):
    pesan: str
    session_id: str = "default"  
    riwayat: List[Dict[str, str]] = [] # Format: [{"role": "user", "content": "halo"}, {"role": "assistant", "content": "hai"}]

@app.get("/")
def read_root():
    return {"status": "Sistem RAG Sentuh Tanahku (Genius + Memory Mode) Aktif!"}

def try_cerebras(prompt: str) -> str:
    cerebras_client = Cerebras(api_key=CEREBRAS_API_KEY)
    response = cerebras_client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama3.1-8b",
    )
    return response.choices[0].message.content

def try_mistral(prompt: str) -> str:
    response = requests.post(
        "https://api.mistral.ai/v1/chat/completions",
        headers={"Authorization": f"Bearer {MISTRAL_API_KEY}", "Content-Type": "application/json"},
        json={"model": "mistral-large-latest", "messages": [{"role": "user", "content": prompt}], "max_tokens": 2048},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

def try_sambanova(prompt: str) -> str:
    response = requests.post(
        "https://api.sambanova.ai/v1/chat/completions",
        headers={"Authorization": f"Bearer {SAMBANOVA_API_KEY}", "Content-Type": "application/json"},
        json={"model": "Meta-Llama-3.3-70B-Instruct", "messages": [{"role": "user", "content": prompt}], "max_tokens": 2048},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

def try_groq(prompt: str) -> str:
    groq_client = Groq(api_key=GROQ_API_KEY)
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=2048,
    )
    return response.choices[0].message.content

def try_cloudflare(prompt: str) -> str:
    url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/@cf/meta/llama-3.1-8b-instruct"
    headers = {"Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}"}
    response = requests.post(url, headers=headers, json={"prompt": prompt}, timeout=30)
    response.raise_for_status()
    return response.json()["result"]["response"]

def try_gemini(prompt: str) -> str:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    response = gemini_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    return response.text

# Urutan fallback: LLM pertama dicoba dulu, kalau gagal lanjut ke berikutnya
# Tambah LLM baru cukup tambah fungsi try_xxx() dan sisipkan di list ini
FALLBACK_CHAIN = [
    ("cerebras/llama3.1-8b",     try_cerebras,    lambda: bool(CEREBRAS_API_KEY)),
    ("groq/llama-3.3-70b",       try_groq,        lambda: bool(GROQ_API_KEY)),
    ("mistral-large",            try_mistral,      lambda: bool(MISTRAL_API_KEY)),
    ("sambanova/llama-3.3-70b",  try_sambanova,    lambda: bool(SAMBANOVA_API_KEY)),
    ("gemini-2.5-flash",         try_gemini,       lambda: bool(GEMINI_API_KEY)),
    ("cloudflare/llama-3.1-8b",  try_cloudflare,   lambda: bool(CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN)),
]

def generate_jawaban(prompt: str) -> tuple[str, str]:
    """Coba LLM satu per satu sesuai urutan FALLBACK_CHAIN. Return (jawaban, model_label)."""
    errors = []
    for label, fn, has_key in FALLBACK_CHAIN:
        if not has_key():
            continue
        try:
            return fn(prompt), label
        except Exception as e:
            print(f"[fallback] {label} gagal: {e}")
            errors.append(f"{label}: {e}")
    raise Exception("Semua LLM gagal. Detail: " + " | ".join(errors))


@app.post("/api/chat")
def chat_endpoint(request: ChatRequest):
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise HTTPException(status_code=500, detail="Konfigurasi server belum lengkap (API Key hilang).")
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY belum diset (wajib untuk embedding).")

    try:
        # Embedding selalu pakai Gemini karena knowledge base dibangun dengan dimensi 768
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)

        # 1. Jadikan pertanyaan sebagai vektor (DENGAN DIMENSI 768)
        emb_response = gemini_client.models.embed_content(
            model='gemini-embedding-001',
            contents=request.pesan,
            config=types.EmbedContentConfig(
                output_dimensionality=768 # <-- PENYESUAIAN WAJIB agar muat di Supabase!
            )
        )
        query_vector = emb_response.embeddings[0].values

        # 2. Cari dokumen di Supabase
        rpc_url = f"{SUPABASE_URL}/rest/v1/rpc/match_bpn_knowledge"
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "query_embedding": query_vector,
            "match_threshold": 0.5, 
            "match_count": 3        
        }
        
        db_response = requests.post(rpc_url, headers=headers, json=payload)
        
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

        # 3. RANGKAI RIWAYAT CHAT SEBELUMNYA
        teks_riwayat = ""
        if request.riwayat:
            teks_riwayat = "\n--- RIWAYAT PERCAKAPAN SEBELUMNYA ---\n"
            # Ambil maksimal 4 chat terakhir agar konteks tidak terlalu panjang dan hemat token
            for chat in request.riwayat[-4:]:
                pengirim = "User" if chat["role"] == "user" else "Senta"
                teks_riwayat += f"{pengirim}: {chat['content']}\n"
            teks_riwayat += "--------------------------------------\n"

        # 4. Inject Riwayat ke Prompt Senta (PERSONA BESTIE & NGELES ELEGAN)
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

        jawaban, model_label = generate_jawaban(prompt_sistem)

        return {
            "status": "success",
            "model_used": model_label,
            "jawaban": jawaban,
            "sumber": sumber_list
        }

    except Exception as e:
        print(f"Error: {str(e)}") 
        raise HTTPException(status_code=500, detail=str(e))