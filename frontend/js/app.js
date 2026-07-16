// ===== Design system Hai — cores e padrões visuais dos gráficos =====
const HAI = {
  azul: "#16608f",        // hai-500 (cor única dos dados)
  azulEscuro: "#0e4467",  // hai-700 (hover)
  ok: "#059669",          // ganhas
  erro: "#dc2626",        // perdidas
  grid: "rgba(15,23,42,.06)",
  tick: "#94a3b8",
  texto: "#64748b",
};

if (typeof Chart !== "undefined") {
  Chart.defaults.font.family = "'Inter', ui-sans-serif, system-ui, 'Segoe UI', Roboto, Arial, sans-serif";
  Chart.defaults.font.size = 11;
  Chart.defaults.color = HAI.texto;
  Chart.defaults.plugins.tooltip.backgroundColor = "rgba(15,23,42,.92)";
  Chart.defaults.plugins.tooltip.padding = 10;
  Chart.defaults.plugins.tooltip.cornerRadius = 10;
  Chart.defaults.plugins.tooltip.titleFont = { size: 12, weight: "600" };
  Chart.defaults.plugins.tooltip.bodyFont = { size: 12 };
  Chart.defaults.plugins.tooltip.boxWidth = 8;
  Chart.defaults.plugins.tooltip.boxHeight = 8;
  Chart.defaults.plugins.tooltip.usePointStyle = true;
}

// Eixo de valores "fantasma" (grid a 6%, sem borda) + eixo de categorias limpo
function eixos(horizontal) {
  const valores = {
    grid: { color: HAI.grid, drawTicks: false },
    border: { display: false },
    ticks: { color: HAI.tick, maxTicksLimit: 6, precision: 0 },
    beginAtZero: true,
  };
  const categorias = {
    grid: { display: false },
    border: { display: false },
    ticks: { color: HAI.texto },
  };
  return horizontal ? { x: valores, y: categorias } : { x: categorias, y: valores };
}

// Ícone de estado vazio (caixa de entrada)
const VAZIO_SVG = `<svg class="hai-bob" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 16 12 14 15 10 15 8 12 2 12"/><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/></svg>`;
function vazio(texto) {
  return `<div class="vazio">${VAZIO_SVG}<span>${texto}</span></div>`;
}

// ===== Navegação entre abas =====
const abas = document.querySelectorAll(".tab");
abas.forEach(t => {
  t.addEventListener("click", () => {
    abas.forEach(x => x.classList.remove("active"));
    t.classList.add("active");
    const alvo = t.dataset.aba;
    document.querySelectorAll(".aba").forEach(s => s.classList.add("oculta"));
    document.getElementById("aba-" + alvo).classList.remove("oculta");
    if (alvo === "atividades") carregarAtividades();
    if (alvo === "oportunidades") carregarOportunidades();
    if (alvo === "relatorios") carregarRelatorios();
    if (alvo === "perguntas") carregarPerguntas();
  });
  // Acessibilidade: as abas funcionam também pelo teclado (Tab + Enter/Espaço)
  t.addEventListener("keydown", e => {
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); t.click(); }
  });
});

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

  const maxVend = Math.max(1, ...d.top_vendedores.map(v => v.abertas));
  document.getElementById("top-vendedores").innerHTML = d.top_vendedores.map(v =>
    `<div class="rank-row"><span class="rank-nome" title="${v.vendedor}">${v.vendedor}</span>
     <div class="rank-track"><div class="rank-fill" style="width:${(v.abertas/maxVend)*100}%"></div></div>
     <span class="qtd">${v.abertas}</span></div>`).join("");
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
       ${a.negociacao ? `<div class="tl-deal">${a.negociacao}</div>` : ""}
       <div class="tl-text">${(a.texto || "").replace(/</g,"&lt;")}</div>
     </div>`).join("") || vazio("Nenhuma atividade encontrada.");
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
     <td class="num">${n.valor_fmt}</td><td>${n.ultima_atividade||""}</td></tr>`).join("")
    || `<tr><td colspan='6'>${vazio("Nenhuma negociação.")}</td></tr>`;
}

// ===== RELATORIOS =====
const graficos = {};
function desenhar(id, config) {
  if (graficos[id]) graficos[id].destroy();
  graficos[id] = new Chart(document.getElementById(id), config);
}

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
    `<tr><td>${v.vendedor}</td><td>${v.cargo||"—"}</td><td class="num">${v.abertas}</td><td class="num">${v.ganhas}</td><td class="num">${v.perdidas}</td><td class="num">${v.conversao}%</td></tr>`).join("");

  if (typeof Chart === "undefined") return; // sem internet para carregar a biblioteca

  // Funil por etapa (barras horizontais, uma cor só — a marca)
  desenhar("g-funil", {
    type: "bar",
    data: { labels: d.por_etapa.map(e => e.etapa),
      datasets: [{ label: "Abertas", data: d.por_etapa.map(e => e.quantidade),
        backgroundColor: HAI.azul, hoverBackgroundColor: HAI.azulEscuro,
        borderRadius: 5, borderSkipped: "start", maxBarThickness: 22 }] },
    options: { indexAxis: "y", responsive: true,
      plugins: { legend: { display: false } }, scales: eixos(true) },
  });

  // Ganhas x Perdidas x Abertas (rosca fina com total no centro)
  const total = g.ganhas + g.perdidas + g.abertas;
  document.getElementById("donut-total").textContent = total.toLocaleString("pt-BR");
  document.getElementById("donut-rotulo").textContent = "negociações";
  desenhar("g-status", {
    type: "doughnut",
    data: { labels: ["Ganhas","Perdidas","Abertas"],
      datasets: [{ data: [g.ganhas, g.perdidas, g.abertas],
        backgroundColor: [HAI.ok, HAI.erro, HAI.azul],
        borderColor: "#fff", borderWidth: 2, hoverOffset: 4 }] },
    options: { responsive: true, cutout: "72%",
      layout: { padding: 6 },  // folga p/ o hoverOffset não cortar a fatia na borda
      plugins: { legend: { position: "bottom",
        labels: { usePointStyle: true, pointStyle: "circle", boxWidth: 6, padding: 14 } } } },
    // Mantém o número central alinhado ao centro REAL da rosca,
    // qualquer que seja a altura da legenda.
    plugins: [{
      id: "centroRosca",
      afterLayout(c) {
        const el = document.querySelector(".donut-center");
        if (el) el.style.transform =
          "translateY(" + (((c.chartArea.top + c.chartArea.bottom) / 2) - (c.height / 2)) + "px)";
      },
    }],
  });

  // Abertas por vendedor (barra horizontal, uma cor só)
  desenhar("g-vendedor", {
    type: "bar",
    data: { labels: d.por_vendedor.map(v => v.vendedor),
      datasets: [{ label: "Abertas", data: d.por_vendedor.map(v => v.abertas),
        backgroundColor: HAI.azul, hoverBackgroundColor: HAI.azulEscuro,
        borderRadius: 5, borderSkipped: "start", maxBarThickness: 22 }] },
    options: { indexAxis: "y", responsive: true,
      plugins: { legend: { display: false } }, scales: eixos(true) },
  });

  // Criadas por mês (linha fina com área a 10%)
  desenhar("g-mes", {
    type: "line",
    data: { labels: d.por_mes.map(m => m.mes),
      datasets: [{ label: "Criadas", data: d.por_mes.map(m => m.quantidade),
        borderColor: HAI.azul, borderWidth: 2, tension: .3,
        backgroundColor: "rgba(22,96,143,.10)", fill: true,
        pointRadius: 0, pointHoverRadius: 5, pointHitRadius: 24,
        pointBackgroundColor: HAI.azul, pointBorderColor: "#fff", pointBorderWidth: 2 }] },
    options: { responsive: true, interaction: { mode: "index", intersect: false },
      plugins: { legend: { display: false } }, scales: eixos(false) },
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
    alvo.innerHTML = `<h3>${esc(b.titulo)}</h3>${vazio(esc(b.vazio))}`;
    return;
  }
  // Colunas com número (a partir da 2ª) alinham à direita
  const numerica = b.linhas[0].map((c, i) => i > 0 && b.linhas.every(ln => !isNaN(parseFloat(String(ln[i]).replace(/[R$%.\s]/g, "").replace(",", ".")))));
  const cab = b.colunas.map((c, i) => `<th${numerica[i] ? ' class="num"' : ""}>${esc(c)}</th>`).join("");
  const corpo = b.linhas.map(ln => `<tr>${ln.map((c, i) => `<td${numerica[i] ? ' class="num"' : ""}>${esc(c)}</td>`).join("")}</tr>`).join("");
  alvo.innerHTML = `<h3>${esc(b.titulo)}</h3>
    <div class="tabela-wrap"><table class="tabela"><thead><tr>${cab}</tr></thead><tbody>${corpo}</tbody></table></div>`;
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
  // Se a aba de perguntas estiver aberta, recarrega na hora (senão os botões
  // ficariam "mortos" até o usuário trocar de aba e voltar).
  if (abaAtiva === "perguntas") carregarPerguntas();
}, 5 * 60 * 1000);
