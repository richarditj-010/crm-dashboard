"""Configurações centrais do projeto (lê o arquivo .env uma única vez)."""
from pathlib import Path
import os

from dotenv import load_dotenv

# Raiz do projeto = pasta "crm dashboard"
#  config.py -> app -> backend -> (raiz)
RAIZ = Path(__file__).resolve().parents[2]

load_dotenv(RAIZ / ".env")

RD_CRM_TOKEN = os.getenv("RD_CRM_TOKEN", "").strip()
RD_CRM_BASE_URL = os.getenv("RD_CRM_BASE_URL", "https://crm.rdstation.com/api/v1").strip()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()

# Senha de acesso ao painel (proteção na nuvem).
# Se PAINEL_SENHA estiver vazio (uso local), o painel abre sem pedir senha.
# Na nuvem (Render), defina PAINEL_SENHA para exigir login (usuário + senha).
PAINEL_USUARIO = os.getenv("PAINEL_USUARIO", "hai").strip()
PAINEL_SENHA = os.getenv("PAINEL_SENHA", "").strip()

APP_HOST = os.getenv("APP_HOST", "127.0.0.1").strip()
APP_PORT = int(os.getenv("APP_PORT", "8000"))

# Ex-funcionários (não aparecem como vendedores ativos nos rankings/filtros/relatórios).
# Para incluir/remover alguém no futuro, basta editar esta lista (nome como aparece no CRM).
EX_FUNCIONARIOS = [
    "Alexandre Rosa",
    "Flaviane Miguel",
    "Sandrei Neves",
    "Barbara Pereira",
    "Pollyana Juttel",
    "Alex Saner",
    "Benjamin Lechuga",
    "Fabrício",
    "Fernando Peirão",
    "Rodrigo",
    "Maycon",
]


def _normaliza(s: str) -> str:
    """Tira espaços extras e maiúsculas — os nomes vêm do CRM com espaços inconsistentes."""
    return " ".join((s or "").lower().split())


def eh_ex_funcionario(nome: str) -> bool:
    """Verifica se um nome está na lista de ex-funcionários (ignora maiúsculas e espaços extras)."""
    alvo = _normaliza(nome)
    return any(_normaliza(ex) == alvo or alvo.startswith(_normaliza(ex)) for ex in EX_FUNCIONARIOS)


# Cargo de cada vendedor (para organizar o painel por função).
# Para editar no futuro, basta mudar aqui (o nome pode ter espaço a mais, é ignorado).
CARGOS = {
    "Krysthopher Scheidemantel": "Inside Sales",
    "Eloiza Chalub": "Inside Sales",
    "Daiane Cristina Pereira": "SDR / Prospecção",
    "Camila Peres": "Vendedora",
    "Simeão Batista": "Coordenador / Vendedor",
}
_CARGOS_NORM = {_normaliza(k): v for k, v in CARGOS.items()}


def cargo_de(nome: str) -> str:
    """Retorna o cargo do vendedor (ou 'Outros' se não estiver cadastrado)."""
    return _CARGOS_NORM.get(_normaliza(nome), "Outros")


# Pastas
DATA_DIR = RAIZ / "data"
FRONTEND_DIR = RAIZ / "frontend"
DB_PATH = DATA_DIR / "crm.db"
