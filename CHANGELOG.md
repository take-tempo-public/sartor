# Changelog

All notable changes to Resume Optimizer are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added — Optional Clarification Interview Between Analyze and Generate (2026-05-11)
- **`clarify()` in `analyzer.py`** — third LLM call (optional, between `analyze()` and `generate()`) that produces 3-5 targeted questions: experience probes surfacing JD-required skills missing or weak in the resume, and scope probes disambiguating ambiguity flagged by the analyzer. Uses a dedicated short `CLARIFY_SYSTEM_PROMPT` rather than the hiring-manager `SYSTEM_PROMPT` — narrower task, tighter grounding, cheaper tokens. Reuses `_parse_or_retry` for telemetry parity; emits `call: "clarify"` in `logs/llm_calls.jsonl`.
- **`POST /api/clarify` and `POST /api/answer-clarifications`** in `app.py`, between the existing `/api/analyze` and `/api/generate`. Both routes use the standard `_safe_username` + `_within(OUTPUT_DIR)` security guards. Questions and answers persist back to the same `context_*.json` file (no new timestamped files) so the UI is refresh-safe and `/api/generate` picks up clarifications by simply reloading the existing context. `run_id` propagates from analyze through clarify to generate so all three calls share a correlation key.
- **`generate()` injects `<candidate_clarifications>` block** when `context_set["clarifications"]` is non-empty. The grounding check widens to accept clarification answers as first-person ground truth — citable in the resume even when not present in the source — but the no-invention rule still applies beyond the union of (resume + clarifications).
- **`ContextSet` TypedDict gained two optional fields** in `hardening.py`: `clarification_questions: list[ClarificationQuestion]` and `clarifications: dict[str, str]`. Both `total=False` so pre-clarify saved contexts continue to round-trip without errors. New regression test in `test_hardening.py::TestContextSetClarificationFields` proves both directions.
- **Frontend "Clarifying Interview" panel** inside the existing Analysis panel: `templates/index.html` adds a collapsible section with `GET CLARIFYING QUESTIONS` / `SUBMIT ANSWERS & GENERATE` / `SKIP` controls. `static/app.js` adds `runClarify()`, `submitClarificationsAndGenerate()`, `skipClarifications()`, and a `_renderClarifyQuestions()` helper that uses safe DOM construction (`textContent`, `appendChild`) for all LLM-supplied strings — defense-in-depth on top of `esc()`. `static/style.css` adds the violet-accented divider and question-card styles, with amber `SCOPE` badges to visually distinguish scope from experience probes.
- **`evals/rubrics/clarification_quality.md`** — new rubric grading question composition (3-5 total, ≥50% experience probes), gap citation specificity (must cite a concrete source from `essential_skills`, `comparison.gaps`, `keyword_placement`, or `keyword_overlap.missing_from_resume`), word limit (≤25 per question), no compound or leading questions, and theme coverage against the new `expected_clarification_themes` field on each fixture.
- **`evals/runner.py` runs `clarify()` between analyze and generate** on every fixture; if clarify fails, the runner logs a warning, emits a `pipeline_error` row for `clarification_quality`, and continues with the existing four rubrics ungated. The clarification questions are added to every per-rubric payload (other rubrics ignore them).
- **`evals/fixtures/synthetic/{data-scientist-junior,pm-senior,sre-mid-level}/expected.json`** each gained `expected_clarification_themes` with `experience_probes` and `scope_probes` lists tailored to the fixture's real gaps, plus `min_clarification_quality_score: 4`.
- **`_call_llm` and `_parse_or_retry` gained an optional `system_prompt` arg** so narrowly-scoped calls like `clarify` can override the hiring-manager persona without code duplication. Default behavior unchanged; the existing `analyze()` and `generate()` calls keep using `SYSTEM_PROMPT` and continue to hit the system-block prompt cache.
- **`PROMPT_VERSION` 2026-05-09.3 → 2026-05-11.1** because new system prompt, new prompt template (clarify), and the generate prompt grew the `<candidate_clarifications>` injection point.
- **New tests**: `tests/test_app_clarify.py` (route handlers, security guards, persistence, idempotency, ID filtering); `tests/test_analyzer.py` expanded with `clarify()` happy-path, retry, `system_prompt` threading, and generate's three injection paths (present, absent, all-skipped); `tests/test_hardening.py` round-trip regression for ContextSet with and without the new fields. All 129 tests pass.

### Added — Response Validation & Typed Context (2026-05-09 follow-up)
- **`_parse_or_retry` helper in `analyzer.py`** replacing the silent `{"raw_response": raw, "parse_error": True}` fallback in `analyze()` and `generate()`. The helper strips markdown fences, runs `json.loads`, and checks the response against a per-call `frozenset` of required keys (`ANALYZE_REQUIRED_KEYS`, `GENERATE_REQUIRED_KEYS`). On `JSONDecodeError` or missing keys, it re-prompts via `_call_llm` with a `<retry_reason>` block appended (`call_kind="<kind>_retry"`) — the cached user prefix is byte-identical so the retry hits prompt cache and adds ~1 cached read instead of full input tokens. After `max_attempts=2` failures it raises `LLMResponseError(raw, validation_error)` rather than degrading silently.
- **`LLMResponseError` exception** carrying the raw response and validation error. Handled in `app.py` at both LLM call sites — returns HTTP 502 with a user-readable message and the validation detail. The eval runner's existing `except Exception` block catches it and records `pipeline_error` unchanged.
- **`ContextSet` `TypedDict` and four nested TypedDicts (`CandidateInfo`, `ResumeInfo`, `SupplementalResume`, `DeterministicAnalysisBlock`)** in `hardening.py`. `build_context_set` now returns `ContextSet`; `analyze`, `generate`, `_stable_user_prefix`, `_supplemental_block`, `save_context_set`, and the `context_set` locals in `app.py` and `evals/runner.py` are all annotated. mypy now catches field-name typos at access sites instead of letting them surface as runtime `KeyError`s. No new runtime dependency — pure stdlib `typing.TypedDict`. The two app-added keys (`llm_analysis`, `run_id`) are expressed via a `total=False` subclass rather than `typing.NotRequired` to keep Python 3.10 compatibility (`NotRequired` is 3.11+).
- **12 new unit tests** in `tests/test_analyzer.py` covering `_strip_fences` across five fence patterns and `_parse_or_retry` happy path, fence-stripped happy path, missing-key recovery, invalid-JSON recovery, missing-key exhaustion, invalid-JSON exhaustion, and `_retry` call_kind attribution. Mocks `analyzer._call_llm` directly — no Anthropic SDK in the test path.
- **`PROMPT_VERSION` 2026-05-09.2 → 2026-05-09.3** because retry attempts now carry a `<retry_reason>` block in the per-call user prompt, and JSONL telemetry uses `prompt_version` for attribution.
- **`_strip_fences` consolidates** the previously-duplicated fence-stripping logic that lived in both `analyze()` and `generate()`. Net deletion of ~16 lines. Uses a single regex (`^```(?:[a-zA-Z]+)?\s*\n?(.*?)\n?\s*```$`) that handles multiline and single-line fenced blocks with or without a language tag.

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
