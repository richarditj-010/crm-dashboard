"""Etapa 3 (apoio) - inspeciona a estrutura real de UMA negociação para modelar o banco."""
import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

RAIZ = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ / ".env")
TOKEN = os.getenv("RD_CRM_TOKEN", "").strip()
BASE = os.getenv("RD_CRM_BASE_URL", "https://crm.rdstation.com/api/v1").strip()

r = httpx.get(f"{BASE}/deals", params={"token": TOKEN, "limit": 1}, timeout=30)
data = r.json()
deal = (data.get("deals") or [None])[0]
print("CHAVES DO TOPO DA RESPOSTA:", list(data.keys()))
print("\n=== UMA NEGOCIAÇÃO (campos) ===")
print(json.dumps(deal, indent=2, ensure_ascii=False)[:3000])
