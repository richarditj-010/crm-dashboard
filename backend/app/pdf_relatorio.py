"""Gera o PDF "resumo executivo" que vai anexado ao email semanal.

Uma página no visual do design system da Hai: faixa navy com a logo,
cartões de números coloridos, prioridades numeradas, caixa da ação da
semana, tabela da equipe com barrinhas de conversão e pontos de atenção.
É montado NA HORA do envio, com os dados já atualizados do banco.
Usa a biblioteca fpdf2 (pura Python — funciona no PC e no Render).
"""
from fpdf import FPDF

from app.config import FRONTEND_DIR

# Cores do design system Hai
NAVY = (18, 85, 126)
NAVY_ESCURO = (10, 44, 66)
NAVY_CLARO = (182, 209, 230)
FUNDO = (238, 245, 250)
TINTA = (15, 23, 42)
CINZA = (71, 85, 105)
CINZA_CLARO = (148, 163, 184)
VERDE = (5, 150, 105)
VERMELHO = (220, 38, 38)
AMBAR = (180, 83, 9)
AMBAR_FUNDO = (254, 243, 226)
BRANCO = (255, 255, 255)
TRILHO = (217, 232, 242)

LOGO_BRANCA = FRONTEND_DIR / "img" / "logo-hai-branca.png"


def _txt(s):
    """As fontes padrão do PDF não têm emoji/travessão — troca por equivalentes simples."""
    trocas = {"—": "-", "–": "-", "’": "'", "‘": "'", "“": '"', "”": '"', "…": "..."}
    for de, para in trocas.items():
        s = s.replace(de, para)
    return s.encode("latin-1", "replace").decode("latin-1")


def _n_linhas(pdf, largura, altura, texto):
    """Quantas linhas um texto vai ocupar (para desenhar caixas do tamanho certo)."""
    try:
        return max(1, len(pdf.multi_cell(largura, altura, _txt(texto), split_only=True)))
    except TypeError:  # versão antiga da fpdf2 sem split_only
        import math
        return max(1, math.ceil(pdf.get_string_width(_txt(texto)) / (largura - 4)))


def _titulo_secao(pdf, texto):
    pdf.set_text_color(*NAVY)
    pdf.set_font("helvetica", "B", 10.5)
    pdf.cell(0, 7, _txt(texto.upper()), new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(226, 232, 240)
    pdf.set_line_width(0.3)
    pdf.line(12, pdf.get_y(), 198, pdf.get_y())
    pdf.ln(3)


def _caixa_destacada(pdf, texto, cor_barra, cor_fundo, cor_texto):
    """Caixa com barrinha colorida à esquerda (ação da semana / atenção)."""
    linhas = _n_linhas(pdf, 176, 6, texto)
    alt = linhas * 6 + 6
    y0 = pdf.get_y()
    pdf.set_fill_color(*cor_fundo)
    pdf.rect(15, y0, 183, alt, "F")
    pdf.set_fill_color(*cor_barra)
    pdf.rect(12, y0, 3, alt, "F")
    pdf.set_xy(19, y0 + 3)
    pdf.set_text_color(*cor_texto)
    pdf.set_font("helvetica", "", 10.5)
    pdf.multi_cell(176, 6, _txt(texto), new_x="LMARGIN", new_y="NEXT")
    pdf.set_y(y0 + alt + 4)


def gerar_pdf(m, prioridades, acao, atencao) -> bytes:
    """Monta o PDF e devolve os bytes prontos pra anexar no email."""
    pdf = FPDF("P", "mm", "A4")
    pdf.set_auto_page_break(True, margin=16)
    pdf.set_margins(12, 12, 12)
    pdf.add_page()

    # --- Faixa navy do topo, com a logo da Hai ---
    pdf.set_fill_color(*NAVY_ESCURO)
    pdf.rect(0, 0, 210, 30, "F")
    pdf.set_fill_color(*NAVY)
    pdf.rect(0, 29, 210, 1.4, "F")
    if LOGO_BRANCA.exists():
        pdf.image(str(LOGO_BRANCA), x=12, y=5.5, h=18)
        x_titulo = 48
    else:
        x_titulo = 12
    pdf.set_text_color(*BRANCO)
    pdf.set_font("helvetica", "B", 15)
    pdf.set_xy(x_titulo, 8)
    pdf.cell(0, 7, _txt("Relatório Comercial"))
    pdf.set_text_color(*NAVY_CLARO)
    pdf.set_font("helvetica", "", 9.5)
    pdf.set_xy(x_titulo, 16)
    pdf.cell(0, 5, _txt(f"Resumo executivo da semana - dados atualizados em {m['gerado_em']}"))

    # --- Cartões com os números principais ---
    fechadas = m["ganhas"] + m["perdidas"]
    conv_geral = round(100 * m["ganhas"] / fechadas, 1) if fechadas else 0.0
    paradas15_total = sum(q for _, q in m["paradas15"])
    cartoes = [
        (str(m["abertas"]), "negociações em aberto", NAVY),
        (str(m["ganhas_mes"]), "vendas fechadas no mês", VERDE if m["ganhas_mes"] else VERMELHO),
        (str(paradas15_total), "paradas há 15+ dias", AMBAR if paradas15_total else VERDE),
        (f"{conv_geral}%", "conversão geral", NAVY),
    ]
    y, larg, alt, esp = 37, 44.5, 25, 3.5
    x = 12
    for numero, rotulo, cor in cartoes:
        pdf.set_fill_color(*FUNDO)
        pdf.rect(x, y, larg, alt, "F")
        pdf.set_fill_color(*cor)
        pdf.rect(x, y, larg, 1.6, "F")   # filete colorido no topo do cartão
        pdf.set_text_color(*cor)
        pdf.set_font("helvetica", "B", 17)
        pdf.set_xy(x, y + 5)
        pdf.cell(larg, 8, _txt(numero), align="C")
        pdf.set_text_color(*CINZA)
        pdf.set_font("helvetica", "", 8.5)
        pdf.set_xy(x + 2, y + 15)
        pdf.multi_cell(larg - 4, 4, _txt(rotulo), align="C")
        x += larg + esp
    pdf.set_y(y + alt + 8)

    # --- Prioridades da semana (bolinhas numeradas) ---
    _titulo_secao(pdf, "3 prioridades da semana")
    for i, p in enumerate(prioridades, 1):
        y0 = pdf.get_y()
        pdf.set_fill_color(*NAVY)
        pdf.ellipse(12, y0 + 0.5, 6.5, 6.5, "F")
        pdf.set_text_color(*BRANCO)
        pdf.set_font("helvetica", "B", 10)
        pdf.set_xy(12, y0 + 0.8)
        pdf.cell(6.5, 6, str(i), align="C")
        pdf.set_xy(22, y0)
        pdf.set_text_color(*TINTA)
        pdf.set_font("helvetica", "", 10.5)
        pdf.multi_cell(176, 6.5, _txt(p), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1.5)
    pdf.ln(2)

    # --- Ação desta semana ---
    _titulo_secao(pdf, "Ação desta semana")
    _caixa_destacada(pdf, acao, NAVY, FUNDO, TINTA)
    pdf.ln(2)

    # --- Equipe: visão rápida (com barrinha de conversão) ---
    _titulo_secao(pdf, "Equipe - visão rápida")
    ganhas_mes_vend = dict(m["ganhas_mes_vend"])
    paradas_vend = dict(m["paradas15"])
    colunas = [("Vendedor", 58, "L"), ("Abertas", 26, "C"), ("Vendas no mês", 30, "C"),
               ("Paradas 15+", 30, "C"), ("Conversão", 42, "C")]
    pdf.set_fill_color(*NAVY)
    pdf.set_text_color(*BRANCO)
    pdf.set_font("helvetica", "B", 9)
    for nome_col, larg_col, alin in colunas:
        pdf.cell(larg_col, 7, _txt(nome_col), fill=True, align=alin)
    pdf.ln()
    max_conv = max([c["conversao"] for c in m["conversao"]] + [1])
    zebra = False
    for c in m["conversao"]:
        y0 = pdf.get_y()
        pdf.set_fill_color(*(FUNDO if zebra else BRANCO))
        vend = c["vendedor"]
        vendas_mes = ganhas_mes_vend.get(vend, 0)
        pdf.set_text_color(*TINTA)
        pdf.set_font("helvetica", "B", 9.5)
        pdf.cell(58, 7, _txt(vend), fill=True)
        pdf.set_font("helvetica", "", 9.5)
        pdf.cell(26, 7, str(c["abertas"]), fill=True, align="C")
        pdf.set_text_color(*(VERDE if vendas_mes else CINZA_CLARO))
        pdf.set_font("helvetica", "B" if vendas_mes else "", 9.5)
        pdf.cell(30, 7, str(vendas_mes), fill=True, align="C")
        pdf.set_text_color(*TINTA)
        pdf.set_font("helvetica", "", 9.5)
        pdf.cell(30, 7, str(paradas_vend.get(vend, 0)), fill=True, align="C")
        # célula da conversão: barrinha + número
        pdf.cell(42, 7, "", fill=True)
        pdf.set_fill_color(*TRILHO)
        pdf.rect(158, y0 + 2.4, 22, 2.2, "F")
        pdf.set_fill_color(*NAVY)
        pdf.rect(158, y0 + 2.4, max(0.6, 22 * (c["conversao"] / max_conv)), 2.2, "F")
        pdf.set_xy(181, y0)
        pdf.set_font("helvetica", "B", 9)
        pdf.set_text_color(*TINTA)
        pdf.cell(16, 7, f"{c['conversao']}%", align="R")
        pdf.ln()
        zebra = not zebra
    pdf.ln(4)

    # --- Pontos de atenção (só aparecem quando existem) ---
    if atencao:
        _titulo_secao(pdf, "Pontos de atenção")
        for a in atencao:
            _caixa_destacada(pdf, a, AMBAR, AMBAR_FUNDO, AMBAR)

    # --- Rodapé (sem quebra automática, senão ele "vaza" pra uma 2ª página em branco) ---
    pdf.set_auto_page_break(False)
    pdf.set_y(-15)
    pdf.set_draw_color(226, 232, 240)
    pdf.set_line_width(0.3)
    pdf.line(12, pdf.get_y() - 2, 198, pdf.get_y() - 2)
    pdf.set_text_color(*CINZA_CLARO)
    pdf.set_font("helvetica", "I", 8)
    pdf.cell(0, 5, _txt("Gerado automaticamente pelo painel comercial - números lidos "
                        "direto do Pipedrive."), align="C")

    return bytes(pdf.output())
