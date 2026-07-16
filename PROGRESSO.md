# 📋 PROGRESSO DO PROJETO — CRM Dashboard (Hai Logistics)

> Documento vivo: atualizado a cada passo. Serve para você saber **o que já está pronto**,
> **onde paramos** e **o que vem a seguir**. Última atualização: **16/07/2026**.

---

## 🔄 MIGRAÇÃO: RD Station → Pipedrive (16/07/2026)

A Hai **trocou de CRM**: saiu do RD Station e passou a usar o **Pipedrive** (o RD Station
não é mais alimentado). O painel foi migrado para puxar do Pipedrive — **tudo o mais
continua igual** (telas, relatórios, email de segunda, login).

**O que mudou por baixo (só a "fonte" dos dados):**
- Novo motor `backend/app/integration/pipedrive_client.py` (conversa com a API do Pipedrive).
- `sync.py` agora traduz Pipedrive → mesmas tabelas do banco (nada mais mudou).
- `config.py`: token via `PIPEDRIVE_TOKEN`; equipe/cargos atualizados; lista de
  ex-funcionários zerada (todos os usuários atuais visíveis).

**Conferência (16/07/2026) — painel × API do Pipedrive, no mesmo instante:**
- Abertas ✅ 889 = 889 · Ganhas ✅ 16 = 16 · Perdidas ✅ 677 = 677.
- Nuvem (Render) também conferida = 889 abertas. **PC e nuvem migrados e corretos.**
- Ressalva (igual à do RD Station): a equipe quase não preenche valor (só 14 de 889
  abertas têm valor > R$0) — as **contagens** é que são confiáveis, não o R$ do pipeline.

**Token do Pipedrive:** de admin (Simeão), guardado no `.env` local e como env var
`PIPEDRIVE_TOKEN` no Render. O `RD_CRM_TOKEN` antigo ficou só como backup.

**Falta:** Etapa 7 — melhorar design/layout (a pedido do Richard, é a última etapa).

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

## ✅ Envio automático de segunda — FUNCIONANDO (concluído 02/07/2026)

**Como funciona (nada depende de PC ligado):**

1. Toda **segunda entre 08h e 09h**, um robô do Google (**Apps Script**, projeto
   "envio email crm segunda as 08" dentro da conta `disparoemailrichard@gmail.com`)
   acorda sozinho.
2. Ele chama o painel no Render (`/api/relatorio-semanal-dados?chave=...`), que devolve
   o relatório PRONTO: texto do email + PDF com os dados recém-sincronizados
   (o robô insiste por ~4 min enquanto o painel Free acorda).
3. O robô envia o email **pelo próprio Gmail** para `richard@hailogistics.com.br`
   (o Render Free bloqueia envio direto por SMTP — por isso o Gmail é quem envia).
4. O remetente está nos **Remetentes Confiáveis** do Outlook do Richard → cai direto
   na caixa de entrada.

**Peças de apoio:**
- **cron-job.org** (conta do Richard): job "Relatorio CRM segunda 08h", `0 8 * * 1`,
  chama `/api/relatorio-semanal?chave=...`. Hoje serve de **despertador extra** do
  painel às 08h em ponto (o envio SMTP dele falha no Render, sem efeito colateral).
- **Render → Environment** tem: PAINEL_SENHA, RD_CRM_TOKEN, SMTP_HOST, SMTP_PORT,
  SMTP_USER, SMTP_PASSWORD, RELATORIO_EMAIL_TO, RELATORIO_CRON_CHAVE.
- **Testes reais feitos em 02/07/2026:** envio do PC ✅, envio pelo robô do Google ✅
  (execução concluída sem erro, email recebido).

**Para mudar o destinatário no futuro:** trocar `RELATORIO_EMAIL_TO` no Render
(Environment) — pode ter vários emails separados por vírgula.

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

## 🔐 Acesso ao painel (login)

- **Como entra:** abre o link → aparece uma telinha → digita a senha **`BOSS`** (tudo
  maiúsculo) → Entrar. **Não tem campo de usuário.**
- **Onde abrir:**
  - 🖥️ PC (este computador): atalho **"Abrir Dashboard CRM"** (versão local).
  - ☁️ Nuvem (PC, iPad, celular): **https://crm-dashboard-x8v6.onrender.com**
- **Pede senha de novo:** o login vale por **30 minutos sem uso** (enquanto o painel
  está aberto/em uso, renova sozinho). Fechou e voltou depois disso → pede `BOSS`
  outra vez (PC, iPad e celular). O prazo é controlado pelo servidor — o Chrome
  costuma "lembrar" a sessão mesmo fechado, por isso não dava pra confiar no navegador.
  Para mudar o tempo: `PAINEL_SESSAO_MIN` no `.env` (PC) ou Environment (Render).
- **Trocar a senha no futuro:** na nuvem, em render.com → serviço `crm-dashboard` →
  Environment → `PAINEL_SENHA`. No PC, no arquivo `.env` (linha `PAINEL_SENHA`).

## 🗒️ Histórico (changelog)

- **16/07/2026 (tarde 2)** — **Senha volta a ser pedida.** O Chrome restaurava a sessão
  mesmo depois de fechado (comportamento do navegador, atalho em modo aplicativo).
  Solução no servidor: o "selo" de login agora é assinado com carimbo de hora e vale
  **30 min sem uso** (renova sozinho enquanto o painel está em uso; `PAINEL_SESSAO_MIN`
  para ajustar). Selos antigos/falsificados/vencidos barrados (testado). Se o prazo
  vencer com a tela aberta, ela volta sozinha para a tela de senha.
- **16/07/2026 (tarde)** — **VISUAL NOVO: design system Hai.** O painel ganhou a mesma
  identidade do sistema interno da Hai: logo oficial no topo, fonte Inter, cartões
  arredondados, gráficos limpos numa cor só (azul-marinho da marca), tabelas com
  cabeçalho fixo e números alinhados, tela de **login nova** (fundo navy "aurora" +
  cartão branco + "Movendo seu sucesso"), animações suaves. Corrigido o filtro de
  etapas de Oportunidades (25 repetidas → 7 únicas). Revisão adversarial com 3
  revisores: 7 achados, todos corrigidos (celular sem rolagem lateral, rosca com
  total central sempre alinhado, abas navegáveis por teclado etc.). Logo e inspiração
  movidas de Downloads para o projeto (`frontend/img/` e `design/`). Nada de lógica,
  dados ou textos mudou — só o visual.
- **16/07/2026** — **MIGRAÇÃO PARA O PIPEDRIVE.** A Hai trocou de CRM (RD Station →
  Pipedrive). Trocada só a "fonte" dos dados: novo `pipedrive_client.py` + `sync.py`
  adaptado; o resto (telas/relatórios/email/login) segue idêntico. Token de admin
  (Simeão) no `.env` e no Render (`PIPEDRIVE_TOKEN`). Números conferidos contra a API
  ao vivo: abertas 889, ganhas 16, perdidas 677 — batem exato no PC **e** na nuvem.
  Equipe/cargos atualizados (Jeisson, Amanda, Fabrício Sant'Anna, Natalia adicionados;
  Simeão corrigido). Commit `9a2a904` publicado; Render redeployado e conferido.
- **02/07/2026** — **Relatório semanal por email FUNCIONANDO** (testado de verdade, 2 envios
  reais recebidos). Como o Microsoft 365 não permite mais envio simples (SMTP), foi criada
  uma conta Gmail só para disparos: `disparoemailrichard@gmail.com` (senha de aplicativo no
  `.env`). Destino: `richard@hailogistics.com.br`. O **corpo do email** mantém o formato
  aprovado (visão geral → 3 prioridades → ação da semana → pontos de atenção), mas as
  prioridades agora são **escolhidas a cada envio** conforme os números do CRM (o mais
  crítico sobe pro topo). O **anexo** virou um **PDF de 1 página** (resumo executivo:
  cartões de números, prioridades, tabela da equipe), gerado na hora com dados atualizados
  (biblioteca fpdf2). No painel, o botão de email virou **"📄 Baixar Relatório Geral"**
  (a Elaine pode baixar e mandar manualmente se precisar). Git reinstalado no PC.
- **22/06/2026** — **Login refeito**: trocada a janelinha do navegador (usuário+senha) por
  uma **tela própria só com a senha** (`BOSS`). Passou a **pedir a senha a cada sessão**
  (fecha/abre o navegador → pede de novo), no PC e no iPad. Testado e funcionando nos dois.
  Senha igual no PC e na nuvem (BOSS). Filtros conferidos: OK.
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
