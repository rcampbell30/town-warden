# Known Limitations

## Police.uk location data

Police.uk location data is approximate/anonymised. Town Warden must not present it as exact incident location data.

## Configured town zone mapping

The current mapping is rough coordinate and zone fallback logic. It is good enough for demonstration but should be replaced with proper boundary or ward mapping before production use.

## SQLite

SQLite is suitable for local development and demos. Production should use PostgreSQL or another managed database.

## Developer controls

The `/dev/*` endpoints are for local workflow and diagnostics only.
In production (`ENVIRONMENT=production`), these routes require `x-admin-token` matching `ADMIN_TOKEN`.

## Street Manager

Street Manager webhook endpoints are implemented and filtered to the configured pilot area where location data is available. Filtering still depends on payload quality, authority names, postcodes, coordinates, and the configured bounding box.

## Pattern Intelligence

Pattern Intelligence insights are currently rule-based heuristics, not machine-learning predictions.

Insights in both dashboards are source-limited, experimental rule-based analysis and should not be treated as official public authority conclusions.

## Dashboard split (v4)

v4 introduces a Public Dashboard and a Developer Dashboard.
The Public Dashboard intentionally simplifies wording and hides raw controls/logs.
The Developer Dashboard keeps full diagnostics, history filters, raw metadata, and local-only controls.

## Open-Meteo reliability

Open-Meteo data can be throttled or rate-limited, and source health should be checked before interpretation.

## Production readiness gaps

The production path still requires authentication/roles, improved GIS mapping, monitoring/alerting, and always-on hosting hardening.

## Decision support only

Town Warden is not an automated decision-maker. It is a signal-monitoring and decision-support prototype.
