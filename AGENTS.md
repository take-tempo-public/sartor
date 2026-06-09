# callback. — AI agent contract

> **Purpose:** the universal contract that any AI coding agent (Claude
> Code, Cursor, Codex, Continue, Aider, etc.) reads before making
> non-trivial changes to this codebase. Pointers to deeper docs, key
> code patterns, branch / commit conventions, security guardrails,
> what NOT to do.
> **Audience:** AI coding agents AND humans who want the same
> at-a-glance rules. This is the *canonical* tool-agnostic version;
> tool-specific overrides live in companion files like `CLAUDE.md`.
> **Authoritative for:** branch / commit conventions; the
> `_safe_username` / `_within` security gate; the `ruff` + `mypy` +
> `pytest` minimum-bar; `PROMPT_VERSION` discipline; what kinds of
> changes are NOT welcome. Sibling docs:
> [`vision.md`](vision.md) (product intent),
> [`docs/architecture.md`](docs/architecture.md) (system + modules),
> [`docs/PRODUCT_SHAPE.md`](docs/PRODUCT_SHAPE.md) (v1 → v2 ladder).

---

## Read these first

- [docs/architecture.md](docs/architecture.md) — system overview, module map, four Mermaid diagrams (pipeline / persistence / data-flow / llm-routing). Start here for a fast tour.
- [vision.md](vision.md) — product intent, self-imposed constraints, learnings + direction.
- [docs/PRODUCT_SHAPE.md](docs/PRODUCT_SHAPE.md) — unified Corpus Item pattern; v1.0 → v2 sequencing ladder; deferred items.
- [SECURITY.md](SECURITY.md) — threat model, API key rules, accepted risks.
- [CONTRIBUTING.md](CONTRIBUTING.md) — branch + commit conventions, dev loop.
- [README.md](README.md) — user-facing overview.

The project follows the [10 Principles framework](https://jdforsythe.github.io/10-principles/overview/). The codebase is annotated with principle references (P1, P2, P5, P6, P8, P9) — they are load-bearing, not decoration.

---

## Architecture at a glance

Full system + module map in [`docs/architecture.md`](docs/architecture.md). Quick orientation:

- **All LLM calls live in `analyzer.py`.** Sonnet 4.6 for heavy reasoning (`analyze`, `clarify`, `iterate_clarify`, `generate`, `generate_cover_letter`); Haiku 4.5 for structured selection (`recommend`, `recommend_summary`, `critique_proposal`, `extract_experiences`).
- **`hardening.py`, `parser.py`, `generator.py`, `scraper.py`, `json_resume.py`, `corpus_to_json_resume.py`, `pdf_render.py` are deterministic** — no LLM calls allowed. The P1 Hardening boundary.
- **`context_set` is the JSON contract** between every pipeline stage. Each `/api/generate` writes a NEW timestamped child file via `hardening.save_iteration_context()`; the `parent_context_path` chain is the iteration audit trail.
- **`PROMPT_VERSION` in `analyzer.py`** must bump in the SAME commit when any prompt changes, so eval telemetry attributes scores correctly.

For the full pipeline sequence (with all eight LLM call kinds, which Flask route fires each, and cost/latency footprints), see [`docs/diagrams/pipeline.mmd`](docs/diagrams/pipeline.mmd) and [`docs/diagrams/llm-routing.mmd`](docs/diagrams/llm-routing.mmd).

---

## Key patterns — always follow these

### Security (every Flask route that touches the filesystem)

```python
safe_user = _safe_username(username)          # sanitize + confirm user exists
safe_file = secure_filename(filename)         # strip traversal sequences
if not _within(path, PARENT_DIR): abort(403)  # resolved-path containment check
```

A `route-security-lint` hook enforces this on `app.py` edits — see [`.claude-plugin/hooks/`](.claude-plugin/hooks/).

### Branch before code changes

A `require-feature-branch` PreToolUse hook blocks `Edit`/`Write` while on `main`/`master`. Create a feature branch when moving from plan to execute (`git checkout -b <type>/<short-desc>`). Intentional main edits: `export CLAUDE_ALLOW_MAIN_EDITS=1`.

**Branch close-out checklist (closing agent, in order):**
0. **Pre-close sweep — run this BEFORE the gate, ON THE BRANCH (never post-merge).** Enumerate the COMPLETE set of close-out obligations and resolve each (or explicitly defer *with the user*) so the session closes **once**, not three times:
   - working changes staged + internally consistent (no dangling refs / links);
   - **memory learnings** from the session written now — doing memory or cleanup *after* the merge (on `main`) gets blocked by `require-feature-branch` + the merge-wiped `~/.claude/plans/.approved` marker, forcing a repeat flag-clear-and-ceremony that steps on the next branch's work; the cheap window is here, pre-merge;
   - every **loose end flagged this session** resolved or explicitly deferred;
   - **branches to prune** identified.
   "Done" is the *output* of this sweep, not a declaration — do not announce completion until it is empty. Declaring progress over verifying completeness manufactures tech debt, repeat close-outs, and eroded trust.
1. Quality gate green (`python -m ruff check .` + `python -m mypy .` + `python -m pytest`).
2. Commit — message records what was done and why (or "no code change — verified" if the branch closed clean).
3. Ask user to confirm merge to `main`; execute merge after confirmation.
4. Prune the merged branch(es) with the user's OK, then generate the next-agent handoff prompt using [`docs/dev/AGENT_HANDOFF_TEMPLATE.md`](docs/dev/AGENT_HANDOFF_TEMPLATE.md) **as copyable chat text (never a file written into `output/`)** and give it to the user as the **last act** before closing the window.

### Document generation

- Always pass `template_path` (original `.docx`) to `generate_resume()` when output is docx.
- `_write_docx()` opens the original as a style template — never call `docx.Document()` on blank.
- `BULLET_RE` in `generator.py` normalizes all bullet variants.

### LLM prompts

- The hiring-manager persona lives at `analyzer.py:SYSTEM_PROMPT`; analyze-time interview persona at `analyzer.py:CLARIFY_SYSTEM_PROMPT`; iteration-time persona at `analyzer.py:CLARIFY_ITERATION_SYSTEM_PROMPT`. Edit there, not inline.
- When any prompt changes (or any per-call prompt template), bump `PROMPT_VERSION` in the same commit so observability/eval can attribute behavior.
- Supplemental resumes injected via `_supplemental_block(iteration)` — wrapper switches to `<historical_resumes>` (with the original primary folded in) when iteration ≥ 1.
- Grounding check in generation prompt enforces no invented facts; the worked-examples block (OK / NOT OK pairs) is the load-bearing teaching signal — when adding new failure modes to the SYSTEM_PROMPT, also add a worked example.
- When clarifications OR first-person preview edits are present, the grounding check widens to accept them as legitimate source material. The no-invention rule still applies beyond the union of (resume + clarifications + typed edits) — keep this carve-out surgical, not blanket.
- `_call_llm` and `_parse_or_retry` accept an optional `system_prompt` arg; calls that override it (like `clarify` / `clarify_iteration`) pay one extra cache-miss on the system block but the heavy user-prefix cache is unaffected.

### Eval observability

- Eval results carry `prompt_version` so the dashboard's score-over-time chart can attribute regressions to specific prompt revisions.
- Deterministic post-generation metrics (`verb_diversity`, `specificity_density`, `grounding_overlap`, `cost_usd`) ride along on every result. `grounding_overlap.missing_samples` is the actionable fabrication signal.
- Document tuning iterations in `evals/TUNING_LOG.md` (what changed, why, scores before/after, lessons). This is the institutional-memory artifact for future tuners.
- **Prompt-override primitive** (`analyzer.prompt_overrides()` + `evals/runner.py --prompt-overrides`): A/B a candidate system prompt **without editing the persona constants**. Inside the context manager every LLM call sends the candidate prompt and stamps `prompt_version=candidate:<hash>` (telemetry + eval records), so candidate runs are quarantined from score-over-time. The default (no-override) path is byte-identical — the resolver returns the identical constant object and the logged version stays `PROMPT_VERSION`, so the analyze→generate cache is untouched. Override scope is the named system-prompt constants only (the `_BASE_SYSTEM_PROMPTS` registry), not the dynamic user-prompt builders. `/prompt-tune` and the v1.0.4 tuning loop build on this.

### Frontend config persistence

- `_savePrimaryResume(filename)` — persists `latest_resume` to config on chip click.
- `_saveIncludedResumes()` — persists `included_resumes[]` on badge toggle.
- `saveConfig()` spreads `included_resumes` and `portfolio_urls` to survive panel saves.

---

## Testing and validation

Every change should pass the local validator loop before commit:

```bash
ruff check .
mypy .
pytest
```

The Playwright **UX** tier (`pytest -m ux`) drives the wizard in a headless Chromium against a threaded live server (LLM-free — analyzer functions are stubbed, the real routes run). It skips when the Chromium binary is absent (`python -m playwright install chromium`), so the default `pytest` stays green everywhere. The shared navigation/selector driver lives in [`ui_pages/`](ui_pages/) — one registry, consumed by the suite **and** `scripts/capture_screenshots.py`.

CI runs the same on PR. Eval harness (Anthropic API costs apply) runs locally and on label-gated CI:

```bash
python evals/runner.py --suite synthetic --subset smoke   # ~$0.10, grounding only
python evals/runner.py --suite synthetic                  # ~$1.50, all 4 rubrics × 3 fixtures
```

Dashboard for trends + heatmap + failure-mode clustering: visit `http://localhost:5000/_dashboard` while `python app.py` is running locally. Only reachable via `localhost`/`127.0.0.1` (host-header guard).

---

## What NOT to do

- Do not call `docx.Document()` without a template — output won't match the original's style.
- Do not invent numbers, titles, or dates in LLM output — grounding check is the enforcement.
- Do not skip `_safe_username()` / `_within()` on any new route touching the filesystem.
- Do not commit real personal data: `evals/fixtures/real/`, `configs/*.config` (except `example.config`), `resumes/`, `output/`.
- Do not add features or refactor beyond what was asked — minimal targeted edits only.
- Do not call an LLM from `hardening.py`, `parser.py`, `scraper.py`, `generator.py`, `pdf_render.py`, `json_resume.py`, or `corpus_to_json_resume.py` — those are deterministic by design.
- Do not introduce a new dependency without adding it to `pyproject.toml` AND updating `CHANGELOG.md`.
- Do not bypass the `route-security-lint`, `require-feature-branch`, or `ruff-changed` PreToolUse hooks without explicit authorization documented in the commit message.
