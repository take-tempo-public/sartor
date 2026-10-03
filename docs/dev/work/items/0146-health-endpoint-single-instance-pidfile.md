```toml
schema = 1
id = 146
kind = "item"
title = "Health endpoint, single-instance launch, and a pid/lock file in SARTOR_HOME"
status = "open"
decision_owner = "agent"
branches = ["chore/release-v1.1.0"]
refs = ["app.py", "docs/dev/work/items/0145-*.md"]
summary = "A second launch starts a second server attempt on :5000; nothing identifies a running sartor or stops it cleanly."
```

**Current behavior.** This is a code read of `app.py`, not run on 2026-10-02.
- `main()` parses `--port` (default 5000), prints the URL, opens the browser on a timer
  (`webbrowser.open`, `app.py:375`), then calls `app.run(host=…, port=…)` (`app.py:388`).
- A grep found no running-instance check, no health route in `app.py`, and no pid file.

**What should happen, following industry practice** (VS Code single instance; Jupyter's server
list and port handling):
1. **A health endpoint** such as `GET /healthz`, answering with app identity, version and pid.
   - Localhost-only, behind the same host-header guard as `/_dashboard`.
   - It doubles as the container `HEALTHCHECK` (item 145).
2. **On launch, probe the port:**
   - **If sartor answers:** open the browser on the running copy and exit 0.
   - **If another program owns the port:** print a clear error naming the port, or fall back to
     the next free port, stating it.
   - **The macOS case matters:** on macOS 12+, AirPlay Receiver listens on :5000, so a Mac
     user's first launch can collide.
3. **A pid/lock file under `SARTOR_HOME`,** written at start and removed on clean exit. Treat a
   stale lock (its pid is dead) as absent. This is what launcher `status` and `down` read.

**Related:**
- Item 128 (stray processes) is the dev-side cousin; this item is the product side.
- Item 147 is the browser-side half.

## Updates

### 2026-10-02 — filed on `chore/release-v1.1.0` (owner-directed)
