# Kairos ShiftPlanner — Guida Utente

Ultimo aggiornamento: 11/11/2025

---

## 1. Accesso
Apri l’indirizzo dell’app (es. `http://localhost:8000` o dominio aziendale).  
Effettua il **login** con le credenziali assegnate.

> Lo staff può creare/modificare/inviare piani turno, gestire template piani turno e assegnazioni, visualizzare statistiche.

---

## 2. Area principale (Hub Funzioni)
Dalla home vengono mostrate **card** per accedere alle funzioni principali:
- Piani turno mensili
- Template piani turno
- Note calendario
- Previsione turnazione annuale
- Statistiche

### Card Statistiche
Mostra riepiloghi per turno e mansioni “Preposto”.  
Permette filtri per **azienda** e **periodo** con aggiornamento automatico (filtro live).

---

## 3. Gestione Piani Turni

### Creazione nuovo piano
1. Accedi come utente staff → “Gestione Piani”  
2. Clic su **Crea piano**
3. Seleziona mese, anno, template
4. Conferma → il piano viene generato con le righe del template.

> Se il piano per quel mese esiste già, l’app apre direttamente il piano esistente.

### Visualizzazione
- Ogni riga rappresenta una mansione (es. "Ufficio",“Magazzino”) e un turno al quale è legato
- Ogni colonna corrisponde a un giorno del mese.  
- Le celle mostrano il nome del dipendente (es. “Rossi Mario” - assegnato a mansione Ufficio ricadente nel Turno D -).

### Modifiche
- Clic su una cella → assegna o rimuovi dipendente e turno.  
- Le modifiche vengono salvate automaticamente.  
- I conflitti (stesso dipendente su più mansioni lo stesso giorno) sono segnalati.

### Note
- Clic sull’icona di nota nella cella → aggiungi o modifica testo.  
- Le note vengono incluse anche nei file Excel esportati.

---

## 4. Notifiche Email

### Invio notifiche
- Accessibile dalla pagina del piano → **“Invia notifiche”**
- La funzione Invia Notifiche permette di inviare automaticamente, tramite email, il piano turni aggiornato ai dipendenti che hanno una variazione rispetto all’ultimo invio.
- L’obiettivo è notificare solo chi ha realmente modifiche, evitando invii inutili e riducendo il rischio di confusione.

### Come funziona

- Quando l’utente Staff preme il pulsante “Invia Notifiche”:
  - Viene aperta una finestra di conferma, che avvisa l’utente del carattere potenzialmente impattante dell’azione.
  - Alla conferma, il sistema:
    - analizza il piano turni corrente
    - confronta ogni assegnazione con l’ultimo “snapshot” salvato
    - individua quali dipendenti hanno almeno una variazione 
    - prepara le email da inviare solo a questi destinatari
  - Per ogni dipendente con modifiche:
    - il sistema genera una email personalizzata con:
      - riepilogo dei turni
      - note associate alle giornate
    - invia la comunicazione all'indirizzo email registrato
  - A invio concluso:
    - viene aggiornato lo snapshot del piano per i soli dipendenti notificati
    - viene mostrato un riepilogo dei risultati tramite toast

### Cosa vede l'utente Staff dopo l'invio

- Un riepilogo che indica:
  - numero totale di dipendenti registrati in Kairos
  - numero di dipendenti coinvolti nel piano
  - quanti hanno un indirizzo email valido
  - quanti presentano modifiche reali da notificare
  - quante email sono state effettivamente inviate
  - elenco dei destinatari notificati
- In caso di errori SMTP, questi vengono inclusi nel report.

### Report CSV
- Dopo ogni invio viene scaricato automaticamente un file CSV contenente:
  - timestamp dell’invio (Europa/Roma)
  - nome del piano/mese
  - totale dipendenti con variazioni
  - lista dei destinatari coinvolti
  - per ciascun destinatario:
    - nome completo
    - email
    - esito invio (successo / errore)
    - eventuale messaggio di errore
- Questo file funge da log locale dell’invio effettuato.

### Quando viene inviata una notifica
- Una notifica viene inviata solo se:
  - il dipendente è presente nel piano con almeno un’assegnazione
  - l’indirizzo email è valido
  - almeno una sua giornata rispetto allo snapshot precedente è cambiata 
    (turno diverso, note cambiate, assegnazione aggiunta o rimossa)
- Se non ci sono modifiche, nessuna email viene generata.

### Contenuto email ricevuta dal lavoratore
- Oggetto: `Piano turni <Mese> <Anno>`  
- Corpo: saluto personalizzato, tabella turni.  
- Allegato: calendario personale in HTML e testo.

---

## 5. Dashboard Statistiche

### Accesso
Home → card **Statistiche** → “Apri dashboard”.

### Funzionalità
- Grafici **per turno** e **per Preposto**
- Tabelle riepilogative
- KPI principali:
  - **Assegnazioni personale in turno**
  - **Dipendenti assegnati di totale**
  - Card automatiche per ferie, permessi, assenze ecc.
- Filtri live:
  - Azienda
  - Intervallo date (dal/al)
  - Preset rapidi: ultimo mese, trimestre, semestre, anno

---

## 6. Esportazione Excel
Da ogni piano → “Esporta XLSX”  
Include:
- Giorni con intestazione e weekend in rosso
- Nomi dipendenti + turno
- Commenti per note
- Formattazione automatica (colonne 22px, intestazione colorata)

---

## 7. Previsione turnazione annuale
Questa funzione consente di generare automaticamente una pianificazione futura completa per un dipendente, a partire da:
- Turno iniziale (es. A, B, C, 12H-D, 12H-N, ecc.)
- Pattern lavoro/riposo (es. 4/2, 5/2, 7/7)
- Data di partenza
- Anno finale da raggiungere
- Esclusione festività calendario italiano

| Campo                    | Descrizione                                            |
| ------------------------ | ------------------------------------------------------ |
| Dipendente               | Destinatario della pianificazione                      |
| Turno                    | Tipo di turno di partenza                              |
| Giorni lavorativi        | Durata del primo ciclo di attività                     |
| Giorni riposo            | Numero di giorni consecutivi di riposo                 |
| Data di partenza         | Dal primo giorno utile                                 |
| Anno finale              | Il sistema crea turni fino al 31/12 dell’anno indicato |
| Escludi festività (opz.) | Se attivo: le festività nazionali diventano riposo     |

Logica dei pattern
- I turni si susseguono automaticamente.

Esempi:

| Turno iniziale | Pattern | Turno successivo |
| -------------- | ------: | ---------------- |
| A              |     4/2 | C → B → A …      |
| B              |     4/2 | A → C → B …      |
| C              |     4/2 | B → A → C …      |
| A              |     5/2 | B → A …          |
| B              |     5/2 | A → B …          |
| 12H-D          |     7/7 | 12H-N → 12H-D …  |
| 12H-N          |     7/7 | 12H-D → 12H-N …  |
Se il turno è diverso da quelli in elenco, non viene applicata una rotazione automatica.

Cosa viene generato

Per ogni mese nel periodo scelto:
- Un PDF con calendario mensile completo
- Una email automatica al dipendente
- Riepilogo testo/HTML nel corpo della mail

I PDF includono:
- Turno previsto per ogni giorno
- Riposi (inclusi quelli per festività se selezionato)
- Intestazione mese e dati del dipendente

N.B. La funzione è completamente indipendente dai piani turni attivi:
- non modifica il sistema reale di turnazione.

Output

Email al lavoratore che contiene:
- Oggetto: Previsione turnazione <Mese Inizio> <Anno> - Cognome Nome
- Testo descrittivo
- Allegati tutti i PDF, uno per mese

Download automatico ZIP

Contestualmente, lo Staff riceve il download di un archivio che contiene:
- tutti i PDF mensili generati
- README.txt con:
- anagrafica dipendente
- parametri usati per la generazione
- pattern lavoro/riposo
- turnazione di partenza
- flag festività
- timestamp della generazione (fuso Italia)

---

## 8. Report commessa
Riservato a **staff e amministratori**. Si apre dalla Home, pannello **Report commessa**.

### Fonte dei dati
- **Piani Kairos** (predefinita): scegli anno e intervallo di mesi e premi *Carica*. Vengono letti i piani
  turni salvati in Kairos. Un giorno senza assegnazione vale come riposo; le righe Ferie, Malattia,
  Formazione, Permessi ecc. vengono riconosciute come giustificativi.
- **File esterno**: trascina o scegli il piano turni ATI (`.xlsm` o `.xlsx`, massimo 60 MB). Il file viene
  solo letto: **nulla viene salvato in Kairos**. La lettura richiede circa 10-20 secondi.
  Formato atteso: fogli mese con "Numero mese" in A1, date dalla colonna H, matrice posizioni × giorni,
  blocco DIPENDENTE alla riga 813 e foglio "Dipendenti" (società, prescrizioni, contatti). I fogli nascosti
  vengono ignorati.

La barra sotto la fonte indica sempre da dove arrivano i dati che stai guardando.

### Sezioni
- **Scheda dipendente**: indicatori del periodo, nastro turni e calendario del mese (scegli il mese in alto),
  note di cella, mansioni svolte. P = preposto quel giorno; bordo giallo = nota nella cella.
- **Report dipendente**: ore lavorate, media, giorni da preposto, grafici per categoria, mese e mansione.
- **Ricerca per mansione**: chi ha svolto una mansione e quando; cerca anche nel testo delle note.
- **Preposti**: chi era preposto, in quale posizione e in che giorno, come scritto nel piano.
- **Riepilogo commessa**: ore erogate, giornate-uomo e risorse per attività, con filtro per mese e società.
- **Dati & export**: piani o fogli letti, anomalie del file, note su caselle senza nome, persone del file
  non presenti in Kairos, export CSV.

### Prescrizioni mediche
Dato facoltativo. Con la fonte Kairos si aggiunge o modifica dalla scheda dipendente (*Aggiungi* /
*Modifica*; testo vuoto = rimozione). Con il file esterno viene mostrato quello del foglio "Dipendenti".
Le prescrizioni sono visibili solo a staff e amministratori e **non sono incluse negli export CSV**.

### Convenzioni di calcolo
- Ore dei turni: dagli orari dei tipi turno di Kairos o dalla legenda del foglio MAIN del file.
- Ferie e permessi (PAR) valgono convenzionalmente 8 ore; la formazione 8 ore.
- Le celle "ERROR" del file sono mostrate come *Anomalia* e non sono conteggiate nelle ore.

---

## 9. Backup e sicurezza dati
- I backup del database vengono creati **ogni notte alle 03:00**.
- I file si trovano nella cartella `backups/` (solo accesso admin).
- I backup vecchi di 1 giorno vengono rimossi.

---

## 10. Suggerimenti d’uso
- Filtri statistici: aggiornamento automatico → non serve cliccare “Applica”.  
- Usa browser desktop aggiornato (Chrome o Edge).  
- Evita modifiche simultanee sullo stesso piano da più utenti.  
- In caso di errore o piano bloccato → ricarica la pagina o contatta l’amministratore.

---

_Fine guida utente._
