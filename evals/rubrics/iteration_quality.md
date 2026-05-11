# Iteration Quality Rubric

You are grading the questions surfaced by the **iteration interview** — the post-generation clarifying step that probes the CURRENT draft's specific weaknesses, not the original resume. Good iteration questions reference items the candidate just edited, build on confirmed prior clarifications without re-asking them, and target specific weaknesses surfaced by the deterministic metrics. Bad iteration questions duplicate analyzer-time clarify questions, ignore the recent edit context, or fabricate gaps the four signal sources (recent edits, current draft text, deterministic metrics, prior clarifications) do not support.

## Inputs

The payload contains:
- `analysis` — the analyzer's output. Reuse the same gap context as `clarification_quality.md`: `essential_skills`, `comparison.gaps`, `comparison.title_alignment`, `keyword_placement`.
- `original_resume` — the ORIGINAL resume the user uploaded. Use only as historical reference; iteration questions should not target gaps already filled in the current draft.
- `current_draft_resume` — the CURRENT iteration's resume (possibly with the candidate's first-person edits typed in). This is the authoritative version the questions should probe.
- `current_draft_cover_letter` — the current iteration's cover letter, included for context.
- `recent_edits_summary` — short unified diff (or empty string) showing what the candidate edited since the last generation. When non-empty, at least one question should follow up on this.
- `deterministic_signals` — the four metric blocks computed on the current draft: `verb_diversity`, `specificity_density`, `grounding_overlap`, `keyword_coverage`. Weak signals (e.g. `verb_diversity.diversity_ratio < 0.5`, `grounding_overlap.missing_samples` non-empty, `keyword_coverage.still_missing_from_current_draft` non-empty) are the primary positive citation source.
- `prior_clarifications` — list of `{question, answer, kind}` already confirmed in earlier iterations. Iteration questions must NOT re-ask these but MAY follow up on them (deeper scope, frequency, ownership).
- `iteration_questions` — array the model produced. Each entry has `id`, `text`, `target_gap`, `kind`. `kind` is one of `experience_probe`, `scope_probe`, or the iteration-specific `iteration_probe`.
- `expected.expected_iteration_themes` — per-fixture map (when the fixture has an iteration scenario) with `iteration_probes` / `experience_probes` / `scope_probes` lists of themes that good iteration questions SHOULD cover for the simulated scenario.

## What good looks like

A strong iteration question set:

1. Contains 3–5 questions, no more, no fewer.
2. **Builds on prior clarifications, never re-asks.** If `prior_clarifications` already records "Yes, used K8s in production 2023", a question asking "Have you used Kubernetes?" is a `redundant_question` failure. Acceptable follow-ups: scale ("how many nodes / clusters?"), cadence ("primary on-call rotation or shadow?"), ownership ("did you set the SLOs?").
3. **At least 50% of questions are `experience_probe` or `iteration_probe`** combined. Pure scope clarification without any experience or iteration probing is too narrow for this stage — the iteration interview's primary value is sourcing new ground truth.
4. **When `recent_edits_summary` is non-empty, at least one question references the edit.** A user who just typed "shipped V2 to enterprise" should see a question probing scope, customer segment, or timeframe of that edit. Ignoring recent edits earns a `missed_recent_edit` failure.
5. **Each question's `target_gap` cites a SPECIFIC current-draft weakness** — name a JD essential skill still missing per `keyword_coverage.still_missing_from_current_draft`, quote a deterministic-signal value (e.g. "verb_diversity 0.32, repeated led/managed"), reference an item in `recent_edits_summary`, or cite a `prior_clarifications` entry it builds on. Generic gaps ("the candidate's background") fail.
6. Question text is ≤25 words, asks ONE thing (no compound "and/or" joining two distinct asks), is not leading.
7. No generic interview prompts ("Tell me about yourself").
8. Coverage of `expected_iteration_themes` (when present): at least one question hits one of the listed themes per kind that has a non-empty list.

## What bad looks like

- **Re-asking confirmed truths.** The most common iteration failure mode. If `prior_clarifications` records the answer, the question is redundant_question.
- **Targeting the original resume.** Asking about a gap that the current draft has already closed (e.g. "your resume doesn't mention K8s" when the current draft just added a K8s bullet) earns `targets_stale_draft`.
- **Ignoring the recent edit.** When `recent_edits_summary` is non-empty and zero questions reference it, that's a missed signal — the user's most recent action should drive the highest-value question.
- **Fabricating signal-source gaps.** Citing `target_gap: "verb_diversity is 0.32"` when the actual `verb_diversity.diversity_ratio` is 0.7 earns `fabricated_gap`.

## Scoring (0.0–5.0, one-decimal precision)

Anchor bands:
- **5.0** — All composition rules met. Every question cites a specific signal-source weakness in the current draft. When recent edits exist, at least one question follows up on them. No re-asking of prior clarifications. Hits at least one `expected_iteration_theme` per non-empty kind list. Concise, well-targeted, no leading or compound questions.
- **4.0** — Composition rules met; minor weakness — e.g. target_gap is paraphrased rather than directly cited, OR one expected theme list goes uncovered.
- **3.0** — One clear deficiency: too few/too many questions, recent edits exist but no question references them, OR one question re-asks a prior clarification, OR one question targets a stale gap the current draft already filled.
- **2.0** — Multiple deficiencies: e.g. recent edits ignored AND a redundant question, or several questions are generic, or several have no concrete cite.
- **1.0** — Mostly generic questions; little or no connection to current-draft signal sources; significant overlap with prior clarifications.
- **0.0** — No usable iteration questions; all generic, all redundant with priors, or all fabricate gaps the signals don't support.

You may emit fractional scores between bands. The pass threshold for this product is 4.0.

## Output

Respond with valid JSON only — no markdown fences, no commentary outside the JSON:

```json
{
  "score": 4.3,
  "reasons": ["one short bullet per finding, citing the specific question or omission"],
  "failed_rules": ["redundant_question", "missed_recent_edit", "targets_stale_draft", "fabricated_gap", "generic_question", "wrong_count", "too_few_experience_iteration_probes", "compound_question", "leading_question", "over_word_limit", "missing_expected_theme"]
}
```

`failed_rules` should be machine-friendly slugs from this set (extend if needed):
`redundant_question` (re-asks a prior_clarifications entry), `missed_recent_edit` (recent_edits_summary non-empty but no question references it), `targets_stale_draft` (gap already filled in current draft), `fabricated_gap` (cites a signal-source value that doesn't match), `generic_question`, `wrong_count` (not 3-5), `too_few_experience_iteration_probes` (<50% combined experience+iteration), `compound_question`, `leading_question`, `over_word_limit` (>25 words), `missing_expected_theme` (no question hits any expected_iteration_theme of its kind).
