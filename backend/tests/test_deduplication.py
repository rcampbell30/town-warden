import main


def test_duplicate_street_manager_webhook_saves_once(client, permit_payload):
    first = client.post("/webhooks/street-manager/permits", json=permit_payload)
    second = client.post("/webhooks/street-manager/permits", json=permit_payload)

    assert first.status_code == 200
    assert first.json()["saved"] is True
    assert second.status_code == 200
    assert second.json()["saved"] is False

    health = client.get("/source-health").json()["sources"]["Street Manager"]
    assert health["status"] == "connected"
    assert health["records_returned"] == 2
    assert health["events_emitted"] == 1
    assert health["new_events_queued"] == 1
    assert health["duplicates_skipped"] == 1
    assert main.duplicate_count == 1

    history = client.get("/history").json()
    assert len(history) == 1
    assert history[0]["source_event_id"] == first.json()["source_event_id"]
