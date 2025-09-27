# Shift Planner (Django + Postgres + Docker)

## Avvio rapido
```bash
docker compose up -d --build
# (opzionale) seed dati e superuser admin/admin
docker exec -it shiftplanner_web python manage.py seed_demo
```

Apri: http://localhost:8000

## Login
- Crea un superuser da `/admin/` oppure esegui il seed (`admin` / `admin`).

## Funzionalità
- Griglia mensile stile Excel (professioni x giorni)
- Selezione multi-cella e applicazione lavoratore+turno alle celle selezionate
- Notifica email (console)
- Admin Django (master data e piani)
- API DRF (Session + JWT)

## Note
- Il web attende Postgres (wait_for_db), poi migrate + collectstatic.
- Le date sono inviate come `YYYY-MM-DD` (no toISOString) per evitare slittamenti UTC.
