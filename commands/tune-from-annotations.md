---
description: Drive the annotations-driven prompt tuning loop — read an improvement_brief.md, draft a candidate system-prompt edit via the tune-drafter subagent, A/B it against the real-suite regression fixture (plus an anchor canary) using the prompt-override primitive, present the delta tables, and promote only on explicit approval. analyzer.py is never edited until you say "promote."
argument-hint: [--candidate <name>] [--subset smoke|full]
allowed-tools:
  - Bash
  - Read
  - Edit
  - Write
---

The annotations-driven sibling of [`/prompt-tune`](prompt-tune.md). Where
`/prompt-tune` asks the user for the wording change, this command **reads the
improvement brief** (`evals/annotation.py`'s `build_improvement_brief` output)
and drafts the candidate from it, then A/Bs against the **real-data** regression
fixture the annotation contract produced. It is built on the same prompt-override
primitive (`analyzer.prompt_overrides` + the runner's `--prompt-overrides`), so
`analyzer.py` is **not edited during the trial** and the candidate run is logged
as `prompt_version=candidate:<hash>` (never pollutes score-over-time). The
constant is edited only at the very end, on an explicit **promote**.

Resolve `<name>` from `--candidate` (default: the single candidate directory
under `evals/fixtures/real/`). All inputs live in
`evals/fixtures/real/<name>/`: `improvement_brief.md`, `seed.json`, and the
collated fixture dir (with `expected.json` + `jd.txt`).

### Scope note — what the override primitive can A/B

`--prompt-overrides` only injects the **system-prompt constants** in
`analyzer._BASE_SYSTEM_PROMPTS` (`SYSTEM_PROMPT`, `CLARIFY_SYSTEM_PROMPT`, …). It
does **not** override user-prompt builders. The cover-letter opener rule lives in
`_COVER_LETTER_RULES_BLOCK`, a user-prompt fragment — so a cover-letter-opener
fix is A/B'd as a **`SYSTEM_PROMPT`** worked example (the AGENTS.md way to teach a
failure mode). If the durable home turns out to be `_COVER_LETTER_RULES_BLOCK`,
that is a promote-time choice the trial cannot directly measure — call it out
rather than silently overriding a constant the primitive can't reach.

## Steps

1. **Clean base.** `git status` — confirm a clean tree (keeps the optional final
   promote edit reviewable). Confirm `evals/fixtures/real/<name>/` has
   `improvement_brief.md` and `seed.json`; if missing, stop and point the user at
   the export → bootstrap → annotate → collate steps in
   [`evals/README.md`](../evals/README.md).
2. **Baseline (no overrides).** Run both suites and capture each JSONL path the
   runner prints:
   - target: `python evals/runner.py --suite real --seed evals/fixtures/real/<name>/seed.json $ARGUMENTS`
   - canary: `python evals/runner.py --suite anchor $ARGUMENTS`
   (`$ARGUMENTS` defaults to `--subset full`.) The anchor canary exists because a
   `SYSTEM_PROMPT` change is global — it must not regress the committed synthetic
   fixtures.
3. **Draft the candidate.** Delegate to the **`tune-drafter`** subagent with the
   `improvement_brief.md` path + the target constant (default `SYSTEM_PROMPT`).
   It is **read-only** (`Read`/`Grep`/`Glob` only — no `Edit`/`Write`): it returns
   the *full* candidate constant text in its message and cannot touch
   `analyzer.py`, so the baseline it was drafted against stays intact for the A/B.
   Take its returned text and `Write` it to `evals/_tune_candidate.json` as a
   one-key object: `{"<CONSTANT_NAME>": "<full candidate prompt text>"}`.
   (Override values are full prompt text, not diffs.)
4. **Candidate (overrides active).** Re-run both suites with the override and
   capture each JSONL path:
   - `python evals/runner.py --suite real --seed evals/fixtures/real/<name>/seed.json --prompt-overrides evals/_tune_candidate.json $ARGUMENTS`
   - `python evals/runner.py --suite anchor --prompt-overrides evals/_tune_candidate.json $ARGUMENTS`
   Note the `candidate:<hash>` from each run's "PROMPT OVERRIDES ACTIVE" banner.
5. **Delta tables.** For each suite, run the deterministic delta helper and show
   its output verbatim (don't hand-tally JSONL):
   - `python -m evals.tune --baseline <real_baseline.jsonl> --candidate <real_candidate.jsonl>`
   - `python -m evals.tune --baseline <anchor_baseline.jsonl> --candidate <anchor_candidate.jsonl>`
   Label them **real (target)** and **anchor (regression canary)**. The helper
   exits 2 if any rubric regressed (Δ ≤ −0.5) — surface that.
6. **Promote / Revert.** Ask the user. Promote **only** on an explicit "promote":
   - **Promote:** `Edit` the chosen constant in `analyzer.py` to the candidate
     text; bump `PROMPT_VERSION` to the next iteration **in the same edit**;
     append an [`evals/TUNING_LOG.md`](../evals/TUNING_LOG.md) entry following
     its four-question structure (what changed / why — the brief's failure mode /
     result — the real + anchor before-after scores from step 5 / what we
     learned); suggest a commit message like
     `feat(prompts): <rule> per <candidate> annotation brief`. Delete
     `evals/_tune_candidate.json`. Do **not** commit on the user's behalf — they
     review the diff first.
   - **Revert:** delete `evals/_tune_candidate.json`. Nothing in `analyzer.py`
     changed, so there is nothing to undo.

`evals/_tune_candidate.json` is gitignored — never commit it. If the anchor
canary shows a regression the user still wants to accept, that decision belongs
in the TUNING_LOG entry's "what we learned," explicitly.
