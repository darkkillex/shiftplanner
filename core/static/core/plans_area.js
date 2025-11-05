(function(){
  const input = document.getElementById('plans-filter');
  const list  = document.getElementById('plans-list');
  if(!input || !list) return;

  const items = () => Array.from(list.querySelectorAll('.collection-item'));
  const countEl = document.getElementById('plans-count');

  function norm(s){
    return (s||'').toString().toLowerCase()
      .normalize('NFD').replace(/[\u0300-\u036f]/g,'').trim();
  }

  function apply(){
    const q = norm(input.value);
    let shown = 0;
    items().forEach(li=>{
      const target = li.querySelector('[data-text]');
      const hay = (target?.dataset.text || target?.textContent || '');
      const ok = !q || norm(hay).includes(q);
      li.style.display = ok ? '' : 'none';
      if(ok) shown++;
    });
    countEl.textContent = `Mostrati: ${shown}/${items().length}`;
  }

  // init
  input.addEventListener('input', ()=> requestAnimationFrame(apply));
  apply();
})();
