from pathlib import Path

import main


def test_dev_routes_reject_missing_or_wrong_token_in_production(client, monkeypatch):
    monkeypatch.setattr(main, "ENVIRONMENT", "production")
    monkeypatch.setattr(main, "ADMIN_TOKEN", "secret-test-token")

    missing = client.post("/dev/reset-database")
    wrong = client.post("/dev/reset-database", headers={"x-admin-token": "wrong"})
    force_missing = client.post("/dev/force-refresh")
    force_wrong = client.post("/dev/force-refresh", headers={"x-admin-token": "wrong"})
    cleanup_missing = client.post("/dev/cleanup-retention")

    assert missing.status_code == 403
    assert wrong.status_code == 403
    assert force_missing.status_code == 403
    assert force_wrong.status_code == 403
    assert cleanup_missing.status_code == 403


def test_dev_routes_accept_valid_token_in_production(client, monkeypatch):
    monkeypatch.setattr(main, "ENVIRONMENT", "production")
    monkeypatch.setattr(main, "ADMIN_TOKEN", "secret-test-token")

    response = client.post("/dev/clear-live-feed", headers={"x-admin-token": "secret-test-token"})

    assert response.status_code == 200
    assert response.json()["message"] == "Live feed memory cleared."


def test_local_dev_routes_are_predictable_without_token(client, monkeypatch):
    monkeypatch.setattr(main, "ENVIRONMENT", "local")

    response = client.post("/dev/clear-live-feed")

    assert response.status_code == 200


def test_frontend_does_not_expose_admin_token():
    frontend_root = Path(__file__).resolve().parents[2] / "frontend"
    public_files = list(frontend_root.glob("*.html"))

    assert public_files
    for path in public_files:
        text = path.read_text(encoding="utf-8")
        assert "ADMIN_TOKEN" not in text
        assert "x-admin-token" not in text
