@echo off
chcp 65001 >nul
title CRM Dashboard - Hai Logistics   (FECHE esta janela para DESLIGAR o painel)
cd /d "%~dp0backend"

echo ============================================================
echo   CRM DASHBOARD - Hai Logistics
echo ============================================================
echo.
echo   Iniciando o painel... a janela do navegador abre sozinha
echo   em alguns segundos.
echo.
echo   Para DESLIGAR o painel: basta FECHAR esta janela preta.
echo ============================================================
echo.

rem Abre o navegador depois de 6 segundos (tempo do servidor subir)
start "" cmd /c "timeout /t 6 /nobreak >nul & start "" http://127.0.0.1:8000"

rem Liga o servidor nesta janela (fechar a janela desliga tudo)
"..\.venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
