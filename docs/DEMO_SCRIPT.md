# Town Warden Demo Script

Use this when showing the project to someone else.

## 1. Start with the problem

Local services produce signals across separate systems: policing data, weather data, roadworks, waste, transport, council reports, and public complaints.

Humans rarely see the combined pattern early enough.

Town Warden is a prototype civic nervous system for one place: Blackpool.

## 2. Show the architecture

Open `docs/ARCHITECTURE.md` and explain:

```text
Connectors → Deduplication → Storage → Agents → Dashboard
```

The system is deliberately rule-based and explainable at this stage.

## 3. Start the backend

```powershell
cd backend
.\venv\Scripts\Activate.ps1
uvicorn main:app --reload
```

Open:

```text
http://127.0.0.1:8000/source-health
```

Explain that this is the raw API output.

## 4. Start the frontend

```powershell
cd frontend
py -m http.server 3000
```

Open:

```text
http://localhost:3000
```

## 5. Show Source Health

Point out:

- Police.uk connector
- Open-Meteo connector
- Street Manager pending connector
- Simulation disabled
- Deduplication guard
- Next source refresh countdown

Explain that repeated source records are not processed twice.

## 6. Show Live Civic Events

Explain that live events are normalised into one common format:

```text
type
location
text
source
source_event_id
real_data
```

## 7. Show Analytics Intelligence

Explain that the system is no longer just displaying events.

It is summarising stored signals into:

- total events
- total alerts
- real vs simulated count
- top locations
- most active agents
- duplicates skipped

## 8. Show History Intelligence

Use the filters to show stored events by type/source.

Explain that SQLite gives the prototype memory between backend restarts.

## 9. Show Developer Controls

Explain that these are local-only controls for development:

- force refresh
- clear live feed
- clear risk map
- reset local database

State clearly that production would require authentication before exposing these.

## 10. Close with the roadmap

Open `docs/PRODUCTION_PLAN.md`.

The most important next production step is the Street Manager roadworks API.
