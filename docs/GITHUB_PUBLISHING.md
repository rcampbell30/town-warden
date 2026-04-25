# GitHub Publishing Checklist

Before publishing:

- [ ] Confirm `.gitignore` exists.
- [ ] Confirm `venv/` is not included.
- [ ] Confirm `__pycache__/` is not included.
- [ ] Confirm `town_warden.db` is not included.
- [ ] Confirm `.env` is not included.
- [ ] Confirm no API keys/secrets are in code.
- [ ] Confirm README quickstart works from a fresh folder.
- [ ] Confirm MIT licence is present.

Suggested commands:

```powershell
git init
git add .
git status
git commit -m "Initial Town Warden demo-ready prototype"
```

Then create a GitHub repository and follow GitHub's push instructions.
