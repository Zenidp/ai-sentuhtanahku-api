import os
import requests
import time
from pypdf import PdfReader
from google import genai
import json

# --- 1. KONFIGURASI ---
SUPABASE_URL = "https://hzmlxnsnuycvqkpetxhe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh6bWx4bnNudXljdnFrcGV0eGhlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzEzNDM1ODQsImV4cCI6MjA4NjkxOTU4NH0.0ahv8dGihy3EtCeR-NTPUuh4faW8lnJyq-laH7KGxW0"
GEMINI_API_KEY = "AIzaSyCAStXtATtpinWyay5RZvRusvZXYJmqGR4"

client = genai.Client(api_key=GEMINI_API_KEY)

# --- 2. FUNGSI CEK DUPLIKAT ---
def is_file_uploaded(filename):
    """Mengecek ke Supabase apakah file ini sudah pernah diupload"""
    url = f"{SUPABASE_URL}/rest/v1/bpn_documents"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }
    # Query: Cari data dimana kolom 'sumber' sama dengan filename, ambil 1 saja cukup
    params = {
        "sumber": f"eq.{filename}",
        "select": "id",
        "limit": "1"
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        # Jika list tidak kosong, berarti file sudah ada
        return len(data) > 0
    except Exception as e:
        print(f"⚠️ Gagal cek status file: {e}")
        return False # Anggap belum ada biar aman

# --- 3. FUNGSI STANDAR LAINNYA ---
def clean_text_basic(text):
    return " ".join(text.split())

def get_pdf_text(pdf_path):
    print(f"📖 Membaca PDF: {os.path.basename(pdf_path)}...")
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + " "
    return clean_text_basic(text)

def split_text_into_chunks(text, chunk_size=1000, overlap=100):
    chunks = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap
    return chunks

def generate_embedding(teks):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.embed_content(
                model='gemini-embedding-001',
                contents=teks[:9000]
            )
            return response.embeddings[0].values
        except Exception as e:
            print(f"⚠️ Gagal embedding: {e}")
            time.sleep(2)
    return None

def upload_to_supabase(chunks, filename):
    print(f"🚀 Mulai Upload: {filename} ({len(chunks)} bagian)")
    
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    url = f"{SUPABASE_URL}/rest/v1/bpn_documents"

    sukses = 0
    for i in range(len(chunks)):
        chunk = chunks[i]
        
        # Retry logic upload
        for attempt in range(3):
            try:
                vektor = generate_embedding(chunk)
                if not vektor: break

                payload = {
                    "judul": f"{filename} - Part {i+1}",
                    "konten": chunk,
                    "sumber": filename,
                    "embedding": vektor
                }

                res = requests.post(url, headers=headers, json=payload, timeout=10)
                if res.status_code in [200, 201]:
                    print(f"  ✅ Bagian {i+1} OK")
                    sukses += 1
                    break
                else:
                    time.sleep(1)
            except:
                time.sleep(1)
        
        time.sleep(0.1) 

    print(f"🏁 Selesai upload {filename}.\n")

def main():
    folder_path = "dokumen_sumber"
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        return

    files = [f for f in os.listdir(folder_path) if f.lower().endswith('.pdf')]
    if not files: return

    print(f"🔍 Mengecek {len(files)} file di folder...")

    for file in files:
        # --- LOGIKA SMART SKIP ---
        print(f"❓ Memeriksa status: {file} ... ", end="")
        
        if is_file_uploaded(file):
            print("SUDAH ADA di Database. Skip! ⏩")
            continue # Lanjut ke file berikutnya
        
        print("BELUM ADA. Proses... ▶️")
        
        # Proses file baru
        path = os.path.join(folder_path, file)
        raw_text = get_pdf_text(path)
        if len(raw_text) < 50: continue
            
        chunks = split_text_into_chunks(raw_text)
        upload_to_supabase(chunks, file)

if __name__ == "__main__":
    main()