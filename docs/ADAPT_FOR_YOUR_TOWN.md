# Adapt Town Warden For Your Town

Town Warden is an experimental civic-intelligence dashboard that combines public
data sources into a local civic picture. The default project configuration is
Blackpool, but the app is now designed so developers can clone it and adapt it
to another UK town by editing JSON configuration.

Town Warden is not official council, police, NHS, or emergency-service advice.
Keep that disclaimer visible in any adapted deployment.

## Public Data Sources

- Police.uk: public incident and crime signals near a configured map centre
- Open-Meteo: weather context near the configured map centre
- Street Manager: street works webhooks filtered to the configured local area

Each source has coverage limitations. Police.uk coordinates are approximate,
weather is contextual, and Street Manager records may be incomplete or national
unless filtered carefully.

## What A Town Config Controls

Town config files live in `config/towns/`.

A config controls:

- Town name and dashboard wording
- Public disclaimer and footer text
- Map centre and default zoom
- Approximate bounding box for geographic filtering
- Local zones and fallback coordinates
- Enabled sources
- Source labels
- Local authority and highway authority keywords
- Street Manager relevance keywords
- Optional boundary file path for future polygon filtering
- Public project links

The backend exposes safe public settings through `GET /town-config`. It does
not expose `ADMIN_TOKEN`, `DATABASE_URL`, private webhook secrets, or full
environment variables.

## Create A New Town Config

Copy the Blackpool config:

```powershell
Copy-Item config\towns\blackpool.json config\towns\your-town.json
```

Then edit:

- `town_id`: a lowercase identifier such as `preston`
- `town_name`: formal town name
- `display_name`: public display name
- `dashboard_title`
- `dashboard_subtitle`
- `public_disclaimer`
- `footer_text`

You can also use the lightweight helper:

```powershell
py scripts\create_town_config.py
```

The helper creates a starter file only. You still need to review the zones,
bounding box, postcodes, and authority keywords.

## Set The Map Centre

Edit:

```json
"map_centre": {
  "lat": 53.0,
  "lng": -2.0,
  "zoom": 12
}
```

Police.uk and Open-Meteo use this centre for local data requests. The frontend
map also starts here.

## Define Local Zones

Zones are deliberately simple. Each zone needs a label and fallback coordinate:

```json
{
  "name": "Town Centre",
  "label": "Town Centre",
  "fallback_lat": 53.0,
  "fallback_lng": -2.0,
  "radius_m": 900,
  "risk_weight": 1.2,
  "keywords": ["centre", "high street"]
}
```

Fallback coordinates are used only when a source event has no precise
coordinates. The map marks those positions as fallback, not exact.

## Set The Bounding Box

Street Manager records are accepted when they have strong evidence that they
belong to the configured town. Coordinates are checked against:

```json
"approximate_bounding_box": {
  "min_lat": 53.73,
  "max_lat": 53.90,
  "min_lng": -3.10,
  "max_lng": -2.95
}
```

Use a cautious box around your pilot area. If in doubt, make it smaller and
expand later.

## Add Local Keywords

Set keywords that Street Manager records may contain:

```json
"local_authority_keywords": ["Example Council"],
"highway_authority_keywords": ["Example Council"],
"street_manager_relevance_keywords": ["Example Town", "EX1"],
"postcode_prefixes": ["EX"]
```

Out-of-area records are accepted by the webhook endpoint but are not stored as
Town Warden civic events. They do not enter history, analytics, map data, risk
scores, or insights.

## Enable Or Disable Sources

```json
"enabled_sources": {
  "police_uk": true,
  "open_meteo": true,
  "street_manager": true
}
```

Leave a source disabled only if your adapted dashboard should not count it as a
live real source.

## Run Locally

Backend:

```powershell
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

Frontend:

```powershell
cd frontend
py -m http.server 3000
```

Open `http://localhost:3000`.

## Set TOWN_CONFIG

For local testing:

```powershell
$env:TOWN_CONFIG="config/towns/your-town.json"
cd backend
uvicorn main:app --reload
```

For Render, add:

```text
TOWN_CONFIG=config/towns/your-town.json
```

## Production Environment Variables

Set these on Render:

```text
ENVIRONMENT=production
TOWN_CONFIG=config/towns/your-town.json
ADMIN_TOKEN=<strong random value>
DATABASE_URL=<Render PostgreSQL URL>
SOURCE_REFRESH_SECONDS=60
```

Never put `ADMIN_TOKEN`, `DATABASE_URL`, or private credentials in frontend
files.

## Deploy

Backend: deploy the FastAPI app to Render using `backend/requirements.txt` and
the start command documented in `docs/DEPLOYMENT.md`.

Frontend: deploy the `frontend/` folder to Netlify as static files.

## Data Limitations

Town Warden combines public-source signals into a civic picture. It does not
verify incidents, dispatch services, or replace official local authority or
emergency-service channels. Use official channels for urgent or safety-critical
decisions.
