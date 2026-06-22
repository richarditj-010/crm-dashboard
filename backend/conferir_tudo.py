"""
Conferência COMPLETA: cruza cada número do dashboard com a API oficial do RD Station,
considerando a exclusão dos ex-funcionários. Também checa consistência interna.
"""
import os, sys
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
APP = "http://127.0.0.1:8000"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from app.config import EX_FUNCIONARIOS, eh_ex_funcionario


def api_total(params):
    p = {"token": TOKEN, "limit": 1, **params}
    return httpx.get(f"{BASE}/deals", params=p, timeout=40).json().get("total") or 0


def app_get(path):
    return httpx.get(f"{APP}{path}", timeout=30).json()


print("=" * 64)
print("CONFERÊNCIA COMPLETA — Dashboard x API do RD Station")
print("=" * 64)

# 1) Descobrir os user_id dos ex-funcionários
usuarios = httpx.get(f"{BASE}/users", params={"token": TOKEN}, timeout=40).json().get("users", [])
ex_ids = {u.get("id") or u.get("_id"): u.get("name") for u in usuarios if eh_ex_funcionario(u.get("name", ""))}
print(f"\nEx-funcionários identificados: {list(ex_ids.values())}")

# 2) Totais oficiais (API) e quanto pertence aos ex-funcionários
total_api = api_total({})
ganhas_api = api_total({"win": "true"})
perdidas_api = api_total({"win": "false"})

ex_total = ex_ganhas = ex_perdidas = 0
for uid in ex_ids:
    ex_total += api_total({"user_id": uid})
    ex_ganhas += api_total({"user_id": uid, "win": "true"})
    ex_perdidas += api_total({"user_id": uid, "win": "false"})

esp_total = total_api - ex_total
esp_ganhas = ganhas_api - ex_ganhas
esp_perdidas = perdidas_api - ex_perdidas
esp_abertas = esp_total - esp_ganhas - esp_perdidas

print(f"\nAPI (conta toda):      total={total_api}  ganhas={ganhas_api}  perdidas={perdidas_api}")
print(f"Dos ex-funcionários:   total={ex_total}  ganhas={ex_ganhas}  perdidas={ex_perdidas}")
print(f"ESPERADO no dashboard: total={esp_total}  ganhas={esp_ganhas}  perdidas={esp_perdidas}  abertas={esp_abertas}")

# 3) O que o dashboard REALMENTE mostra
home = app_get("/api/home")["resumo"]
rel = app_get("/api/relatorios")
print(f"\nDASHBOARD mostra:      total={home['total_negociacoes']}  ganhas(rel)={rel['geral']['ganhas']}  "
      f"perdidas(rel)={rel['geral']['perdidas']}  abertas={home['abertas']}")

# 4) Comparações
def chk(nome, esperado, real):
    s = "OK ✅" if esperado == real else f"DIVERGE ❌ (esperado {esperado}, dashboard {real})"
    print(f"  - {nome:<22} {s}")

print("\nRESULTADO DA CONFERÊNCIA:")
chk("Total negociações", esp_total, home["total_negociacoes"])
chk("Ganhas", esp_ganhas, rel["geral"]["ganhas"])
chk("Perdidas", esp_perdidas, rel["geral"]["perdidas"])
chk("Em aberto", esp_abertas, home["abertas"])

# 5) Consistência interna (soma das etapas = abertas; soma vendedores = abertas)
soma_etapas = sum(e["quantidade"] for e in rel["por_etapa"])
soma_vend_abertas = sum(v["abertas"] for v in rel["por_vendedor"])
print("\nCONSISTÊNCIA INTERNA:")
chk("Σ etapas = abertas", home["abertas"], soma_etapas)
chk("Σ vendedores = abertas", home["abertas"], soma_vend_abertas)

# 6) Nenhum ex-funcionário aparece em lugar nenhum
nomes_rel = {v["vendedor"] for v in rel["por_vendedor"]}
nomes_top = {v["vendedor"] for v in home_top} if (home_top := app_get("/api/home").get("top_vendedores")) else set()
op = app_get("/api/oportunidades")
atv = app_get("/api/atividades?limite=1")
vazou = [n for n in (nomes_rel | nomes_top | set(op["vendedores"]) | set(atv["vendedores"])) if eh_ex_funcionario(n)]
print("\nLIMPEZA DE EX-FUNCIONÁRIOS:")
print(f"  - Nenhum ex-funcionário visível: {'OK ✅' if not vazou else 'FALHOU ❌ ' + str(vazou)}")

print("\n" + "=" * 64)
