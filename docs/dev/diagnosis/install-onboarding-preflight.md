# Diagnosis — PDF is offered in the UI with no Chromium present, and the docstring naming the failure is wrong

> **Status:** root cause PROVEN for item 103's mechanism; the *design* for the
> capability probe was refuted twice by this instrument and rebuilt against the
> measurements below.
> **Branch:** `feat/install-onboarding-preflight`

This dossier covers **item 103** (`docs/dev/work/items/0103-pdf-output-no-graceful-degradation.md`),
which filed itself as explicitly un-observed:

> Not yet observed as a runtime exception — the user was advised not to select
> PDF, so the failure was avoided rather than seen. The claim that it throws is
> read from `_run_setup()`'s own docstring, not from an observed traceback.
> Instrument before fixing (C-7).

It is the C-7 instrument that item demanded, run before any fix.

---

## Symptom

On macOS 12.7.4 (2026-09-02, live non-maintainer install) `python -m playwright
install chromium` failed — current Playwright releases ship no Chromium build
supporting macOS 12. `sartor --setup` reported it as a *warning* and continued.
The two PDF buttons in the UI (`templates/index.html:468` `#fmtPdf`,
`templates/index.html:579` `#coverFmtPdf`) stayed selectable. A user who
accepted the setup warning has no way to know which offered output formats
actually work.

---

## Observed

All five probes run 2026-09-03 on this machine (Windows 11, Python 3.13.14,
`win32`, Playwright chromium v1223). **Every probe was run in two arms** — a
control with the real browsers path, and an absence arm with
`PLAYWRIGHT_BROWSERS_PATH` pointed at an empty directory. The control arm is
what makes the absence arm meaningful rather than vacuous (the lesson from
`reference-scroll-spy-settle-gate-leak`: an absence assertion needs a control).

**O-1 — `render_pdf` does NOT raise `RuntimeError`. The docstring is false.**
`pdf_render.py:117-120` claims "RuntimeError if Playwright fails to launch
(Chromium not installed → `python -m playwright install chromium`)", and
`pdf_render.py:308-310` repeats it for `render_cover_letter_pdf`. Measured:

```
playwright Error MRO: ['Error', 'Exception', 'BaseException', 'object']
issubclass(PWError, RuntimeError): False
issubclass(PWError, Exception):    True
```

The absence arm raises `playwright._impl._errors.Error`, and
`isinstance(exc, RuntimeError)` is **False**. Any caller written to
`except RuntimeError:` around `render_pdf` would not catch the missing-Chromium
case at all. Nothing in-tree does today (`blueprints/generation.py` catches
broad `Exception`), so this has not yet produced a live bug — but it is a
docstring contradicting the code it describes, on a module inside the
deterministic boundary.

**O-2 — `chromium.executable_path` names a DIFFERENT binary than
`launch(headless=True)` needs.** `render_pdf:163` calls `p.chromium.launch()`
passing no `headless` argument, so it takes the headless default. Absence arm,
verbatim first lines:

```
chromium.executable_path : ...\empty-browsers\chromium-1223\chrome-win64\chrome.exe
launch(headless=True)  -> BrowserType.launch: Executable doesn't exist at
    ...\empty-browsers\chromium_headless_shell-1223\chrome-headless-shell-win64\chrome-headless-shell.exe
launch(headless=False) -> BrowserType.launch: Executable doesn't exist at
    ...\empty-browsers\chromium-1223\chrome-win64\chrome.exe
```

Different artifact, different directory. `exists(executable_path)` is therefore
**not** a sound probe for "PDF will work" — it checks the headed binary while
the PDF path needs the headless shell. This refuted the probe design this
branch's plan had written down before the instrument ran.

**O-3 — a chromium install is five artifacts, not one.**
`python -m playwright install --dry-run chromium` reports five install
locations: `chromium-1223`, `chromium_headless_shell-1223`, `ffmpeg-1011`
(twice), `winldd-1007`. So a partial or interrupted install is a real state,
and it is exactly the state O-2's single-stat probe would misreport.

**O-4 — Playwright writes its own completeness sentinel.** Every artifact
directory under the browsers root carries an `INSTALLATION_COMPLETE` marker
file:

```
YES  chromium_headless_shell-1223      YES  chromium-1223
YES  chromium_headless_shell-1234      YES  chromium-1234
YES  ffmpeg-1011                       YES  winldd-1007
```

That is a stronger signal than directory existence: it distinguishes a complete
install from an interrupted one.

**O-5 — probe cost, measured, both arms.** This is the measurement that decided
the design:

| Probe | control | absence | what it checks |
|---|---|---|---|
| `sync_playwright()` + `executable_path` | **2912 ms** | **3099 ms** | 1 of 5 artifacts |
| `browsers.json` + 2 stats, driver never started | **8.4 ms** | **8.5 ms** | both chromium artifacts, via O-4's marker |
| `playwright install --dry-run chromium` | 4071 ms | 3559 ms | all five |
| real `launch()` + `close()` | **14369 ms** | 324 ms | definitional |

Entering `sync_playwright()` spawns the Node driver process — the ~3 s is that,
not the stat. The earlier 0.4–2.5 ms figure for `exists(executable_path)` was
measured *inside* an already-open context and is not what a caller pays.

**O-6 — the headless-shell path is derivable, cheaply and without the driver.**
`playwright/driver/package/browsers.json` carries the revision for both
`chromium` and `chromium-headless-shell`; the browsers root is
`PLAYWRIGHT_BROWSERS_PATH` or the per-OS cache default. Verified in both arms:

```
CONTROL:  headed=True  shell=True  revs=1223/1223
ABSENCE:  headed=False shell=False revs=1223/1223
```

**O-7 — printing the Playwright error crashes on a cp1252 console.** The
absence arm's message embeds box-drawing characters (Playwright's "Looks like
Playwright was just installed" banner); `print(exc)` raised a
`UnicodeEncodeError` out of `encodings/cp1252.py`. Same class as memory
`reference-windows-console-unicode-print-crash`. Anything that logs
`str(exc)` from this path on Windows can crash on the log call rather than the
render.

---

## Falsified

- **"`exists(chromium.executable_path)` is a sound availability probe."**
  Killed by O-2: it names the headed binary, while the PDF path launches the
  headless shell. This was the design written into this branch's own plan
  before the instrument ran — the plan said "Chromium availability —
  `chromium.executable_path` + a filesystem `exists()` check". Had the
  instrument been scoped only to `launch()` (the hypothesis under test), this
  would have shipped: the launch failure alone tells you nothing about which
  file the cheap probe checks.
- **"Use the Playwright API for the probe; it is the supported path."**
  Killed by O-5 on cost: ~3 s per process to start a Node driver, for a
  question answerable in 8.4 ms with two `stat` calls. At app startup that is a
  3-second regression paid by every user, including the majority for whom
  Chromium is present and PDF works.
- **"`render_pdf` raises `RuntimeError` on missing Chromium"** (the claim in its
  own docstring, and the claim item 103 inherited). Killed by O-1.

---

## Inferred

- **Unverified:** whether the `browsers.json` layout (`browsers[].name` /
  `.revision`) and the `<root>/<name>-<revision>/INSTALLATION_COMPLETE` path
  shape are stable across Playwright versions. Observed true for the pinned
  `playwright>=1.40,<2.0` resolution installed here (v1223 driver); **not**
  verified against other 1.x releases, and it is an internal layout, not a
  documented API. The fix must therefore degrade safely when the layout is
  unrecognised rather than reporting "unavailable" and hiding a working button.
- **Unverified:** whether macOS 12 specifically is the floor for the *headless
  shell* as well as for the headed build. Item 100 records the observed macOS 12
  install failure; this session could not test macOS.

---

## Falsification

**The experiment, stated so it can fail.** A test that must fail on HEAD:

Assert that with the browsers root pointed at an empty directory, the
capability probe reports PDF unavailable, and that with the real root it
reports available. On HEAD there is no probe at all, so the import fails and
the test errors — a fail. If it were to pass on HEAD, a probe already exists
and item 103's premise is wrong; stop and report.

Second, narrower: assert `render_pdf`'s documented exception type matches what
it raises. On HEAD the docstring says `RuntimeError` and the code raises
`playwright._impl._errors.Error` (O-1), so an assertion tying the two together
fails on HEAD.

Both are deterministic, no browser launch, no race.

---

## The fix

Written against O-1 through O-6, not against the docstring:

1. **`preflight.py`** — a `chromium_available()` probe that reads
   `browsers.json` for both chromium revisions and stats each artifact's
   `INSTALLATION_COMPLETE` marker (O-4, O-6). Never starts the driver (O-5),
   never launches a browser. Resolved once per process, not per request.
   When the layout is unrecognised or `playwright` is not importable, it
   reports **unknown** and the caller treats unknown as available — a layout
   change must not blank out a working feature (the Inferred gap above).
2. **Correct the two false docstrings** in `pdf_render.py` to name the
   exception the code actually raises (O-1).
3. **Surface the flag to the client** so both PDF buttons can be disabled with
   an explanation pointing at `sartor --setup` (item 103's stated fix).

---

## Acceptance bar

- The probe agrees with a real `launch()` in **both** arms — control and
  absence — not just the absence arm.
- The two `pdf_render.py` docstrings name `playwright.sync_api.Error`, and a
  test asserts the raised type matches, so the claim cannot silently rot again.
- Probe cost stays in the single-digit-milliseconds range; a regression to the
  ~3 s driver-start path is a failure of this work, not a detail.
- No test launches a real browser to check availability.
- Green without retries. A `PASSED` that needed a rerun is not evidence here
  (charter C-7 rule 3).
