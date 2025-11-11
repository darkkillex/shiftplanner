# Kairos ShiftPlanner — Runbook Operativo

Ultimo aggiornamento: 11/11/2025 (Europe/Rome)

## Obiettivo
Promemoria sintetico per avvio servizi, dashboard statistiche, backup DB e buone pratiche per gestori e sviluppatori.

---

## 1. Dashboard **Statistiche**
### Rotte
- `GET /analytics/` → pagina overview
- `GET /analytics/summary/` → JSON per KPI, grafici e tabelle

### Views (riassunto)
- `analytics_overview(request)` → carica pagina con filtri (azienda, date) e preset rapidi.
- `analytics_summary(request)` → parametri: `company_id`, `start`, `end`, `preset` in {`m1`,`q1`,`h1`,`y1`}.  
  Restituisce:
  - KPI:
    - `assignments_turno`: assegnazioni **al netto** delle mansioni di assenza/permesso.
    - `employees_assigned` di `employees_total`.
    - breakdown esclusioni.
  - Tabelle: per turno, Preposto.
  - Grafici: bar Chart.js (per turno, Preposto).

### Esclusioni dalle **Assegnazioni personale in turno**
Escluse se `profession__name` contiene:
```
Formazione, Ferie, Permessi, Congedo, Congedo Matrimoniale,
Permesso 104, Permesso Sindacale, Malattia, Assenza, Sciopero
```

### Template
`templates/analytics_overview.html`
- Toolbar preset rapidi (in alto): M1, Q1, H1, Y1.
- Filtri live: azienda, dal/al (input date).
- KPI card:
  - **Assegnazioni personale in turno**
  - **Dipendenti assegnati**: `X di Y`
  - Card dinamiche per ciascuna esclusione.
- Grafici: `<canvas id="ch-shift">`, `<canvas id="ch-preposto">`.
- Tabelle: `#tbl-shift`, `#tbl-preposto`.

### JavaScript esterno
`static/js/analytics_overview.js`
- Fetch **hardcoded** verso `/analytics/summary/`.
- Debounce 250 ms per filtro live.
- Distruzione e redraw dei grafici Chart.js a ogni fetch.
- Rigenerazione card di esclusione.
- Nota preset: visualizza range effettivo e filtro azienda.

> Nota: se in futuro vuoi evitare URL hardcoded, esporre `window.URLS.analyticsSummary` in `layout.html`.

---

## 2. Avvio servizi con Docker Compose
### Comando consigliato
```bash
docker compose up -d --build
```
Avvia/ricompila **web**, **db**, **backup**.

### Avvio selettivo
```bash
docker compose up -d --build web db backup
```

### Stato e log
```bash
docker compose ps
docker compose logs -f web
docker compose logs -f db
docker compose logs -f backup
```

---

## 3. Backup DB giornaliero
### Soluzione adottata (consigliata)
Immagine: `prodrigestivill/postgres-backup-local:15`

```yaml
backup:
  image: prodrigestivill/postgres-backup-local:15
  container_name: shiftplanner_backup
  depends_on:
    db:
      condition: service_healthy
  environment:
    POSTGRES_HOST: db
    POSTGRES_DB: ${POSTGRES_DB}
    POSTGRES_USER: ${POSTGRES_USER}
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    CRON_TIME: "0 3 * * *"    # ogni giorno alle 03:00
    BACKUP_KEEP_DAYS: "1"     # conserva 1 giorno
    BACKUP_KEEP_WEEKS: "0"
    BACKUP_KEEP_MONTHS: "0"
    TZ: "Europe/Rome"
  volumes:
    - ./backups:/backups
  restart: unless-stopped
```

#### Test immediato
```bash
docker exec -it shiftplanner_backup /usr/local/bin/backup
docker exec -it shiftplanner_backup ls -l /backups
```

#### Ripristino
```bash
gunzip -c backups/<file>.sql.gz | psql -h 127.0.0.1 -U ${POSTGRES_USER} -d ${POSTGRES_DB}
```

> In test manuale, se `pg_dump` chiede password, passa `PGPASSWORD` nell'env o usa lo script `/usr/local/bin/backup` dell'immagine.

---

## 4. Variabili d’ambiente (prod)
Impostare in `.env` (non committare):
```
POSTGRES_DB=shiftplanner
POSTGRES_USER=shiftplanner
POSTGRES_PASSWORD=<sicura>
EMAIL_HOST=<smtp>
EMAIL_HOST_USER=<utente>
EMAIL_HOST_PASSWORD=<password>
EMAIL_PORT=587
EMAIL_USE_TLS=1
APP_BASE_URL=https://<dominio>
REPLY_TO_EMAIL=ops@<dominio>
```
Riferite da Django e dal servizio `backup` via `env_file: .env` o `environment:`.

---

## 5. Indici e vincoli DB (performance)
Nel modello `Assignment` (Django `Meta`):
```python
constraints = [
    models.UniqueConstraint(fields=['plan','profession','date'], name='uniq_assignment_cell')
]
indexes = [
    models.Index(fields=['plan','date','profession']),
    models.Index(fields=['plan','date','employee']),
    models.Index(fields=['date']),
    models.Index(fields=['employee','date']),
    models.Index(fields=['profession','date']),
    models.Index(fields=['shift_type','date']),
]
```
Suggerito: aggiungere flag su `Profession` (`is_absence`, `is_preposto`) e usare questi al posto di `icontains` per scalabilità.

---

## 6. Troubleshooting rapido
- **Dashboard vuota**: controlla login, `Network` → chiamata `/analytics/summary/` deve essere `200`.  
- **Grafici enormi**: i `<canvas>` hanno wrapper con `style="height:320px"` e `maintainAspectRatio:false`.  
- **Backup non visibile** in Docker Desktop: avvia tutto con `docker compose up -d` (non solo `web`).  
- **Backup in loop**: usa l’immagine `prodrigestivill/postgres-backup-local:15`; evita shell script con `${ts}`.  
- **Permessi backup**: assicurati che la cartella `./backups` esista sulla macchina host.  

---

## 7. Comandi utili
```bash
# rebuild solo web senza toccare le dipendenze
docker compose up -d --no-deps --build web

# shell dentro il DB
docker exec -it shiftplanner_db psql -U ${POSTGRES_USER} -d ${POSTGRES_DB}

# dump manuale dentro il container di backup (con env)
docker exec -it -e PGPASSWORD=$POSTGRES_PASSWORD shiftplanner_backup sh -lc \
  'pg_dump -h db -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > /backups/manual.sql.gz'
```

---

## 8. Roadmap minima
- Flag `is_absence` e `is_preposto` su `Profession` + migrazione dati.
- Cache 60–120s per `/analytics/summary/` su preset noti.
- Job di retention/archiviazione annuale o partizionamento per anno su `Assignment`.
- `.env` separato prod/stage/dev e guida deploy.

---

## 9. Convenzioni progetto
- Script JS esterni: endpoint **hardcoded** o `window.URLS` in `layout.html`.
- Niente tag Django (`{% url %}`) dentro file `.js` statici.
- Aggiungi `backups/` a `.gitignore`.
- Evita dati sensibili nel repo (password, token).

---

_Fine._
