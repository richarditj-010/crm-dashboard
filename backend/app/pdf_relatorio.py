"""Gera o PDF "resumo executivo" que vai anexado ao email semanal.

Uma página, visual limpo: números grandes, prioridades da semana, visão rápida
da equipe e pontos de atenção. É montado NA HORA do envio, com os dados já
atualizados do banco — nunca fica velho.
Usa a biblioteca fpdf2 (pura Python — funciona no PC e no Render).
"""
from fpdf import FPDF

AZUL = (31, 59, 99)
AZUL_CLARO = (238, 242, 248)
CINZA = (95, 105, 120)
CINZA_ESCURO = (40, 45, 55)
VERMELHO = (176, 58, 46)
BRANCO = (255, 255, 255)


def _txt(s):
    """As fontes padrão do PDF não têm emoji/travessão — troca por equivalentes simples."""
    trocas = {"—": "-", "–": "-", "’": "'", "‘": "'", "“": '"', "”": '"', "…": "..."}
    for de, para in trocas.items():
        s = s.replace(de, para)
    return s.encode("latin-1", "replace").decode("latin-1")


def gerar_pdf(m, prioridades, acao, atencao) -> bytes:
    """Monta o PDF e devolve os bytes prontos pra anexar no email."""
    pdf = FPDF("P", "mm", "A4")
    pdf.set_auto_page_break(True, margin=12)
    pdf.add_page()

    # --- Faixa do título ---
    pdf.set_fill_color(*AZUL)
    pdf.rect(0, 0, 210, 26, "F")
    pdf.set_text_color(*BRANCO)
    pdf.set_font("helvetica", "B", 15)
    pdf.set_xy(10, 6)
    pdf.cell(0, 7, _txt("Relatório Comercial — CRM Hai Logistics"))
    pdf.set_font("helvetica", "", 9.5)
    pdf.set_xy(10, 14)
    pdf.cell(0, 5, _txt(f"Resumo executivo da semana — dados atualizados em {m['gerado_em']}"))

    # --- Cartões com os números principais ---
    fechadas = m["ganhas"] + m["perdidas"]
    conv_geral = round(100 * m["ganhas"] / fechadas, 1) if fechadas else 0.0
    paradas15_total = sum(q for _, q in m["paradas15"])
    cartoes = [
        (str(m["abertas"]), "negociações em aberto"),
        (str(m["ganhas_mes"]), "vendas fechadas no mês"),
        (str(paradas15_total), "paradas há 15+ dias"),
        (f"{conv_geral}%", "conversão geral"),
    ]
    y, larg, alt, esp = 32, 44.5, 22, 4
    x = 10
    for numero, rotulo in cartoes:
        pdf.set_fill_color(*AZUL_CLARO)
        pdf.rect(x, y, larg, alt, "F")
        pdf.set_text_color(*AZUL)
        pdf.set_font("helvetica", "B", 16)
        pdf.set_xy(x, y + 4)
        pdf.cell(larg, 7, _txt(numero), align="C")
        pdf.set_text_color(*CINZA)
        pdf.set_font("helvetica", "", 8.5)
        pdf.set_xy(x + 2, y + 12)
        pdf.multi_cell(larg - 4, 4, _txt(rotulo), align="C")
        x += larg + esp
    pdf.set_y(y + alt + 6)

    def titulo_secao(texto):
        pdf.set_text_color(*AZUL)
        pdf.set_font("helvetica", "B", 12)
        pdf.cell(0, 7, _txt(texto), new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(*AZUL)
        pdf.set_line_width(0.4)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(2.5)

    # --- Prioridades da semana ---
    titulo_secao("Prioridades da semana")
    for i, p in enumerate(prioridades, 1):
        pdf.set_text_color(*AZUL)
        pdf.set_font("helvetica", "B", 10.5)
        pdf.cell(7, 6, f"{i}.")
        pdf.set_text_color(*CINZA_ESCURO)
        pdf.set_font("helvetica", "", 10.5)
        pdf.multi_cell(183, 6, _txt(p), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)
    pdf.ln(3)

    # --- Ação desta semana ---
    titulo_secao("Ação desta semana")
    pdf.set_fill_color(*AZUL_CLARO)
    pdf.set_text_color(*CINZA_ESCURO)
    pdf.set_font("helvetica", "", 10.5)
    pdf.multi_cell(190, 6.5, _txt(acao), fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # --- Equipe: visão rápida ---
    titulo_secao("Equipe — visão rápida")
    ganhas_mes_vend = dict(m["ganhas_mes_vend"])
    paradas_vend = dict(m["paradas15"])
    colunas = [("Vendedor", 62, "L"), ("Abertas", 32, "C"), ("Vendas no mês", 32, "C"),
               ("Paradas 15+", 32, "C"), ("Conversão", 32, "C")]
    pdf.set_fill_color(*AZUL)
    pdf.set_text_color(*BRANCO)
    pdf.set_font("helvetica", "B", 9.5)
    for nome_col, larg_col, alin in colunas:
        pdf.cell(larg_col, 7, _txt(nome_col), fill=True, align=alin)
    pdf.ln()
    pdf.set_text_color(*CINZA_ESCURO)
    pdf.set_font("helvetica", "", 9.5)
    zebra = False
    for c in m["conversao"]:
        pdf.set_fill_color(*(AZUL_CLARO if zebra else BRANCO))
        vend = c["vendedor"]
        valores = [vend, str(c["abertas"]), str(ganhas_mes_vend.get(vend, 0)),
                   str(paradas_vend.get(vend, 0)), f"{c['conversao']}%"]
        for (nome_col, larg_col, alin), v in zip(colunas, valores):
            pdf.cell(larg_col, 6.5, _txt(v), fill=True, align=alin)
        pdf.ln()
        zebra = not zebra
    pdf.ln(5)

    # --- Pontos de atenção (só aparecem quando existem) ---
    if atencao:
        titulo_secao("Pontos de atenção")
        pdf.set_text_color(*VERMELHO)
        pdf.set_font("helvetica", "", 10)
        for a in atencao:
            pdf.multi_cell(190, 5.5, _txt("- " + a), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)

    # --- Rodapé (sem quebra automática, senão ele "vaza" pra uma 2ª página em branco) ---
    pdf.set_auto_page_break(False)
    pdf.set_y(-16)
    pdf.set_text_color(*CINZA)
    pdf.set_font("helvetica", "I", 8)
    pdf.cell(0, 5, _txt("Gerado automaticamente pelo painel comercial — números lidos "
                        "direto do RD Station CRM."), align="C")

    return bytes(pdf.output())
