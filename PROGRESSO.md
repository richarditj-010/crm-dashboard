# 📋 PROGRESSO DO PROJETO — CRM Dashboard (Hai Logistics)

> Documento vivo: atualizado a cada passo. Serve para você saber **o que já está pronto**,
> **onde paramos** e **o que vem a seguir**. Última atualização: **11/06/2026**.

---

## 🟢 Como ligar o sistema (resumo rápido)

1. Abrir o PowerShell na pasta do projeto
2. Rodar o servidor:
   ```powershell
   cd "backend"
   ..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```
3. Abrir no navegador: **http://127.0.0.1:8000**
4. Para desligar: fechar a janela do PowerShell (ou Ctrl+C)

> (Mais pra frente faço um atalho/ícone pra ligar com 1 clique.)

---

## ✅ O que já está PRONTO

| Etapa | Status | Detalhe |
|---|---|---|
| 1. Setup do projeto | ✅ | Pastas, ambiente Python (.venv), bibliotecas |
| 2. Token RD Station | ✅ | Token do admin validado — lê a conta da empresa toda |
| 3. Banco SQLite | ✅ | Tabelas: deals, users, deal_stages, sync_log |
| 4. Cliente da API | ✅ | Lê negociações, usuários, etapas (com paginação) |
| 5. Sincronização | ✅ | Puxa do CRM e grava no banco local |
| 6. Backend FastAPI | ✅ | Endpoints internos + botão "Atualizar" |
| 7. Tela Home | ✅ | Cartões, pipeline por etapa, ranking por vendedor |

---

## 📊 Conferência dos dados (em 11/06/2026)

Comparamos o painel com a própria API do RD Station:

| Métrica | API (oficial) | Nosso painel | Resultado |
|---|---|---|---|
| Ganhas | 11 | 11 | ✅ Bate exato |
| Perdidas | 561 | 561 | ✅ Bate exato |
| Total | 1480 | 1478 | ⚠️ Diferença de 2 |
| Em aberto | 908 | 906 | ⚠️ Diferença de 2 |

**Conclusão:** dados ~99,9% corretos. As categorias que importam (ganhas/perdidas) batem
exatamente. A diferença de 2 (em ~1480) está sendo investigada — não afeta decisões.

---

## ✅ Abas do dashboard (atualizado 11/06/2026)

| Aba | Status | Detalhe |
|---|---|---|
| **Home** | ✅ pronta | Cartões, pipeline por etapa, ranking por vendedor |
| **Atividades** | ✅ pronta | Linha do tempo (3528 atividades), filtro por vendedor + busca |
| **Oportunidades** | ✅ pronta | Lista de negociações abertas, filtros por etapa/vendedor, valor somado |
| **Relatórios** | ✅ pronta | Conversão geral + desempenho por vendedor (abertas/ganhas/perdidas) |
| **Perguntas Rápidas** | ✅ pronta | Botões de respostas prontas (grátis, sem IA paga) + **Baixar Relatório Geral** |

> **Decisão (11/06/2026):** a IA paga (chave da Anthropic) foi **descartada** — Richard
> não quis custo. No lugar: **Perguntas Rápidas** (respostas calculadas dos próprios dados)
> + botão **"Baixar Relatório Geral"** (.md) para colar numa conversa com a Claude (plano
> Max do Richard) e perguntar à vontade, sem custo de API.

## 🚧 O que ainda falta / a investigar

| Item | Status | O que precisa |
|---|---|---|
| "Quantas ligações/e-mails" | 🔎 a investigar | A listagem de atividades não traz o "tipo" — precisa do endpoint de tarefas |
| Sincronização automática | ✅ | Atualiza sozinho ao abrir e a cada 30 min (+ botão manual) |
| Atalho para ligar com 1 clique | ✅ | Atalho **"Abrir Dashboard CRM"** na Área de Trabalho (arquivo `Abrir Dashboard.bat` na pasta) |

---

## 🔑 Pendências que dependem de você

1. **Chave da Claude (para a aba de IA / "perguntar")** — é o que permite o chefe
   digitar perguntas ("o que a Camila fez hoje?") e receber resposta. É um cadastro
   na Anthropic (custo baixo por uso). Quando tiver, é só me passar.

---

## 📁 Estrutura dos arquivos (pra você se localizar)

```
crm dashboard/
├── backend/app/
│   ├── main.py          ← servidor + endpoints do dashboard
│   ├── config.py        ← configurações (lê o .env)
│   ├── sync.py          ← sincronização CRM → banco
│   ├── db/models.py     ← as "gavetas" do banco
│   └── integration/rd_client.py  ← conversa com a API do RD Station
├── frontend/            ← a tela (HTML/CSS/JS)
├── data/crm.db          ← banco local (gerado)
├── .env                 ← token e segredos (NÃO compartilhar)
├── PROGRESSO.md         ← este documento
└── README.md
```

---

## 🧹 Ex-funcionários removidos do dashboard (todas as funções)

Lista editável em `backend/app/config.py` → `EX_FUNCIONARIOS`:
Alexandre Rosa, Flaviane Miguel, Sandrei Neves, Barbara Pereira, Pollyana Juttel,
Alex Saner, Benjamin Lechuga, Fabrício, Fernando Peirão, Rodrigo, Maycon.

**Vendedores ativos que ficaram:** Krysthopher Scheidemantel, Eloiza Chalub,
Daiane Cristina Pereira, Camila Peres, Simeão Batista (+ Natalia Otero, sem negócios ainda).

## ✅ Conferência completa (Dashboard × API do RD Station)

| Item | Resultado |
|---|---|
| Ganhas | ✅ Bate exato (11) |
| Perdidas | ✅ Bate exato (549) |
| Σ etapas = abertas | ✅ OK (funil corrigido: junta todos os funis) |
| Σ vendedores = abertas | ✅ OK |
| Ex-funcionários ocultos | ✅ Nenhum aparece |
| Total geral | ⚠️ Diferença fixa de 2 (API conta 2 a mais do que entrega na listagem — quirk do RD Station, ~0,1%, não afeta decisões) |

## 🗒️ Histórico (changelog)

- **11/06/2026** — Etapas 1 a 7 concluídas. Dashboard Home no ar com dados reais
  (1478 negociações, 16 vendedores, 9 etapas). Conferência de dados feita.
  Diagnóstico: 27 negociações em hold, 3528 atividades disponíveis.
- **11/06/2026** — Criado atalho de 1 clique ("Abrir Dashboard CRM" na Área de
  Trabalho + `Abrir Dashboard.bat`). Sistema testado e funcionando após reabertura
  do projeto em nova conversa.
- **11/06/2026** — IA paga descartada (sem custo). Criada a aba **"Perguntas Rápidas"**
  (8 perguntas prontas) + botão **"Baixar Relatório Geral"** (.md) para usar na Claude Max.
  Endpoints `/api/perguntas-rapidas` e `/api/relatorio-geral` testados e OK.
- **11/06/2026** — **Conferência de veracidade** feita contra a API ao vivo: contagens
  batem EXATO (1478 deals, 11 ganhas, 561 perdidas, 3528 atividades). Ressalvas reais
  do RD Station: 98% das abertas estão com valor R$ 0 (equipe não preenche), e
  "atividades hoje" só mostra o que foi registrado no CRM.
- **11/06/2026** — **Atualização automática** ligada (ao abrir + a cada 30 min; tela
  recarrega a cada 5 min). **Cargos** cadastrados em `config.py` (`CARGOS`) e exibidos
  nas Perguntas Rápidas, Relatórios e no Relatório Geral, com bloco "Equipe por cargo".
