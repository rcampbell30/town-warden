# Town Warden

Town Warden is an experimental civic-intelligence dashboard that combines public
data sources into a local civic picture. The default example is Blackpool, but
the project is designed to be adapted to other UK towns through configuration.

It is a civic-tech prototype and portfolio project. It is not an official
council, police, NHS, or emergency-service system.

## Live Demo

- Backend: https://town-warden.onrender.com
- Frontend: https://town-warden.netlify.app

## Architecture

- Backend: Python FastAPI
- Frontend: static HTML/CSS/JavaScript
- Local/default database: SQLite
- Production database option: PostgreSQL via `DATABASE_URL`
- Frontend hosting: Netlify
- Backend hosting: Render

## Data Sources

- Police.uk: public incident intelligence
- Open-Meteo: weather context
- Street Manager: live street works webhooks, filtered to the configured town area

## Main Features

- Source health and runtime status
- Civic risk and system health scoring
- Event history and analytics
- Map-ready civic signals with coordinate confidence
- Street Manager payload mapping, deduplication, and local-area filtering
- Source-aware agent insights
- Protected developer/admin routes
- Config-driven town settings through `TOWN_CONFIG`

## Screenshots

Add current dashboard screenshots here when preparing a public portfolio page:

- Public dashboard desktop
- Public dashboard mobile
- Developer diagnostics dashboard

## Key Endpoints

```text
GET  /
GET  /town-config
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
- `TOWN_CONFIG`: path to a town config JSON file. Defaults to `config/towns/blackpool.json`
- `ADMIN_TOKEN`: required to operate protected `/dev/*` routes in production
- `DATABASE_URL`: optional PostgreSQL URL. If missing, SQLite is used.
- `SOURCE_REFRESH_SECONDS`: source polling interval
- `ALLOW_SIMULATION`: defaults to disabled
- `EVENT_RETENTION_DAYS`: default `90`
- `ALERT_RETENTION_DAYS`: default `90`
- `RISK_SNAPSHOT_RETENTION_DAYS`: default `30`

Do not put `ADMIN_TOKEN`, `DATABASE_URL`, webhook secrets, or private keys in
frontend files.

## Adapting For Another Town

Town-specific settings live in `config/towns/`. To create a new town dashboard,
copy `config/towns/blackpool.json`, rename it, and edit the town name, map
centre, zones, bounding box, local authority keywords, source labels, and
footer/disclaimer text.

Set:

```text
TOWN_CONFIG=config/towns/your-town.json
```

See [docs/ADAPT_FOR_YOUR_TOWN.md](docs/ADAPT_FOR_YOUR_TOWN.md) for the full
clone/adapt workflow.

## Deployment

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Limitations

- Police.uk locations are approximate/anonymised.
- Street Manager relevance depends on available area fields, postcodes,
  authority names, coordinates, and the configured bounding box.
- Current zones are coarse unless you add stronger local mapping data.
- Agent insights are rule-based, source-limited, and experimental.
- The public dashboard must remain clearly labelled as not official authority
  advice.
