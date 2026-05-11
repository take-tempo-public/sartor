# Resume Optimizer — Agent and Contributor Contract

This file is the project-shared contract. Read it before any non-trivial change.
For machine-specific overrides, see your local `CLAUDE.local.md` (gitignored).

---

## Read These First

- [vision.md](vision.md) — product intent, LLM persona rules, output requirements
- [SECURITY.md](SECURITY.md) — threat model, API key rules, accepted risks
- [CONTRIBUTING.md](CONTRIBUTING.md) — branch + commit conventions, dev loop
- [README.md](README.md) — user-facing workflow

The project follows the [10 Principles framework](https://jdforsythe.github.io/10-principles/overview/). The codebase is annotated with principle references (P1, P2, P5, P6, P8, P9) — they are load-bearing, not decoration.

---

## Architecture at a Glance

**Two-, three-, or N-call LLM pipeline** (all in [analyzer.py](analyzer.py)):
- Call 1: `analyze()` — JD breakdown, ideal resume, comparison, keyword strategy
- Call 1.5 (optional): `clarify()` — 3-5 targeted questions surfacing real-but-undocumented experience and disambiguating analyzer-flagged scope. Uses `CLARIFY_SYSTEM_PROMPT` (a short dedicated persona, not the hiring-manager `SYSTEM_PROMPT`). User may skip; questions persist to the same context file for resumability.
- Call 2: `generate()` — tailored resume + cover letter + proofread pass. When clarifications are present, they ride along as `<candidate_clarifications>` and are treated as first-person ground truth (citable even when absent from the resume; no-invention rule still applies beyond the union of resume + clarifications). At iteration ≥ 1, the original primary + supplementals demote to `<historical_resumes>` and the current draft (edited > last_generated) becomes the authoritative `<resume>`.
- Call N (optional, repeatable): `clarify_iteration()` after each generation, plus another `generate()` per iteration. Probes the CURRENT draft's specific weaknesses using four signal sources: current resume vs JD gaps, recent edit diff, deterministic metrics (verb diversity / specificity / grounding / keyword coverage on the current draft), and prior clarifications (treated as established truth). Uses `CLARIFY_ITERATION_SYSTEM_PROMPT`.

**Core design rules:**
- **P1 Hardening** — deterministic Python for mechanical work; LLM only for fuzzy reasoning
- **P8 Human Gates** — two required review checkpoints (analysis review + post-generation refinement) plus one optional clarification interview between them, plus an optional iteration interview after each generation. Skipping any clarification step does not degrade generate below the prior behavior.
- **P5 Institutional Memory** — ALWAYS/NEVER BECAUSE rules in `analyzer.py:SYSTEM_PROMPT`; analyze-time clarification persona in `analyzer.py:CLARIFY_SYSTEM_PROMPT`; iteration-time persona in `analyzer.py:CLARIFY_ITERATION_SYSTEM_PROMPT`
- **P2 Context Hygiene** — `context_set` is the structured JSON contract between all stages. Iteration state (`iteration`, `parent_context_path`, `edited_resume_text`, `edited_cover_letter_text`, `last_generated_resume`, `last_generated_cover_letter`, `iteration_notes`) is all `total=False` so pre-iteration files round-trip. Each `/api/generate` writes a NEW timestamped child file (`context_{ts}_iter{N}.json`) rather than mutating the parent — the parent_context_path chain is the iteration audit trail.

**Multi-resume source pool:**
- Primary resume → `context_set["resume"]` (determines output format + style template)
- Included supplementals → `context_set["supplemental_resumes"]` (fed to both LLM calls)
- User controls inclusion via the two-zone chip UI; state persists to `configs/{user}.config`

**`context_set` lifecycle:**
```
/api/analyze               → build_context_set() → analyze() → save to output/{user}/context_*.json (iter 0)
/api/clarify (optional)    → load → clarify() → write back to same file (+ clarification_questions)
/api/answer-clarifications → load → merge answers → write back to same file (+ clarifications)
/api/generate              → load → generate() → save_iteration_context()
                             → output/{user}/context_{ts}_iter1.json (parent_context_path → iter 0)
/api/save-edits (optional) → load latest → store edited_resume_text / edited_cover_letter_text
/api/iterate-clarify (opt) → load latest → clarify_iteration() → append to clarification_questions
/api/generate (again)      → load latest (with edits and/or new clarifications)
                             → save_iteration_context() → context_{ts}_iter2.json (parent → iter 1)
```
The same `run_id` (minted in `/api/analyze`) propagates through every iteration so JSONL telemetry correlates the entire user session as one chain. Each `/api/generate` returns the new `context_path` — the frontend MUST adopt it for any subsequent call so the iteration chain stays intact.

---

## File Map

```
app.py              Flask routes + security helpers (_safe_username, _within).
                    /api/analyze, /api/clarify, /api/answer-clarifications,
                    /api/iterate-clarify, /api/save-edits, /api/generate.
analyzer.py         LLM calls: analyze(), clarify(), clarify_iteration(), generate(),
                    _supplemental_block(iteration), _current_draft_text, _current_cover_letter_draft,
                    SYSTEM_PROMPT (hiring-manager persona), CLARIFY_SYSTEM_PROMPT
                    (analyze-time interview), CLARIFY_ITERATION_SYSTEM_PROMPT (post-generation interview)
hardening.py        Deterministic tools: keyword extraction, ATS checks, build_context_set(),
                    save_iteration_context(); summarize_recent_edits + compute_iteration_signals
                    used by both /api/iterate-clarify and the eval iteration phase;
                    plus four post-generation metrics (verb_diversity, specificity_density,
                    grounding_overlap, call_cost) used by the eval harness and dashboard
generator.py        Document output: _write_docx() uses original .docx as style template
parser.py           Resume parsing (docx/pdf/md → structured dict)
scraper.py          LinkedIn/portfolio URL scraping (best-effort, fails gracefully)
static/app.js       All frontend logic — vanilla JS, fetch API, no framework. Iteration loop:
                    _detectEdits, _showEditModal, _gateEditsBeforeAction, runIterateClarify,
                    _onGenerationComplete (adopts new context_path per iteration).
static/style.css    LCARS aesthetic: dark bg, amber/teal/orange/blue palette.
                    Modal overlay, iteration pill, sr-only / skip-link / focus-visible.
templates/index.html Single-page app shell. Iteration pill, GET INTERVIEW QUESTIONS button,
                     edit-detection modal (role=dialog, aria-modal), skip link, sr live region.

dashboard/          Read-only Flask blueprint at /_dashboard. Score trend, rubric × fixture
                    heatmap, failure-mode clustering, cost cards. Chart.js via CDN; no new
                    Python deps. See dashboard/README.md.
tests/              Unit tests (pytest)
evals/              LLM eval harness with synthetic + real fixtures.
                    Float 0.0-5.0 scoring (schema_version 2) since 2026-05-09.
                    See evals/README.md and evals/TUNING_LOG.md for the iteration record.
.claude-plugin/     Project's Claude Code plugin (commands, agents, hooks)
.github/            CI workflows + issue/PR templates
configs/            User .config files — gitignored
resumes/            Uploaded resume files by user — gitignored
output/             Generated docs + context JSON by user — gitignored
logs/               JSONL telemetry from analyzer.py — gitignored
```

---

## Key Patterns — Always Follow These

**Security (every Flask route that touches the filesystem):**
```python
safe_user = _safe_username(username)          # sanitize + confirm user exists
safe_file = secure_filename(filename)         # strip traversal sequences
if not _within(path, PARENT_DIR): abort(403)  # resolved-path containment check
```
A `route-security-lint` hook enforces this once Step 5 lands — see `.claude-plugin/hooks/`.

**Document generation:**
- Always pass `template_path` (original `.docx`) to `generate_resume()` when output is docx
- `_write_docx()` opens the original as a style template — never call `docx.Document()` on blank
- `BULLET_RE` in `generator.py` normalizes all bullet variants

**LLM prompts:**
- The hiring-manager persona lives at `analyzer.py:SYSTEM_PROMPT`; analyze-time interview persona at `analyzer.py:CLARIFY_SYSTEM_PROMPT`; iteration-time interview persona at `analyzer.py:CLARIFY_ITERATION_SYSTEM_PROMPT`. Edit there, not inline.
- When any prompt changes (or any per-call prompt template), bump `PROMPT_VERSION` in the same commit so observability/eval can attribute behavior
- Supplemental resumes injected via `_supplemental_block(iteration)` — wrapper switches to `<historical_resumes>` (with the original primary folded in) when iteration ≥ 1
- Grounding check in generation prompt enforces no invented facts; the worked-examples block (OK / NOT OK pairs) is the load-bearing teaching signal — when adding new failure modes to the SYSTEM_PROMPT, also add a worked example here
- When clarifications OR first-person preview edits are present, the grounding check widens to accept them as legitimate source material. The no-invention rule still applies beyond the union of (resume + clarifications + typed edits) — keep this carve-out surgical, not blanket. The typed-edits OK/NOT-OK example ("Shipped V2 to enterprise" → don't add headcount the candidate didn't type) is part of the worked-examples block.
- `_call_llm` and `_parse_or_retry` accept an optional `system_prompt` arg; calls that override it (like `clarify` / `clarify_iteration`) pay one extra cache-miss on the system block but the heavy user-prefix cache is unaffected (both clarify variants use no cached prefix)

**Eval observability:**
- Eval results carry `prompt_version` so the dashboard's score-over-time chart can attribute regressions to specific prompt revisions
- Deterministic post-generation metrics (`verb_diversity`, `specificity_density`, `grounding_overlap`, `cost_usd`) ride along on every result. `grounding_overlap.missing_samples` is the actionable fabrication signal — items containing technology names or domain nouns are the candidates to inspect
- Document tuning iterations in `evals/TUNING_LOG.md` (what changed, why, scores before/after, lessons). This is the institutional-memory artifact for future tuners

**Frontend config persistence:**
- `_savePrimaryResume(filename)` — persists `latest_resume` to config on chip click
- `_saveIncludedResumes()` — persists `included_resumes[]` on badge toggle
- `saveConfig()` spreads `included_resumes` and `portfolio_urls` to survive panel saves

---

## Testing and Validation

Every change should pass the local validator loop before commit:
```bash
ruff check .
mypy .
pytest
```
CI runs the same on PR. Eval harness (Anthropic API costs apply) runs locally and on label-gated CI:
```bash
python evals/runner.py --suite synthetic --subset smoke   # ~$0.10, grounding only
python evals/runner.py --suite synthetic                  # ~$1.50, all 4 rubrics × 3 fixtures
```

Dashboard for trends + heatmap + failure-mode clustering: visit `http://localhost:5000/_dashboard` while `python app.py` is running locally. Only reachable via `localhost`/`127.0.0.1` (host-header guard).

---

## What NOT to Do

- Do not call `docx.Document()` without a template — output won't match the original's style
- Do not invent numbers, titles, or dates in LLM output — grounding check is the enforcement
- Do not skip `_safe_username()` / `_within()` on any new route touching the filesystem
- Do not commit real personal data: `evals/fixtures/real/`, `configs/*.config` (except `example.config`), `resumes/`, `output/`
- Do not add features or refactor beyond what was asked — minimal targeted edits only
- Do not call an LLM from `hardening.py`, `parser.py`, `scraper.py`, or `generator.py` — those are deterministic by design
- Do not introduce a new dependency without adding it to `pyproject.toml` AND updating `CHANGELOG.md`
