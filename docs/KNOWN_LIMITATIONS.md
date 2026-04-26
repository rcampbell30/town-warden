# Known Limitations

## Police.uk location data

Police.uk location data is approximate/anonymised. Town Warden must not present it as exact incident location data.

## Blackpool zone mapping

The current mapping is rough coordinate logic. It is good enough for demonstration but should be replaced with proper boundary or ward mapping before production.

## SQLite

SQLite is suitable for local development and demos. Production should use PostgreSQL or another managed database.

## Developer controls

The `/dev/*` endpoints are for local workflow and are protected in production using `ADMIN_TOKEN` (or blocked outside local mode if no token is configured).

## Street Manager

Street Manager webhook endpoints are implemented, but live integration is pending external API approval/activation and real payload tuning.

## Pattern Intelligence

Pattern Intelligence insights are currently rule-based heuristics, not machine-learning predictions.

Insights are developer-facing, source-limited early indicators and should not be treated as official public authority conclusions.

## Open-Meteo reliability

Open-Meteo data can be throttled or rate-limited, and source health should be checked before interpretation.

## Production readiness gaps

The production path still requires PostgreSQL, authentication/roles, improved GIS mapping, deeper automated tests, and always-on hosting hardening.

## Decision support only

Town Warden is not an automated decision-maker. It is a signal-monitoring and decision-support prototype.
