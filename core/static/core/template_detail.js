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

  const btnInsert = document.getElementById("btn-insert");
  const refRowSel = document.getElementById("ref-row");
  const posSel    = document.getElementById("position");
  const dutyInput = document.getElementById("duty");
  const baseInput = document.getElementById("base");
  const spacerChk = document.getElementById("is-spacer");

  // Gestione toggle riga [spazio]
  if (spacerChk) {
    spacerChk.addEventListener("change", () => {
      const isSpacer = spacerChk.checked;
      if (isSpacer) {
        if (dutyInput) {
          dutyInput.value = "";
          dutyInput.setAttribute("disabled", "disabled");
        }
        if (baseInput) {
          baseInput.value = "";
          baseInput.setAttribute("disabled", "disabled");
        }
      } else {
        if (dutyInput) dutyInput.removeAttribute("disabled");
        if (baseInput) baseInput.removeAttribute("disabled");
      }
      if (window.M && M.updateTextFields) {
        M.updateTextFields();
      }
    });
  }

  // --- INSERT ROW ---
  if (btnInsert) {
    btnInsert.addEventListener("click", async (e) => {
      e.preventDefault();

      const ref = refRowSel ? refRowSel.value : "";
      const pos = (posSel && posSel.value) || "after";
      const isSpacer = spacerChk ? spacerChk.checked : false;

      const duty = dutyInput ? dutyInput.value.trim() : "";
      const base = baseInput ? baseInput.value.trim() : "";

      if (!ref) {
        return M.toast({ html: "Seleziona la riga di riferimento", classes: "orange" });
      }

      if (isSpacer && (duty || base)) {
        return M.toast({
          html: "Per una riga [spazio] lascia vuoti Duty e Base",
          classes: "orange",
        });
      }

      if (!isSpacer && !duty && !base) {
        return M.toast({
          html: "Compila almeno Duty o Base, oppure seleziona riga di separazione",
          classes: "orange",
        });
      }

      const url = `/api/templates/${templateId}/insert_row/`;
      const body = {
        position: pos,
        template_row_id: Number(ref),
      };

      if (isSpacer) {
        body.is_spacer = true;
      } else {
        if (duty) body.duty = duty;
        else body.base = base;
      }

      let resp;
      try {
        resp = await fetch(url, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrftoken,
          },
          credentials: "same-origin",
          body: JSON.stringify(body),
        });
      } catch (e) {
        return M.toast({
          html: "Errore di rete durante l'inserimento",
          classes: "red",
        });
      }

      if (!resp.ok) {
        let msg = "Errore durante l'inserimento";
        try {
          const j = await resp.json();
          if (j.detail) msg = j.detail;
        } catch (_) {}
        return M.toast({ html: msg, classes: "red" });
      }

      const js = await resp.json();
      const label = js.is_spacer ? "[spazio]" : (js.duty || "");
      M.toast({
        html: `Inserita: ${label} in posizione #${js.insert_order}`,
        classes: "green",
      });

      // ricarico per riallineare gli ordini e la UI
      location.reload();
    });
  }

  // --- DELETE ROW ---
  async function deleteTemplateRow(templateId, rowId) {
    if (!confirm("Eliminare la riga dal template e da tutti i piani derivati?")) return;

    const url = `/api/templates/${templateId}/delete_row/`;
    let resp;
    try {
      resp = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrftoken,
        },
        credentials: "same-origin",
        body: JSON.stringify({ template_row_id: rowId }),
      });
    } catch (e) {
      alert("Errore di rete durante l'eliminazione della riga.");
      return;
    }

    const data = await resp.json().catch(() => ({}));

    if (!resp.ok || data.ok === false) {
      let msg = (data && data.detail) || "Impossibile eliminare la riga.";
      if (data && data.assegnazioni && data.assegnazioni.length) {
        msg +=
          "\n\nAssegnazioni rilevate:\n" +
          data.assegnazioni
            .map(
              (a) =>
                `• ${a.dipendente} — ${a.piano} (${a.turno}, ${a.data})`
            )
            .join("\n");
      }
      alert(msg);
      return;
    }

    M.toast({
      html: `Riga '${data.deleted_duty || "[spazio]"}' eliminata con successo.`,
      classes: "green",
    });
    const li = document.querySelector(`[data-row-id="${rowId}"]`);
    if (li) li.remove();
    else location.reload();
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
