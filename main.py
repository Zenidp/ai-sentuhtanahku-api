from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google import genai
import os
import requests

app = FastAPI(title="API AI Sentuh Tanahku (RAG Mode)")

# Konfigurasi Kunci dari Environment Variables
SUPABASE_URL = "https://hzmlxnsnuycvqkpetxhe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh6bWx4bnNudXljdnFrcGV0eGhlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzEzNDM1ODQsImV4cCI6MjA4NjkxOTU4NH0.0ahv8dGihy3EtCeR-NTPUuh4faW8lnJyq-laH7KGxW0"
GEMINI_API_KEY = "AIzaSyA9k21yPFqTkX2YMU8IeIH2ew2RJ5S9G2o"

# GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
# SUPABASE_URL = os.environ.get("SUPABASE_URL")
# SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

class ChatRequest(BaseModel):
    pesan: str
    session_id: str

@app.get("/")
def read_root():
    return {"status": "Sistem RAG Sentuh Tanahku Aktif!"}

@app.post("/api/chat")
def chat_endpoint(request: ChatRequest):
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)

        # 1. Ubah pertanyaan warga menjadi angka (Embedding)
        emb_response = client.models.embed_content(
            model='gemini-embedding-001',
            contents=request.pesan
        )
        query_vector = emb_response.embeddings[0].values

        # 2. Cari dokumen yang relevan di Supabase via RPC match_bpn_documents
        rpc_url = f"{SUPABASE_URL}/rest/v1/rpc/match_bpn_documents"
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "query_embedding": query_vector,
            "match_threshold": 0.5, # Ambil yang kemiripannya di atas 50%
            "match_count": 3        # Ambil 3 dokumen terbaik
        }
        
        db_response = requests.post(rpc_url, headers=headers, json=payload)
        documents = db_response.json()

        # 3. Gabungkan hasil pencarian menjadi konteks untuk Gemini
        konteks_dokumen = "\n\n".join([doc['konten'] for doc in documents])
        sumber_list = list(set([doc['sumber'] for doc in documents]))

        # 4. Minta Gemini menjawab berdasarkan data tersebut
        prompt_sistem = f"""
        Anda adalah asisten AI resmi Kementerian ATR/BPN. 
        Tugas Anda membantu warga menjawab pertanyaan mengenai pertanahan.
        Gunakan data referensi resmi di bawah ini untuk menjawab. 
        Jika jawaban tidak ada di referensi, katakan Anda tidak tahu dan sarankan datang ke kantor pertanahan terdekat.

        REFERENSI RESMI:
        {konteks_dokumen}

        PERTANYAAN WARGA: {request.pesan}
        """

        ai_response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=prompt_sistem
        )

        return {
            "status": "success",
            "jawaban": ai_response.text,
            "sumber": sumber_list
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))