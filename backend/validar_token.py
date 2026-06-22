"""
Etapa 2 - Validação do token do RD Station CRM.

Este script NÃO faz parte do sistema final. Ele apenas testa se o token
configurado no arquivo .env consegue se conectar à API do RD Station CRM
e enxergar dados reais (negociações, usuários, atividades).

Como rodar:
    .venv\\Scripts\\python.exe backend\\validar_token.py
"""

import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv
import os

# Garante que o terminal do Windows mostre acentos/símbolos sem quebrar
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# Carrega o .env que está na raiz do projeto (pasta "crm dashboard")
RAIZ = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ / ".env")

TOKEN = os.getenv("RD_CRM_TOKEN", "").strip()
BASE_URL = os.getenv("RD_CRM_BASE_URL", "https://crm.rdstation.com/api/v1").strip()


def linha():
    print("-" * 60)


def checar(endpoint: str, params: dict, descricao: str):
    """Faz uma chamada GET e retorna (ok, dados) com mensagens amigáveis."""
    params = {"token": TOKEN, **params}
    url = f"{BASE_URL}/{endpoint}"
    try:
        resp = httpx.get(url, params=params, timeout=30)
    except Exception as e:
        print(f"[ERRO DE CONEXÃO] {descricao}: {e}")
        return False, None

    if resp.status_code == 200:
        return True, resp.json()
    elif resp.status_code == 401:
        print(f"[TOKEN INVÁLIDO] {descricao}: o RD Station recusou o token (401).")
        return False, None
    elif resp.status_code == 429:
        print(f"[LIMITE DE REQUISIÇÕES] {descricao}: muitas chamadas (429). Aguarde e tente de novo.")
        return False, None
    else:
        print(f"[FALHA {resp.status_code}] {descricao}: {resp.text[:200]}")
        return False, None


def main():
    print("\n=== VALIDAÇÃO DO TOKEN - RD STATION CRM ===\n")

    if not TOKEN or TOKEN.startswith("cole_aqui"):
        print("Nenhum token configurado no arquivo .env (campo RD_CRM_TOKEN). Pare e configure primeiro.")
        sys.exit(1)

    print(f"Token (parcial): {TOKEN[:6]}...{TOKEN[-4:]}")
    print(f"Base URL: {BASE_URL}")
    linha()

    # 1) Negociações
    ok_deals, deals = checar("deals", {"limit": 1}, "Negociações")
    if ok_deals:
        total = deals.get("total") if isinstance(deals, dict) else None
        print(f"[OK] Negociações acessíveis. Total na conta: {total}")
        amostra = (deals.get("deals") or []) if isinstance(deals, dict) else []
        if amostra:
            d = amostra[0]
            print(f"     Exemplo de negociação: '{d.get('name')}' | etapa: "
                  f"{(d.get('deal_stage') or {}).get('name')}")

    # 2) Usuários (equipe de vendas)
    ok_users, users = checar("users", {}, "Usuários/Equipe")
    if ok_users:
        lista = users.get("users") if isinstance(users, dict) else users
        lista = lista or []
        print(f"[OK] Equipe acessível. {len(lista)} usuário(s) encontrados:")
        for u in lista[:10]:
            print(f"     - {u.get('name')} ({u.get('email')})")

    # 3) Funis / etapas
    ok_stages, stages = checar("deal_stages", {}, "Etapas do funil")
    if ok_stages:
        lista = stages.get("deal_stages") if isinstance(stages, dict) else stages
        lista = lista or []
        print(f"[OK] Funil acessível. {len(lista)} etapa(s):")
        for s in lista[:15]:
            print(f"     - {s.get('name')}")

    linha()
    if ok_deals or ok_users or ok_stages:
        print("RESULTADO: TOKEN VÁLIDO! Conseguimos ler dados reais do CRM. ✅")
    else:
        print("RESULTADO: não foi possível ler nenhum dado. Verifique o token. ❌")
    print()


if __name__ == "__main__":
    main()
