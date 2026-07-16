"""Corpo BONITO (HTML) do email semanal — visual do design system da Hai.

Monta um email com cabeçalho navy, cartões de números, prioridades numeradas,
caixa da "ação da semana", tabela da equipe e pontos de atenção. Tudo com
estilos embutidos (inline) e layout de tabelas — o formato que o Outlook e o
Gmail entendem. O texto simples continua existindo como alternativa (fallback).
"""

# Cores do design system Hai
NAVY = "#12557e"
NAVY_ESCURO = "#0a2c42"
NAVY_CLARO = "#b6d1e6"
FUNDO_SUAVE = "#eef5fa"
TINTA = "#0f172a"
CINZA = "#475569"
CINZA_CLARO = "#94a3b8"
VERDE = "#059669"
VERMELHO = "#dc2626"
AMBAR = "#b45309"
AMBAR_FUNDO = "#fef3e2"

FONTE = "font-family:'Segoe UI',Roboto,Arial,sans-serif;"

PAINEL_URL = "https://crm-dashboard-x8v6.onrender.com"


def _br(n) -> str:
    """1234 -> '1.234' (separador de milhar do Brasil)."""
    try:
        return f"{int(n):,}".replace(",", ".")
    except (TypeError, ValueError):
        return str(n)


def _kpi(numero, rotulo, cor) -> str:
    return f"""<td width="25%" style="padding:4px;">
      <div style="background:{FUNDO_SUAVE};border-radius:12px;padding:14px 6px;text-align:center;">
        <div style="{FONTE}font-size:24px;font-weight:700;color:{cor};line-height:1.1;">{numero}</div>
        <div style="{FONTE}font-size:11px;color:{CINZA};margin-top:4px;">{rotulo}</div>
      </div></td>"""


def _titulo_secao(texto) -> str:
    return f"""<div style="{FONTE}font-size:12px;font-weight:700;letter-spacing:.06em;
      text-transform:uppercase;color:{NAVY};margin:26px 0 10px;border-bottom:2px solid {FUNDO_SUAVE};
      padding-bottom:6px;">{texto}</div>"""


def corpo_html(m, prioridades, acao, atencao, semana: str) -> str:
    """Monta o HTML completo do email. `semana` é a data (ex.: '16/07')."""
    fechadas = m["ganhas"] + m["perdidas"]
    conv_geral = round(100 * m["ganhas"] / fechadas, 1) if fechadas else 0.0
    paradas15_total = sum(q for _, q in m["paradas15"])
    ganhas_mes_vend = dict(m["ganhas_mes_vend"])
    paradas_vend = dict(m["paradas15"])

    # --- Prioridades numeradas ---
    linhas_prio = ""
    for i, p in enumerate(prioridades, 1):
        linhas_prio += f"""<tr>
          <td width="34" valign="top" style="padding:7px 0;">
            <div style="{FONTE}width:24px;height:24px;border-radius:99px;background:{NAVY};
              color:#ffffff;font-size:12.5px;font-weight:700;text-align:center;line-height:24px;">{i}</div></td>
          <td valign="top" style="{FONTE}padding:8px 0;font-size:14px;color:{TINTA};line-height:1.5;">{p}</td>
        </tr>"""

    # --- Tabela da equipe (visão rápida) ---
    th = (f"{FONTE}font-size:10.5px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;"
          f"color:#ffffff;background:{NAVY};padding:8px 10px;")
    linhas_eq = ""
    for idx, c in enumerate(m["conversao"]):
        vend = c["vendedor"]
        fundo = "#f7fafc" if idx % 2 else "#ffffff"
        td = f"{FONTE}font-size:13px;color:{TINTA};padding:8px 10px;border-bottom:1px solid #f1f5f9;"
        vendas_mes = ganhas_mes_vend.get(vend, 0)
        cor_vendas = VERDE if vendas_mes else CINZA_CLARO
        linhas_eq += f"""<tr style="background:{fundo};">
          <td style="{td}"><b>{vend}</b><br>
            <span style="font-size:11px;color:{CINZA_CLARO};">{c.get('cargo') or ''}</span></td>
          <td align="center" style="{td}">{_br(c['abertas'])}</td>
          <td align="center" style="{td}color:{cor_vendas};font-weight:700;">{vendas_mes}</td>
          <td align="center" style="{td}">{_br(paradas_vend.get(vend, 0))}</td>
          <td align="center" style="{td}">{c['conversao']}%</td>
        </tr>"""

    # --- Pontos de atenção (só quando existem) ---
    bloco_atencao = ""
    if atencao:
        itens = "".join(
            f"""<div style="{FONTE}font-size:13px;color:{AMBAR};line-height:1.55;margin:6px 0;">&bull; {a}</div>"""
            for a in atencao)
        bloco_atencao = f"""{_titulo_secao("&#9888;&#65039; Pontos de atenção")}
          <div style="background:{AMBAR_FUNDO};border-radius:12px;padding:14px 16px;">{itens}</div>"""

    cor_vendas_kpi = VERDE if m["ganhas_mes"] else VERMELHO
    cor_paradas = AMBAR if paradas15_total else VERDE

    return f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#e8eef4;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#e8eef4;">
<tr><td align="center" style="padding:26px 12px;">
<table role="presentation" width="640" cellpadding="0" cellspacing="0" style="max-width:640px;width:100%;">

  <!-- Cabeçalho navy -->
  <tr><td style="background:{NAVY_ESCURO};background-image:linear-gradient(135deg,{NAVY},{NAVY_ESCURO});
      border-radius:16px 16px 0 0;padding:28px 32px;">
    <div style="{FONTE}color:#ffffff;font-size:24px;font-weight:700;letter-spacing:-.01em;">Hai Logistics</div>
    <div style="{FONTE}color:{NAVY_CLARO};font-size:13.5px;margin-top:5px;">
      Relatório Comercial &middot; Semana {semana}</div>
  </td></tr>

  <!-- Corpo branco -->
  <tr><td style="background:#ffffff;border-radius:0 0 16px 16px;padding:26px 32px 30px;">

    <!-- Cartões de números -->
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>
      {_kpi(_br(m["abertas"]), "negociações em aberto", NAVY)}
      {_kpi(_br(m["ganhas_mes"]), "vendas fechadas no mês", cor_vendas_kpi)}
      {_kpi(_br(paradas15_total), "paradas há 15+ dias", cor_paradas)}
      {_kpi(f"{conv_geral}%", "conversão geral", NAVY)}
    </tr></table>

    {_titulo_secao("&#127919; 3 prioridades da semana")}
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0">{linhas_prio}</table>

    {_titulo_secao("&#9889; Ação desta semana")}
    <div style="background:{FUNDO_SUAVE};border-left:4px solid {NAVY};border-radius:0 12px 12px 0;
      padding:14px 16px;{FONTE}font-size:14px;color:{TINTA};line-height:1.55;">{acao}</div>

    {_titulo_secao("&#128101; Equipe — visão rápida")}
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
      <tr>
        <th align="left" style="{th}border-radius:10px 0 0 0;">Vendedor</th>
        <th align="center" style="{th}">Abertas</th>
        <th align="center" style="{th}">Vendas mês</th>
        <th align="center" style="{th}">Paradas 15+</th>
        <th align="center" style="{th}border-radius:0 10px 0 0;">Conversão</th>
      </tr>
      {linhas_eq}
    </table>

    {bloco_atencao}

    <!-- Botão do painel -->
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>
      <td align="center" style="padding:28px 0 6px;">
        <a href="{PAINEL_URL}" style="{FONTE}display:inline-block;background:{NAVY};
          background-image:linear-gradient(180deg,#16608f,{NAVY});color:#ffffff;font-size:14px;
          font-weight:600;text-decoration:none;padding:12px 28px;border-radius:12px;">
          &#128202;&nbsp; Abrir o painel completo</a>
      </td></tr></table>

    <div style="{FONTE}font-size:11.5px;color:{CINZA_CLARO};text-align:center;margin-top:14px;line-height:1.5;">
      Resumo executivo em PDF no anexo.<br>
      Gerado automaticamente pelo painel comercial &middot; dados do Pipedrive &middot; {m["gerado_em"]}</div>
  </td></tr>

</table>
</td></tr></table>
</body></html>"""
