```toml
schema = 1
id = 147
kind = "item"
title = "In-app Quit, opt-in idle shutdown, and beforeunload limited to unsaved edits"
status = "open"
decision_owner = "agent"
branches = ["chore/release-v1.1.0"]
refs = ["app.py", "static/app.js", "docs/dev/work/items/0146-*.md"]
summary = "Closing the tab leaves the server running (correct), but there is no in-app way to stop it and no idle exit."
```

**Owner question (2026-10-02):** "When closing the webpage, do we close the python app too? Should
we prompt on window close? Should we detect an already-running version?" The third part is item
146.

**The answer, following industry practice** (Jupyter, Streamlit, Gradio, Ollama):
- **Closing a tab must NOT stop the server.**
  - `beforeunload`/`pagehide` fire on refresh, on navigation and for one tab of several.
  - They don't fire on a browser crash or kill.
  - So tying shutdown to them kills the app on a refresh.
- **Build these instead:**
  1. **An explicit in-app Quit,** modeled on Jupyter's File → Shut Down.
     - It calls `POST /api/shutdown`.
     - Localhost-only, behind the host-header guard, with a CSRF-safe same-origin check.
     - It writes nothing to the filesystem, so the `_safe_username`/`_within` pattern doesn't
       apply. Say so in the route's docstring for `route-security-lint`.
     - It shuts down cleanly and removes item 146's pid file.
  2. **Opt-in idle shutdown,** modeled on Jupyter's `shutdown_no_activity_timeout`.
     - The page sends a heartbeat; the server exits N minutes after the last heartbeat.
     - Off by default, or set by the launcher (item 145).
  3. **`beforeunload` only for unsaved edits,** for example a half-typed Compose bullet. Never as
     "close the app?". Browsers show only a generic "Leave site?" and can't run code after the
     answer.

## Updates

### 2026-10-02 — filed on `chore/release-v1.1.0` (owner-directed)
