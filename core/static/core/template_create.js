document.addEventListener('DOMContentLoaded', function() {
  // auto-resize Materialize (se presente)
  try {
    var taAuto = document.querySelector('textarea.materialize-textarea');
    if (taAuto && window.M && M.textareaAutoResize) {
      M.textareaAutoResize(taAuto);
    }
  } catch (e) {
    console.warn('textareaAutoResize error:', e);
  }

  // textarea: sappiamo che il campo del form si chiama "rows_text"
  const textarea  = document.querySelector('textarea[name="rows_text"]');
  const tableBody = document.getElementById('tpl-rows-tbody');
  const shiftTpl  = document.getElementById('row-shift-template');

  if (!textarea || !tableBody) {
    console.warn('Textarea rows_text o tbody tpl-rows-tbody non trovati');
    return;
  }

  // HTML delle option dei turni, preso dal <select> nascosto
  const SHIFT_OPTIONS_HTML = shiftTpl ? shiftTpl.innerHTML : '<option value="">— Nessun turno associato —</option>';

  function rebuildRowsTable() {
    const raw = textarea.value || "";
    const lines = raw.replace(/\r\n/g, "\n").split("\n");
    tableBody.innerHTML = "";

    lines.forEach((ln, idx) => {
      const order   = idx + 1;
      const trimmed = ln.trim();
      const tr      = document.createElement('tr');
      const isSpacer = trimmed === "";

      if (isSpacer) {
        tr.classList.add('template-spacer-row');
        tr.innerHTML = `
          <td style="width:60px;">${order}</td>
          <td>(separatore)</td>
          <td>—</td>
        `;
      } else {
        tr.innerHTML = `
          <td style="width:60px;">${order}</td>
          <td>${trimmed}</td>
          <td>
            <select class="browser-default tpl-row-shift"
                    name="row_shift_${order}">
              ${SHIFT_OPTIONS_HTML}
            </select>
          </td>
        `;
      }

      tableBody.appendChild(tr);
    });
  }

  // prima costruzione (anche per moduli precompilati)
  rebuildRowsTable();

  // ricostruisci la tabella ogni volta che cambia il testo nella textarea
  textarea.addEventListener('input', rebuildRowsTable);
});
