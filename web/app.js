/**
 * ============================================================================
 * LÓGICA DE FRONTEND JS - LAVANDERÍA INDUSTRIAL (VERSIÓN INICIAL ESTABLE)
 * ============================================================================
 */

const API_BASE = '/api';

const state = {
  stock: [],
  alertas: [],
  historial: [],
  categoryFilter: 'all',
  searchQuery: ''
};

document.addEventListener('DOMContentLoaded', () => {
  initApp();
  setupThemeToggle();
});

function initApp() {
  fetchStock();
  fetchHistorial();
}

function switchMainView(viewId, ev) {
  const views = document.querySelectorAll('.view-section');
  views.forEach(v => v.classList.remove('active'));

  const targetView = document.getElementById(viewId);
  if (targetView) targetView.classList.add('active');

  const navTabs = document.querySelectorAll('.nav-tab');
  navTabs.forEach(tab => tab.classList.remove('active'));

  if (ev && ev.target) {
    const btn = ev.target.closest('.nav-tab');
    if (btn) btn.classList.add('active');
  } else {
    const activeTab = document.querySelector(`.nav-tab[data-view="${viewId}"]`);
    if (activeTab) activeTab.classList.add('active');
  }
}

function renderWashingTimeline(programa, stoneVariante) {
  const timelineEl = document.getElementById('washing-timeline');
  if (!timelineEl) return;

  const allSteps = [
    { key: 'DESENGOME', name: '1. Desengome', icon: '💧' },
    { key: 'STONE', name: stoneVariante === 'STONE_ENZIMA' ? '2. Stone (Polvo)' : '2. Stone (Líquida)', icon: '🌾' },
    { key: 'BLEACH', name: '3. Bleach', icon: '🧪' },
    { key: 'NEUTRALIZADO', name: '4. Neutralizado', icon: '⚗️' },
    { key: 'BLANQUEO', name: '5. Blanqueo', icon: '✨' }
  ];

  const rutas = {
    PROCESO_COMPLETO: ['DESENGOME', 'STONE', 'BLEACH', 'NEUTRALIZADO', 'BLANQUEO'],
    PROCESO_STONE_COMPLETO: ['DESENGOME', 'STONE', 'NEUTRALIZADO'],
    PROCESO_BLANQUEO_TOTAL: ['DESENGOME', 'BLEACH', 'NEUTRALIZADO', 'BLANQUEO'],
    DESENGOME: ['DESENGOME'],
    STONE: ['STONE'],
    STONE_ENZIMA: ['STONE'],
    STONE_LIQUIDA: ['STONE'],
    BLEACH: ['BLEACH'],
    NEUTRALIZADO: ['NEUTRALIZADO'],
    BLANQUEO: ['BLANQUEO']
  };

  const activeKeys = rutas[programa] || ['DESENGOME'];

  timelineEl.innerHTML = allSteps.map((step, idx) => {
    const isActive = activeKeys.includes(step.key);
    const arrowHtml = idx < allSteps.length - 1 ? '<span class="timeline-arrow">➔</span>' : '';
    return `
      <div class="timeline-step ${isActive ? 'active' : ''}">
        <div class="timeline-step-icon">${step.icon}</div>
        <span class="timeline-step-label">${step.name}</span>
      </div>
      ${arrowHtml}
    `;
  }).join('');
}

async function fetchStock() {
  try {
    const res = await fetch(`${API_BASE}/stock`);
    const data = await res.json();
    if (data.exito) {
      state.stock = data.stock || [];
      state.alertas = data.alertas || [];

      updateStockStatsSummary();
      renderKPIs();
      renderAlertBanner();
      calculateLiveDosage();
      populateSelects();
    }
  } catch (err) {
    showToast('danger', 'Error de conexión al obtener el stock de inventario.');
  }
}

function updateStockStatsSummary() {
  const totalEl = document.getElementById('stat-total-insumos');
  const optimoEl = document.getElementById('stat-stock-optimo');
  const alertasEl = document.getElementById('stat-alertas-count');

  const total = state.stock.length;
  const alertas = state.alertas.length;
  const optimo = Math.max(0, total - alertas);

  if (totalEl) totalEl.textContent = total;
  if (optimoEl) optimoEl.textContent = optimo;
  if (alertasEl) alertasEl.textContent = alertas;
}

function filterStockCategory(cat, ev) {
  state.categoryFilter = cat;

  const tabBtns = document.querySelectorAll('#stock-category-tabs .tab-btn');
  tabBtns.forEach(btn => btn.classList.remove('active'));

  if (ev && ev.target) {
    ev.target.classList.add('active');
  } else {
    const activeBtn = document.querySelector(`#stock-category-tabs .tab-btn[data-cat="${cat}"]`);
    if (activeBtn) activeBtn.classList.add('active');
  }

  renderKPIs();
}

function handleStockFilter() {
  const input = document.getElementById('search-stock');
  state.searchQuery = input ? input.value.trim().toLowerCase() : '';
  renderKPIs();
}

function renderKPIs() {
  const container = document.getElementById('kpi-cards-container');
  if (!container) return;

  container.innerHTML = '';

  const nombresBonitos = {
    humectante_g: { label: 'Humectante', icon: '💧', maxEstimado: 20000, cat: 'pretratamiento' },
    dispersante_g: { label: 'Dispersante', icon: '🌀', maxEstimado: 25000, cat: 'pretratamiento' },
    antiquiebre_g: { label: 'Anti-quiebre', icon: '🛡️', maxEstimado: 15000, cat: 'pretratamiento' },
    enzima_g: { label: 'Enzima (Polvo)', icon: '🌾', maxEstimado: 20000, cat: 'enzimas' },
    enzima_liquida_ml: { label: 'Enzima Líquida', icon: '🧪', maxEstimado: 20000, cat: 'enzimas' },
    acido_acetico_ml: { label: 'Ácido Acético', icon: '⚗️', maxEstimado: 15000, cat: 'enzimas' },
    cloro_ml: { label: 'Cloro Concentrado', icon: '🧪', maxEstimado: 20000, cat: 'blanqueo' },
    soda_g: { label: 'Soda Cáustica', icon: '⚡', maxEstimado: 30000, cat: 'blanqueo' },
    bisulfito_g: { label: 'Bisulfito de Sodio', icon: '🧂', maxEstimado: 20000, cat: 'neutralizado' },
    oxalico_g: { label: 'Ácido Oxálico', icon: '⚗️', maxEstimado: 15000, cat: 'neutralizado' },
    jabon_g: { label: 'Jabón', icon: '🧼', maxEstimado: 50000, cat: 'blanqueo' },
    secuestrante_g: { label: 'Secuestrante', icon: '🛡️', maxEstimado: 15000, cat: 'blanqueo' },
    peroxido_ml: { label: 'Peróxido de Hidrógeno', icon: '💥', maxEstimado: 25000, cat: 'blanqueo' },
    blanqueador_g: { label: 'Blanqueador Óptico', icon: '✨', maxEstimado: 20000, cat: 'blanqueo' },
    suavizante_g: { label: 'Suavizante Textil', icon: '🌸', maxEstimado: 30000, cat: 'neutralizado' }
  };

  const filteredItems = state.stock.filter(item => {
    const meta = nombresBonitos[item.insumo] || { label: item.insumo, cat: 'all' };
    const matchesCategory = 
      state.categoryFilter === 'all' ||
      (state.categoryFilter === 'alertas' && item.cantidad <= item.stock_minimo) ||
      meta.cat === state.categoryFilter;

    const matchesSearch = 
      !state.searchQuery ||
      (item.nombre_display || meta.label || item.insumo).toLowerCase().includes(state.searchQuery);

    return matchesCategory && matchesSearch;
  });

  if (filteredItems.length === 0) {
    container.innerHTML = `
      <div style="grid-column: 1 / -1; text-align: center; color: var(--text-muted); padding: 2.5rem;">
        🔍 No se encontraron insumos químicos en esta categoría o búsqueda.
      </div>
    `;
    return;
  }

  filteredItems.forEach(item => {
    const meta = nombresBonitos[item.insumo] || { label: item.insumo, icon: '📦', maxEstimado: 1000 };
    const esStockBajo = item.cantidad <= item.stock_minimo;
    
    const maxVal = Math.max(item.stock_minimo * 2.5, item.cantidad * 1.1, meta.maxEstimado);
    const porcentaje = Math.min(Math.max((item.cantidad / maxVal) * 100, 5), 100);
    const barClass = esStockBajo ? (item.cantidad === 0 ? 'critical' : 'warning') : 'normal';
    const badgeClass = esStockBajo ? 'badge-danger' : 'badge-success';
    const badgeText = esStockBajo ? 'Bajo' : 'Óptimo';

    const decimals = (item.unidad === 'L' || item.unidad === 'l' || item.unidad === 'ml') ? 1 : 0;
    const cantFormateada = formatNumber(item.cantidad, decimals);
    const minFormateado = formatNumber(item.stock_minimo, decimals);

    const cardHtml = `
      <div class="kpi-card">
        <div class="kpi-card-header">
          <span class="kpi-title">${meta.icon} ${escapeHtml(item.nombre_display || meta.label)}</span>
          <span class="badge ${badgeClass}">${badgeText}</span>
        </div>
        
        <div class="kpi-body">
          <div>
            <span class="kpi-value">${cantFormateada}</span>
            <span class="kpi-unit">${escapeHtml(item.unidad)}</span>
          </div>
        </div>

        <div class="progress-bar-track">
          <div class="progress-bar-fill ${barClass}" style="width: ${porcentaje}%"></div>
        </div>

        <div class="kpi-footer">
          <span>Mín: <strong>${minFormateado} ${item.unidad}</strong></span>
          <button class="btn btn-secondary btn-sm" onclick="openReabastecerModal('${item.insumo}')">+ Reabastecer</button>
        </div>
      </div>
    `;
    container.innerHTML += cardHtml;
  });
}

function renderAlertBanner() {
  const container = document.getElementById('alert-banner-container');
  if (!container) return;

  if (!state.alertas || state.alertas.length === 0) {
    container.innerHTML = '';
    return;
  }

  const detalles = state.alertas.map(a => {
    const decimals = (a.unidad === 'L' || a.unidad === 'l' || a.unidad === 'ml') ? 1 : 0;
    return `${a.nombre_display || a.insumo} (${formatNumber(a.cantidad, decimals)} ${a.unidad})`;
  }).join(', ');

  container.innerHTML = `
    <div class="alert-banner">
      <div>
        <strong>⚠️ Atención: Stock Bajo o Agotado:</strong> ${detalles}. Reabastezca para continuar operando sin interrupciones.
      </div>
    </div>
  `;
}

function populateSelects() {
  const selectReabastecer = document.getElementById('select-insumo-reabastecer');
  const selectMinimo = document.getElementById('select-insumo-minimo');

  if (selectReabastecer) {
    selectReabastecer.innerHTML = state.stock.map(item => `
      <option value="${item.insumo}">${escapeHtml(item.nombre_display)} (${item.unidad})</option>
    `).join('');
  }

  if (selectMinimo) {
    selectMinimo.innerHTML = state.stock.map(item => `
      <option value="${item.insumo}">${escapeHtml(item.nombre_display)} (${item.unidad})</option>
    `).join('');
    handleSelectMinimoInsumoChange();
  }
}

function handleProgramaChange() {
  const selectPrograma = document.getElementById('select-programa');
  const groupStoneVariante = document.getElementById('group-stone-variante');

  if (selectPrograma && groupStoneVariante) {
    if (selectPrograma.value === 'STONE') {
      groupStoneVariante.classList.remove('hidden');
    } else {
      groupStoneVariante.classList.add('hidden');
    }
  }
  calculateLiveDosage();
}

function calculateLiveDosage() {
  const inputPeso = document.getElementById('input-peso');
  const selectPrograma = document.getElementById('select-programa');
  const selectStoneVariante = document.getElementById('select-stone-variante');
  const previewContainer = document.getElementById('dosage-preview-container');
  const badgeEl = document.getElementById('dosage-status-badge');

  if (!inputPeso || !previewContainer) return;

  const peso = parseFloat(inputPeso.value);
  let programa = selectPrograma ? selectPrograma.value : 'PROCESO_COMPLETO';

  const stoneVar = selectStoneVariante ? selectStoneVariante.value : 'STONE_LIQUIDA';
  renderWashingTimeline(programa, stoneVar);

  if (programa === 'STONE') {
    programa = stoneVar;
  }

  const recetas = {
    DESENGOME: [
      { key: 'humectante_g', label: 'Humectante', icon: '💧', unit: 'g', pct: 0.25 },
      { key: 'dispersante_g', label: 'Dispersante', icon: '🌀', unit: 'g', pct: 0.35 },
      { key: 'antiquiebre_g', label: 'Anti-quiebre', icon: '🛡️', unit: 'g', pct: 0.20 }
    ],
    STONE_ENZIMA: [
      { key: 'enzima_g', label: 'Enzima (Polvo)', icon: '🌾', unit: 'g', pct: 0.80 }
    ],
    STONE_LIQUIDA: [
      { key: 'enzima_liquida_ml', label: 'Enzima Líquida', icon: '🧪', unit: 'ml', pct: 0.50 },
      { key: 'acido_acetico_ml', label: 'Ácido Acético', icon: '⚗️', unit: 'ml', pct: 0.25 }
    ],
    BLEACH: [
      { key: 'cloro_ml', label: 'Cloro Concentrado', icon: '🧪', unit: 'ml', pct: 0.50 },
      { key: 'soda_g', label: 'Soda Cáustica', icon: '⚡', unit: 'g', pct: 0.25 }
    ],
    NEUTRALIZADO: [
      { key: 'humectante_g', label: 'Humectante', icon: '💧', unit: 'g', pct: 0.20 },
      { key: 'dispersante_g', label: 'Dispersante', icon: '🌀', unit: 'g', pct: 0.25 },
      { key: 'bisulfito_g', label: 'Bisulfito de Sodio', icon: '🧂', unit: 'g', pct: 0.35 },
      { key: 'oxalico_g', label: 'Ácido Oxálico', icon: '⚗️', unit: 'g', pct: 0.25 }
    ],
    BLANQUEO: [
      { key: 'jabon_g', label: 'Jabón', icon: '🧼', unit: 'g', pct: 0.40 },
      { key: 'dispersante_g', label: 'Dispersante', icon: '🌀', unit: 'g', pct: 0.25 },
      { key: 'secuestrante_g', label: 'Secuestrante', icon: '🛡️', unit: 'g', pct: 0.20 },
      { key: 'soda_g', label: 'Soda Cáustica', icon: '⚡', unit: 'g', pct: 0.35 },
      { key: 'peroxido_ml', label: 'Peróxido de Hidrógeno', icon: '💥', unit: 'ml', pct: 0.50 },
      { key: 'blanqueador_g', label: 'Blanqueador Óptico', icon: '✨', unit: 'g', pct: 0.65 }
    ]
  };

  const stonePaso = selectStoneVariante ? selectStoneVariante.value : 'STONE_LIQUIDA';
  const rutas = {
    PROCESO_COMPLETO: ['DESENGOME', stonePaso, 'BLEACH', 'NEUTRALIZADO', 'BLANQUEO'],
    PROCESO_STONE_COMPLETO: ['DESENGOME', stonePaso, 'NEUTRALIZADO'],
    PROCESO_BLANQUEO_TOTAL: ['DESENGOME', 'BLEACH', 'NEUTRALIZADO', 'BLANQUEO']
  };

  const pasos = rutas[programa] || [programa];
  const aggregatedReceta = {};

  pasos.forEach(paso => {
    const list = recetas[paso] || [];
    list.forEach(item => {
      if (!aggregatedReceta[item.key]) {
        aggregatedReceta[item.key] = { ...item, pct: 0 };
      }
      aggregatedReceta[item.key].pct = parseFloat((aggregatedReceta[item.key].pct + item.pct).toFixed(2));
    });
  });

  const itemsReceta = Object.values(aggregatedReceta);

  if (isNaN(peso) || peso <= 0) {
    previewContainer.innerHTML = itemsReceta.map(item => `
      <div class="dosage-item">
        <span class="item-label">${item.icon} ${item.label} <small style="opacity:0.7">(${item.pct}%)</small></span>
        <span class="item-value">0 <small>${item.unit}</small></span>
      </div>
    `).join('');

    if (badgeEl) {
      badgeEl.className = 'badge badge-neutral';
      badgeEl.textContent = 'Ingrese peso';
    }
    return;
  }

  const stockDict = {};
  state.stock.forEach(item => stockDict[item.insumo] = item.cantidad);

  let todoOK = true;

  previewContainer.innerHTML = itemsReceta.map(item => {
    const cantCalc = peso * item.pct * 10.0;
    const req = (item.unit === 'ml' || item.unit === 'L') ? cantCalc.toFixed(1) : Math.round(cantCalc);

    const cantDisponible = stockDict[item.key] || 0;
    const hayStock = cantDisponible >= parseFloat(req);
    if (!hayStock) todoOK = false;

    return `
      <div class="dosage-item ${hayStock ? '' : 'insufficient-stock'}">
        <span class="item-label">${item.icon} ${item.label} <small style="opacity:0.75; font-size:0.75rem;">(${item.pct}% s.p.m.)</small></span>
        <span class="item-value">${formatNumber(req, item.unit === 'ml' || item.unit === 'L' ? 1 : 0)} <small>${item.unit}</small></span>
      </div>
    `;
  }).join('');

  if (badgeEl) {
    if (todoOK) {
      badgeEl.className = 'badge badge-success';
      badgeEl.textContent = 'Stock Suficiente ✅';
    } else {
      badgeEl.className = 'badge badge-danger';
      badgeEl.textContent = 'Stock Insuficiente ❌';
    }
  }
}

async function fetchHistorial(clienteFiltro) {
  try {
    const params = clienteFiltro ? `?cliente=${encodeURIComponent(clienteFiltro)}` : '';
    const res = await fetch(`${API_BASE}/historial${params}`);
    const data = await res.json();
    if (data.exito) {
      state.historial = data.historial || [];
      renderHistorial();
    }
  } catch (err) {
    showToast('danger', 'Error de conexión al obtener el historial de lotes.');
  }
}

function renderHistorial() {
  const tbody = document.getElementById('historial-tbody');
  if (!tbody) return;

  if (!state.historial || state.historial.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="8" style="text-align: center; color: var(--text-muted); padding: 2.5rem;">
          No se encontraron lotes en el historial.
        </td>
      </tr>
    `;
    return;
  }

  const nombresProgramas = {
    PROCESO_COMPLETO: 'Proceso Completo (5 Pasos)',
    PROCESO_STONE_COMPLETO: 'Ruta Stone Wash Completo',
    PROCESO_BLANQUEO_TOTAL: 'Ruta Blanqueo Total',
    DESENGOME: 'Paso 1: Desengome',
    STONE_ENZIMA: 'Paso 2: Stone (Enzima Polvo)',
    STONE_LIQUIDA: 'Paso 2: Stone (Enzima Líquida + Acético)',
    STONE: 'Paso 2: Stone',
    BLEACH: 'Paso 3: Bleach',
    NEUTRALIZADO: 'Paso 4: Neutralizado',
    BLANQUEO: 'Paso 5: Blanqueo Óptico'
  };

  const nombresInsumos = {
    humectante_g: { name: 'Humectante', unit: 'g' },
    dispersante_g: { name: 'Dispersante', unit: 'g' },
    antiquiebre_g: { name: 'Anti-quiebre', unit: 'g' },
    enzima_g: { name: 'Enzima (Polvo)', unit: 'g' },
    enzima_liquida_ml: { name: 'Enzima Líquida', unit: 'ml' },
    acido_acetico_ml: { name: 'Ácido Acético', unit: 'ml' },
    cloro_ml: { name: 'Cloro', unit: 'ml' },
    soda_g: { name: 'Soda Cáustica', unit: 'g' },
    bisulfito_g: { name: 'Bisulfito', unit: 'g' },
    oxalico_g: { name: 'Ácido Oxálico', unit: 'g' },
    jabon_g: { name: 'Jabón', unit: 'g' },
    detergente_g: { name: 'Jabón', unit: 'g' },
    secuestrante_g: { name: 'Secuestrante', unit: 'g' },
    peroxido_ml: { name: 'Peróxido', unit: 'ml' },
    blanqueador_g: { name: 'Blanqueador Óptico', unit: 'g' },
    suavizante_g: { name: 'Suavizante', unit: 'g' }
  };

  tbody.innerHTML = state.historial.map(row => {
    const esProcesado = row.estado === 'PROCESADO';
    const badgeClass = esProcesado ? 'badge-success' : 'badge-danger';

    const btnAnular = esProcesado
      ? `<button class="btn btn-danger-outline btn-sm" onclick="handleAnularLote('${row.id_lote}')">🚫 Anular</button>`
      : `<span style="font-size: 0.75rem; color: var(--text-muted);">Reintegrado</span>`;

    const programaKey = row.programa || 'DESENGOME';
    const programaText = nombresProgramas[programaKey] || programaKey;

    // Generar resumen dinámico de insumos consumidos
    let insumosStr = '';
    const dict = row.insumos_dict || {};
    const items = [];
    
    for (const [key, cant] of Object.entries(dict)) {
      if (cant > 0) {
        const spec = nombresInsumos[key] || { name: key, unit: '' };
        items.push(`${spec.name}: ${formatNumber(cant, spec.unit === 'ml' ? 1 : 0)} ${spec.unit}`);
      }
    }

    if (items.length > 0) {
      insumosStr = items.join(' • ');
    } else {
      insumosStr = 'Sin insumos registrados';
    }

    return `
      <tr>
        <td><strong>${row.fecha_hora}</strong></td>
        <td><code>${row.id_lote}</code></td>
        <td>${escapeHtml(row.cliente)}</td>
        <td><span class="badge badge-info">${escapeHtml(programaText)}</span></td>
        <td><strong>${(row.peso_kg || 0).toFixed(1)}</strong> kg</td>
        <td><small style="color: var(--text-secondary); font-weight: 500;">${escapeHtml(insumosStr)}</small></td>
        <td><span class="badge ${badgeClass}">${row.estado}</span></td>
        <td>${btnAnular}</td>
      </tr>
    `;
  }).join('');
}

async function handleRegistrarLote(event) {
  event.preventDefault();

  const idLoteInput = document.getElementById('input-id-lote');
  const clienteInput = document.getElementById('input-cliente');
  const programaSelect = document.getElementById('select-programa');
  const stoneVarianteSelect = document.getElementById('select-stone-variante');
  const pesoInput = document.getElementById('input-peso');

  const id_lote = idLoteInput.value.trim().toUpperCase();
  const cliente = clienteInput.value.trim();
  let programa = programaSelect ? programaSelect.value : 'DESENGOME';

  if (programa === 'STONE' && stoneVarianteSelect) {
    programa = stoneVarianteSelect.value;
  }

  const peso_kg = parseFloat(pesoInput.value);

  if (!id_lote || !cliente || isNaN(peso_kg) || peso_kg <= 0) {
    showToast('danger', 'Complete todos los campos con datos válidos.');
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/lotes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id_lote, cliente, peso_kg, programa })
    });

    const data = await res.json();

    if (data.exito) {
      showToast('success', `🎉 ${data.mensaje}`);
      document.getElementById('form-lote').reset();
      handleProgramaChange();
      fetchStock();
      fetchHistorial();
    } else {
      let msg = data.mensaje;
      if (data.faltantes && Object.keys(data.faltantes).length > 0) {
        msg += ' Faltan: ' + Object.entries(data.faltantes).map(([k, v]) => `${k}: ${v}`).join(', ');
      }
      showToast('danger', `❌ ${msg}`);
    }
  } catch (err) {
    showToast('danger', 'Error de red al procesar el lote.');
  }
}

async function handleAnularLote(id_lote) {
  if (!confirm(`¿Está seguro de anular el lote "${id_lote}"? Se reintegrarán el agua, detergente y suavizante al stock.`)) {
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/lotes/anular`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id_lote })
    });

    const data = await res.json();
    if (data.exito) {
      showToast('success', `✅ ${data.mensaje}`);
      fetchStock();
      fetchHistorial();
    } else {
      showToast('danger', `❌ ${data.mensaje}`);
    }
  } catch (err) {
    showToast('danger', 'Error de red al anular el lote.');
  }
}

function openReabastecerModal(insumo = '') {
  const select = document.getElementById('select-insumo-reabastecer');
  if (insumo && select) {
    select.value = insumo;
  }
  document.getElementById('modal-reabastecer').classList.remove('hidden');
}

function closeReabastecerModal() {
  document.getElementById('modal-reabastecer').classList.add('hidden');
}

async function handleReabastecer(event) {
  event.preventDefault();

  const insumo = document.getElementById('select-insumo-reabastecer').value;
  const cantidad = parseFloat(document.getElementById('input-cant-reabastecer').value);

  if (isNaN(cantidad) || cantidad <= 0) {
    showToast('danger', 'Ingrese una cantidad positiva.');
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/stock/reabastecer`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ insumo, cantidad })
    });

    const data = await res.json();
    if (data.exito) {
      showToast('success', `✅ ${data.mensaje}`);
      closeReabastecerModal();
      document.getElementById('input-cant-reabastecer').value = '';
      fetchStock();
    } else {
      showToast('danger', `❌ ${data.mensaje}`);
    }
  } catch (err) {
    showToast('danger', 'Error al reabastecer el stock.');
  }
}

function openMinimoModal() {
  document.getElementById('modal-minimo').classList.remove('hidden');
}

function closeMinimoModal() {
  document.getElementById('modal-minimo').classList.add('hidden');
}

function handleSelectMinimoInsumoChange() {
  const clave = document.getElementById('select-insumo-minimo').value;
  const item = state.stock.find(s => s.insumo === clave);
  if (item) {
    document.getElementById('input-edit-minimo').value = item.stock_minimo;
  }
}

async function handleGuardarMinimos(event) {
  event.preventDefault();

  const insumo = document.getElementById('select-insumo-minimo').value;
  const nuevo_minimo = parseFloat(document.getElementById('input-edit-minimo').value);

  try {
    const res = await fetch(`${API_BASE}/stock/minimo`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ insumo, nuevo_minimo })
    });

    const data = await res.json();
    if (data.exito) {
      showToast('success', 'Stock mínimo actualizado correctamente.');
      closeMinimoModal();
      fetchStock();
    } else {
      showToast('danger', `❌ ${data.mensaje}`);
    }
  } catch (err) {
    showToast('danger', 'Error al actualizar la configuración.');
  }
}

function handleFilterHistorial() {
  const val = document.getElementById('filter-cliente').value.trim();
  fetchHistorial(val);
}

function handleExportarCSV() {
  window.location.href = `${API_BASE}/exportar`;
  showToast('success', 'Generando y descargando historial CSV...');
}

function setupThemeToggle() {
  const btn = document.getElementById('theme-toggle-btn');
  if (!btn) return;

  const savedTheme = localStorage.getItem('lavanderia_theme');
  if (savedTheme === 'light') {
    document.body.classList.remove('dark-mode');
    document.body.classList.add('light-mode');
    btn.textContent = '☀️';
    btn.setAttribute('title', 'Cambiar a modo oscuro');
  } else {
    document.body.classList.remove('light-mode');
    document.body.classList.add('dark-mode');
    btn.textContent = '🌙';
    btn.setAttribute('title', 'Cambiar a modo claro');
  }

  btn.addEventListener('click', () => {
    const isLight = document.body.classList.contains('light-mode');
    if (isLight) {
      document.body.classList.remove('light-mode');
      document.body.classList.add('dark-mode');
      btn.textContent = '🌙';
      btn.setAttribute('title', 'Cambiar a modo claro');
      localStorage.setItem('lavanderia_theme', 'dark');
      showToast('info', '🌙 Modo Oscuro Activado');
    } else {
      document.body.classList.remove('dark-mode');
      document.body.classList.add('light-mode');
      btn.textContent = '☀️';
      btn.setAttribute('title', 'Cambiar a modo oscuro');
      localStorage.setItem('lavanderia_theme', 'light');
      showToast('info', '☀️ Modo Claro Activado');
    }
  });
}

function showToast(type, message) {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span>${message}</span>`;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

function formatNumber(num, decimals = 0) {
  const val = Number(num);
  const cleanVal = isNaN(val) ? 0 : val;
  return cleanVal.toLocaleString('es-CO', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  });
}

function escapeHtml(str) {
  return String(str || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
