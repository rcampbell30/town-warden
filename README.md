# Town Warden

Town Warden is an experimental civic-intelligence prototype for Blackpool. It
combines public-source signals from Police.uk, Open-Meteo, and Street Manager
webhooks, then presents source health, civic risk, map signals, history,
analytics, and rule-based agent insights.

It is a civic-tech prototype and portfolio project. It is not an official
council, police, NHS, or emergency-service system.

## Stack

- Backend: Python FastAPI
- Frontend: static HTML/CSS/JavaScript
- Local/default database: SQLite
- Production database option: PostgreSQL via `DATABASE_URL`
- Frontend hosting: Netlify
- Backend hosting: Render

## Current Sources

- Police.uk: public incident intelligence
- Open-Meteo: weather context
- Street Manager: live street works webhooks filtered to the Blackpool pilot area

## Key Endpoints

```text
GET  /
GET  /source-health
GET  /runtime-status
GET  /history
GET  /analytics
GET  /map-data
GET  /agent-log
GET  /insights
WS   /ws
POST /webhooks/street-manager/permits
POST /webhooks/street-manager/activities
POST /webhooks/street-manager/section-58
```

Protected development/admin routes:

```text
POST /dev/force-refresh
POST /dev/clear-live-feed
POST /dev/clear-risk-map
POST /dev/cleanup-retention
POST /dev/reset-database
```

In production, `/dev/*` routes require an `x-admin-token` header matching
`ADMIN_TOKEN`.

## Local Backend

```powershell
cd backend
py -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload
```

Backend runs at `http://127.0.0.1:8000`.

## Local Frontend

```powershell
cd frontend
py -m http.server 3000
```

Frontend runs at `http://localhost:3000`.

## Tests

```powershell
cd backend
pip install -r requirements.txt
pytest
```

Tests use temporary SQLite databases and mocked source responses. They do not
call Police.uk, Open-Meteo, Street Manager, or production databases.

## Environment Variables

- `ENVIRONMENT=local|production|test`
- `ADMIN_TOKEN`: required to operate protected `/dev/*` routes in production
- `DATABASE_URL`: optional PostgreSQL URL. If missing, SQLite is used.
- `SOURCE_REFRESH_SECONDS`: source polling interval
- `ALLOW_SIMULATION`: defaults to disabled
- `EVENT_RETENTION_DAYS`: default `90`
- `ALERT_RETENTION_DAYS`: default `90`
- `RISK_SNAPSHOT_RETENTION_DAYS`: default `30`
- `TOWN_WARDEN_AREA_NAME`: default `Blackpool`
- `TOWN_WARDEN_MIN_LAT`, `TOWN_WARDEN_MAX_LAT`, `TOWN_WARDEN_MIN_LNG`, `TOWN_WARDEN_MAX_LNG`: approximate pilot-area bounds

Do not put `ADMIN_TOKEN`, `DATABASE_URL`, webhook secrets, or private keys in
frontend files.

## Deployment

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Limitations

- Police.uk locations are approximate/anonymised.
- Street Manager is filtered to the Blackpool pilot area using available area
  fields, postcodes, and an approximate bounding box.
- Current Blackpool risk zones are coarse and not official GIS boundaries.
- Agent insights are rule-based, source-limited, and experimental.
- The public dashboard must remain clearly labelled as not official authority
  advice.
