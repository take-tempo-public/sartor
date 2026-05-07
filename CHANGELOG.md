# Changelog

All notable changes to Resume Optimizer are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
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

### Removed
- `requirements.txt` (superseded by `pyproject.toml`)

### Fixed
- `generate()` prompt now requires explicit `# / ## / ### / -` markdown markers on resume_content output. Without these markers the document writer fell back to undifferentiated plain paragraphs, losing template heading visual styles. Prompt was unchanged across the v0.1.x line; making the marker requirement loud is the fix.
- `_write_docx` no longer materializes empty markdown lines as empty paragraphs. The resulting double-gap between `## SECTION` headings and their body content was visible in every multi-section docx output. Templates' per-paragraph `space_after` provides the visual rhythm; empty paragraphs were stacking on top of it.

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
