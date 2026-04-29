from connectors import police_uk


def test_police_uk_connector_builds_incident_events_without_external_call(monkeypatch):
    sample = [
        {
            "id": 12345,
            "category": "anti-social-behaviour",
            "month": "2026-04",
            "location": {
                "latitude": "53.8310",
                "longitude": "-3.0530",
                "street": {
                    "id": 9001,
                    "name": "On or near Queen's Promenade",
                },
            },
        }
    ]
    health_calls = []

    monkeypatch.setattr(police_uk, "fetch_json", lambda url: sample)

    events = police_uk.fetch_events(lambda *args, **kwargs: health_calls.append((args, kwargs)))

    assert len(events) == 1
    event = events[0]
    assert event["type"] == "incident"
    assert event["source"] == "Police.uk"
    assert event["real_data"] is True
    assert event["location"] == "North Shore"
    assert event["source_event_id"] == "policeuk:12345"
    assert event["metadata"]["coordinate_confidence"] == "approximate"
    assert health_calls[0][0][0] == "Police.uk"
    assert health_calls[0][0][1] == "connected"


def test_police_uk_connector_handles_invalid_response_without_external_call(monkeypatch):
    health_calls = []
    monkeypatch.setattr(police_uk, "fetch_json", lambda url: {"unexpected": "shape"})

    events = police_uk.fetch_events(lambda *args, **kwargs: health_calls.append((args, kwargs)))

    assert events == []
    assert health_calls[0][0][1] == "disconnected"
