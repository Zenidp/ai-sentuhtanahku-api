import os
import requests
from google import genai

# 1. KONFIGURASI KUNCI (ISI BAGIAN INI!)
SUPABASE_URL = "https://hzmlxnsnuycvqkpetxhe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh6bWx4bnNudXljdnFrcGV0eGhlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzEzNDM1ODQsImV4cCI6MjA4NjkxOTU4NH0.0ahv8dGihy3EtCeR-NTPUuh4faW8lnJyq-laH7KGxW0"
GEMINI_API_KEY = "AIzaSyA9k21yPFqTkX2YMU8IeIH2ew2RJ5S9G2o"

# 2. INISIALISASI GEMINI
client = genai.Client(api_key=GEMINI_API_KEY)

# 3. DATA DOKUMEN SOP BPN
dokumen_bpn = [
    {
        "judul": "Syarat Pendaftaran Tanah Pertama Kali",
        "konten": "Untuk pendaftaran tanah pertama kali (sebelumnya belum bersertifikat), pemohon wajib melampirkan Dokumen Asli KTP, Fotokopi Kartu Keluarga, Bukti Penguasaan Fisik Tanah selama lebih dari 20 tahun berturut-turut, Surat Pernyataan Bebas Sengketa dari Kelurahan, dan Surat Keterangan Riwayat Tanah.",
        "sumber": "SOP BPN No. 1 Tahun 2026 Pasal 4"
    },
    {
        "judul": "Syarat Pemecahan Sertifikat Tanah",
        "konten": "Pemecahan sertifikat tanah memerlukan pengajuan form permohonan pemecahan, Fotokopi Sertifikat Hak Milik (SHM) asli, KTP pemilik, Surat Persetujuan dari kreditor (jika tanah sedang diagunkan), dan Site Plan (rencana tapak) pemecahan yang disetujui dinas tata ruang setempat.",
        "sumber": "SOP BPN No. 2 Tahun 2026 Pasal 10"
    },
    {
        "judul": "Biaya Pengukuran Tanah PNBP",
        "konten": "Biaya pengukuran tanah diatur dalam PP tentang PNBP. Rumus biaya pengukuran untuk luas tanah kurang dari 10 Hektar adalah: (Luas Tanah / 500) x Rp 100.000 + Rp 100.000. Tambahan biaya transportasi petugas survei disesuaikan dengan jarak lokasi.",
        "sumber": "PP PNBP Kementerian ATR/BPN"
    }
]

def generate_embedding(teks: str) -> list[float]:
    """Mengubah teks menjadi vektor menggunakan Gemini"""
    print(f"Mengubah ke angka: '{teks[:30]}...'")
    response = client.models.embed_content(
        model='gemini-embedding-001', # <--- GANTI JADI INI
        contents=teks,
    )
    return response.embeddings[0].values

def inject_ke_supabase():
    print("Memulai injeksi data ke Supabase (Metode API API Rest)...\n")
    
    # Header khusus untuk otentikasi REST API Supabase
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    
    # URL Endpoint untuk tabel 'bpn_documents'
    endpoint_url = f"{SUPABASE_URL}/rest/v1/bpn_documents"

    for doc in dokumen_bpn:
        vektor = generate_embedding(doc["konten"])
        
        payload = {
            "judul": doc["judul"],
            "konten": doc["konten"],
            "sumber": doc["sumber"],
            "embedding": vektor
        }
        
        # Kirim HTTP POST ke Supabase
        response = requests.post(endpoint_url, headers=headers, json=payload)
        
        if response.status_code in [200, 201]:
            print(f"✅ Berhasil menyuntikkan: {doc['judul']}")
        else:
            print(f"❌ Gagal: {response.text}")

    print("\n🎉 Proses Selesai!")

if __name__ == "__main__":
    inject_ke_supabase()