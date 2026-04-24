const state = { signals: [], selected: null, level: "", search: "" };

const $ = (id) => document.getElementById(id);
const fmt = (value, digits = 2) => Number(value ?? 0).toFixed(digits);
const esc = (value) => String(value ?? "").replace(/[&<>'"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[c]));

async function api(path, options = {}) {
  const response = await fetch(path, options);
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

async function loadStatus() {
  const status = await api("/api/status");
  const summary = status.summary || {};
  $("statusCards").innerHTML = `
    <div class="card"><div>Versión</div><div class="value">${esc(status.version)}</div></div>
    <div class="card"><div>IA</div><div class="value">${esc(status.ai_provider)}</div></div>
    <div class="card"><div>Señales</div><div class="value">${summary.total_signals || 0}</div></div>
    <div class="card"><div>Nivel 3</div><div class="value">${summary.level_3 || 0}</div></div>
  `;
}

async function loadSignals() {
  const params = new URLSearchParams({ limit: "150" });
  if (state.level) params.set("level", state.level);
  if (state.search) params.set("search", state.search);
  state.signals = await api(`/api/signals?${params.toString()}`);
  renderTable();
}

function renderTable() {
  if (!state.signals.length) {
    $("tableWrap").innerHTML = `<p class="muted">No hay señales guardadas que coincidan con el filtro.</p>`;
    return;
  }
  $("tableWrap").innerHTML = `
    <table>
      <thead>
        <tr><th>Nivel</th><th>Activo</th><th>Score</th><th>Calidad</th><th>Consenso</th><th>Precio</th><th>R/R</th></tr>
      </thead>
      <tbody>
        ${state.signals.map((s, i) => `
          <tr onclick="selectSignal(${i})">
            <td><span class="badge level-${s.level}">N${s.level}</span></td>
            <td><strong>${esc(s.ticker)}</strong><br><span class="muted">${esc(s.name)}</span></td>
            <td>${fmt(s.score_total)}</td>
            <td class="quality-${esc(s.data_quality)}">${esc(s.data_quality)}</td>
            <td>${esc(s.consensus_label)}</td>
            <td>${fmt(s.price, 4)}</td>
            <td>${fmt(s.rr)}</td>
          </tr>`).join("")}
      </tbody>
    </table>
  `;
}

window.selectSignal = function(index) {
  state.selected = state.signals[index];
  renderDetail(state.selected);
};

function renderDetail(s) {
  const warnings = (s.warnings || []).map(w => `<li class="warning">${esc(w)}</li>`).join("") || "<li>Sin advertencias críticas.</li>";
  const sources = (s.data_sources || []).map(src => `
    <tr><td>${esc(src.source)}</td><td>${src.ok ? "OK" : "ERROR"}</td><td>${src.price ?? "-"}</td><td>${esc(src.timestamp || "-")}</td><td>${esc(src.error || "")}</td></tr>
  `).join("");

  $("detailBox").innerHTML = `
    <h3>${esc(s.ticker)} · ${esc(s.name)}</h3>
    <p>${esc(s.verdict)}</p>
    <div class="grid2">
      <div class="metric"><span>Precio</span>${fmt(s.price, 4)}</div>
      <div class="metric"><span>Stop</span>${fmt(s.stop, 4)}</div>
      <div class="metric"><span>Objetivo</span>${fmt(s.target, 4)}</div>
      <div class="metric"><span>R/R</span>${fmt(s.rr)}</div>
      <div class="metric"><span>Macro</span>${fmt(s.score_macro)}</div>
      <div class="metric"><span>Sector</span>${fmt(s.score_sector)}</div>
    </div>
    <h4>Factores</h4>
    <p>Tendencia ${s.trend_score}/3 · Volumen ${s.volume_score}/3 · Precio ${s.price_score}/3 · Momentum ${s.momentum_score}/3 · Riesgo ${s.risk_score}/3</p>
    <h4>Advertencias</h4><ul>${warnings}</ul>
    <h4>Fuentes</h4>
    <table><thead><tr><th>Fuente</th><th>Estado</th><th>Precio</th><th>Timestamp</th><th>Error</th></tr></thead><tbody>${sources}</tbody></table>
    <h4>Análisis IA</h4>
    <pre id="aiBox">${esc(s.ai_summary)}</pre>
    <div class="actions">
      <button onclick="analyzeSelected()">Analizar con IA</button>
      <button class="secondary" onclick="evaluateSelected()">Evaluar resultado</button>
    </div>
  `;
}

window.analyzeSelected = async function() {
  if (!state.selected) return;
  $("aiBox").textContent = "Analizando con IA...";
  const result = await api(`/api/signals/${state.selected.id}/analyze`, { method: "POST" });
  state.selected.ai_summary = result.ai_summary;
  $("aiBox").textContent = result.ai_summary;
};

window.evaluateSelected = async function() {
  if (!state.selected) return;
  const result = await api(`/api/signals/${state.selected.id}/evaluate`, { method: "POST" });
  alert(`${result.status}: ${result.note}`);
};

async function runScan() {
  $("scanBtn").disabled = true;
  $("scanBtn").textContent = "Escaneando...";
  try {
    await api("/api/scan", { method: "POST" });
    await refresh();
  } finally {
    $("scanBtn").disabled = false;
    $("scanBtn").textContent = "Ejecutar escaneo";
  }
}

async function searchAssets() {
  const q = $("searchInput").value.trim();
  state.search = q;
  await loadSignals();
  if (!q) { $("assetMatches").innerHTML = ""; return; }
  const assets = await api(`/api/assets/search?q=${encodeURIComponent(q)}`);
  $("assetMatches").innerHTML = assets.map(a => `
    <div class="asset-card">
      <strong>${esc(a.ticker)}</strong> · ${esc(a.name)}<br>
      <span class="muted">${esc(a.region)} / ${esc(a.sector)} / ${esc(a.thesis_type)}</span><br><br>
      <button onclick="analyzeNow('${esc(a.ticker)}')">Analizar ahora</button>
    </div>
  `).join("") || `<p class="muted">Sin coincidencias en universo global.</p>`;
}

window.analyzeNow = async function(ticker) {
  const result = await api(`/api/assets/${encodeURIComponent(ticker)}/analyze-now`, { method: "POST" });
  state.selected = result;
  renderDetail(result);
};

async function refresh() {
  await loadStatus();
  await loadSignals();
}

$("scanBtn").addEventListener("click", runScan);
$("refreshBtn").addEventListener("click", refresh);
$("searchBtn").addEventListener("click", searchAssets);
$("searchInput").addEventListener("keydown", (e) => { if (e.key === "Enter") searchAssets(); });
$("levelFilter").addEventListener("change", async (e) => { state.level = e.target.value; await loadSignals(); });

refresh().catch(err => { $("tableWrap").innerHTML = `<pre>${esc(err.message)}</pre>`; });
