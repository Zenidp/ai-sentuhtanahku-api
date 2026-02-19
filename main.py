from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google import genai
from google.genai import types # <-- Tambahan import untuk konfigurasi dimensi
import os
import requests
from typing import List, Dict

app = FastAPI(title="API AI Sentuh Tanahku (Genius + Memory Mode)")

# --- KONFIGURASI KEAMANAN ---
# Catatan: Jika nanti naik ke production, lebih aman pindahkan key ini ke file .env ya!
SUPABASE_URL = "https://hzmlxnsnuycvqkpetxhe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh6bWx4bnNudXljdnFrcGV0eGhlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzEzNDM1ODQsImV4cCI6MjA4NjkxOTU4NH0.0ahv8dGihy3EtCeR-NTPUuh4faW8lnJyq-laH7KGxW0"
GEMINI_API_KEY = "AIzaSyCAStXtATtpinWyay5RZvRusvZXYJmqGR4"

# Struktur untuk menerima riwayat obrolan
class ChatRequest(BaseModel):
    pesan: str
    session_id: str = "default"  
    riwayat: List[Dict[str, str]] = [] # Format: [{"role": "user", "content": "halo"}, {"role": "assistant", "content": "hai"}]

@app.get("/")
def read_root():
    return {"status": "Sistem RAG Sentuh Tanahku (Genius + Memory Mode) Aktif!"}

@app.post("/api/chat")
def chat_endpoint(request: ChatRequest):
    # Pengecekan API Key. Karena sudah diisi di atas, blok ini akan aman dilewati.
    if not GEMINI_API_KEY or not SUPABASE_URL or not SUPABASE_KEY:
        raise HTTPException(status_code=500, detail="Konfigurasi server belum lengkap (API Key hilang).")

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)

        # 1. Jadikan pertanyaan sebagai vektor (DENGAN DIMENSI 768)
        emb_response = client.models.embed_content(
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
        1. Sapaan: Panggil user "Kak", "Sobat", atau "Bestie". 
        2. Perhatikan [RIWAYAT PERCAKAPAN SEBELUMNYA]. Jika user merujuk ke obrolan sebelumnya, jawablah dengan nyambung berdasarkan riwayat tersebut.
        3. Bahasa percakapan harus luwes, asik, dan elegan. Jangan kaku sama sekali.
        4. Wajib pakai emoji yang relevan.
        5. Pecah jawaban jadi paragraf atau poin-poin pendek agar nyaman dibaca.
        6. Sebutkan Dasar Hukum sekilas di akhir jawaban jika ada di referensi.

        JURUS "NGELES" ELEGAN:
        Jika jawaban TIDAK ADA di referensi sama sekali, DILARANG KERAS mengarang/halusinasi. Gunakan gaya ngeles yang elegan dan tetap asik.
        Contoh: "Duh maaf banget ya bestie 🙏, kalau soal yang satu ini Senta belum dapet bocoran datanya dari pusat nih. Coba deh mampir ke loket BPN terdekat atau cek langsung di aplikasi Sentuh Tanahku! Ada hal lain yang bisa Senta bantu?"

        PERTANYAAN USER SAAT INI: {request.pesan}
        """

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
        print(f"Error: {str(e)}") 
        raise HTTPException(status_code=500, detail=str(e))