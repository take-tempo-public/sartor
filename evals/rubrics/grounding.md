# Grounding Rubric

You are grading whether a generated resume + cover letter contains any claim that does not trace back to the original resume or supplemental resumes the candidate provided. Fabrication is the single worst failure mode of this product.

## Inputs

The payload contains:
- `original_resume` — the candidate's actual resume text
- `supplemental_resumes` — array of additional resume text the candidate has used
- `generated_resume` — the LLM-produced resume output
- `generated_cover_letter` — the LLM-produced cover letter
- `expected.forbidden_inventions` — regex patterns that MUST NOT appear in the generated output (per-fixture)

## Scoring (0–5)

- **5** — Every claim, number, title, company, and timeframe in the generated artifacts traces directly to source. Reframing and verb upgrades are fine; new facts are not.
- **4** — One minor reframing on the boundary (e.g., "improved performance" where source said "made faster") that a reasonable reader could accept.
- **3** — One clear new claim that source doesn't support, but the rest is grounded.
- **2** — Multiple invented details, mostly minor (small metric, small scope inflation).
- **1** — A major fabrication: invented role, invented company, invented credential, invented quantitative metric.
- **0** — Pervasive fabrication; the output describes a different candidate than the source.

## Output

Respond with valid JSON only — no markdown fences, no commentary outside the JSON:

```json
{
  "score": 0,
  "reasons": ["one short bullet per finding, citing the specific phrase"],
  "failed_rules": ["invented_metric", "invented_role", "forbidden_pattern_match", ...]
}
```

`failed_rules` should be machine-friendly slugs from this set (extend if needed):
`invented_metric`, `invented_role`, `invented_company`, `invented_credential`, `invented_timeframe`, `forbidden_pattern_match`, `scope_inflation`, `verb_overreach`.
