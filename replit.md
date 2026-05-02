# Town Warden

A civic intelligence dashboard for UK towns that aggregates public data (Police.uk, Open-Meteo, Street Manager) to provide near real-time visualization of local civic risks, weather context, and street works.

## Architecture

- **Backend**: Python FastAPI on port 8000 (localhost), served via uvicorn
- **Frontend**: Vanilla HTML/CSS/JS static files served via Python's `http.server` on port 5000 (0.0.0.0)
- **Database**: SQLite (default/local) or PostgreSQL (when `DATABASE_URL` is set)
- **Real-time**: WebSockets from frontend to backend

## Project Structure

```
backend/        FastAPI application
  main.py       Main app, routes, WebSocket, data pipeline
  config.py     Environment variable configuration
  storage.py    SQLite/PostgreSQL persistence
  town_config.py Town config loader
  agents/       Rule-based warden agents
  connectors/   Data source connectors (police_uk, open_meteo, street_manager)
  services/     Shared services
  tests/        pytest test suite
frontend/
  index.html    Public civic dashboard
  dev.html      Developer diagnostic view
config/
  towns/        Town JSON config files (blackpool.json, example-town.json)
scripts/        Utility scripts
start.sh        Startup script (runs both backend and frontend)
```

## Running

The `Start application` workflow runs `bash start.sh`, which:
1. Starts FastAPI backend on `localhost:8000`
2. Starts static file server on `0.0.0.0:5000`

## Environment Variables

See `.env.example` for all options. Key ones:
- `ENVIRONMENT` — `local` or `production`
- `TOWN_CONFIG` — path to town JSON config (default: `config/towns/blackpool.json`)
- `DATABASE_URL` — PostgreSQL URL (leave blank for SQLite)
- `ADMIN_TOKEN` — admin API token
- `ALLOW_SIMULATION` — enable simulated data mode (`true`/`false`)

## Replit-Specific Notes

- Frontend detects `.replit.dev` / `.repl.co` domains and routes API calls to port 8000 on the same host
- Backend CORS allows `*.replit.dev` and `*.repl.co` origins
- Deployment configured as `vm` (always-running) since the app uses WebSockets and in-memory state
