# Backend

The backend is a FastAPI application.

It handles:

- public data ingestion
- source health checks
- deduplication
- SQLite persistence with optional PostgreSQL via `DATABASE_URL`
- rule-based civic agents
- WebSocket streaming
- history and analytics APIs
- protected developer/admin controls

## Run

```powershell
cd backend
py -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload
```

## Main endpoints

```text
GET  /
GET  /source-health
GET  /runtime-status
GET  /history
GET  /analytics
GET  /map-data
GET  /agent-log
GET  /insights
POST /dev/force-refresh
POST /dev/clear-live-feed
POST /dev/clear-risk-map
POST /dev/cleanup-retention
POST /dev/reset-database
WS   /ws
```

## Notes

In production, `/dev/*` endpoints require `x-admin-token` matching
`ADMIN_TOKEN`. Do not expose `ADMIN_TOKEN`, `DATABASE_URL`, or private webhook
secrets in frontend code.

If `DATABASE_URL` is missing, the backend uses SQLite. If `DATABASE_URL` starts
with `postgres://` or `postgresql://`, it uses PostgreSQL and creates required
tables/indexes at startup.
