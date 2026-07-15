"""Shim kompatibilitas deploy Render — transisi monorepo.

Render masih menjalankan `uvicorn main:app` dari root repo. File ini
meneruskan `app` ke aplikasi sebenarnya di apps/api/main.py.

HAPUS file ini dan requirements.txt di root setelah Root Directory
di dashboard Render diset ke `apps/api` (docs/DEPLOYMENT.md bagian 1 & 3).
"""
import importlib.util
from pathlib import Path

_api_main = Path(__file__).resolve().parent / "apps" / "api" / "main.py"
_spec = importlib.util.spec_from_file_location("senta_api_main", _api_main)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

app = _mod.app
