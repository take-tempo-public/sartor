```toml
schema = 1
id = 75
kind = "item"
title = "Retired roles reach the A3 draft_experience_summaries prompt -- frozen snapshot never intersected against live is_active"
status = "closed"
decision_owner = "agent"
branches = ["fix/retired-roles-a3-prompt"]
refs = [
  "blueprints/applications.py",
  "db/build_context.py",
  "corpus_to_json_resume.py",
  "evals/corpus_drafting_probe.py",
]
verified_by = [
  "tests/test_draft_experience_summaries.py::TestDraftExperienceSummariesRoute::test_retired_role_never_reaches_the_draft_prompt",
]
resolution = "Both consumers of _build_experience_summary_targets (the A3 route and evals/corpus_drafting_probe.py) now pass a live active_exp_ids set (same query shape as the gap-fill lane's cand_exp_ids); the helper skips frozen-snapshot roles not in it, and the 'mirrors exactly' docstring was fixed in the same change, never alone. Diagnosis: docs/dev/diagnosis/retired-roles-a3-prompt.md."
summary = "_build_experience_summary_targets reads the frozen snapshot, not live is_active -- a retired role can reach Sonnet."
```

**The defect (verified by the reviewer executing the real function, not by
reading it).** `blueprints/applications.py:_build_experience_summary_targets`
(~line 2725) reads the **analyze-time frozen `career_corpus` snapshot** --
`corpus = ctx.get("career_corpus")`, then `for exp in corpus:` -- and never
intersects it against live `Experience.is_active`. A role soft-retired by A1b
therefore still reaches the `draft_experience_summaries` Sonnet prompt.

The sibling `existing_intros` input IS live-filtered
(`_active_intros_by_experience`, ~`applications.py:2801`, joins
`Experience.is_active == 1`), but the omission rule is `if not bullets and
not existing_intros: continue` -- so a retired role whose frozen snapshot
still carries bullets passes on the bullets alone.

**The asymmetry that makes this a real inconsistency, not a design choice.**
The sibling gap-fill lane was hardened at exactly this seam --
`draft_application_gap_fill` builds `cand_exp_ids` from the live DB
(~`applications.py:2410`, `.filter_by(candidate_id=candidate.id,
is_active=1)`). A3's lane did not get the same treatment.

**Blast radius, traced and bounded -- record this, it's why the item is
`watching` and not urgent.**

- Never renders: `get_application_composition` filters `is_active=1`
  (~`applications.py:1155-1160`), so the retired role gets no card.
- Cannot be kept: `experience_summary_decide` filters `is_active=1`
  (~`applications.py:3071`) -> 400 "Draft targets an unknown experience".
- Never reaches the grounding union: `assemble_source_union` reads
  `experience_summary_items`, built from the already-filtered `experiences`
  list (`db/build_context.py:98`, `:250`).
- `experience_summary_targets` never hits disk -- `ctx` is mutated in
  memory, then `context_transaction` re-reads fresh and writes only
  `llm_experience_summary_drafts`.

**Actual cost.** Wasted Sonnet tokens on an unusable role, an inert entry in
the in-memory context, and a stated invariant ("a retired role never reaches
the LLM") that is narrower than advertised.

**The docstring correction is part of this same future fix, not a
prerequisite or a separate item.** The docstring at ~`applications.py:2711`
claims the effective-bullet rule "mirrors
`corpus_to_json_resume.build_json_resume_from_corpus` **exactly**" -- it does
not, because that function reads the live DB (`corpus_to_json_resume.py:187`,
`is_active=1`) while this one reads the frozen snapshot. **The docstring must
NOT be "corrected" on its own**: the docstring describes the correct intent
and the code is what's wrong, so patching the prose alone would enshrine the
defect. Both get fixed together, by making the code match the documented
intent (intersect the frozen `career_corpus` snapshot against live
`Experience.is_active` before building targets, mirroring the
`cand_exp_ids` pattern already proven in the gap-fill lane).

**Candidate shape, not evaluated or endorsed:** load the set of currently
active experience ids alongside `existing_intros` (same query shape as
`draft_application_gap_fill`'s `cand_exp_ids`), and skip any `exp` in the
frozen `career_corpus` snapshot whose id is not in that set, before the
`if not bullets and not existing_intros: continue` check runs.

## Updates

### 2026-08-11 -- fixed on `fix/retired-roles-a3-prompt` (C-7 reproduction first)

Reproduction written and observed failing on HEAD `7a6d8e7` BEFORE the fix
("retired role 2 reached the draft targets: [1, 2]" -- full fenced run in the
diagnosis dossier). Fix is the candidate shape the filing sketched: the route
queries live active experience ids (ids-only, mirroring `cand_exp_ids`) and
the helper drops frozen-snapshot roles not in the set, before the
bullets/intros omission rule runs. One consumer the filing did not name was
found by the gate's mypy step: `evals/corpus_drafting_probe.py` imports the
route's helper for production-identical staging and now applies the same
intersection. Docstring corrected in the same change per this item's own
"never alone" rule.

### 2026-08-10 -- filed at `feat/prior-apps-pipeline` close-out (final Epic A adversarial review)

Filed following the final Epic A adversarial review's confirmed finding
(reviewer executed `_build_experience_summary_targets` directly, not just
read it). `decision_owner = "agent"` -- mechanical alignment with an
existing, proven sibling pattern (the gap-fill lane's live `is_active`
filter); no product call is involved.
