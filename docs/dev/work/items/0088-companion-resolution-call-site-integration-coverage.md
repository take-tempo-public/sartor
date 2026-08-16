```toml
schema = 1
id = 88
kind = "item"
title = "Integration coverage for the four companion-resolution call sites (3 preview routes + PDF render)"
status = "watching"
decision_owner = "agent"
branches = ["fix/b1-stale-template-companions"]
refs = [
  "generator.py",
  "pdf_render.py",
  "docx_to_persona_html.py",
  "docs/dev/blast-radius/b1-stale-template-companions.md",
]
summary = "The 3 preview routes + _render_pdf_from_json pass the refreshed companion; today only a manual grep verifies it."
```

**Origin.** Raised by the `fix/b1-stale-template-companions` Sonnet refuter as
`F2-render-pdf-wiring-untested`, judged CONFIRMED-but-defer by the closer's
orchestrator: the coverage gap is real, but closing it is a test-architecture
decision outside B1a's brief, not an implementation correction.

**The gap, reproduced.** `generator._render_pdf_from_json` calls
`pdf_render.html_template_path_for` at `generator.py:161` and `:219`. Its only
appearance under `tests/` is a docstring mention at
`tests/test_docx_to_persona_html.py:91`; no test drives `generate_resume(...,
output_format=".pdf")` through to a resolved template. The `.pdf` hits in
`tests/test_generate_cover_letter_formats.py:177,212` go through the
cover-letter renderer — a different function — not this path.

**Why this is lower risk than "untested" implies.**
`pdf_render.html_template_path_for` (`pdf_render.py:59-68`) is exactly `return
html if html.exists() else None` — byte-for-byte the same predicate
`resolve_companion_html` uses on its own absent branch (`if not
html_path.exists(): generate`). The `html_template is None` → bundled-Classic
fallback at `generator.py:263-273` is untouched by this branch. The swap is
behavior-preserving by inspection, and the staleness arm it depends on
(`companion_stamp_is_current`) is covered at module level by the tests added
on this branch (`tests/test_docx_to_persona_html.py`).

**Why deferred rather than fixed here.** Real PDF rendering is
Playwright/Chromium, and the existing PDF tests are skipif-gated
(`tests/test_pdf_render.py:369`, `:431`) — a faithful integration test would
skip in the default `pytest` the gate runs, adding no assurance to the gate
that actually blocks a merge. The alternative — monkeypatching a `render_pdf`
seam to assert only the resolved template path — introduces a new test seam
for a call site that is one of four structurally identical ones, and picking
that shape is a design decision, not a fix to what B1a shipped.

**Scope for the eventual fix.** Cover all four companion-resolution call
sites together, not just the PDF one: the three `blueprints/templates.py`
preview routes and `generator._render_pdf_from_json`. Assert each passes the
**refreshed** companion (post-`resolve_companion_html`), not merely a
resolved one — today the wiring is verified only by the blast-radius
dossier's manual `git grep -n html_template_path_for` check
(`docs/dev/blast-radius/b1-stale-template-companions.md`, "Verification"
section), which is a human step, not a gate.

## Updates

### 2026-08-12 — filed during `fix/b1-stale-template-companions` close-out (B1a closer)
