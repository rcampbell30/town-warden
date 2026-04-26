# Known Limitations

## Police.uk location data

Police.uk location data is approximate/anonymised. Town Warden must not present it as exact incident location data.

## Blackpool zone mapping

The current mapping is rough coordinate logic. It is good enough for demonstration but should be replaced with proper boundary or ward mapping before production.

## SQLite

SQLite is suitable for local development and demos. Production should use PostgreSQL or another managed database.

## Developer controls

The `/dev/*` endpoints are useful locally but unsafe publicly unless authentication is added.

## Street Manager

The Street Manager connector is currently a stub pending API access.

## Pattern Intelligence

Pattern Intelligence insights are currently rule-based heuristics, not machine-learning predictions.

Insights are developer-facing early indicators and should not be treated as official public authority conclusions.

## Decision support only

Town Warden is not an automated decision-maker. It is a signal-monitoring and decision-support prototype.
