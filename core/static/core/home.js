(function(){
  "use strict";
  const $  = (s,r=document)=>r.querySelector(s);
  const $$ = (s,r=document)=>Array.from(r.querySelectorAll(s));
  const norm = s => (s||"").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g,"").trim();

  document.addEventListener('DOMContentLoaded', ()=>{
    const input = $('#hub-filter');
    const clear = $('#hub-filter-clear');
    const count = $('#hub-count');
    const items = $$('.hub-item');

    function apply(){
      const q = norm(input?.value);
      let shown = 0;
      items.forEach(el=>{
        const hay = (el.dataset.text || el.textContent || '');
        const ok = !q || norm(hay).includes(q);
        el.style.display = ok ? '' : 'none';
        if (ok) shown++;
      });
      if (count) count.textContent = q ? `Mostrati: ${shown}/${items.length}` : 'Mostrati: tutti';
    }

    if (input){
      let t; input.addEventListener('input', ()=>{ clearTimeout(t); t=setTimeout(apply, 120); });
    }
    if (clear){
      clear.addEventListener('click', ()=>{
        if (input) input.value = '';
        apply();
        input && input.focus();
      });
    }
    apply();
  });
})();
