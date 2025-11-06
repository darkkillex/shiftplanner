(function(){
  "use strict";
  const $  = (s, r=document)=>r.querySelector(s);
  const $$ = (s, r=document)=>Array.from(r.querySelectorAll(s));
  const norm = s => (s||"").toLowerCase()
    .normalize("NFD").replace(/[\u0300-\u036f]/g,"").trim();

  document.addEventListener('DOMContentLoaded', function(){
    const input   = $('#filter-tpl');
    const clear   = $('#filter-clear');
    const counter = $('#filter-count');
    const list    = $('#tpl-list');

    if (!list) return;

    const items = () => $$('#tpl-list > li.collection-item');

    function haystack(li){
      return (
        li.querySelector('[data-text]')?.dataset.text ||
        li.querySelector('.template-name')?.textContent ||
        li.querySelector('a')?.textContent ||
        li.textContent ||
        ''
      );
    }

    function apply(){
      const q = norm(input?.value || '');
      let shown = 0;
      items().forEach(li=>{
        const hay = norm(haystack(li));
        const ok  = !q || hay.includes(q);
        li.style.display = ok ? '' : 'none';
        if (ok) shown++;
      });
      if (counter) {
        counter.textContent = q ? `Mostrati: ${shown}/${items().length}` : 'Mostrati: tutti';
      }
    }

    // live filter con piccolo debounce
    if (input){
      let t;
      input.addEventListener('input', ()=>{
        clearTimeout(t);
        t = setTimeout(apply, 120);
      });
    }

    // clear
    if (clear){
      clear.addEventListener('click', ()=>{
        if (input) input.value = '';
        apply();
        if (input) input.focus();
      });
    }

    apply();
  });
})();
