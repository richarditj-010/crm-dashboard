"""
Modelos do banco (as 'gavetas' onde os dados do CRM ficam guardados).
Fase 1 - foco no necessário para o dashboard Home.
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class User(Base):
    """Vendedor / usuário da equipe."""
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, default="")
    email: Mapped[str] = mapped_column(String, default="")
    nickname: Mapped[str] = mapped_column(String, default="")


class DealStage(Base):
    """Etapa do funil de vendas."""
    __tablename__ = "deal_stages"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, default="")
    nickname: Mapped[str] = mapped_column(String, default="")
    order: Mapped[int] = mapped_column(Integer, default=0)


class Deal(Base):
    """Negociação (oportunidade) do CRM."""
    __tablename__ = "deals"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, default="")

    amount_total: Mapped[float] = mapped_column(Float, default=0.0)
    amount_unique: Mapped[float] = mapped_column(Float, default=0.0)
    amount_monthly: Mapped[float] = mapped_column(Float, default=0.0)

    # win: None = aberta, True = ganha, False = perdida
    win: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    hold: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    rating: Mapped[int] = mapped_column(Integer, default=0)
    interactions: Mapped[int] = mapped_column(Integer, default=0)

    stage_id: Mapped[str] = mapped_column(String, default="")
    stage_name: Mapped[str] = mapped_column(String, default="")
    user_id: Mapped[str] = mapped_column(String, default="")
    user_name: Mapped[str] = mapped_column(String, default="")
    organization_name: Mapped[str] = mapped_column(String, default="")

    # Datas guardadas como texto ISO (simples e suficiente na Fase 1)
    created_at: Mapped[str] = mapped_column(String, default="")
    updated_at: Mapped[str] = mapped_column(String, default="")
    closed_at: Mapped[str] = mapped_column(String, default="")
    prediction_date: Mapped[str] = mapped_column(String, default="")
    last_activity_at: Mapped[str] = mapped_column(String, default="")
    last_activity_markup: Mapped[str] = mapped_column(String, default="")
    last_activity_content: Mapped[str] = mapped_column(String, default="")


class Activity(Base):
    """Atividade do CRM (anotação, e-mail, etc.) — linha do tempo."""
    __tablename__ = "activities"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, default="")
    user_name: Mapped[str] = mapped_column(String, default="")
    deal_id: Mapped[str] = mapped_column(String, default="")
    text: Mapped[str] = mapped_column(String, default="")
    date: Mapped[str] = mapped_column(String, default="")  # ISO


class SyncLog(Base):
    """Registro de cada sincronização (para mostrar 'última atualização')."""
    __tablename__ = "sync_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    finished_at: Mapped[datetime] = mapped_column(DateTime)
    deals_count: Mapped[int] = mapped_column(Integer, default=0)
    users_count: Mapped[int] = mapped_column(Integer, default=0)
    stages_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String, default="ok")
    message: Mapped[str] = mapped_column(String, default="")
