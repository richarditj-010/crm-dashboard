"""
Sincronização: puxa os dados do RD Station CRM e grava no SQLite local.
O dashboard sempre lê do SQLite (rápido e sem estourar o limite da API).
"""
from datetime import datetime, timezone, timedelta

from app.db.database import SessionLocal
from app.db.models import User, DealStage, Deal, Activity, SyncLog
from app.integration.rd_client import RDStationCRM

# Fuso de Brasília (UTC-3), só para registrar o horário da sincronização
FUSO_BR = timezone(timedelta(hours=-3))


def _num(v) -> float:
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def sincronizar() -> dict:
    """Executa uma sincronização completa. Retorna um resumo."""
    crm = RDStationCRM()
    db = SessionLocal()
    try:
        usuarios = crm.listar_usuarios()
        etapas = crm.listar_etapas()
        negociacoes = crm.listar_negociacoes()
        atividades = crm.listar_atividades()

        # mapa user_id -> nome (para enriquecer as atividades)
        nome_por_user = {str(u.get("id") or u.get("_id")): (u.get("name") or "") for u in usuarios}

        # --- Usuários ---
        db.query(User).delete()
        for u in usuarios:
            db.add(User(
                id=str(u.get("id") or u.get("_id")),
                name=u.get("name") or "",
                email=u.get("email") or "",
                nickname=u.get("nickname") or "",
            ))

        # --- Etapas do funil (mantém a ordem retornada) ---
        db.query(DealStage).delete()
        for ordem, s in enumerate(etapas):
            db.add(DealStage(
                id=str(s.get("id") or s.get("_id")),
                name=s.get("name") or "",
                nickname=s.get("nickname") or "",
                order=ordem,
            ))

        # --- Negociações ---
        db.query(Deal).delete()
        for d in negociacoes:
            stage = d.get("deal_stage") or {}
            user = d.get("user") or {}
            org = d.get("organization") or {}
            db.add(Deal(
                id=str(d.get("id") or d.get("_id")),
                name=d.get("name") or "",
                amount_total=_num(d.get("amount_total")),
                amount_unique=_num(d.get("amount_unique")),
                amount_monthly=_num(d.get("amount_montly")),  # nome com 'typo' vem assim da API
                win=d.get("win"),
                hold=d.get("hold"),
                rating=int(d.get("rating") or 0),
                interactions=int(d.get("interactions") or 0),
                stage_id=str(stage.get("id") or stage.get("_id") or ""),
                stage_name=stage.get("name") or "",
                user_id=str(user.get("id") or user.get("_id") or ""),
                user_name=user.get("name") or "",
                organization_name=org.get("name") or "",
                created_at=d.get("created_at") or "",
                updated_at=d.get("updated_at") or "",
                closed_at=d.get("closed_at") or "",
                prediction_date=d.get("prediction_date") or "",
                last_activity_at=d.get("last_activity_at") or "",
                last_activity_markup=d.get("markup_last_activities") or "",
                last_activity_content=d.get("last_activity_content") or "",
            ))

        # --- Atividades (linha do tempo) ---
        db.query(Activity).delete()
        for a in atividades:
            uid = str(a.get("user_id") or "")
            texto = (a.get("text") or "").strip()
            db.add(Activity(
                id=str(a.get("id") or a.get("_id")),
                user_id=uid,
                user_name=nome_por_user.get(uid, ""),
                deal_id=str(a.get("deal_id") or ""),
                text=texto[:1000],
                date=a.get("date") or "",
            ))

        log = SyncLog(
            finished_at=datetime.now(FUSO_BR).replace(tzinfo=None),
            deals_count=len(negociacoes),
            users_count=len(usuarios),
            stages_count=len(etapas),
            status="ok",
            message="Sincronização concluída.",
        )
        db.add(log)
        db.commit()

        return {
            "status": "ok",
            "deals": len(negociacoes),
            "users": len(usuarios),
            "stages": len(etapas),
        }
    except Exception as e:
        db.rollback()
        db.add(SyncLog(
            finished_at=datetime.now(FUSO_BR).replace(tzinfo=None),
            status="erro",
            message=str(e)[:300],
        ))
        db.commit()
        raise
    finally:
        db.close()
