# Architecture — callback.

> **Purpose:** developer-facing architecture overview. The system
> diagram, the module map, the DB schema, and the LLM routing table.
> One page that a new contributor (human or LLM) can read in 5
> minutes and then navigate the codebase confidently.
> **Audience:** humans contributing PRs; LLM agents (Claude Code,
> sub-agents) onboarding to the repo.
> **Authoritative for:** the canonical pipeline shape, the on-disk
> data flow, the model assignment per LLM call, the DB ER model.
> When the code changes shape, this doc + the four diagrams in
> [`docs/diagrams/`](diagrams/) must change with it.
> Sibling docs:
> [`CLAUDE.md`](../CLAUDE.md) (contributor contract),
> [`docs/PRODUCT_SHAPE.md`](PRODUCT_SHAPE.md) (product intent),
> [`docs/PERF_ANALYZE.md`](PERF_ANALYZE.md) (analyze latency audit),
> [`vision.md`](../vision.md) (LLM persona rules).

---

## System overview

callback. is a local-first Flask app that tailors résumés and
optional cover letters to specific job descriptions. The
pipeline is **two-or-more LLM calls in sequence**, each gated by
a human review or curation step:

1. **Analyze** (Sonnet) — JD breakdown, ATS-keyword strategy,
   ideal-résumé synthesis
2. **Clarify** *(optional, Sonnet)* — surfaces real-but-undocumented
   candidate experience
3. **Recommend** (Haiku) — selects best bullets + summary variants
   for the JD; runs in parallel
4. **Generate** (Sonnet) — produces the tailored résumé markdown,
   honoring user curation
5. **Iterate** *(optional, repeatable)* — clarify-iteration + new
   generate per round; child context files chain via `parent_context_path`
6. **Generate cover letter** *(optional, Sonnet)* — against the
   finalized résumé, with the same refine/iterate affordances

Full sequence diagram: [`docs/diagrams/pipeline.mmd`](diagrams/pipeline.mmd).

### The four canonical diagrams

| Diagram | Source | Purpose |
|---|---|---|
| [Pipeline](diagrams/pipeline.mmd) | `analyzer.py` + `app.py` route map | One full apply-run, sequence-diagram view |
| [Persistence](diagrams/persistence.mmd) | `db/models.py` | DB tables + FK relationships + cascade behavior |
| [Data flow](diagrams/data-flow.mmd) | `hardening.py` + route handlers | `context_set` lifecycle across iterations |
| [LLM routing](diagrams/llm-routing.mmd) | `analyzer.py` `_call_llm` sites + `PERF_ANALYZE.md` | Which route fires which model, with cost / latency |

All four render natively on GitHub when committed in a fenced
`mermaid` block, and parse cleanly by every modern LLM. Use a
local Mermaid live editor (`mermaid.live`) to preview changes
before commit.

---

## Module map

Each top-level Python file at the project root has one stated
purpose. Code that belongs elsewhere goes elsewhere.

| File | Purpose | Key public surface | What NOT to put here |
|---|---|---|---|
| [`app.py`](../app.py) | Flask routes, security helpers, request/response glue | `app.route(...)` handlers, `_safe_username`, `_within`, `inject_static_version` | LLM calls, model definitions, parsing logic |
| [`analyzer.py`](../analyzer.py) | All LLM calls; system prompts; response parsing | `analyze()`, `clarify()`, `clarify_iteration()`, `recommend_bullets()`, `recommend_summaries()`, `generate()`, `generate_cover_letter_against_resume()`, `_parse_or_retry()`, `SYSTEM_PROMPT` family | Filesystem I/O, route handling, schema definitions |
| [`hardening.py`](../hardening.py) | Deterministic Python: keyword extraction, ATS checks, context-set lifecycle, post-generation metrics | `build_context_set()`, `save_iteration_context()`, `summarize_recent_edits()`, `compute_iteration_signals()`, `ContextSet` TypedDict, verb-diversity / specificity / grounding scorers | LLM calls (P1 hardening boundary) |
| [`generator.py`](../generator.py) | Document output: .md / .docx / .pdf | `generate_resume(content, output_format, ...)`, `_write_docx()`, `_render_pdf_from_json()`, `BULLET_RE` normalizer | LLM calls, parsing of LLM responses |
| [`parser.py`](../parser.py) | Résumé file parsing (.docx / .pdf / .md → structured dict) | `parse_resume()`, format-specific helpers | LLM calls, document generation |
| [`pdf_render.py`](../pdf_render.py) | Jinja2 + Playwright PDF and live-preview render | `render_pdf()`, `render_html_string()`, `html_template_path_for()` | LLM calls, route handling |
| [`json_resume.py`](../json_resume.py) | JSON Resume v1.0 normalizer for markdown → structured | `md_to_json_resume()`, `SCHEMA_URI` | LLM calls, generation |
| [`corpus_to_json_resume.py`](../corpus_to_json_resume.py) | Build JSON Resume doc directly from corpus DB rows + composition overrides | `build_json_resume_from_corpus()` | LLM calls, route handling |
| [`scraper.py`](../scraper.py) | LinkedIn / portfolio URL fetch (best-effort) | `scrape_url()` | LLM calls, processing |
| [`db/models.py`](../db/models.py) | SQLAlchemy 2.0 ORM models — see persistence diagram | `Candidate`, `Experience`, `Bullet`, `SummaryItem`, `Application`, `ApplicationRun`, etc. | Route handlers, business logic |
| [`db/session.py`](../db/session.py) | SQLAlchemy engine + session factory; Alembic migration runner | `init_db()`, `get_session()` | Business logic |
| [`db/build_context.py`](../db/build_context.py) | DB-backed `build_context_set` variant; bullet scorer | `score_corpus_bullet()`, `_bullet_tag_values()` | Route handlers |
| [`dashboard/`](../dashboard/) | Read-only Flask blueprint at `/_dashboard` for eval results, cost cards, failure-mode heatmap | `dashboard_bp` | LLM calls, mutation |
| [`evals/runner.py`](../evals/runner.py) | LLM eval harness — synthetic + real fixtures, 0.0-5.0 rubric scoring | `run_suite()`, `_load_baseline_scores()` | Production paths |

**Code that crosses modules.** When a route in `app.py` needs to
call the LLM, it imports the analyzer function. When the analyzer
needs deterministic processing, it imports from `hardening.py`.
**These directions never reverse** — `hardening.py` does not
import `analyzer.py`; `analyzer.py` does not import `app.py`.

---

## Persistence model

The DB schema is in [`docs/diagrams/persistence.mmd`](diagrams/persistence.mmd).
Highlights:

- **Candidate** is the root of nearly every other table. One row
  per user; identity columns + the legacy `profile_text` (kept
  for back-compat with pre-`SummaryItem` data).
- **Experience → ExperienceTitle / Bullet** is the corpus
  backbone. Bullets are the only fully-Corpus-Item type
  ([`docs/PRODUCT_SHAPE.md §3`](PRODUCT_SHAPE.md) for the
  asymmetry matrix); SummaryItem extends the same pattern.
- **Tag** is shared across bullets, titles, summary items, and
  persona templates via junction tables — one taxonomy, multiple
  consumers.
- **Application → ApplicationRun** captures every iteration of
  every apply-run. `ApplicationRun.parent_run_id` forms the
  iteration audit trail (self-referential, ON DELETE SET NULL).
- **ApplicationBullet** is the audit row: which bullets ended up
  in which run's output, at what position. Bullets are NEVER
  cascade-deleted (soft-retire only) to preserve audit integrity.

---

## LLM routing + cost

Full picture: [`docs/diagrams/llm-routing.mmd`](diagrams/llm-routing.mmd).
Latency data from real production usage in
[`docs/PERF_ANALYZE.md`](PERF_ANALYZE.md).

**Sonnet 4.6** (`claude-sonnet-4-6`) handles heavy reasoning:
`analyze`, `clarify`, `iterate_clarify`, `generate`,
`generate_cover_letter`. These calls produce large JSON
responses; `analyze` is the slowest call on the critical path
(p50 ~90 s).

**Haiku 4.5** (`claude-haiku-4-5-20251001`) handles structured
selection / classification: `recommend` (bullets),
`recommend_summary`, `critique_proposal`,
`promote_clarification_to_bullet`, `extract_experiences`.
~5-second median, ~$0.002 per call.

**Cache prefix.** `analyze` and `generate` share a heavy
cached user prefix (corpus + résumé blocks). The clarify
variants (`clarify`, `clarify_iteration`) override the system
prompt and pay one cache-miss on the system block, but the
heavy user prefix is unaffected.

**Retry attribution.** Every call_kind has a sibling
`<kind>_retry` for dashboard breakdowns. Implementation in
[`analyzer.py`](../analyzer.py) `_parse_or_retry()`.

---

## context_set lifecycle

The `context_set` JSON file is the contract between every stage.
Full data-flow diagram: [`docs/diagrams/data-flow.mmd`](diagrams/data-flow.mmd).

Key invariants:

- **One file per iteration.** `/api/generate` writes a NEW child
  file via `save_iteration_context()`; the `parent_context_path`
  chain is the audit trail. The parent is never mutated.
- **Containment guard.** Every route that reads/writes a context
  file checks `_within(path, OUTPUT_DIR)`. Path traversal is
  CVE-class — see [`SECURITY.md`](../SECURITY.md).
- **Resumability.** Clarify questions and answers ride along on
  the same file; users can quit and resume mid-application.
- **Run ID propagation.** The same 12-hex `run_id` (minted in
  `/api/analyze`) propagates through every LLM call so
  `logs/llm_calls.jsonl` correlates the entire session.

---

## Output formats

| Format | Pipeline | Template type | When to use |
|---|---|---|---|
| **`.md`** | `_normalize_markdown()` → write | None | Quick paste; ATS submissions that accept markdown |
| **`.docx`** | `_normalize_markdown()` → `_write_docx()` with persona `.docx` as style template | `personas/bundled/<name>.docx` | Word-based ATS portals; recruiter inbox |
| **`.pdf`** | `_normalize_markdown()` → `md_to_json_resume()` → Jinja2 `.html` → Playwright Chromium → PDF | `personas/bundled/<name>.html` + `.css` | Direct apply forms; user portfolios |

Every output also writes a sidecar
`resume_TS.jsonresume.json` (canonical JSON Resume v1.0
intermediate) for downstream tooling and re-render. Best-effort
write; failures don't block the primary output.

---

## Security model

Single-tenant local-first; the server binds to `127.0.0.1:5000`
only. Full threat model in [`SECURITY.md`](../SECURITY.md).

Two helpers every route that touches the filesystem must use:

- **`_safe_username(username) -> str | None`** — strips path
  traversal via `secure_filename`; verifies the user's
  `configs/<user>.config` actually exists. Returns `None` for
  invalid / unknown users.
- **`_within(path, parent) -> bool`** — resolves the input path
  and confirms it's a child of `parent`. Always called on
  paths sourced from request data.

The `route-security-lint` hook in `.claude-plugin/hooks/` blocks
`Edit`/`Write` on `app.py` that defines a new route handler
without these guards. Don't bypass it.

---

## Test discipline

`ruff`, `mypy`, `pytest` are the minimum bar. All three must
pass before any commit lands. The eval harness
(`python evals/runner.py --suite synthetic`) is label-gated CI
because it costs ~$1.50 per full run.

When a prompt changes, bump `PROMPT_VERSION` in the same commit
so the eval dashboard can attribute score changes correctly.
The version string lives in [`analyzer.py`](../analyzer.py).

---

## Where to go next

- **Adding a new LLM call?** Mirror the pattern in `analyzer.py`:
  add a `RECOMMEND_X_SYSTEM_PROMPT`, an `X` function, a
  `recommend_x` route, an eval rubric. See `recommend_summaries`
  as the latest example.
- **Adding a new corpus item type?** Mirror `SummaryItem`: model
  + migration + CRUD routes + recommend call + Compose UI
  surface. See [`PRODUCT_SHAPE.md §3`](PRODUCT_SHAPE.md) for
  the unifying pattern.
- **Adding a new output format?** Add a branch to
  `generator.generate_resume()` and a renderer module. The
  JSON Resume intermediate already exists; reuse it.
- **Debugging a slow call?** Start with
  [`docs/PERF_ANALYZE.md`](PERF_ANALYZE.md); reproduce the
  audit query against your own `logs/llm_calls.jsonl`.
