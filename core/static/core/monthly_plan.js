/* Early init dei <select> di Materialize */
(function initMaterializeSelectsEarly() {
  function init() {
    try {
      if (!window.M || !M.FormSelect) return;
      document.querySelectorAll('select').forEach(el => {
        if (!M.FormSelect.getInstance(el)) {
          M.FormSelect.init(el);
        }
      });
    } catch (e) {
      console.warn('Init early FormSelect fallita:', e);
    }
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }
})();

/* Script principale ShiftPlanner */
(function () {
  "use strict";

  // Namespace & helper
  const ShiftPlanner = window.ShiftPlanner || (window.ShiftPlanner = {});
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  // --- Palette pastello per mansione con più varietà ---
  const PROF_COLORS = new Map();

  function hash32(str){
    let h = 2166136261 >>> 0;
    for (let i=0;i<str.length;i++){ h ^= str.charCodeAt(i); h = Math.imul(h, 16777619); }
    return h >>> 0;
  }

  function colorForProfession(key) {
    if (!key) return null;
    const k = String(key).trim().toLowerCase();
    if (PROF_COLORS.has(k)) return PROF_COLORS.get(k);

    // Colori marcati ma leggibili su testo nero
    const h = hash32(k);
    const hue = h % 360;
    const sat = 45 + (h % 25);      // 45–70%
    const light = 78 + (h % 8);     // 78–85%
    const col = `hsl(${hue} ${sat}% ${light}%)`;

    PROF_COLORS.set(k, col);
    return col;
  }

  // Tooltip lazy
  function initTooltipsLazy(maxMs = 3000) {
    const start = Date.now();
    (function tick() {
      if (window.M && M.Tooltip) {
        try { M.Tooltip.init(document.querySelectorAll('.tooltipped')); } catch (_) {}
        return;
      }
      if (Date.now() - start > maxMs) return;
      setTimeout(tick, 80);
    })();
  }

  // CSRF
  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
  }

  // --- Persistenza scroll tra reload della pagina ---
  const SCROLL_KEY = 'monthly_plan_scroll';

  function saveScrollPosition() {
    try {
      const wrapper = document.querySelector('.grid-wrapper');
      const payload = {
        windowY: window.scrollY || window.pageYOffset || 0,
        wrapperY: wrapper ? wrapper.scrollTop : null,
        wrapperX: wrapper ? wrapper.scrollLeft : null,
      };
      sessionStorage.setItem(SCROLL_KEY, JSON.stringify(payload));
    } catch (e) {
      console.warn('Impossibile salvare scroll:', e);
    }
  }

  function restoreScrollPosition() {
    try {
      const raw = sessionStorage.getItem(SCROLL_KEY);
      if (!raw) return;
      sessionStorage.removeItem(SCROLL_KEY);

      const data = JSON.parse(raw);
      requestAnimationFrame(() => {
        if (typeof data.windowY === 'number') {
          window.scrollTo(0, data.windowY);
        }
        const wrapper = document.querySelector('.grid-wrapper');
        if (wrapper && typeof data.wrapperY === 'number') {
          wrapper.scrollTop = data.wrapperY;
        }
        if (wrapper && typeof data.wrapperX === 'number') {
          wrapper.scrollLeft = data.wrapperX;
          const topScroll = document.getElementById('grid-scroll-top');
          if (topScroll) topScroll.scrollLeft = data.wrapperX;
        }
      });
    } catch (e) {
      console.warn('Impossibile ripristinare scroll:', e);
    }
  }

  // --- Persistenza filtri tra reload ---
  function saveFilters() {
    try {
      localStorage.setItem("filter_prof", document.getElementById("filter-prof")?.value || "");
      localStorage.setItem("filter_emp", document.getElementById("filter-emp")?.value || "");
    } catch (e) {
      console.warn('Impossibile salvare filtri:', e);
    }
  }

  function restoreFilters() {
    try {
      const fp = document.getElementById("filter-prof");
      const fe = document.getElementById("filter-emp");

      const savedProf = localStorage.getItem("filter_prof") || "";
      const savedEmp  = localStorage.getItem("filter_emp")  || "";

      if (fp) fp.value = savedProf;
      if (fe) fe.value = savedEmp;
    } catch (e) {
      console.warn('Impossibile ripristinare filtri:', e);
    }
  }

  // --- Festività Italia + Pasqua/Lunedì dell'Angelo ---
  function easterDate(year){
    // Algoritmo Meeus/Jones/Butcher
    const a = year % 19;
    const b = Math.floor(year/100);
    const c = year % 100;
    const d = Math.floor(b/4);
    const e = b % 4;
    const f = Math.floor((b+8)/25);
    const g = Math.floor((b - f + 1)/3);
    const h = (19*a + b - d - g + 15) % 30;
    const i = Math.floor(c/4);
    const k = c % 4;
    const l = (32 + 2*e + 2*i - h - k) % 7;
    const m = Math.floor((a + 11*h + 22*l)/451);
    const month = Math.floor((h + l - 7*m + 114)/31); // 3=Marzo, 4=Aprile
    const day   = ((h + l - 7*m + 114) % 31) + 1;
    return new Date(year, month-1, day);
  }
  function addDays(d, n){ const x=new Date(d); x.setDate(x.getDate()+n); return x; }

  function isItalianHoliday(y, m, d){
    const fixed = new Set([
      `${y}-01-01`, // Capodanno
      `${y}-01-06`, // Epifania
      `${y}-04-25`, // Liberazione
      `${y}-05-01`, // Lavoro
      `${y}-06-02`, // Repubblica
      `${y}-08-15`, // Ferragosto
      `${y}-11-01`, // Ognissanti
      `${y}-12-08`, // Immacolata
      `${y}-12-25`, // Natale
      `${y}-12-26`  // Santo Stefano
    ]);
    const easter = easterDate(y);
    const easterISO = easter.toISOString().slice(0,10);
    const easterMonISO = addDays(easter,1).toISOString().slice(0,10);
    const iso = `${y}-${String(m).padStart(2,'0')}-${String(d).padStart(2,'0')}`;
    return fixed.has(iso) || iso === easterISO || iso === easterMonISO;
  }

  // -------------------------------
  // Config/refs bootstrap
  // -------------------------------
  document.addEventListener("DOMContentLoaded", () => {
    // Modal note
    if (window.M && M.Modal) {
      const noteModalElem = $("#noteModal");
      if (noteModalElem) {
        M.Modal.init(noteModalElem, { dismissible: true });
      }

      const notifyModalElem = $("#notifyConfirmModal");
      if (notifyModalElem) {
        M.Modal.init(notifyModalElem, { dismissible: true });
      }
    }

    const wrapper = $(".grid-wrapper");
    if (!wrapper) return;

    const planId = Number(wrapper.dataset.planId);
    const year = Number(wrapper.dataset.year);
    const month = Number(wrapper.dataset.month);

    const state = {
      planId,
      year,
      month,
      days: 0,
      selected: new Set(),
      isMouseDown: false,
      // refs
      grid: $("#grid"),
      gridHead: $("#grid-head"),
      gridBody: $("#grid tbody"),
      topScroll: $("#grid-scroll-top"),
      topInner: $("#grid-scroll-inner"),
      noteModal: $("#noteModal"),
      noteInput: $("#noteInput"),
      noteCellLabel: $("#noteCellLabel"),
      noteSaveBtn: $("#noteSaveBtn"),
      employeeSel: $("#employee"),
      shiftSel: $("#shift"),
      noteToolbarInput: $("#note"),
      applyBtn: $("#apply"),
      clearBtn: $("#clear"),
      notifyBtn: $("#notify"),
      // csrf
      csrftoken: getCookie("csrftoken"),
    };

    // bootstrap page
    initGrid(state)
      .then(() => {
        // Ripristina eventuali filtri salvati prima di inizializzare i filtri
        restoreFilters();

        initScrollSync(state);
        initSelection(state);
        initAutoScroll(state);
        initFilter(state);
        initEmployeeFilterLive();
        initApply(state);
        initClear(state);
        initNotify(state);
        initNoteEditing(state);
        // 3) Forza l'applicazione dei filtri ripristinati
        const fp = document.getElementById("filter-prof");
        if (fp && fp.value) {
          fp.dispatchEvent(new Event("input", { bubbles: true }));
        }

        const fe = document.getElementById("filter-emp");
        if (fe && fe.value) {
          fe.dispatchEvent(new Event("input", { bubbles: true }));
        }

        // 4) Ripristina posizione di scroll dopo che la griglia e i filtri sono in stato finale
        restoreScrollPosition();
      })
      .catch(() => {
        if (window.M?.toast) M.toast({ html: "Errore inizializzazione", classes: "red" });
        else console.error("Errore inizializzazione");
      });
  });


  // -------------------------------
  // Init & render griglia
  // -------------------------------
  async function initGrid(state) {
    const { planId, gridHead, gridBody, year, month } = state;

    const res = await fetch(`/api/plans/${planId}/grid/`, { credentials: "same-origin" });
    if (!res.ok) throw new Error("grid fetch failed");
    const data = await res.json();
    state.days = data.days;

    // Header con flag giorno
    const dayFlags = {}; // i -> { saturday, sunday, holiday }
    const weekdayFmt = new Intl.DateTimeFormat("it-IT", { weekday: "short" });
    for (let i = 1; i <= state.days; i++) {
      const th = document.createElement("th");
      const date = new Date(year, month - 1, i);
      const wd = weekdayFmt.format(date);
      const dow = date.getDay(); // 0=Dom, 6=Sab
      const isSun = (dow === 0);
      const isSat = (dow === 6);
      const isHol = isItalianHoliday(year, month, i);

      th.innerHTML = `<div class="day-num">${i}</div><div class="day-label">${wd}</div>`;
      if (isSun) th.classList.add("sunday");
      if (isSat) th.classList.add("saturday");
      if (isHol) th.classList.add("holiday");

      dayFlags[i] = { saturday:isSat, sunday:isSun, holiday:isHol };
      gridHead.appendChild(th);
    }

    // Corpo
    data.rows.forEach((row) => {
      const tr = document.createElement("tr");

      const th = document.createElement("th");
      th.textContent = row.profession;
      tr.appendChild(th);

      // Colore riga per mansione
      const isSpacer = !!row.spacer;
      const rowKey = row.profession || "";
      const rowBg  = isSpacer ? null : colorForProfession(rowKey);

      if (isSpacer) {
        tr.classList.add("spacer-row");
        th.classList.add("spacer-head");
      } else if (rowBg) {
        th.style.backgroundColor = rowBg;
      }

      for (let i = 1; i <= state.days; i++) {
        const cellData = row[String(i)] || {};
        const td = document.createElement("td");
        td.className = "cell";
        td.dataset.professionId = row.profession_id;
        td.dataset.day = i;

        // Sabato/Domenica/Festività: SOLO sulle celle del giorno
        const f = dayFlags[i];
        if (f?.saturday) td.classList.add("saturday");
        if (f?.sunday)   td.classList.add("sunday");
        if (f?.holiday)  td.classList.add("holiday");

        // Colore riga per mansione
        if (isSpacer) {
          td.classList.add("spacer-cell");
        } else if (rowBg) {
          td.style.backgroundColor = rowBg;
        }

        // contenuto + dataset utili
        const name = cellData.employee_name || "";
        const shiftLabel = cellData.shift_label || "";
        const text = name ? name + (shiftLabel ? ` (${shiftLabel})` : "") : "";

        td.dataset.employeeId = cellData.employee_id || "";
        td.dataset.notes = cellData.notes || "";
        td.dataset.name = name;
        td.dataset.shiftLabel = shiftLabel;

        if (cellData.has_note) {
          const tooltipText = (cellData.notes || "").replace(/"/g, "&quot;");
          td.innerHTML = `
            <span>${text}</span>
            <i class="material-icons tiny tooltipped"
               data-position="bottom"
               data-tooltip="${tooltipText}">sticky_note_2</i>
          `;
        } else {
          td.textContent = text;
        }

        tr.appendChild(td);
      }
      gridBody.appendChild(tr);
    });

    // tooltip su note
    initTooltipsLazy();
  }

  // -------------------------------
  // Scroll sync (barra top + wrapper)
  // -------------------------------
  function initScrollSync(state) {
    const { topScroll, topInner, grid } = state;
    if (!topScroll || !topInner || !grid) return;

    function syncTopWidth() {
      requestAnimationFrame(() => {
        topInner.style.width = grid.scrollWidth + "px";
      });
    }
    syncTopWidth();
    window.addEventListener("resize", syncTopWidth);

    topScroll.addEventListener("scroll", () => {
      grid.parentElement.scrollLeft = topScroll.scrollLeft;
    });
    grid.parentElement.addEventListener("scroll", () => {
      topScroll.scrollLeft = grid.parentElement.scrollLeft;
    });
  }

  // -------------------------------
  // Selezione celle (click & drag)
  // -------------------------------
  function initSelection(state) {
    const { selected } = state;

    document.addEventListener("mousedown", (e) => {
      if (e.target.classList.contains("cell")) state.isMouseDown = true;
    });
    document.addEventListener("mouseup", () => {
      state.isMouseDown = false;
    });

    $$("#grid td.cell").forEach((td) => {
      td.addEventListener("mousedown", (e) => {
        selected.clear();
        $$("#grid td.cell.selected").forEach((x) => x.classList.remove("selected"));
        selected.add(`${td.dataset.professionId}#${td.dataset.day}`);
        td.classList.add("selected");
        e.preventDefault();
      });
      td.addEventListener("mouseenter", () => {
        if (!state.isMouseDown) return;
        selected.add(`${td.dataset.professionId}#${td.dataset.day}`);
        td.classList.add("selected");
      });
    });
  }

  // -------------------------------
  // Contenitore scrollabile (auto-scroll durante drag)
  // -------------------------------
  function initAutoScroll(state) {
    const wrapper = state.grid.closest('.grid-wrapper');
    if (!wrapper) return;

    const EDGE = 40;
    const MAX_SPEED = 28;
    let rafId = null;
    let mouseX = 0, mouseY = 0;
    let active = false;

    function onMouseMove(e) {
      mouseX = e.clientX;
      mouseY = e.clientY;
    }

    function step() {
      if (!active) { rafId = null; return; }

      const rect = wrapper.getBoundingClientRect();
      let dx = 0, dy = 0;

      // Orizzontale
      if (mouseX < rect.left + EDGE) {
        dx = -Math.min(MAX_SPEED, (rect.left + EDGE - mouseX));
      } else if (mouseX > rect.right - EDGE) {
        dx =  Math.min(MAX_SPEED, (mouseX - (rect.right - EDGE)));
      }
      // Verticale
      if (mouseY < rect.top + EDGE) {
        dy = -Math.min(MAX_SPEED, (rect.top + EDGE - mouseY));
      } else if (mouseY > rect.bottom - EDGE) {
        dy =  Math.min(MAX_SPEED, (mouseY - (rect.bottom - EDGE)));
      }

      if (dx !== 0 || dy !== 0) {
        wrapper.scrollLeft += dx;
        wrapper.scrollTop  += dy;

        // Se hai la scrollbar superiore sincronizzata, allineala
        const topScroll = document.getElementById('grid-scroll-top');
        if (topScroll) topScroll.scrollLeft = wrapper.scrollLeft;
      }

      rafId = requestAnimationFrame(step);
    }

    // Attiva solo quando stai selezionando (mouse premuto)
    wrapper.addEventListener('mousedown', (e) => {
      if (e.target && e.target.classList.contains('cell')) {
        active = true;
        document.addEventListener('mousemove', onMouseMove);
        if (!rafId) rafId = requestAnimationFrame(step);
      }
    });

    // Ferma quando rilasci o esci dalla finestra
    function stop() {
      active = false;
      document.removeEventListener('mousemove', onMouseMove);
      if (rafId) { cancelAnimationFrame(rafId); rafId = null; }
    }
    document.addEventListener('mouseup', stop);
    window.addEventListener('blur', stop);
    wrapper.addEventListener('mouseleave', () => {
      // non fermiamo subito: potresti voler uscire di poco mentre scorri
    });
  }

  // -------------------------------
  // Filtro professioni (colonna 0)
  // -------------------------------
  function initFilter(state) {
    const input = $("#filter-prof");
    const clearBtn = $("#filter-clear");
    const countEl = $("#filter-count");
    const tbody = $("#grid tbody");
    if (!input || !tbody) return;

    function normalize(s) {
      return (s || "")
        .toLowerCase()
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .trim();
    }

    function applyFilter() {
      const q = normalize(input.value);
      const rows = tbody.rows;
      let shown = 0;

      if (!q) {
        for (let i = 0; i < rows.length; i++) rows[i].style.display = "";
        if (countEl) countEl.textContent = "Mostrate: tutte";
        return;
      }

      for (let i = 0; i < rows.length; i++) {
        const tr = rows[i];
        const firstCell = tr.cells[0];
        const text = firstCell ? firstCell.textContent : "";
        const ok = normalize(text).includes(q);
        tr.style.display = ok ? "" : "none";
        if (ok) shown++;
      }
      if (countEl) countEl.textContent = `Mostrate: ${shown}/${rows.length}`;
    }

    let t;
    input.addEventListener("input", () => {
      clearTimeout(t);
      t = setTimeout(applyFilter, 120);
    });
    if (clearBtn) {
      clearBtn.addEventListener("click", () => {
        input.value = "";
        applyFilter();
        input.focus();
      });
    }
    applyFilter();
  }

  // --- Filtro dipendenti (live) ---
  function initEmployeeFilterLive() {
    const input   = document.getElementById('filter-emp');
    const clearBtn= document.getElementById('filter-emp-clear');
    const countEl = document.getElementById('filter-emp-count');
    const tbody   = document.querySelector('#grid tbody');
    if (!input || !tbody) return;

    const normalize = (s) =>
      (s || '')
        .toLowerCase()
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .trim();

    function applyFilter() {
      const q = normalize(input.value);
      const rows = tbody.rows;
      let shown = 0;

      if (!q) {
        for (let i = 0; i < rows.length; i++) rows[i].style.display = '';
        if (countEl) countEl.textContent = 'Mostrate: tutte';
        return;
      }

      for (let i = 0; i < rows.length; i++) {
        const tr = rows[i];
        let match = false;

        // scorri TUTTE le celle dati (salta la 1a che è la professione)
        for (let c = 1; c < tr.cells.length; c++) {
          const td = tr.cells[c];
          // usiamo il dataset.name messo a render, più robusto del textContent
          const empName = (td && td.dataset && td.dataset.name) ? td.dataset.name : td.textContent;
          if (normalize(empName).includes(q)) { match = true; break; }
        }

        tr.style.display = match ? '' : 'none';
        if (match) shown++;
      }

      if (countEl) countEl.textContent = `Mostrate: ${shown}/${rows.length}`;
    }

    let t;
    input.addEventListener('input', () => {
      clearTimeout(t);
      t = setTimeout(applyFilter, 120);
    });

    if (clearBtn) {
      clearBtn.addEventListener('click', () => {
        input.value = '';
        applyFilter();
        input.focus();
      });
    }
    applyFilter();
  }

  // -------------------------------
  // APPLY (assegnazione)
  // -------------------------------
  function initApply(state) {
    const { applyBtn, employeeSel, shiftSel, noteToolbarInput, selected, csrftoken, planId, year, month } = state;
    if (!applyBtn) return;

    applyBtn.addEventListener("click", async () => {
      const employeeId = employeeSel.value;
      if (!employeeId) return M.toast({ html: "Seleziona un lavoratore", classes: "orange" });
      const shiftId = shiftSel.value || null;
      if (!shiftId) return M.toast({ html: "Seleziona un turno", classes: "orange" });
      const note = (noteToolbarInput?.value || "").trim();

      const cells = Array.from(selected).map((k) => {
        const [p, d] = k.split("#");
        const dd = String(Number(d)).padStart(2, "0");
        const mm = String(month).padStart(2, "0");
        return { profession_id: Number(p), date: `${year}-${mm}-${dd}` };
      });
      if (!cells.length) return M.toast({ html: "Seleziona almeno una cella", classes: "orange" });

      const resp = await fetch(`/api/plans/${planId}/bulk_assign/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...(csrftoken ? {'X-CSRFToken': csrftoken} : {}) },
        credentials: 'same-origin',
        body: JSON.stringify({
          employee_id: Number(employeeId),
          shift_type_id: shiftId ? Number(shiftId) : null,
          cells,
          note,
        })
      });

      if (resp.status === 409) {
        const js = await resp.json().catch(() => ({}));
        const conflicts = js.conflicts || [];

        if (conflicts.length) {
          const employeeName = $("#employee")?.selectedOptions?.[0]?.textContent || "Lavoratore";
          const dateFmt = new Intl.DateTimeFormat("it-IT", { day: "2-digit", month: "2-digit", year: "numeric" });

          let html = `<br>Conflitti:</br>${employeeName}<br>`;
          conflicts.forEach(c => {
            const d = new Date(c.date);
            const dStr = dateFmt.format(d);
            const shift = c.shift_label ? `${c.shift_label}` : "(nessun turno indicato)";
            html += `${c.profession}<br>${shift}<br>${dStr}<br><br>`;
          });

          return M.toast({ html, classes: "red", displayLength: 8000 });
        }

        return M.toast({ html: "Conflitto su date selezionate.", classes: "red" });
      }

      if (!resp.ok) {
        let msg = "Errore applicazione";
        try {
          const js = await resp.json();
          if (js.detail) msg = js.detail;
          if (js.skipped && js.skipped.length) {
            const lines = js.skipped.slice(0, 8).map(s => `${s.date}: ${s.reason}`);
            msg += "<br>" + lines.join("<br>");
          }
          if (js.errors && js.errors.length) {
            const lines = js.errors.slice(0, 8).map(e => JSON.stringify(e));
            msg += "<br>" + lines.join("<br>");
          }
        } catch (_) {}
        return M.toast({ html: msg, classes: "red", displayLength: 8000 });
      }

      // Salva posizione di scroll e filtri prima del reload
      saveScrollPosition();
      saveFilters();
      location.reload();
    });
  }

  // -------------------------------
  // CLEAR (rimozione assegnazioni)
  // -------------------------------
  function initClear(state) {
    const { clearBtn, selected, csrftoken, planId, year, month } = state;
    if (!clearBtn) return;

    clearBtn.addEventListener("click", async () => {
      if (!selected.size) return M.toast({ html: "Seleziona almeno una cella", classes: "orange" });
      if (!confirm("Rimuovere le assegnazioni dalle celle selezionate?")) return;

      const cells = Array.from(selected).map((k) => {
        const [p, d] = k.split("#");
        const dd = String(Number(d)).padStart(2, "0");
        const mm = String(month).padStart(2, "0");
        return { profession_id: Number(p), date: `${year}-${mm}-${dd}` };
      });

      const resp = await fetch(`/api/plans/${planId}/bulk_clear/`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...(csrftoken ? { "X-CSRFToken": csrftoken } : {}) },
        credentials: "same-origin",
        body: JSON.stringify({ cells }),
      });
      if (!resp.ok) return M.toast({ html: "Errore rimozione", classes: "red" });

      // Salva posizione di scroll e filtri prima del reload
      saveScrollPosition();
      saveFilters();
      location.reload();
    });
  }

  // -------------------------------
  // EXPORT CSV destinatari notify (Europe/Rome)
  // -------------------------------
  function downloadNotifyRecipientsCSV(js, planId) {
    function zonedIso(ts = new Date(), timeZone = 'Europe/Rome') {
      const dtf = new Intl.DateTimeFormat('it-IT', {
        timeZone,
        year: 'numeric', month: '2-digit', day: '2-digit',
        hour: '2-digit', minute: '2-digit', second: '2-digit',
        hour12: false,
        timeZoneName: 'shortOffset'
      });
      const parts = Object.fromEntries(dtf.formatToParts(ts).map(p => [p.type, p.value]));
      let off = (parts.timeZoneName || '').replace('GMT', '').replace('UTC', '');
      const m = off.match(/^([+-])?(\d{1,2})(?::?(\d{2}))?$/);
      if (m) {
        const sign = m[1] || '+';
        const hh = String(m[2]).padStart(2, '0');
        const mm = String(m[3] || '0').padStart(2, '0');
        off = `${sign}${hh}:${mm}`;
      } else {
        off = '+00:00';
      }
      const Y = parts.year, M = parts.month, D = parts.day;
      const h = parts.hour, i = parts.minute, s = parts.second;
      return `${Y}-${M}-${D}T${h}:${i}:${s}${off}`;
    }

    const sentAt = zonedIso(new Date(), 'Europe/Rome');

    const rows = [
      ['sent_at_europe_rome'],
      [sentAt],
      [],
      ['recipient_full_name']
    ];
    (js.recipients || []).forEach(name => rows.push([name]));

    const csv = rows.map(r => r.map(v => `"${String(v).replace(/"/g, '""')}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    const safeTs = sentAt.slice(0,19).replace(/[:T]/g, '-');
    a.href = url;
    a.download = `notify_recipients_planID_${planId}_date_${safeTs}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  // -------------------------------
  // NOTIFY (invio email)
  // -------------------------------
  function initNotify(state) {
    const { notifyBtn, csrftoken, planId } = state;
    if (!notifyBtn) return;

    const modalElem = document.getElementById("notifyConfirmModal");
    const confirmBtn = document.getElementById("notifyConfirmBtn");
    const cancelBtn  = document.getElementById("notifyCancelBtn");

    if (!modalElem || !confirmBtn) return;

    const modal = M.Modal.getInstance(modalElem) || M.Modal.init(modalElem, { dismissible: true });

    async function doNotify() {
      const resp = await fetch(`/api/plans/${planId}/notify/`, {
        method: "POST",
        headers: csrftoken ? { "X-CSRFToken": csrftoken } : {},
        credentials: "same-origin",
      });
      if (!resp.ok) {
        M.toast({ html: "Errore invio notifiche", classes: "red" });
        return;
      }
      const js = await resp.json().catch(() => ({}));

      M.toast({
        html: `
          Dipendenti registrati: ${js.total_employees_registered ?? 0}<br>
          Dipendenti totali nel piano: ${js.total_in_plan ?? 0}<br>
          Con email valida: ${js.with_email ?? 0}<br>
          Da notificare ora: ${js.prepared ?? 0}<br>
          Email inviate: ${js.sent ?? 0}<br>
          ${js.recipients?.length ? "<hr>" + js.recipients.join(", ") : ""}
        `,
        displayLength: 8000
      });

      downloadNotifyRecipientsCSV(js, planId);
    }

    // Click su "Invia notifiche" → apri modal
    notifyBtn.addEventListener("click", () => {
      modal.open();
    });

    // Conferma nel modal → chiude modal e fa notify
    confirmBtn.addEventListener("click", async () => {
      modal.close();
      await doNotify();
    });

  }


  // -------------------------------
  // NOTE editing (dblclick + modal + salvataggio)
  // -------------------------------
  function initNoteEditing(state) {
    const { noteModal, noteInput, noteCellLabel, noteSaveBtn, csrftoken, planId, year, month } = state;
    if (!noteModal || !noteInput || !noteCellLabel || !noteSaveBtn) return;
    const modal = M.Modal.getInstance(noteModal);

    let currentCell = null;

    function renderCell(td) {
      const name = td.dataset.name || "";
      const shiftLabel = td.dataset.shiftLabel || "";
      const text = name ? name + (shiftLabel ? ` (${shiftLabel})` : "") : "";
      const notes = td.dataset.notes || "";

      if (notes) {
        const tooltipText = notes.replace(/"/g, "&quot;");
        td.innerHTML = `
          <span>${text}</span>
          <i class="material-icons tiny tooltipped"
             data-position="bottom"
             data-tooltip="${tooltipText}">sticky_note_2</i>
        `;
        const icon = td.querySelector(".tooltipped");
        if (icon) M.Tooltip.init(icon);
      } else {
        td.textContent = text;
      }
    }

    $$("#grid td.cell").forEach((td) => {
      td.addEventListener("dblclick", () => {
        if (!td.dataset.employeeId) {
          return M.toast({
            html: "Nessuna assegnazione in questa cella. Assegna un lavoratore prima di aggiungere una nota.",
            classes: "orange",
          });
        }
        currentCell = td;
        noteInput.value = td.dataset.notes || "";
        const lbl = document.querySelector("label[for='noteInput']");
        if (lbl) lbl.classList.add("active");
        const profName = td.parentElement.querySelector("th")?.textContent || "";
        const day = td.dataset.day;
        noteCellLabel.textContent = `${profName} — Giorno ${day}`;
        modal.open();
      });
    });

    noteSaveBtn.addEventListener("click", async () => {
      if (!currentCell) return;
      const note = (noteInput.value || "").trim();

      const body = {
        profession_id: Number(currentCell.dataset.professionId),
        date: `${year}-${String(month).padStart(2, "0")}-${String(currentCell.dataset.day).padStart(2, "0")}`,
        note,
      };

      const resp = await fetch(`/api/plans/${planId}/set_note/`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...(csrftoken ? { "X-CSRFToken": csrftoken } : {}) },
        credentials: "same-origin",
        body: JSON.stringify(body),
      });
      if (!resp.ok) return M.toast({ html: "Errore salvataggio nota", classes: "red" });

      const js = await resp.json().catch(() => ({}));
      currentCell.dataset.notes = js.notes || "";
      renderCell(currentCell);
      modal.close();
      M.toast({ html: js.notes ? "Nota salvata" : "Nota rimossa" });
    });
  }
})();
