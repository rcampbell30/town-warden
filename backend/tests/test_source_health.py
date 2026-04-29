def test_source_health_includes_expected_sources(client):
    payload = client.get("/source-health").json()
    sources = payload["sources"]

    assert {"Police.uk", "Open-Meteo", "Street Manager", "Simulation"}.issubset(sources)
    assert sources["Simulation"]["status"] == "disabled"
    assert "filtered_out_of_area" in sources["Street Manager"]
    assert "system_health_score" in payload
    assert "civic_risk_score" in payload


def test_active_sources_count_when_real_sources_connected(client):
    for path, payload in [
        ("/webhooks/street-manager/permits", {
            "permitReferenceNumber": "BC001-SH-1",
            "streetName": "Promenade",
            "town": "Blackpool",
        }),
    ]:
        client.post(path, json=payload)

    import main

    main.source_health["Police.uk"]["status"] = "connected"
    main.source_health["Police.uk"]["records_returned"] = 1
    main.source_health["Open-Meteo"]["status"] = "connected"
    main.source_health["Open-Meteo"]["records_returned"] = 1

    payload = client.get("/source-health").json()
    assert payload["active_sources_count"] == 3
    assert payload["total_sources_count"] == 3


def test_runtime_status_exposes_production_readiness_fields(client):
    payload = client.get("/runtime-status").json()

    assert payload["database_backend"] == "sqlite"
    assert "dev_routes_protected" in payload
    assert "system_health_score" in payload
    assert "civic_risk_score" in payload
    assert payload["retention"]["events_days"] > 0


def test_home_status_matches_runtime_status_for_public_fields(client):
    import main

    main.source_health["Police.uk"]["status"] = "connected"
    main.source_health["Police.uk"]["records_returned"] = 1
    main.source_health["Open-Meteo"]["status"] = "connected"
    main.source_health["Open-Meteo"]["records_returned"] = 1
    main.source_health["Street Manager"]["status"] = "connected"
    main.source_health["Street Manager"]["records_returned"] = 1

    home_payload = client.get("/").json()
    runtime_payload = client.get("/runtime-status").json()

    assert home_payload["message"] == "Town Warden backend is running"
    assert home_payload["environment"] == runtime_payload["environment"]
    assert home_payload["dev_routes_protected"] == runtime_payload["dev_routes_protected"]
    assert home_payload["active_sources_count"] == runtime_payload["active_sources_count"]
    assert home_payload["active_sources"] == runtime_payload["source_status_summary"]["active"]
    assert set(home_payload["sources"]) == set(main.REAL_SOURCE_NAMES)
    assert "source_health" not in home_payload
    assert "ADMIN_TOKEN" not in str(home_payload)
    assert "DATABASE_URL" not in str(home_payload)


def test_street_manager_connected_after_webhook(client, permit_payload):
    response = client.post("/webhooks/street-manager/permits", json=permit_payload)
    assert response.status_code == 200

    street_manager = client.get("/source-health").json()["sources"]["Street Manager"]
    assert street_manager["status"] == "connected"
    assert street_manager["records_returned"] == 1
    assert "payload received" in street_manager["message"].lower()
