"""Diagnóstico: negociações em 'hold' e estrutura das atividades."""
import json, os, sys
from pathlib import Path
import httpx
from dotenv import load_dotenv

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

RAIZ = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ / ".env")
TOKEN = os.getenv("RD_CRM_TOKEN").strip()
BASE = os.getenv("RD_CRM_BASE_URL").strip()

def get(ep, params):
    return httpx.get(f"{BASE}/{ep}", params={"token": TOKEN, **params}, timeout=40).json()

# 1) Negociações em hold (pausadas)
hold = get("deals", {"limit": 1, "hold": "true"})
print("Negociacoes em HOLD (total):", hold.get("total"))

# 2) Estrutura das atividades (amostra)
atv = get("activities", {"limit": 3})
print("\nCHAVES da resposta de activities:", list(atv.keys()) if isinstance(atv, dict) else type(atv))
lista = atv.get("activities") if isinstance(atv, dict) else atv
print("Total de atividades:", atv.get("total") if isinstance(atv, dict) else "?")
if lista:
    print("\n=== UMA ATIVIDADE (campos) ===")
    print(json.dumps(lista[0], indent=2, ensure_ascii=False)[:2000])
    print("\nTIPOS encontrados na amostra:", set(a.get("_type") or a.get("type") or a.get("activity_type") for a in lista))
