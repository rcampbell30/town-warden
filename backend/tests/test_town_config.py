import copy
import json

import pytest

import main
from town_config import TownConfigError, load_town_config, public_town_config, reload_town_config


def test_blackpool_config_loads():
    config = load_town_config("config/towns/blackpool.json")

    assert config["town_id"] == "blackpool"
    assert config["display_name"] == "Blackpool"
    assert config["map_centre"]["lat"] == 53.8175
    assert config["zones"]


def test_missing_town_config_env_falls_back_to_blackpool(monkeypatch):
    monkeypatch.delenv("TOWN_CONFIG", raising=False)

    config = reload_town_config()

    assert config["town_id"] == "blackpool"


def test_invalid_town_config_fails_with_useful_error(tmp_path):
    path = tmp_path / "invalid-town.json"
    path.write_text(json.dumps({"town_id": "broken"}), encoding="utf-8")

    with pytest.raises(TownConfigError) as exc:
        load_town_config(str(path))

    assert "missing required" in str(exc.value).lower()


def test_town_config_endpoint_returns_safe_public_fields(client, monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "super-secret")
    monkeypatch.setenv("DATABASE_URL", "postgresql://secret-user:secret-pass@example.internal/db")

    payload = client.get("/town-config").json()
    encoded = json.dumps(payload)

    assert payload["town_id"] == "blackpool"
    assert payload["display_name"] == "Blackpool"
    assert "map_centre" in payload
    assert "zones" in payload
    assert "ADMIN_TOKEN" not in encoded
    assert "DATABASE_URL" not in encoded
    assert "super-secret" not in encoded
    assert "secret-pass" not in encoded


def test_public_town_config_filters_internal_project_links():
    config = copy.deepcopy(load_town_config("config/towns/blackpool.json"))
    config["project_links"] = {
        "github": "https://github.com/rcampbell30/town-warden",
        "internal": "https://town-warden-db.internal/render",
    }

    payload = public_town_config(config)

    assert "github" in payload["project_links"]
    assert "internal" not in payload["project_links"]


def test_street_manager_filter_uses_configured_keywords_and_bounds(monkeypatch):
    original_config = main.TOWN_CONFIG_DATA
    original_display_name = main.TOWN_DISPLAY_NAME
    custom_config = copy.deepcopy(load_town_config("config/towns/example-town.json"))

    monkeypatch.setattr(main, "TOWN_CONFIG_DATA", custom_config)
    monkeypatch.setattr(main, "TOWN_DISPLAY_NAME", custom_config["display_name"])

    example_payload = {
        "permitReferenceNumber": "EX-001",
        "streetName": "Market Street",
        "town": "Example Town",
        "highwayAuthorityName": "Example Council",
        "coordinates": {"latitude": 53.004, "longitude": -2.004},
    }
    blackpool_payload = {
        "permitReferenceNumber": "BPL-001",
        "streetName": "Promenade",
        "town": "Blackpool",
        "highwayAuthorityName": "Blackpool Council",
        "coordinates": {"latitude": 53.8191, "longitude": -3.0552},
    }

    accepted_event = main.normalize_street_manager_payload(example_payload, "permit")
    rejected_event = main.normalize_street_manager_payload(blackpool_payload, "permit")

    assert main.is_relevant_to_town_street_manager(example_payload, accepted_event)[0] is True
    assert main.is_relevant_to_town_street_manager(blackpool_payload, rejected_event)[0] is False

    monkeypatch.setattr(main, "TOWN_CONFIG_DATA", original_config)
    monkeypatch.setattr(main, "TOWN_DISPLAY_NAME", original_display_name)


def test_enabled_sources_are_read_from_config(monkeypatch):
    custom_config = copy.deepcopy(load_town_config("config/towns/example-town.json"))

    monkeypatch.setattr(main, "TOWN_CONFIG_DATA", custom_config)

    assert main.source_enabled("police_uk") is True
    assert main.source_enabled("open_meteo") is True
    assert main.source_enabled("street_manager") is False


def test_map_data_exposes_configured_town_map_fields(client):
    payload = client.get("/map-data").json()

    assert payload["town_id"] == "blackpool"
    assert payload["display_name"] == "Blackpool"
    assert payload["map_centre"]["zoom"] == 12
    assert {zone["name"] for zone in payload["zones"]} >= {"Town Centre", "North Shore", "South Shore"}
