```toml
schema = 1
id = 22
kind = "item"
title = "recommend_skill/suggest_skill/recommend_experience_summary/draft_surgical_refinement never logged despite being called"
status = "closed"
resolution = "Item's own two-explanation split resolved differently for each pair, not by a single live click-through as originally proposed. recommend_skill/suggest_skill's 'zero rows' claim was correct at filing time but is now moot: those 9 rows exist in the log, imported from the owner's separate E2E clone AFTER filing (a 128-row backdated block, matching closed item 6's own closure narrative verbatim), not from this checkout's own traffic. recommend_experience_summary and draft_surgical_refinement were genuinely never logged on this machine -- confirmed via three falsification tiers (docs/dev/diagnosis/never-logged-call-kinds.md): an inventory-complete capability probe (tests/test_call_kind_telemetry.py, all six zero-row call kinds, not just these two), route-level reachability tests (tests/test_call_kind_route_telemetry.py), and a live click-through against a real python app.py (candidate testuser, never the real robert candidate) that produced two real priced rows for the first time on this machine. Explanation (a) CONFIRMED for both: real, correct routes, simply never previously exercised in a gate-satisfying state -- recommend_experience_summary needs 2+ active ExperienceSummaryItem variants on one role (zero existed in this DB before this branch); draft_surgical_refinement needs a frozen approved_composition (none existed before this branch). No analyzer.py change. Diagnosis also found two additional never-logged kinds the original filing didn't list (suggest_skill_from_corpus, promote_clarification_to_bullet -- same disposition, live click-through deferred as out of this branch's UI-surface scope), fixed a latent UX-stub gap prophylactically (tests/ux/stubs.py, same shape item 21 fixed for check_refinement_scope), corrected item 33's severity (71.1% of the real telemetry log is synthetic, not 'low-severity' as originally characterized), and filed a new item 34 (corpus blueprints' _get_client unpatched in the UX harness -- worse in kind, a real billed-API risk, not just a stub gap)."
decision_owner = "agent"
refs = [
  "analyzer.py:3513",
  "analyzer.py:3734",
  "analyzer.py:3957",
  "analyzer.py:4544",
  "docs/dev/diagnosis/never-logged-call-kinds.md",
  "tests/test_call_kind_telemetry.py",
  "tests/test_call_kind_route_telemetry.py",
]
summary = "4 call kinds have real call sites but zero logged rows ever - dead paths or an instrumentation gap, not yet known."
```

Found 2026-07-28 during the PX-39 (item 6) pipeline trace. `analyzer.py`
defines `call_kind` strings for `recommend_skill` (`analyzer.py:3712`),
`suggest_skill` (`analyzer.py:3935`), `recommend_experience_summary`
(`analyzer.py:3491`), and `draft_surgical_refinement` (`analyzer.py:4522`),
each with a real Flask route that calls it
(`recommend-skills`/`suggest-skills`/`recommend-experience-summaries`/
`draft-refinement` in `blueprints/applications.py`). None of the four appear
even once in this project's `logs/llm_calls.jsonl` (4103+ records checked
2026-07-28), unlike every other call kind in the same file.

Two explanations, not yet distinguished: (a) these routes are real but simply
never exercised by any traffic that populated this log (plausible for
`suggest-skills`, which per the trace has no auto-fire site — user-triggered
only), or (b) something prevents the call from completing/logging when these
routes ARE hit. Needs a live click-through per route to tell which.

## Updates

### 2026-07-28 — filed during docs/pipeline-truth-and-era4-baseline

### 2026-08-03 — investigated, resolved, closed (`fix/never-logged-call-kinds`)

**Provenance correction to this item's own description above:** `recommend_skill` and
`suggest_skill` DO now have rows in the log (7 and 2 respectively) — but confirmed by
append-order analysis that those rows were imported from the owner's separate E2E clone
instance after this item was filed, not produced by this checkout's own traffic. The
filing was correct at the time it was written.

`recommend_experience_summary` and `draft_surgical_refinement` were genuinely never
logged, resolved via three falsification tiers rather than a single click-through:
Tier 1 proved the shared telemetry funnel emits correctly for all six zero-row call
kinds found (this item's remaining two, plus `suggest_skill_from_corpus` and
`promote_clarification_to_bullet`, which the original filing didn't list); Tier 2
proved both routes reach the real analyzer function; Tier 3 drove a real
`python app.py` against candidate `testuser` and produced two real priced rows —
the first `ExperienceSummaryItem` variants and the first frozen `approved_composition`
this database has ever held. Explanation (a) confirmed: both are correct, working
routes that had simply never been exercised in a state that satisfies their own
deterministic short-circuit gate. Full evidence chain:
`docs/dev/diagnosis/never-logged-call-kinds.md`.

**Filed forward:** item 34 (corpus blueprints' `_get_client` unpatched in the UX
harness). **Updated:** item 33 (real magnitude corrected to 71.1% of the log).
