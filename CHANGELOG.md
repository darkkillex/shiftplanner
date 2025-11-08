# v0.6.0
* Ristrutturata home page - aggiunta di card dedicate alle varie funzioni disponibili
* Resa materialize pagina Profilo
* Resa materialize pagina cambio password

# v0.5.3
* Inserita possibilità di inserimento mansione nel template PT, con conseguente modifica a cascata sui PT legati al template oggetto di modifica
* Resa obbligatoria la selezione di Turno all'atto dell'assegnazione del lavoratore sul PT
* Aggiunto footer materialize
* Aggiunta pagina Informativa privacy

# v0.5.2
* Le pagine PT e template PT sono state rese materialize e corredate di filtri live
* Integrata colorazione alle righe mansioni nella tabella PT, per maggiore leggibilità delle righe

# v0.5.1
* Feedback notifica selettiva maggiormente dettagliata
* Download automatico del report di invio notifiche

# v0.5.0
* Implementata notifica selettiva solamente per i lavoratori che subiscono modifiche al piano turni del mese

# v0.4.5
* Bugfix: non veniva mostrato tutto il testo contenuto nel changelog accessibile dall'iperlink della vers.
* Fissata navbar
* Cambio del colore navbar a Pantone 308

# v0.4.4
* Adeguata pagina "nuovo template PT" al material style
* Homepage: inserito un calendario che permette di inserire delle note/appunti
* Menù a tendina PT -Lavoratore-: ordinata lista lavoratori per cognome-nome
* Menù a tendina PT -Turno- e legenda notifiche: ordinata lista turni per id

# v0.4.3
* Aggiunto nel lato admin la gestione dei template PT (inclusa la clonazione del template)
* Aggiunta la possibilità di clonare i Plan (solo struttura/con assegnazioni)

# v0.4.2
* Corretta la gestione delle mansioni duplicate nei template e nel backend(gestione separata da convenzione '.NUMERO')
* Visualizzazione Lista dei template in memoria
* Aggiornamento Seed Professions per base di partenza lista mansioni

# v0.4.1
* Aggiunto nel footer della notifica email il nome dell'utente che ha generato la revisione del PT ricevuto
* Aggiunta nel footer dell'app la versione(dinamica) dell'applicazione e la consultazione del changelog
* Style refactoring layout.html: separato style css e integrato in un sorgente specifico

# v0.4.0
* Funzionalità di invio del piano turni specifico piano turni a dipendenti in turno 
* Aggiunto il tracking n° di Rev. del Piano turni generato sulla base degli invii effettuati via email 
* Aggiunti elementi visivi (icone)
* Accesso lato admin ristretto ai soli superusers

# v0.3.0
* Aggiunta azione di download piano turni in formato .xlsx
* Controllo duplicati assegnazione turno su stesso per il dipendente
* Griglia piano turni scrollabile tramite DnD

# v0.2.0
* Celle - rimosso cod. Turno e inserita label dedicata
* Aggiunto Campo Note (opzionale) da poter inserire all'atto dell'applicazione del turno
* Modifica/rimozione/aggiunta nota su cella, dopo doppio click su cella 
* Refactoring degli script JS in sorgenti dedicati 
* Bug fixing non corretta inizializzazione e visualizzazione allo scorrere del mouse, delle note presenti 
* Inserito blocco inserimento del lavoratore se già presente su altre mansioni lo stesso giorno
* Inibito lato Area Amministrazione a utenti Staff 
* Aggiunta azione per estrazione del piano mensile in .csv/.xlsx 
* Homepage: reso indipendente da sezione admin la funzione +Crea nuovo Piano 
* Inserito filtro live sulla tabella Dipendenti
* Riposizionati componenti e tasti secondo logiche più coerenti 
* Aggiunte icone material sui campi mancanti 
* Aggiunto scorrimento della tabella tramite click-and-hold del mouse per scorrere e selezionare più giorni (non visibili)

# v0.1.3
* Inserito filtro live sulla tabella Professioni
* Inseriti nome e cognome dell'utente connesso nella sezione Profilo
* Inserito badge privilegi utente connesso nella sezione Profilo
* Riposizionati i bottoni e i menù nella navbar

# v0.1.2
* Aggiunta nella griglia PT, iniziali del giorno (Es. Lun, mar, mer etc.)
* Aggiunta nella griglia, colorazione intestazioni delle date festive in rosso 
* Aggiunto material design alla UI 
* Aggiunta responsività tabella 
* Aggiunta barra per scorrimento in orizzontale per ovviare al problema di navigazione derivante da grossa quantità di dati (Professioni)

# v0.1.1
* Aggiunta sulla navbar profilo utente loggato 
* Aggiunta consultazione profilo utente loggato 
* Aggiunta funzione di cambio password

# v0.1.0
* Bugfix: azione logout non funzionante 
* Creata azione "Rimuovi da celle selezionate" 
