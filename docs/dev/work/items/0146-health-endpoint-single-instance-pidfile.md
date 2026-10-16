```toml
schema = 1
id = 146
kind = "item"
title = "Health endpoint, single-instance launch, and a pid/lock file in SARTOR_HOME"
status = "closed"
decision_owner = "agent"
branches = ["chore/release-v1.1.0", "feat/single-instance-and-quit"]
refs = [
  "app.py",
  "instance.py",
  "blueprints/lifecycle.py",
  "docs/dev/blast-radius/single-instance-and-quit.md",
  "docs/dev/work/items/0145-*.md",
]
summary = "A second launch starts a second server attempt on :5000; nothing identifies a running sartor or stops it cleanly."
resolution = "2026-10-15, feat/single-instance-and-quit. Observed first: on Windows a second launch, and a launch next to a foreign server, bind the port silently (Werkzeug's own address-in-use error never fires), so the guard is a pre-bind probe. GET /healthz (localhost-only; app, version, pid, instance_id, idle_timeout_s); launch asks the port who owns it: a running Sartor is reused (browser opens on it, exit 0), another program exits 1 naming the port and --port, no silent fallback; atomic sartor-instance.json in SARTOR_HOME, released only by its owner. Measured: a refused loopback connect costs 2.04 s here, so the probe binds exclusively first (0.3 ms) and connects only to classify an owner (25 ms). Real app, reloader and FLASK_DEBUG=0: second launch exit 0, foreign owner exit 1, no file written. Charter C-2 amended (loopback to itself is not egress), pinned by an AST test. Declared limits: two launches racing inside the probe window still both bind (the file is written after the probe); the probe checks 127.0.0.1 only, never --host; the launch itself costs 1.9-2.5 s of which the import share was not separated; macOS/Linux timing not measured. The container HEALTHCHECK and the launcher's use of the file stay with item 145."
verified_by = [
  "tests/test_instance.py::TestProbe",
  "tests/test_cli_setup.py::test_a_running_sartor_is_reused_not_duplicated",
  "tests/test_cli_setup.py::test_a_foreign_owner_exits_one_naming_the_port",
  "tests/test_cli_setup.py::test_the_reload_child_neither_probes_nor_claims_the_file",
  "tests/test_lifecycle_routes.py::test_healthz_identifies_this_server",
  "tests/test_egress_allowlist.py::test_instance_module_names_only_loopback",
]
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

### 2026-10-15 — taken by `feat/single-instance-and-quit` (owner pick, with item 147)

**Observed (Windows 11, Python 3.13, Flask 3.1.3, Werkzeug 3.1.8; real `app.py`; one run each):**
- **A second `python app.py` on a port a first copy already serves does not fail.** In both debug
  (reloader) and `FLASK_DEBUG=0` it stays running and logs `* Running on http://127.0.0.1:P`.
- **A plain `http.server` owning the port does not stop sartor from "binding" it either.**
- Werkzeug's `EADDRINUSE` message and its macOS AirPlay hint **never fired** on this OS.
  So this item is a defect on Windows, and a pre-bind probe is the only guard there.
- Under the reloader, a serving child that exits 0 ends the supervisor with exit 0 and leaves no
  `python.exe` behind.

**Not observed:** which process answered `GET /` in those runs; a race of two simultaneous
launches (declared as an open limit, see `docs/dev/blast-radius/single-instance-and-quit.md`
§Deferred). Full table and the consumer enumeration are in that dossier.

### 2026-10-15 — closed on `feat/single-instance-and-quit`

Built with item 147. One design departure from the item's text, measured: the item suggested
probing the port by connecting. A refused loopback connect costs **2.04 s** here (Windows
retries), and a free port is the common case, so the probe binds exclusively first (0.3 ms) and
connects only to classify an owner (25 ms). The "fall back to the next free port" option was not
taken: browser state is per-origin, port included.

The open limit, stated so it is not counted as protection: **two launches racing inside the
probe window can both bind.** Windows permits it (observed), and the instance file is written
after the probe, so it cannot arbitrate. Closing it needs an exclusive listening socket, which
means replacing `app.run`. Not done here.
