import os
import requests
import time
from pypdf import PdfReader
from google import genai

# --- 1. KONFIGURASI ---
SUPABASE_URL = "https://hzmlxnsnuycvqkpetxhe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh6bWx4bnNudXljdnFrcGV0eGhlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzEzNDM1ODQsImV4cCI6MjA4NjkxOTU4NH0.0ahv8dGihy3EtCeR-NTPUuh4faW8lnJyq-laH7KGxW0"
GEMINI_API_KEY = "AIzaSyCAStXtATtpinWyay5RZvRusvZXYJmqGR4"

# --- 2. KONFIGURASI RESUME (PENTING!) ---
# Jika script mati di tengah jalan, lihat log terakhir "Gagal bagian X".
# Ganti angka 0 di bawah ini menjadi X (misal: 150) untuk melanjutkan.
MULAI_DARI_PART = 0 

client = genai.Client(api_key=GEMINI_API_KEY)

def clean_text_basic(text):
    return " ".join(text.split())

def get_pdf_text(pdf_path):
    print(f"📖 Membaca PDF (FULL): {os.path.basename(pdf_path)}...")
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
            print(f"⚠️ Gagal embedding (percobaan {attempt+1}): {e}")
            time.sleep(2 * (attempt + 1))
    return None

def upload_to_supabase(chunks, filename):
    print(f"\n🚀 Memproses: {filename} (Total {len(chunks)} potongan)")
    
    # LOGIKA RESUME: Lewati potongan yang sudah sukses sebelumnya
    if MULAI_DARI_PART > 0:
        print(f"⏩ Melompati {MULAI_DARI_PART} bagian awal. Lanjut dari Part {MULAI_DARI_PART + 1}...")

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    url = f"{SUPABASE_URL}/rest/v1/bpn_documents"

    sukses = 0
    
    # Loop mulai dari titik resume
    for i in range(MULAI_DARI_PART, len(chunks)):
        chunk = chunks[i]
        
        # Retry logic 
        max_retries = 5
        berhasil = False
        
        for attempt in range(max_retries):
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
                    print(f"  ✅ Bagian {i+1} tersimpan.")
                    sukses += 1
                    berhasil = True
                    break 
                else:
                    print(f"  ❌ Gagal bagian {i+1}: {res.text}")
                    time.sleep(1)
                    
            except Exception as e:
                print(f"  ⚠️ Koneksi error: {e}")
                time.sleep(2)
        
        if not berhasil:
            print(f"❌❌ GAGAL TOTAL di bagian {i+1}. Script berhenti.")
            print(f"👉 TIPS: Ubah 'MULAI_DARI_PART = {i}' di script lalu jalankan lagi.")
            exit() # Matikan script agar user sadar ada error

        time.sleep(0.2) 

    print(f"🏁 Selesai! {sukses} bagian berhasil diupload.")

def main():
    folder_path = "dokumen_sumber"
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        return

    files = [f for f in os.listdir(folder_path) if f.lower().endswith('.pdf')]
    if not files: return

    print(f"🔍 Ditemukan {len(files)} file PDF. Mode: RAW + RESUME SUPPORT.")
    
    for file in files:
        path = os.path.join(folder_path, file)
        
        # 1. Baca (Raw)
        raw_text = get_pdf_text(path)
        
        if len(raw_text) < 50:
            continue
            
        # 2. Chunking
        chunks = split_text_into_chunks(raw_text)
        
        # 3. Upload (Dengan dukungan Resume)
        upload_to_supabase(chunks, file)

if __name__ == "__main__":
    main()