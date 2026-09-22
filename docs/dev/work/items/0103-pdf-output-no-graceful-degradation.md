```toml
schema = 1
id = 103
kind = "item"
title = "PDF output is offered in the UI even when the Chromium binary is absent"
status = "closed"
decision_owner = "agent"
branches = [
  "feat/install-onboarding-preflight","docs/container-persistence-guidance"]
refs = ["app.py:160-200", "docs/install.md:30-36", "pyproject.toml"]
summary = "Missing Chromium is a setup warning but a runtime exception; the UI still offers PDF it cannot render."
resolution = "Instrumented first, then fixed, on feat/install-onboarding-preflight (2026-09-03) -- this item asked for that explicitly and it paid off twice. docs/dev/diagnosis/install-onboarding-preflight.md records seven observations from a two-arm probe (real browsers path vs an empty PLAYWRIGHT_BROWSERS_PATH). TWO REFUTATIONS: (O-1) render_pdf does NOT raise RuntimeError -- playwright.sync_api.Error's MRO is (Error, Exception, BaseException, object) and isinstance(exc, RuntimeError) is False, so BOTH pdf_render docstrings were false and this item had inherited the claim from one of them; corrected and pinned by a test. (O-2) chromium.executable_path names chromium-<rev>/chrome-*/chrome, but launch(headless=True) -- render_pdf's effective default -- needs chromium_headless_shell-<rev>, a different artifact; the exists(executable_path) probe this branch had already planned would have called a partial install 'available' and shipped the bug back. The fix: preflight.chromium_capability() checks BOTH artifacts via Playwright's own INSTALLATION_COMPLETE sentinel, reading revisions from driver/package/browsers.json without starting the Playwright driver (8.4ms vs 2912ms measured, O-5); the shell route passes pdf_available() to the template; both PDF buttons render disabled + aria-disabled with a visible reason. Unknown leans AVAILABLE so a future Playwright layout change degrades to today's behavior rather than blanking PDF out for everyone. On macOS below the Chromium floor the remedy text branches, because there `playwright install chromium` cannot succeed -- telling this item's own user to re-run the command that already failed is the misdirection the preflight exists to remove."
verified_by = [
  "tests/test_pdf_capability_ui.py (9 tests: both buttons, both states, aria, the visible reason, and that the probe is not re-run per request)",
  "tests/test_pdf_render_missing_chromium.py (4 tests pinning the corrected exception class)",
  "tests/test_preflight.py::TestChromiumCapability::test_probe_checks_headless_shell_not_just_executable_path",
  "docs/dev/diagnosis/install-onboarding-preflight.md (the two-arm instrument, O-1..O-7)",
]
```

**Observed** (2026-09-02, macOS 12.7.4). `python -m playwright install chromium` failed —
current Playwright releases ship no Chromium build supporting macOS 12. Setup reported this
as a warning and continued, correctly: `docs/install.md:30-32` states PDF is optional and
that DOCX, Markdown and the live preview do not need it.

**The gap is what happens afterwards.** Chromium's absence is a *warning* at setup time and
an *exception* at use time. Nothing in the UI reflects the missing capability — the PDF
output option remains selectable, and choosing it reaches a code path that expects a browser
binary. A user who accepted the setup warning has no way to know which of the offered output
formats will actually work.

**Proposed fix.** Detect Chromium availability and disable or hide the PDF option when it is
missing, with a short explanation pointing at `sartor --setup`. Degrading to DOCX/Markdown is
already the documented posture; the UI should express it.

**Note on the version range.** `pyproject.toml` pins `playwright>=1.40,<2.0`, so pip resolves
the newest 1.x — which is precisely the build that dropped macOS 12. Whether to pin lower for
older hosts, or simply document the floor, is a separate decision this item does not make.

## Updates

### 2026-09-02 — filed from a live macOS install session

Not yet observed as a runtime exception — the user was advised not to select PDF, so the
failure was avoided rather than seen. The claim that it throws is read from
`_run_setup()`'s own docstring ("a fresh install would hit a cryptic error the first time it
renders a PDF"), not from an observed traceback. Instrument before fixing (C-7).
