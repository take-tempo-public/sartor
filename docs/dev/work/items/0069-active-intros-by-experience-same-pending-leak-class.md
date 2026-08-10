```toml
schema = 1
id = 69
kind = "item"
title = "`_active_intros_by_experience` feeds a foreign PENDING intro into the draft prompt as \"existing intros\" -- same is_active-only filter the A3 pending-leak fix closed elsewhere"
status = "watching"
decision_owner = "agent"
refs = [
  "blueprints/applications.py",
  "docs/dev/blast-radius/role-summary-drafting.md",
]
summary = "Prompt-context bias only (no rendered-resume leak) -- lower severity than what A3 fixed, but the same root class."
```

**Disclosed in the A3 commit message itself (`7d3ff33`), filed here as the tracked
item it promised.** Quoted verbatim: *"Known gap, disclosed not hidden:
`_active_intros_by_experience` (existing per-role intros fed into the draft prompt
as context) has the same `is_active`-only filter -- a foreign pending intro could
bias a NEW draft's wording via prompt context. Does not reach any rendered resume
directly, so left out of this sprint's scope; named here for the record."*

**The mechanism, read directly off the code
(`blueprints/applications.py:2828-2854`, `_active_intros_by_experience`).** The
query joins `ExperienceSummaryItem` to `Experience` and filters on
`Experience.candidate_id == candidate_id`, `Experience.is_active == 1`, and
`ExperienceSummaryItem.is_active == 1` -- **no filter on
`ExperienceSummaryItem.is_pending_review`**. Its result (`intros_by_exp`) feeds
`_build_experience_summary_targets`'s `existing_intros` field
(`applications.py:2791,2822`), which is sent to `analyzer.draft_experience_summaries`
as prompt context labelled "existing intros for this role" -- i.e. an
`ExperienceSummaryItem` row kept-but-not-yet-reviewed for a **different**
application (via `/experience-summary-decide`'s keep path) can shape the wording
of a brand-new draft for **this** application, before anyone has reviewed it.

**Why this is the same class as the guard A3 already built, and lower severity.**
A3's commit fixed the equivalent gap at four read sites that reach a **rendered
résumé**: the composition GET picker, composition SAVE validation,
`corpus_to_json_resume._resolve_chosen_experience_summary_text`, and the grounding
union in `db/build_context.py`'s `_experience_summary_groups` (which excludes
pending rows unconditionally). This site is a fifth read of the same
`is_active`-only-filtered rows, but it feeds an LLM **prompt**, not output --
so a foreign pending intro can influence *phrasing*, never appear verbatim in a
downloaded document. That is a real, lower bar than a rendered-document leak, which
is why A3 scoped it out rather than folding it in.

**Relationship to the blast-radius dossier's D5.** `docs/dev/blast-radius/role-summary-drafting.md`'s
`## Deferred` D5 names the *same class* of gap (no cross-application pending-leak
guard for intro variants, mirroring gap-fill's `accepted_generated_bullet_ids`) but
enumerates a **different** set of read sites -- the composition GET's
`role_summary_variants`, `/recommend-experience-summaries` staging, and
`corpus_to_json_resume._resolve_chosen_experience_summary_text`. It does not name
`_active_intros_by_experience`. This item is the sixth site in that same family,
filed separately because it is the one the commit message flagged directly and
because its exposure route (prompt bias) differs from D5's (picker/render
visibility).

**Candidate fix, not evaluated or endorsed:** add `ExperienceSummaryItem.is_pending_review == 0`
(or an equivalent "belongs to this application or is already reviewed" condition)
to the filter in `_active_intros_by_experience`, mirroring the guard
`db/build_context.py`'s `_experience_summary_groups` already applies for the
grounding union. That would need its own read of whatever per-application
acceptance ledger A4 or a later sprint establishes for this row family --
`accepted_experience_summary_ids`, per this sprint's own precedent, is the
candidate shape (see the A4 sprint brief's "Decisions taken alone last sprint that
this one inherits").

## Updates

### 2026-08-09 — filed at `feat/role-summary-drafting` close-out (Epic A, sprint A3)
