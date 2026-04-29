import copy
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

IMPORT_DB = BACKEND_ROOT / ".test-runtime" / "import_test.db"
IMPORT_DB.parent.mkdir(exist_ok=True)
os.environ.setdefault("TOWN_WARDEN_DB", str(IMPORT_DB))

import main  # noqa: E402
import storage  # noqa: E402


BASE_SOURCE_HEALTH = copy.deepcopy(main.source_health)


@pytest.fixture
def app_state(tmp_path, monkeypatch):
    test_db = tmp_path / "town_warden_test.db"
    monkeypatch.setattr(storage, "DB_NAME", str(test_db))

    main.setup_database()
    main.clear_database()

    main.history.clear()
    main.risk_map.clear()
    main.real_event_queue.clear()
    main.agent_log.clear()
    main.insights.clear()
    main.duplicate_count = 0
    main.last_source_fetch_time = None
    main.source_health.clear()
    main.source_health.update(copy.deepcopy(BASE_SOURCE_HEALTH))

    yield

    main.clear_database()


@pytest.fixture
def client(app_state):
    return TestClient(main.app)


@pytest.fixture
def permit_payload():
    return {
        "permitReferenceNumber": "BC001-PM-000123",
        "worksReference": "BC001-WR-000123",
        "streetName": "Promenade",
        "locationDescription": "Near North Pier",
        "town": "Blackpool",
        "activityType": "resurfacing works",
        "worksCategory": "major",
        "trafficManagementType": "lane closure",
        "startDate": "2026-04-27",
        "endDate": "2026-04-29",
        "responsibleOrganisation": "Example Utilities",
        "highwayAuthority": "Blackpool Council",
        "coordinates": {
            "latitude": 53.8191,
            "longitude": -3.0552,
        },
    }


@pytest.fixture
def activity_payload():
    return {
        "activityReference": "ACT-998877",
        "streetName": "Talbot Road",
        "locationDescription": "Outside the station",
        "town": "Blackpool",
        "activityType": "excavation",
        "trafficManagementType": "temporary lights",
        "startDate": "2026-05-01",
        "endDate": "2026-05-02",
        "responsibleOrganisation": "Example Contractor",
        "highwayAuthorityName": "Blackpool Council",
    }


@pytest.fixture
def section58_payload():
    return {
        "notificationId": "S58-445566",
        "streetName": "Lytham Road",
        "locationDescription": "South Shore corridor",
        "notificationType": "section 58 restriction",
        "startDate": "2026-06-01",
        "highwayAuthorityName": "Blackpool Council",
    }


@pytest.fixture
def london_payload():
    return {
        "permitReferenceNumber": "LDN-0001",
        "streetName": "Oxford Street",
        "town": "London",
        "highwayAuthorityName": "Westminster City Council",
        "postcode": "W1D 1BS",
        "activityType": "utility works",
        "coordinates": {
            "latitude": 51.5154,
            "longitude": -0.1418,
        },
    }


@pytest.fixture
def crawley_payload():
    return {
        "permitReferenceNumber": "CRW-0001",
        "streetName": "The Boulevard",
        "town": "Crawley",
        "county": "West Sussex",
        "highwayAuthorityName": "West Sussex County Council",
        "coordinates": {
            "latitude": 51.1091,
            "longitude": -0.1872,
        },
    }


@pytest.fixture
def shropshire_payload():
    return {
        "permitReferenceNumber": "SHR-0001",
        "streetName": "High Street",
        "town": "Shrewsbury",
        "county": "Shropshire",
        "highwayAuthorityName": "Shropshire Council",
        "activityType": "carriageway repair",
        "coordinates": {
            "latitude": 52.7073,
            "longitude": -2.7553,
        },
    }


@pytest.fixture
def surrey_payload():
    return {
        "permitReferenceNumber": "SRY-0001",
        "streetName": "High Street",
        "town": "Guildford",
        "county": "Surrey",
        "highwayAuthorityName": "Surrey County Council",
        "coordinates": {
            "latitude": 51.2362,
            "longitude": -0.5704,
        },
    }


@pytest.fixture
def hampshire_payload():
    return {
        "permitReferenceNumber": "HAM-0001",
        "streetName": "Commercial Road",
        "town": "Southampton",
        "county": "Hampshire",
        "highwayAuthorityName": "Hampshire County Council",
        "coordinates": {
            "latitude": 50.9097,
            "longitude": -1.4044,
        },
    }


@pytest.fixture
def blackpool_coordinate_payload():
    return {
        "permitReferenceNumber": "COORD-0001",
        "streetName": "Unnamed works site",
        "activityType": "inspection",
        "coordinates": {
            "latitude": 53.8178,
            "longitude": -3.0509,
        },
    }


@pytest.fixture
def no_location_payload():
    return {
        "permitReferenceNumber": "NOLOC-0001",
        "activityType": "works notification",
    }
