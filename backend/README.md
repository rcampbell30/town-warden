# Backend

The backend is a FastAPI application.

It handles:

- public data ingestion
- source health checks
- deduplication
- SQLite persistence
- rule-based civic agents
- WebSocket streaming
- history and analytics APIs
- local developer controls

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
GET  /history
GET  /analytics
POST /dev/force-refresh
POST /dev/clear-live-feed
POST /dev/clear-risk-map
POST /dev/reset-database
WS   /ws
```

## Notes

The dev endpoints are for local development only. Do not deploy them publicly without authentication.
