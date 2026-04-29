# Deployment

Town Warden is deployed as a static Netlify frontend and a FastAPI backend on
Render.

Town Warden is an experimental civic-intelligence prototype. It must not be
presented as official council, police, NHS, or emergency-service advice.

## Backend on Render

Use a Python web service.

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
```

Optional but recommended for production:

```text
DATABASE_URL=<Render PostgreSQL internal database URL>
SOURCE_REFRESH_SECONDS=60
EVENT_RETENTION_DAYS=90
ALERT_RETENTION_DAYS=90
RISK_SNAPSHOT_RETENTION_DAYS=30
```

Street Manager pilot-area defaults:

```text
TOWN_WARDEN_AREA_NAME=Blackpool
TOWN_WARDEN_MIN_LAT=53.73
TOWN_WARDEN_MAX_LAT=53.90
TOWN_WARDEN_MIN_LNG=-3.10
TOWN_WARDEN_MAX_LNG=-2.95
```

Never expose `ADMIN_TOKEN`, `DATABASE_URL`, webhook secrets, or private keys in
frontend code.

## PostgreSQL

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

## Frontend on Netlify

Deploy the `frontend/` directory as static files.

The public dashboard automatically uses:

```text
https://town-warden.onrender.com
```

for the live backend, and local `127.0.0.1:8000` when served from localhost.

## Verification

After deployment, check:

```text
GET /source-health
GET /runtime-status
GET /analytics
GET /history
GET /map-data
GET /insights
```

Then load:

```text
https://town-warden.netlify.app
```

Confirm the dashboard still clearly separates System Health from Civic Risk and
shows the experimental/not-official disclaimer.
