# Grounding Rubric

You are grading whether a generated resume + cover letter contains any claim that does not trace back to the original resume or supplemental resumes the candidate provided. Fabrication is the single worst failure mode of this product.

## Inputs

The payload contains:
- `original_resume` — the candidate's actual resume text
- `supplemental_resumes` — array of additional resume text the candidate has used
- `generated_resume` — the LLM-produced resume output
- `generated_cover_letter` — the LLM-produced cover letter
- `expected.forbidden_inventions` — regex patterns that MUST NOT appear in the generated output (per-fixture)
- `deterministic_analysis.post_generation.grounding_overlap` — n-gram overlap between generated and source. Treat `missing_samples` (3-grams in generated absent from source) as strong evidence of fabrication when items contain noun phrases or technology names. Ignore stopword/glue n-grams. The overlap_ratio is informative but not definitive — paraphrase legitimately reduces ratio.

## Scoring (0.0–5.0, one-decimal precision)

Anchor bands:
- **5.0** — Every claim, number, title, company, and timeframe in the generated artifacts traces directly to source. Reframing and verb upgrades are fine; new facts are not.
- **4.0** — One minor reframing on the boundary (e.g., "improved performance" where source said "made faster") that a reasonable reader could accept.
- **3.0** — One clear new claim that source doesn't support, but the rest is grounded.
- **2.0** — Multiple invented details, mostly minor (small metric, small scope inflation).
- **1.0** — A major fabrication: invented role, invented company, invented credential, invented quantitative metric.
- **0.0** — Pervasive fabrication; the output describes a different candidate than the source.

You may emit fractional scores between bands. A 4.3 means stronger than band-4 but short of band-5; a 4.7 means borderline-passing-as-5; a 2.5 means halfway between bands 2 and 3. Always emit one decimal place. The pass threshold for this product is 4.0.

## Output

Respond with valid JSON only — no markdown fences, no commentary outside the JSON:

```json
{
  "score": 4.3,
  "reasons": ["one short bullet per finding, citing the specific phrase"],
  "failed_rules": ["invented_metric", "invented_role", "forbidden_pattern_match"]
}
```

`failed_rules` should be machine-friendly slugs from this set (extend if needed):
`invented_metric`, `invented_role`, `invented_company`, `invented_credential`, `invented_timeframe`, `forbidden_pattern_match`, `scope_inflation`, `verb_overreach`.
