"""
Conferência: compara os números do nosso painel (banco local) com os números
que a própria API do RD Station CRM reporta usando os filtros oficiais dela.
Se baterem, é prova de que os dados estão puxados certinhos.
"""
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
BASE = os.getenv("RD_CRM_BASE_URL").strip()


def total_api(params):
    p = {"token": TOKEN, "limit": 1, **params}
    r = httpx.get(f"{BASE}/deals", params=p, timeout=40)
    return r.json().get("total")

# --- Números segundo a API (fonte oficial) ---
total_geral = total_api({})
total_ganhas = total_api({"win": "true"})
total_perdidas = total_api({"win": "false"})
abertas_calc = total_geral - (total_ganhas or 0) - (total_perdidas or 0)

print("=== CONFERÊNCIA: API do RD Station x nosso painel ===\n")
print(f"Total de negociações (API): {total_geral}")
print(f"  - Ganhas (API, win=true):   {total_ganhas}")
print(f"  - Perdidas (API, win=false):{total_perdidas}")
print(f"  - Em aberto (cálculo):      {abertas_calc}")

# --- Números segundo o nosso banco local ---
sys.path.insert(0, str(Path(__file__).resolve().parent))
from app.db.database import SessionLocal
from app.db.models import Deal

db = SessionLocal()
deals = db.query(Deal).all()
db.close()

abertas = sum(1 for d in deals if d.win is None)
ganhas = sum(1 for d in deals if d.win is True)
perdidas = sum(1 for d in deals if d.win is False)

print("\nNosso painel (banco local):")
print(f"  Total: {len(deals)} | Abertas: {abertas} | Ganhas: {ganhas} | Perdidas: {perdidas}")

print("\n=== RESULTADO ===")
def ok(a, b):
    return "BATE ✅" if a == b else f"DIVERGE ❌ ({a} x {b})"

print(f"Total:    {ok(total_geral, len(deals))}")
print(f"Ganhas:   {ok(total_ganhas, ganhas)}")
print(f"Perdidas: {ok(total_perdidas, perdidas)}")
print(f"Abertas:  {ok(abertas_calc, abertas)}")
