def test_map_data_returns_map_ready_street_manager_event(client, permit_payload):
    client.post("/webhooks/street-manager/permits", json=permit_payload)

    payload = client.get("/map-data").json()

    assert "zones" in payload
    assert "events" in payload
    assert "signals" in payload
    assert payload["events"] == payload["signals"]

    event = payload["events"][0]
    assert event["source"] == "Street Manager"
    assert event["type"] == "infrastructure"
    assert event["title"] == "Street works permit"
    assert event["location"] == "Promenade"
    assert event["coordinate_confidence"] == "exact"
    assert event["lat"] == 53.8191
    assert event["lng"] == -3.0552
    assert event["metadata"]["permit_reference"] == "BC001-PM-000123"
    assert payload["map_diagnostics"]["exact_coordinate_events"] == 1


def test_map_data_marks_missing_coordinates_as_zone_fallback(client, section58_payload):
    client.post("/webhooks/street-manager/section-58", json=section58_payload)

    event = client.get("/map-data").json()["events"][0]

    assert event["source"] == "Street Manager"
    assert event["coordinate_confidence"] == "zone_fallback"
    assert event["is_approximate"] is True
    assert "zone centre" in event["approximate_note"].lower()
