import main


def test_blackpool_area_payload_is_relevant(permit_payload):
    event = main.normalize_street_manager_payload(permit_payload, "permit")

    relevant, reason = main.is_relevant_to_blackpool_street_manager(permit_payload, event)

    assert relevant is True
    assert reason in {"area_text", "coordinate_bounds", "postcode"}


def test_blackpool_coordinates_payload_is_relevant(blackpool_coordinate_payload):
    event = main.normalize_street_manager_payload(blackpool_coordinate_payload, "permit")

    relevant, reason = main.is_relevant_to_blackpool_street_manager(blackpool_coordinate_payload, event)

    assert relevant is True
    assert reason == "coordinate_bounds"


def test_london_payload_is_filtered(client, london_payload):
    response = client.post("/webhooks/street-manager/permits", json=london_payload)

    assert response.status_code == 200
    assert response.json()["status"] == "filtered_out"
    assert response.json()["saved"] is False
    assert client.get("/history").json() == []
    assert client.get("/analytics").json()["total_events"] == 0
    assert client.get("/map-data").json()["events"] == []
    assert main.risk_map == {}
    assert main.insights == []

    health = client.get("/source-health").json()["sources"]["Street Manager"]
    assert health["records_returned"] == 1
    assert health["events_emitted"] == 0
    assert health["duplicates_skipped"] == 0
    assert health["filtered_out_of_area"] == 1


def test_shropshire_payload_is_filtered(client, shropshire_payload):
    response = client.post("/webhooks/street-manager/permits", json=shropshire_payload)

    assert response.status_code == 200
    assert response.json()["status"] == "filtered_out"
    assert client.get("/history").json() == []
    assert client.get("/map-data").json()["events"] == []


def test_no_location_payload_is_filtered(client, no_location_payload):
    response = client.post("/webhooks/street-manager/permits", json=no_location_payload)

    assert response.status_code == 200
    assert response.json()["status"] == "filtered_out"
    assert client.get("/history").json() == []


def test_filtered_payload_does_not_inflate_duplicate_count(client, london_payload):
    client.post("/webhooks/street-manager/permits", json=london_payload)
    client.post("/webhooks/street-manager/permits", json=london_payload)

    health = client.get("/source-health").json()["sources"]["Street Manager"]
    assert health["filtered_out_of_area"] == 2
    assert health["duplicates_skipped"] == 0
    assert main.duplicate_count == 0
