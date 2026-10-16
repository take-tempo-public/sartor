```toml
schema = 1
id = 147
kind = "item"
title = "In-app Quit, opt-in idle shutdown, and beforeunload limited to unsaved edits"
status = "closed"
decision_owner = "agent"
branches = ["chore/release-v1.1.0", "feat/single-instance-and-quit"]
refs = [
  "app.py",
  "static/app.js",
  "blueprints/lifecycle.py",
  "instance.py",
  "docs/dev/blast-radius/single-instance-and-quit.md",
  "docs/dev/work/items/0146-*.md",
]
summary = "Closing the tab leaves the server running (correct), but there is no in-app way to stop it and no idle exit."
resolution = "2026-10-15, feat/single-instance-and-quit. Settings -> Quit Sartor (confirm first) POSTs /api/shutdown: localhost + same-origin + X-Sartor-Action header, 202 then exit 0 in 0.3-0.5 s with the instance file released (real app, reloader and FLASK_DEBUG=0); 501 unless started by sartor, so a WSGI host is never killed by a button. Opt-in --idle-timeout MINUTES (min 5, off by default): real runs exited 0 at 300.1 s (single process) and 300.3 s (reloader, the dev default; 0 reloader restarts) with /healthz polled throughout (exempt). An in-flight count blocks expiry, including streamed responses, which the first version did not cover (found by checking a doc claim; red-before test). beforeunload prompts only for a scheduled Compose autosave, Step-6 text differing from the generated baseline, or an open form modal with changed fields; silent after Quit. Found by the UX test and fixed: a dialog opened from the Settings drawer was unclickable (drawer z-index 1500 over .cb-modal 1000). Declared limits: the unload guard's editor and autosave arms set the state the predicates read rather than walking the wizard to it; the idle path was not run against a real SSE route (proved on a route shaped like them); one run per mode, not a rate. The first reloader-mode idle run was invalidated by this session's own edits (the reloader restarted the child) and is not counted, see the dossier."
verified_by = [
  "tests/test_lifecycle_routes.py::test_shutdown_accepts_a_same_origin_request_with_the_action_header",
  "tests/test_lifecycle_routes.py::test_shutdown_is_refused_and_does_nothing",
  "tests/test_lifecycle_routes.py::test_a_streamed_response_holds_the_in_flight_count_until_it_closes",
  "tests/test_instance.py::test_idle_monitor_fires_once_after_the_timeout",
  "tests/test_cli_setup.py::test_idle_monitor_runs_only_in_the_serving_process",
  "tests/ux/regression/test_20261015_quit_and_unsaved_guard.py",
  "tests/ux/a11y/test_axe_smoke.py::test_axe_quit_control_confirm_and_stopped_dialog",
]
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

### 2026-10-15 — closed on `feat/single-instance-and-quit`

Built with item 146 (owner pick). Evidence and the consumer enumeration are in
`docs/dev/blast-radius/single-instance-and-quit.md`. Three things the work turned up, each
written down there when found:

- **Idle expiry did not cover streamed responses.** The four SSE routes return
  `Response(generator)` without `stream_with_context`, so request teardown ran before the
  generator did its work and the in-flight count read 0 for a whole generation. Found by checking
  a sentence for the user docs against the code. Fixed by letting the response own the count.
- **A dialog opened from the Settings drawer was unclickable** (drawer `z-index` 1500, `.cb-modal`
  1000). Found by the new UX test; fixed for the two shared dialogs a drawer control opens.
- **The first reloader-mode idle run proved nothing.** The reloader watches every `.py` under the
  repo root and restarted the child three times while this session edited files, so the clock kept
  resetting. Recorded as not a result. Clean runs afterwards, with nothing edited: single-process
  exited at 300.1 s; reloader mode exited at 300.3 s with 0 restarts.

Left for item 145: the container `HEALTHCHECK`, `doctor` reporting a running instance, and the
launcher reading the instance file.
