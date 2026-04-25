# Demo-Ready Checklist

## Done

- [x] Real-data-only mode
- [x] Police.uk connector
- [x] Open-Meteo connector
- [x] Street Manager stub
- [x] Source health panel
- [x] Deduplication guard
- [x] Source refresh countdown
- [x] SQLite persistence
- [x] History endpoint
- [x] Analytics endpoint
- [x] Developer controls
- [x] Clean GitHub-style structure
- [x] README
- [x] Demo script
- [x] `.gitignore`
- [x] MIT licence

## Check before showing someone

- [ ] Backend starts with `uvicorn main:app --reload`
- [ ] Frontend starts with `py -m http.server 3000`
- [ ] Dashboard opens at `http://localhost:3000`
- [ ] `/source-health` returns JSON
- [ ] Police.uk shows connected or waiting/disconnected gracefully
- [ ] Open-Meteo shows connected or waiting/disconnected gracefully
- [ ] Dev controls are only used locally
- [ ] No `venv/`, `__pycache__/`, `.env`, or `.db` files are in Git
