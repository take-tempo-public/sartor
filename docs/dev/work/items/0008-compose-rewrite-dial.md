```toml
schema = 1
id = 8
kind = "item"
title = "Compose-time rewrite latitude - the 'generate but don't invent' dial"
status = "blocked"
decision_owner = "user"
depends_on = [6]
blocked_on = "evidence-gated on the PX-39 real-corpus run producing a comparison; owner has now excluded the Microsoft JD from that run"
refs = ["docs/dev/COMPOSE_REWRITE_DIAL.md", "docs/dev/RELEASE_CHECKLIST.md:2246-2276"]
summary = "Design doc landed (COMPOSE_REWRITE_DIAL.md); nothing built yet - read it before touching refinement/grounding code."
```

Full findings and design context live in `COMPOSE_REWRITE_DIAL.md` — read
that, not this summary, before acting. Corpus-selected bullets render
verbatim today, never re-worded for JD fit; that capability existed
(pre-2026-05 WYSIWYG-era `generate()`) and was lost as WYSIWYG-divergence
collateral, not a deliberate grounding decision. The middle-dial machinery
(`draft_surgical_refinement` + `supersedes_bullet_id` + `pattern_kind`)
already exists; it's missing a JD-driven, compose-wide trigger.

**Update (2026-07-28):** the design doc's own closing section proposed
using the Microsoft JD in a PX-39 run for a validating side-by-side
comparison. The owner has since directed that the Microsoft JD stay excluded
from PX-39 (not app-generated, not a fair pipeline comparison) — this
item's evidence path needs revisiting; `COMPOSE_REWRITE_DIAL.md` itself may
need a one-line update noting the divergence (not done here, flagged only).
Owner has separate annotation material for the normal `/tune-from-annotations`
workflow once the tuning phase opens.

## Updates

### 2026-07-28 — filed during chore/work-item-tracking (migrated, with the Microsoft-JD-exclusion update folded in)

### 2026-07-28 — item 6 (PX-39) closed; this item's evidence path is now empty, not just JD-excluded

Owner directive: keep `depends_on = [6]` and `status = blocked` — do not
re-scope on this branch. Item 6 closed using zero-spend historical telemetry,
not a fresh paid run, so the "same paid runs yield both PX-39's deliverable
and a side-by-side" premise in `COMPOSE_REWRITE_DIAL.md`'s own "What would
validate this" section never happened — no side-by-side was produced,
independent of the Microsoft-JD exclusion already noted above. Corrected
`COMPOSE_REWRITE_DIAL.md:157-166` in place (original reasoning struck through
and kept for context). The owner's separate annotation material for
`/tune-from-annotations` (see that doc's "Where further material lands")
remains the likely real evidence channel — still the owner's call, not
decided here.
