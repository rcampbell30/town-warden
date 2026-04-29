def test_history_returns_street_manager_event(client, permit_payload):
    client.post("/webhooks/street-manager/permits", json=permit_payload)

    history = client.get("/history").json()

    assert len(history) == 1
    event = history[0]
    assert event["source"] == "Street Manager"
    assert event["type"] == "infrastructure"
    assert event["real_data"] is True
    assert "Street works permit" in event["text"]
    assert "Promenade" in event["text"]
    assert event["metadata"]["permit_reference"] == "BC001-PM-000123"


def test_history_includes_police_event_and_excludes_filtered_street_manager(client, london_payload):
    import main

    main.save_event({
        "type": "incident",
        "location": "North Shore",
        "text": "Police.uk signal: test incident near promenade",
        "timestamp": "2026-04-29T10:00:00",
        "source": "Police.uk",
        "source_event_id": "policeuk:test-history",
        "real_data": True,
        "metadata": {"coordinate_confidence": "approximate"},
    })
    client.post("/webhooks/street-manager/permits", json=london_payload)

    history = client.get("/history").json()

    assert len(history) == 1
    assert history[0]["source"] == "Police.uk"
    assert history[0]["type"] == "incident"
