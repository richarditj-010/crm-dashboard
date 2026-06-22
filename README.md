# CRM Dashboard — Monitoramento Comercial (RD Station CRM)

Sistema local de monitoramento comercial integrado ao **RD Station CRM** (Hai Logistics).
Mostra métricas, atividades da equipe, oportunidades, relatórios por vendedor e por cargo,
e permite baixar um **Relatório Geral** para analisar com a Claude.

> 📋 **Para saber o estado atual, o que está pronto e o que falta, leia o `PROGRESSO.md`.**
> Ele é o documento vivo do projeto (atualizado a cada passo).

## Como ligar (1 clique)

Dê dois cliques no atalho **"Abrir Dashboard CRM"** na Área de Trabalho
(ou no arquivo `Abrir Dashboard.bat` dentro desta pasta).
O painel abre sozinho no navegador em **http://127.0.0.1:8000**.
Para desligar: feche a janela preta.

> Só funciona enquanto a janela preta (servidor) estiver aberta, e só **neste computador**
> (127.0.0.1 = máquina local).

## Como ligar (manual, pelo PowerShell)

```powershell
cd "backend"
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Atualização dos dados

- **Automática:** ao abrir o painel e depois a cada **30 minutos** (configurável em
  `backend/app/main.py` → `SYNC_INTERVALO_MIN`). A tela recarrega sozinha a cada 5 min.
- **Manual:** botão **"↻ Atualizar"** no topo do painel.

## Arquitetura

```
RD Station CRM (API REST v1)  →  SQLite local (data/crm.db)  →  FastAPI (backend)  →  Dashboard Web
```

## Estrutura de pastas

```
crm dashboard/
├── backend/app/
│   ├── main.py                  # servidor + endpoints + atualização automática
│   ├── config.py                # .env, lista de EX_FUNCIONARIOS e CARGOS
│   ├── sync.py                  # sincronização CRM → banco
│   ├── db/models.py             # tabelas (deals, users, deal_stages, activities, sync_log)
│   └── integration/rd_client.py # cliente da API do RD Station CRM
├── frontend/                    # tela (HTML/CSS/JS)
├── data/crm.db                  # banco local (gerado)
├── .env                         # token e segredos (NÃO compartilhar)
├── Abrir Dashboard.bat          # liga o painel com 1 clique
├── PROGRESSO.md                 # diário do projeto (LEIA ESTE)
└── README.md
```

## Onde mexer nas coisas mais comuns

- **Trocar/ajustar cargos:** `backend/app/config.py` → dicionário `CARGOS`.
- **Incluir/remover ex-funcionário:** `backend/app/config.py` → lista `EX_FUNCIONARIOS`.
- **Mudar de quanto em quanto tempo atualiza:** `backend/app/main.py` → `SYNC_INTERVALO_MIN`.
- **Token do RD Station:** arquivo `.env` → `RD_CRM_TOKEN`.

## Observações importantes sobre os dados (conferido em 11/06/2026)

- As **quantidades** (negociações, ganhas, perdidas, por vendedor/etapa/cargo) batem
  **exatamente** com a API do RD Station.
- Os **valores em R$** são pouco confiáveis: ~98% das negociações abertas estão com
  valor **R$ 0** no próprio RD Station (a equipe não preenche o valor). Use as contagens.
- **"Atividades hoje"** mostra só o que foi **registrado no CRM** naquele dia.
</content>
