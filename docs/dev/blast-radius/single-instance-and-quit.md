# Blast radius — single-instance-and-quit

> **Branch:** `feat/single-instance-and-quit`
> **Status:** enumeration complete for the surfaces below (written before the first production edit).
> Re-derived by grep on 2026-10-15 at `eb3ecc9` plus this branch's ledger commit; no figure here is
> carried from the plan, the handoff or `blast_radius.py`.

Work items 146 (`/healthz`, single-instance probe, instance file) and 147 (in-app Quit, opt-in idle
shutdown, `beforeunload` for unsaved edits). Item 145 (launcher, wrappers, image `HEALTHCHECK`) is a
later branch.

---

## Surface

The one **gated** surface this branch edits:

- `ui_pages/selectors.py` — **additive only**: new keys on the existing `Settings` class (`:403`) for
  the Quit control, and one new class `Lifecycle` for the stopped state. No existing key is renamed,
  moved or removed.

Not gated, but changed (listed so each has a decision):

- `app.py` — `main()` (`:289-388`): a `--idle-timeout` flag, the pre-bind probe, the instance file,
  and the `atexit` release. `register_blueprints` (`:47-76`) mounts one more blueprint.
- `instance.py` — **new**, top-level, stdlib only. The only module that opens a socket (loopback).
- `blueprints/lifecycle.py` — **new**: `GET /healthz`, `POST /api/shutdown`, `POST /api/heartbeat`,
  and a `before_app_request` activity touch. `blueprints/__init__.py` exports it.
- `web_infra/request_gates.py` — one new function, `_is_same_origin_request`; re-exported from
  `web_infra/__init__.py` (an acknowledged-not-gated re-export shim, `blast_radius.py:206`).
- `web_infra/openapi.py:60` — `_app_version` becomes the public `app_version`.
- `blueprints/users.py:95` — one new template variable for `render_template("index.html", …)`.
- `templates/index.html` (Settings drawer, `:1365`) and `static/app.js` — the Quit control, the
  heartbeat, and `_hasUnsavedEdits` + one `beforeunload` listener.
- `pyproject.toml` — `py-modules` (`:156-173`) and the mypy-strict roster (`:437-472`).
- `tests/test_egress_allowlist.py` — `SANCTIONED_EGRESS_FILES` gains `instance.py`.
- `docs/governance/charter.md` C-2 — a dated amendment (owner-directed, 2026-10-15).

---

## Enumeration

Commands run from the repo root; counts are the tool's, not estimated.

### Observed before building (pre-build run, scratchpad script, real `app.py`, this machine)

Windows 11, Python 3.13 (Store), Flask 3.1.3, Werkzeug 3.1.8. One run per scenario; the raw JSON is
`observed.json` in the session scratchpad and the parts that matter are quoted here.

| Scenario | Observed |
|---|---|
| **A1** second `python app.py --no-browser --port P` while a first copy serves P, default (debug, reloader) | `second_exit: null`, `second_still_running: true`. The second log ends `* Running on http://127.0.0.1:P`, `* Restarting with stat`, `* Debugger is active!`. **No bind error, no exit.** First copy still alive; `GET /` answers 200. |
| **A2** the same with `FLASK_DEBUG=0` | `second_exit: null`, `second_still_running: true`; log ends `* Running on http://127.0.0.1:P`. **No bind error, no exit.** |
| **B** a plain `http.server` owns P, then `python app.py --port P` | `exit: null`; sartor's log ends `* Running on http://127.0.0.1:P` plus the reloader lines. **No bind error, no exit.** The foreign server still answers 200. |
| **C** under the reloader, the serving child calls `os._exit(0)` (driver imports the real `app.app`, `debug=True`) | `supervisor_exit: 0`; the port stops answering; `python.exe` count 1 before and after (the one is the unrelated isidium MCP server, pid 28852, started 15:47). **No orphan.** |

What this settles, and what it does not:

- **On Windows a second launch does not fail.** Werkzeug's `EADDRINUSE` branch (read in
  `werkzeug/serving.py`, the `server_bind` `except OSError`) never fired in A1, A2 or B. A second
  sartor, or a sartor next to a foreign server, **binds the same port silently**. This is a defect in
  its own right and not only a missing feature: which process receives a given connection is
  undefined, so a user can be talking to a stale copy.
- **A pre-bind probe is therefore the only guard on this OS**, not a nicety layered on Werkzeug's own
  error. Hence the probe decides `SARTOR` / `FOREIGN` / `FREE` *before* `app.run`.
- **Not observed:** which process answered `GET /` in A1/A2/B (the script recorded the status code,
  not the body or the pid). Not claimed.
- **Not observed:** two launches racing within the probe window (both see `FREE`, both bind). The
  design does not close this; it is declared under Deferred.
- The reloader supervisor exiting 0 when its child exits 0 is observed (C), which is the premise
  `request_shutdown` relies on.

### Measured: three ways to ask "is this port taken?" (same machine; scratchpad `measure_probe.py`)

| Method | Result |
|---|---|
| `http.client` GET `/healthz` on a **free** port | `ConnectionRefusedError` after **2.043 s** median (5 runs: 2.037–2.058 s). Windows retries a refused loopback connect. |
| exclusive bind (`SO_EXCLUSIVEADDRUSE`) on a **free** port | succeeds in **0.3 ms** |
| exclusive bind on a listener built the way `http.server`/Werkzeug builds one (`allow_reuse_address=1`) | refused, `WinError 10048`, **0.1 ms** |
| plain `SO_REUSEADDR` bind on that same listener | **succeeds** — the silent double-bind of A1/A2/B reproduced at the socket level |
| `http.client` GET `/healthz` against a live listener (classifying the owner) | **24.5 ms** |

**Consequence for the design (supersedes the plan's "probe by connecting first"):** a connect-first
probe would add ~2 s to every normal launch, because the common case is a free port. So `probe`
binds exclusively first. A successful bind means `FREE` with no connection at all. Only a *failed*
bind is followed by a `GET /healthz` to classify the owner as `SARTOR` or `FOREIGN`, and that
connect succeeds, so it costs ~25 ms. Measured: one run per row, not a rate.

Not measured: macOS or Linux (there a plain bind already fails on a listening port, so the bind
test is correct there but its timing is unmeasured here).

### Observed after the build (real `app.py`, scratchpad `e2e_launch.py`, same machine; one run per mode)

| Check | Default (reloader) | `FLASK_DEBUG=0` |
|---|---|---|
| second `python app.py --no-browser --port P` | **exit 0**, prints `sartor. is already running — http://localhost:P`; first copy still alive | **exit 0**, same message; first copy still alive |
| wall-clock of that second launch | 2.53 s | 1.86 s |
| `GET /healthz` | 200, `pid` 29000 (the serving child), `instance_id` matches the file | 200, `pid` 5608 |
| instance file `pid` | 13188 (the supervisor — **differs from `/healthz`**, as designed) | 5608 |
| `POST /api/shutdown` with no action header / `Sec-Fetch-Site: cross-site` | 403 / 403; server still up | 403 / 403; server still up |
| `POST /api/shutdown` same-origin with the action header | 202 `{"status":"stopping"}`; **process exit 0 after 0.49 s** | 202; **exit 0 after 0.33 s** |
| after Quit | instance file gone; port closed | instance file gone; port closed |

And with a plain `http.server` owning the port: `python app.py` **exit 1**, `! Port P is in use by
another program, so sartor. did not start. … sartor --port P+1`, **no instance file written**.

All processes started were killed; the only `python.exe` left was the unrelated isidium MCP server
(pid 28852). `git status` showed no `sartor-instance.json` (it is in `.gitignore`).

Not separated: how much of the 1.9–2.5 s second launch is interpreter and import time (`import app`
pulls the whole app) versus the probe, which the measured table above puts at tens of milliseconds
for an owned port.

### Found by the UX test: a dialog opened from the Settings drawer was unclickable

First run of `test_20261015_quit_and_unsaved_guard.py::test_quit_asks_first_then_shows_the_stopped_state`
failed at `page.click("#cbConfirmCancel")` with Playwright's own call log:
`<div data-settings-dismiss class="settings-drawer-backdrop"> from <aside id="settingsDrawer"> subtree
intercepts pointer events`. Cause (read in `static/style.css`): `.cb-modal` is `z-index: 1000`, the
Settings drawer `1500`. A confirm or error dialog opened **from** the drawer sat underneath its
backdrop, so a mouse user could not press Quit or Keep running.

Fix: `#cbConfirmModal, #errorModal { z-index: 1600 }` beside the drawer rules, scoped to the two
shared dialogs a drawer control can open (the second is the 501/403 path of Quit). Same test, same
selectors, passes after. Before/after is one run each.

**Not checked:** whether other flows already open `#errorModal` from the drawer (profile fetch
failure) and were hit by the same stacking. The new rule would fix them too; that is a side effect,
not a finding.

### Idle shutdown: the first real run was invalid, so it is NOT a result

`idle_e2e.py` (`--idle-timeout 5`, default reloader mode) was still up after 544 s. The run's log
shows why it proves nothing: the Werkzeug reloader watches every `.py` under the repo root and
restarted the serving child three times (17:37:36, 17:39:04, 17:41:24) because this session edited
`ui_pages/selectors.py` and the new test file meanwhile. Each restart re-runs `main()`, which builds
a fresh tracker, so the 300 s clock restarted; the last restart was ~100 s before the script gave up.

Consequences recorded rather than guessed at:

- **Idle shutdown was not demonstrated by that run.** A clean run is below (single-process mode first,
  then the reloader mode, with no `.py` edited while it runs).
- It does surface a real property: **in the reloader (dev default), a code change resets the idle
  clock** — expected for a dev server, harmless, and not worth a mechanism.

**Clean single-process run (`FLASK_DEBUG=0`, `--idle-timeout 5`, nothing edited, `/healthz` polled
every 20 s throughout):** `exited: true`, `exit_code: 0`, **`seconds_up: 300.1`**, instance file
removed. So idle shutdown works in a real process, and the `/healthz` exemption holds under real
polling (30 polls did not extend the clock). One run.

**Clean reloader-mode run (the dev default; `--idle-timeout 5`; only `.md` edited while it ran;
`/healthz` polled every 20 s):** `exited: true`, `exit_code: 0`, **`seconds_up: 300.3`**, instance
file removed, **0 "Detected change" lines** in the log (so the clock was never reset). The idle
monitor runs in the serving child; its `os._exit(0)` ended the supervisor with 0, as C observed.
One run. This supersedes the invalidated one above.

### Found while writing the docs: the in-flight count did not cover streamed responses

The doc sentence "a generation that is still running is never cut off" was about to ship, so it was
checked against the code. All four SSE routes (`blueprints/analysis.py:300`, `generation.py:1839`,
`assistant.py:284`, `diagnostics.py:102`) return `Response(stream(), mimetype="text/event-stream")`
**without** `stream_with_context`. Flask therefore tears the request down when the view returns,
before the generator does its work, and the teardown-time `tracker.end()` released the count at once.
Red-before test (`test_a_streamed_response_holds_the_in_flight_count_until_it_closes`): the
generator saw `in_flight == 0` for the whole stream — i.e. with `--idle-timeout` and the tab closed
mid-run past the timeout, the server could be stopped during a paid run, the one case the counter
exists for.

Fix: `_hand_count_to_stream` (an `after_app_request` hook) moves the count onto the response's
iterable via `werkzeug.wsgi.ClosingIterator`, released once when the server closes it (finished,
disconnected, or never read; the unstarted case is tested). Green after: `seen == [1, 1]`, count 0
after close, 0 after an abandoned stream.

Side effect observed and accepted: Flask turns an unhandled exception into a *streamed* 500, so
that count is also held until the response is closed — which every WSGI server does, and which the
test client does only via `with client.get(...)`. Two of my tests initially failed on exactly this
(instrument, not product).

**Not verified:** a real SSE route (`/api/generate/stream`) end to end under `--idle-timeout`; the
mechanism is proved on a route shaped like them, not on them.

### `ui_pages/selectors.py` importers

```
Grep  pattern: ^\s*(from ui_pages(\.selectors)? import|import ui_pages|from \.selectors import|
              from \. import .*selectors|from ui_pages\.selectors)   glob: *.py   (whole tree)
  -> 136 import lines across 83 files
     ui_pages/            12 files (wizard_*.py x6, base, corpus, dashboard_console, pipeline,
                                    prior_apps, user_picker)
     scripts/              2 files (capture_screenshots.py, bench_corpus_scale.py)
     tests/ux/conftest.py  1
     tests/ux/**          68 files
  => 14 non-test importers
```

```
Grep  pattern: __dict__|\bvars\(|getmembers|dir\(selectors|dir\(S\b|__annotations__|fields\(
      glob: ui_pages/**/*.py, tests/ux/**/*.py, scripts/capture_screenshots.py,
            scripts/bench_corpus_scale.py, tests/test_consumer_enumeration_gate.py
  -> 0 hits
```

**Negative finding:** nothing enumerates the registry's members. A new key or class cannot change
what an existing importer sees.

### `app.main()` callers

```
Grep  pattern: (app_module|app_mod|appmod|app)\.main\(|from app import[^\n]*\bmain\b|runpy|
              "app\.py"|'app\.py'     glob: *.{py,yml,yaml,toml,sh,cmd,ps1}
  -> tests/test_cli_setup.py:28,44   main(["--setup"])        returns before the server
     tests/test_cli_setup.py:52      main([])                 REACHES app.run  -> probe
     tests/test_cli_setup.py:61      main(["--host","0.0.0.0","--port","8080"])  REACHES app.run
     tests/test_cli_setup.py:75      main(["--no-browser"])   REACHES app.run
     tests/test_setup_api_key.py:275,281,290  main(["--doctor"])   returns before the server
  (the remaining hits are path strings in enforcement tests and scripts/wiki_relevance.py:158)
pyproject.toml:148    sartor = "app:main"        (console script)
Dockerfile:62         CMD ["sartor", "--host", "0.0.0.0"]   (goes through the console script)
```

### `_app_version`

```
Grep  pattern: _app_version|app_version   glob: *.{py,md,toml}
  -> web_infra/openapi.py:60 (def), web_infra/openapi.py:77 (the one call, SpecTree(version=...))
```

### Blueprint registration and route inventories

```
Grep  pattern: url_map|iter_rules|register_blueprints|from blueprints import|import blueprints|
              _BLUEPRINTS|ALL_BLUEPRINTS   glob: *.{py,md,json,yml}
  -> app.py:26 (import), :47 (def), :112 (call)
     scripts/generate_openapi_spec.py walks app.url_map, but strict mode keeps only the 5
       spectree-decorated routes (docstring :17-21) -> the new routes do not appear
     tests/ import individual blueprint modules for monkeypatching; none asserts the set of
       registered blueprints or a route count
     docs/wiki/pages/code-module-map.md:105, diagnostics-console.md:26, route-surface.md:25,36
       state a blueprint COUNT ("nine") in prose
Grep  pattern: before_request|after_request|teardown_request   glob: app.py, blueprints/**,
      web_infra/**, dashboard/**
  -> dashboard/routes.py:1000 only (a blueprint-scoped hook). No app-wide request hook exists.
```

### Egress and routing gates a new module must pass

```
tests/test_egress_allowlist.py:120   SANCTIONED_EGRESS_FILES   (socket / http.client / urllib.request
                                     importers outside this set fail the gate)
tests/test_route_containment_gate.py (AST over blueprints/**; filesystem indicators need
                                     _safe_username/_within or a reviewed exemption)
scripts/enforcement/guards/route_security_lint.py  (regex over app.py + blueprints/**.py)
tests/test_mypy_strict_roster_gate.py  (new top-level modules must be on the strict roster)
```

---

## Consumers

| # | Site (`path:line`) | Decision | Rationale |
|---|---|---|---|
| 1 | `ui_pages/selectors.py:403` (`Settings`) | **update** | Add the Quit control keys. Additive; 0 enumerators found. |
| 2 | `ui_pages/selectors.py` (new class `Lifecycle`) | **update** | One key for the stopped state, so the UX test and `capture_screenshots.py` share a handle. |
| 3 | `ui_pages/*.py` (12 importers), `scripts/capture_screenshots.py`, `scripts/bench_corpus_scale.py` | **no change** | Additive keys only; nothing enumerates members (0 hits above). |
| 4 | `tests/ux/**` (69 files incl. `conftest.py`) | **no change** | Same. The new UX test is the only new consumer. |
| 5 | `tests/test_cli_setup.py:52,61,75` | **update** | These reach `app.run`, so they would now probe the real machine's `:5000` / `:8080`. A dev server running there would turn them into "already running, exit 0". Stub the probe in these tests, and add the new `main()` cases beside them. |
| 6 | `tests/test_cli_setup.py:28,44`, `tests/test_setup_api_key.py:275,281,290` | **no change** | `--setup` and `--doctor` return before the probe by design (the probe sits after both). Asserted by a test, not assumed. |
| 7 | `pyproject.toml:148`, `Dockerfile:62` | **no change** | Same `main`; the container's `0.0.0.0` bind is probed on `127.0.0.1`, which a wildcard bind answers. |
| 8 | `web_infra/openapi.py:60,77` | **update** | Promote to `app_version()`; the single call site follows. |
| 9 | `web_infra/__init__.py:27,40` | **update** | Re-export `_is_same_origin_request`. 15 importers of the shim see an added name only. |
| 10 | `app.py:47-76` `register_blueprints`, `blueprints/__init__.py` | **update** | Mount and export `lifecycle_bp`. No test asserts the blueprint set (grep above). |
| 11 | `blueprints/users.py:95` | **update** | One new template variable; `index.html` reads it under `{% if %}`, so a missing value renders as before. |
| 12 | `scripts/generate_openapi_spec.py` | **no change** | Strict mode excludes undecorated routes; verified by reading the generator, and re-run at close-out. |
| 13 | `tests/test_egress_allowlist.py:120` | **update** | Add `instance.py` with its reason, plus a test pinning its only URL host to `127.0.0.1`. Needs the C-2 amendment first. |
| 14 | `docs/governance/charter.md` C-2, `SECURITY.md`, `CHANGELOG.md` | **update** | The amendment ceremony (dated entry, CHANGELOG, owner sign-off at the PR). |
| 15 | `docs/wiki/pages/code-module-map.md:105`, `diagnostics-console.md:26`, `route-surface.md:25,36` | **update at close-out** | Blueprint count prose goes stale; `app.py` is wiki-relevant (`scripts/wiki_relevance.py:158`), so the scoped `/wiki-self-update` is required before the PR. |
| 16 | `docs/user/install.md` (`:641-645` "Port 5000 already in use", flags list) | **update** | The behaviour the section describes changes. Verify every label against `templates/index.html`. |
| 17 | `.gitignore` | **update** | `sartor-instance.json`: in a dev checkout `base_dir` is the repo root. |
| 18 | `pyproject.toml:156-173`, `:437-472` | **update** | `instance` into `py-modules` and the strict roster. |
| 19 | `scripts/wiki_relevance.py:155` `KNOWN_RELEVANT_TOP_LEVEL` | **update** | **Found after the first draft of this table**, by a name search for the sibling root module (`preflight`): `tests/test_wiki_relevance_classification.py` requires every tracked root entry to be classified, so a new root `instance.py` fails it until listed. Added. The derived-set test reads `git ls-files`, so the file must be staged before that test sees it. |

---

## Deferred

- **Two launches racing inside the probe window** (both see `FREE`, both bind, which Windows allows:
  A1). The instance file is written *after* the probe, so it cannot arbitrate. Closing it needs
  either an exclusive create before the probe or `SO_EXCLUSIVEADDRESSUSE` on the listening socket,
  and the latter means replacing `app.run` with a hand-built server. **Declared, not closed.** The
  window is a few hundred milliseconds between two user-initiated launches; the consequence is today's
  behaviour, not a new one. To be recorded on item 146 as an open limit.
- **The probe checks `127.0.0.1` only**, never the `--host` value. A user who binds a specific LAN
  address gets no single-instance protection on that address. The constant host is what lets the
  egress pin test be an exact assertion; widening it would give up that property.
- **Item 145's image `HEALTHCHECK`**, `doctor` reporting a running instance, and the launcher reading
  the instance file: item 145's branch.
- **`analyzer.py:568` `LOG_DIR`, `db/session.py:24-25`, `preflight.py:415`** still ignore
  `SARTOR_HOME` (an earlier finding, `CHANGELOG.md:3045`). This branch writes one file under
  `Config.base_dir` and does not touch those.

---

## Verification

How a missed consumer would surface:

- `tests/test_cli_setup.py` fails loudly if the probe is not stubbed and a server owns `:5000`; the
  new `main()` cases assert the three outcomes against stub probes **and** one against a real loopback
  `http.server`.
- `tests/test_egress_allowlist.py` fails if `instance.py` is not sanctioned, and the new pin test
  fails if any host other than `127.0.0.1` appears in it (checked once by a scratchpad mutation).
- `tests/test_mypy_strict_roster_gate.py` and the docstring-coverage gate fail if the new modules are
  not registered.
- `tests/test_route_containment_gate.py` walks the new blueprint's routes; it must stay green
  *without* an exemption entry (the blueprint has no filesystem indicator by construction).
- `python scripts/generate_openapi_spec.py` run before and after: the path list is unchanged (5).
- `python -m scripts.gate`, cited with `--result`.
