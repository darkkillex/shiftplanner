document.addEventListener('DOMContentLoaded', function() {
  const sel = document.getElementById('company');
  if (window.M && M.FormSelect) M.FormSelect.init(sel);

  const startEl = document.getElementById('start');
  const endEl   = document.getElementById('end');
  const noteEl  = document.getElementById('preset-note');

  let chShift = null, chPreposto = null;

  function renderChart(canvasId, cfg) {
    const el = document.getElementById(canvasId);
    if (!el) return;
    const prev = canvasId === 'ch-shift' ? chShift : chPreposto;
    if (prev) prev.destroy();
    const chart = new Chart(el, {
      type: 'bar',
      data: cfg,
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        plugins: { legend: { position: 'top' } },
        scales: { y: { beginAtZero: true, ticks: { precision: 0 } } }
      }
    });
    if (canvasId === 'ch-shift') chShift = chart; else chPreposto = chart;
  }

  function fillTable(tbodyId, rows, map) {
    const tb = document.querySelector(`#${tbodyId} tbody`);
    tb.innerHTML = '';
    rows.forEach(r => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${map.label(r)}</td>
        <td>${map.assign(r)}</td>
        <td>${map.employees(r)}</td>
      `;
      tb.appendChild(tr);
    });
  }

  function currentParams(extra={}) {
    const p = {
      company_id: sel.value || "",
      start: startEl.value || "",
      end: endEl.value || ""
    };
    return Object.assign(p, extra);
  }

  async function fetchAndRender(params = {}) {
    const u = new URL('/analytics/summary/', window.location.origin);
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') u.searchParams.set(k, v);
    });

    const res = await fetch(u.toString(), { credentials: 'same-origin' });
    if (!res.ok) return;
    const data = await res.json();

    // KPI principali
    document.getElementById('kpi-assign-turno').textContent = data.kpi.assignments_turno;

    // Dipendenti: "assegnati di totale"
    document.getElementById('kpi-emp').textContent =
      `${data.kpi.employees_assigned} di ${data.kpi.employees_total}`;

    // --- KPI esclusioni: Ferie, Permessi, ecc. ---
    const row = document.getElementById('kpi-excluded-row');
    if (row) {
      row.innerHTML = '';
      (data.kpi.excluded_breakdown || []).forEach(item => {
        const col = document.createElement('div');
        col.className = 'col s12 m6 l3';
        col.innerHTML = `
          <div class="card">
            <div class="card-content center">
              <div class="grey-text text-darken-1">${item.label}</div>
              <div style="font-size:2rem;font-weight:600">${item.count}</div>
            </div>
          </div>`;
        row.appendChild(col);
      });
    }

    // Grafici
    renderChart('ch-shift', data.charts.per_shift);
    renderChart('ch-preposto', data.charts.preposto);

    // Tabelle
    fillTable('tbl-shift', data.tables.per_shift, {
      label: r => r["shift_type__label"] || r["shift_type__code"] || "—",
      assign: r => r.assignments,
      employees: r => r.employees,
    });
    fillTable('tbl-preposto', data.tables.preposto, {
      label: r => r["profession__name"],
      assign: r => r.assignments,
      employees: r => r.employees,
    });

    // Sincronizza date effettive e nota preset
    startEl.value = data.scope.start;
    endEl.value = data.scope.end;
    const compTxt = sel.value ? sel.options[sel.selectedIndex].text : 'tutte le aziende';
    noteEl.textContent = `Intervallo ${data.scope.start} → ${data.scope.end} • Filtro: ${compTxt}`;
  }

  // Debounce per filtro live
  let t = null;
  function debouncedFetch() {
    clearTimeout(t);
    t = setTimeout(() => fetchAndRender(currentParams()), 250);
  }

  // Preset in alto: NON resettano l'azienda, applicano subito
  document.querySelectorAll('[data-preset]').forEach(b => {
    b.addEventListener('click', () => {
      fetchAndRender(currentParams({ preset: b.dataset.preset }));
    });
  });

  // Filtro live: cambia azienda/date => aggiorna dopo 250ms
  sel.addEventListener('change', debouncedFetch);
  startEl.addEventListener('input', debouncedFetch);
  endEl.addEventListener('input', debouncedFetch);

  // Primo load
  fetchAndRender(currentParams());
});