"""
Backend FastAPI do CRM Dashboard.
- Serve a página do dashboard (frontend)
- Expõe endpoints internos que entregam os dados já tratados (do SQLite)
"""
import hashlib
import secrets
import threading
import time as _time
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta, date

from urllib.parse import parse_qs

from fastapi import FastAPI, Body, Request
from fastapi.responses import (
    FileResponse, PlainTextResponse, Response, RedirectResponse, HTMLResponse,
)
from fastapi.staticfiles import StaticFiles

from app.config import (
    FRONTEND_DIR, ANTHROPIC_API_KEY, eh_ex_funcionario, cargo_de, _normaliza,
    PAINEL_SENHA,
)
from app.db.database import init_db, SessionLocal
from app.db.models import Deal, User, DealStage, Activity, SyncLog
from app.sync import sincronizar

FUSO_BR = timezone(timedelta(hours=-3))


# De quanto em quanto tempo o painel busca dados novos do RD Station (em minutos).
SYNC_INTERVALO_MIN = 30


def _loop_sync(pular_primeira: bool):
    """Roda em segundo plano: mantém o banco sempre atualizado com o RD Station."""
    if not pular_primeira:
        # Ao abrir o painel, já busca dados frescos (sem travar a tela).
        try:
            sincronizar()
            print("[sync] atualização ao abrir concluída")
        except Exception as e:
            print(f"[sync] falhou ao abrir: {e}")
    while True:
        _time.sleep(SYNC_INTERVALO_MIN * 60)
        try:
            sincronizar()
            print("[sync] atualização automática concluída")
        except Exception as e:
            print(f"[sync] falha na atualização automática: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ao subir o servidor: cria as tabelas.
    init_db()
    # IMPORTANTE (nuvem/Render): a sincronização roda SEMPRE em segundo plano, para o
    # servidor "abrir a porta" na hora e não estourar o tempo de espera do Render.
    # O _loop_sync(False) faz a primeira busca já agora (em segundo plano) e depois
    # repete a cada SYNC_INTERVALO_MIN minutos.
    threading.Thread(target=_loop_sync, args=(False,), daemon=True).start()
    yield


app = FastAPI(title="CRM Dashboard - Hai Logistics", lifespan=lifespan)


# --- Login simples por senha (tela própria, sem campo de usuário) ---
# Ao abrir o painel aparece uma telinha pedindo só a senha. Acertou -> entra e fica
# logado (um "selo" guardado no navegador por 30 dias). A senha vem do config (.env);
# se PAINEL_SENHA estiver vazia, o painel abre direto, sem pedir nada.
COOKIE_LOGIN = "crm_auth"
# "Selo" guardado no navegador quando a senha está certa. É derivado da senha, então
# trocar a senha invalida os acessos antigos automaticamente (e sobrevive a reinícios).
SELO_LOGIN = hashlib.sha256(f"crm-hai::{PAINEL_SENHA}".encode("utf-8")).hexdigest()


def _logado(request) -> bool:
    """True se o navegador já tem o selo de login válido."""
    return secrets.compare_digest(request.cookies.get(COOKIE_LOGIN, ""), SELO_LOGIN)


def _pagina_login(erro: bool = False) -> HTMLResponse:
    """A telinha de login: só uma caixa de senha + botão Entrar."""
    aviso = '<p class="erro">Senha incorreta. Tente de novo.</p>' if erro else ""
    html = f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Entrar — CRM Dashboard</title>
<style>
  *{{box-sizing:border-box}} body{{margin:0;font-family:Segoe UI,Arial,sans-serif;
    background:#0f2540;display:flex;align-items:center;justify-content:center;min-height:100vh}}
  .cartao{{background:#fff;padding:36px 32px;border-radius:14px;box-shadow:0 10px 40px rgba(0,0,0,.3);
    width:340px;text-align:center}}
  .logo{{font-size:42px}} h1{{font-size:20px;margin:8px 0 2px;color:#0f2540}}
  small{{color:#6b7a90}} form{{margin-top:22px}}
  input{{width:100%;padding:13px 14px;font-size:16px;border:2px solid #cdd7e3;border-radius:9px;
    outline:none}} input:focus{{border-color:#1565c0}}
  button{{width:100%;margin-top:12px;padding:13px;font-size:16px;font-weight:600;color:#fff;
    background:#1565c0;border:0;border-radius:9px;cursor:pointer}} button:hover{{background:#0d47a1}}
  .erro{{color:#c62828;font-size:14px;margin:14px 0 0}}
</style></head>
<body>
  <div class="cartao">
    <div class="logo">📊</div>
    <h1>CRM Dashboard</h1>
    <small>Hai Logistics</small>
    {aviso}
    <form method="post" action="/login">
      <input type="password" name="senha" placeholder="Digite a senha" autofocus required />
      <button type="submit">Entrar</button>
    </form>
  </div>
</body></html>"""
    return HTMLResponse(html, status_code=401 if erro else 200)


@app.middleware("http")
async def proteger_com_senha(request, call_next):
    """Exige a senha antes de mostrar o painel (quando PAINEL_SENHA está definida).

    A própria tela de login (/login) é liberada. Quem não estiver logado é mandado
    para ela; chamadas internas de dados (/api/...) respondem 401.
    """
    if not PAINEL_SENHA:
        return await call_next(request)
    caminho = request.url.path
    if caminho == "/login" or _logado(request):
        return await call_next(request)
    if caminho.startswith("/api/"):
        return Response(status_code=401)
    return RedirectResponse("/login")


@app.get("/login")
def login_pagina():
    return _pagina_login()


@app.post("/login")
async def login_enviar(request: Request):
    corpo = (await request.body()).decode("utf-8", "ignore")
    senha = parse_qs(corpo).get("senha", [""])[0]
    if secrets.compare_digest(senha, PAINEL_SENHA):
        resp = RedirectResponse("/", status_code=303)
        resp.set_cookie(
            COOKIE_LOGIN, SELO_LOGIN,
            max_age=60 * 60 * 24 * 30,  # fica logado por 30 dias
            httponly=True, samesite="lax",
        )
        return resp
    return _pagina_login(erro=True)


def _mes_atual() -> str:
    agora = datetime.now(FUSO_BR)
    return f"{agora.year:04d}-{agora.month:02d}"


def _moeda(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _deals_ativos(db):
    """Todas as negociações, EXCLUINDO as de ex-funcionários (limpeza global)."""
    return [d for d in db.query(Deal).all() if not eh_ex_funcionario(d.user_name)]


def _dias_desde(iso: str):
    """Quantos dias se passaram desde uma data ISO (texto). None se não der pra ler."""
    s = (iso or "")[:10]
    if len(s) != 10:
        return None
    try:
        ano, mes, dia = int(s[:4]), int(s[5:7]), int(s[8:10])
        return (datetime.now(FUSO_BR).date() - date(ano, mes, dia)).days
    except Exception:
        return None


def _coletar_metricas(db):
    """Calcula tudo que as 'Perguntas Rápidas' e o 'Relatório Geral' precisam.
    Centraliza a conta para o painel e o relatório baixado ficarem sempre iguais."""
    deals = _deals_ativos(db)
    stages = db.query(DealStage).order_by(DealStage.order).all()
    ordem_etapa = {s.name.strip().lower(): s.order for s in stages}

    abertas = [d for d in deals if d.win is None]
    ganhas = [d for d in deals if d.win is True]
    perdidas = [d for d in deals if d.win is False]
    mes = _mes_atual()
    hoje = datetime.now(FUSO_BR).strftime("%Y-%m-%d")

    # --- Atividades de hoje, por vendedor ---
    atvs = [a for a in db.query(Activity).all() if not eh_ex_funcionario(a.user_name)]
    hoje_por_vend = {}
    for a in atvs:
        if (a.date or "")[:10] == hoje:
            nome = a.user_name or "(sem vendedor)"
            hoje_por_vend[nome] = hoje_por_vend.get(nome, 0) + 1

    # --- Abertas por vendedor (qtd + valor) ---
    ab_vend = {}
    for d in abertas:
        nome = d.user_name or "(sem vendedor)"
        v = ab_vend.setdefault(nome, {"qtd": 0, "valor": 0.0})
        v["qtd"] += 1
        v["valor"] += d.amount_total

    # --- Paradas (abertas sem atividade há X dias). Sem data = consideramos parada. ---
    def paradas_acima(dias_min):
        cont = {}
        for d in abertas:
            dd = _dias_desde(d.last_activity_at)
            if dd is None or dd > dias_min:
                nome = d.user_name or "(sem vendedor)"
                cont[nome] = cont.get(nome, 0) + 1
        return cont
    paradas7 = paradas_acima(7)
    paradas15 = paradas_acima(15)

    # --- Ganhas no mês, por vendedor ---
    ganhas_mes_vend = {}
    for d in ganhas:
        if (d.closed_at or "")[:7] == mes:
            nome = d.user_name or "(sem vendedor)"
            ganhas_mes_vend[nome] = ganhas_mes_vend.get(nome, 0) + 1

    # --- Conversão por vendedor ---
    por_vend = {}
    for d in deals:
        nome = d.user_name or "(sem vendedor)"
        v = por_vend.setdefault(nome, {"abertas": 0, "ganhas": 0, "perdidas": 0})
        if d.win is None:
            v["abertas"] += 1
        elif d.win is True:
            v["ganhas"] += 1
        else:
            v["perdidas"] += 1
    conversao = []
    for nome, v in por_vend.items():
        fechadas = v["ganhas"] + v["perdidas"]
        conv = round(100 * v["ganhas"] / fechadas, 1) if fechadas else 0.0
        conversao.append({"vendedor": nome, "cargo": cargo_de(nome), **v, "conversao": conv})
    conversao.sort(key=lambda x: x["conversao"], reverse=True)

    # --- Equipe agrupada por cargo ---
    cargos_agg = {}
    for nome, v in por_vend.items():
        cg = cargo_de(nome)
        c = cargos_agg.setdefault(cg, {"cargo": cg, "vendedores": 0, "abertas": 0, "ganhas": 0, "perdidas": 0})
        c["vendedores"] += 1
        c["abertas"] += v["abertas"]
        c["ganhas"] += v["ganhas"]
        c["perdidas"] += v["perdidas"]
    por_cargo = sorted(cargos_agg.values(), key=lambda x: x["abertas"], reverse=True)

    # --- Pipeline por etapa (abertas) ---
    agg_e = {}
    for d in abertas:
        nome = " ".join((d.stage_name or "Sem etapa").split())
        a = agg_e.setdefault(nome.lower(), {"etapa": nome, "qtd": 0, "valor": 0.0})
        a["qtd"] += 1
        a["valor"] += d.amount_total
    por_etapa = sorted(agg_e.values(), key=lambda x: (ordem_etapa.get(x["etapa"].lower(), 999), x["etapa"]))

    # --- Top negociações abertas por valor (para o relatório) ---
    top_abertas = sorted(abertas, key=lambda d: d.amount_total, reverse=True)[:15]

    # --- Negociações criadas por mês (para o relatório) ---
    contagem_mes = {}
    for d in deals:
        m = (d.created_at or "")[:7]
        if len(m) == 7:
            contagem_mes[m] = contagem_mes.get(m, 0) + 1
    por_mes = [{"mes": m, "qtd": contagem_mes[m]} for m in sorted(contagem_mes)[-12:]]

    return {
        "gerado_em": datetime.now(FUSO_BR).strftime("%d/%m/%Y %H:%M"),
        "total": len(deals), "abertas": len(abertas),
        "ganhas": len(ganhas), "perdidas": len(perdidas),
        "ganhas_mes": sum(ganhas_mes_vend.values()),
        "pipeline_aberto": sum(d.amount_total for d in abertas),
        "hoje_por_vend": sorted(hoje_por_vend.items(), key=lambda x: x[1], reverse=True),
        "ab_vend": sorted(ab_vend.items(), key=lambda x: x[1]["qtd"], reverse=True),
        "paradas7": sorted(paradas7.items(), key=lambda x: x[1], reverse=True),
        "paradas15": sorted(paradas15.items(), key=lambda x: x[1], reverse=True),
        "ganhas_mes_vend": sorted(ganhas_mes_vend.items(), key=lambda x: x[1], reverse=True),
        "conversao": conversao,
        "por_cargo": por_cargo,
        "por_etapa": por_etapa,
        "top_abertas": top_abertas,
        "por_mes": por_mes,
        "ab_vend_cargo": {nome: cargo_de(nome) for nome, _ in ab_vend.items()},
    }


@app.get("/api/home")
def home():
    """Métricas da tela inicial, calculadas a partir do SQLite."""
    db = SessionLocal()
    try:
        deals = _deals_ativos(db)
        users = db.query(User).all()
        stages = db.query(DealStage).order_by(DealStage.order).all()
        ultimo_sync = db.query(SyncLog).order_by(SyncLog.id.desc()).first()

        abertas = [d for d in deals if d.win is None]
        ganhas = [d for d in deals if d.win is True]
        perdidas = [d for d in deals if d.win is False]

        mes = _mes_atual()
        ganhas_mes = [d for d in ganhas if (d.closed_at or "")[:7] == mes]

        pipeline_total = sum(d.amount_total for d in abertas)
        atividades_hoje = sum(1 for d in deals if d.last_activity_markup == "today")

        # Pipeline por etapa (abertas) — agrupado por NOME (junta todos os funis/pipelines)
        ordem_etapa = {s.name.strip().lower(): s.order for s in stages}
        agg = {}
        for d in abertas:
            nome = " ".join((d.stage_name or "Sem etapa").split())
            a = agg.setdefault(nome.lower(), {"etapa": nome, "quantidade": 0, "valor": 0.0})
            a["quantidade"] += 1
            a["valor"] += d.amount_total
        por_etapa = sorted(agg.values(), key=lambda x: (ordem_etapa.get(x["etapa"].lower(), 999), x["etapa"]))
        for e in por_etapa:
            e["valor_fmt"] = _moeda(e["valor"])

        # Top vendedores por nº de negociações abertas
        contagem = {}
        for d in abertas:
            if d.user_name and not eh_ex_funcionario(d.user_name):
                contagem[d.user_name] = contagem.get(d.user_name, 0) + 1
        top_vendedores = sorted(
            ({"vendedor": k, "abertas": v} for k, v in contagem.items()),
            key=lambda x: x["abertas"], reverse=True,
        )[:8]

        return {
            "resumo": {
                "total_negociacoes": len(deals),
                "abertas": len(abertas),
                "ganhas_mes": len(ganhas_mes),
                "perdidas": len(perdidas),
                "pipeline_total": pipeline_total,
                "pipeline_total_fmt": _moeda(pipeline_total),
                "atividades_hoje": atividades_hoje,
                "vendedores": len(users),
            },
            "por_etapa": por_etapa,
            "top_vendedores": top_vendedores,
            "ultima_sincronizacao": (
                ultimo_sync.finished_at.strftime("%d/%m/%Y %H:%M") if ultimo_sync else "—"
            ),
        }
    finally:
        db.close()


@app.get("/api/oportunidades")
def oportunidades(etapa: str = "", vendedor: str = ""):
    """Lista de negociações abertas, com filtros por etapa e vendedor."""
    db = SessionLocal()
    try:
        stages = db.query(DealStage).order_by(DealStage.order).all()
        users = db.query(User).order_by(User.name).all()
        abertas = [d for d in db.query(Deal).all()
                   if d.win is None and not eh_ex_funcionario(d.user_name)]

        filtradas = abertas
        if etapa:
            filtradas = [d for d in filtradas if d.stage_name == etapa]
        if vendedor:
            filtradas = [d for d in filtradas if d.user_name == vendedor]

        # ordena por última atividade (mais recentes primeiro)
        filtradas.sort(key=lambda d: d.last_activity_at or "", reverse=True)

        lista = [{
            "name": d.name,
            "etapa": d.stage_name,
            "vendedor": d.user_name,
            "empresa": d.organization_name,
            "valor_fmt": _moeda(d.amount_total),
            "valor": d.amount_total,
            "ultima_atividade": (d.last_activity_at or "")[:10],
        } for d in filtradas[:400]]

        return {
            "etapas": [s.name for s in stages],
            "vendedores": [u.name for u in users if u.name and not eh_ex_funcionario(u.name)],
            "total_filtrado": len(filtradas),
            "valor_filtrado_fmt": _moeda(sum(d.amount_total for d in filtradas)),
            "negociacoes": lista,
        }
    finally:
        db.close()


@app.get("/api/relatorios")
def relatorios():
    """Métricas por vendedor e por etapa, com taxa de conversão."""
    db = SessionLocal()
    try:
        deals = _deals_ativos(db)
        stages = db.query(DealStage).order_by(DealStage.order).all()

        # Por vendedor
        por_vendedor = {}
        for d in deals:
            nome = d.user_name or "(sem vendedor)"
            if eh_ex_funcionario(nome):
                continue
            v = por_vendedor.setdefault(nome, {"abertas": 0, "ganhas": 0, "perdidas": 0})
            if d.win is None:
                v["abertas"] += 1
            elif d.win is True:
                v["ganhas"] += 1
            else:
                v["perdidas"] += 1
        lista_vend = []
        for nome, v in por_vendedor.items():
            fechadas = v["ganhas"] + v["perdidas"]
            conv = round(100 * v["ganhas"] / fechadas, 1) if fechadas else 0.0
            lista_vend.append({"vendedor": nome, "cargo": cargo_de(nome), **v, "conversao": conv})
        lista_vend.sort(key=lambda x: x["abertas"], reverse=True)

        # Por etapa (abertas) — agrupado por NOME (junta todos os funis/pipelines)
        abertas = [d for d in deals if d.win is None]
        ordem_etapa = {s.name.strip().lower(): s.order for s in stages}
        agg_e = {}
        for d in abertas:
            nome = " ".join((d.stage_name or "Sem etapa").split())
            agg_e.setdefault(nome.lower(), {"etapa": nome, "quantidade": 0})["quantidade"] += 1
        por_etapa = sorted(agg_e.values(), key=lambda x: (ordem_etapa.get(x["etapa"].lower(), 999), x["etapa"]))

        # Geral
        ganhas = sum(1 for d in deals if d.win is True)
        perdidas = sum(1 for d in deals if d.win is False)
        abertas_n = sum(1 for d in deals if d.win is None)
        fechadas = ganhas + perdidas
        conv_geral = round(100 * ganhas / fechadas, 1) if fechadas else 0.0

        # Negociações criadas por mês (últimos 12 meses com dados)
        contagem_mes = {}
        for d in deals:
            mes = (d.created_at or "")[:7]  # AAAA-MM
            if len(mes) == 7:
                contagem_mes[mes] = contagem_mes.get(mes, 0) + 1
        meses_ordenados = sorted(contagem_mes.keys())[-12:]
        por_mes = [{"mes": m, "quantidade": contagem_mes[m]} for m in meses_ordenados]

        return {
            "geral": {
                "ganhas": ganhas, "perdidas": perdidas, "abertas": abertas_n,
                "conversao": conv_geral,
            },
            "por_vendedor": lista_vend,
            "por_etapa": por_etapa,
            "por_mes": por_mes,
        }
    finally:
        db.close()


@app.get("/api/atividades")
def atividades(vendedor: str = "", busca: str = "", limite: int = 100):
    """Linha do tempo de atividades, com filtro por vendedor e busca por texto."""
    db = SessionLocal()
    try:
        users = db.query(User).order_by(User.name).all()
        # nome da negociação por id (para mostrar a que negociação a atividade pertence)
        nome_deal = {d.id: d.name for d in db.query(Deal).all()}

        atvs = [a for a in db.query(Activity).all() if not eh_ex_funcionario(a.user_name)]
        if vendedor:
            atvs = [a for a in atvs if a.user_name == vendedor]
        if busca:
            b = busca.lower()
            atvs = [a for a in atvs if b in (a.text or "").lower()]
        atvs.sort(key=lambda a: a.date or "", reverse=True)

        lista = [{
            "vendedor": a.user_name or "—",
            "negociacao": nome_deal.get(a.deal_id, ""),
            "data": (a.date or "")[:16].replace("T", " "),
            "texto": (a.text or "")[:240],
        } for a in atvs[:limite]]

        return {
            "vendedores": [u.name for u in users if u.name and not eh_ex_funcionario(u.name)],
            "total": len(atvs),
            "atividades": lista,
        }
    finally:
        db.close()


@app.get("/api/perguntas-rapidas")
def perguntas_rapidas():
    """Respostas prontas (sem IA, sem custo): cada 'bloco' vira um botão no painel."""
    db = SessionLocal()
    try:
        m = _coletar_metricas(db)
    finally:
        db.close()

    blocos = [
        {
            "id": "hoje",
            "titulo": "✅ O que cada vendedor fez hoje",
            "colunas": ["Vendedor", "Atividades hoje"],
            "linhas": [[nome, qtd] for nome, qtd in m["hoje_por_vend"]],
            "vazio": "Ninguém registrou atividade hoje ainda.",
        },
        {
            "id": "abertas",
            "titulo": "📂 Negociações abertas por vendedor",
            "colunas": ["Vendedor", "Cargo", "Abertas", "Valor"],
            "linhas": [[nome, m["ab_vend_cargo"].get(nome, "Outros"), v["qtd"], _moeda(v["valor"])]
                       for nome, v in m["ab_vend"]],
            "vazio": "Nenhuma negociação aberta.",
        },
        {
            "id": "cargos",
            "titulo": "👥 Equipe por cargo",
            "colunas": ["Cargo", "Vendedores", "Abertas", "Ganhas", "Perdidas"],
            "linhas": [[c["cargo"], c["vendedores"], c["abertas"], c["ganhas"], c["perdidas"]] for c in m["por_cargo"]],
            "vazio": "Sem dados.",
        },
        {
            "id": "paradas7",
            "titulo": "⏰ Paradas há mais de 7 dias (sem atividade)",
            "colunas": ["Vendedor", "Negociações paradas"],
            "linhas": [[nome, qtd] for nome, qtd in m["paradas7"]],
            "vazio": "Nenhuma negociação parada há mais de 7 dias. 🎉",
        },
        {
            "id": "paradas15",
            "titulo": "🚨 Paradas há mais de 15 dias (atenção!)",
            "colunas": ["Vendedor", "Negociações paradas"],
            "linhas": [[nome, qtd] for nome, qtd in m["paradas15"]],
            "vazio": "Nenhuma negociação parada há mais de 15 dias. 🎉",
        },
        {
            "id": "ranking",
            "titulo": "🏆 Ranking de ganhas no mês",
            "colunas": ["Vendedor", "Ganhas no mês"],
            "linhas": [[nome, qtd] for nome, qtd in m["ganhas_mes_vend"]],
            "vazio": "Nenhuma venda fechada neste mês ainda.",
        },
        {
            "id": "conversao",
            "titulo": "📈 Taxa de conversão por vendedor",
            "colunas": ["Vendedor", "Cargo", "Conversão", "Ganhas", "Perdidas"],
            "linhas": [[c["vendedor"], c["cargo"], f"{c['conversao']}%", c["ganhas"], c["perdidas"]] for c in m["conversao"]],
            "vazio": "Sem dados de conversão.",
        },
        {
            "id": "etapas",
            "titulo": "🔻 Pipeline por etapa",
            "colunas": ["Etapa", "Negociações", "Valor"],
            "linhas": [[e["etapa"], e["qtd"], _moeda(e["valor"])] for e in m["por_etapa"]],
            "vazio": "Sem etapas.",
        },
    ]
    return {"gerado_em": m["gerado_em"], "blocos": blocos}


@app.get("/api/relatorio-geral")
def relatorio_geral():
    """Gera um relatório de texto com TUDO, para baixar e colar numa conversa com a Claude."""
    db = SessionLocal()
    try:
        m = _coletar_metricas(db)
    finally:
        db.close()

    L = []
    L.append("# RELATÓRIO GERAL — CRM Hai Logistics")
    L.append(f"Gerado em: {m['gerado_em']}")
    L.append("")
    L.append("> Este relatório foi gerado pelo painel comercial. Cole o conteúdo abaixo numa")
    L.append("> conversa com a Claude e pergunte o que quiser sobre a equipe e as vendas.")
    L.append("")
    L.append("## Resumo geral")
    L.append(f"- Total de negociações: {m['total']}")
    L.append(f"- Em aberto: {m['abertas']}")
    L.append(f"- Ganhas (total): {m['ganhas']}")
    L.append(f"- Perdidas (total): {m['perdidas']}")
    L.append(f"- Ganhas no mês: {m['ganhas_mes']}")
    L.append(f"- Pipeline em aberto: {_moeda(m['pipeline_aberto'])}")
    fechadas = m["ganhas"] + m["perdidas"]
    conv_geral = round(100 * m["ganhas"] / fechadas, 1) if fechadas else 0.0
    L.append(f"- Taxa de conversão geral: {conv_geral}%")
    L.append("")

    def tabela(titulo, colunas, linhas, vazio="(sem dados)"):
        L.append(f"## {titulo}")
        if not linhas:
            L.append(vazio)
            L.append("")
            return
        L.append("| " + " | ".join(colunas) + " |")
        L.append("| " + " | ".join("---" for _ in colunas) + " |")
        for ln in linhas:
            L.append("| " + " | ".join(str(c) for c in ln) + " |")
        L.append("")

    tabela("Equipe por cargo",
           ["Cargo", "Vendedores", "Abertas", "Ganhas", "Perdidas"],
           [[c["cargo"], c["vendedores"], c["abertas"], c["ganhas"], c["perdidas"]] for c in m["por_cargo"]])
    tabela("Desempenho por vendedor (conversão)",
           ["Vendedor", "Cargo", "Abertas", "Ganhas", "Perdidas", "Conversão"],
           [[c["vendedor"], c["cargo"], c["abertas"], c["ganhas"], c["perdidas"], f"{c['conversao']}%"] for c in m["conversao"]])
    tabela("Atividades de hoje por vendedor", ["Vendedor", "Atividades hoje"],
           [[n, q] for n, q in m["hoje_por_vend"]], "Ninguém registrou atividade hoje ainda.")
    tabela("Negociações abertas por vendedor", ["Vendedor", "Abertas", "Valor"],
           [[n, v["qtd"], _moeda(v["valor"])] for n, v in m["ab_vend"]])
    tabela("Paradas há mais de 7 dias (sem atividade)", ["Vendedor", "Paradas"],
           [[n, q] for n, q in m["paradas7"]], "Nenhuma.")
    tabela("Paradas há mais de 15 dias", ["Vendedor", "Paradas"],
           [[n, q] for n, q in m["paradas15"]], "Nenhuma.")
    tabela("Ganhas no mês por vendedor", ["Vendedor", "Ganhas no mês"],
           [[n, q] for n, q in m["ganhas_mes_vend"]], "Nenhuma venda fechada neste mês ainda.")
    tabela("Pipeline por etapa (abertas)", ["Etapa", "Negociações", "Valor"],
           [[e["etapa"], e["qtd"], _moeda(e["valor"])] for e in m["por_etapa"]])
    tabela("15 maiores negociações abertas (por valor)", ["Negociação", "Empresa", "Etapa", "Vendedor", "Valor"],
           [[d.name, d.organization_name or "", d.stage_name, d.user_name, _moeda(d.amount_total)] for d in m["top_abertas"]])
    tabela("Negociações criadas por mês", ["Mês", "Quantidade"],
           [[x["mes"], x["qtd"]] for x in m["por_mes"]])

    texto = "\n".join(L)
    nome_arq = "relatorio-crm-" + datetime.now(FUSO_BR).strftime("%Y-%m-%d") + ".md"
    return PlainTextResponse(texto, headers={
        "Content-Disposition": f'attachment; filename="{nome_arq}"',
        "Content-Type": "text/markdown; charset=utf-8",
    })


@app.post("/api/ia")
def ia(pergunta: str = Body(..., embed=True)):
    """Responde perguntas em linguagem natural sobre os dados do CRM (usa Claude)."""
    if not ANTHROPIC_API_KEY:
        return {
            "ok": False,
            "resposta": "A IA ainda não está ativada. Falta cadastrar a chave da Claude "
                        "(Anthropic) no arquivo .env (campo ANTHROPIC_API_KEY). Assim que ela "
                        "for adicionada, o chefe poderá perguntar qualquer coisa aqui.",
        }

    # Monta um resumo dos dados para dar contexto ao modelo
    db = SessionLocal()
    try:
        deals = _deals_ativos(db)
        stages = db.query(DealStage).order_by(DealStage.order).all()
        abertas = [d for d in deals if d.win is None]
        contexto = {
            "total": len(deals),
            "abertas": len(abertas),
            "ganhas": sum(1 for d in deals if d.win is True),
            "perdidas": sum(1 for d in deals if d.win is False),
            "pipeline_aberto": sum(d.amount_total for d in abertas),
            "por_etapa": {s.name: sum(1 for d in abertas if d.stage_id == s.id) for s in stages},
            "atividades_hoje": sum(1 for d in deals if d.last_activity_markup == "today"),
        }
    finally:
        db.close()

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=600,
            system=(
                "Você é um assistente comercial da Hai Logistics. Responda em português, de forma "
                "objetiva, usando SOMENTE os dados de contexto do CRM fornecidos. Se a informação "
                "não estiver no contexto, diga que ainda não está disponível no painel."
            ),
            messages=[{
                "role": "user",
                "content": f"Dados atuais do CRM (JSON): {contexto}\n\nPergunta do gestor: {pergunta}",
            }],
        )
        resposta = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
        return {"ok": True, "resposta": resposta}
    except Exception as e:
        return {"ok": False, "resposta": f"Erro ao consultar a IA: {e}"}


@app.post("/api/sync")
def forcar_sync():
    """Botão 'Atualizar': puxa os dados do CRM de novo."""
    try:
        resumo = sincronizar()
        return {"ok": True, **resumo}
    except Exception as e:
        return {"ok": False, "erro": str(e)}


# --- Frontend (HTML/CSS/JS) ---
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/")
def index():
    return FileResponse(str(FRONTEND_DIR / "index.html"))
