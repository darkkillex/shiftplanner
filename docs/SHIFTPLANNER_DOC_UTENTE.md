# Kairos ShiftPlanner — Guida Utente

Ultimo aggiornamento: 11/11/2025

---

## 1. Accesso
Apri l’indirizzo dell’app (es. `http://localhost:8000` o dominio aziendale).  
Effettua il **login** con le credenziali assegnate.

> Gli utenti standard vedono solo i propri piani turni.  
> Lo staff può creare/modificare piani, template, assegnazioni e visualizzare statistiche.

---

## 2. Area principale (Hub Funzioni)
Dalla home vengono mostrate **card** per accedere alle funzioni principali:
- Piani mensili
- Template piani
- Note calendario
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
- Ogni riga rappresenta una mansione (es. “Magazzino.4”).  
- Ogni colonna corrisponde a un giorno del mese.  
- Le celle mostrano il nome del dipendente e il turno (es. “Rossi M (Mattino)”).

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
- Il sistema confronta le assegnazioni correnti con l’ultimo invio.  
- Solo i dipendenti con variazioni ricevono un’email.

### Contenuto email
- Oggetto: `Piano turni <Mese> <Anno>`  
- Corpo: saluto personalizzato, tabella turni, legenda codici.  
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

## 7. Backup e sicurezza dati
- I backup del database vengono creati **ogni notte alle 03:00**.
- I file si trovano nella cartella `backups/` (solo accesso staff tecnico).
- I backup vecchi di 1 giorno vengono rimossi.

---

## 8. Suggerimenti d’uso
- Filtri statistici: aggiornamento automatico → non serve cliccare “Applica”.  
- Usa browser desktop aggiornato (Chrome o Edge).  
- Evita modifiche simultanee sullo stesso piano da più utenti.  
- In caso di errore o piano bloccato → ricarica la pagina o contatta l’amministratore.

---

_Fine guida utente._
