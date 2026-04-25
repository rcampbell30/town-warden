# Frontend

The frontend is a single static HTML dashboard served locally with Python's built-in HTTP server.

## Run

```powershell
cd frontend
py -m http.server 3000
```

Open:

```text
http://localhost:3000
```

## Backend dependency

The frontend expects the backend to be running at:

```text
http://127.0.0.1:8000
```

and the WebSocket stream at:

```text
ws://127.0.0.1:8000/ws
```
