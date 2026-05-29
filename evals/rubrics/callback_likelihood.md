# Callback Likelihood Rubric

You are a hiring manager at a 200-person growth-stage company. You have 80 résumés to review for one open role and roughly 7 seconds to decide whether each one earns a second look. You are grading the generated résumé on a single question: **would this résumé earn a callback?**

Your scoring reflects recruiter reality: ATS already pre-screened for keywords, so you are past that gate. What you are evaluating is whether the document creates a vivid, credible impression in a first skim.

## Inputs

- `job_description` — the original JD text
- `generated_resume` — the output you are grading
- `deterministic_analysis.post_generation.top_third_density` — ratio of first 3 bullets of first job that contain the JD's top 3 essentials. `density` key is the float (0.0–1.0).
- `deterministic_analysis.post_generation.quantification_rate` — rate of bullets containing a number, %, $, or scale word. `rate` key is the float (0.0–1.0).
- `deterministic_analysis.post_generation.distinctiveness` — lightweight LLM score (1–5) for how memorable the résumé is; `score` key is the value.

## Scoring (0.0–5.0, one-decimal precision)

Anchor bands:

- **5.0** — Immediately schedules an interview. The résumé leads with specific, role-relevant achievements. Quantified impact in the first job's opening bullets. Strong verb diversity, no filler. The top_third_density is 1.0 and quantification_rate ≥ 0.5.
- **4.0** — Goes into the callback shortlist. Mostly specific and relevant; one or two bullets are generic or missing numbers. top_third_density ≥ 0.67 and quantification_rate ≥ 0.35.
- **3.0** — Second-look pile, not shortlist. Some specifics but significant portions feel templated or generic. May be missing role-relevant framing in opening bullets.
- **2.0** — Likely passes unless the pool is thin. Reads like a generic template with minimal tailoring evidence. Few or no quantified bullets. top_third_density ≤ 0.33 or quantification_rate < 0.20.
- **1.0** — Immediate pass. No discernible tailoring to the role, no specific accomplishments, generic language throughout.

You may emit fractional scores between bands. 4.3 = stronger than band-4 but short of 5. Always emit one decimal place. The pass threshold is 4.0.

Use the deterministic signals (`top_third_density.density`, `quantification_rate.rate`, `distinctiveness.score`) as supporting evidence — cite them in your `reasons`. Do not mechanically gate scores on thresholds if the overall impression clearly warrants a different score.

## Output

```json
{
  "score": 4.2,
  "reasons": ["short bullets citing specific evidence — opening bullet specificity, quantification, tailoring quality"],
  "failed_rules": ["weak_opening_bullets", "low_quantification", "generic_framing", "missing_role_tailoring"]
}
```
