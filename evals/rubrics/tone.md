# Tone Rubric (Cover Letter)

You are grading whether the generated cover letter matches the project's prescribed voice: VP-level professional, concise, direct, confident, no throat-clearing or hedging.

## Inputs

- `generated_cover_letter` — the LLM-produced cover letter
- `job_description` — the JD (to assess specificity of the hook)

## Checks

1. **Length**: 250–320 words. Outside this band = automatic deduction.
2. **Three paragraphs** — hook, evidence, close.
3. **No throat-clearing openers**: First sentence MUST NOT begin with "I am writing", "I am excited", "I am pleased", "Please find", "I would like to".
4. **No hedging language**: "I believe", "I think", "I hope", "I feel", "I would like to", "I am hoping" — each occurrence is a deduction.
5. **No banned phrases**: `passionate about`, `team player`, `detail-oriented`, `hard worker`, `results-driven`, `leverage`, `synergy`. Each occurrence is a deduction.
6. **Specific hook**: First paragraph references something concrete about the company/role/JD beyond the role title.
7. **Active voice + confidence**: "I led", "I built", "I delivered" — not "I have had the opportunity to". Spot-check 2-3 sentences.
8. **Sentence length**: Average 12–16 words; no single sentence over 25 words. Sample 3-4 sentences if uncertain.

## Scoring (0–5)

- **5** — All eight checks pass.
- **4** — Seven of eight pass, one minor miss (e.g., 245 words instead of 250).
- **3** — Six of eight pass, OR one banned phrase appears.
- **2** — Five of eight pass, OR throat-clearing opener detected.
- **1** — Four or fewer pass.
- **0** — Letter is unrelated to the JD or unintelligible.

## Output

```json
{
  "score": 0,
  "reasons": ["one bullet per check that failed, with the specific phrase"],
  "failed_rules": ["throat_clearing_opener", "banned_phrase:leverage", "hedging:I_believe", "length_under", "generic_hook"]
}
```
