# Architecture

Town Warden is split into four layers.

## 1. Connectors

Connectors fetch and normalise public data.

```text
backend/connectors/
├── police_uk.py
├── open_meteo.py
├── street_manager.py
└── simulation.py
```

Each connector returns standard Town Warden event dictionaries.

## 2. Persistence

`storage.py` handles SQLite tables for:

- events
- alerts
- risk snapshots

It also provides event deduplication through `source_event_id`.

## 3. Agents

Agents detect patterns and generate alerts.

```text
backend/agents/
├── primary.py
├── cascade.py
├── trend.py
└── zone.py
```

Primary wardens look at raw event types. Cascade wardens react to upstream signals. Trend and zone wardens detect acceleration and critical pressure.

## 4. API and dashboard

`main.py` exposes:

- `/ws`
- `/history`
- `/analytics`
- `/source-health`
- `/dev/*` controls

The frontend consumes those endpoints and displays a real-time control dashboard.
