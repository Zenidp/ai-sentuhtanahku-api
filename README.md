# 🏛️ Sentuh Tanahku AI — Frontend (Senta UI)

> Antarmuka chat modern untuk **Senta**, asisten virtual layanan pertanahan BPN.

Frontend ini adalah antarmuka pengguna berbasis Next.js yang menyediakan pengalaman chat yang elegan dan responsif untuk berinteraksi dengan sistem RAG Sentuh Tanahku AI.

> **Repositori terkait:** Backend API tersedia di [`ai-sentuhtanahku-api`](https://github.com/username/ai-sentuhtanahku-api) — lihat README di sana untuk dokumentasi sistem lengkap dan arsitektur keseluruhan.

---

## ✨ Fitur

- **Chat real-time** dengan streaming jawaban
- **Riwayat percakapan** tersimpan per user (PostgreSQL)
- **Model selector** — dapat berganti model AI
- **Artifact panel** — render kode, dokumen, dan spreadsheet hasil AI
- **Autentikasi** dengan NextAuth v5
- **Dark/Light mode**
- **Responsive** untuk desktop dan mobile

---

## 🛠️ Tech Stack

| Komponen | Teknologi |
|---|---|
| Framework | Next.js 16 (App Router) |
| Language | TypeScript + React 19 |
| AI Integration | Vercel AI SDK v6 + AI Gateway |
| Default Model | `google/gemini-2.5-flash-lite` (Senta AI v1.0) |
| Auth | NextAuth v5 |
| ORM | Drizzle ORM |
| Database | PostgreSQL (Vercel Postgres) |
| Cache | Redis (Vercel KV) |
| Storage | Vercel Blob |
| Styling | Tailwind CSS v4 + Radix UI |
| Package Manager | pnpm |

---

## 🚀 Setup Lokal

**1. Install dependencies**
```bash
pnpm install
```

**2. Buat `.env.local`**
```env
AUTH_SECRET=your-random-secret-32-chars
AI_GATEWAY_API_KEY=your-vercel-ai-gateway-key
BLOB_READ_WRITE_TOKEN=your-vercel-blob-token
POSTGRES_URL=your-postgres-connection-string
REDIS_URL=your-redis-connection-string
```

**3. Migrasi database**
```bash
pnpm db:migrate
```

**4. Jalankan development server**
```bash
pnpm dev
```

Akses di `http://localhost:3000`

---

## 📋 Scripts

```bash
pnpm dev          # Development server (Turbopack)
pnpm build        # Build production
pnpm start        # Jalankan production build
pnpm db:migrate   # Migrasi database
pnpm db:studio    # Drizzle Studio GUI
pnpm test         # Playwright E2E tests
pnpm lint         # Linting
pnpm format       # Format kode
```

---

## 🚢 Deploy ke Vercel

1. Connect repo ke Vercel
2. Tambahkan semua environment variables
3. Deploy — otomatis saat push ke `main`

Live: **https://ai-sentuhtanahku-ui.vercel.app**
