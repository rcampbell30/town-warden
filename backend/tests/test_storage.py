from datetime import datetime, timedelta

import storage


def test_sqlite_is_default_database_backend(monkeypatch):
    monkeypatch.setattr(storage, "DATABASE_URL", "")
    assert storage.database_backend() == "sqlite"


def test_postgres_backend_selected_from_database_url(monkeypatch):
    monkeypatch.setattr(storage, "DATABASE_URL", "postgresql://user:pass@example.com/db")
    assert storage.database_backend() == "postgres"


def test_cleanup_old_records_removes_only_expired_rows(app_state):
    old_timestamp = (datetime.now() - timedelta(days=120)).isoformat()
    recent_timestamp = datetime.now().isoformat()

    storage.save_event({
        "timestamp": old_timestamp,
        "type": "incident",
        "location": "Town Centre",
        "text": "old event",
        "source": "Police.uk",
        "source_event_id": "old-event",
        "real_data": True,
    })
    storage.save_event({
        "timestamp": recent_timestamp,
        "type": "incident",
        "location": "Town Centre",
        "text": "recent event",
        "source": "Police.uk",
        "source_event_id": "recent-event",
        "real_data": True,
    })

    deleted = storage.cleanup_old_records(
        event_retention_days=90,
        alert_retention_days=90,
        risk_snapshot_retention_days=30,
    )

    assert deleted["events"] == 1
    assert storage.event_exists("old-event") is False
    assert storage.event_exists("recent-event") is True
