/* =====================================================================
   Kairos — Report commessa
   Il server restituisce un dataset normalizzato (stesso formato sia dai
   piani Kairos sia dal file Excel esterno); qui si fanno solo filtri,
   aggregazioni e rendering.
   ===================================================================== */
(function () {
  "use strict";

  const CFG = JSON.parse(document.getElementById("rc-config").textContent);

  /* ------------------------------------------------------------------ costanti */
  const CAT_COLOR = {lavoro:"#0076A5", notte:"#6E3FB0", riposo:"#B0BEC5", ferie:"#1F9D6B",
                     formazione:"#D98A00", assenza:"#B3261E", spare:"#BF5A9A", anomalia:"#37474F"};
  const CAT_LABEL = {lavoro:"Turno di lavoro", notte:"Turno notte", riposo:"Riposo", ferie:"Ferie / permessi",
                     formazione:"Formazione", assenza:"Assenza", spare:"Spare", anomalia:"Anomalia nel file"};
  const MESI = ["Gennaio","Febbraio","Marzo","Aprile","Maggio","Giugno","Luglio","Agosto","Settembre","Ottobre","Novembre","Dicembre"];
  const DOW = ["Lun","Mar","Mer","Gio","Ven","Sab","Dom"];
  const QUICK = ["Preposto","Formazione","Coordinatore","Ponteggi","Front Office","Gas Free","HSE","Soccorritore",
                 "Magazzino","Ufficio","Delegato ai Lavori","Ambiente"];
  const isWork = c => c === "lavoro" || c === "notte";

  /* ------------------------------------------------------------------ stato */
  let DS = null;            // dataset grezzo dal server
  let REC = [];             // record espansi
  let PERSONE = [];         // [{i, nome, soc, ..., rec: []}]
  let MESI_PRESENTI = [];   // ['2026-01', ...]
  let FESTIVI = new Set();
  let PREPCASI = [];
  let SEL = null;           // indice persona selezionata
  let SCHEDA_MESE = "";     // filtro mese nella scheda
  let mansFilter = "", soloNote = false;
  let SRC = "kairos";
  let LAST_FILE = null;     // ultimo file Excel caricato (serve per l'import prescrizioni)
  let PI_CLEAR = false;
  const CHARTS = {};

  /* ------------------------------------------------------------------ util */
  const $ = id => document.getElementById(id);
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const norm = s => String(s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/['’]/g, " ");
  const fmtOre = v => (Math.round(v * 10) / 10).toLocaleString("it-IT") + " h";
  const ddmm = d => d.slice(8) + "/" + d.slice(5, 7);
  const dowOf = d => DOW[(new Date(d + "T00:00").getDay() + 6) % 7];
  const isWeekend = d => { const w = new Date(d + "T00:00").getDay(); return w === 0 || w === 6; };
  const meseLabel = m => MESI[+m.slice(5) - 1] + " " + m.slice(0, 4);
  const codeDesc = c => (DS.legend[c] && DS.legend[c].d) || c;
  const toast = (html, cls) => { if (window.M && M.toast) M.toast({html, classes: cls || ""}); else alert(html.replace(/<[^>]+>/g, "")); };
  function csrf() {
    const el = document.querySelector("[name=csrfmiddlewaretoken]");
    return el ? el.value : "";
  }
  function socChip(soc) {
    return `<span class="rc-chip soc-${esc(soc)}">${esc(soc || "?")}</span>`;
  }
  function meseOptions(sel, withAll, allLabel) {
    const cur = sel.value;
    sel.innerHTML = (withAll ? `<option value="">${allLabel || "Tutti i mesi"}</option>` : "") +
      MESI_PRESENTI.map(m => `<option value="${m}">${meseLabel(m)}</option>`).join("");
    if ([...sel.options].some(o => o.value === cur)) sel.value = cur;
  }
  function trunc(s, n) {
    s = String(s).trim(); if (s.length <= n) return s;
    const cut = s.slice(0, n), sp = cut.lastIndexOf(" ");
    return (sp > n * 0.55 ? cut.slice(0, sp) : cut) + "…";
  }
  function emptyBox(icon, text) {
    return `<div class="rc-empty"><i class="material-icons">${icon}</i>${text}</div>`;
  }

  /* ================================================================== FONTE DATI */
  function initSource() {
    const from = $("rcFrom"), to = $("rcTo");
    from.innerHTML = to.innerHTML = MESI.map((m, i) => `<option value="${i + 1}">${m}</option>`).join("");
    from.value = "1"; to.value = "12";
    from.addEventListener("change", () => { if (+to.value < +from.value) to.value = from.value; });
    to.addEventListener("change", () => { if (+from.value > +to.value) from.value = to.value; });

    document.querySelectorAll(".rc-source-switch button").forEach(b => b.addEventListener("click", () => {
      SRC = b.dataset.src;
      document.querySelectorAll(".rc-source-switch button").forEach(x => x.classList.toggle("on", x === b));
      $("rcSrcKairos").classList.toggle("rc-hide", SRC !== "kairos");
      $("rcSrcExcel").classList.toggle("rc-hide", SRC !== "excel");
    }));
    $("rcLoadKairos").addEventListener("click", loadKairos);
    $("rcYear").addEventListener("change", loadKairos);

    const fi = $("rcFile"), drop = $("rcDrop");
    fi.addEventListener("change", e => { if (e.target.files[0]) loadExcel(e.target.files[0]); fi.value = ""; });
    ["dragover", "dragenter"].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.add("hot"); }));
    ["dragleave", "drop"].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.remove("hot"); }));
    drop.addEventListener("drop", e => { const f = e.dataTransfer.files[0]; if (f) loadExcel(f); });
  }

  function busy(on) {
    $("rcProgress").classList.toggle("rc-hide", !on);
    $("rcLoadKairos").disabled = on;
  }

  async function fetchJson(url, opts) {
    const r = await fetch(url, Object.assign({credentials: "same-origin"}, opts || {}));
    let data = null;
    try { data = await r.json(); } catch (e) { /* risposta non JSON */ }
    if (!r.ok) throw new Error((data && data.detail) || `Errore ${r.status}`);
    return data;
  }

  let REQ = 0;   // solo l'ultima richiesta lanciata aggiorna la pagina
  async function loadKairos() {
    const q = new URLSearchParams({year: $("rcYear").value, from: $("rcFrom").value, to: $("rcTo").value});
    const my = ++REQ;
    busy(true);
    try {
      const ds = await fetchJson(CFG.urls.kairos + "?" + q);
      if (my === REQ) ingest(ds);
    } catch (e) {
      toast("Errore nel caricamento dei piani: " + esc(e.message), "red");
    } finally { busy(false); }
  }

  async function loadExcel(file) {
    if (!/\.(xlsm|xlsx)$/i.test(file.name)) { toast("Servono file .xlsm o .xlsx", "red"); return; }
    if (file.size > CFG.maxUploadMb * 1024 * 1024) { toast(`File troppo grande (massimo ${CFG.maxUploadMb} MB)`, "red"); return; }
    $("rcFname").textContent = file.name + " — lettura in corso (può richiedere 10-20 secondi)…";
    const fd = new FormData(); fd.append("file", file);
    const my = ++REQ;
    busy(true);
    try {
      const ds = await fetchJson(CFG.urls.excel, {method: "POST", body: fd, headers: {"X-CSRFToken": csrf()}});
      if (my !== REQ) return;
      LAST_FILE = file;
      ingest(ds);
      $("rcFname").textContent = file.name;
    } catch (e) {
      $("rcFname").textContent = "Trascina qui il piano turni (.xlsm / .xlsx)";
      toast(esc(e.message), "red");
    } finally { busy(false); }
  }

  /* ================================================================== INGEST */
  function ingest(ds) {
    DS = ds;
    const mans = ds.mans;
    PERSONE = ds.people.map((p, i) => ({
      i, nome: p.n, soc: p.soc || "", socFull: p.socFull || "", mail: p.mail || "", tel: p.tel || "",
      presc: p.presc || "", liv: p.liv || "", eid: p.eid, rec: []
    }));
    REC = ds.rec.map(r => {
      const p = PERSONE[r[0]];
      const o = {p: r[0], nome: p.nome, societa: p.soc || "?", data: r[1], code: r[2], cat: r[3], ore: r[4],
                 mansione: r[5] >= 0 ? mans[r[5]] : "", preposto: r[6] >= 0, prepPos: r[6] >= 0 ? mans[r[6]] : "",
                 nota: r[7] || "", autore: r[8] || "", area: r[9] || "", notaPos: r[10] || ""};
      p.rec.push(o);
      return o;
    });
    PREPCASI = ds.prep.map(c => ({data: c[0], turno: c[1], posizione: mans[c[2]] || "", riga: c[3],
                                  p: c[4], titolare: PERSONE[c[4]].nome, soc: PERSONE[c[4]].soc || "?", foglio: c[5]}));
    MESI_PRESENTI = ds.months;
    FESTIVI = new Set(ds.holidays);
    // gli indici cambiano a ogni caricamento: ritrova la persona selezionata per nome
    if (SEL !== null) {
      const prev = window.__rcSelName;
      const hit = PERSONE.find(p => p.nome === prev);
      SEL = hit ? hit.i : null;
    }

    renderStatus();
    if (!REC.length) {
      $("rcApp").classList.add("rc-hide");
      return;
    }
    $("rcApp").classList.remove("rc-hide");

    meseOptions($("rcMMese"), true);
    meseOptions($("rcPMese"), true);
    meseOptions($("rcCmMese"), true);
    meseOptions($("rcRpMese"), true, "Tutto il periodo");
    const socs = [...new Set(PERSONE.map(p => p.soc).filter(Boolean))].sort();
    $("rcCmSoc").innerHTML = `<option value="">${socs.length ? socs.join(" + ") : "Tutte le società"}</option>` +
      socs.map(s => `<option value="${esc(s)}">Solo ${esc(s)}</option>`).join("");
    const today = new Date().toISOString().slice(0, 7);
    SCHEDA_MESE = MESI_PRESENTI.includes(today) ? today : MESI_PRESENTI[MESI_PRESENTI.length - 1] || "";

    renderLista(); renderScheda(); renderChips(); renderMansione(); renderPreposti();
    renderDiag(); renderReport(); renderCommessa();
  }

  function renderStatus() {
    const s = DS.source;
    const icon = s.kind === "kairos" ? "storage" : "description";
    const bySoc = {};
    PERSONE.forEach(p => { if (p.rec.length) bySoc[p.soc || "?"] = (bySoc[p.soc || "?"] || 0) + 1; });
    const nPers = PERSONE.filter(p => p.rec.length).length;
    const socTxt = Object.keys(bySoc).sort().map(k => `<b>${bySoc[k]}</b> ${esc(k)}`).join(" / ");
    $("rcStatus").innerHTML = REC.length
      ? `<span class="rc-badge ${s.kind}"><i class="material-icons">${icon}</i>${esc(s.label)}</span>
         <span class="rc-stats"><b>${nPers}</b> dipendenti${socTxt ? ` (${socTxt})` : ""} ·
           <b>${MESI_PRESENTI.length}</b> mese/i · <b>${PREPCASI.length}</b> giornate da preposto ·
           <b>${REC.filter(r => r.nota).length}</b> note</span>
         <span class="rc-hint" style="margin-left:auto">${esc(s.detail || "")}</span>`
      : `<span class="rc-badge ${s.kind}"><i class="material-icons">${icon}</i>${esc(s.label)}</span>
         <span class="rc-hint">Nessun piano turni trovato per il periodo selezionato.</span>`;
  }

  /* ================================================================== TABS */
  const TABS = ["persona", "report", "mansione", "preposti", "commessa", "dati"];
  function initTabs() {
    document.querySelectorAll(".rc-tab").forEach(t => t.addEventListener("click", () => {
      document.querySelectorAll(".rc-tab").forEach(x => x.classList.toggle("on", x === t));
      TABS.forEach(k => $("tab-" + k).classList.toggle("rc-hide", k !== t.dataset.tab));
      if (t.dataset.tab === "report") renderReport();
      if (t.dataset.tab === "commessa") renderCommessa();
    }));
  }

  /* ================================================================== ELENCO */
  function renderLista() {
    const q = norm($("rcSearch").value).split(/\s+/).filter(Boolean);
    const list = PERSONE.filter(p => p.rec.length && q.every(t => norm(p.nome).includes(t)))
      .sort((a, b) => a.nome.localeCompare(b.nome, "it"));
    $("rcPCount").textContent = `(${list.length})`;
    $("rcPList").innerHTML = list.length
      ? list.map(p => `<div class="rc-pitem ${SEL === p.i ? "on" : ""}" data-i="${p.i}">
          <span>${esc(p.nome)}${p.presc ? '<i class="material-icons" title="Prescrizioni mediche presenti">medical_information</i>' : ""}</span>
          <span class="soc">${esc(p.soc)}</span></div>`).join("")
      : '<div class="rc-hint" style="padding:10px">Nessun dipendente trovato.</div>';
  }
  function selectPerson(i) {
    SEL = i; window.__rcSelName = PERSONE[i].nome; renderLista(); renderScheda();
    $("rcRpSel").value = String(i);
  }

  /* ================================================================== SCHEDA */
  function renderScheda() {
    const box = $("rcScheda");
    if (SEL === null) { box.innerHTML = emptyBox("person_search", "Seleziona un dipendente dall'elenco."); return; }
    const p = PERSONE[SEL];
    const rec = SCHEDA_MESE ? p.rec.filter(r => r.data.startsWith(SCHEDA_MESE)) : p.rec;
    const n = c => rec.filter(r => r.cat === c).length;
    const lav = rec.filter(r => isWork(r.cat));
    const weekend = lav.filter(r => isWeekend(r.data)).length;
    const festivi = lav.filter(r => FESTIVI.has(r.data)).length;
    const nPrep = rec.filter(r => r.preposto).length, nNote = rec.filter(r => r.nota).length;

    const agg = new Map();
    for (const r of rec) { if (!r.mansione) continue; if (!agg.has(r.mansione)) agg.set(r.mansione, []); agg.get(r.mansione).push(r.data); }
    const aggList = [...agg.entries()].sort((a, b) => b[1].length - a[1].length);

    const meseSel = `<select id="rcSchedaMese" class="browser-default" style="height:36px;border:1px solid var(--rc-line);border-radius:4px;width:auto">
      <option value="">Tutti i mesi</option>${MESI_PRESENTI.filter(m => p.rec.some(r => r.data.startsWith(m)))
        .map(m => `<option value="${m}" ${m === SCHEDA_MESE ? "selected" : ""}>${meseLabel(m)}</option>`).join("")}</select>`;

    let html = `
    <div class="rc-phead">
      <div>
        <h5>${esc(p.nome)}</h5>
        <div class="rc-meta">${socChip(p.soc)}${p.liv ? `<span>· ${esc(p.liv)}</span>` : ""}
          ${p.tel ? `<span>· ${esc(p.tel)}</span>` : ""}${p.mail ? `<span>· ${esc(p.mail)}</span>` : ""}</div>
      </div>
      <div class="rc-toolbar rc-noprint" style="margin:0">
        ${meseSel}
        <button class="btn-flat waves-effect" onclick="window.print()"><i class="material-icons left">print</i>Stampa</button>
        <button class="btn-flat waves-effect" data-export="persona"><i class="material-icons left">download</i>CSV</button>
      </div>
    </div>
    ${prescBox(p)}
    <div class="rc-pad" style="padding-bottom:0">
    <div class="rc-kpis">
      <div class="rc-kpi accent"><b>${lav.length}</b><span>Giorni lavorati</span></div>
      <div class="rc-kpi"><b>${n("notte")}</b><span>Di cui notte</span></div>
      <div class="rc-kpi"><b>${n("riposo")}</b><span>Riposi</span></div>
      <div class="rc-kpi"><b>${n("ferie")}</b><span>Ferie / permessi</span></div>
      <div class="rc-kpi"><b>${n("formazione")}</b><span>Formazione</span></div>
      <div class="rc-kpi"><b>${n("assenza")}</b><span>Altre assenze</span></div>
      <div class="rc-kpi"><b>${weekend}</b><span>Weekend lavorati</span></div>
      <div class="rc-kpi"><b>${festivi}</b><span>Festivi lavorati</span></div>
      <div class="rc-kpi"><b style="${nPrep ? "color:var(--c-ferie)" : ""}">${nPrep}</b><span>Giorni da preposto</span></div>
      <div class="rc-kpi note"><b style="${nNote ? "" : "color:inherit"}">${nNote}</b><span>Note in cella</span></div>
      ${n("anomalia") ? `<div class="rc-kpi"><b class="rc-warn">${n("anomalia")}</b><span>Anomalie nel file</span></div>` : ""}
    </div></div>`;

    for (const m of MESI_PRESENTI) {
      if (SCHEDA_MESE && m !== SCHEDA_MESE) continue;
      const mr = p.rec.filter(r => r.data.startsWith(m));
      if (!mr.length) continue;
      html += nastro(m, mr) + calendario(m, mr);
    }

    html += `<div class="rc-legend">` + Object.keys(CAT_LABEL).filter(k => k !== "anomalia" || n("anomalia"))
      .map(k => `<span><i style="background:${CAT_COLOR[k]}"></i>${CAT_LABEL[k]}</span>`).join("") +
      `<span><i style="background:var(--c-note)"></i>Nota nella cella</span>
       <span><i style="background:var(--c-ferie)"></i>P = preposto quel giorno</span></div>`;

    const conNote = rec.filter(r => r.nota);
    if (conNote.length) {
      html += `<div class="rc-pad" style="border-top:1px solid var(--rc-line)">
        <div class="rc-h4" style="margin-top:0">Note e variazioni (${conNote.length})</div>
        <table class="rc-table"><thead><tr><th style="width:96px">Data</th><th style="width:70px">Turno</th><th>Nota</th><th style="width:150px">Autore</th></tr></thead><tbody>` +
        conNote.map(r => `<tr><td>${ddmm(r.data)} <span class="rc-hint">${dowOf(r.data)}</span></td>
          <td><span class="rc-code" style="background:${CAT_COLOR[r.cat]}">${esc(r.code || "-")}</span></td>
          <td><span class="rc-notetxt">${esc(r.nota)}</span>${r.mansione ? `<div class="rc-hint">${esc(r.mansione)}</div>` : ""}</td>
          <td class="rc-hint">${esc(r.autore || "—")}</td></tr>`).join("") + `</tbody></table></div>`;
    }

    html += `<div class="rc-pad" style="border-top:1px solid var(--rc-line)"><div class="rc-h4" style="margin-top:0">Mansioni svolte</div>
      <table class="rc-table"><thead><tr><th>Mansione</th><th class="num" style="width:70px">Giorni</th><th>Date</th></tr></thead><tbody>` +
      (aggList.length ? aggList.map(([m, dates]) => `<tr><td><b>${esc(m)}</b></td><td class="num">${dates.length}</td>
        <td>${dates.map(d => `<span class="rc-pill">${ddmm(d)}</span>`).join("")}</td></tr>`).join("")
        : `<tr><td colspan="3" class="rc-hint">Nessuna mansione registrata nel periodo.</td></tr>`) +
      `</tbody></table></div>`;

    box.innerHTML = html;
    $("rcSchedaMese").addEventListener("change", e => { SCHEDA_MESE = e.target.value; renderScheda(); });
    bindPresc(p);
  }

  /* ---- prescrizioni mediche ---- */
  function prescBox(p) {
    const editable = DS.source.kind === "kairos" && p.eid;
    const origin = DS.source.kind === "excel" ? '<span class="rc-hint" style="text-transform:none;letter-spacing:0;font-weight:400">· dal foglio Dipendenti del file</span>' : "";
    if (!p.presc && !editable) return "";
    return `<div class="rc-presc ${p.presc ? "" : "empty"}" id="rcPresc">
      <div class="t"><i class="material-icons">medical_information</i>Prescrizioni mediche ${origin}
        ${editable ? `<span class="lnk rc-noprint" id="rcPrescEdit">${p.presc ? "Modifica" : "Aggiungi"}</span>` : ""}</div>
      <div class="v" id="rcPrescView">${p.presc ? esc(p.presc) : '<span class="rc-hint">Nessuna prescrizione registrata.</span>'}</div>
    </div>`;
  }
  function bindPresc(p) {
    const btn = $("rcPrescEdit");
    if (!btn) return;
    btn.addEventListener("click", () => {
      const box = $("rcPresc");
      box.classList.remove("empty");
      $("rcPrescView").innerHTML = `<textarea id="rcPrescTxt" class="browser-default" style="width:100%" maxlength="4000">${esc(p.presc)}</textarea>
        <div class="acts"><button class="btn btn-small waves-effect" style="background:#005B81" id="rcPrescSave">Salva</button>
        <button class="btn-flat btn-small waves-effect" id="rcPrescCancel">Annulla</button>
        <span class="rc-hint">Lascia vuoto per rimuovere. Visibile solo a staff e amministratori.</span></div>`;
      btn.classList.add("rc-hide");
      $("rcPrescTxt").focus();
      $("rcPrescCancel").addEventListener("click", renderScheda);
      $("rcPrescSave").addEventListener("click", async () => {
        try {
          const res = await fetchJson(CFG.urls.presc.replace(/0\/$/, p.eid + "/"), {
            method: "POST", headers: {"Content-Type": "application/json", "X-CSRFToken": csrf()},
            body: JSON.stringify({text: $("rcPrescTxt").value})
          });
          p.presc = res.text;
          toast("Prescrizioni salvate");
          renderLista(); renderScheda();
        } catch (e) { toast("Salvataggio non riuscito: " + esc(e.message), "red"); }
      });
    });
  }

  function nastro(m, mr) {
    const byDate = new Map(mr.map(r => [r.data, r]));
    const [y, mm] = m.split("-").map(Number);
    const last = new Date(y, mm, 0).getDate();
    let t = "";
    for (let d = 1; d <= last; d++) {
      const key = `${m}-${String(d).padStart(2, "0")}`;
      const r = byDate.get(key);
      const col = r ? CAT_COLOR[r.cat] : "#ECEFF1";
      const lbl = r && r.code ? r.code.replace("12H-", "") : "";
      const tip = key.split("-").reverse().join("/") + " · " + (r ? (r.code ? codeDesc(r.code) : CAT_LABEL[r.cat]) : "—") +
        (r && r.mansione ? " · " + r.mansione : "") + (r && r.preposto ? "\n★ Preposto — " + r.prepPos : "") + (r && r.nota ? "\n📝 " + r.nota : "");
      t += `<div class="rc-tick ${isWeekend(key) ? "we" : ""} ${FESTIVI.has(key) ? "fest" : ""}"><div class="d">${d}</div>
        <div class="b ${r && r.cat === "riposo" ? "rest" : ""} ${r && r.nota ? "nt" : ""} ${r && r.preposto ? "pp" : ""}" style="background:${col}" title="${esc(tip)}">${esc(lbl)}</div></div>`;
    }
    return `<div class="rc-nastro"><div class="lbl">${MESI[mm - 1]} ${y} · nastro turni</div><div class="rc-tape">${t}</div></div>`;
  }

  function calendario(m, mr) {
    const byDate = new Map(mr.map(r => [r.data, r]));
    const [y, mm] = m.split("-").map(Number);
    const last = new Date(y, mm, 0).getDate();
    const off = (new Date(y, mm - 1, 1).getDay() + 6) % 7;
    let cells = "";
    for (let i = 0; i < off; i++) cells += `<div class="rc-day void"></div>`;
    for (let d = 1; d <= last; d++) {
      const key = `${m}-${String(d).padStart(2, "0")}`;
      const r = byDate.get(key);
      const cat = r ? r.cat : "riposo";
      const col = CAT_COLOR[cat];
      const fest = FESTIVI.has(key);
      const nota = r && r.nota ? r.nota : "";
      const notaTip = nota + (r && r.autore ? " — " + r.autore : "");
      cells += `<div class="rc-day ${fest ? "fest" : ""} ${nota ? "hasnote" : ""}"><div class="bar" style="background:${r ? col : "#ECEFF1"}"></div>
        <div class="n">${d}${r && r.preposto ? `<span class="rc-flag p" title="${esc("Preposto — " + r.prepPos)}">P</span>` : ""}${nota ? `<span class="rc-flag nt" title="${esc(notaTip)}">nota</span>` : ""}</div>
        ${r && r.code ? `<span class="code" style="background:${col}" title="${esc(codeDesc(r.code))}">${esc(r.code)}</span>` : ""}
        <div class="m">${esc(r ? (r.mansione || CAT_LABEL[cat]) : "")}</div>
        ${nota ? `<div class="note" title="${esc(notaTip)}">${esc(nota)}</div>` : ""}</div>`;
    }
    return `<div class="rc-cal"><h6>${MESI[mm - 1]} ${y}</h6>
      <div class="rc-dow">${DOW.map(d => `<div>${d}</div>`).join("")}</div><div class="rc-days">${cells}</div></div>`;
  }

  /* ================================================================== GRAFICI */
  const FONT = "Roboto, 'Segoe UI', sans-serif";
  function chart(id, cfg) {
    if (CHARTS[id]) { CHARTS[id].destroy(); delete CHARTS[id]; }
    const el = $(id); if (!el || !window.Chart) return;
    CHARTS[id] = new Chart(el, cfg);
  }
  function baseOpts(extra) {
    return Object.assign({
      responsive: true, maintainAspectRatio: false, animation: false,
      plugins: {legend: {display: false}, tooltip: {backgroundColor: "#263238", padding: 10, titleFont: {family: FONT}, bodyFont: {family: FONT}}},
    }, extra || {});
  }
  const axis = (extra) => Object.assign({grid: {color: "#eeeeee"}, border: {display: false},
    ticks: {color: "#757575", font: {family: FONT, size: 11}}}, extra || {});

  function donutChart(id, data, centerLabel) {
    const tot = data.reduce((s, d) => s + d.value, 0);
    const shown = data.filter(d => d.value);
    chart(id, {
      type: "doughnut",
      data: {labels: shown.map(d => d.label), datasets: [{data: shown.map(d => d.value), backgroundColor: shown.map(d => d.color),
             borderColor: "#fff", borderWidth: 2, hoverOffset: 4}]},
      options: baseOpts({cutout: "64%", plugins: {
        legend: {display: true, position: "right", labels: {font: {family: FONT, size: 12}, boxWidth: 11, boxHeight: 11,
          generateLabels: ch => ch.data.labels.map((l, i) => ({text: `${l}  ${ch.data.datasets[0].data[i]}`,
            fillStyle: ch.data.datasets[0].backgroundColor[i], strokeStyle: "#fff", index: i}))}},
        tooltip: {backgroundColor: "#263238", callbacks: {label: c => ` ${c.label}: ${c.raw} giorni (${Math.round(c.raw / tot * 100)}%)`}}}}),
      plugins: [{id: "center", afterDraw(ch) {
        const {ctx, chartArea: a} = ch; const x = (a.left + a.right) / 2, y = (a.top + a.bottom) / 2;
        ctx.save(); ctx.textAlign = "center"; ctx.fillStyle = "#263238"; ctx.font = `600 22px ${FONT}`; ctx.fillText(tot, x, y + 2);
        ctx.fillStyle = "#757575"; ctx.font = `11px ${FONT}`; ctx.fillText(centerLabel || "giorni", x, y + 18); ctx.restore();
      }}]
    });
  }
  function vbarChart(id, labels, values, fmt) {
    chart(id, {
      type: "bar",
      data: {labels, datasets: [{data: values, backgroundColor: "#0076A5", borderRadius: 4, maxBarThickness: 34}]},
      options: baseOpts({scales: {x: axis({grid: {display: false}}), y: axis({beginAtZero: true})},
        plugins: {legend: {display: false}, tooltip: {backgroundColor: "#263238", callbacks: {label: c => " " + fmt(c.raw)}}}})
    });
  }
  function hbarChart(id, rows, fmt, color) {
    const wrap = $(id).parentElement;
    wrap.style.height = Math.max(120, rows.length * 24 + 40) + "px";
    chart(id, {
      type: "bar",
      data: {labels: rows.map(r => trunc(r.label, 48)), datasets: [{data: rows.map(r => r.value), backgroundColor: color || "#0076A5",
             borderRadius: 4, barPercentage: 0.78, categoryPercentage: 0.9}]},
      options: baseOpts({indexAxis: "y",
        scales: {x: axis({beginAtZero: true, position: "top"}), y: axis({grid: {display: false}, ticks: {color: "#37474f", font: {family: FONT, size: 11.5}, autoSkip: false}})},
        plugins: {legend: {display: false}, tooltip: {backgroundColor: "#263238", callbacks: {title: c => rows[c[0].dataIndex].label, label: c => " " + fmt(c.raw)}}}})
    });
  }

  /* ================================================================== REPORT DIPENDENTE */
  function statsPersona(rec) {
    const cat = {}; Object.keys(CAT_LABEL).forEach(c => cat[c] = 0);
    const mans = new Map(), mesi = new Map();
    let oreLav = 0, oreFor = 0, gLav = 0, we = 0, fest = 0;
    for (const r of rec) {
      cat[r.cat] = (cat[r.cat] || 0) + 1;
      if (isWork(r.cat)) {
        oreLav += r.ore; gLav++;
        if (isWeekend(r.data)) we++;
        if (FESTIVI.has(r.data)) fest++;
        const k = r.data.slice(0, 7); mesi.set(k, (mesi.get(k) || 0) + r.ore);
      }
      if (r.cat === "formazione") oreFor += r.ore;
      if (r.mansione) { if (!mans.has(r.mansione)) mans.set(r.mansione, {giorni: 0, ore: 0}); const x = mans.get(r.mansione); x.giorni++; x.ore += r.ore; }
    }
    return {cat, mans, mesi, oreLav, oreFor, gLav, we, fest, media: gLav ? oreLav / gLav : 0,
            nPrep: rec.filter(r => r.preposto).length};
  }
  function renderReport() {
    const sel = $("rcRpSel");
    const persone = PERSONE.filter(p => p.rec.length).sort((a, b) => a.nome.localeCompare(b.nome, "it"));
    if (sel.options.length !== persone.length || sel.dataset.src !== DS.source.label) {
      sel.innerHTML = persone.map(p => `<option value="${p.i}">${esc(p.nome)}</option>`).join("");
      sel.dataset.src = DS.source.label;
    }
    if (SEL !== null) sel.value = String(SEL);
    const p = PERSONE[+sel.value];
    const body = $("rcRpBody");
    if (!p) { body.innerHTML = emptyBox("person_off", "Nessun dipendente disponibile."); return; }
    const mese = $("rcRpMese").value;
    const s = statsPersona(mese ? p.rec.filter(r => r.data.startsWith(mese)) : p.rec);
    const periodo = mese ? meseLabel(mese) : (MESI_PRESENTI.length > 1 ? meseLabel(MESI_PRESENTI[0]) + " – " + meseLabel(MESI_PRESENTI[MESI_PRESENTI.length - 1]) : meseLabel(MESI_PRESENTI[0]));

    body.innerHTML = `
      <div class="rc-phead" style="padding:0 0 12px;border:0">
        <div><h5>${esc(p.nome)}</h5><div class="rc-meta">${socChip(p.soc)}<span>· ${esc(periodo)}</span></div></div>
      </div>
      <div class="rc-kpis">
        <div class="rc-kpi accent"><b>${fmtOre(s.oreLav)}</b><span>Ore lavorate</span></div>
        <div class="rc-kpi"><b>${s.gLav}</b><span>Giorni lavorati</span></div>
        <div class="rc-kpi"><b>${fmtOre(s.media)}</b><span>Media ore/giorno</span></div>
        <div class="rc-kpi"><b>${s.mans.size}</b><span>Mansioni diverse</span></div>
        <div class="rc-kpi"><b style="color:var(--c-ferie)">${s.nPrep}</b><span>Giorni da preposto</span></div>
        <div class="rc-kpi"><b>${fmtOre(s.oreFor)}</b><span>Ore formazione</span></div>
        <div class="rc-kpi"><b>${s.we}</b><span>Weekend lavorati</span></div>
        <div class="rc-kpi"><b>${s.fest}</b><span>Festivi lavorati</span></div>
      </div>
      <div class="rc-grid2">
        <div class="rc-card"><div class="rc-ct">Ripartizione giornate per categoria</div>
          <div class="rc-pad"><div class="rc-chartbox" style="height:240px"><canvas id="rcChDonut"></canvas></div></div></div>
        <div class="rc-card"><div class="rc-ct">Ore lavorate per mese</div>
          <div class="rc-pad"><div class="rc-chartbox" style="height:240px"><canvas id="rcChMesi"></canvas></div></div></div>
      </div>
      <div class="rc-card"><div class="rc-ct">Ore per mansione</div>
        <div class="rc-pad rc-scroll"><div class="rc-chartbox"><canvas id="rcChMans"></canvas></div></div></div>
      <div class="rc-card"><div class="rc-ct">Dettaglio mansioni</div><div class="rc-pad" style="padding-top:4px">
        <table class="rc-table"><thead><tr><th>Mansione</th><th class="num">Giorni</th><th class="num">Ore</th></tr></thead><tbody>
        ${[...s.mans.entries()].sort((a, b) => b[1].ore - a[1].ore).map(([m, v]) => `<tr><td>${esc(m)}</td><td class="num">${v.giorni}</td><td class="num">${fmtOre(v.ore)}</td></tr>`).join("")
          || '<tr><td colspan="3" class="rc-hint">Nessuna mansione registrata.</td></tr>'}
        </tbody></table></div></div>`;

    donutChart("rcChDonut", Object.keys(CAT_LABEL).map(c => ({label: CAT_LABEL[c], value: s.cat[c] || 0, color: CAT_COLOR[c]})));
    const mk = [...s.mesi.keys()].sort();
    vbarChart("rcChMesi", mk.map(m => MESI[+m.slice(5) - 1].slice(0, 3) + " " + m.slice(2, 4)), mk.map(m => Math.round(s.mesi.get(m) * 10) / 10), fmtOre);
    hbarChart("rcChMans", [...s.mans.entries()].map(([m, v]) => ({label: m, value: Math.round(v.ore * 10) / 10})).sort((a, b) => b.value - a.value), fmtOre);
  }

  /* ================================================================== MANSIONE */
  function renderChips() {
    const nNote = REC.filter(r => r.nota).length;
    $("rcMChips").innerHTML =
      `<button class="rc-qchip note ${soloNote ? "on" : ""}" id="rcChipNote">Solo giorni con nota (${nNote})</button>` +
      `<button class="rc-qchip ${!mansFilter ? "on" : ""}" data-q="">Tutte</button>` +
      QUICK.map(q => `<button class="rc-qchip ${mansFilter === q ? "on" : ""}" data-q="${esc(q)}">${esc(q)}</button>`).join("");
  }
  function filtraMansione() {
    const q = norm(mansFilter).trim();
    const mese = $("rcMMese").value;
    return REC.filter(r => (r.mansione || r.nota) && (!mese || r.data.startsWith(mese)) && (!soloNote || r.nota)
      && (!q || norm(r.mansione).includes(q) || norm(r.nota).includes(q)));
  }
  function renderMansione() {
    const rows = filtraMansione();
    const per = new Map();
    for (const r of rows) {
      const k = r.p + "||" + r.mansione;
      if (!per.has(k)) per.set(k, {nome: r.nome, societa: r.societa, mansione: r.mansione, date: [], note: []});
      const x = per.get(k); x.date.push(r.data);
      if (r.nota) x.note.push({d: r.data, t: r.nota, a: r.autore});
    }
    const list = [...per.values()].sort((a, b) => b.date.length - a.date.length || a.nome.localeCompare(b.nome, "it"));
    const el = $("rcMRes");
    if (!list.length) { el.innerHTML = emptyBox("search_off", "Nessun risultato per questo filtro. Prova con meno parole."); return; }
    const LIM = 400;
    el.innerHTML = `<p class="rc-hint">${list.length} combinazioni dipendente/mansione · ${rows.length} giornate · ${rows.filter(r => r.nota).length} con nota</p>
      <table class="rc-table"><thead><tr><th>Dipendente</th><th>Società</th><th>Mansione</th><th class="num">Giorni</th><th>Date e note</th></tr></thead><tbody>` +
      list.slice(0, LIM).map(x => `<tr><td><b>${esc(x.nome)}</b></td><td class="rc-hint">${esc(x.societa)}</td><td>${esc(x.mansione || "—")}</td>
        <td class="num">${x.date.length}</td><td>${x.date.map(d => `<span class="rc-pill">${ddmm(d)}</span>`).join("")}
        ${x.note.map(n => `<div style="font-size:12px;margin-top:3px"><span class="rc-notetxt">${ddmm(n.d)} ${esc(n.t)}</span>${n.a ? ` <span class="rc-hint">— ${esc(n.a)}</span>` : ""}</div>`).join("")}</td></tr>`).join("") +
      `</tbody></table>` + (list.length > LIM ? `<p class="rc-hint">Mostrate le prime ${LIM} righe: affina la ricerca o usa l'export CSV.</p>` : "");
  }

  /* ================================================================== PREPOSTI */
  function filtraPreposti() {
    const me = $("rcPMese").value, q = norm($("rcPCerca").value).trim();
    return PREPCASI.filter(c => (!me || c.data.startsWith(me)) && (!q || norm(c.posizione).includes(q) || norm(c.titolare).includes(q)));
  }
  function renderPreposti() {
    const rows = filtraPreposti();
    const bySoc = {}; rows.forEach(c => bySoc[c.soc] = (bySoc[c.soc] || 0) + 1);
    $("rcPKpi").innerHTML = `<div class="rc-kpis">
      <div class="rc-kpi accent"><b>${rows.length}</b><span>Giornate da preposto</span></div>
      <div class="rc-kpi"><b>${new Set(rows.map(c => c.p)).size}</b><span>Persone coinvolte</span></div>
      <div class="rc-kpi"><b>${new Set(rows.map(c => c.posizione)).size}</b><span>Posizioni</span></div>
      ${Object.keys(bySoc).sort().map(s => `<div class="rc-kpi"><b>${bySoc[s]}</b><span>Giornate ${esc(s)}</span></div>`).join("")}</div>`;
    const el = $("rcPRes");
    if (!rows.length) { el.innerHTML = emptyBox("verified_user", "Nessun preposto con questi filtri."); return; }
    const LIM = 600;
    const rigaLbl = DS.source.kind === "excel" ? "riga Excel" : "riga piano";
    el.innerHTML = `<table class="rc-table"><thead><tr><th style="width:96px">Data</th><th style="width:60px">Turno</th><th>Posizione</th><th>Preposto (come da piano)</th><th>Società</th></tr></thead><tbody>` +
      rows.slice(0, LIM).map(c => `<tr><td>${ddmm(c.data)} <span class="rc-hint">${dowOf(c.data)}</span></td><td>${esc(c.turno)}</td>
        <td>${esc(c.posizione)}<div class="rc-hint">${esc(c.foglio)} · ${rigaLbl} ${esc(c.riga)}</div></td>
        <td><b>${esc(c.titolare)}</b></td><td>${socChip(c.soc)}</td></tr>`).join("") + `</tbody></table>` +
      (rows.length > LIM ? `<p class="rc-hint">Mostrate le prime ${LIM} righe su ${rows.length}: usa i filtri o l'export CSV per l'elenco completo.</p>` : "");
  }

  /* ================================================================== COMMESSA */
  function datiCommessa() {
    const mese = $("rcCmMese").value, socF = $("rcCmSoc").value;
    const rows = REC.filter(r => (isWork(r.cat) || r.cat === "formazione") && (!mese || r.data.startsWith(mese)) && (!socF || r.societa === socF));
    const att = new Map();
    for (const r of rows) {
      const m = r.mansione || "(senza mansione indicata)";
      if (!att.has(m)) att.set(m, {ore: 0, giorni: 0, persone: new Set()});
      const x = att.get(m); x.ore += r.ore; x.giorni++; x.persone.add(r.nome);
    }
    const list = [...att.entries()].map(([m, v]) => ({mansione: m, ore: v.ore, giorni: v.giorni, persone: v.persone, n: v.persone.size}))
      .sort((a, b) => b.ore - a.ore);
    return {rows, list};
  }
  function renderCommessa() {
    if (!DS) return;
    const {rows, list} = datiCommessa();
    const oreTot = rows.reduce((s, r) => s + r.ore, 0);
    const oreSoc = {}; rows.forEach(r => oreSoc[r.societa] = (oreSoc[r.societa] || 0) + r.ore);
    $("rcCmBody").innerHTML = `
      <div class="rc-kpis">
        <div class="rc-kpi accent"><b>${fmtOre(oreTot)}</b><span>Ore erogate</span></div>
        <div class="rc-kpi"><b>${rows.length}</b><span>Giornate-uomo</span></div>
        <div class="rc-kpi"><b>${new Set(rows.map(r => r.p)).size}</b><span>Risorse impiegate</span></div>
        <div class="rc-kpi"><b>${list.length}</b><span>Attività distinte</span></div>
        ${Object.keys(oreSoc).sort().map(s => `<div class="rc-kpi"><b>${oreTot ? Math.round(oreSoc[s] / oreTot * 100) : 0}%</b><span>Ore ${esc(s)}</span></div>`).join("")}
      </div>
      <div class="rc-card rc-noprint" id="rcCmChartCard">
        <div class="rc-ct">Ore per attività (${list.length})
          <button class="btn-flat btn-small waves-effect rc-noprint" id="rcCmPrint" style="text-transform:none;letter-spacing:0"><i class="material-icons left">print</i>Stampa solo il grafico</button></div>
        <div class="rc-pad rc-scroll"><div class="rc-chartbox"><canvas id="rcChAtt"></canvas></div></div>
      </div>
      <div class="rc-card" id="rcCmTableCard"><div class="rc-ct">Dettaglio attività (${list.length})</div><div class="rc-pad" style="padding-top:4px">
        <table class="rc-table"><thead><tr><th>Attività / mansione</th><th class="num">Ore</th><th class="num">Giornate-uomo</th><th class="num">Risorse</th><th>Composizione</th></tr></thead><tbody>
        ${list.map(x => `<tr><td><b>${esc(x.mansione)}</b></td><td class="num">${fmtOre(x.ore)}</td><td class="num">${x.giorni}</td><td class="num">${x.n}</td>
          <td>${[...x.persone].sort((a, b) => a.localeCompare(b, "it")).slice(0, 6).map(n => `<span class="rc-pill">${esc(n)}</span>`).join("")}${x.n > 6 ? `<span class="rc-hint"> +${x.n - 6} altri</span>` : ""}</td></tr>`).join("")
          || '<tr><td colspan="5" class="rc-hint">Nessuna attività nel periodo selezionato.</td></tr>'}
        </tbody></table></div></div>`;
    hbarChart("rcChAtt", list.map(x => ({label: x.mansione, value: Math.round(x.ore * 10) / 10})), fmtOre);
    $("rcCmPrint").addEventListener("click", () => { document.body.classList.add("rc-print-attivita"); window.print(); });
  }
  window.addEventListener("afterprint", () => document.body.classList.remove("rc-print-attivita"));

  /* ================================================================== DATI */
  function renderDiag() {
    const D = DS.diag || [], O = DS.orphans || [], U = DS.unmatched || [];
    const isX = DS.source.kind === "excel";
    let h = `<div class="rc-h4">${isX ? "Fogli letti" : "Piani letti"}</div>
      <table class="rc-table"><thead><tr><th>${isX ? "Foglio" : "Piano"}</th><th>Mese</th><th class="num">Giorni</th><th class="num">Dipendenti</th><th class="num">Note</th><th>Esito</th></tr></thead><tbody>` +
      D.map(d => `<tr><td>${esc(d.foglio)}</td><td>${esc(d.mese || "—")}</td><td class="num">${d.giorni || "—"}</td><td class="num">${d.persone || "—"}</td>
        <td class="num">${d.note || 0}</td><td>${esc(d.esito)}${d.esitoNote ? `<div class="rc-hint">${esc(d.esitoNote)}</div>` : ""}</td></tr>`).join("") + `</tbody></table>`;
    const anom = REC.filter(r => r.cat === "anomalia");
    if (anom.length) {
      h += `<div class="rc-h4 rc-warn">Celle con "ERROR" nel file (${anom.length})</div>
        <p class="rc-hint">Le formule del piano turni scrivono ERROR quando la cella non è coerente, ad esempio la stessa persona su due posizioni nello stesso giorno. Queste giornate non sono conteggiate nelle ore.</p>
        <table class="rc-table"><thead><tr><th>Dipendente</th><th class="num">Giornate</th><th>Date</th></tr></thead><tbody>` +
        Object.entries(anom.reduce((a, r) => ((a[r.nome] = a[r.nome] || []).push(r.data), a), {})).sort((a, b) => b[1].length - a[1].length)
          .map(([n, ds]) => `<tr><td><b>${esc(n)}</b></td><td class="num">${ds.length}</td><td>${ds.map(d => `<span class="rc-pill">${ddmm(d)}</span>`).join("")}</td></tr>`).join("") +
        `</tbody></table>`;
    }
    if (O.length) {
      h += `<div class="rc-h4">Note su caselle senza nome (${O.length})</div>
        <table class="rc-table"><thead><tr><th style="width:70px">Cella</th><th style="width:96px">Data</th><th>Posizione</th><th>Nota</th><th style="width:140px">Autore</th></tr></thead><tbody>` +
        O.map(o => `<tr><td>${esc(o.cella)}</td><td>${ddmm(o.data)}</td><td>${esc(o.posizione)}</td><td class="rc-notetxt">${esc(o.testo)}</td><td class="rc-hint">${esc(o.autore)}</td></tr>`).join("") +
        `</tbody></table>`;
    }
    if (isX) {
      h += `<div class="rc-h4">Persone del file non presenti in Kairos (${U.length})</div>` +
        (U.length ? `<p class="rc-hint">Il confronto è per "Cognome Nome". Utile per riallineare l'anagrafica dei dipendenti.</p>
          <div>${U.map(n => `<span class="rc-pill" style="background:#fff3e0;color:#a65f00">${esc(n)}</span>`).join("")}</div>`
          : `<p class="rc-hint">Tutte le persone del file sono presenti in Kairos.</p>`);
    }
    $("rcDiag").innerHTML = h;
    renderPrescImport();
  }

  /* ---- import prescrizioni dal file verso Kairos ---- */
  function renderPrescImport(result) {
    const box = $("rcPrescImport");
    if (DS.source.kind !== "excel" || !LAST_FILE) { box.innerHTML = ""; return; }
    let h = `<div class="rc-presc rc-noprint" style="margin:6px 0 18px">
      <div class="t"><i class="material-icons">medical_information</i>Importa le prescrizioni mediche in Kairos</div>
      <div class="v rc-hint" style="margin-top:6px;white-space:normal">Confronta le prescrizioni del foglio "Dipendenti" di <b>${esc(LAST_FILE.name)}</b>
        con quelle salvate in Kairos. Prima vedi le differenze, poi decidi se applicarle. Abbinamento per "Cognome Nome".</div>
      <div class="acts" style="flex-wrap:wrap">
        <label style="margin-right:12px"><input type="checkbox" class="filled-in" id="rcPiClear" ${PI_CLEAR ? "checked" : ""}>
          <span style="font-size:13px">Rimuovi da Kairos le prescrizioni vuote nel file</span></label>
        <button class="btn btn-small waves-effect" style="background:#005B81" id="rcPiPreview"><i class="material-icons left">compare_arrows</i>Confronta con Kairos</button>
      </div>`;
    if (result) {
      const r = result;
      const tbl = (title, items, showOld) => items.length ? `<div class="rc-h4" style="margin-top:14px">${title} (${items.length})</div>
        <table class="rc-table"><thead><tr><th style="width:220px">Dipendente</th>${showOld ? "<th>In Kairos</th>" : ""}<th>${showOld ? "Dal file" : "Prescrizione"}</th></tr></thead><tbody>` +
        items.map(it => `<tr><td><b>${esc(it.nome)}</b></td>${showOld ? `<td class="rc-hint">${esc(it.old || "—")}</td>` : ""}<td>${esc(it.new || "(vuota)")}</td></tr>`).join("") +
        `</tbody></table>` : "";
      h += `<div style="margin-top:12px" class="rc-stats">Nel file: <b>${r.file_rows}</b> dipendenti, <b>${r.file_with_presc}</b> con prescrizione ·
          nuove <b>${r.create.length}</b> · aggiornate <b>${r.update.length}</b> · da rimuovere <b>${r.clear.length}</b> · invariate <b>${r.unchanged}</b></div>` +
        tbl("Nuove", r.create, false) + tbl("Aggiornate", r.update, true) + tbl("Da rimuovere", r.clear, true) +
        (r.kept.length ? `<p class="rc-hint" style="margin-top:10px">Vuote nel file ma presenti in Kairos, mantenute: ${r.kept.map(i => esc(i.nome)).join(", ")}</p>` : "") +
        (r.not_found.length ? `<p class="rc-hint rc-warn" style="margin-top:10px">Non trovati in Kairos (saltati): ${r.not_found.map(esc).join(", ")}</p>` : "") +
        (r.ambiguous.length ? `<p class="rc-hint rc-warn">Omonimi in Kairos (saltati): ${r.ambiguous.map(esc).join(", ")}</p>` : "") +
        (r.applied ? `<p style="margin-top:12px;color:#1F7A52;font-weight:500">Applicato: ${r.applied.create} nuove, ${r.applied.update} aggiornate, ${r.applied.clear} rimosse.</p>`
          : r.changes ? `<div class="acts" style="margin-top:12px"><button class="btn waves-effect" style="background:#e65100" id="rcPiApply">
              <i class="material-icons left">save</i>Applica ${r.changes} modifiche in Kairos</button></div>`
          : `<p class="rc-hint" style="margin-top:10px">Nessuna modifica da applicare: Kairos è già allineato al file.</p>`);
    }
    box.innerHTML = h + `</div>`;
    $("rcPiClear").addEventListener("change", e => { PI_CLEAR = e.target.checked; renderPrescImport(); });
    $("rcPiPreview").addEventListener("click", () => prescImport("preview"));
    const ap = $("rcPiApply");
    if (ap) ap.addEventListener("click", () => {
      if (confirm(`Confermi la scrittura di ${result.changes} modifiche alle prescrizioni mediche in Kairos?`)) prescImport("apply");
    });
  }
  async function prescImport(mode) {
    const fd = new FormData();
    fd.append("file", LAST_FILE); fd.append("mode", mode); fd.append("clear_missing", PI_CLEAR ? "1" : "0");
    busy(true);
    try {
      const r = await fetchJson(CFG.urls.prescImport, {method: "POST", body: fd, headers: {"X-CSRFToken": csrf()}});
      renderPrescImport(r);
      if (mode === "apply") toast("Prescrizioni importate in Kairos");
    } catch (e) { toast(esc(e.message), "red"); }
    finally { busy(false); }
  }

  /* ================================================================== EXPORT CSV */
  function csv(rows) {
    return "﻿" + rows.map(r => r.map(v => { v = v == null ? "" : String(v); return /[";\n]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v; }).join(";")).join("\r\n");
  }
  function scarica(nome, testo) {
    const b = new Blob([testo], {type: "text/csv;charset=utf-8"});
    const a = document.createElement("a"); a.href = URL.createObjectURL(b); a.download = nome;
    document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(a.href), 2000);
  }
  const HEAD = ["Dipendente", "Società", "Data", "Giorno", "Codice turno", "Descrizione turno", "Categoria", "Ore", "Mansione",
                "Preposto", "Posizione preposto", "Area/Servizio", "Nota cella", "Autore nota", "Nota posizione"];
  const riga = r => [r.nome, r.societa, r.data, dowOf(r.data), r.code, r.code ? codeDesc(r.code) : "", CAT_LABEL[r.cat],
                     String(r.ore).replace(".", ","), r.mansione, r.preposto ? "SI" : "NO", r.prepPos, r.area, r.nota, r.autore, r.notaPos];
  const slug = () => (DS.source.label || "report").replace(/[^\w-]+/g, "_").replace(/_+/g, "_");
  const EXPORTS = {
    persona() {
      if (SEL === null) return;
      const p = PERSONE[SEL];
      const rec = SCHEDA_MESE ? p.rec.filter(r => r.data.startsWith(SCHEDA_MESE)) : p.rec;
      scarica(`turni_${p.nome.replace(/\s+/g, "_")}${SCHEDA_MESE ? "_" + SCHEDA_MESE : ""}.csv`, csv([HEAD, ...rec.map(riga)]));
    },
    mansione() { scarica("ricerca_mansione.csv", csv([HEAD, ...filtraMansione().map(riga)])); },
    preposti() {
      const out = [["Data", "Foglio/Piano", "Turno", "Posizione", "Riga", "Preposto", "Società"]];
      for (const c of filtraPreposti()) out.push([c.data, c.foglio, c.turno, c.posizione, c.riga, c.titolare, c.soc]);
      scarica("preposti.csv", csv(out));
    },
    commessa() {
      const out = [["Attività/mansione", "Ore totali", "Giornate-uomo", "Numero risorse", "Elenco risorse"]];
      for (const x of datiCommessa().list) out.push([x.mansione, String(Math.round(x.ore * 10) / 10).replace(".", ","), x.giorni, x.n, [...x.persone].sort().join(" / ")]);
      scarica("riepilogo_commessa.csv", csv(out));
    },
    all() { scarica(`turni_completi_${slug()}.csv`, csv([HEAD, ...REC.map(riga)])); },
    worked() { scarica(`turni_lavorati_${slug()}.csv`, csv([HEAD, ...REC.filter(r => isWork(r.cat)).map(riga)])); },
    notes() { scarica(`note_celle_${slug()}.csv`, csv([HEAD, ...REC.filter(r => r.nota).map(riga)])); },
  };

  /* ================================================================== EVENTI */
  function initEvents() {
    $("rcSearch").addEventListener("input", renderLista);
    $("rcPList").addEventListener("click", e => { const it = e.target.closest(".rc-pitem"); if (it) selectPerson(+it.dataset.i); });
    $("rcRpSel").addEventListener("change", e => { SEL = +e.target.value; window.__rcSelName = PERSONE[SEL].nome; renderReport(); renderLista(); renderScheda(); });
    $("rcRpMese").addEventListener("change", renderReport);
    $("rcMSearch").addEventListener("input", e => { mansFilter = e.target.value; renderChips(); renderMansione(); });
    $("rcMMese").addEventListener("change", renderMansione);
    $("rcMChips").addEventListener("click", e => {
      const c = e.target.closest(".rc-qchip"); if (!c) return;
      if (c.id === "rcChipNote") soloNote = !soloNote;
      else { mansFilter = c.dataset.q; $("rcMSearch").value = mansFilter; }
      renderChips(); renderMansione();
    });
    ["rcPMese", "rcPCerca"].forEach(id => $(id).addEventListener("input", renderPreposti));
    ["rcCmMese", "rcCmSoc"].forEach(id => $(id).addEventListener("change", renderCommessa));
    document.addEventListener("click", e => {
      const b = e.target.closest("[data-export]"); if (!b || !DS) return;
      EXPORTS[b.dataset.export] && EXPORTS[b.dataset.export]();
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    initSource(); initTabs(); initEvents();
    loadKairos();
  });
})();
