from datetime import datetime

from connectors import open_meteo


def reset_open_meteo_cache():
    open_meteo.rate_limited_until = None
    open_meteo.cached_events = []
    open_meteo.cached_message = None
    open_meteo.cached_at = None


def test_open_meteo_connector_builds_weather_events_without_external_call(monkeypatch):
    reset_open_meteo_cache()
    health_calls = []
    response = {
        "current": {
            "temperature_2m": 9.5,
            "precipitation": 1.2,
            "wind_speed_10m": 31,
            "weather_code": 61,
        }
    }

    monkeypatch.setattr(open_meteo, "fetch_json", lambda url: (response, None))
    monkeypatch.setattr(open_meteo, "now", lambda: datetime(2026, 4, 29, 10, 30))

    events = open_meteo.fetch_events(lambda *args, **kwargs: health_calls.append((args, kwargs)))

    assert len(events) == 2
    assert {event["type"] for event in events} == {"weather"}
    assert {event["source"] for event in events} == {"Open-Meteo"}
    assert health_calls[0][0][1] == "connected"
    assert health_calls[0][1]["events_emitted"] == 2


def test_open_meteo_cache_reuse_does_not_call_external_api(monkeypatch):
    reset_open_meteo_cache()
    health_calls = []
    calls = {"count": 0}
    response = {
        "current": {
            "temperature_2m": 11,
            "precipitation": 0,
            "wind_speed_10m": 30,
            "weather_code": 3,
        }
    }

    def fake_fetch(url):
        calls["count"] += 1
        return response, None

    monkeypatch.setattr(open_meteo, "fetch_json", fake_fetch)
    monkeypatch.setattr(open_meteo, "now", lambda: datetime(2026, 4, 29, 10, 30))

    first = open_meteo.fetch_events(lambda *args, **kwargs: health_calls.append((args, kwargs)))
    second = open_meteo.fetch_events(lambda *args, **kwargs: health_calls.append((args, kwargs)))

    assert calls["count"] == 1
    assert first == second
    assert health_calls[-1][0][1] == "connected"
    assert "Cached weather reused" in health_calls[-1][0][2]
