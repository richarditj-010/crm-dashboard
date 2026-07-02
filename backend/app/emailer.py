"""Envio do relatório por email via SMTP.

Usa a biblioteca padrão do Python (smtplib) — não precisa instalar nada.
Configurado por padrão para o Microsoft 365 (smtp.office365.com), mas funciona
com qualquer provedor que aceite SMTP (basta ajustar as variáveis no .env).
"""
import smtplib
import socket
from email.message import EmailMessage

from app.config import (
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM, RELATORIO_EMAIL_TO,
)


def config_ok() -> bool:
    """True se as credenciais mínimas de envio estão preenchidas no .env."""
    return bool(SMTP_USER and SMTP_PASSWORD and RELATORIO_EMAIL_TO)


def destinatarios() -> list:
    """Lista de emails de destino (aceita vários separados por vírgula no .env)."""
    return [e.strip() for e in RELATORIO_EMAIL_TO.split(",") if e.strip()]


def enviar_relatorio_email(assunto, corpo_texto, anexo_nome=None, anexo_conteudo=None):
    """Envia o relatório por email. Levanta exceção se falhar (quem chama trata).

    - corpo_texto: resumo legível (texto simples) que aparece no corpo do email.
    - anexo_nome / anexo_conteudo: anexo opcional — bytes de um .pdf ou texto de um .md.
    Retorna a lista de destinatários para quem foi enviado.
    """
    destinos = destinatarios()
    msg = EmailMessage()
    msg["Subject"] = assunto
    msg["From"] = SMTP_FROM
    msg["To"] = ", ".join(destinos)
    msg.set_content(corpo_texto)

    if anexo_nome and anexo_conteudo is not None:
        if isinstance(anexo_conteudo, bytes):
            dados = anexo_conteudo
        else:
            dados = anexo_conteudo.encode("utf-8")
        if anexo_nome.lower().endswith(".pdf"):
            maintype, subtype = "application", "pdf"
        else:
            maintype, subtype = "text", "markdown"
        msg.add_attachment(dados, maintype=maintype, subtype=subtype, filename=anexo_nome)

    # Servidores de nuvem (ex.: Render) não têm rota IPv6, e o Gmail anuncia
    # IPv6 primeiro — sem isto o envio na nuvem falha com "Network is
    # unreachable". Força IPv4 só durante o envio e restaura no final.
    getaddrinfo_original = socket.getaddrinfo

    def _ipv4_apenas(host, port, family=0, *args, **kwargs):
        return getaddrinfo_original(host, port, socket.AF_INET, *args, **kwargs)

    socket.getaddrinfo = _ipv4_apenas
    try:
        try:
            # STARTTLS (porta 587) é o padrão do Gmail e da maioria dos provedores.
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as servidor:
                servidor.ehlo()
                servidor.starttls()
                servidor.ehlo()
                servidor.login(SMTP_USER, SMTP_PASSWORD)
                servidor.send_message(msg)
        except OSError:
            # Porta 587 bloqueada (alguns provedores de nuvem fazem isso) —
            # tenta a porta 465, que usa TLS direto.
            with smtplib.SMTP_SSL(SMTP_HOST, 465, timeout=30) as servidor:
                servidor.login(SMTP_USER, SMTP_PASSWORD)
                servidor.send_message(msg)
    finally:
        socket.getaddrinfo = getaddrinfo_original

    return destinos
