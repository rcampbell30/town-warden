"""Police.uk connector for Blackpool civic incident signals."""

from datetime import datetime

from config import BLACKPOOL_LAT, BLACKPOOL_LNG, POLICE_CANDIDATE_LIMIT
from services.fetching import fetch_json


def map_blackpool_zone(lat, lng):
    """
    Rough v1 mapping from Police.uk approximate coordinates to dashboard zones.

    This is deliberately simple for now. The later production version should
    replace this with proper boundary polygons or a geocoding/ward lookup.
    """
    if lat is None or lng is None:
        return "Town Centre"

    try:
        lat = float(lat)
        lng = float(lng)
    except (TypeError, ValueError):
        return "Town Centre"

    if lat >= 53.825:
        return "North Shore"

    if lat <= 53.805:
        return "Blackpool South"

    if lng <= -3.045:
        return "South Shore"

    return "Town Centre"


def fetch_events(update_source_health):
    """Fetch and normalise Police.uk records into Town Warden events."""
    url = f"https://data.police.uk/api/crimes-street/all-crime?lat={BLACKPOOL_LAT}&lng={BLACKPOOL_LNG}"

    data = fetch_json(url)

    if not isinstance(data, list):
        update_source_health(
            "Police.uk",
            "disconnected",
            "Police.uk request failed or returned invalid data.",
            records_returned=0,
            events_emitted=0,
            new_events_queued=0,
        )
        return []

    events = []

    for crime in data[:POLICE_CANDIDATE_LIMIT]:
        category = crime.get("category", "unknown-crime")
        month = crime.get("month", "unknown-month")
        crime_id = crime.get("id")

        location_data = crime.get("location", {})
        street = location_data.get("street", {})

        if crime_id is None:
            street_id = street.get("id", "unknown-street")
            crime_id = f"{month}:{category}:{street_id}:{len(events)}"

        lat = location_data.get("latitude")
        lng = location_data.get("longitude")
        zone = map_blackpool_zone(lat, lng)
        street_name = street.get("name", "approximate Police.uk location")
        coordinates = None
        try:
            coordinates = {"latitude": float(lat), "longitude": float(lng)}
        except (TypeError, ValueError):
            pass

        events.append({
            "type": "incident",
            "location": zone,
            "text": f"Police.uk signal: {category} reported near {street_name} ({month})",
            "timestamp": datetime.now().isoformat(),
            "source": "Police.uk",
            "source_event_id": f"policeuk:{crime_id}",
            "real_data": True,
            "zone_confidence": "rough_coordinate_mapping",
            "approx_street": street_name,
            "metadata": {
                "category": category,
                "month": month,
                "street_name": street_name,
                "street_id": street.get("id"),
                "coordinates": coordinates,
                "coordinate_confidence": "approximate" if coordinates else "zone_fallback",
                "zone_confidence": "rough_coordinate_mapping",
            },
        })

    update_source_health(
        "Police.uk",
        "connected",
        f"Returned {len(data)} records; prepared {len(events)} candidate events.",
        records_returned=len(data),
        events_emitted=len(events),
        new_events_queued=0,
    )

    return events
