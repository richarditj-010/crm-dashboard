"""
Backend FastAPI do CRM Dashboard.
- Serve a página do dashboard (frontend)
- Expõe endpoints internos que entregam os dados já tratados (do SQLite)
"""
import base64
import hashlib
import hmac
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
    PAINEL_SENHA, PAINEL_SESSAO_MIN, RELATORIO_CRON_CHAVE,
)
from app.db.database import init_db, SessionLocal
from app.db.models import Deal, User, DealStage, Activity, SyncLog
from app.sync import sincronizar
from app import emailer, email_html, pdf_relatorio

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
# Ao abrir o painel aparece uma telinha pedindo só a senha. Acertou -> o navegador
# guarda um "selo" ASSINADO com prazo por inatividade: enquanto o painel está em uso
# o selo se renova sozinho; parou de usar por PAINEL_SESSAO_MIN minutos (fechou, foi
# almoçar, voltou outro dia) -> pede a senha de novo. O prazo é controlado AQUI no
# servidor porque alguns navegadores (Chrome) restauram a sessão mesmo depois de
# fechados. A senha vem do config (.env); vazia = painel abre direto, sem pedir nada.
COOKIE_LOGIN = "crm_sessao"
# Chave da assinatura do selo: derivada da senha — trocar a senha
# invalida os acessos antigos automaticamente.
_CHAVE_SELO = hashlib.sha256(f"crm-hai::{PAINEL_SENHA}".encode("utf-8")).digest()


def _assinatura(ts: str) -> str:
    return hmac.new(_CHAVE_SELO, ts.encode("ascii"), hashlib.sha256).hexdigest()


def _selo_novo() -> str:
    """Selo 'carimbo de hora + assinatura' — só o servidor sabe gerar."""
    ts = format(int(_time.time()), "x")
    return f"{ts}.{_assinatura(ts)}"


def _logado(request) -> bool:
    """True se o navegador tem um selo válido, usado há menos de PAINEL_SESSAO_MIN."""
    selo = request.cookies.get(COOKIE_LOGIN, "")
    ts, _, sig = selo.partition(".")
    if not ts or not sig or not secrets.compare_digest(sig, _assinatura(ts)):
        return False
    try:
        idade = _time.time() - int(ts, 16)
    except ValueError:
        return False
    return 0 <= idade <= PAINEL_SESSAO_MIN * 60


def _b64_asset(nome: str) -> str:
    """Lê uma imagem do frontend e devolve em base64 (para embutir na tela de login,
    que aparece ANTES do login — o /static é protegido pela senha)."""
    try:
        return base64.b64encode((FRONTEND_DIR / "img" / nome).read_bytes()).decode("ascii")
    except Exception:
        return ""


_LOGO_LOGIN_B64 = _b64_asset("logo-hai-branca.png")
_FAVICON_B64 = _b64_asset("favicon.png")

# Tela de login no design system da Hai (mesma cara do sistema interno):
# fundo navy "aurora", cartão branco à esquerda, destaque da marca à direita.
_LOGIN_HTML = """<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Entrar — CRM Dashboard</title>
<link rel="icon" type="image/png" href="data:image/png;base64,__FAVICON__" />
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:"Inter",ui-sans-serif,system-ui,"Segoe UI",Roboto,Arial,sans-serif;
    -webkit-font-smoothing:antialiased;min-height:100vh;display:flex;flex-direction:column;
    background:linear-gradient(125deg,#16608f 0%,#12557e 30%,#0a2c42 55%,#12557e 80%,#16608f 100%);
    background-size:280% 280%;animation:hai-aurora 22s ease infinite}
  @keyframes hai-aurora{0%{background-position:0% 50%}50%{background-position:100% 50%}100%{background-position:0% 50%}}
  @keyframes hai-blur-up{from{opacity:0;filter:blur(6px);transform:translateY(10px)}to{opacity:1;filter:blur(0);transform:none}}
  @keyframes hai-fade-up{from{opacity:0;transform:translateY(18px) scale(.985)}to{opacity:1;transform:none}}
  @keyframes hai-shake-k{0%,100%{transform:translateX(0)}20%{transform:translateX(-6px)}40%{transform:translateX(5px)}60%{transform:translateX(-3px)}80%{transform:translateX(2px)}}
  @keyframes hai-shimmer-sweep{0%{transform:translateX(-150%) skewX(-18deg)}100%{transform:translateX(250%) skewX(-18deg)}}
  .topo{position:absolute;top:38px;left:195px;z-index:2}
  .topo img{height:180px;width:auto;opacity:.97;
    filter:drop-shadow(0 4px 14px rgba(4,18,31,.35));
    animation:hai-blur-up .7s cubic-bezier(.22,.61,.36,1) both,
              hai-flutuar 12s ease-in-out 1.2s infinite}
  @keyframes hai-flutuar{0%,100%{transform:translateY(0) rotate(0deg)}50%{transform:translateY(-14px) rotate(-1.2deg)}}
  /* Bolhas de luz vagando pelo fundo */
  .orbes{position:fixed;inset:0;overflow:hidden;pointer-events:none;z-index:0}
  .orbe{position:absolute;border-radius:50%;filter:blur(70px)}
  .orbe.o1{width:440px;height:440px;background:#4d8bba;opacity:.32;top:-130px;right:-90px;
    animation:hai-float 18s ease-in-out infinite}
  .orbe.o2{width:360px;height:360px;background:#86b2d3;opacity:.22;bottom:-120px;left:20%;
    animation:hai-float 26s ease-in-out infinite reverse}
  .orbe.o3{width:300px;height:300px;background:#16608f;opacity:.5;top:36%;right:28%;
    animation:hai-float 32s ease-in-out 2s infinite}
  .palco,.topo{position:relative}
  .topo{position:absolute}
  .palco{z-index:1}
  @media (max-width:900px){.topo{position:static;padding:28px 0 0 24px}.topo img{height:84px}}
  .palco{flex:1;display:flex;align-items:center;justify-content:center;padding:24px 34px 60px}
  .duas{display:grid;grid-template-columns:400px 1fr;gap:72px;align-items:center;max-width:1040px;width:100%}
  .cartao{background:#fff;border-radius:18px;padding:34px 32px;border:1px solid rgba(255,255,255,.4);
    box-shadow:0 24px 60px -12px rgba(4,18,31,.5);animation:hai-blur-up .6s cubic-bezier(.22,.61,.36,1) both;
    position:relative}
  /* Brilho percorrendo a borda do cartão */
  @keyframes hai-shine{0%{background-position:0% 0%}100%{background-position:200% 0%}}
  .cartao::before{content:"";position:absolute;inset:0;border-radius:inherit;padding:1.5px;
    background:linear-gradient(110deg,rgba(134,178,211,0) 20%,rgba(134,178,211,.5) 40%,rgba(217,232,242,.95) 50%,rgba(134,178,211,.5) 60%,rgba(134,178,211,0) 80%);
    background-size:200% 100%;-webkit-mask:linear-gradient(#fff 0 0) content-box,linear-gradient(#fff 0 0);
    -webkit-mask-composite:xor;mask-composite:exclude;animation:hai-shine 3.6s linear infinite;pointer-events:none}
  .cartao.hai-shake{animation:hai-blur-up .6s cubic-bezier(.22,.61,.36,1) both,hai-shake-k .45s ease-out .15s both}
  .cartao h1{font-size:20px;font-weight:700;color:#0f172a}
  .cartao small{display:block;font-size:13px;color:#64748b;margin-top:3px}
  .erro{color:#b91c1c;background:#fef2f2;border:1px solid #fecaca;border-radius:12px;
    font-size:13px;padding:10px 12px;margin-top:16px}
  form{margin-top:22px}
  label{display:block;font-size:11px;font-weight:600;letter-spacing:.07em;text-transform:uppercase;
    color:#94a3b8;margin-bottom:7px}
  .campo{position:relative}
  .campo svg{position:absolute;left:12px;top:50%;transform:translateY(-50%);width:15px;height:15px;color:#94a3b8}
  input{width:100%;padding:12px 13px 12px 37px;font-size:15px;color:#0f172a;background:#f8fafc;
    border:1px solid #e2e8f0;border-radius:12px;outline:none;transition:border-color .15s,box-shadow .15s,background .15s}
  input:focus{border-color:#4d8bba;background:#fff;box-shadow:0 0 0 3px #d9e8f2}
  button{position:relative;overflow:hidden;width:100%;margin-top:16px;padding:13px;font-family:inherit;
    font-size:15px;font-weight:600;color:#fff;display:flex;align-items:center;justify-content:center;gap:8px;
    background:linear-gradient(to bottom,#16608f,#12557e);border:0;border-radius:12px;cursor:pointer;
    box-shadow:0 6px 16px -4px rgba(10,44,66,.45);transition:transform .12s ease,box-shadow .15s ease}
  button:hover{background:linear-gradient(to bottom,#12557e,#0e4467);box-shadow:0 8px 20px -4px rgba(10,44,66,.55)}
  button:active{transform:translateY(1px) scale(.99)}
  button::after{content:"";position:absolute;top:0;bottom:0;width:40%;
    background:linear-gradient(90deg,transparent,rgba(255,255,255,.28),transparent);
    animation:hai-shimmer-sweep 2.8s ease-in-out infinite;pointer-events:none}
  button svg{width:16px;height:16px}
  .lado{color:#fff;animation:hai-fade-up .9s cubic-bezier(.22,.61,.36,1) .15s both}
  .lado h2{font-size:31px;font-weight:700;line-height:1.2;text-wrap:balance}
  .lado .sub{font-size:15px;color:#d9e8f2;margin-top:12px;max-width:46ch;line-height:1.55}
  .itens{margin-top:30px;display:flex;flex-direction:column;gap:16px}
  .item{display:flex;align-items:center;gap:13px;font-size:14.5px;
    animation:hai-fade-up .8s cubic-bezier(.22,.61,.36,1) both}
  .item:nth-child(1){animation-delay:.35s}
  .item:nth-child(2){animation-delay:.55s}
  .item:nth-child(3){animation-delay:.75s}
  .item .ico{display:inline-flex;align-items:center;justify-content:center;width:38px;height:38px;flex-shrink:0;
    border-radius:12px;background:rgba(255,255,255,.12);box-shadow:inset 0 0 0 1px rgba(255,255,255,.22)}
  .item .ico svg{width:17px;height:17px}
  .lado .rodape{margin-top:34px;font-size:12.5px;color:#86b2d3}
  @media (max-width:900px){.duas{grid-template-columns:minmax(0,400px);justify-content:center}.lado{display:none}.topo{text-align:center}}
  @media (prefers-reduced-motion:reduce){body,.cartao,.cartao.hai-shake,.lado,button::after,
    .topo img,.orbe,.cartao::before,.item{animation:none}}
</style></head>
<body>
  <div class="orbes" aria-hidden="true"><span class="orbe o1"></span><span class="orbe o2"></span><span class="orbe o3"></span></div>
  <div class="topo"><img src="data:image/png;base64,__LOGO__" alt="Hai Logistics" /></div>
  <div class="palco">
    <div class="duas">
      <div class="cartao__SHAKE__">
        <h1>CRM Dashboard</h1>
        <small>Hai Logistics</small>
        __AVISO__
        <form method="post" action="/login">
          <label for="senha">Senha</label>
          <div class="campo">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="11" x="3" y="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
            <input id="senha" type="password" name="senha" placeholder="Digite a senha" autofocus required />
          </div>
          <button type="submit">Entrar
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>
          </button>
        </form>
      </div>
      <div class="lado">
        <h2>Movendo seu sucesso</h2>
        <p class="sub">Acompanhe o funil, a equipe e os resultados comerciais — tudo num só lugar.</p>
        <div class="itens">
          <div class="item"><span class="ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/></svg></span>Funil por etapa e por vendedor</div>
          <div class="item"><span class="ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z"/></svg></span>Perguntas rápidas com respostas na hora</div>
          <div class="item"><span class="ico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/></svg></span>Relatório semanal no seu e-mail</div>
        </div>
        <p class="rodape">© Hai Logistics · uso interno</p>
      </div>
    </div>
  </div>
</body></html>"""


def _pagina_login(erro: bool = False) -> HTMLResponse:
    """A telinha de login: só uma caixa de senha + botão Entrar."""
    aviso = '<p class="erro" role="alert">Senha incorreta. Tente de novo.</p>' if erro else ""
    html = (_LOGIN_HTML
            .replace("__AVISO__", aviso)
            .replace("__SHAKE__", " hai-shake" if erro else "")
            .replace("__LOGO__", _LOGO_LOGIN_B64)
            .replace("__FAVICON__", _FAVICON_B64))
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
    # As rotas do envio semanal são chamadas por robôs externos (sem login no navegador):
    # elas se protegem sozinhas com uma chave secreta, então passam direto por aqui.
    if caminho in ("/login", "/api/relatorio-semanal", "/api/relatorio-semanal-dados"):
        return await call_next(request)
    if _logado(request):
        resp = await call_next(request)
        # Renova o prazo a cada uso — o selo "desliza" enquanto o painel está ativo.
        resp.set_cookie(COOKIE_LOGIN, _selo_novo(), httponly=True, samesite="lax")
        return resp
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
        # Selo assinado com carimbo de hora: vale por PAINEL_SESSAO_MIN minutos sem
        # uso e se renova a cada acesso. Passou do prazo -> pede a senha de novo.
        resp.set_cookie(
            COOKIE_LOGIN, _selo_novo(),
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

        # Os 4 funis do Pipedrive repetem as MESMAS etapas — no filtro, cada nome
        # aparece uma vez só (o filtro compara por nome, então continua funcionando).
        etapas_unicas, _vistos = [], set()
        for s in stages:
            nome = " ".join((s.name or "").split())
            if nome and nome.lower() not in _vistos:
                _vistos.add(nome.lower())
                etapas_unicas.append(nome)

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
            "etapas": etapas_unicas,
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


def _montar_relatorio_md(m) -> str:
    """Monta o texto Markdown do Relatório Geral a partir das métricas já coletadas.
    Usado tanto no download quanto no envio por email — assim o conteúdo fica sempre igual."""
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

    return "\n".join(L)


def _prioridades_semana(m):
    """Escolhe as 3 prioridades da semana + a "ação da semana" a partir dos números.
    Cada prioridade candidata recebe um peso de urgência calculado dos próprios dados;
    as 3 de maior peso entram — por isso o conteúdo muda conforme o CRM muda.
    Usada no corpo do email E no PDF anexo (os dois contam a mesma história).
    Retorna (lista com 3 textos, texto da ação da semana)."""
    agora = datetime.now(FUSO_BR)
    paradas15_total = sum(q for _, q in m["paradas15"])

    # Conta negociações abertas por etapa procurando palavras-chave no nome da etapa.
    def qtd_etapa(*chaves):
        return sum(e["qtd"] for e in m["por_etapa"]
                   if any(c in e["etapa"].lower() for c in chaves))
    n_fechamento = qtd_etapa("fech")
    n_proposta = qtd_etapa("proposta enviada") or qtd_etapa("propost")
    n_visita = qtd_etapa("visita", "reuni")
    n_recuperacao = qtd_etapa("recupera")
    n_entrada = qtd_etapa("entrada", "contato feito")

    candidatas = []
    if paradas15_total:
        maior = max(m["paradas15"], key=lambda x: x[1])
        extra = (f" (maior volume: {maior[0].split()[0]}, com {maior[1]})"
                 if maior[1] >= 30 else "")
        candidatas.append((paradas15_total * 1.0, "paradas",
                           f"Retomar as {paradas15_total} negociações paradas há mais de "
                           f"15 dias{extra} — dar andamento ou encerrar o que não tem futuro"))
    if n_fechamento:
        candidatas.append((n_fechamento * 40.0, "fechamento",
                           f"Avançar as {n_fechamento} negociações em Fechamento — "
                           f"são as mais próximas de virar venda"))
    if m["ganhas_mes"] == 0 and agora.day >= 10:
        candidatas.append((120.0, "sem_venda",
                           f"Destravar a primeira venda do mês — já estamos no dia "
                           f"{agora.day} e nenhum fechamento foi registrado"))
    if n_proposta:
        candidatas.append((n_proposta * 10.0, "propostas",
                           f"Ativar as {n_proposta} propostas enviadas — cliente com "
                           f"proposta na mão precisa de follow-up agora"))
    if n_visita:
        candidatas.append((n_visita * 12.0, "visitas",
                           f"Realizar (e registrar) as {n_visita} visitas/reuniões "
                           f"agendadas — é a etapa que gera proposta"))
    if n_recuperacao:
        candidatas.append((n_recuperacao * 6.0, "recuperacao",
                           f"Trabalhar as {n_recuperacao} negociações em Recuperação — "
                           f"clientes que já demonstraram interesse antes"))
    if n_entrada:
        candidatas.append((n_entrada * 3.0, "entrada",
                           f"Qualificar os {n_entrada} contatos em Entrada/Contato feito — "
                           f"decidir rápido quem vira oportunidade de verdade"))

    candidatas.sort(key=lambda c: c[0], reverse=True)
    top3 = candidatas[:3]
    while len(top3) < 3:  # garantia: sempre 3 prioridades, mesmo com CRM vazio
        top3.append((0.0, "registro",
                     "Manter o CRM atualizado — toda negociação com próximo passo "
                     "e data definidos"))

    # A "ação da semana" acompanha a prioridade nº 1.
    ACOES = {
        "paradas": "Atualizem o status de cada negociação parada até sexta-feira: "
                   "registre o que foi feito, o próximo passo e a data prevista. "
                   "Sem registro, não existe.",
        "fechamento": "Cada negociação em Fechamento deve terminar a semana com "
                      "definição: ganhou, perdeu ou data de decisão marcada no CRM.",
        "sem_venda": "Cada vendedor escolhe a negociação mais quente da própria carteira "
                     "e concentra esforço nela — o objetivo é sair do zero ainda esta semana.",
        "propostas": "Todo cliente com proposta na mão deve receber um contato até "
                     "sexta — com o retorno registrado no CRM.",
        "visitas": "Confirmar e realizar as visitas/reuniões da semana, registrando "
                   "o resultado de cada uma no CRM.",
        "recuperacao": "Retomar contato com os clientes em Recuperação e registrar "
                       "a resposta de cada um no CRM.",
        "entrada": "Classificar os contatos novos até sexta: avançar os promissores "
                   "e encerrar os sem perfil.",
        "registro": "Atualizem o status de cada negociação no CRM até sexta-feira. "
                    "Registre o que foi feito, o próximo passo e a data prevista. "
                    "Sem registro, não existe.",
    }
    return [texto for _, _, texto in top3], ACOES[top3[0][1]]


def _pontos_atencao(m):
    """Alertas gerados por regras a partir dos dados (sem IA). Só entram quando
    a condição acontece de verdade — semana sem problema, seção sem alerta."""
    atencao = []
    media_valor = m["pipeline_aberto"] / m["abertas"] if m["abertas"] else 0
    if media_valor < 1000:
        atencao.append(f"O pipeline total de {_moeda(m['pipeline_aberto'])} é baixo para "
                       f"{m['abertas']} negociações abertas — boa parte provavelmente está "
                       f"sem valor preenchido, o que dificulta priorizar.")

    ganhas_por_vend = {c["vendedor"]: c["ganhas"] for c in m["conversao"]}
    zerados = [(nome, v["qtd"]) for nome, v in m["ab_vend"]
               if v["valor"] < 1 and ganhas_por_vend.get(nome, 0) == 0 and v["qtd"] >= 20]
    zerados.sort(key=lambda x: x[1], reverse=True)
    top_z = zerados[:2]
    total_z = sum(q for _, q in top_z)
    if len(top_z) >= 2:
        nomes = " e ".join(n.split()[0] for n, _ in top_z)
        atencao.append(f"{nomes} têm juntas {total_z} negociações abertas com R$ 0 em "
                       f"pipeline e 0 vendas — vale uma conversa individual antes de cobrar "
                       f"publicamente no grupo.")
    elif len(top_z) == 1:
        nome, qtd = top_z[0]
        atencao.append(f"{nome.split()[0]} tem {qtd} negociações abertas com R$ 0 e 0 vendas "
                       f"— vale uma conversa individual antes de cobrar no grupo.")
    return atencao


def _resumo_email(m) -> str:
    """Monta o texto PRONTO PARA COLAR NO WHATSAPP. A ESTRUTURA é sempre a mesma
    (visão geral → 3 prioridades → ação da semana → pontos de atenção), mas as
    prioridades e a ação são ESCOLHIDAS A CADA ENVIO conforme os números da semana:
    o que estiver mais crítico no CRM sobe pro topo. (Pedido do Richard em
    02/07/2026: padrão fixo de formato, conteúdo variável.)"""
    hoje = datetime.now(FUSO_BR).strftime("%d/%m")
    paradas15_total = sum(q for _, q in m["paradas15"])
    prioridades, acao = _prioridades_semana(m)

    L = []
    L.append(f"📊 CRM — Semana {hoje}")
    L.append("")
    L.append("*Visão geral*")
    L.append(f"{m['abertas']} negociações em aberto")
    L.append(f"{m['ganhas_mes']} vendas fechadas no mês")
    L.append(f"{paradas15_total} negociações paradas há mais de 15 dias (sem nenhuma atividade)")
    L.append("")
    L.append("*3 prioridades da semana*")
    for emoji, texto in zip(["1️⃣", "2️⃣", "3️⃣"], prioridades):
        L.append(f"{emoji} {texto}")
    L.append("")
    L.append("*Ação desta semana*")
    L.append(acao)

    atencao = _pontos_atencao(m)
    if atencao:
        L.append("")
        L.append("⚠️ Pontos de atenção")
        for a in atencao:
            L.append(f"- {a}")

    L.append("")
    L.append("——")
    L.append("(Resumo executivo em PDF no anexo.)")
    return "\n".join(L)


def _gerar_e_enviar_relatorio():
    """Gera o relatório e envia por email. Retorna (ok: bool, mensagem: str)."""
    if not emailer.config_ok():
        return False, ("Envio de email ainda não configurado. Faltam preencher "
                       "SMTP_USER e SMTP_PASSWORD no arquivo .env.")
    db = SessionLocal()
    try:
        m = _coletar_metricas(db)
    finally:
        db.close()
    corpo = _resumo_email(m)
    prioridades, acao = _prioridades_semana(m)
    atencao = _pontos_atencao(m)
    anexo_pdf = pdf_relatorio.gerar_pdf(m, prioridades, acao, atencao)
    agora = datetime.now(FUSO_BR)
    corpo_html = email_html.corpo_html(m, prioridades, acao, atencao,
                                       semana=agora.strftime("%d/%m"))
    hoje = agora.strftime("%d/%m/%Y")
    nome_arq = "relatorio-crm-" + agora.strftime("%Y-%m-%d") + ".pdf"
    assunto = f"Relatório Comercial CRM — Hai Logistics ({hoje})"
    destinos = emailer.enviar_relatorio_email(assunto, corpo, nome_arq, anexo_pdf,
                                              corpo_html=corpo_html)
    return True, "Relatório enviado para " + ", ".join(destinos) + "."


@app.get("/api/relatorio-geral")
def relatorio_geral():
    """Gera o relatório de texto com TUDO, para baixar e colar numa conversa com a Claude."""
    db = SessionLocal()
    try:
        m = _coletar_metricas(db)
    finally:
        db.close()
    texto = _montar_relatorio_md(m)
    nome_arq = "relatorio-crm-" + datetime.now(FUSO_BR).strftime("%Y-%m-%d") + ".md"
    return PlainTextResponse(texto, headers={
        "Content-Disposition": f'attachment; filename="{nome_arq}"',
        "Content-Type": "text/markdown; charset=utf-8",
    })


@app.post("/api/enviar-relatorio")
def enviar_relatorio():
    """Botão 'Enviar agora pro meu email' — dispara o envio na hora (dashboard logado)."""
    try:
        ok, msg = _gerar_e_enviar_relatorio()
        return {"ok": ok, "mensagem": msg}
    except Exception as e:
        return {"ok": False, "mensagem": f"Não consegui enviar o email: {e}"}


@app.get("/api/relatorio-semanal")
def relatorio_semanal(chave: str = ""):
    """Envio automático semanal — chamado por um agendador externo (ex.: cron-job.org)
    toda segunda às 08:00. Protegido por chave secreta (RELATORIO_CRON_CHAVE no .env)."""
    if not RELATORIO_CRON_CHAVE or not secrets.compare_digest(chave, RELATORIO_CRON_CHAVE):
        return Response(status_code=403)
    # O Render Free "dorme" e acorda com o banco vazio (ele se reconstrói na
    # sincronização que roda no startup). Espera os dados chegarem antes de
    # enviar — senão o relatório de segunda sairia zerado.
    for _ in range(48):  # espera até ~4 minutos
        db = SessionLocal()
        try:
            tem_dados = db.query(Deal).first() is not None
        finally:
            db.close()
        if tem_dados:
            break
        _time.sleep(5)
    try:
        ok, msg = _gerar_e_enviar_relatorio()
        return {"ok": ok, "mensagem": msg}
    except Exception as e:
        return {"ok": False, "mensagem": f"Falha no envio semanal: {e}"}


@app.get("/api/relatorio-semanal-dados")
def relatorio_semanal_dados(chave: str = ""):
    """Entrega o relatório PRONTO (texto do email + PDF) para o robô do Google
    (Apps Script) enviar pelo próprio Gmail — o Render Free bloqueia envio direto
    por SMTP. Protegido pela mesma chave secreta do envio semanal."""
    if not RELATORIO_CRON_CHAVE or not secrets.compare_digest(chave, RELATORIO_CRON_CHAVE):
        return Response(status_code=403)
    db = SessionLocal()
    try:
        if db.query(Deal).first() is None:
            # Painel acabou de acordar e ainda está sincronizando —
            # responde rápido e o robô tenta de novo em alguns segundos.
            return {"pronto": False}
        m = _coletar_metricas(db)
    finally:
        db.close()
    corpo = _resumo_email(m)
    prioridades, acao = _prioridades_semana(m)
    atencao = _pontos_atencao(m)
    anexo_pdf = pdf_relatorio.gerar_pdf(m, prioridades, acao, atencao)
    agora = datetime.now(FUSO_BR)
    return {
        "pronto": True,
        "assunto": f"Relatório Comercial CRM — Hai Logistics ({agora.strftime('%d/%m/%Y')})",
        "corpo": corpo,
        # Versão BONITA do corpo (HTML) — o robô do Google usa como htmlBody.
        "corpo_html": email_html.corpo_html(m, prioridades, acao, atencao,
                                            semana=agora.strftime("%d/%m")),
        "nome_arquivo": "relatorio-crm-" + agora.strftime("%Y-%m-%d") + ".pdf",
        "pdf_base64": base64.b64encode(anexo_pdf).decode("ascii"),
        "destinatarios": emailer.destinatarios(),
    }


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
