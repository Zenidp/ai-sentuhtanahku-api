# Panduan Deployment (Monorepo)

Sistem ini terdiri dari dua deployment yang membaca **repository yang sama** namun folder berbeda (fitur *Root Directory* di Render & Vercel).

## 1. Backend — Render

Di dashboard Render → service `ai-sentuhtanahku-api` → **Settings**:

| Setting | Nilai |
|---|---|
| Repository | repo monorepo ini |
| Branch | `main` |
| **Root Directory** | `apps/api` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn main:app --host 0.0.0.0 --port $PORT` |

Environment variables (Settings → Environment): lihat [apps/api/.env.example](../apps/api/.env.example). Minimal: `SUPABASE_URL`, `SUPABASE_KEY`, `GEMINI_API_KEYS`. Semakin banyak API key provider yang diisi, semakin kuat fallback chain-nya.

> 💡 Dengan Root Directory `apps/api`, Render hanya akan rebuild ketika ada perubahan di folder tersebut.

> ⚠️ **Shim transisi:** selama Root Directory di Render masih kosong (setting lama), deploy tetap berjalan lewat `main.py` dan `requirements.txt` di **root repo** yang meneruskan ke `apps/api`. Setelah Root Directory diset ke `apps/api`, **hapus kedua file shim tersebut**.

## 2. Frontend — Vercel

Di dashboard Vercel → project `ai-sentuhtanahku-ui` → **Settings → General**:

| Setting | Nilai |
|---|---|
| Repository | repo monorepo ini |
| **Root Directory** | `apps/web` |
| Framework Preset | Next.js |
| Install Command | `pnpm install` (default) |

Environment variables: `AUTH_SECRET`, `POSTGRES_URL`, `REDIS_URL`, `BLOB_READ_WRITE_TOKEN`, dan AI Gateway key — lihat [apps/web/.env.example](../apps/web/.env.example).

## 3. Migrasi dari dua repo ke monorepo (sekali jalan)

Riwayat git kedua repo lama sudah digabung penuh ke repo ini. Langkah finalisasi di sisi GitHub:

1. **Push branch monorepo** ke GitHub (`git push origin monorepo`), review, lalu merge/rename ke `main`.
2. (Opsional, direkomendasikan) **Rename repo** `ai-sentuhtanahku-api` → `ai-sentuhtanahku` di GitHub Settings, karena sekarang berisi seluruh sistem. GitHub otomatis me-redirect URL lama.
3. Di **Vercel**: ubah project agar menunjuk ke repo monorepo ini dan set Root Directory = `apps/web`.
4. Di **Render**: set Root Directory = `apps/api` (Build/Start command tidak berubah karena path relatif terhadap root directory).
5. Setelah kedua deployment hijau, **arsipkan** repo lama `ai-sentuhtanahku-ui` (GitHub Settings → Archive) agar tidak ada yang push ke tempat yang salah.

## 4. Uptime / keep-alive

- Endpoint `GET /health/db` sengaja murah (query 1 baris ke Supabase, tanpa LLM) — arahkan cron/uptime monitor ke sana untuk mencegah Supabase free tier ter-pause (~7 hari idle).
- Script [apps/api/scripts/set_render_gemini_keys.py](../apps/api/scripts/set_render_gemini_keys.py) dapat dipakai untuk memutar/menyetel `GEMINI_API_KEYS` di Render via API tanpa membuka dashboard.
