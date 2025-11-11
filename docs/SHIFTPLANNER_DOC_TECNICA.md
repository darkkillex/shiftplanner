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

---

_Fine documento tecnico._
