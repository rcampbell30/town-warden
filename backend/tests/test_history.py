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
