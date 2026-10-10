```toml
schema = 1
id = 159
kind = "item"
title = "UX tests can synchronize on the shared #_corpusToast (item 155's class); no class-wide guard"
status = "open"
decision_owner = "agent"
branches = ["test/assertion-strength"]
refs = [
  "static/app.js:5876",
  "tests/ux/regression/test_20260809_wizard_rail_frozen_gate.py:135",
  "tests/ux/regression/test_20260611_prior_app_resume_robustness.py:218",
  "docs/dev/handoffs/test-reliability.md",
]
summary = "Any UX test may wait on #_corpusToast, which every save writes (last writer wins); 155 was one. Guard the class."
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
