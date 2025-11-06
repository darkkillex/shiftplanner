(function () {
  // Refs
  const input   = document.getElementById('plans-filter');
  const clear   = document.getElementById('plans-filter-clear');
  const countEl = document.getElementById('plans-count');
  const list    = document.getElementById('plans-list');
  if (!list) return;

  // Prendi tutti i LI filtrabili sotto #plans-list
  // Evita eventuali placeholder "Nessun piano."
  const items = Array.from(list.querySelectorAll('li.collection-item')).filter(li => {
    return !li.classList.contains('grey-text'); // adatta se usi altra classe per l'empty
  });

  // Funzione di normalizzazione
  const norm = (s) =>
    (s || '')
      .toString()
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .trim();

  // Estrazione testo per ogni LI: usa data-text se presente,
  // altrimenti concatena testo di link, chip, badge, ecc.
  function liText(li) {
    const dt = li.querySelector('[data-text]');
    if (dt && dt.dataset.text) return dt.dataset.text;

    // fallback: prendi testo visibile di vari elementi
    const parts = [];
    li.querySelectorAll('a, .chip, .secondary-text, .title, .subtitle, span, strong').forEach(el => {
      parts.push(el.textContent || '');
    });
    // se nulla trovato, usa textContent del LI
    if (!parts.length) parts.push(li.textContent || '');
    return parts.join(' ').replace(/\s+/g, ' ').trim();
  }

  // Precalcola il testo normalizzato per performance
  const itemData = items.map(li => ({
    li,
    hay: norm(liText(li))
  }));

  function updateCount(shown, total, qActive) {
    if (!countEl) return;
    countEl.textContent = qActive
      ? `Mostrati: ${shown}/${total}`
      : `Mostrati: ${total}/${total}`;
  }

  function toggleLabelActive(active) {
    const lbl = document.querySelector("label[for='plans-filter']");
    if (!lbl) return;
    if (active) lbl.classList.add('active'); else lbl.classList.remove('active');
  }

  function apply() {
    const qRaw = input ? input.value : '';
    const q = norm(qRaw);
    let shown = 0;

    itemData.forEach(({ li, hay }) => {
      const ok = !q || hay.includes(q);
      li.style.display = ok ? '' : 'none';
      if (ok) shown++;
    });

    updateCount(shown, itemData.length, !!q);
    toggleLabelActive(!!q);
  }

  // Debounce input
  if (input) {
    let t;
    input.addEventListener('input', () => {
      clearTimeout(t);
      t = setTimeout(apply, 120);
    });
  }

  // Clear
  if (clear) {
    clear.addEventListener('click', (e) => {
      e.preventDefault();
      if (input) input.value = '';
      apply();
      input && input.focus();
    });
  }

  // Prime render
  apply();
})();
