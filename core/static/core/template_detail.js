(function () {
  // --- Init Materialize ---
  function initMaterialize() {
    if (!window.M) return;
    try {
      M.FormSelect.init(document.querySelectorAll("select"));
    } catch (e) {}
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initMaterialize, { once: true });
  } else initMaterialize();

  // --- CSRF helper ---
  function getCookie(name) {
    const v = `; ${document.cookie}`;
    const p = v.split(`; ${name}=`);
    if (p.length === 2) return p.pop().split(";").shift();
  }
  const csrftoken = getCookie("csrftoken");

  // --- INSERT ROW (resta identica alla tua attuale logica) ---
  const btnInsert = document.getElementById("btn-insert");
  if (btnInsert) {
    btnInsert.addEventListener("click", async () => {
      const ref = document.getElementById("ref-row").value;
      const pos = document.getElementById("position").value || "after";
      const duty = document.getElementById("duty").value.trim();
      const base = document.getElementById("base").value.trim();
      if (!ref)
        return M.toast({ html: "Seleziona la riga di riferimento", classes: "orange" });
      if (!duty && !base)
        return M.toast({ html: "Inserisci duty o base", classes: "orange" });

      const url = `/api/templates/${templateId}/insert_row/`;
      const body = { position: pos, template_row_id: Number(ref) };
      if (duty) body.duty = duty;
      else body.base = base;

      const resp = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrftoken },
        credentials: "same-origin",
        body: JSON.stringify(body),
      });

      if (!resp.ok) {
        let msg = "Errore durante l'inserimento";
        try {
          const j = await resp.json();
          if (j.detail) msg = j.detail;
        } catch (_) {}
        return M.toast({ html: msg, classes: "red" });
      }

      const js = await resp.json();
      M.toast({
        html: `Inserita: ${js.duty} in posizione #${js.insert_order}`,
        classes: "green",
      });
      location.reload();
    });
  }

  // --- DELETE ROW ---
  async function deleteTemplateRow(templateId, rowId) {
    if (!confirm("Eliminare la riga dal template e da tutti i piani derivati?")) return;

    const url = `/api/templates/${templateId}/delete_row/`;
    const resp = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrftoken,
      },
      credentials: "same-origin",
      body: JSON.stringify({ template_row_id: rowId }),
    });

    const data = await resp.json().catch(() => ({}));

    if (!resp.ok || data.ok === false) {
      let msg = (data && data.detail) || "Impossibile eliminare la riga.";
      if (data && data.assegnazioni && data.assegnazioni.length) {
        msg += "\n\nAssegnazioni rilevate:\n" +
          data.assegnazioni.map(
            (a) => `• ${a.dipendente} — ${a.piano} (${a.turno}, ${a.data})`
          ).join("\n");
      }
      alert(msg);
      return;
    }

    // OK
    M.toast({ html: `Riga '${data.deleted_duty}' eliminata con successo.`, classes: "green" });
    const li = document.querySelector(`[data-row-id="${rowId}"]`);
    if (li) li.remove(); else location.reload();
  }

  // --- Event delegation per i pulsanti "Elimina" ---
  document.addEventListener("click", function (e) {
    const btn = e.target.closest(".js-row-delete");
    if (!btn) return;
    e.preventDefault();
    const templateId = btn.dataset.templateId;
    const rowId = btn.dataset.rowId;
    if (!templateId || !rowId) return;
    deleteTemplateRow(templateId, Number(rowId));
  });

})();
