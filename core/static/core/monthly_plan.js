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


// Inizializza i tooltip quando M.Tooltip è pronto
  function initTooltipsLazy(maxMs = 3000) {
  const start = Date.now();
  (function tick() {
    if (window.M && M.Tooltip) {
      try { M.Tooltip.init(document.querySelectorAll('.tooltipped')); } catch (_) {}
      return;
    }
    if (Date.now() - start > maxMs) return; // smetti di riprovare
    setTimeout(tick, 80);
  })();
}

    // Helper CSRF
  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
  }

  // -------------------------------
  // Config/refs bootstrap
  // -------------------------------
  document.addEventListener("DOMContentLoaded", () => {
    // Inizializza Modal (i select li abbiamo già inizializzati sopra)
    const modalElem = $("#noteModal");
    if (modalElem && window.M && M.Modal) {
      M.Modal.init(modalElem, { dismissible: true });
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
        initScrollSync(state);
        initSelection(state);
        initAutoScroll(state);
        initFilter(state);
        initEmployeeFilterLive();
        initApply(state);
        initClear(state);
        initNotify(state);
        initNoteEditing(state);
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

    // Header
    const weekdayFmt = new Intl.DateTimeFormat("it-IT", { weekday: "short" });
    for (let i = 1; i <= state.days; i++) {
      const th = document.createElement("th");
      const date = new Date(year, month - 1, i);
      const wd = weekdayFmt.format(date);
      th.innerHTML = `<div>${i}</div><div class="day-label">${wd}</div>`;
      if (date.getDay() === 0) th.classList.add("holiday");
      gridHead.appendChild(th);
    }

    // Corpo
    data.rows.forEach((row) => {
      const tr = document.createElement("tr");

      const th = document.createElement("th");
      th.textContent = row.profession;
      tr.appendChild(th);

      for (let i = 1; i <= state.days; i++) {
        const cellData = row[String(i)] || {};
        const td = document.createElement("td");
        td.className = "cell";
        td.dataset.professionId = row.profession_id;
        td.dataset.day = i;

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

    // init tooltip per eventuali note "latenti" nella comparsa
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
    // Contenitore scrollabile(click & drag)
    // -------------------------------

  function initAutoScroll(state) {
    const wrapper = state.grid.closest('.grid-wrapper'); //
    if (!wrapper) return;

    const EDGE = 40;               // px dal bordo che attiva lo scroll
    const MAX_SPEED = 28;          // px per frame (~60fps)
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
      // lasciamo step proseguire se active === true
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

  // --- FILTRO DIPENDENTI (live) ---
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
          if (normalize(empName).includes(q)) {
            match = true;
            break;
          }
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
            // prendiamo il nome del lavoratore selezionato dalla tendina
            const employeeName = $("#employee")?.selectedOptions?.[0]?.textContent || "Lavoratore";

            // formatter per data in italiano (es. 5 ottobre 2025)
            const dateFmt = new Intl.DateTimeFormat("it-IT", { day: "2-digit", month: "2-digit", year: "numeric" });

            let html = `<br>Conflitti:</br>${employeeName}<br>`;
            conflicts.forEach(c => {
              const d = new Date(c.date); // c.date è ISO
              const dStr = dateFmt.format(d);
              const shift = c.shift_label ? `${c.shift_label}` : "(nessun turno indicato)";
              html += `${c.profession}<br>${shift}<br>${dStr}<br><br>`;
            });

            return M.toast({ html, classes: "red", displayLength: 8000 });
          }

        return M.toast({ html: "Conflitto su date selezionate.", classes: "red" });
      }

      if (!resp.ok) {
        return M.toast({ html: "Errore applicazione", classes: "red" });
      }
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
      location.reload();
    });
  }

  // -------------------------------
  // NOTIFY (invio email)
  // -------------------------------
  function initNotify(state) {
    const { notifyBtn, csrftoken, planId } = state;
    if (!notifyBtn) return;
    notifyBtn.addEventListener("click", async () => {
      if (!confirm("Inviare email a TUTTI i dipendenti con assegnazioni in questo piano?")) return;
      const resp = await fetch(`/api/plans/${planId}/notify/`, {
        method: "POST",
        headers: csrftoken ? { "X-CSRFToken": csrftoken } : {},
        credentials: "same-origin",
      });
      if (!resp.ok) return M.toast({ html: "Errore invio notifiche", classes: "red" });
      const js = await resp.json().catch(() => ({}));
      M.toast({ html: `Email inviate: ${js.sent ?? js.prepared ?? 0}` });
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
