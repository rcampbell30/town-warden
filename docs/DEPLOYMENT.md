# Deployment

Town Warden is deployed as a static Netlify frontend and a FastAPI backend on
Render.

It is an experimental civic-intelligence prototype. It must not be presented as
official council, police, NHS, or emergency-service advice.

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
pytest
```

The tests use temporary SQLite databases and mocked source responses. They do
not call Police.uk, Open-Meteo, Street Manager, or production databases.

## Backend On Render

Create a Python web service.

Recommended start command:

```bash
cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT
```

Install dependencies from:

```text
backend/requirements.txt
```

## Backend Environment Variables

Required for production:

```text
ENVIRONMENT=production
ADMIN_TOKEN=<strong random value>
TOWN_CONFIG=config/towns/blackpool.json
```

Optional but recommended:

```text
DATABASE_URL=<Render PostgreSQL internal database URL>
SOURCE_REFRESH_SECONDS=60
EVENT_RETENTION_DAYS=90
ALERT_RETENTION_DAYS=90
RISK_SNAPSHOT_RETENTION_DAYS=30
```

`TOWN_CONFIG` can point at any checked-in town config JSON file. If it is
missing, the backend defaults to `config/towns/blackpool.json`.

Never expose `ADMIN_TOKEN`, `DATABASE_URL`, webhook secrets, or private keys in
frontend code.

## Render PostgreSQL

Create a Render PostgreSQL database and copy its internal database URL into the
backend service as:

```text
DATABASE_URL=<Render internal PostgreSQL URL>
```

If `DATABASE_URL` starts with `postgres://` or `postgresql://`, the backend uses
PostgreSQL and creates the required tables/indexes at startup.

If `DATABASE_URL` is missing, the backend uses the SQLite fallback. This keeps
local development simple and keeps the test suite lightweight.

The unique `source_event_id` index is created for deduplication in both SQLite
and PostgreSQL.

## Admin Routes

In production, all `/dev/*` routes require:

```text
x-admin-token: <ADMIN_TOKEN>
```

Protected routes:

```text
POST /dev/force-refresh
POST /dev/clear-live-feed
POST /dev/clear-risk-map
POST /dev/cleanup-retention
POST /dev/reset-database
```

The public frontend must not expose admin controls or tokens.

## Frontend On Netlify

Deploy the `frontend/` directory as static files.

The public dashboard automatically uses:

```text
https://town-warden.onrender.com
```

for the live backend, and local `127.0.0.1:8000` when served from localhost.

No frontend build step is required.

## Manual Redeploy Notes

- Render: redeploy the backend service after backend, config, or dependency
  changes.
- Netlify: redeploy after changes to `frontend/`.
- If a new town config is added, ensure the file is committed and `TOWN_CONFIG`
  points at the correct path.

## Verify Deployment

Check backend endpoints:

```text
GET /town-config
GET /runtime-status
GET /source-health
GET /analytics
GET /history
GET /map-data
GET /insights
```

`/runtime-status` should show:

- expected environment
- expected database backend
- dev routes protected in production
- active source counts
- system health and civic risk fields

`/source-health` should show Police.uk, Open-Meteo, Street Manager, and
Simulation. Street Manager should include `filtered_out_of_area` when local
geographic filtering is active.

## Safe Force Refresh

Use `/dev/force-refresh` only with the admin token in production:

```bash
curl -X POST https://your-backend.onrender.com/dev/force-refresh \
  -H "x-admin-token: <ADMIN_TOKEN>"
```

Do not store this token in frontend files or public documentation.
