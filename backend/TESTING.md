# Backend Testing

Run the backend test suite from the backend folder:

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
