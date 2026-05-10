# Keyword Coverage Rubric

You are grading whether the generated resume successfully integrates the job description's essential keywords. ATS systems rank by keyword presence first; a tailored resume that omits the JD's vocabulary fails its primary job.

## Inputs

- `job_description` — the original JD text
- `deterministic_analysis.keyword_overlap.missing_from_resume` — keywords the JD has that the original resume lacked (these are the high-value targets)
- `analysis.keyword_placement` — the LLM's plan for where to weave each missing keyword in
- `generated_resume` — the actual generated output
- `expected.must_keywords` — keywords that MUST appear in the generated resume (per-fixture)

## Scoring (0.0–5.0, one-decimal precision)

Anchor bands:
- **5.0** — Every `must_keyword` and ≥80% of `missing_from_resume` keywords appear in `generated_resume`. Integration reads naturally; no keyword-stuffing or forced phrasing.
- **4.0** — Every `must_keyword` present, 60–80% of missing keywords integrated. Reads naturally.
- **3.0** — Every `must_keyword` present, <60% of missing keywords integrated, OR all keywords present but integration is awkward (keyword soup).
- **2.0** — One or more `must_keyword` missing.
- **1.0** — Multiple `must_keyword`s missing.
- **0.0** — The generated resume bears no relationship to the JD vocabulary.

You may emit fractional scores between bands. 4.3 = stronger than band-4 but short of 5; 3.7 = strong band-3 nearly at 4. Always emit one decimal place. The pass threshold is 4.0.

## Output

```json
{
  "score": 4.3,
  "reasons": ["short bullets noting missing must_keywords and integration quality"],
  "failed_rules": ["missing_must_keyword:$keyword", "low_coverage", "keyword_stuffing", "forced_phrasing"]
}
```
