import json
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

try:
    from config import BLACKPOOL_LAT, BLACKPOOL_LNG
except ImportError:
    BLACKPOOL_LAT = 53.8175
    BLACKPOOL_LNG = -3.0357


OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


def fetch_json(url):
    """
    Fetch JSON from Open-Meteo.

    Uses a browser-like User-Agent so hosted environments are less likely
    to get odd network behaviour.
    """

    try:
        request = Request(
            url,
            headers={
                "User-Agent": "Town-Warden/1.0 civic-intelligence-demo"
            },
        )

        with urlopen(request, timeout=12) as response:
            raw = response.read()
            text = raw.decode("utf-8")
            return json.loads(text), None

    except HTTPError as error:
        try:
            body = error.read().decode("utf-8")
        except Exception:
            body = ""

        return None, f"HTTP {error.code}: {body[:180]}"

    except URLError as error:
        return None, f"URL error: {error.reason}"

    except TimeoutError:
        return None, "Request timed out."

    except json.JSONDecodeError:
        return None, "Response was not valid JSON."


def build_weather_url():
    """
    Build the Open-Meteo URL safely.

    Keep the current variables simple and stable.
    """

    params = {
        "latitude": BLACKPOOL_LAT,
        "longitude": BLACKPOOL_LNG,
        "current": ",".join([
            "temperature_2m",
            "precipitation",
            "wind_speed_10m",
            "weather_code",
        ]),
        "timezone": "Europe/London",
    }

    return f"{OPEN_METEO_URL}?{urlencode(params)}"


def extract_current_weather(data):
    """
    Supports both the modern Open-Meteo 'current' format and the older
    'current_weather' style if the API response changes shape.
    """

    if not isinstance(data, dict):
        return None

    if isinstance(data.get("current"), dict):
        current = data["current"]

        return {
            "temperature": current.get("temperature_2m"),
            "precipitation": current.get("precipitation", 0) or 0,
            "wind_speed": current.get("wind_speed_10m", 0) or 0,
            "weather_code": current.get("weather_code"),
        }

    if isinstance(data.get("current_weather"), dict):
        current = data["current_weather"]

        return {
            "temperature": current.get("temperature"),
            "precipitation": 0,
            "wind_speed": current.get("windspeed", 0) or 0,
            "weather_code": current.get("weathercode"),
        }

    return None


def fetch_events(update_source_health):
    """
    Fetch Blackpool weather from Open-Meteo and convert threshold hits
    into Town Warden weather events.
    """

    url = build_weather_url()
    data, error = fetch_json(url)

    if error:
        update_source_health(
            "Open-Meteo",
            "disconnected",
            f"Open-Meteo request failed: {error}",
            records_returned=0,
            events_emitted=0,
            new_events_queued=0,
        )
        return []

    current = extract_current_weather(data)

    if current is None:
        update_source_health(
            "Open-Meteo",
            "disconnected",
            f"Open-Meteo returned unexpected JSON shape: {str(data)[:180]}",
            records_returned=0,
            events_emitted=0,
            new_events_queued=0,
        )
        return []

    precipitation = current["precipitation"]
    wind_speed = current["wind_speed"]
    temperature = current["temperature"]
    weather_code = current["weather_code"]

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
        message = (
            f"Weather checked. Wind {wind_speed} km/h, "
            f"precipitation {precipitation}mm, temperature {temperature}°C. "
            f"Events emitted: {len(events)}."
        )
    else:
        message = (
            f"Weather checked. No threshold triggered. "
            f"Wind {wind_speed} km/h, precipitation {precipitation}mm, "
            f"temperature {temperature}°C, weather code {weather_code}."
        )

    update_source_health(
        "Open-Meteo",
        "connected",
        message,
        records_returned=1,
        events_emitted=len(events),
        new_events_queued=0,
    )

    return events