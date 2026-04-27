import main


def test_permit_payload_normalisation_maps_useful_fields(permit_payload):
    event = main.normalize_street_manager_payload(permit_payload, "permit")

    assert event["source"] == "Street Manager"
    assert event["type"] == "infrastructure"
    assert event["real_data"] is True
    assert event["source_event_id"] == "streetmanager:permit:BC001-PM-000123"
    assert "unknown reference" not in event["text"].lower()
    assert "Promenade" in event["text"]
    assert "resurfacing works" in event["text"]
    assert event["metadata"]["permit_reference"] == "BC001-PM-000123"
    assert event["metadata"]["works_reference"] == "BC001-WR-000123"
    assert event["metadata"]["coordinates"]["latitude"] == 53.8191


def test_activity_payload_normalisation(activity_payload):
    event = main.normalize_street_manager_payload(activity_payload, "activity")

    assert event["source_event_id"] == "streetmanager:activity:ACT-998877"
    assert event["metadata"]["activity_reference"] == "ACT-998877"
    assert event["metadata"]["topic"] == "activity"
    assert "Street works activity" in event["text"]
    assert "Talbot Road" in event["text"]


def test_section_58_payload_normalisation(section58_payload):
    event = main.normalize_street_manager_payload(section58_payload, "section-58")

    assert event["source_event_id"] == "streetmanager:section-58:S58-445566"
    assert event["metadata"]["topic"] == "section-58"
    assert "Section 58" in event["text"]
    assert event["metadata"]["highway_authority"] == "Blackpool Council"


def test_missing_fields_do_not_crash_mapper():
    event = main.normalize_street_manager_payload({"MessageId": "fallback-only"}, "permit")

    assert event["source"] == "Street Manager"
    assert event["type"] == "infrastructure"
    assert event["location"] == "Blackpool"
    assert event["source_event_id"].startswith("streetmanager:permit:")
    assert "unknown reference" not in event["text"].lower()
