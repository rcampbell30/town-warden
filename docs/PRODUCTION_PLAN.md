# Blackpool Production-Ready Plan

Town Warden is currently demo-ready. Production-ready means it can run online reliably, safely, and transparently for real users.

## Summary

Estimated path: **14 major steps**.

The Street Manager roadworks API is included as a required step because infrastructure/roadworks data is central to the Blackpool use case.

## Step 1 — Freeze the demo baseline

Goal: keep a stable version that can always be shown.

Tasks:

- Commit the demo-ready version to Git.
- Tag it as `v0.1-demo`.
- Keep README, docs, and quickstart working.

Exit criteria:

- Fresh clone runs locally from README alone.

## Step 2 — Add Street Manager roadworks API

Goal: replace the current roadworks stub with a real connector.

Tasks:

- Register for Street Manager/open roadworks data access.
- Store key/config outside code.
- Add connector implementation in `backend/connectors/street_manager.py`.
- Normalise works into Town Warden event format.
- Add `source_event_id` for deduplication.
- Add source-health metrics.

Exit criteria:

- Roadworks events appear in dashboard.
- Repeated roadworks records are not duplicated.

## Step 3 — Improve Blackpool location mapping

Goal: make zone/location intelligence credible.

Tasks:

- Replace rough coordinate thresholds with better boundary logic.
- Add ward/area labels if possible.
- Add confidence values.
- Show approximate street/area when available.

Exit criteria:

- Events distribute into plausible Blackpool areas.
- System explains location confidence.

## Step 4 — Add a real map layer

Goal: replace schematic boxes with a usable map.

Tasks:

- Add Leaflet/OpenStreetMap frontend map.
- Plot events by approximate coordinates where safe/available.
- Keep anonymisation clear.
- Show zone-level heat/risk overlays.

Exit criteria:

- Map shows current risk and recent events.

## Step 5 — Add automated tests

Goal: stop regressions as the project grows.

Minimum tests:

- storage save/read
- deduplication
- Police.uk normalisation with sample JSON
- Open-Meteo threshold events
- Street Manager normalisation
- analytics endpoint
- dev controls

Exit criteria:

- Tests run with one command.

## Step 6 — Move configuration to environment variables

Goal: remove hardcoded operational settings.

Tasks:

- Add `.env.example`.
- Read settings from environment variables.
- Keep safe defaults for local development.

Exit criteria:

- No API keys/secrets in code.

## Step 7 — Migrate SQLite to PostgreSQL

Goal: reliable production persistence.

Tasks:

- Add database URL config.
- Replace direct SQLite calls or add database abstraction.
- Add migrations.
- Keep SQLite for local demo mode if useful.

Exit criteria:

- Production database survives restarts/deployments.

## Step 8 — Add structured logging

Goal: understand failures without watching the terminal.

Tasks:

- Log source fetch attempts.
- Log connector failures.
- Log duplicate counts.
- Log database errors.
- Log WebSocket connections/disconnections.

Exit criteria:

- Source failures can be diagnosed from logs.

## Step 9 — Add authentication for developer controls

Goal: stop public misuse.

Tasks:

- Protect `/dev/*` endpoints.
- Use a local/deployment admin token.
- Hide controls unless authenticated.

Exit criteria:

- Anonymous users cannot reset DB or force source refresh.

## Step 10 — Deploy backend

Goal: get FastAPI online.

Tasks:

- Choose hosting provider.
- Configure start command.
- Configure environment variables.
- Attach PostgreSQL.
- Confirm WebSocket support.

Exit criteria:

- Backend URL is live and stable.

## Step 11 — Deploy frontend

Goal: get the dashboard online.

Tasks:

- Replace localhost URLs with deployed backend URLs.
- Use `wss://` for WebSocket.
- Deploy static frontend.

Exit criteria:

- Public frontend connects to deployed backend.

## Step 12 — Add transparency and disclaimers

Goal: make the system trustworthy.

Tasks:

- Explain sources.
- Explain approximate/anonymised locations.
- Explain limitations.
- Explain this is decision-support, not automated authority.

Exit criteria:

- A non-technical user can understand what the system does and does not claim.

## Step 13 — Run a Blackpool pilot period

Goal: observe behaviour before wider use.

Tasks:

- Run continuously for 2–4 weeks.
- Track connector uptime.
- Track duplicate behaviour.
- Track false positives.
- Tune thresholds.

Exit criteria:

- System produces useful, stable signals over time.

## Step 14 — Prepare multi-town expansion

Goal: make it reusable beyond Blackpool.

Tasks:

- Move town settings into config.
- Add multiple town profiles.
- Generalise zones.
- Document how to add a new town.

Exit criteria:

- A second town can be added without rewriting core code.

## Production-ready definition

Town Warden becomes Blackpool production-ready when:

- real connectors are stable
- roadworks data is live
- database is production-grade
- developer controls are protected
- deployment is reliable
- tests exist
- logs exist
- data limitations are transparent
- a pilot period has been completed
