(function(){
  function getCookie(name){
    const m = document.cookie.match('(^|;)\\s*'+name+'\\s*=\\s*([^;]+)');
    return m ? m.pop() : '';
  }
  const CSRF = getCookie('csrftoken');
  const headersJSON = {'Content-Type':'application/json','X-CSRFToken': CSRF};

  const list = document.getElementById('reminder-list');
  const calEl = document.getElementById('calendar');
  let currentYear, currentMonth;

  async function fetchReminders(y, m){
    const r = await fetch(`/api/reminders/?year=${y}&month=${m}`, {credentials:'same-origin'});
    if(!r.ok) return [];
    return r.json();
  }
  function spanDays(a,b){ return Math.round((b-a)/(1000*60*60*24)); }

  function classify(rem){
    if(rem.completed) return 'done';
    const now = new Date(); now.setHours(0,0,0,0);
    const d = new Date(rem.date+'T00:00:00');
    const dd = spanDays(now, d);
    if(dd < 0) return 'overdue';
    if(dd <= 3) return 'due-soon';
    return '';
  }

  function renderList(data){
    list.innerHTML = '';
    if(!data.length){
      list.innerHTML = '<li class="collection-item">Nessuna scadenza.</li>';
      return;
    }
    data.forEach(r=>{
      const d = new Date(r.date+'T00:00:00');
      const cls = classify(r);
      const li = document.createElement('li');
      li.className = `collection-item ${cls}`;
      li.innerHTML = `
        <div class="reminder-row">
          <label>
            <input type="checkbox" ${r.completed?'checked':''} data-id="${r.id}">
            <span></span>
          </label>
          <div class="reminder-meta">
            <span class="reminder-date">${d.toLocaleDateString()}</span>
            <span>${r.title}</span>
          </div>
        </div>
        ${r.details ? `<div class="grey-text text-darken-1 reminder-details">${r.details}</div>`:''}
      `;
      li.querySelector('input[type=checkbox]').addEventListener('change', async (e)=>{
        await fetch(`/api/reminders/${r.id}/`, {
          method:'PATCH', headers: headersJSON, credentials:'same-origin',
          body: JSON.stringify({completed: e.target.checked})
        });
        load();
      });
      list.appendChild(li);
    });
  }

  async function load(){
    const data = await fetchReminders(currentYear, currentMonth);
    renderList(data);
    calendar.removeAllEvents();
    calendar.addEventSource(data.map(r=>{
      const cls = classify(r);
      return {
        id: r.id,
        title: r.title + (r.completed?' ✓':''),
        start: r.date,
        classNames: cls ? [cls] : []
      };
    }));
  }

  const calendar = new FullCalendar.Calendar(calEl, {
    initialView: 'dayGridMonth',
    firstDay: 1,
    locale: 'it',
    height: 'auto',
    headerToolbar: { left:'prev,next today', center:'title', right:'' }, /* rimosso bottone Month */

    dateClick: async (info)=>{
      const title = prompt(`Nuovo appunto per ${info.dateStr}:`);
      if(!title) return;
      await fetch('/api/reminders/', {
        method:'POST', headers: headersJSON, credentials:'same-origin',
        body: JSON.stringify({date: info.dateStr, title, details: ''})
      });
      await load();
    },

    datesSet: async (arg)=>{
      const d = arg.view.currentStart;
      currentYear = d.getFullYear();
      currentMonth = d.getMonth() + 1;
      await load();
    }
  });

  calendar.render();
})();