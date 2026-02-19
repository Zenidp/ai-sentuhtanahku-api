import json
from google import genai
from google.genai import types  # <--- [BARU] Import tipe data khusus Gemini
from supabase import create_client, Client

# --- KONFIGURASI KUNCI API ---
SUPABASE_URL = "https://hzmlxnsnuycvqkpetxhe.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh6bWx4bnNudXljdnFrcGV0eGhlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzEzNDM1ODQsImV4cCI6MjA4NjkxOTU4NH0.0ahv8dGihy3EtCeR-NTPUuh4faW8lnJyq-laH7KGxW0"
GEMINI_API_KEY = "AIzaSyCAStXtATtpinWyay5RZvRusvZXYJmqGR4"

# Setup Supabase & Gemini Client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
client = genai.Client(api_key=GEMINI_API_KEY)

TABLE_NAME = "bpn_knowledge_base"

def generate_embedding(text: str) -> list[float]:
    """Fungsi untuk mengubah teks menjadi vektor (Dimensi dipaksa ke 768)."""
    try:
        response = client.models.embed_content(
            model='gemini-embedding-001',
            contents=text,
            # <--- [KUNCI RAHASIA]: Kita perintahkan Gemini untuk memotongnya jadi 768 dimensi
            config=types.EmbedContentConfig(output_dimensionality=768) 
        )
        return response.embeddings[0].values
    except Exception as e:
        print(f"❌ Error saat membuat embedding: {e}")
        return None

def ingest_json_data(json_filepath: str):
    print(f"Membaca file {json_filepath}...")
    
    try:
        with open(json_filepath, 'r', encoding='utf-8') as file:
            data = json.load(file)
    except Exception as e:
        print(f"❌ Gagal membaca file JSON: {e}")
        return

    print(f"Ditemukan {len(data)} dokumen. Memulai proses injeksi...\n")

    for index, item in enumerate(data):
        print(f"[{index + 1}/{len(data)}] Memproses: {item['metadata'].get('kategori_layanan', 'Dokumen')}")
        
        content_to_embed = item.get("content_to_embed", "")
        content = item.get("content", "")
        metadata = item.get("metadata", {})

        print("   -> Membuat vektor embedding...")
        embedding = generate_embedding(content_to_embed)

        if embedding:
            payload = {
                "content": content,
                "content_to_embed": content_to_embed,
                "metadata": metadata,
                "embedding": embedding
            }

            try:
                # Karena sebelumnya gagal, data di Supabase masih kosong, jadi aman dari duplikat!
                response = supabase.table(TABLE_NAME).insert(payload).execute()
                print("   ✅ Berhasil disimpan ke Supabase!")
            except Exception as e:
                print(f"   ❌ Gagal menyimpan ke Supabase: {e}")
        else:
            print("   ⚠️ Lewati dokumen ini karena gagal membuat embedding.")
            
    print("\n🎉 Proses injeksi JSON selesai!")

if __name__ == "__main__":
    ingest_json_data("data_bpn.json")