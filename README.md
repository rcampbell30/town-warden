# Town Warden

Town Warden is a local civic-intelligence prototype for Blackpool.

It ingests public data, normalises it into civic events, deduplicates repeated source records, stores events in SQLite, runs rule-based agents, and displays live signals in a browser dashboard.

## Current demo status

This version is **demo-ready**, not production-ready.

It is suitable for:

- local demonstrations
- GitHub publishing
- portfolio/interview evidence
- explaining the architecture
- extending with more connectors

It is not yet suitable for unsupervised public production use.

## Current features

- FastAPI backend
- WebSocket live event stream
- SQLite persistence
- Real-data-only mode
- Police.uk connector
- Open-Meteo connector
- Street Manager connector stub
- Source health panel
- Deduplication guard
- Next source refresh countdown
- History endpoint and UI
- Analytics endpoint and UI
- Developer controls for local testing
- Modular connector/agent structure

## Folder structure

```text
town-warden/
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── storage.py
│   ├── requirements.txt
│   ├── connectors/
│   ├── agents/
│   ├── services/
│   └── README.md
├── frontend/
│   ├── index.html
│   └── README.md
├── docs/
├── scripts/
├── .env.example
├── .gitignore
├── LICENSE
└── README.md
```

## Quick start on Windows

Open PowerShell in this folder.

### Backend

```powershell
cd backend
py -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload
```

Backend runs at:

```text
http://127.0.0.1:8000
```

### Frontend

Open a second PowerShell window.

```powershell
cd frontend
py -m http.server 3000
```

Frontend runs at:

```text
http://localhost:3000
```

## Useful backend URLs

```text
http://127.0.0.1:8000/
http://127.0.0.1:8000/source-health
http://127.0.0.1:8000/history
http://127.0.0.1:8000/analytics
```

## Demo script

See:

```text
docs/DEMO_SCRIPT.md
```

## Production plan

See:

```text
docs/PRODUCTION_PLAN.md
```

## Important limitations

- Police.uk locations are approximate/anonymised.
- Current Blackpool zone mapping is rough coordinate mapping, not GIS boundary mapping.
- SQLite is for local development.
- Developer controls are not authenticated and must not be exposed publicly.
- Street Manager roadworks connector is stubbed until API access is configured.

## Licence

MIT License.
