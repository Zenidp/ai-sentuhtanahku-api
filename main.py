from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google import genai
import os
import requests

app = FastAPI(title="API AI Sentuh Tanahku (RAG Mode)")

# --- KONFIGURASI KEAMANAN (PENTING!) ---
# Mengambil kunci dari Environment Variables di Render/Laptop
# Jangan tulis API Key langsung di sini agar aman saat push ke GitHub.
# SUPABASE_URL = os.environ.get("https://hzmlxnsnuycvqkpetxhe.supabase.co")
# SUPABASE_KEY = os.environ.get("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh6bWx4bnNudXljdnFrcGV0eGhlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzEzNDM1ODQsImV4cCI6MjA4NjkxOTU4NH0.0ahv8dGihy3EtCeR-NTPUuh4faW8lnJyq-laH7KGxW0")
# GEMINI_API_KEY = os.environ.get("AIzaSyA9k21yPFqTkX2YMU8IeIH2ew2RJ5S9G2o")
SUPABASE_URL = "https://hzmlxnsnuycvqkpetxhe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh6bWx4bnNudXljdnFrcGV0eGhlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzEzNDM1ODQsImV4cCI6MjA4NjkxOTU4NH0.0ahv8dGihy3EtCeR-NTPUuh4faW8lnJyq-laH7KGxW0"
GEMINI_API_KEY = "AIzaSyA9k21yPFqTkX2YMU8IeIH2ew2RJ5S9G2o"

class ChatRequest(BaseModel):
    pesan: str
    session_id: str = "default"  # Default value jika user lupa mengirim

@app.get("/")
def read_root():
    return {"status": "Sistem RAG Sentuh Tanahku (Gemini 2.5) Aktif!"}

@app.post("/api/chat")
def chat_endpoint(request: ChatRequest):
    # Validasi variabel environment sebelum lanjut
    if not GEMINI_API_KEY or not SUPABASE_URL or not SUPABASE_KEY:
        raise HTTPException(status_code=500, detail="Konfigurasi server belum lengkap (API Key hilang).")

    try:
        # Inisialisasi Client Gemini Baru
        client = genai.Client(api_key=GEMINI_API_KEY)

        # 1. Ubah pertanyaan warga menjadi angka (Embedding)
        # Menggunakan model embedding yang sama dengan saat inject data
        emb_response = client.models.embed_content(
            model='gemini-embedding-001',
            contents=request.pesan
        )
        # Akses values vektor (sesuaikan dengan struktur SDK terbaru)
        query_vector = emb_response.embeddings[0].values

        # 2. Cari dokumen yang relevan di Supabase via RPC match_bpn_documents
        rpc_url = f"{SUPABASE_URL}/rest/v1/rpc/match_bpn_documents"
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json"
        }
        
        # Payload untuk mencari kemiripan
        payload = {
            "query_embedding": query_vector,
            "match_threshold": 0.5, # Ambil yang kemiripannya di atas 50%
            "match_count": 3        # Ambil 3 dokumen terbaik
        }
        
        db_response = requests.post(rpc_url, headers=headers, json=payload)
        
        if db_response.status_code != 200:
            raise Exception(f"Error Supabase: {db_response.text}")
            
        documents = db_response.json()

        # 3. Gabungkan hasil pencarian menjadi konteks untuk Gemini
        # Jika tidak ada dokumen yang cocok, beri konteks kosong
        if not documents:
            konteks_dokumen = "Tidak ditemukan dokumen SOP spesifik yang relevan."
            sumber_list = []
        else:
            konteks_dokumen = "\n\n".join([doc['konten'] for doc in documents])
            sumber_list = list(set([doc['sumber'] for doc in documents]))

        # 4. Minta Gemini menjawab berdasarkan data tersebut
        # Menggunakan model TERBARU: gemini-2.5-flash
        prompt_sistem = f"""
        Anda adalah asisten AI resmi Kementerian ATR/BPN bernama "Sentuh Tanahku AI".
        Tugas Anda membantu warga menjawab pertanyaan mengenai pertanahan dengan ramah dan profesional.
        
        INSTRUKSI PENTING:
        1. Gunakan HANYA data referensi di bawah ini untuk menjawab.
        2. Jika jawaban tidak ada di referensi, katakan dengan jujur: "Maaf, saya belum memiliki informasi spesifik mengenai hal tersebut. Silakan datang ke kantor BPN terdekat untuk konsultasi lebih lanjut."
        3. Jangan mengarang aturan atau pasal sendiri.

        REFERENSI DATA BPN:
        {konteks_dokumen}

        PERTANYAAN WARGA: {request.pesan}
        """

        # Generate jawaban menggunakan Gemini 2.5 Flash
        ai_response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt_sistem
        )

        return {
            "status": "success",
            "model_used": "gemini-2.5-flash",
            "jawaban": ai_response.text,
            "sumber": sumber_list
        }

    except Exception as e:
        print(f"Error: {str(e)}") # Print ke log server untuk debugging
        raise HTTPException(status_code=500, detail=str(e))