# Senta API — Backend (FastAPI)

Backend RAG untuk **Senta (Sentuh Tanahku AI)**: menerima pertanyaan user, membuat embedding via Gemini, mencari dokumen relevan di Supabase (pgvector), lalu menghasilkan jawaban lewat fallback chain 28+ model dari 9 provider LLM.

## Menjalankan secara lokal

```bash
cd apps/api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # isi kredensial Anda
uvicorn main:app --reload   # http://localhost:8000
```

> **Catatan:** muat `.env` ke environment sebelum menjalankan (mis. `export $(grep -v '^#' .env | xargs)`), karena aplikasi membaca konfigurasi dari environment variables.

## Endpoint

| Method | Path | Deskripsi |
|---|---|---|
| `GET` | `/` | Health check sederhana |
| `GET` | `/health/db` | Ping murah ke Supabase (untuk uptime monitor / anti-pause free tier) |
| `POST` | `/api/chat` | Endpoint chat utama (RAG) |
| `GET` | `/test-provider/{provider}` | Uji semua model milik satu provider |
| `GET` | `/test-provider/{provider}/{model}` | Uji satu model spesifik |

Contoh request chat:

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"pesan": "Apa itu hak tanggungan?", "session_id": "demo", "riwayat": []}'
```

## Struktur

```
apps/api/
├── main.py            # Aplikasi FastAPI (RAG + fallback chain LLM)
├── requirements.txt   # Dependensi produksi
├── .env.example       # Template environment variables
├── data/
│   └── data_bpn.json  # Knowledge base sumber (SOP & regulasi BPN)
└── scripts/           # Alat bantu operasional (bukan bagian runtime API)
    ├── ingest_json.py           # Injeksi data/data_bpn.json ke Supabase
    ├── ingest_pdf.py            # Injeksi dokumen PDF
    ├── ingest_pdf_mulai_dari.py # Injeksi PDF, lanjut dari halaman tertentu
    ├── ingest_txt.py            # Injeksi file .txt
    ├── inject_data.py           # Injeksi data manual
    ├── set_render_gemini_keys.py# Set GEMINI_API_KEYS di Render via API
    └── demo_streamlit.py        # UI demo lama (butuh `pip install streamlit`)
```

Jalankan script ingest dari folder `apps/api` agar path relatif benar, contoh:

```bash
python scripts/ingest_json.py
```

## Deployment (Render)

- **Root Directory:** `apps/api`
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`

Lihat [docs/DEPLOYMENT.md](../../docs/DEPLOYMENT.md) untuk detail lengkap.
