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

**Two-call LLM pipeline** (all in [analyzer.py](analyzer.py)):
- Call 1: `analyze()` — JD breakdown, ideal resume, comparison, keyword strategy
- Call 2: `generate()` — tailored resume + cover letter + proofread pass

**Core design rules:**
- **P1 Hardening** — deterministic Python for mechanical work; LLM only for fuzzy reasoning
- **P8 Human Gates** — two explicit user review checkpoints before any output is produced
- **P5 Institutional Memory** — ALWAYS/NEVER BECAUSE rules in `analyzer.py:SYSTEM_PROMPT`
- **P2 Context Hygiene** — `context_set` is the structured JSON contract between all stages

**Multi-resume source pool:**
- Primary resume → `context_set["resume"]` (determines output format + style template)
- Included supplementals → `context_set["supplemental_resumes"]` (fed to both LLM calls)
- User controls inclusion via the two-zone chip UI; state persists to `configs/{user}.config`

**`context_set` lifecycle:**
```
/api/analyze  → build_context_set() → analyze() → save to output/{user}/context_*.json
/api/generate → load context JSON  → generate() → write docx/md files
```

---

## File Map

```
app.py              Flask routes + security helpers (_safe_username, _within)
analyzer.py         LLM calls: analyze(), generate(), _supplemental_block(), SYSTEM_PROMPT
hardening.py        Deterministic tools: keyword extraction, ATS checks, build_context_set()
generator.py        Document output: _write_docx() uses original .docx as style template
parser.py           Resume parsing (docx/pdf/md → structured dict)
scraper.py          LinkedIn/portfolio URL scraping (best-effort, fails gracefully)
static/app.js       All frontend logic — vanilla JS, fetch API, no framework
static/style.css    LCARS aesthetic: dark bg, amber/teal/orange/blue palette
templates/index.html Single-page app shell

tests/              Unit tests (pytest)
evals/              LLM eval harness with synthetic + real fixtures
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
- System prompt lives at `analyzer.py:SYSTEM_PROMPT` — edit there, not inline
- When `SYSTEM_PROMPT` changes, bump `PROMPT_VERSION` in the same commit so observability/eval can attribute behavior
- Supplemental resumes injected via `_supplemental_block()` in both prompts
- Grounding check in generation prompt enforces no invented facts

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
python evals/runner.py --suite synthetic --subset smoke
```

---

## What NOT to Do

- Do not call `docx.Document()` without a template — output won't match the original's style
- Do not invent numbers, titles, or dates in LLM output — grounding check is the enforcement
- Do not skip `_safe_username()` / `_within()` on any new route touching the filesystem
- Do not commit real personal data: `evals/fixtures/real/`, `configs/*.config` (except `example.config`), `resumes/`, `output/`
- Do not add features or refactor beyond what was asked — minimal targeted edits only
- Do not call an LLM from `hardening.py`, `parser.py`, `scraper.py`, or `generator.py` — those are deterministic by design
- Do not introduce a new dependency without adding it to `pyproject.toml` AND updating `CHANGELOG.md`
