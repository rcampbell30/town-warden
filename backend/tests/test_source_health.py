def test_source_health_includes_expected_sources(client):
    payload = client.get("/source-health").json()
    sources = payload["sources"]

    assert {"Police.uk", "Open-Meteo", "Street Manager", "Simulation"}.issubset(sources)
    assert sources["Simulation"]["status"] == "disabled"
    assert "filtered_out_of_area" in sources["Street Manager"]


def test_street_manager_connected_after_webhook(client, permit_payload):
    response = client.post("/webhooks/street-manager/permits", json=permit_payload)
    assert response.status_code == 200

    street_manager = client.get("/source-health").json()["sources"]["Street Manager"]
    assert street_manager["status"] == "connected"
    assert street_manager["records_returned"] == 1
    assert "payload received" in street_manager["message"].lower()
