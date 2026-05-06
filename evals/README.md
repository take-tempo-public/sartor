# Resume Optimizer Eval Harness

Runs the full `analyze()` + `generate()` pipeline against fixture inputs and grades each output against a set of rubrics. Used to detect prompt-engineering regressions before they ship.

## Layout

```
evals/
  runner.py                    Orchestrator
  schemas/
    context_set.schema.json    JSON Schema for the context_set payload
  rubrics/
    grounding.md               No fabrication / source traceability
    keyword_coverage.md        JD keyword integration
    ats_format.md              Bullet/heading/length structure
    tone.md                    Cover letter voice + banned phrases
  fixtures/
    synthetic/                 Public-safe fixtures, committed
      sre-mid-level/
      pm-senior/
      data-scientist-junior/
    real/                      Your local JD/resume pairs (gitignored)
  results/                     JSONL output (gitignored)
```

## Running

```bash
# All synthetic fixtures × all rubrics (~12 grading calls, ~$0.20)
python evals/runner.py --suite synthetic

# Smoke subset — synthetic × grounding only (~3 grading calls, ~$0.10)
python evals/runner.py --suite synthetic --subset smoke

# Single named fixture
python evals/runner.py --fixture sre-mid-level

# Real fixtures (your local data)
python evals/runner.py --suite real
```

CI runs the smoke subset only when a PR carries the `eval` label. Full runs are local-only because Anthropic API costs apply.

## Adding a fixture

```
evals/fixtures/synthetic/{slug}/
  jd.txt            Plain text job description
  resume.md         Markdown resume (or .docx, .pdf)
  expected.json     {must_keywords: [...], forbidden_inventions: [regex...], min_grounding_score: 4}
```

Synthetic fixtures must use fictional companies and people — no real PII. Real fixtures go under `evals/fixtures/real/` (gitignored).

## How grading works

For each (fixture × rubric) pair:
1. Runner builds a `context_set` via `hardening.build_context_set()`
2. Runs `analyze()` then `generate()`
3. Sends generated artifacts + the rubric markdown to Claude Haiku 4.5 as the judge
4. Judge returns `{score: 0-5, reasons: [...], failed_rules: [...]}`
5. Result line appended to `evals/results/{timestamp}.jsonl`

Score ≥ 4 = pass. Score < 4 = fail. Exit code is 2 if any rubric fails.

The Step 8 `eval-judge` subagent uses the same rubrics and the same payload shape — the runner is the automated path; the subagent is the interactive-debugging path.
