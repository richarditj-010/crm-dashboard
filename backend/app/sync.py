"""
Sincronização: puxa os dados do Pipedrive e grava no SQLite local.
O dashboard sempre lê do SQLite (rápido e sem estourar o limite da API).

Este arquivo é a ÚNICA peça que conhece o "formato" do Pipedrive: ele traduz
os campos do Pipedrive para as mesmas "gavetas" (tabelas) que o painel já usava.
Assim, telas, relatórios e email continuam funcionando sem mudança nenhuma.
(Antes esta sincronização lia do RD Station — ver histórico no git.)
"""
from datetime import datetime, timezone, timedelta

from app.db.database import SessionLocal
from app.db.models import User, DealStage, Deal, Activity, SyncLog
from app.integration.pipedrive_client import Pipedrive

# Fuso de Brasília (UTC-3), só para registrar o horário da sincronização
FUSO_BR = timezone(timedelta(hours=-3))


def _num(v) -> float:
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def _texto(v) -> str:
    """Datas/valores do Pipedrive podem vir como None — devolve sempre texto."""
    return "" if v is None else str(v)


def _id_e_nome(campo, nome_fallback: str = ""):
    """No Pipedrive, campos como user_id/org_id às vezes vêm como um objeto
    {id, name, ...} e às vezes como um número simples. Trata os dois casos."""
    if isinstance(campo, dict):
        return _texto(campo.get("id") or campo.get("value")), (campo.get("name") or nome_fallback or "")
    if campo in (None, ""):
        return "", nome_fallback or ""
    return _texto(campo), nome_fallback or ""


def _texto_atividade(a: dict) -> str:
    """Monta um texto legível da atividade: 'Tipo — Assunto' (ou a anotação)."""
    partes = []
    tipo = (a.get("type_name") or "").strip()
    assunto = (a.get("subject") or "").strip()
    if tipo:
        partes.append(tipo)
    if assunto:
        partes.append(assunto)
    texto = " — ".join(partes)
    if not texto:
        texto = (a.get("note") or "").strip()
    return texto


def _data_atividade(a: dict) -> str:
    """Data de referência da atividade para a linha do tempo:
    quando concluída, usa a hora de conclusão; senão, a data agendada; senão, a criação."""
    if a.get("marked_as_done_time"):
        return _texto(a.get("marked_as_done_time"))
    if a.get("due_date"):
        return (_texto(a.get("due_date")) + " " + _texto(a.get("due_time"))).strip()
    return _texto(a.get("add_time"))


def sincronizar() -> dict:
    """Executa uma sincronização completa. Retorna um resumo."""
    pd = Pipedrive()
    db = SessionLocal()
    try:
        usuarios = pd.listar_usuarios()
        etapas = pd.listar_etapas()
        negociacoes = pd.listar_negociacoes()
        atividades = pd.listar_atividades()

        # mapa etapa_id -> nome (a negociação do Pipedrive só traz o id da etapa)
        nome_etapa = {str(s.get("id")): (s.get("name") or "") for s in etapas}
        # mapa user_id -> nome (para enriquecer as atividades)
        nome_por_user = {str(u.get("id")): (u.get("name") or "") for u in usuarios}
        # data de hoje (Brasília) para marcar "atividade hoje"
        hoje = datetime.now(FUSO_BR).strftime("%Y-%m-%d")

        # --- Usuários (vendedores) ---
        db.query(User).delete()
        for u in usuarios:
            db.add(User(
                id=str(u.get("id")),
                name=u.get("name") or "",
                email=u.get("email") or "",
                nickname="",
            ))

        # --- Etapas do funil ---
        # O Pipedrive tem 4 funis com as MESMAS 6 etapas. O painel agrupa por NOME
        # (junta os funis), então usamos `order_nr` (0..5) como ordem de exibição.
        db.query(DealStage).delete()
        for s in etapas:
            db.add(DealStage(
                id=str(s.get("id")),
                name=s.get("name") or "",
                nickname="",
                order=int(s.get("order_nr") or 0),
            ))

        # --- Negociações ---
        db.query(Deal).delete()
        for d in negociacoes:
            status = d.get("status")  # open / won / lost
            win = True if status == "won" else (False if status == "lost" else None)

            uid, uname = _id_e_nome(d.get("user_id"), d.get("owner_name") or "")
            stage_id = str(d.get("stage_id") or "")
            ultima_ativ = _texto(d.get("last_activity_date"))

            # Data de fechamento: usa o que existir (fechamento / ganho / perda).
            closed_at = _texto(d.get("close_time") or d.get("won_time") or d.get("lost_time"))

            db.add(Deal(
                id=str(d.get("id")),
                name=d.get("title") or "",
                amount_total=_num(d.get("value")),
                amount_unique=0.0,   # Pipedrive tem um único campo de valor
                amount_monthly=0.0,
                win=win,
                hold=bool(d.get("is_archived")) or None,
                rating=0,
                interactions=int(d.get("activities_count") or 0),
                stage_id=stage_id,
                stage_name=nome_etapa.get(stage_id, ""),
                user_id=uid,
                user_name=uname or d.get("owner_name") or "",
                organization_name=d.get("org_name") or "",
                created_at=_texto(d.get("add_time")),
                updated_at=_texto(d.get("update_time")),
                closed_at=closed_at,
                prediction_date=_texto(d.get("expected_close_date")),
                last_activity_at=ultima_ativ,
                # o painel conta "atividades hoje" olhando este marcador == "today"
                last_activity_markup=("today" if ultima_ativ[:10] == hoje else ""),
                last_activity_content="",
            ))

        # --- Atividades (linha do tempo) ---
        db.query(Activity).delete()
        for a in atividades:
            uid = str(a.get("user_id") or "")
            db.add(Activity(
                id=str(a.get("id")),
                user_id=uid,
                user_name=nome_por_user.get(uid, a.get("owner_name") or ""),
                deal_id=str(a.get("deal_id") or ""),
                text=_texto_atividade(a)[:1000],
                date=_data_atividade(a),
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
