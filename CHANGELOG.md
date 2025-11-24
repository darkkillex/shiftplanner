# v0.7.8
### 🛠️ Miglioramenti
* Nuovo report CSV completo (timestamp, metadati del piano, stato per destinatario, errori SMTP).
* Toast di notifica migliorato con dettagli su invii riusciti ed errori.
* Modal di conferma invio più sicuro e chiaro.
* Backend notify() reso più robusto con log per destinatario.


# v0.7.7
### 🐞 Bugfix
* Corretto il sistema di generazione delle Profession dai template: eliminata la creazione eccessiva di suffissi (es. Ufficio.5+.6+.7…). Ora il numero di slot per mansione cresce solo quando serve realmente.
* Risolto problema di visualizzazione del logo navbar dalla pagina del registro delle versioni.

### 🛠️ Miglioramenti
* Riorganizzate le interazioni di stile e il testo contenuto nel registro delle versioni.

# v0.7.6
### 🛠️ Miglioramenti
* Salvata la posizione di ultimo scroll delle righe della grid PT dopo assegnazione/rimozione personale su turno
* Salvati eventuali filtri applicati dopo assegnazione/rimozione personale su turno.
* Aggiunta conferma invio notifiche: introdotto un modal di avviso prima dell’invio massivo delle email, per evitare invii accidentali e rendere l’azione più sicura.

# v0.7.5
### 🛠️ Miglioramenti
* Aumentato il limite di caratteri per mappare il nome di professioni fino a 200 caratteri.
* Reso obbligatorio il campo "Nome piano" all'atto di creazione di un nuovo PT.
* Resa materialize la pagina di creazione di un nuovo PT.

### 🐞 Bugfix
* Corretto script di generazione del suffisso (.#) professioni che non risultava essere sequenziale.

# v0.7.4
### 🛠️ Miglioramenti
* Aggiunta campo "telefono" al Dipendente
* Aggiunta nuova pagina “Elenco dipendenti” con:
  - tabella cognome/nome/azienda/telefono/email
  - filtro live per nome/cognome/email/telefono
  - filtro per azienda (select Materialize)
  - contatore dinamico dei risultati
  - bottone “Pulisci filtri”
* Aggiunto file JS dedicato per la gestione dei filtri (employees_directory.js).
* Inserita card “Elenco dipendenti” nella home.
* Allineato lo stile della pagina agli altri moduli (header, filtri e responsive design).

# v0.7.3
### ✨ Nuove funzionalità
* Aggiunta card Documentazione.
* Documentazione utente aggiornata(rev. flusso funzionalità).

### 🛠️ Miglioramenti
* Aggiornamento scadenze:
  * La pagina Scadenze è stata migliorata e resa più chiara: il calendario ora è il fulcro della schermata.
  * È possibile vedere chi ha creato una nota e chi l’ha chiusa, con data e ora.
  * Quando si completa o si riapre una nota viene chiesta conferma per evitare errori.
  * Le note si aggiornano subito, sia nella lista sia nel calendario.
  * Aggiunti messaggi visivi per conferma delle azioni.
  * Migliorata la gestione delle note anche dal pannello admin.


# v0.7.2
### ✨ Nuove funzionalità
* Rimozione delle **righe mansione** nei template del piano turni, con **propagazione automatica** ai piani collegati.  
* **Blocco di sicurezza**: impedita l’eliminazione di righe con assegnazioni attive.  
* Comandi di **verifica e riallineamento** tra `TemplateRow` e `PlanRow`:
  * `sync_template_plan_rows` per riallineare automaticamente i piani.
  * `audit_template_plan_integrity` per generare report CSV di integrità.

### 🛠️ Miglioramenti
* Propagazione degli **ordini** fra template e piani più stabile.  
* Script JS separato (`template_detail.js`) per la gestione delle righe nel template.  
* Documentazione tecnica aggiornata (manutenzione e strumenti).

---

# v0.7.1
### ✨ Nuove funzionalità
* **Backup automatico giornaliero** del database (pg_dump schedulato).  
* Aggiunta **documentazione tecnica**, **manuale utente** e **runbook operativo**.

---

# v0.7.0
### ✨ Nuove funzionalità
* Pagina **Statistiche** con filtri per azienda e periodo, grafici (Chart.js) e tabelle riepilogative.  
* KPI su turni, mansioni “Preposto” e conteggi esclusioni (ferie, permessi, ecc.).

---

# v0.6.1
### 🛠️ Miglioramenti
* Evidenziazione in rosso nel calendario per **sabati, domeniche e festività italiane**.  
* Email di notifica piano turni **snellita** e più leggibile.

---

# v0.6.0
### ✨ Nuove funzionalità
* **Home page** ristrutturata con card funzionali.  
* Adozione **Material Design** per Profilo e Cambio password.

---

# v0.5.3
### ✨ Nuove funzionalità
* **Inserimento riga mansione** nel template con propagazione ai piani derivati.  
* Reso **obbligatorio** il campo **Turno** in fase di assegnazione.  
* Aggiunti **footer Materialize** e **pagina Informativa Privacy**.

---

# v0.5.2
### 🖌️ UI/UX
* Pagine **Piano Turni** e **Template** portate a **Materialize**, con **filtri live**.  
* Colorazione alternata/tematica delle righe mansioni per migliorare la leggibilità.

---

# v0.5.1
### 🛠️ Miglioramenti
* Report notifica selettiva **più dettagliato**.  
* **Download automatico** del report di invio notifiche.

---

# v0.5.0
### ✨ Nuove funzionalità
* **Notifica selettiva** ai soli dipendenti con modifiche nel piano mensile.

---

# v0.4.5
### 🐞 Bugfix
* Corretto il rendering del testo del changelog nel popup versione.

### 🛠️ Miglioramenti
* Navbar resa **fissa** e aggiornata al colore **Pantone 308**.

---

# v0.4.4
### ✨ Nuove funzionalità
* **Calendario con note** in homepage.  
* Ordinamento menu a tendina: **Lavoratori** per cognome-nome, **Turni** per ID.  
* Pagina “Nuovo Template PT” allineata a **Material Design**.

---

# v0.4.3
### ✨ Nuove funzionalità
* Gestione **Template PT** lato admin, inclusa **clonazione template**.  
* Possibilità di **clonare i piani** (solo struttura o con assegnazioni).

---

# v0.4.2
### 🛠️ Miglioramenti
* Gestione mansioni duplicate via convenzione `.<NUMERO>` in template e backend.  
* Visualizzazione **lista template** disponibile lato admin.  
* Aggiornato **seed professioni** per base mansioni.

---

# v0.4.1
### ✨ Nuove funzionalità
* Nome dell’utente che genera la revisione **incluso nel footer** dell’email.  
* Footer app con **versione dinamica** e **changelog** consultabile.  
* Refactoring layout: **CSS separato** in file dedicato.

---

# v0.4.0
### ✨ Nuove funzionalità
* **Invio piano turni via email** ai dipendenti.  
* **Tracking revisioni** del PT in base agli invii.  
* Interfaccia amministrativa **ristretta ai superuser**.

---

# v0.3.0
### ✨ Nuove funzionalità
* **Export Excel (.xlsx)** del piano turni.  
* Blocco **duplicati assegnazione** per dipendente.  
* Scorrimento griglia tramite **drag & drop**.

---

# v0.2.0
### ✨ Nuove funzionalità
* **Label turno** nelle celle al posto del codice.  
* Campo **Note** opzionale all’atto dell’assegnazione.  
* **Modifica/rimozione/aggiunta** nota su doppio click.  
* Blocco inserimento se il lavoratore è già assegnato altrove nello stesso giorno.  
* Azione di export piano mensile in **CSV/XLSX**.  
* Home: azione **Crea nuovo piano** indipendente dalla sezione admin.  
* Refactoring JS in **sorgenti dedicati**.

### 🖌️ UI/UX
* Scorrimento tabella tramite **click-and-hold** per selezione su più giorni.  
* Riposizionamento componenti e tasti per coerenza.  
* Icone Material aggiunte sui campi mancanti.

---

# v0.1.3
### 🖌️ UI/UX
* **Filtro live** sulla tabella Professioni.  
* Mostrati **nome e cognome** dell’utente nel profilo.  
* Badge **privilegi utente** visibile nel profilo.

---

# v0.1.2
### 🖌️ UI/UX
* Introdotta colorazione rossa per **date festive**.  
* Aggiunto **Material Design** e **responsività** alle tabelle.  
* Barra di scorrimento **orizzontale** per molte professioni.

---

# v0.1.1
### ✨ Nuove funzionalità
* **Profilo utente loggato** in navbar e pagina dedicata.  
* Funzione **cambio password**.

---

# v0.1.0
### 🚀 Prima versione
* Funzionalità base di gestione piani turni.  
* Azione **“Rimuovi da celle selezionate”**.  
* Bugfix: **logout** non funzionante.

---