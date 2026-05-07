# ATS Format Rubric

You are grading whether the generated resume's structure is ATS-friendly. ATS parsers are unforgiving: tables, columns, exotic characters, and missing standard headings cause silent rejection.

## Inputs

- `generated_resume` — the LLM-produced output (markdown with `#`, `##`, `###`, bullets)
- `deterministic_analysis.ats_warnings` — any pre-existing ATS warnings on the input resume (for context)

## Checks

1. **Section headings**: At minimum one of `Experience` / `Professional Experience` / `Work Experience`, plus `Education`, plus `Skills` (or close variants) must appear as `## Heading` lines.
2. **Length**: 250–1100 words total. Too short = under-described; too long = ATS truncation risk.
3. **Bullet style**: Bullets use `-` or `*` consistently. No mixed bullet markers within a section. No nested bullets deeper than one level.
4. **No tables / no pipes**: A pipe character `|` in body text suggests a table layout. ≤3 pipes in the whole resume is OK (separators in contact line, etc.).
5. **No tab columns**: Tab characters as column separators break ATS parsing.
6. **Contact line near top**: Email and at least one of phone/LinkedIn within the first 5 lines.

## Scoring (0–5)

- **5** — All six checks pass.
- **4** — Five of six pass, one minor miss (e.g., 1140 words instead of 1100).
- **3** — Four of six pass, OR one major miss (missing major section heading).
- **2** — Three of six pass.
- **1** — Two or fewer of six pass.
- **0** — Output is unparseable or empty.

## Output

```json
{
  "score": 0,
  "reasons": ["one bullet per check that failed, with the specific evidence"],
  "failed_rules": ["missing_heading:Experience", "length_overflow", "table_layout", "missing_contact"]
}
```
