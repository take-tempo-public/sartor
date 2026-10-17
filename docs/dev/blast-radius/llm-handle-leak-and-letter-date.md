# Blast radius — llm-handle-leak-and-letter-date

> **Branch:** `fix/llm-handle-leak-and-letter-date`
> **Status:** enumeration complete for the planned edit set. **Unenforced:** `analyzer.py` and `hardening.py` are
> listed-but-not-gated in `scripts/enforcement/blast_radius.py:199-209`, so no hook checks this file (C-11, C-0).

---

## Surface

- `analyzer.py`:
  - `_LLMResponse` (new `handle_guard` validator) and the `ClarifyResponse.enforce_composition_rules` early-return
    at `:349`.
  - `_parse_or_retry_streaming` (gains `validation_context`).
  - 14 persona constants (gain a shared no-ids rule).
  - `_COVER_LETTER_RULES_BLOCK` FORMAT date line.
  - `generate_cover_letter_against_resume` and `_build_generate_prompt` (gain `<letter_date>`).
  - `PROMPT_VERSION`.
  - Call sites of `_parse_or_retry` / `_parse_or_retry_streaming` (gain `validation_context`).
- `hardening.py`: new pure functions only (`handles_from_markup`, `corpus_handles`, `find_leaked_handles`,
  `compute_letter_date`). No existing signature changes.
- `evals/runner.py`: new sibling record key `leaked_handles`; `_run_assemble_pipeline` gains a defaulted `capture`.

---

## Enumeration

Run on this branch before any code edit, over `*.py`, `*.js`, `*.md`, excluding `.git`, `.claude`,
`node_modules`, `docs-site` and `docs/`. Counts are files-per-symbol (`grep -rnE … | awk -F: '{print $1}' | sort | uniq -c`).

| Pattern | Hits by file |
|---|---|
| `_parse_or_retry\(` | analyzer.py 20; tests/test_analyzer.py 9; test_clarify_context_probe.py 2; one each in test_suggest_skills_from_corpus.py, test_suggest_skills.py, test_refinement_scope.py, test_recommend_skills.py, test_recommend_experience_summaries.py; onboarding/extract_experiences.py 1; evals/TUNING_LOG.md 1; CHANGELOG.md 1 |
| `_parse_or_retry_streaming\(` | analyzer.py 4; tests/test_analyzer.py 3 |
| `validation_context` | tests/test_clarify_context_probe.py 7; analyzer.py 5; evals/TUNING_LOG.md 1 |
| `hidden_qualities_non_empty` | tests/test_clarify_context_probe.py 7; analyzer.py 2; evals/TUNING_LOG.md 1 |
| `enforce_composition_rules` | analyzer.py 1; CHANGELOG.md 1 |
| `class .*\(_LLMResponse\)` | analyzer.py 19 |
| `LLMResponseError` | blueprints/applications.py 19; analyzer.py 16; blueprints/generation.py 5; blueprints/analysis.py 5; blueprints/corpus/skills.py 3; blueprints/corpus/proposals.py 3; scripts/smoke_phase_b1.py 3; evals/runner.py 2; onboarding/extract_experiences.py 1; tests/ux/stubs.py 1; plus 8 test files |
| `_COVER_LETTER_RULES_BLOCK` | analyzer.py 3; tests/test_corpus_mode_prompt.py 2; evals/TUNING_LOG.md 4; CHANGELOG.md 4; commands/tune-from-annotations.md 2; evals/README.md 1; agents/tune-drafter.md 1 |
| `generate_cover_letter_against_resume` | blueprints/generation.py 5; analyzer.py 3; evals/runner.py 1; demo_fixtures.py 1; 11 test files (fakes at test_deterministic_generate.py:122,180, test_eval_runner.py:924, test_frozen_composition_staleness.py:164, test_cover_letter_detached.py:96, test_context_write_races.py:186) |
| `PROMPT_VERSION` (`*.py`) | tests/test_prompt_overrides.py 12; analyzer.py 11; tests/test_avatar_streaming.py 7 (AVATAR_PROMPT_VERSION, separate); tests/test_corpus_mode_prompt.py 4; evals/corpus_drafting_probe.py 3; scripts/enforcement/blast_radius.py 2; db/build_context.py 2; tests/test_eval_runner.py 1; evals/runner.py 1; scripts/vector_before_after_eval.py 1 |
| Streaming retry display (`eventName === 'retry'`) | static/app.js:1151 and :1884 (both render `payload.reason`, :1153/:1155/:1886/:1888) |
| Persona constants (`^[A-Z_]*SYSTEM_PROMPT\s*=`) | 18 in analyzer.py; `_BASE_SYSTEM_PROMPTS` registry holds 17 (all but AVATAR) |

**Negative results:** the persona constants that will NOT get the rule: `AVATAR_SYSTEM_PROMPT` (documentation
assistant, no corpus ids), `SCOPE_CHECK_SYSTEM_PROMPT` (classifier, JSON only), `PROMOTE_CLARIFICATION_SYSTEM_PROMPT`
and `DRAFT_SUMMARY_SYSTEM_PROMPT` (their prompts ship no id-bearing markup — to be confirmed by grep when C3/C4 are
written, recorded under Deferred).

---

## Consumers

| # | Site | Decision | Rationale |
|---|---|---|---|
| 1 | `analyzer.py` `_parse_or_retry` (20 internal call sites) | update (pass `validation_context={"handle_guard": …}` at each prose-producing call) | the validator is inert unless the context says so, so unlisted sites keep today's behaviour |
| 2 | `onboarding/extract_experiences.py:165` | no change | extracts experiences from an uploaded résumé; ships no handles |
| 3 | `analyzer.py` `_parse_or_retry_streaming` (4 sites) | update (new `validation_context` param, passed to `model_validate` at :1599) | streaming analyze and generate need the same guard |
| 4 | `ClarifyResponse.enforce_composition_rules` (`:349`) | update | it enables on any non-None context; passing `handle_guard` alone to `clarify_iteration` would wrongly switch on the analyze-time question-mix rules |
| 5 | `tests/test_clarify_context_probe.py` (7 `hidden_qualities_non_empty`) | update/extend | pins the context contract the `:349` change touches |
| 6 | 19 `_LLMResponse` subclasses | no change to subclasses; guard lives on the base | one validator, skipped for id-named keys |
| 7 | `blueprints/applications.py` (19), `generation.py` (5), `analysis.py` (5), `corpus/skills.py` (3), `corpus/proposals.py` (3) | no change | they already map `LLMResponseError` to an error response; a repeated leak now reaches them, which the owner accepted |
| 8 | `static/app.js:1151`, `:1884` | no change | already render `payload.reason`; the validator's message is written to be user-readable |
| 9 | 14 persona constants | update (append `_NO_HANDLES_IN_PROSE_RULE`) | owner-decided scope: all nine builders |
| 8a | `_parse_or_retry` / `_parse_or_retry_streaming` final-attempt branch (`_accept_soft_leaks`) | update (owner decision 2026-10-17, after the candidate run's 1-in-6 hard error) | a purely handle-leak failure is accepted with a logged warning after the retry **unless** a leak is in a `hard_fields` field; those are `resume_content` and `cover_letter_content` for `generate`/`generate_streaming` and `cover_letter_content` for the dedicated letter call. Bad JSON or a missing key is never accepted. A leak in a shipped field still raises `LLMResponseError`. Checked by `TestShippedFieldsAreHard` (the three call sites) and `TestValidatorAndRetry` (hard, soft, mixed, non-leak) |
| 9a | `critique_proposal`, `check_refinement_scope`, `promote_clarification_to_bullet`, `draft_positioning_summary` parser calls | no guard (exempt, listed in `tests/test_handle_guard.py` `EXEMPT_CALL_KINDS` with a reason) | read, not assumed: an AST count of `id="` attributes in each function's source returned 0, and none calls an id-block helper. Critique still gets the prompt fix (its `source bullet b41` example) |
| 9b | `onboarding/extract_experiences.py:165` | exempt (`EXEMPT_CALLER_FILES`) | extracts experiences from an uploaded résumé; nothing shipped to leak |
| 9c | any future `_parse_or_retry*` call | fails `TestEveryCallForwardsAGuard` until it forwards `validation_context` or is listed with a reason | the fail-closed mechanism (C-11); it checks forwarding, not that the handle set is right (C-0) |
| 10 | `_BASE_SYSTEM_PROMPTS` registry / `tests/test_prompt_overrides.py:135` | no change to the registry; new constant must not end in `SYSTEM_PROMPT` | the drift test would otherwise demand registration |
| 11 | `_COVER_LETTER_RULES_BLOCK` (`generate()` and `generate_cover_letter_against_resume`) | update (FORMAT date line) | single source of truth for both letter paths |
| 12 | `tests/test_corpus_mode_prompt.py` `TestCoverLetterWorkedExamples` | no change expected | counts `NOT OK:`/`OK:` as `>=`; re-checked in C4 |
| 13 | Six `generate_cover_letter_against_resume` fakes | no change | the signature is unchanged; the date comes from a module clock seam, not a parameter |
| 14 | `commands/tune-from-annotations.md`, `agents/tune-drafter.md`, `evals/README.md` | no change | mention the rules block by name only |
| 15 | `PROMPT_VERSION` consumers (`db/build_context.py`, `evals/runner.py`, tests) | update value only | bump in the same commit as the prompt change (C4) |
| 16 | `evals/runner.py` `_run_assemble_pipeline` | update (defaulted `capture=None`) | assemble mode discards recommend rationales today |
| 17 | `det_metrics` passed to the judge (`evals/runner.py:~1401`) | no change | the new metric is a sibling key, so rubric inputs stay identical to history |

---

## Deferred

- **`_parse_or_retry` drops `max_tokens` on the retry call** (`analyzer.py:~1700-1709`). Seen while reading; out of
  scope for this branch. Carried in the handoff's ledger, not fixed here.
- **Saved analyses that already contain a handle** will keep feeding later letters and may trigger retries. Cleaning
  upstream prose before reuse is a separate design; raised to the owner.
- **Eval cannot exercise** `suggest_skills` ×2, `draft_gap_fill`, `recommend_experience_summaries`, `recommend_skills`,
  `draft_experience_summaries`, `draft_surgical_refinement`, or the critique call. They get unit tests and the
  runtime validator only.

---

## Verification

A missed consumer surfaces through: `tests/test_leaked_handles.py` (including a mutation control), a per-call test
that every prose-producing call forwards the guard context (a leak then a clean response yields one `_retry`),
`tests/test_prompt_overrides.py` (registry drift), `tests/test_clarify_context_probe.py` (the `:349` change), and the
full gate `python -m scripts.gate`. This dossier itself is unenforced, so the first two are the real check.
