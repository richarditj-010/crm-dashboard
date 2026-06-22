"""
Cliente da API do RD Station CRM.
Responsável por conversar com o CRM, tratar paginação e limite de requisições (429).
"""
import time

import httpx

from app.config import RD_CRM_BASE_URL, RD_CRM_TOKEN


class RDStationCRM:
    def __init__(self, token: str = RD_CRM_TOKEN, base_url: str = RD_CRM_BASE_URL):
        self.token = token
        self.base_url = base_url.rstrip("/")

    def _get(self, endpoint: str, params: dict | None = None, tentativas: int = 3) -> dict:
        params = {"token": self.token, **(params or {})}
        url = f"{self.base_url}/{endpoint}"
        for tentativa in range(1, tentativas + 1):
            resp = httpx.get(url, params=params, timeout=40)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 429:
                # Limite de requisições: espera um pouco e tenta de novo
                espera = 5 * tentativa
                time.sleep(espera)
                continue
            resp.raise_for_status()
        raise RuntimeError(f"Falha ao chamar {endpoint} após {tentativas} tentativas (limite de requisições).")

    # ---- Recursos ----
    def listar_usuarios(self) -> list[dict]:
        data = self._get("users")
        return data.get("users", data if isinstance(data, list) else [])

    def listar_etapas(self) -> list[dict]:
        data = self._get("deal_stages")
        return data.get("deal_stages", data if isinstance(data, list) else [])

    def listar_negociacoes(self, limite_por_pagina: int = 200, max_paginas: int = 50) -> list[dict]:
        """Puxa TODAS as negociações, paginando até acabar."""
        todas: list[dict] = []
        pagina = 1
        while pagina <= max_paginas:
            # Ordem estável (mais antigas primeiro): evita que registros "escapem"
            # da paginação quando novas negociações são criadas durante a sincronização.
            data = self._get("deals", {
                "limit": limite_por_pagina,
                "page": pagina,
                "order": "created_at",
                "direction": "asc",
            })
            lote = data.get("deals", [])
            todas.extend(lote)
            if not data.get("has_more") or not lote:
                break
            pagina += 1
        return todas

    def listar_atividades(self, limite_por_pagina: int = 200, max_paginas: int = 60) -> list[dict]:
        """Puxa as atividades (linha do tempo), paginando até acabar."""
        todas: list[dict] = []
        pagina = 1
        while pagina <= max_paginas:
            data = self._get("activities", {"limit": limite_por_pagina, "page": pagina})
            lote = data.get("activities", [])
            todas.extend(lote)
            if not data.get("has_more") or not lote:
                break
            pagina += 1
        return todas
