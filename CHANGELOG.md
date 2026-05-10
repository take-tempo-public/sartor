# Changelog

All notable changes to Resume Optimizer are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added — Eval & Dashboard Gap-Closing (2026-05-09 follow-up)
- **`run_id` correlation** between `logs/llm_calls.jsonl` and `evals/results/*.jsonl`. The runner mints one 12-hex UUID per fixture pipeline; both the analyze and generate calls share it in telemetry, and every per-rubric eval result inherits it. Live `app.py` traffic also generates run_ids and persists them on the saved `context_set` so `/api/analyze` and `/api/generate` from a single user session correlate. New "Run" column in both dashboard tables.
- **p50 / p95 latency and per-call cost percentiles** in `_summarize_calls`. A new `_percentile` helper does linear-interpolation percentiles over sorted lists. Surfaces tail behavior that means alone hide.
- **Local regression alerting** in `evals/runner.py`. Before a run starts, `_load_baseline_scores` walks every prior result file and builds a `{(fixture, rubric): most_recent_record}` baseline. After each grading, `_detect_regression` compares the new score to baseline; drops greater than `REGRESSION_DELTA` (default 0.5, env-overridable via `REGRESSION_DELTA`) log a `WARNING` with the prior `prompt_version` and accumulate into an end-of-run summary table.
- **`evals/rubrics/keyword_coverage.md` "covered in cover letter" rule** for keywords that match `expected.forbidden_inventions` (domain experience the candidate genuinely lacks). Prevents the no-win situation where the model is forced to choose between fabricating experience (loses grounding) or omitting keywords (loses keyword_coverage). The judge now credits a B2B PM applying to healthtech for placing `EHR` and `HIPAA` in the cover letter as transferable understanding rather than fabricated experience.
- **`SYSTEM_PROMPT` "metrics" rule expanded** with concrete examples: counts ("three reports"), durations ("one year", "monthly cadence"), team or scope sizes, GitHub stars, frequencies ("week over week", "24/7 on-call"). The previous narrower rule was being read as "only %s and $s" and dropping legitimate small numbers. `PROMPT_VERSION` 2026-05-09.1 → 2026-05-09.2.
- **TUNING_LOG entry for 2026-05-09.2** documenting the gap-closing iteration: 12/12 still pass, two +0.5 improvements, two -0.6 tone "regressions" flagged by the new alerter (within Haiku judge variance band; to be confirmed across the next 2-3 runs).
- **13 new unit tests** for `_normalize_eval_record` run_id default, `_percentile` interpolation/edge-cases, `_summarize_calls` percentile fields, `_detect_regression` baseline behaviors, and `_load_baseline_scores` excluding the current file. 96/96 tests passing total.

### Added — Eval & Dashboard Refinement (2026-05-09)
- **Float scoring (0.0–5.0, one-decimal precision)** across all four rubrics. Replaces the previous integer 0–5 scale; same band semantics, ~10× the granularity. The Haiku judge can now express "stronger than 4 but short of 5" as `4.3` instead of collapsing to `4` or `5`. Rationale: integer scoring hid real prompt-tuning progress and forced false equivalence between near-passing and clean-passing runs.
- **`schema_version` field** on every eval result (`schema_version: 2`). Old integer-score records load through `dashboard.routes._normalize_eval_record` which coerces them to floats and fills defaults; stored files are never rewritten.
- **Four deterministic post-generation metrics in `hardening.py`** computed on every eval run:
  - `compute_verb_diversity` — unique leading verbs / total bullets; flags repetition that the SYSTEM_PROMPT already discourages
  - `compute_specificity_density` — fraction of bullets containing a quantifier; pairs with grounding (high density + low grounding = invented numbers)
  - `compute_grounding_overlap` — 3-gram overlap between generated output and source. Returns up to 10 `missing_samples` 3-grams that the LLM produced but source doesn't contain — these are the actionable fabrication signals. Stopword-only n-grams excluded.
  - `compute_call_cost` — per-call USD using a `MODEL_PRICING` table for Sonnet 4.6 and Haiku 4.5
- **`prompt_version`, `deterministic_metrics`, `cost_usd`, `pipeline_latency_ms` fields** on every eval result, enabling regression attribution to specific prompt revisions.
- **Dashboard charts and aggregations** (no new Python deps; Chart.js loaded from CDN):
  - Per-rubric pass-rate bar chart
  - Score-over-time line chart with per-point `prompt_version` tooltip
  - Rubric × fixture heatmap (HSL color, red→green)
  - Top failure-modes table (per-record dedup of `failed_rules` slugs)
  - Total-cost and mean-cost-per-call summary cards
  - Graceful degradation: heatmap and failure-mode table render server-side; only bar/line charts require JS
- **Anti-invention prompt edits** in `analyzer.py` (`SYSTEM_PROMPT` and `generate()` GROUNDING CHECK): three new ALWAYS/NEVER rules and three OK/NOT-OK worked-example pairs targeting the failure patterns observed on `data-scientist-junior` (advanced-technique substitution, tool-vendor specificity, scope adjective escalation). `PROMPT_VERSION` bumped from `2026-05-06.5` to `2026-05-09.1` in the same commit.
- **`evals/TUNING_LOG.md`** — institutional-memory document recording each prompt iteration with what changed, why, scores before/after, and what we learned. Seeded with the 2026-05-09 anti-invention iteration (12/12 pass on synthetic suite, $1.46 total cost).
- **`dashboard/README.md`** — what the dashboard shows, how to launch it, schema-version compatibility notes, instructions for adding a new chart.
- **35+ new unit tests** (`tests/test_eval_runner.py`, extended `tests/test_hardening.py`, new `tests/test_dashboard_routes.py`) covering float coercion at the judge boundary, deterministic-metric edge cases, dashboard aggregations, and graceful-degradation rendering with no eval data.
- `pyproject.toml` replacing `requirements.txt` (pinned dep ranges + `[dev]` extras)
- `tests/` with 28 unit tests covering the deterministic helpers and path-traversal defenses
- GitHub Actions CI workflow (`ruff` + `mypy` + `pytest`, label-gated synthetic eval smoke)
- `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, GitHub issue and PR templates
- `.claude-plugin/` scaffold: `plugin.json` manifest, three migrated plan-mode hooks, five new deterministic hooks (`block-secrets`, `ruff-changed`, `block-merge-to-main`, `validate-context`, `route-security-lint`)
- Three project subagents: `eval-judge` (Haiku, grading), `prompt-archaeologist` (Sonnet, prompt-failure diagnosis), `git-flow` (Sonnet, conventional-commit workflow)
- Five project skills: `/eval`, `/replay`, `/prompt-tune`, `/bench`, `/inspect-context`
- Eval harness under `evals/`: `runner.py`, four rubrics (grounding, keyword_coverage, ats_format, tone), three synthetic fixtures (sre-mid-level, pm-senior, data-scientist-junior), JSON Schema for `context_set`
- LLM telemetry: `analyzer.py` emits one JSONL record per call to `logs/llm_calls.jsonl` with timestamps, tokens (including `cache_creation_input_tokens` / `cache_read_input_tokens`), latency, prompt version, status
- Prompt caching: stable user-message prefix (resume + JD + supplementals + candidate profile) sent as a cacheable text block per call. Verified live: ~4,300 cached input tokens read on every generate call within the 5-minute TTL, ~37% input-token cost reduction across an analyze + generate + refinement-generate sequence
- Template-faithful docx output: `generator._write_docx` now walks the original resume's first ~30 paragraphs and captures formatting prototypes per role (name, subtitle, contact, section_heading, job_title, job_subtitle, body), then applies them to the matching markdown elements. Right-aligned date column on `### ` lines is preserved via the captured tab stop. Required for templates that use direct paragraph formatting rather than Word named styles.
- Dashboard blueprint at `/_dashboard` reading the JSONL telemetry and eval results into two filterable tables; localhost-only
- `PROMPT_VERSION` constant in `analyzer.py`; bumped on any `SYSTEM_PROMPT` change so eval results trace to a specific revision
- Project allowlist in `.claude/settings.json` for the `ruff`/`mypy`/`pytest`/`pip show` dev loop

### Changed
- `app.py` Flask debug flag is now env-driven (`FLASK_DEBUG`, default-on for dev). Set `FLASK_DEBUG=0` to disable for any future hosted deployment.
- Type annotations cleaned up across `analyzer.py`, `generator.py`, and `parser.py` to satisfy `mypy --strict-optional`.
- `CLAUDE.md` is now project-shared (committed) — was machine-local. Per-clone overrides moved to `CLAUDE.local.md` (gitignored).
- `.claude/launch.json` removed from tracking (had a hardcoded Windows path); kept locally and gitignored.
- `.gitignore` rewritten for `.claude/*` allow-list pattern: future Claude Code internals (worktrees, caches) auto-ignored; only `settings.json` is tracked.
- README install commands now use `pip install -e .` instead of `pip install -r requirements.txt`.
- README gains a "Claude Code Plugin" discovery section listing all commands, agents, and hooks.
- Hook wiring lives in `.claude/settings.json` rather than the plugin manifest, since Claude Code v2.1.131 in VSCode doesn't support `/plugin install` for local paths. The `.claude-plugin/` layout is preserved for future marketplace publication.
- `analyzer.py:MODEL` upgraded from `claude-sonnet-4-20250514` (May 2025 Sonnet 4) to `claude-sonnet-4-6`. Same per-token price; better structured-output adherence and instruction-following on the long generate prompt. Rationale comment added near the constant documenting the model-selection trade-offs (Sonnet for analyze/generate, Haiku for high-volume structured grading, no Opus for cost reasons). `PROMPT_VERSION` bumped to `2026-05-06.5` so telemetry distinguishes pre-/post-bump runs.
- `analyzer.py:MAX_TOKENS` raised from 4096 to 8192. Sonnet 4.6's analyze() output is more verbose than older Sonnet 4 was on detail-rich real inputs and was hitting the 4096 cap mid-JSON, surfacing as a downstream "non-JSON response" error. 8192 leaves headroom; the model still uses what it needs.

### Removed
- `requirements.txt` (superseded by `pyproject.toml`)

### Fixed
- `generate()` prompt now requires explicit `# / ## / ### / -` markdown markers on resume_content output. Without these markers the document writer fell back to undifferentiated plain paragraphs, losing template heading visual styles. Prompt was unchanged across the v0.1.x line; making the marker requirement loud is the fix.
- `_write_docx` no longer materializes empty markdown lines as empty paragraphs. The resulting double-gap between `## SECTION` headings and their body content was visible in every multi-section docx output. Templates' per-paragraph `space_after` provides the visual rhythm; empty paragraphs were stacking on top of it.
- `_call_llm` now logs a warning and records a `stop_reason` field in `logs/llm_calls.jsonl` whenever the model hits `max_tokens`. Previously a truncated JSON response surfaced as a confusing parse error in the UI; now truncations are visible directly in the telemetry stream.

### Known issues
- Junior-level fixtures (e.g., `evals/fixtures/synthetic/data-scientist-junior`) can score below the grounding rubric's pass threshold of 4 due to the model inflating an analyst's actual scope to match a more senior JD (slugs: `scope_inflation`, `verb_overreach`, `invented_metric`). Pre-existing across the v0.1.x line — surfaced for the first time by the new eval harness. To be addressed via prompt tightening in v0.2.1; the `prompt-archaeologist` subagent is the intended workflow.

---

## [0.1.0] — 2026-05-06

Initial public release.

### Added
- Two-call LLM pipeline (`analyze()` + `generate()`) producing tailored resume + cover letter from a job description
- Refinement scope validation via Haiku classifier
- Streaming LLM calls for warm-connection long-running generations
- Multi-resume source pool with primary/supplemental selection in the UI
- Full candidate profile injection into both LLM calls (skills, certifications, education, notes, scraped LinkedIn/portfolio content)
- Deterministic hardening layer: keyword extraction, ATS format checks, keyword overlap scoring, context-set assembly
- Resume parsing for `.docx`, `.pdf`, `.md` with section inference
- Document generation preserving the original `.docx` as a style template
- Two human-gated review checkpoints (analysis review, output review) per the P8 Strategic Human Gate principle
- LCARS-styled single-page UI
- MIT license, comprehensive `.gitignore`, `SECURITY.md`, `README.md`, `vision.md`
