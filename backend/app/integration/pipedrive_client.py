"""
Cliente da API do Pipedrive (CRM atual da Hai Logistics desde 07/2026).

Substitui o antigo rd_client.py (RD Station). A responsabilidade é a mesma:
conversar com o CRM, tratar a paginação e o limite de requisições (429).
Quem transforma esses dados nas "gavetas" do banco é o sync.py.
"""
import time

import httpx

from app.config import PIPEDRIVE_BASE_URL, PIPEDRIVE_TOKEN


class Pipedrive:
    def __init__(self, token: str = PIPEDRIVE_TOKEN, base_url: str = PIPEDRIVE_BASE_URL):
        self.token = token
        self.base_url = base_url.rstrip("/")

    def _get(self, endpoint: str, params: dict | None = None, tentativas: int = 3) -> dict:
        """Faz uma chamada GET. No Pipedrive o token vai como parâmetro `api_token`."""
        params = {"api_token": self.token, **(params or {})}
        url = f"{self.base_url}/{endpoint}"
        for tentativa in range(1, tentativas + 1):
            resp = httpx.get(url, params=params, timeout=40)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 429:
                # Limite de requisições: espera um pouco e tenta de novo.
                time.sleep(5 * tentativa)
                continue
            resp.raise_for_status()
        raise RuntimeError(f"Falha ao chamar {endpoint} após {tentativas} tentativas (limite de requisições).")

    def _get_paginado(self, endpoint: str, params: dict | None = None,
                      limite: int = 500, max_paginas: int = 200) -> list[dict]:
        """Puxa TODOS os itens de um endpoint, seguindo a paginação do Pipedrive
        (que usa `start`/`limit` e informa em additional_data.pagination se há mais)."""
        todos: list[dict] = []
        start = 0
        for _ in range(max_paginas):
            data = self._get(endpoint, {**(params or {}), "start": start, "limit": limite})
            lote = data.get("data") or []
            todos.extend(lote)
            pag = (data.get("additional_data") or {}).get("pagination") or {}
            if pag.get("more_items_in_collection"):
                start = pag.get("next_start")
            else:
                break
        return todos

    # ---- Recursos ----
    def listar_usuarios(self) -> list[dict]:
        """Vendedores/usuários da conta."""
        return self._get("users").get("data") or []

    def listar_etapas(self) -> list[dict]:
        """Etapas de todos os funis (cada uma traz pipeline_id e order_nr)."""
        return self._get("stages").get("data") or []

    def listar_funis(self) -> list[dict]:
        """Funis (pipelines) — TLD, Despacho, Exportação, Importação."""
        return self._get("pipelines").get("data") or []

    def listar_negociacoes(self) -> list[dict]:
        """TODAS as negociações não excluídas (abertas + ganhas + perdidas).
        O padrão do endpoint /deals já é `all_not_deleted`, então a lixeira
        (negociações deletadas) fica de fora automaticamente."""
        return self._get_paginado("deals")

    def listar_atividades(self) -> list[dict]:
        """Atividades (linha do tempo) de TODOS os vendedores.
        IMPORTANTE: `user_id=0` é o que faz o Pipedrive devolver as atividades de
        toda a equipe (sem isso, ele só devolveria as do dono do token)."""
        return self._get_paginado("activities", {"user_id": 0})
