// ===== Navegação entre abas =====
const abas = document.querySelectorAll(".tab");
abas.forEach(t => t.addEventListener("click", () => {
  abas.forEach(x => x.classList.remove("active"));
  t.classList.add("active");
  const alvo = t.dataset.aba;
  document.querySelectorAll(".aba").forEach(s => s.classList.add("oculta"));
  document.getElementById("aba-" + alvo).classList.remove("oculta");
  if (alvo === "atividades") carregarAtividades();
  if (alvo === "oportunidades") carregarOportunidades();
  if (alvo === "relatorios") carregarRelatorios();
  if (alvo === "perguntas") carregarPerguntas();
}));

// ===== HOME =====
async function carregarHome() {
  const d = await (await fetch("/api/home")).json();
  document.getElementById("ultimo-sync").textContent = "Última sincronização: " + d.ultima_sincronizacao;
  const r = d.resumo;
  const cards = [
    { rotulo: "Negociações (total)", valor: r.total_negociacoes, cls: "" },
    { rotulo: "Em aberto", valor: r.abertas, cls: "azul" },
    { rotulo: "Pipeline em aberto", valor: r.pipeline_total_fmt, cls: "azul" },
    { rotulo: "Ganhas no mês", valor: r.ganhas_mes, cls: "verde" },
    { rotulo: "Atividades hoje", valor: r.atividades_hoje, cls: "" },
    { rotulo: "Vendedores", valor: r.vendedores, cls: "" },
  ];
  document.getElementById("cards").innerHTML = cards.map(c =>
    `<div class="card"><div class="rotulo">${c.rotulo}</div><div class="valor ${c.cls}">${c.valor}</div></div>`).join("");

  const maxQtd = Math.max(1, ...d.por_etapa.map(e => e.quantidade));
  document.getElementById("por-etapa").innerHTML = d.por_etapa.map(e =>
    `<div class="bar-row"><span title="${e.etapa}">${e.etapa}</span>
     <div class="bar-track"><div class="bar-fill" style="width:${(e.quantidade/maxQtd)*100}%"></div></div>
     <span class="bar-qtd">${e.quantidade}</span></div>`).join("");

  document.getElementById("top-vendedores").innerHTML = d.top_vendedores.map(v =>
    `<div class="rank-row"><span>${v.vendedor}</span><span class="qtd">${v.abertas}</span></div>`).join("");
}

// ===== ATIVIDADES =====
let atvFiltrosCarregados = false;
async function carregarAtividades() {
  const vend = document.getElementById("atv-vendedor").value;
  const busca = document.getElementById("atv-busca").value;
  const d = await (await fetch(`/api/atividades?vendedor=${encodeURIComponent(vend)}&busca=${encodeURIComponent(busca)}`)).json();
  if (!atvFiltrosCarregados) {
    document.getElementById("atv-vendedor").innerHTML =
      '<option value="">Todos os vendedores</option>' + d.vendedores.map(v => `<option>${v}</option>`).join("");
    document.getElementById("atv-vendedor").value = vend;
    atvFiltrosCarregados = true;
  }
  document.getElementById("atv-total").textContent = `${d.total} atividade(s)`;
  document.getElementById("atv-lista").innerHTML = d.atividades.map(a =>
    `<div class="tl-item">
       <div class="tl-head"><b>${a.vendedor}</b> <span class="muted">${a.data}</span></div>
       ${a.negociacao ? `<div class="tl-deal">📁 ${a.negociacao}</div>` : ""}
       <div class="tl-text">${(a.texto || "").replace(/</g,"&lt;")}</div>
     </div>`).join("") || "<p class='muted'>Nenhuma atividade encontrada.</p>";
}

// ===== OPORTUNIDADES =====
let opFiltrosCarregados = false;
async function carregarOportunidades() {
  const etapa = document.getElementById("op-etapa").value;
  const vend = document.getElementById("op-vendedor").value;
  const d = await (await fetch(`/api/oportunidades?etapa=${encodeURIComponent(etapa)}&vendedor=${encodeURIComponent(vend)}`)).json();
  if (!opFiltrosCarregados) {
    document.getElementById("op-etapa").innerHTML =
      '<option value="">Todas as etapas</option>' + d.etapas.map(e => `<option>${e}</option>`).join("");
    document.getElementById("op-vendedor").innerHTML =
      '<option value="">Todos os vendedores</option>' + d.vendedores.map(v => `<option>${v}</option>`).join("");
    opFiltrosCarregados = true;
  }
  document.getElementById("op-etapa").value = etapa;
  document.getElementById("op-vendedor").value = vend;
  document.getElementById("op-total").textContent = `${d.total_filtrado} negociação(ões) · ${d.valor_filtrado_fmt}`;
  document.querySelector("#op-tabela tbody").innerHTML = d.negociacoes.map(n =>
    `<tr><td>${n.name}</td><td>${n.empresa||""}</td><td>${n.etapa}</td><td>${n.vendedor}</td>
     <td>${n.valor_fmt}</td><td>${n.ultima_atividade||""}</td></tr>`).join("")
    || "<tr><td colspan='6' class='muted'>Nenhuma negociação.</td></tr>";
}

// ===== RELATORIOS =====
const graficos = {};
function desenhar(id, config) {
  if (graficos[id]) graficos[id].destroy();
  graficos[id] = new Chart(document.getElementById(id), config);
}
const CORES = ["#1565c0","#2e7d32","#ef6c00","#6a1b9a","#00838f","#c62828","#558b2f","#4527a0","#ad1457","#00695c","#f9a825"];

async function carregarRelatorios() {
  const d = await (await fetch("/api/relatorios")).json();
  const g = d.geral;
  const cards = [
    { rotulo: "Ganhas (total)", valor: g.ganhas, cls: "verde" },
    { rotulo: "Perdidas (total)", valor: g.perdidas, cls: "vermelho" },
    { rotulo: "Em aberto", valor: g.abertas, cls: "azul" },
    { rotulo: "Taxa de conversão", valor: g.conversao + "%", cls: "azul" },
  ];
  document.getElementById("rel-cards").innerHTML = cards.map(c =>
    `<div class="card"><div class="rotulo">${c.rotulo}</div><div class="valor ${c.cls}">${c.valor}</div></div>`).join("");
  document.querySelector("#rel-tabela tbody").innerHTML = d.por_vendedor.map(v =>
    `<tr><td>${v.vendedor}</td><td>${v.cargo||"—"}</td><td>${v.abertas}</td><td>${v.ganhas}</td><td>${v.perdidas}</td><td>${v.conversao}%</td></tr>`).join("");

  if (typeof Chart === "undefined") return; // sem internet para carregar a biblioteca

  // Funil por etapa (barras)
  desenhar("g-funil", {
    type: "bar",
    data: { labels: d.por_etapa.map(e => e.etapa),
      datasets: [{ label: "Abertas", data: d.por_etapa.map(e => e.quantidade), backgroundColor: "#1565c0" }] },
    options: { plugins: { legend: { display: false } }, responsive: true },
  });

  // Ganhas x Perdidas x Abertas (rosca)
  desenhar("g-status", {
    type: "doughnut",
    data: { labels: ["Ganhas","Perdidas","Abertas"],
      datasets: [{ data: [g.ganhas, g.perdidas, g.abertas], backgroundColor: ["#2e7d32","#c62828","#1565c0"] }] },
    options: { responsive: true },
  });

  // Abertas por vendedor (barra horizontal)
  desenhar("g-vendedor", {
    type: "bar",
    data: { labels: d.por_vendedor.map(v => v.vendedor),
      datasets: [{ label: "Abertas", data: d.por_vendedor.map(v => v.abertas),
        backgroundColor: d.por_vendedor.map((_, i) => CORES[i % CORES.length]) }] },
    options: { indexAxis: "y", plugins: { legend: { display: false } }, responsive: true },
  });

  // Criadas por mês (linha)
  desenhar("g-mes", {
    type: "line",
    data: { labels: d.por_mes.map(m => m.mes),
      datasets: [{ label: "Criadas", data: d.por_mes.map(m => m.quantidade),
        borderColor: "#1565c0", backgroundColor: "rgba(21,101,192,.15)", fill: true, tension: .3 }] },
    options: { plugins: { legend: { display: false } }, responsive: true },
  });
}

// ===== PERGUNTAS RAPIDAS =====
let prBlocos = [];
function esc(t) { return String(t == null ? "" : t).replace(/</g, "&lt;"); }

async function carregarPerguntas() {
  const cont = document.getElementById("pr-botoes");
  if (prBlocos.length) return; // já carregado
  cont.innerHTML = "<span class='muted'>Carregando…</span>";
  const d = await (await fetch("/api/perguntas-rapidas")).json();
  prBlocos = d.blocos;
  document.getElementById("pr-gerado").textContent = "Dados de: " + d.gerado_em;
  cont.innerHTML = prBlocos.map(b =>
    `<button class="pr-btn" onclick="mostrarPergunta('${b.id}')">${esc(b.titulo)}</button>`).join("");
}

function mostrarPergunta(id) {
  const b = prBlocos.find(x => x.id === id);
  if (!b) return;
  document.querySelectorAll(".pr-btn").forEach(btn =>
    btn.classList.toggle("ativo", btn.getAttribute("onclick").includes(`'${id}'`)));
  const alvo = document.getElementById("pr-resposta");
  if (!b.linhas.length) {
    alvo.innerHTML = `<h3>${esc(b.titulo)}</h3><p class="muted">${esc(b.vazio)}</p>`;
    return;
  }
  const cab = b.colunas.map(c => `<th>${esc(c)}</th>`).join("");
  const corpo = b.linhas.map(ln => `<tr>${ln.map(c => `<td>${esc(c)}</td>`).join("")}</tr>`).join("");
  alvo.innerHTML = `<h3>${esc(b.titulo)}</h3>
    <div class="tabela-wrap"><table class="tabela"><thead><tr>${cab}</tr></thead><tbody>${corpo}</tbody></table></div>`;
}

function baixarRelatorio() {
  const status = document.getElementById("rel-status");
  status.textContent = " Baixando…";
  // abre o endpoint que devolve o arquivo .md para download
  window.location.href = "/api/relatorio-geral";
  setTimeout(() => { status.textContent = " ✅ Baixado! Veja na pasta de Downloads."; }, 1200);
}

// ===== Botão atualizar =====
document.getElementById("btn-atualizar").addEventListener("click", async () => {
  const btn = document.getElementById("btn-atualizar");
  btn.disabled = true; btn.textContent = "Atualizando…";
  try { await fetch("/api/sync", { method: "POST" }); await carregarHome(); }
  finally { btn.disabled = false; btn.textContent = "↻ Atualizar"; }
});

carregarHome();

// Atualiza sozinho a tela a cada 5 minutos (o servidor renova os dados do banco
// automaticamente a cada 30 min e também ao abrir o painel).
setInterval(() => {
  const abaAtiva = document.querySelector(".tab.active")?.dataset.aba;
  if (abaAtiva === "home") carregarHome();
  prBlocos = [];  // força recarregar as "Perguntas Rápidas" com dados frescos
}, 5 * 60 * 1000);
