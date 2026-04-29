# Backend Testing

Install backend requirements and run the test suite from the backend folder:

```bash
cd backend
pip install -r requirements.txt
pytest
```

The tests use pytest and FastAPI's TestClient. They point SQLite at a temporary
test database for each test, so they do not modify the local demo database or
any production data.

The suite uses mocked Street Manager payloads and does not call Police.uk,
Open-Meteo, Street Manager, or any other external API.

By default tests run with SQLite only. PostgreSQL support is enabled in the app
when `DATABASE_URL` is set, but the normal test suite avoids requiring a live
PostgreSQL service.

The tests cover:

- Street Manager normalisation and Blackpool geographic filtering
- deduplication
- Police.uk and Open-Meteo connector behaviour with mocked responses
- `/source-health`, `/runtime-status`, `/history`, `/analytics`, `/map-data`
- protected `/dev/*` routes
- retention cleanup helpers
