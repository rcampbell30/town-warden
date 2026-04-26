import json
from datetime import datetime, timedelta
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

try:
    from config import BLACKPOOL_LAT, BLACKPOOL_LNG
except ImportError:
    BLACKPOOL_LAT = 53.8175
    BLACKPOOL_LNG = -3.0357


OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# Open-Meteo does not need second-by-second checks.
# Cache successful responses for 60 minutes.
CACHE_SECONDS = 60 * 60

# If Open-Meteo rate-limits us, stop asking for the rest of the day.
rate_limited_until = None
cached_events = []
cached_message = None
cached_at = None


def now():
    return datetime.now()


def fetch_json(url):
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

        return None, {
            "status": error.code,
            "body": body[:250],
            "retry_after": error.headers.get("Retry-After"),
        }

    except URLError as error:
        return None, {
            "status": "url_error",
            "body": str(error.reason),
            "retry_after": None,
        }

    except TimeoutError:
        return None, {
            "status": "timeout",
            "body": "Request timed out.",
            "retry_after": None,
        }

    except json.JSONDecodeError:
        return None, {
            "status": "json_error",
            "body": "Response was not valid JSON.",
            "retry_after": None,
        }


def build_weather_url():
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


def build_events_from_weather(current):
    precipitation = current["precipitation"]
    wind_speed = current["wind_speed"]
    temperature = current["temperature"]

    weather_hour = now().strftime("%Y%m%d%H")
    events = []

    if precipitation > 0:
        events.append({
            "type": "weather",
            "location": "Blackpool South",
            "text": f"Weather signal: precipitation {precipitation}mm, temperature {temperature}°C",
            "timestamp": now().isoformat(),
            "source": "Open-Meteo",
            "source_event_id": f"openmeteo:{weather_hour}:rain:Blackpool-South",
            "real_data": True,
        })

    if wind_speed >= 25:
        events.append({
            "type": "weather",
            "location": "North Shore",
            "text": f"Weather signal: elevated coastal wind speed {wind_speed} km/h",
            "timestamp": now().isoformat(),
            "source": "Open-Meteo",
            "source_event_id": f"openmeteo:{weather_hour}:wind:North-Shore",
            "real_data": True,
        })

    return events


def tomorrow_morning():
    tomorrow = now() + timedelta(days=1)
    return tomorrow.replace(hour=1, minute=0, second=0, microsecond=0)


def fetch_events(update_source_health):
    global rate_limited_until
    global cached_events
    global cached_message
    global cached_at

    current_time = now()

    # If rate-limited, do not keep hammering Open-Meteo.
    if rate_limited_until and current_time < rate_limited_until:
        update_source_health(
            "Open-Meteo",
            "rate_limited",
            f"Open-Meteo rate-limited until {rate_limited_until.isoformat()}. Using cached/no weather events.",
            records_returned=0,
            events_emitted=0,
            new_events_queued=0,
        )
        return cached_events

    # Use cached weather for 60 minutes.
    if cached_at and current_time - cached_at < timedelta(seconds=CACHE_SECONDS):
        update_source_health(
            "Open-Meteo",
            "connected",
            f"{cached_message} Cached weather reused.",
            records_returned=1,
            events_emitted=len(cached_events),
            new_events_queued=0,
        )
        return cached_events

    url = build_weather_url()
    data, error = fetch_json(url)

    if error:
        status = error.get("status")
        body = error.get("body", "")
        retry_after = error.get("retry_after")

        if status == 429:
            if retry_after and str(retry_after).isdigit():
                rate_limited_until = current_time + timedelta(seconds=int(retry_after))
            else:
                rate_limited_until = tomorrow_morning()

            update_source_health(
                "Open-Meteo",
                "rate_limited",
                f"Open-Meteo rate-limited: {body}. Paused until {rate_limited_until.isoformat()}.",
                records_returned=0,
                events_emitted=0,
                new_events_queued=0,
            )

            return cached_events

        update_source_health(
            "Open-Meteo",
            "disconnected",
            f"Open-Meteo request failed: {body}",
            records_returned=0,
            events_emitted=0,
            new_events_queued=0,
        )

        return cached_events

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
        return cached_events

    cached_events = build_events_from_weather(current)
    cached_at = current_time

    cached_message = (
        f"Weather checked. Wind {current['wind_speed']} km/h, "
        f"precipitation {current['precipitation']}mm, "
        f"temperature {current['temperature']}°C, "
        f"weather code {current['weather_code']}."
    )

    update_source_health(
        "Open-Meteo",
        "connected",
        f"{cached_message} Events emitted: {len(cached_events)}.",
        records_returned=1,
        events_emitted=len(cached_events),
        new_events_queued=0,
    )

    return cached_events