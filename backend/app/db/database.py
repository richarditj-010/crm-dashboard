"""Conexão com o banco de dados (SQLite na Fase 1)."""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import DATA_DIR, DB_PATH

# Garante que a pasta "data" existe
DATA_DIR.mkdir(parents=True, exist_ok=True)

# SQLite local. check_same_thread=False permite uso pelo servidor web.
engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def init_db():
    """Cria as tabelas (as 'gavetas') se ainda não existirem."""
    from app.db import models  # noqa: F401  (garante que os modelos sejam registrados)
    Base.metadata.create_all(bind=engine)
