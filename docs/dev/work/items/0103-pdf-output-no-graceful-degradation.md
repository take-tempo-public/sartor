```toml
schema = 1
id = 103
kind = "item"
title = "PDF output is offered in the UI even when the Chromium binary is absent"
status = "open"
decision_owner = "agent"
branches = ["docs/container-persistence-guidance"]
refs = ["app.py:160-200", "docs/install.md:30-36", "pyproject.toml"]
summary = "Missing Chromium is a setup warning but a runtime exception; the UI still offers PDF it cannot render."
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
