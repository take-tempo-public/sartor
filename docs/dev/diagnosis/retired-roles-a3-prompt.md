# Diagnosis — retired roles reach the A3 draft_experience_summaries prompt

> **Status:** root cause PROVEN (deterministic reproduction failing on HEAD, below)
> **Branch:** `fix/retired-roles-a3-prompt`
> **Work item:** `docs/dev/work/items/0075-retired-roles-reach-a3-drafting-prompt.md`

---

## Symptom

A role soft-retired after analyze (`Experience.is_active = 0`) is still staged as an
`experience_summary_targets` entry and therefore reaches the `draft_experience_summaries`
Sonnet prompt. The stated invariant — "a retired role never reaches the LLM" — is narrower
than advertised: wasted Sonnet tokens on a role that can never render, be kept, or reach
the grounding union.

---

## Observed

- **Deterministic reproduction, failing on HEAD (`7a6d8e7`):**
  `tests/test_draft_experience_summaries.py::TestDraftExperienceSummariesRoute::test_retired_role_never_reaches_the_draft_prompt`
  — seeds two roles via the existing `_seed_intro` fixture, sets `is_active = 0` on the
  second, POSTs `/api/applications/<id>/draft-experience-summaries`, and asserts the
  retired role is not staged. Run 2026-08-11, this branch, pre-fix:

  ```
  tests\test_draft_experience_summaries.py:555: in test_retired_role_never_reaches_the_draft_prompt
      assert s.e2 not in staged, f"retired role {s.e2} reached the draft targets: {staged}"
  E   AssertionError: retired role 2 reached the draft targets: [1, 2]
  E   assert 2 not in [1, 2]
  FAILED tests/test_draft_experience_summaries.py::...::test_retired_role_never_reaches_the_draft_prompt
  ======================== 1 failed in 71.73s (0:01:11) =========================
  ```

- **The mechanism, at the code (read this session, `blueprints/applications.py`):**
  `_build_experience_summary_targets` iterates the frozen snapshot —
  `corpus = ctx.get("career_corpus")` (`applications.py:2722`), `for exp in corpus:`
  (`applications.py:2768`) — and never consults live `Experience.is_active`. The omission
  rule `if not bullets and not existing_intros: continue` (`applications.py:2798`) lets a
  retired role through on its frozen bullets alone: `existing_intros` IS live-filtered
  (`_active_intros_by_experience`, `applications.py:2848-2850`, joins
  `Experience.is_active == 1`), but `bullets` come straight from the snapshot.

- **The item's original filing was itself execution-verified** — the Epic A final
  adversarial reviewer executed `_build_experience_summary_targets` directly (item 75,
  Updates 2026-08-10), not just read it. This session's reproduction confirms it at the
  route level, through the real Flask route and a real migrated DB.

- **The proven sibling pattern to mirror:** the gap-fill lane builds
  `cand_exp_ids = {e.id for e in session.query(Experience).filter_by(candidate_id=..., is_active=1)}`
  (`applications.py:2408-2411`) and drops any proposal whose `experience_id` is not in it
  (`applications.py:2438`).

---

- **A second consumer, found by the gate, not by the first grep (C-10 lesson recorded
  plainly):** the first enumeration grepped `blueprints/applications.py` alone and
  concluded "one caller." Gate run 1 failed at mypy with
  `evals\corpus_drafting_probe.py:168: error: Missing positional argument
  "active_exp_ids" in call to "_build_experience_summary_targets"` — the A3 eval probe
  imports the route's private helper precisely so its staging matches production. The
  whole-tree grep (run after, as it should have been run before) confirms exactly two
  code consumers — the route (`blueprints/applications.py:2941`) and the probe
  (`evals/corpus_drafting_probe.py:168`) — with every other hit in docs/board text. The
  probe now stages the same live intersection. mypy acted as the deterministic backstop
  here; it will not catch a consumer that passes the same arity, so this does not excuse
  the grep.

---

## Falsified

- *(Nothing falsified — the filed mechanism was confirmed on the first reproduction run.)*

---

## Inferred

- *(Nothing left inferred — the mechanism under "Observed" is demonstrated by the failing
  test, not deduced.)*

---

## Falsification

The experiment was the reproduction test above, written and run BEFORE any production
edit.

- **If it fails on HEAD:** the filed mechanism (frozen snapshot never intersected against
  live `is_active`) is confirmed — build the fix. **← This is what happened.**
- **If it passes on HEAD:** the item-75 filing is wrong or already fixed; stop, widen, and
  update the work item instead.

---

## The fix

In `_build_experience_summary_targets`'s caller path, intersect the frozen
`career_corpus` snapshot against the live set of active experience ids before building
targets — the same query shape as the gap-fill lane's `cand_exp_ids` — so a role
soft-retired after analyze drops out of the staged set regardless of its frozen bullets.

Per the work item, the docstring at `applications.py:2709-2713` (claims the rule mirrors
`corpus_to_json_resume.build_json_resume_from_corpus` "exactly" — false while the code
reads only the snapshot, since that function reads the live DB with `is_active=1`,
`corpus_to_json_resume.py:187`) is fixed **in the same change as the code**, never alone:
the docstring describes the correct intent; patching prose alone would enshrine the
defect.

---

## Acceptance bar

- `test_retired_role_never_reaches_the_draft_prompt` passes with **zero retries** (a
  rerun-rescued pass is not a pass — C-7 rule 3).
- The pre-existing A3 suite (`tests/test_draft_experience_summaries.py`) stays green, in
  particular `test_stages_targets_and_persists_keyed_drafts` (both ACTIVE roles staged)
  and `test_recommendations_restrict_the_evidence_set` — proving the filter removes only
  retired roles.
- Full gate green: `python -m scripts.gate`.
