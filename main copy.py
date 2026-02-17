from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google import genai
import os

# Inisialisasi Aplikasi FastAPI
app = FastAPI(
    title="API AI Sentuh Tanahku",
    description="Middleware AI untuk melayani aplikasi mobile Sentuh Tanahku",
    version="1.0.1"
)

# Konfigurasi Client GenAI (SDK Baru)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

class ChatRequest(BaseModel):
    pesan: str
    session_id: str

@app.get("/")
def read_root():
    return {"status": "Server Middleware AI Sentuh Tanahku Aktif dan Berjalan!"}

@app.post("/api/chat")
def chat_endpoint(request: ChatRequest):
    try:
        if not GEMINI_API_KEY:
            raise HTTPException(status_code=500, detail="Gemini API Key belum diatur di server (Environment Variable).")

        # Inisialisasi client menggunakan API Key
        client = genai.Client(api_key=GEMINI_API_KEY)

        dokumen_bpn = "SOP BPN: Pendaftaran tanah pertama kali memerlukan KTP, KK, Bukti Penguasaan Fisik, dan Surat Bebas Sengketa."

        prompt_sistem = f"""
        Anda adalah asisten virtual resmi untuk aplikasi 'Sentuh Tanahku' dari Kementerian ATR/BPN.
        Tugas Anda adalah menjawab pertanyaan warga HANYA berdasarkan informasi berikut:
        {dokumen_bpn}
        
        Pertanyaan Warga: {request.pesan}
        """

        # Memanggil API Gemini menggunakan sintaks SDK terbaru
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt_sistem,
        )

        return {
            "status": "success",
            "jawaban": response.text,
            "sumber_dokumen": ["SOP Pendaftaran Tanah"]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))