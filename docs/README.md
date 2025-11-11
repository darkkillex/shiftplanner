# 🧭 ShiftPlanner

**Gestione turni aziendali e analisi operative**  
_Author: Nicola Mastrangelo_  
_Licenza: MIT_  
_Versione attuale: v0.7.2 (11/11/2025)_

---

## 🧩 Descrizione

**ShiftPlanner** è una web application sviluppata con **Django + DRF** e **PostgreSQL** in ambiente **Docker**, pensata per gestire e analizzare in modo centralizzato i turni del personale.  
Il sistema consente di creare **template di piano turni**, assegnare lavoratori ai turni giornalieri, inviare **notifiche automatiche via email**, e visualizzare **statistiche interattive** tramite Chart.js.

---

## ⚙️ Stack Tecnologico

| Componente | Descrizione |
|-------------|-------------|
| **Backend** | Django 5 + Django REST Framework |
| **Database** | PostgreSQL 15 (container dedicato) |
| **Frontend** | MaterializeCSS + Chart.js |
| **Container** | Docker Compose |
| **Backup** | pg_dump giornaliero schedulato |
| **Analisi** | Statistiche e KPI mensili filtrabili per azienda e periodo |

---

## 🚀 Avvio rapido

### 1️⃣ Clonazione repository
```bash
git clone https://github.com/<PRIVATE_USER>/shiftplanner.git
cd shiftplanner
```

### 2️⃣ Configurazione ambiente
Crea il file `.env` nella root del progetto:
```bash
POSTGRES_DB=shiftplanner
POSTGRES_USER=shiftplanner
POSTGRES_PASSWORD=shiftplanner
POSTGRES_HOST=db
POSTGRES_PORT=5432
DJANGO_SECRET_KEY=<chiave_segretissima>
EMAIL_HOST_USER=<email@example.com>
EMAIL_HOST_PASSWORD=<password>
```

### 3️⃣ Avvio servizi
```bash
docker compose up -d --build
```

Servizi disponibili:
- **Web:** http://localhost:8000  
- **DB:**  PostgreSQL sulla porta 5432

---

## 🧠 Funzionalità principali

- Creazione e gestione **Template di piano turni**.  
- Assegnazione dinamica dei lavoratori ai turni giornalieri.  
- Propagazione automatica delle modifiche dal template ai piani collegati.  
- Blocco assegnazioni duplicate o non valide.  
- Invio notifiche email personalizzate ai dipendenti.  
- Esportazione piani in formato **.xlsx**.  
- Dashboard “Statistiche” con **grafici interattivi** e KPI filtrabili.  
- Backup automatico del database ogni 24 ore.  
- Comandi di **verifica e sincronizzazione** per la coerenza Template ↔ Piano.

---

## 🔧 Manutenzione

Comandi di manutenzione integrità:

```bash
# Analisi e riallineamento template/piani (dry-run)
docker compose exec web python manage.py sync_template_plan_rows --verbose

# Applica correzioni effettive
docker compose exec web python manage.py sync_template_plan_rows --apply --verbose

# Audit di integrità e generazione report CSV
docker compose exec web python manage.py audit_template_plan_integrity
```

Backup manuale istantaneo:
```bash
docker compose exec backup sh -lc 'pg_dump -h db -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > /backups/manual_backup.sql.gz'
```

---

## 📊 Dashboard Statistiche

La sezione “Statistiche” consente di:
- Filtrare i dati per **azienda e periodo** (mese, trimestre, semestre, anno).  
- Visualizzare le unità impiegate nei vari **turni**.  
- Analizzare le mansioni contenenti la parola chiave **“Preposto”**.  
- Escludere automaticamente assenze, ferie, congedi e malattie dal conteggio dei turni attivi.

---

## 📚 Documentazione

| Documento | Descrizione |
|------------|-------------|
| `SHIFTPLANNER_RUNBOOK.md` | Istruzioni operative e comandi di deploy |
| `SHIFTPLANNER_TECHNICAL.md` | Architettura tecnica e strumenti di manutenzione |
| `SHIFTPLANNER_USER_GUIDE.md` | Manuale utente in formato .md / .pdf |
| `CHANGELOG.md` | Registro completo delle versioni e miglioramenti |

---

## 🧾 Licenza

Questo progetto è distribuito sotto licenza **MIT**.  
Vedi il file `LICENSE` per i dettagli.

---

## 💡 Note per i contributori

- Tutte le modifiche devono essere accompagnate da un **commit descrittivo** e un aggiornamento nel `CHANGELOG.md`.  
- Le pull request devono essere basate su branch `dev` e seguire la naming convention:
  ```
  feat/<feature-name>
  fix/<issue-name>
  docs/<section>
  ```
