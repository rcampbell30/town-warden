# Roadmap

## Local Blackpool prototype

- Real-data-only mode
- Source health
- SQLite persistence
- History endpoint
- Analytics endpoint
- Deduplication
- Source refresh cooldown
- Developer controls
- Connector/agent refactor
- Schematic map

## Next technical upgrades

1. v3 Pattern Intelligence (implemented: rule-based insights for patterns, anomalies, source quality, and deduplication signals)
2. v4 dashboard split (implemented: Public Dashboard for shareable viewing, Developer Dashboard for diagnostics and controls)
3. Street Manager production integration (pending external approval)
4. Better zone mapping with ward/boundary polygons
5. Real map via Leaflet/OpenStreetMap
6. PostgreSQL migration
7. Authentication and admin-role controls for operations workflows
8. Deployment hardening for always-on public cloud operations
9. Tests and CI checks
10. Multi-town connector config

## Current safety posture

- Agent insights are rule-based and source-limited, and should never be treated as official authority advice.
- Street Manager webhook routes are live and awaiting external approval/notifications.
- Open-Meteo handling includes source-health visibility for throttling/rate limits.
- Developer routes are protected in production via `ADMIN_TOKEN`; local mode keeps developer workflow unblocked.
