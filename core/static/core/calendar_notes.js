(function() {
  function getCookie(name) {
    const m = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
    return m ? m.pop() : '';
  }

  const CSRF = getCookie('csrftoken');
  const headersJSON = { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF };

  const list = document.getElementById('reminder-list');
  const calEl = document.getElementById('calendar');
  let currentYear, currentMonth;
  let calendar = null;

  // ----------------- API -----------------
  async function fetchReminders(y, m) {
    const r = await fetch(`/api/reminders/?year=${y}&month=${m}`, { credentials: 'same-origin' });
    if (!r.ok) return [];
    return r.json();
  }

  async function fetchReminderDetail(id) {
    const r = await fetch(`/api/reminders/${id}/`, { credentials: 'same-origin' });
    if (!r.ok) return null;
    return r.json();
  }

  function spanDays(a, b) {
    return Math.round((b - a) / (1000 * 60 * 60 * 24));
  }

  function classify(rem) {
    if (rem.completed) return 'done';
    const now = new Date();
    now.setHours(0, 0, 0, 0);
    const d = new Date(rem.date + 'T00:00:00');
    const dd = spanDays(now, d);
    if (dd < 0) return 'overdue';
    if (dd <= 3) return 'due-soon';
    return '';
  }

  // ----------------- Materialize confirm -----------------
  function materialConfirm(message) {
    return new Promise((resolve) => {
      if (!(window.M && M.Modal)) {
        // fallback: conferma nativa
        resolve(window.confirm(message));
        return;
      }

      let modalEl = document.getElementById('reminder-confirm-modal');
      if (!modalEl) {
        modalEl = document.createElement('div');
        modalEl.id = 'reminder-confirm-modal';
        modalEl.className = 'modal';
        modalEl.innerHTML = `
          <div class="modal-content">
            <h6>Conferma</h6>
            <p id="reminder-confirm-message"></p>
          </div>
          <div class="modal-footer">
            <a href="#!" class="modal-close waves-effect btn-flat" data-confirm-cancel>Annulla</a>
            <a href="#!" class="waves-effect waves-light btn" data-confirm-ok>Conferma</a>
          </div>
        `;
        document.body.appendChild(modalEl);
        M.Modal.init(modalEl, { dismissible: false });
      }

      const msgEl = modalEl.querySelector('#reminder-confirm-message');
      msgEl.textContent = message;

      const instance = M.Modal.getInstance(modalEl);
      const btnOk = modalEl.querySelector('[data-confirm-ok]');
      const btnCancel = modalEl.querySelector('[data-confirm-cancel]');

      function cleanup(result) {
        btnOk.removeEventListener('click', onOk);
        btnCancel.removeEventListener('click', onCancel);
        instance.close();
        resolve(result);
      }

      function onOk(e) {
        e.preventDefault();
        cleanup(true);
      }

      function onCancel(e) {
        e.preventDefault();
        cleanup(false);
      }

      btnOk.addEventListener('click', onOk);
      btnCancel.addEventListener('click', onCancel);

      instance.open();
    });
  }

  // ----------------- Rendering HTML singola nota -----------------
  function buildReminderHTML(r) {
    const d = new Date(r.date + 'T00:00:00');

    let createdInfo = '';
    if (r.created_at) {
      const createdDate = new Date(r.created_at);
      const createdLabel = createdDate.toLocaleString();
      const creator = r.created_by_name || '';
      createdInfo = `Creata da ${creator} il ${createdLabel}`;
    }

    let closedInfo = '';
    if (r.completed && r.closed_at) {
      const closedDate = new Date(r.closed_at);
      const closedLabel = closedDate.toLocaleString();
      const closer = r.closed_by_name || '';
      closedInfo = `Chiusa da ${closer} il ${closedLabel}`;
    }

    return `
      <div class="reminder-row">
        <label>
          <input type="checkbox" ${r.completed ? 'checked' : ''} data-id="${r.id}">
          <span></span>
        </label>
        <div class="reminder-meta">
          <span class="reminder-date">${d.toLocaleDateString()}</span>
          <span>${r.title}</span>
          ${(createdInfo || closedInfo) ? `
            <span class="grey-text text-darken-1" style="font-size:0.8rem; margin-top:2px;">
              ${createdInfo}
              ${closedInfo ? '<br>' + closedInfo : ''}
            </span>
          ` : ''}
        </div>
      </div>
      ${r.details ? `<div class="grey-text text-darken-1 reminder-details">${r.details}</div>` : ''}
    `;
  }

  // ----------------- Aggancio handler checkbox singola nota -----------------
  function attachCheckboxHandler(li, r) {
    const cb = li.querySelector('input[type=checkbox]');
    if (!cb) return;

    cb.addEventListener('change', async (e) => {
      const checked = e.target.checked;

      const msg = checked
        ? 'Segnare questa nota come completata?'
        : 'Riportare questa nota come da fare?';

      const ok = await materialConfirm(msg);
      if (!ok) {
        // rollback stato
        e.target.checked = !checked;
        return;
      }

      // PATCH completed
      const resp = await fetch(`/api/reminders/${r.id}/`, {
        method: 'PATCH',
        headers: headersJSON,
        credentials: 'same-origin',
        body: JSON.stringify({ completed: checked })
      });

      if (!resp.ok) {
        // errore → rollback e toast
        e.target.checked = !checked;
        if (window.M && M.toast) {
          M.toast({ html: 'Errore durante l\'aggiornamento', classes: 'red' });
        }
        return;
      }

      // recupera lo stato aggiornato dal server (così abbiamo closed_by/closed_at corretti)
      const updated = await fetchReminderDetail(r.id);
      if (!updated) {
        if (window.M && M.toast) {
          M.toast({ html: 'Aggiornato, ma impossibile ricaricare i dettagli', classes: 'orange' });
        }
      } else {
        // aggiorna classe visiva
        const cls = classify(updated);
        li.className = `collection-item ${cls}`;
        // rigenera HTML interno
        li.innerHTML = buildReminderHTML(updated);
        // riaggancia handler checkbox con dati aggiornati
        attachCheckboxHandler(li, updated);

        // aggiorna evento nel calendario
        if (calendar) {
          const ev = calendar.getEventById(updated.id);
          if (ev) {
            ev.setProp('title', updated.title + (updated.completed ? ' ✓' : ''));
            const clsArr = cls ? [cls] : [];
            ev.setProp('classNames', clsArr);
          }
        }

        // toast di conferma
        if (window.M && M.toast) {
          M.toast({
            html: updated.completed ? 'Nota completata' : 'Nota riaperta',
            classes: updated.completed ? 'green' : 'blue'
          });
        }
      }
    });
  }

  // ----------------- Rendering lista completa -----------------
  function renderList(data) {
    list.innerHTML = '';
    if (!data.length) {
      list.innerHTML = '<li class="collection-item">Nessuna scadenza.</li>';
      return;
    }

    data.forEach(r => {
      const cls = classify(r);
      const li = document.createElement('li');
      li.className = `collection-item ${cls}`;
      li.innerHTML = buildReminderHTML(r);
      attachCheckboxHandler(li, r);
      list.appendChild(li);
    });
  }

  // ----------------- Caricamento dati globali -----------------
  async function load() {
    const data = await fetchReminders(currentYear, currentMonth);
    renderList(data);

    calendar.removeAllEvents();
    calendar.addEventSource(data.map(r => {
      const cls = classify(r);
      return {
        id: r.id,
        title: r.title + (r.completed ? ' ✓' : ''),
        start: r.date,
        classNames: cls ? [cls] : []
      };
    }));
  }

  // ----------------- Init FullCalendar -----------------
  calendar = new FullCalendar.Calendar(calEl, {
    initialView: 'dayGridMonth',
    firstDay: 1,
    locale: 'it',
    height: 'auto',
    headerToolbar: { left: 'prev,next today', center: 'title', right: '' },

    dateClick: async (info) => {
      const title = prompt(`Nuovo appunto per ${info.dateStr}:`);
      if (!title) return;
      await fetch('/api/reminders/', {
        method: 'POST',
        headers: headersJSON,
        credentials: 'same-origin',
        body: JSON.stringify({ date: info.dateStr, title, details: '' })
      });
      await load();
    },

    datesSet: async (arg) => {
      const d = arg.view.currentStart;
      currentYear = d.getFullYear();
      currentMonth = d.getMonth() + 1;
      await load();
    }
  });

  calendar.render();
})();
