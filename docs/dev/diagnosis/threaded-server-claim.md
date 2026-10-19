# Diagnosis — the repo says the production server is single-threaded; is it?

> **Status:** answered by observation on Flask 3.1.3: the production entry point **is threaded**. Why the earlier claim was written is a guess;
> see `## Inferred`.
> **Branch:** `fix/threaded-server-claim`

---

## Symptom

Two opposite claims about `python app.py` / `sartor` / the container's `CMD ["sartor", "--host", "0.0.0.0"]`:

- "Not threaded": the `context_transaction` docstring in `hardening.py` ("Werkzeug defaults to `threaded=False`"), item 25 ("single-threaded
  `app.run()` freezes the app"), `docs/dev/RELEASE_ARC.md`, `docs/dev/reviews/2026-07-diagnostics-round2-findings.md`,
  `docs/dev/diagnosis/context-write-lost-update-gap.md` Observed 8, `docs/dev/diagnosis/test-reliability.md` (item 156: "production can't reach it").
- "Threaded": `tests/ux/conftest.py` ("matching production's threaded dev server"), `db/session.py` (docstring: "Flask's threaded dev server").

Filed as item 177 point 1 by item 7's memory sweep. The same contradiction had been noted as "declared, not filed" in three earlier handoffs
(`docs/dev/handoffs/data-root.md`, `single-instance-and-quit.md`, `dependabot-triage-item.md`).

---

## Observed

All on 2026-10-18, Windows 11, Python 3.13.14, Flask 3.1.3, Werkzeug 3.1.8, branch `fix/threaded-server-claim` at `f32475c` plus the new test.

1. The instrument is `tests/test_production_server_concurrency.py`. Connection A sends a partial request (`GET /healthz HTTP/1.1\r\nHost: probe\r\n`, no
   terminating blank line) and stays open; connection B then sends a full `GET /healthz` and waits 1.5 s for `HTTP/1.`. It does not use any route
   other than `/healthz`, any LLM call or any user data.
2. **Negative control** (in-process `werkzeug.serving.make_server(..., threaded=False)`): B got no answer. `test_probe_negative_control_single_threaded_server_is_detected` PASSED.
3. **Positive control** (`make_server(..., threaded=True)`): B was answered. `test_probe_positive_control_threaded_server_is_detected` PASSED.
   So the probe separates the two cases.
4. **Production entry point, `FLASK_DEBUG=0`** (what the container sets): the test runs `python app.py --port <free> --no-browser` as a subprocess with a
   temp `SARTOR_HOME`, `SARTOR_DEMO=1`, stdin closed. B was answered while A was stalled. `test_production_entry_point_serves_concurrent_requests[debug-off]` PASSED.
5. **Production entry point, `FLASK_DEBUG=1`** (the local default; the reloader child serves): same command. B was answered.
   `[debug-on-reloader]` PASSED (`SARTOR_PROBE_RELOADER=1 python -m pytest tests/test_production_server_concurrency.py -k reloader`).
6. **Repeatability:** the whole file, with the reloader case enabled, was run 10 times in a row: `4 passed` each time (11.6 s to 14.6 s per run,
   140 s for ten). No run was retried (`pytest-rerunfailures` was not passed `--reruns`). After the loop a search of the process list for `app.py`
   found none.
7. **Timing of the default run** (reloader case skipped): `3 passed, 1 skipped in 6.71s`. The reloader case alone is about 5 s of call time.
   The first, cold run measured 42.33 s for four tests (one 9.47 s setup, probe timeout then 3.0 s); the probe timeout was cut to 1.5 s afterwards.
8. `app.py:494` (`app.run(host=args.host, debug=debug_mode, port=args.port)`) passes no `threaded` argument.
   `python -c "import inspect, flask; print([l for l in inspect.getsource(flask.app.Flask.run).splitlines() if 'threaded' in l])"` printed
   `['        options.setdefault("threaded", True)']`.
9. `git grep -n -i -E "single-threaded|not threaded|threaded=False|threaded server|threaded dev"` lists the sites in `## Symptom` and several
   frozen handoffs. The evidence `context-write-lost-update-gap.md` Observed 8 gives is a `grep` for `threaded\s*=` plus the missing kwarg at
   `app.py`; it records no request made to a running server. I did not read the evidence behind every other site.
10. **Lowest allowed Flask:** `pyproject.toml:27` pins `flask>=3.0,<4.0`. The `flask-3.0.0` wheel's `flask/app.py` printed
    `['options.setdefault("threaded", True)']` for the same search as in 8 (read from the wheel with `python -I`, not installed, not run).

---

## Falsified

- **"The production server serializes requests."** Observations 4 and 5 contradict it in both debug modes. A request is answered while another
  connection is half-sent.
- **"The 2026-07-20 correction found the truth."** That change (`fix/context-write-lost-update-gap`) replaced the claim "threaded server" with its
  opposite, and its evidence (Observed 8 there) is a grep for the kwarg, not a request to a running server.

---

## Inferred

**Hypothesis, not fact:** the 2026-07-20 correction read `werkzeug.serving.run_simple`'s default (`threaded=False`) as Flask's. Flask's `run()` sets it to
`True` unless the caller passes something (observations 8 and 10, read from source). That is a guess about why the claim was written, not
something I saw. The default is the same in the lowest and the installed Flask (observation 10), but I have run the probe on 3.1.3 only.

**Not observed:** the item 25 symptom itself ("the app freezes during a diagnostics run"). If the server is threaded, that freeze may have another cause
(for example the single-flight run slot in `blueprints/diagnostics.py`, or a browser holding connections). Nothing here shows what it was.

---

## Falsification

The probe passes only if a request is answered while another is stalled. On HEAD it passed for both debug modes, so the "single-threaded" claim is
dead. Per charter C-7 the next move is to correct the record, not the server: nothing in `app.py` changes.

---

## The fix

Documentation and test only. No behavior change; `app.py` untouched.

- `hardening.py`: the `context_transaction` docstring now says the server is threaded and the lock is load-bearing today.
- Appended errata (not rewrites) on the historical records, corrected in place on living docs, an `## Updates` entry on items 25 and 177.
- The test above stays as the pin, so a future change to the entry point or to Flask's default fails a test instead of flipping a docstring.

Consequences found but not fixed (scope): item 156's Windows `PermissionError` window is reachable in production, and the diagnostics-cancel
rationale in `docs/dev/handoffs/diagnostics-run-cancel.md` ("a real `POST /cancel` couldn't be serviced") no longer holds.

---

## Acceptance bar

- The 10-run loop above passes with no retries, and the test file in the gate shows no `RERUN`.
- `git grep -i "single-threaded"` leaves only frozen handoffs and records that carry an erratum.
- The docker image path is **not verified**: `CMD ["sartor", "--host", "0.0.0.0"]` reaches the same `app:main` (`pyproject.toml:148`), but no container was run.
