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
* Style refactoring layout.html: separato <style> css e integrato in un sorgente specifico

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
* Celle - rimosso cod. Turno e inserita label 
* Aggiunto Campo Note (opzionale) da poter inserire all'atto dell'applicazione del turno
* Modifica/rimozione/aggiunta nota su cella, dopo doppio click su cella 
* Refactoring degli script JS in sorgenti dedicati 
* Bug fixing non corretta inizializzazione e visualizzazione allo scorrere del mouse, delle note presenti 
* Se lavoratore è presente su altre professioni lo stesso giorno, blocca inserimento 
* Inibire lato Area Amministrazione a utenti Staff 
* Aggiungere bottone e azione per estrazione del piano mensile in .csv/.xlsx 
* Homepage: rendere indipendente da sezione admin la funzione +Crea nuovo Piano 
* Applicare filtri tabella su Dipendenti (filtro live)
* Riposizionare componenti e tasti 
* Aggiunte icone material sui campi mancanti 
* Scorrere la tabella se l'utente seleziona tenendo il click del mouse premuto per scorrere e selezionare più giorni (non visibili)

# v0.1.3
* Applicare filtri tabella su Professioni (filtro live)
* Mostrare Nome e Cognome dell'utente connesso nella sezione Profilo
* Mostrare badge privilegi utente connesso nella sezione Profilo
* Riposizionare i bottoni e i menù nell'header (aggiungere separatori tra le scelte)

# v0.1.2
* Nella griglia, riportare oltre al numero del giorno, anche le iniziali (Es. Lun, mar, mer etc.)
* Nella griglia, colorare le intestazioni delle date festive in rosso 
* Aggiunto material design alla UI 
* Aggiunta responsività tabella 
* Aggiunta barra per scorrimento in orizzontale per ovviare al problema di navigazione derivante da grossa quantità di dati (Professioni)

# v0.1.1
* Aggiungere sulla barra in alto l'utente loggato 
* Aggiungere consultazione profilo utente loggato 
* Aggiungere funzione di cambio password

# v0.1.0
* Azione logout non funzionante 
* Creare azione/bottone "Rimuovi da celle selezionate" 
