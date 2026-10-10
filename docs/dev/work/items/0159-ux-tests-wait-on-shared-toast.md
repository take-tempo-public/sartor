```toml
schema = 1
id = 159
kind = "item"
title = "UX tests can synchronize on the shared #_corpusToast (item 155's class); no class-wide guard"
status = "closed"
decision_owner = "agent"
branches = ["test/assertion-strength"]
refs = [
  "static/app.js:5876",
  "tests/ux/regression/test_20260809_wizard_rail_frozen_gate.py:135",
  "tests/ux/regression/test_20260611_prior_app_resume_robustness.py:218",
  "docs/dev/handoffs/test-reliability.md",
  "tests/test_ux_toast_wait_gate.py",
]
summary = "Any UX test may wait on #_corpusToast, which every save writes (last writer wins); 155 was one. Guard the class."
resolution = "2026-10-10, test/assertion-strength: tests/test_ux_toast_wait_gate.py (outside the UX tier, so the gate and CI run it for every agent) finds every reference to the shared toast in the repo's Python (string constants, and loads of names bound to one), keyed by (path, enclosing qualname), and fails on any site not allowlisted at its exact count, or on a stale entry. The two existing reads are allowlisted with reasons (owner decision). Run on item 155's own history it flags the original wait as it ran in CI. Declared limits: a wait on toast text alone, and a selector built at runtime, are not caught."
verified_by = [
  "tests/test_ux_toast_wait_gate.py::test_toast_sites_equal_the_allowlist",
  "tests/test_ux_toast_wait_gate.py::test_scanner_finds_every_reference_shape_and_skips_prose",
  "docs/dev/diagnosis/assertion-strength.md (A5: four allowlist-drift mutations fail the gate; item 155's 3cfb98d wait flagged)",
]
```

**Filed 2026-10-10 on `test/assertion-strength`, at the owner's direction** (the session's
opening prompt: "a repo-wide guard against UX tests waiting on the shared toast").

**The class.** `_toast()` (`static/app.js:5876`) writes ONE lazily created element,
`#_corpusToast` (class `corpus-toast`). Every save in the app calls it, so its text belongs to
whichever call ran last. A UX test that synchronizes on that text can be satisfied, or
defeated, by an actor other than the action under test. Item 155 was exactly this: a notes
response landing after the company save turned "Company saved" into "Notes saved", and
response order alone decided pass or fail (`docs/dev/diagnosis/test-reliability.md` O5–O6).

**Why a guard (C-11).** The previous session recognized 155 as a member of the epic-19 UX
flake family and fixed that one test, but built no class-wide mechanism; its handoff
(`docs/dev/handoffs/test-reliability.md`, §Recurrences 1) declared the gap and surfaced it.
This item closes it.

**State at filing (observed, `rg -i toast tests`):** two UX tests read the toast.
- `test_20260809_wizard_rail_frozen_gate.py:135` waits on a synchronous refusal toast with no
  save in flight (0/112 in CI per the previous handoff).
- `test_20260611_prior_app_resume_robustness.py:218` reads it deliberately, after
  synchronizing on the response, to prove a forced response order held.

**Owner decisions (2026-10-10):** a static test outside the UX tier, so the gate and CI run it
for every agent; both existing reads allowlisted with written reasons.

## Updates

### 2026-10-10 — filed on `test/assertion-strength`

### 2026-10-10 — closed on `test/assertion-strength`

Built as `tests/test_ux_toast_wait_gate.py`; its module docstring states the mechanism and the
limits. Verified in `docs/dev/diagnosis/assertion-strength.md` A5:
- dropping an allowlist entry, adding a stale one, raising a count, and adding a new toast wait
  outside the repo to the scan each fail it;
- a self-test pins every reference shape (literal, constant alias, class-attribute alias,
  f-string, imported alias) and the docstring and comment exemptions in every run;
- on item 155's history it flags `test_card_company_editable_and_persists` at `3cfb98d`, the
  wait as it ran in CI.

Cost: 1.19 s per run, two reads of the repo's 410 `.py` files (measured; the reason is at
`_scan`).

**Declared limits, not built (C-0/C-11):**
- A wait on a toast message's text alone, such as `page.get_by_text("Notes saved")`, names
  neither the id nor the class. Detecting it would mean matching every `_toast('…')` message in
  `static/app.js` against test strings, and those strings also appear elsewhere in the UI.
  Unenforced.
- A selector assembled at runtime is not caught. Unenforced.
