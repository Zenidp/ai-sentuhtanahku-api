#!/usr/bin/env python3
"""
Set GEMINI_API_KEYS di service Render lewat Render API — dengan aman.

Rahasia TIDAK pernah diketik ke chat / hardcode di kode. Script ini membaca
kredensial dari file lokal `.env` (sudah di-gitignore) atau dari environment.

Yang dibutuhkan di `.env` (di folder yang sama, JANGAN di-commit):
    RENDER_API_KEY=rnd_xxxxxxxxxxxxxxxx          # buat di Render → Account Settings → API Keys
    GEMINI_API_KEYS=key1,key2,key3,key4,key5     # 5 key Gemini dipisah koma
    # opsional (kalau nama service beda):
    RENDER_SERVICE_NAME=ai-sentuhtanahku-api

Jalankan:
    python3 set_render_gemini_keys.py

Script ini:
  1. Cari service by name → dapat service ID
  2. Upsert HANYA variabel GEMINI_API_KEYS (variabel lain tidak disentuh)
  3. Trigger 1x deploy
  4. Cetak konfirmasi TERMASK (nilai key tidak pernah ditampilkan)
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.render.com/v1"


def load_dotenv(path=".env"):
    """Parser .env minimal (tanpa dependency)."""
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            # env asli menang; .env hanya mengisi yang belum ada
            os.environ.setdefault(key, val)


def mask(secret: str) -> str:
    if not secret:
        return "(kosong)"
    parts = [p.strip() for p in secret.split(",") if p.strip()]
    masked = [f"{p[:6]}…{p[-4:]}" if len(p) > 12 else "***" for p in parts]
    return f"{len(parts)} key → " + ", ".join(masked)


def api(method: str, path: str, token: str, body=None):
    url = f"{API}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/json")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        detail = e.read().decode()
        print(f"❌ Render API {method} {path} → HTTP {e.code}\n   {detail}")
        sys.exit(1)


def main():
    load_dotenv()

    token = os.getenv("RENDER_API_KEY", "").strip()
    keys = os.getenv("GEMINI_API_KEYS", "").strip()
    service_name = os.getenv("RENDER_SERVICE_NAME", "ai-sentuhtanahku-api").strip()

    if not token:
        sys.exit("❌ RENDER_API_KEY belum diset (di .env atau environment).")
    if not keys:
        sys.exit("❌ GEMINI_API_KEYS belum diset (di .env atau environment).")

    print(f"🔎 Cari service '{service_name}' ...")
    services = api("GET", f"/services?name={urllib.parse.quote(service_name)}&limit=20", token)
    service_id = None
    for item in services or []:
        svc = item.get("service", item)
        if svc.get("name") == service_name:
            service_id = svc.get("id")
            break
    if not service_id:
        sys.exit(f"❌ Service '{service_name}' tidak ditemukan di akun ini.")
    print(f"   ✅ ketemu: {service_id}")

    print(f"🔑 Set GEMINI_API_KEYS  ({mask(keys)})")
    api("PUT", f"/services/{service_id}/env-vars/GEMINI_API_KEYS", token, {"value": keys})
    print("   ✅ variabel ter-upsert (variabel lain tidak disentuh)")

    print("🚀 Trigger deploy ...")
    dep = api("POST", f"/services/{service_id}/deploys", token, {})
    dep_id = (dep or {}).get("id", "(tak diketahui)")
    print(f"   ✅ deploy dimulai: {dep_id}")
    print("\n🎉 Selesai. Tunggu ~1-2 menit sampai deploy 'live', lalu tes chat lagi.")


if __name__ == "__main__":
    main()
