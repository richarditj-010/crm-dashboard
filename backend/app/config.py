"""Configurações centrais do projeto (lê o arquivo .env uma única vez)."""
from pathlib import Path
import os

from dotenv import load_dotenv

# Raiz do projeto = pasta "crm dashboard"
#  config.py -> app -> backend -> (raiz)
RAIZ = Path(__file__).resolve().parents[2]

load_dotenv(RAIZ / ".env")

# --- Pipedrive (CRM ATUAL desde 07/2026) ---
PIPEDRIVE_TOKEN = os.getenv("PIPEDRIVE_TOKEN", "").strip()
PIPEDRIVE_BASE_URL = os.getenv("PIPEDRIVE_BASE_URL", "https://api.pipedrive.com/v1").strip()

# --- RD Station CRM (ANTIGO — mantido só como referência/backup, não usa mais) ---
RD_CRM_TOKEN = os.getenv("RD_CRM_TOKEN", "").strip()
RD_CRM_BASE_URL = os.getenv("RD_CRM_BASE_URL", "https://crm.rdstation.com/api/v1").strip()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()

# Senha de acesso ao painel.
# Ao abrir o painel, aparece uma telinha pedindo só a senha (sem usuário).
# A senha padrão é "BOSS" (igual à da nuvem). Para trocar, é só definir PAINEL_SENHA no .env.
# Se quiser DESLIGAR o login (abrir direto, sem pedir nada), deixe PAINEL_SENHA vazio no .env.
PAINEL_SENHA = os.getenv("PAINEL_SENHA", "BOSS").strip()

APP_HOST = os.getenv("APP_HOST", "127.0.0.1").strip()
APP_PORT = int(os.getenv("APP_PORT", "8000"))

# --- Envio do relatório por email ---
# Servidor de saída (Gmail por padrão — o M365 não aceita mais envio simples por SMTP).
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
# Conta que ENVIA o email e sua "senha de aplicativo" (preencher no .env).
SMTP_USER = os.getenv("SMTP_USER", "").strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").strip()
# De quem o email aparece como remetente (padrão: a própria conta de envio).
SMTP_FROM = os.getenv("SMTP_FROM", "").strip() or SMTP_USER
# Para quem vai o relatório (pode ter vários, separados por vírgula).
RELATORIO_EMAIL_TO = os.getenv("RELATORIO_EMAIL_TO", "richard@hailogistics.com.br").strip()
# Chave secreta que o "despertador" externo (cron) usa para disparar o envio semanal.
RELATORIO_CRON_CHAVE = os.getenv("RELATORIO_CRON_CHAVE", "").strip()

# Ex-funcionários (não aparecem como vendedores ativos nos rankings/filtros/relatórios).
# Para OCULTAR alguém no futuro, basta adicionar o nome aqui (como aparece no Pipedrive).
#
# 07/2026 — Migração para o Pipedrive: a equipe agora é outra e o Richard optou por
# MANTER todos os usuários atuais visíveis. Por isso a lista está vazia.
# (A lista antiga era do RD Station — inclusive um "Fabrício", que NÃO é o atual
#  "Fabrício Sant'Anna"; por isso foi removida, para não escondê-lo por engano.)
EX_FUNCIONARIOS: list[str] = []


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
    "Simeão Aureo Batista Filho": "Coordenador / Vendedor",
    "Jeisson Gelasio": "Vendedor",
    "Amanda": "Vendedora",
    "Fabrício Sant'Anna": "Vendedor",
    "Natalia Otero": "Vendedora",
}
_CARGOS_NORM = {_normaliza(k): v for k, v in CARGOS.items()}


def cargo_de(nome: str) -> str:
    """Retorna o cargo do vendedor (ou 'Outros' se não estiver cadastrado)."""
    return _CARGOS_NORM.get(_normaliza(nome), "Outros")


# Pastas
DATA_DIR = RAIZ / "data"
FRONTEND_DIR = RAIZ / "frontend"
DB_PATH = DATA_DIR / "crm.db"
