# Changelog

## v1.1 — Police.uk data clarity patch

- Clarified that Police.uk street-level records are historical, approximate, and updated monthly.
- Updated public dashboard incident cards to separate Police.uk recorded period from Town Warden detection/display time.
- Added historical/public-source/approximate-location/monthly-update badges.
- Improved resident-facing safety wording and emergency/non-emergency guidance.
- Added README guidance for developers cloning Town Warden into other UK towns.
- Preserved existing data wiring and backend behaviour.

## v1.0 — Cloneable civic intelligence template

- Established Town Warden as a cloneable civic-intelligence template for UK towns.
- Added config-driven town setup with Blackpool as the default example.
- Included FastAPI backend, static frontend, PostgreSQL production support, SQLite fallback, protected admin routes, and backend tests.
