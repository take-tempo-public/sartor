```toml
schema = 1
id = 131
kind = "item"
title = "A retired application cannot be found again: the Retire dialog points at a \"Show retired\" toggle Pipeline doesn't have"
status = "open"
decision_owner = "agent"
branches = ["feat/user-docs"]
refs = [
  "static/app.js:6300-6330",
  "templates/index.html:950-975",
  "blueprints/users.py:308-318",
]
summary = "Retire dialog cites a \"Show retired\" toggle Pipeline lacks; its query drops retired apps."
```

**Observed in code (2026-09-29):**
- **The dialog.** The Retire confirmation in the application detail modal reads "It is hidden
  unless you tick "Show retired". Its iteration history is kept." (`static/app.js:6318`)
- **No checkbox.** The Pipeline panel markup has only a **Refresh** button and a count
  (`templates/index.html:957-973`).
- **Retired rows excluded.** The roster query behind Pipeline returns only
  `Application.is_active == 1` (`blueprints/users.py:314`).
- **Restore is reachable once.** After retiring, the modal re-renders with **Restore**
  (`static/app.js:6306-6312`), but only until the modal is closed. After that, no surface
  lists the application.

The corpus "Show retired" toggle (`static/app.js:5375-5384`) is for experiences, not
applications. The dialog copy was probably carried over from it (inference).

**Docs on `feat/user-docs`** state today's behavior: "retiring hides the application, and you
can only undo it before closing that window". The docs link here.

## Updates

### 2026-09-29 — filed on `feat/user-docs` (Epic D D3), found while writing the Pipeline docs
