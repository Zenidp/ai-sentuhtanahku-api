import os
import requests
import time
from google import genai

# --- KONFIGURASI ---
SUPABASE_URL = "https://hzmlxnsnuycvqkpetxhe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh6bWx4bnNudXljdnFrcGV0eGhlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzEzNDM1ODQsImV4cCI6MjA4NjkxOTU4NH0.0ahv8dGihy3EtCeR-NTPUuh4faW8lnJyq-laH7KGxW0"
GEMINI_API_KEY = "AIzaSyCAStXtATtpinWyay5RZvRusvZXYJmqGR4"

client = genai.Client(api_key=GEMINI_API_KEY)

def split_text(text, chunk_size=1000, overlap=100):
    """Memecah teks bersih menjadi potongan"""
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
    try:
        response = client.models.embed_content(
            model='gemini-embedding-001',
            contents=teks[:9000]
        )
        return response.embeddings[0].values
    except Exception as e:
        print(f"⚠️ Gagal embedding: {e}")
        time.sleep(5)
        return None

def upload_to_supabase(chunks, filename):
    print(f"\n🚀 Uploading: {filename} ({len(chunks)} bagian)")
    
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    url = f"{SUPABASE_URL}/rest/v1/bpn_documents"

    sukses = 0
    for i, chunk in enumerate(chunks):
        vektor = generate_embedding(chunk)
        if not vektor: continue

        payload = {
            "judul": f"{filename} - Part {i+1}",
            "konten": chunk, # Teks sudah bersih dari Anda
            "sumber": filename,
            "embedding": vektor
        }

        try:
            res = requests.post(url, headers=headers, json=payload)
            if res.status_code in [200, 201]:
                print(f"  ✅ Tersimpan: Part {i+1}")
                sukses += 1
            else:
                print(f"  ❌ Gagal: {res.text}")
        except Exception as e:
            print(f"  ⚠️ Error Jaringan: {e}")
        
        time.sleep(0.5) # Rate limit protection

def main():
    folder_path = "dokumen_sumber_txt" # Bikin folder baru ini
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        print(f"Buat folder '{folder_path}' dan masukkan file .txt bersih disana.")
        return

    files = [f for f in os.listdir(folder_path) if f.lower().endswith('.txt')]
    
    for file in files:
        path = os.path.join(folder_path, file)
        with open(path, 'r', encoding='utf-8') as f:
            clean_text = f.read()
            
        chunks = split_text(clean_text)
        upload_to_supabase(chunks, file)

if __name__ == "__main__":
    main()