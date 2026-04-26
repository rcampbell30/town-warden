# Frontend

The frontend is static HTML with no build step:

- `index.html` -> public civic dashboard (safe summaries only)
- `dev.html` -> developer diagnostics dashboard (raw logs/metadata and local-only controls)

## Run

```powershell
cd frontend
py -m http.server 3000
```

Open:

```text
http://localhost:3000
```

Public dashboard:

```text
http://localhost:3000/index.html
```

Developer dashboard:

```text
http://localhost:3000/dev.html
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
