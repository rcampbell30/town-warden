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

1. v3 Pattern Intelligence (implemented: rule-based developer insights for patterns, anomalies, source quality, and deduplication signals)
2. Street Manager production integration (pending external approval)
3. Better zone mapping with ward/boundary polygons
4. Real map via Leaflet/OpenStreetMap
5. PostgreSQL migration
6. Authentication and admin-role controls for operations workflows
7. Deployment hardening for always-on public cloud operations
8. Tests and CI checks
9. Multi-town connector config

## Current safety posture

- Agent insights are rule-based and source-limited, and should never be treated as official authority advice.
- Street Manager webhook routes are live and awaiting external approval/notifications.
- Open-Meteo handling includes source-health visibility for throttling/rate limits.
- Developer controls are protected/disabled in production contexts.
