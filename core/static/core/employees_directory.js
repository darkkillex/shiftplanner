document.addEventListener('DOMContentLoaded', function() {
  // Inizializza select Materialize
  if (window.M && M.FormSelect) {
    const elems = document.querySelectorAll('select');
    M.FormSelect.init(elems);
  }

  const companyFilter = document.getElementById('filter-company');
  const textFilter    = document.getElementById('filter-text');
  const table         = document.getElementById('employees-table');
  const counter       = document.getElementById('emp-counter');
  const btnClear      = document.getElementById('filter-clear');

  if (!table) return;

  const rows = Array.from(table.querySelectorAll('tbody tr'));

  function applyFilters() {
    const companyId = companyFilter.value || "";
    const text = (textFilter.value || "").toLowerCase().trim();

    let visible = 0;

    rows.forEach(row => {
      const rowCompanyId = (row.dataset.companyId || "");
      const searchText   = (row.dataset.search || "").toLowerCase();

      const matchCompany = !companyId || rowCompanyId === companyId;
      const matchText    = !text || searchText.includes(text);

      if (matchCompany && matchText) {
        row.style.display = "";
        visible += 1;
      } else {
        row.style.display = "none";
      }
    });

    if (counter) {
      counter.textContent = `${visible} dipendenti`;
    }
  }

  // Filtro live testo
  if (textFilter) {
    textFilter.addEventListener('input', applyFilters);
  }

  // Filtro azienda
  if (companyFilter) {
    companyFilter.addEventListener('change', applyFilters);
  }

  // Pulsante "Pulisci filtri"
  if (btnClear) {
    btnClear.addEventListener('click', function(e) {
      e.preventDefault();

      // reset testo
      if (textFilter) {
        textFilter.value = "";
      }

      // reset select
      if (companyFilter) {
        companyFilter.value = "";
        if (window.M && M.FormSelect) {
          const instance = M.FormSelect.getInstance(companyFilter);
          if (instance) instance.destroy();
          M.FormSelect.init(companyFilter);
        }
      }

      applyFilters();
    });
  }

  // Prima applicazione (mostra tutto con contatore corretto)
  applyFilters();
});
