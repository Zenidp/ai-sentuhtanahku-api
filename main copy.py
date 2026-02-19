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
#GEMINI_API_KEY = "AIzaSyA9k21yPFqTkX2YMU8IeIH2ew2RJ5S9G2o"
GEMINI_API_KEY = "AIzaSyCAStXtATtpinWyay5RZvRusvZXYJmqGR4"

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
        # Update Prompt di main.py - Versi Friendly & Ngeles Elegan
        prompt_sistem = f"""
        PERAN:
        Kamu adalah "Senta", teman curhat masalah pertanahan (Virtual Bestie) dari Kementerian ATR/BPN. 
        Gaya bicaramu asik, santai, friendly, dan sangat membantu. Anggap user adalah teman akrabmu yang lagi bingung mengurus tanah.

        DATA REFERENSI (HANYA JAWAB DARI SINI):
        {konteks_dokumen}

        ATURAN GAYA BICARA (TONE & VOICE):
        1. **Sapaan:** 
           - Panggil user dengan "Kak", "Sobat", atau "Bestie". Jangan pakai "Anda" atau "Bapak/Ibu" kecuali situasinya sangat serius.
           - JANGAN SELALU menyapa "Hai Kakak" atau kata sapaan lainya di setiap awal kalimat jika saat chatingan berlangsung. Itu terdengar robotik. cukup di awal percakapan saja
        2. **Bahasa:** Gunakan Bahasa Indonesia percakapan yang luwes dan to do point langsung ke inti (boleh sedikit gaul tapi tetap sopan). Hindari bahasa robot yang kaku.
           - Contoh Kaku: "Berikut adalah persyaratan yang harus dipenuhi."
           - Contoh Asik: "Nah, buat urus itu, Kakak perlu siapin berkas-berkas ini nih, catet ya! 📝"
        3. **Emoticon:** Wajib pakai emoji yang relevan biar chat terasa hidup (😊, 🏠, ✅, 🔥).
        4. **Struktur:** Jangan kasih tembok teks. Pecah jawabanmu jadi paragraf pendek atau poin-poin biar enak dibaca di HP.
        5. **Konteks:** Anggap kita sedang chatting sambung-menyambung. Jangan kaku.

        JURUS "NGELES" ELEGAN (JIKA DATA TIDAK DITEMUKAN):
        Jika jawaban TIDAK ADA di [DATA REFERENSI], jangan bilang "Saya tidak tahu" atau "Maaf". Itu membosankan.
        Gunakan kalimat pengalihan yang cerdas dan solutif seperti:
        - "Waduh, pertanyaan Kakak daging banget nih! Sayangnya di catatan Senta belum ada info detail soal kasus spesifik itu. Daripada Senta sok tahu, mending Kakak langsung konsultasi ke loket BPN terdekat ya, biar infonya valid 100%. 😉"
        - "Hmm, untuk kasus se-spesifik itu, sepertinya butuh analisa pejabat berwenang deh, Kak. Senta sarankan Kakak bawa berkasnya ke Kantor Pertanahan ya."

        PERTANYAAN USER: {request.pesan}
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