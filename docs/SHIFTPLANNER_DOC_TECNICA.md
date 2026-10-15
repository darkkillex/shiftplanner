# Kairos ShiftPlanner — Documentazione Tecnica

Ultimo aggiornamento: 11/11/2025

---

## 1. Architettura generale

### Stack
- **Backend:** Django + Django REST Framework
- **Database:** PostgreSQL 15 (container Docker)
- **Frontend:** Template Django + MaterializeCSS + Chart.js
- **Containerizzazione:** Docker Compose (servizi: web, db, backup)
- **Email:** invii personalizzati via `EmailMultiAlternatives`
- **Backup:** `prodrigestivill/postgres-backup-local` con cron giornaliero

### Struttura principale
```
core/
  models.py
  views.py
  serializers.py
  forms.py
templates/
  analytics_overview.html
  monthly_plan.html
  emails/
    plan_personal.html
static/js/
  analytics_overview.js
docker-compose.yml
.env
```

### Servizi Compose
| Servizio | Funzione | Porta |
|-----------|-----------|--------|
| **web** | Django + DRF | 8000 |
| **db** | PostgreSQL 15 | 5432 |
| **backup** | Dump giornaliero | – |

---

## 2. Database e modelli principali

### Modelli core
- **Plan** → definisce mese/anno, nome e template associato.
- **PlanRow** → righe operative (mansioni) per ogni piano.
- **Assignment** → legame tra giorno, mansione, dipendente e turno.
- **Employee** → anagrafica lavoratore (azienda, email, nome).
- **Profession** → elenco mansioni, con nome univoco (es. “Magazzino.4”).
- **ShiftType** → definizione codici turno (es. M, P, N, R).
- **AssignmentSnapshot** → traccia invii email ai dipendenti.

### Vincoli e indici
```python
class Meta:
    constraints = [
        models.UniqueConstraint(fields=['plan','profession','date'], name='uniq_assignment_cell')
    ]
    indexes = [
        models.Index(fields=['plan','date','profession']),
        models.Index(fields=['employee','date']),
        models.Index(fields=['shift_type','date']),
    ]
```
> Garantisce integrità per cella e ottimizza interrogazioni per statistiche.

---

## 3. API REST (principali)

### `/api/plans/<id>/stats/`
Statistiche singolo piano.  
Restituisce:
```json
{
  "totals": {"assignments": 120, "employees": 18},
  "series": {
    "per_day": [3,4,5,...],
    "per_profession": {"Magazzino":12,"Preposto":8},
    "per_shift": {"M":30,"P":20,"N":10},
    "top_employees": [{"name":"Rossi M","n":8}, ...]
  }
}
```

### `/analytics/summary/`
Endpoint interno per dashboard globale. Parametri:
`company_id`, `start`, `end`, `preset` (m1,q1,h1,y1).  
Restituisce KPI, grafici, tabelle JSON per Chart.js.

---

## 4. Flusso dati e logica

1. **Creazione piano** → da template → genera PlanRows e accredita Profession.  
2. **Assegnazioni** → create o aggiornate da UI (bulk_assign API).  
3. **Notifica email** → differenziale rispetto all’ultimo snapshot mensile.  
4. **Statistiche** → calcolate via ORM e aggregate per periodo.  
5. **Backup DB** → dump compresso `.sql.gz` ogni notte.

---

## 5. Deploy e ambienti

### File `.env`
```
POSTGRES_DB=shiftplanner
POSTGRES_USER=shiftplanner
POSTGRES_PASSWORD=<sicura>
EMAIL_HOST=smtp.<dominio>
EMAIL_HOST_USER=notifiche@<dominio>
EMAIL_HOST_PASSWORD=<password>
EMAIL_PORT=587
EMAIL_USE_TLS=1
APP_BASE_URL=https://shiftplanner.<dominio>
REPLY_TO_EMAIL=ops@<dominio>
```

### Comandi deploy
```bash
# build e avvio servizi
docker compose up -d --build

# verifica stato
docker compose ps

# logs
docker compose logs -f web
```

### Backup in produzione
Automatizzato con container dedicato (`restart: unless-stopped`).  
I dump vengono salvati in `./backups` o volume remoto.  

Ripristino:
```bash
gunzip -c backups/<file>.sql.gz | psql -h 127.0.0.1 -U ${POSTGRES_USER} -d ${POSTGRES_DB}
```

---

## 6. Logging e monitoraggio

- Log applicativi Django: console → `docker logs shiftplanner_web`
- Log DB: accesso container → `docker logs shiftplanner_db`
- Log backup: `docker logs shiftplanner_backup`
- Errori email: tracciati in `PlanViewSet.notify()` via `logger.exception()`

---

## 7. Sviluppo e manutenzione

### Migrazioni
```bash
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py migrate
```

### Superuser
```bash
docker compose exec web python manage.py createsuperuser
```

### Utenti in sola lettura
Profilo "Sola lettura": utente staff + gruppo `Sola lettura` (gruppo creato dalla migrazione
`reports.0002_gruppo_sola_lettura`). Logica in `core/readonly.py`:
`ReadOnlyMiddleware` rifiuta (403) ogni POST/PUT/PATCH/DELETE tranne `password_change`,
`reports:excel_dataset` e `reports:import_prescriptions` con `mode=preview`; blocca anche le pagine
`plan_create`, `template_create` e la previsione turnazione. Il context processor `readonly_context`
espone `IS_READONLY` ai template (classe `ro-mode` sul body, elementi `.ro-hide` nascosti).
I superuser non sono mai limitati, anche se nel gruppo.
```bash
docker compose exec web python manage.py utente_sola_lettura mario.rossi --nome Mario --cognome Rossi   # chiede la password
docker compose exec web python manage.py utente_sola_lettura mario.rossi --rimuovi                        # torna staff normale
docker compose exec web python manage.py utente_sola_lettura --elenco
```

### Shell
```bash
docker compose exec web python manage.py shell_plus
```

### Aggiornamento pacchetti
`requirements.txt` in root → rebuild con `docker compose build web`.

---

## 8. Sicurezza e performance
- Password DB solo in `.env` (non nel repo).
- Backup compressi e ruotati (1 giorno).
- Indici DB sui campi usati in filtri e join.
- Uso di `select_related` in tutte le query aggregate.
- Cache raccomandata per `/analytics/summary/`.
- Accesso dashboard statistiche limitato a staff.
- Profilo "Sola lettura" con blocco delle scritture lato server (vedi §7, Utenti in sola lettura).

---
## 9. Manutenzione e strumenti di verifica
- Verificare e riallineare la coerenza tra TemplateRow e PlanRow:

| Comando                                                                                  | Descrizione                                                                                                                                 | Esempio d’uso                                       |
| ---------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------- |
| `python manage.py sync_template_plan_rows --verbose`                                     | Analizza e riallinea automaticamente le righe dei piani rispetto al template (per ordine). Non modifica nulla se non si aggiunge `--apply`. | Da usare dopo interventi manuali o import massivi.  |
| `python manage.py sync_template_plan_rows --apply --verbose`                             | Applica effettivamente le correzioni: crea, aggiorna o rimuove righe incoerenti.                                                            | Eseguire **solo dopo un backup** del database.      |
| `python manage.py audit_template_plan_integrity`                                         | Verifica l’integrità di tutti i piani e template, senza modificarli, e genera un file CSV riepilogativo delle differenze.                   | Utile per controllo mensile o prima di una release. |
| `python manage.py audit_template_plan_integrity --output /app/staticfiles/integrity.csv` | Stessa verifica ma con percorso personalizzato per il report.                                                                               | Per archiviazione o audit automatizzati.            |


## 10. Modulo Report commessa (app `reports`)

### Struttura
```
reports/
  models.py          EmployeeMedicalInfo (OneToOne su core.Employee): prescrizioni mediche
  admin.py           admin dedicato + inline nella scheda Dipendente (aggiunto senza toccare core/admin.py)
  engine.py          legenda codici, categorie, ore, DatasetBuilder (formato dati comune)
  source_kairos.py   adattatore: Plan / PlanRow / Assignment  -> dataset
  source_excel.py    adattatore: piano turni ATI .xlsm/.xlsx  -> dataset
  xlsx_reader.py     lettore XLSX veloce (iterparse sull'XML, solo colonne utili + commenti)
  views.py, urls.py  pagina + API JSON (solo staff/superuser)
  templates/reports/report_commessa.html
  static/reports/report_commessa.{js,css}
  tests.py
```

### Endpoint (prefisso `/report-commessa/`)
| Metodo | URL | Descrizione |
|---|---|---|
| GET | `/` | pagina del report |
| GET | `api/kairos/?year=2026&from=1&to=12` | dataset dai piani Kairos |
| POST | `api/excel/` (multipart `file`) | dataset dal file Excel; nessuna scrittura su DB |
| POST | `api/prescrizioni/<employee_id>/` `{"text": "..."}` | salva/rimuove le prescrizioni |
| POST | `api/prescrizioni/import/` (multipart `file`, `mode=preview\|apply`, `clear_missing`) | import dal foglio Dipendenti |

Le API rispondono 401/403 in JSON a utenti non autenticati o non staff; le risposte dataset sono compresse (gzip).

### Dataset comune
Entrambi gli adattatori producono lo stesso JSON (vedi docstring di `engine.py`): persone, tabella mansioni,
record giornalieri `[persona, data, codice, categoria, ore, mansione, preposto, nota, autore, area, nota posizione]`,
registro preposti, diagnostica. Il front-end fa solo filtri, aggregazioni e grafici (Chart.js 4.4.1).

### Mappatura piani Kairos
- `PlanRow.duty` senza suffisso `.N` = posizione/mansione; riga con "Preposto" = preposto del giorno.
- Codice giornata: turno dell'assegnazione, altrimenti turno della riga; le righe Ferie/Malattia/Formazione/…
  sono riconosciute anche dal nome (`ROW_KEYWORDS` in `engine.py`).
- Più assegnazioni della stessa persona nello stesso giorno: prevale quella di lavoro; le ore si contano una volta.
- Ore: durata del `ShiftType` (gestisce lo scavalco della mezzanotte); 00:00-00:00 = orario non definito.

### Prescrizioni mediche
Modello separato da `Employee` per tenerle fuori da `/api/employees/`, dall'elenco dipendenti e dagli export.
Migrazione `reports/0001_initial` (dipende solo da `core/0001_initial`).

### Import prescrizioni da riga di comando
Logica in `reports/presc_import.py`, condivisa con il pulsante del report.
```bash
python manage.py import_prescrizioni /percorso/Piano_Turni_ATI_2026.xlsm                 # anteprima
python manage.py import_prescrizioni /percorso/Piano_Turni_ATI_2026.xlsm --apply --user admin
# --clear-missing: rimuove da Kairos le prescrizioni vuote nel file
```
In Docker: `docker cp Piano.xlsm shiftplanner_web:/tmp/piano.xlsm` e poi
`docker compose exec web python manage.py import_prescrizioni /tmp/piano.xlsm`.

### Import anagrafica dipendenti
Logica in `core/employee_import.py`. Colonne riconosciute dall'intestazione: Cognome, Nome, Azienda/Società,
Telefono, E-mail, Matricola (facoltativa; se manca, matricola = telefono). Abbinamento per email, poi
matricola, poi "Cognome Nome". La matricola dei dipendenti esistenti non viene mai cambiata.
```bash
python manage.py import_dipendenti /percorso/Personale.xlsx                 # anteprima
python manage.py import_dipendenti /percorso/Personale.xlsx --apply
# --deactivate-missing: disattiva (is_active=False) chi è in Kairos ma non nel file
```
In Docker: `docker cp Personale.xlsx shiftplanner_web:/tmp/personale.xlsx` e poi
`docker compose exec web python manage.py import_dipendenti /tmp/personale.xlsx --apply`.

### Import piani turni dal file Excel ATI
Logica in `reports/plan_import.py`. Per ogni mese: Template «Template ATI <Mese Anno>» (posizioni col. E,
turno col. D, area/POS col. B nelle note, righe vuote = separatori), Plan creato dal template come in
`core.views.plan_create` (slot `Posizione.N`), Assignment con turno di riga e nota dal commento di cella.
I dipendenti devono esistere già (vedi import anagrafica); nomi non trovati vengono saltati e segnalati.
```bash
python manage.py import_piano_turni /percorso/Piano_Turni_ATI_2026.xlsm --mesi 2026-10,2026-11,2026-12            # anteprima
python manage.py import_piano_turni /percorso/Piano_Turni_ATI_2026.xlsm --mesi 2026-10,2026-11,2026-12 --apply
# --replace: se il piano del mese esiste già lo cancella (con le assegnazioni) e lo ricrea
```
In Docker: `docker cp Piano.xlsm shiftplanner_web:/tmp/piano.xlsm` e poi
`docker compose exec web python manage.py import_piano_turni /tmp/piano.xlsm --mesi ... --apply`.

### Test
```bash
python manage.py test core reports --settings=shiftplanner.settings_test
```
`settings_test` crea lo schema dai modelli invece che dalle migrazioni, perché le migrazioni di `core`
presenti nel repository non sono allineate ai modelli attuali.

_Fine documento tecnico._
