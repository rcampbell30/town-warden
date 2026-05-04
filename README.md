Town Warden — Cloneable Civic Intelligence Dashboard for UK Towns
Town Warden is an open-source civic dashboard you can deploy for any UK town in an afternoon.
It combines three public data sources — Police.uk incident patterns, Open-Meteo weather context,
and Street Manager street works notifications — into a single plain-English view for residents
and local stakeholders.
The default instance runs for Blackpool. Your town is one config file away.
🌐 Live demo: town-warden.netlify.app
📖 Clone guide: docs/ADAPT_FOR_YOUR_TOWN.md
🗺️ Federation roadmap: docs/FEDERATION_ROADMAP.md
> **Not an official council, police, NHS, or emergency-service system.**
> Police.uk data is historical pattern data updated monthly — not live alerts.
> For emergencies: 999. Non-emergency: 101.
---
Clone This For Your Town
Town-specific settings live in a single JSON file under `config/towns/`.
```bash
# 1. Copy the Blackpool config
cp config/towns/blackpool.json config/towns/your-town.json

# 2. Edit your town name, map centre, bounding box, zones, and authority keywords
#    Full field reference: docs/ADAPT_FOR_YOUR_TOWN.md

# 3. Point the backend at your config
export TOWN_CONFIG=config/towns/your-town.json

# 4. Deploy
# Backend → Render (or any host running Python/FastAPI)
# Frontend → Netlify (or any static host)
```
See docs/DEPLOYMENT.md for the full deployment walkthrough.
---
What It Does
Civic risk scoring — a plain-English summary of current public-source signals for your area
Live source health — shows whether Police.uk, Open-Meteo, and Street Manager are feeding data
Signal map — street works, public incident markers, and risk zones on a filterable map
Resident-friendly insights — pattern summaries that explain what the data means locally, without overstating it
Street Manager webhooks — automatically filtered to your configured town bounding box
Protected admin routes — `/dev/*` endpoints require an `ADMIN_TOKEN` header in production
---
Architecture
Layer	Technology
Backend	Python · FastAPI
Frontend	Static HTML · CSS · JavaScript
Database	SQLite (local) · PostgreSQL (production)
Backend hosting	Render
Frontend hosting	Netlify
---
Why Police.uk Data Is Not Live
Police.uk street-level data is published retrospectively — usually monthly —
and coordinates are anonymised to a street segment, not an exact address.
Town Warden surfaces this data as resident-awareness pattern information,
not live incident alerts. The dashboard wording is deliberately careful about this.
Do not redeploy a clone that presents Police.uk records as live crime data.
---
Future: Town Warden Network
Each town runs its own fully independent instance today — its own backend, database,
sources, and config, with no dependency on any central server.
A future federation layer would let trusted Town Warden nodes share public-safe summaries
using a common schema, enabling cross-town pattern awareness without centralised surveillance
or raw data sharing. Federation is not implemented in v1.x.
Federation roadmap
Public summary schema
