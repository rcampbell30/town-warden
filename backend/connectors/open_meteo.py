"""Open-Meteo connector for weather pressure signals."""

from datetime import datetime

from config import BLACKPOOL_LAT, BLACKPOOL_LNG
from services.fetching import fetch_json


def fetch_events(update_source_health):
    """Fetch current Blackpool weather and emit threshold-based events."""
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={BLACKPOOL_LAT}"
        f"&longitude={BLACKPOOL_LNG}"
        "&current=temperature_2m,precipitation,rain,wind_speed_10m,weather_code"
        "&timezone=Europe%2FLondon"
    )

    data = fetch_json(url)

    if not isinstance(data, dict):
        update_source_health(
            "Open-Meteo",
            "disconnected",
            "Open-Meteo request failed or returned invalid data.",
            records_returned=0,
            events_emitted=0,
            new_events_queued=0,
        )
        return []

    current = data.get("current", {})
    precipitation = current.get("precipitation", 0) or 0
    wind_speed = current.get("wind_speed_10m", 0) or 0
    temperature = current.get("temperature_2m", "unknown")
    weather_hour = datetime.now().strftime("%Y%m%d%H")

    events = []

    if precipitation > 0:
        events.append({
            "type": "weather",
            "location": "Blackpool South",
            "text": f"Weather signal: precipitation {precipitation}mm, temperature {temperature}°C",
            "timestamp": datetime.now().isoformat(),
            "source": "Open-Meteo",
            "source_event_id": f"openmeteo:{weather_hour}:rain:Blackpool-South",
            "real_data": True,
        })

    if wind_speed >= 25:
        events.append({
            "type": "weather",
            "location": "North Shore",
            "text": f"Weather signal: elevated coastal wind speed {wind_speed} km/h",
            "timestamp": datetime.now().isoformat(),
            "source": "Open-Meteo",
            "source_event_id": f"openmeteo:{weather_hour}:wind:North-Shore",
            "real_data": True,
        })

    if events:
        message = f"Weather checked; {len(events)} weather events emitted."
    else:
        message = f"Weather checked; no threshold triggered. Wind {wind_speed} km/h, precipitation {precipitation}mm."

    update_source_health(
        "Open-Meteo",
        "connected",
        message,
        records_returned=1,
        events_emitted=len(events),
        new_events_queued=0,
    )

    return events
