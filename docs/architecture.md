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
> [`docs/dev/perf/PERF_ANALYZE.md`](dev/perf/PERF_ANALYZE.md) (analyze latency audit),
> [`vision.md`](../vision.md) (LLM persona rules).

---

## System overview

callback. is a local-first Flask app that tailors résumés and
optional cover letters to specific job descriptions. The
pipeline is **two-or-more LLM calls in sequence**, each gated by
a human review or curation step:

1. **Analyze** *(two-pass)* — Haiku 4.5 extraction (JD signals,
   keywords, typed hidden_qualities) → Sonnet 4.6 synthesis
   (comparison, suggestions, overall strategy)
2. **Clarify** *(optional, Haiku)* — surfaces real-but-undocumented
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

```mermaid
%% Pipeline of one full callback. apply-run.
%%
%% Shows the LLM calls that can fire across a single application,
%% the Flask route that triggers each, and which model is used.
%% analyze() is a TWO-PASS call: Haiku 4.5 extraction (JD signals) feeds
%% a Sonnet 4.6 synthesis pass (the analyze→generate cache writer). Sonnet
%% 4.6 also handles generate / iterate_clarify / generate_cover_letter;
%% Haiku 4.5 handles clarify and the structured-recommendation calls
%% (recommend, recommend_summary, critique_proposal,
%% promote_clarification_to_bullet).
%%
%% Renders natively on GitHub Markdown and in any Mermaid live editor.
%% Source: analyzer.py + app.py route map (verified 2026-05-25;
%% two-pass analyze + clarify→Haiku updated 2026-06-02, R1 Phase 2 / v1.0.3).

sequenceDiagram
    autonumber
    participant U as User
    participant FE as Frontend<br/>(static/app.js)
    participant APP as Flask app.py
    participant ANL as analyzer.py
    participant SO as Sonnet 4.6
    participant HK as Haiku 4.5
    participant DB as SQLite<br/>(db/resume.sqlite)
    participant FS as Disk<br/>(output/&lt;user&gt;/)

    Note over U,FS: Step 1 — Analyze
    U->>FE: paste JD, click ANALYZE
    FE->>APP: POST /api/analyze
    APP->>DB: insert Application (status=draft) + ApplicationRun (iter 0)
    APP->>ANL: analyze(ctx, jd)
    Note over ANL: phase: extraction
    ANL->>HK: call_kind="analyze_extraction" (~10s, ~1.1k out)
    HK-->>ANL: JSON {essential_skills, hidden_qualities[typed], keyword_placement, ...}
    Note over ANL: phase: synthesis — cache writer<br/>(shares SYSTEM_PROMPT + user prefix with generate)
    ANL->>SO: call_kind="analyze_synthesis" (~58s, ~2.6k out)
    SO-->>ANL: JSON {comparison, suggestions, overall_strategy}
    Note over ANL: merge → AnalyzeResponse (combined p50 67.7s)
    ANL-->>APP: parsed result
    APP->>FS: save context_*.json (iter 0)
    APP-->>FE: 200 + context_path
    FE-->>U: Step 1 panel + Continue

    Note over U,FS: Step 2 — Clarify (optional)
    U->>FE: click GET CLARIFYING QUESTIONS
    FE->>APP: POST /api/clarify
    APP->>ANL: clarify(ctx)
    ANL->>HK: call_kind="clarify" (~7.5s)
    HK-->>ANL: 3-5 questions
    ANL-->>APP: questions
    APP->>FS: write back to same context file
    APP-->>FE: questions
    FE-->>U: render Q&A form
    U->>FE: submit answers
    FE->>APP: POST /api/answer-clarifications
    APP->>FS: merge answers into context

    Note over U,FS: Step 3 — Compose (recommend + curate)
    FE->>APP: POST /api/applications/&lt;id&gt;/recommend
    APP->>ANL: recommend_bullets(ctx)
    ANL->>HK: call_kind="recommend" (~5s)
    HK-->>ANL: bullet_ids[] per experience
    ANL-->>APP: recommendations
    APP->>FS: write llm_recommendations to context
    FE->>APP: POST /api/applications/&lt;id&gt;/recommend-summary
    APP->>ANL: recommend_summaries(ctx)
    ANL->>HK: call_kind="recommend_summary" (~3s)
    HK-->>ANL: summary_item_id
    ANL-->>APP: rec
    APP->>FS: write llm_summary_recommendation
    U->>FE: pin/exclude/add bullets, pick summary
    FE->>APP: POST /api/applications/&lt;id&gt;/composition
    APP->>FS: write composition_overrides

    Note over U,FS: Step 4 — Template (live preview, no LLM)
    U->>FE: select persona
    FE->>APP: GET /api/applications/&lt;id&gt;/preview?template_id=N
    APP->>DB: build_json_resume_from_corpus()
    DB-->>APP: JSON Resume v1.0 doc
    APP-->>FE: rendered HTML
    FE-->>U: iframe shows live preview

    Note over U,FS: Step 5 — Generate
    U->>FE: click GENERATE
    FE->>APP: POST /api/generate
    APP->>ANL: generate(ctx, with_cover_letter=False)
    ANL->>SO: call_kind="generate" (~50s, ~2.3k out)
    SO-->>ANL: {resume_content, changes_summary}
    ANL-->>APP: parsed
    APP->>FS: save_iteration_context() → context_*_iter1.json
    APP->>FS: write resume_*.docx / .pdf / .md
    APP->>DB: write generated output back onto the iter-0 ApplicationRun
    APP-->>FE: paths + previews
    FE-->>U: Step 6 panel with downloads

    Note over U,FS: Step 6 — Iterate (optional, repeatable)
    U->>FE: edit preview, click REFINE / ITERATE CLARIFY
    FE->>APP: POST /api/iterate-clarify
    APP->>ANL: clarify_iteration(ctx, edits, signals)
    ANL->>SO: call_kind="iterate_clarify" (~14s)
    SO-->>ANL: 3-5 follow-up questions
    APP->>FS: append to clarification_questions
    U->>FE: submit answers
    FE->>APP: POST /api/generate (again)
    APP->>ANL: generate(ctx with iter≥1)
    ANL->>SO: call_kind="generate" again
    Note over APP: child context: parent_context_path chain

    Note over U,FS: Optional — Cover letter
    U->>FE: click + GENERATE COVER LETTER
    FE->>APP: POST /api/generate-cover-letter
    APP->>ANL: generate_cover_letter_against_resume()
    ANL->>SO: call_kind="generate_cover_letter" (~17s)
    SO-->>ANL: {cover_letter_content}
    APP->>FS: write cover_*.docx / .pdf / .md
    APP->>DB: write generated_cover_letter_md onto the run row
    APP-->>FE: preview
```

*(Source: [`docs/diagrams/pipeline.mmd`](diagrams/pipeline.mmd). Embedded above so the diagram renders inline on GitHub; edit either copy and keep both in sync.)*

### The four canonical diagrams

| Diagram | Source | Purpose |
|---|---|---|
| [Pipeline](diagrams/pipeline.mmd) | `analyzer.py` + `app.py` route map | One full apply-run, sequence-diagram view |
| [Persistence](diagrams/persistence.mmd) | `db/models.py` | DB tables + FK relationships + cascade behavior |
| [Data flow](diagrams/data-flow.mmd) | `hardening.py` + route handlers | `context_set` lifecycle across iterations |
| [LLM routing](diagrams/llm-routing.mmd) | `analyzer.py` `_call_llm` sites + `docs/dev/perf/PERF_ANALYZE.md` | Which route fires which model, with cost / latency |

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
| [`recall/`](../recall/) | **Memory substrate** (Stages 1–2): deterministic, provenance-stamped retrieval + assembly that *feeds* the doc-grounded avatar. Core is stdlib-only; refactor-immune (`tests/test_recall_boundary.py` enforces the boundary). `recall/sources/` adds the generic, injected `WikiSource` (S1) / `GitGrepSource` (S2) / `SessionSource` (S5-P1) / `VectorSource` (S3 static-embedding semantic search — brute-force cosine over a rebuildable sidecar; the one tier that imports `numpy`, embedder injected) tiers | `Unit`, `Source`, `Scope`, `Context`, `assemble()`, `WikiSource`, `GitGrepSource`, `SessionSource`, `VectorSource` | LLM calls, `app.py`/`analyzer`/DB/Flask imports, **`model2vec`** (the embedder is injected — it lives in the wiring layer so the substrate stays embedder-agnostic + extractable), callback-specific paths baked into the tiers (injected by the wiring layer) |
| [`blueprints/`](../blueprints/) | Flask route modules split out of the `app.py` monolith (born 7.5; the v1.0.8 split target). Domain seams extracted so far (v1.0.8): `analysis.py` (8.3b), `generation.py` (8.3c), `corpus/` (8.3d — a 42-route sub-package: `experiences`/`summaries`/`skills`/`tags`/`curation`/`proposals` on one `corpus_bp`, serializers in `_shared.py`); templates/personas · applications · users/config · diagnostics still resident in `app.py` (8.3e–h). Each seam registers with no `url_prefix` (URLs byte-identical), reads paths from `current_app.config`, imports the shared `web_infra` helpers, and never imports `app.py`. `assistant.py` = the doc-grounded assistant's SSE route (`POST /api/assistant/ask`) + the callback wiring (source roots + SCHEMA audience rules) binding the generic `recall.sources` tiers; it also builds the `model2vec` embedder (lazy, process-cached) and adds the S3 `VectorSource` **"on when available"** (model + index present). The avatar LLM call itself stays in `analyzer.py`; the vector index is built offline by `scripts/build_vector_index.py` into the gitignored `db/vector_index/` sidecar | `assistant_bp` | the LLM call (that is `analyzer.avatar_answer_streaming`); importing `app.py` |
| [`evals/runner.py`](../evals/runner.py) | LLM eval harness — synthetic + real fixtures, 0.0-5.0 rubric scoring | `run_suite()`, `_load_baseline_scores()` | Production paths |
| [`scripts/perf_baseline.py`](../scripts/perf_baseline.py) | Release-cycle tool: print p50/p90 latency percentiles from `logs/llm_calls.jsonl` as a before/after snapshot for perf interventions (R2 streaming, R3 schema trim, R1 split). Not part of the runtime. | CLI only — `python -m scripts.perf_baseline [--since N] [--log path]` | Production import |
| [`scripts/export_corpus_seed.py`](../scripts/export_corpus_seed.py) | Eval tooling: deterministic, LLM-free snapshot of one candidate's corpus (Candidate / Experience / Bullet / SummaryItem / Skill + tag registry) → `seed.json` under the gitignored `evals/fixtures/real/`. A `_within`-style guard refuses to write elsewhere. Consumed by the corpus-backed eval runner. Not part of the runtime. | CLI only — `python -m scripts.export_corpus_seed --user <name>` | LLM calls, production import |
| [`evals/seed_import.py`](../evals/seed_import.py) | Eval tooling: deterministic, LLM-free importer — the inverse of `export_corpus_seed`. Reads a `seed.json`, validates the schema version, and reconstructs the corpus into a fresh in-memory SQLite (PKs preserved) so the eval runner's `--seed` path drives `build_context_set_from_db` like the live pipeline. `seeded_session()` is the context-manager entry. Not part of the runtime. | `import_seed()`, `seeded_session()`, `load_seed()`, `validate_seed()` | LLM calls, production import, pre-filtering (lives in `build_context_set_from_db`) |
| [`evals/bootstrap.py`](../evals/bootstrap.py) | Eval tooling: drives one corpus seed against N JDs through the real `analyze`/`clarify`/`generate` pipeline (reuses the public primitives + `seeded_session` + `build_context_set_from_db`), then deterministically dedups generated bullets/skills across JDs (Jaccard 0.75) into a gitignored `bootstrap.json` under `evals/fixtures/real/`. Second `run_grounding_signals` call site (`--grounding-signals`). **Orchestrates LLM calls; dedup + collation are deterministic.** A `_within` guard refuses to write elsewhere. Not part of the runtime. | CLI — `python -m evals.bootstrap --seed <p> --jd-dir <d>`; `build_bootstrap_document()`, `dedup_texts()`, `run_pipeline_over_jds()` | Production import; duplicating LLM-call logic (reused from `analyzer.py`); touching the runner's `--seed`/file paths |
| [`evals/annotation.py`](../evals/annotation.py) | Eval tooling: **deterministic, LLM-free** annotation contract — the human-in-the-loop seam from `bootstrap.json` to a `--suite real` fixture. Declares `annotation_schema_version: 1` + a fail-closed validator (mirrors `seed_import.py`). Emits a blank `annotations.json` skeleton (clusters + clarification questions + inline MiniCheck/NLI pre-scores) for a human to fill with a `keep`/`fix`/`omit`/`fabricated` verdict (reusing `evals/rubrics/` `failed_rules` slugs), then collates a completed file into an `expected.json` fixture + an improvement brief. A `_within` guard refuses to write outside `evals/fixtures/real/`. Not part of the runtime. | CLI — `python -m evals.annotation --bootstrap <p> --emit-template` / `--collate`; `validate_annotations()`, `build_annotation_template()`, `collate_expected()`, `build_improvement_brief()` | LLM calls; production import; touching the runner's `--seed`/file/bootstrap paths; editing prompt constants |

**Code that crosses modules.** When a route in `app.py` needs to
call the LLM, it imports the analyzer function. When the analyzer
needs deterministic processing, it imports from `hardening.py`.
**These directions never reverse** — `hardening.py` does not
import `analyzer.py`; `analyzer.py` does not import `app.py`.

---

## Persistence model

The DB schema is in [`docs/diagrams/persistence.mmd`](diagrams/persistence.mmd).

```mermaid
%% Persistence model — db/resume.sqlite ER diagram.
%%
%% Shows the active DB tables and their foreign-key relationships.
%% Cascade behavior (ON DELETE CASCADE vs SET NULL) noted per edge
%% where it differs from the SQLAlchemy default. Source of truth:
%% db/models.py — verify with `grep -nE "^class |ForeignKey" db/models.py`.
%%
%% Pattern legend:
%%   ||--o{   one (required) to many
%%   }o--||   many to one (required)
%%   ||--o|   one to (optional) one
%%   }o--o{   many to many (junction table; rendered as two edges)
%%
%% Renders on GitHub Markdown via `mermaid` fenced block.
%% Field lists are abbreviated to the joinable / curatable columns;
%% audit timestamps (created_at, updated_at) omitted for readability.

erDiagram
    candidate {
        int id PK
        string username UK
        string name
        string email
        string phone
        string linkedin_url
        string website_url
        text profile_text "legacy; SummaryItem variants are canonical post-v1.0"
    }

    experience {
        int id PK
        int candidate_id FK
        string company
        string location
        string start_date "YYYY-MM"
        string end_date "YYYY-MM or NULL=current"
        text summary
        int is_active "soft-retire"
        int is_pending_review
    }

    experience_title {
        int id PK
        int experience_id FK
        string title
        int is_official "partial unique idx: one per experience"
        int truthful_enough_to_use
        int is_pending_review
        string source "official | user_added | llm_proposed:&lt;run_id&gt;"
    }

    bullet {
        int id PK
        int experience_id FK
        text text
        int display_order
        int is_active "soft-retire"
        int is_pending_review
        string source
        string pattern_kind "xyz | car | star"
        int has_outcome
    }

    summary_item {
        int id PK
        int candidate_id FK
        text text
        string label
        int display_order
        int is_active
        int has_outcome
    }

    tag {
        int id PK
        string kind "role | domain | skill | tech"
        string value
        string display_value
    }

    bullet_tag {
        int bullet_id PK_FK
        int tag_id PK_FK
        float confidence
    }

    experience_title_tag {
        int experience_title_id PK_FK
        int tag_id PK_FK
        float confidence
    }

    summary_item_tag {
        int summary_item_id PK_FK
        int tag_id PK_FK
        float confidence
    }

    skill {
        int id PK
        int candidate_id FK
        string name
        string category
        string proficiency
    }

    persona_template {
        int id PK
        int candidate_id FK "NULL=bundled"
        string name
        string path
        string source "bundled | owned"
        int is_default
        int primary_role_tag_id FK
        text description
    }

    application {
        int id PK
        int candidate_id FK
        string title
        text jd_text
        string jd_fingerprint
        string status "draft | submitted | rejected | interview | offer | accepted"
    }

    application_run {
        int id PK
        int application_id FK
        int iteration
        int parent_run_id FK "self-FK; iteration audit trail"
        string run_id UK "12-hex correlation primitive"
        string prompt_version
        int persona_template_id FK
        text corpus_snapshot_json
        text analysis_json
        text clarifications_json
        text generated_resume_md
        text generated_cover_letter_md
        text ats_roundtrip_json
    }

    application_bullet {
        int id PK
        int application_run_id FK
        int bullet_id FK "no cascade; retire instead"
        int position
    }

    clarification {
        int id PK
        int candidate_id FK
        int application_id FK
        string question
        text answer
        string kind "experience_probe | scope_probe | iteration_probe"
        int promoted_to_bullet_id FK
    }

    candidate ||--o{ experience          : "1 → N (cascade)"
    candidate ||--o{ summary_item        : "1 → N (cascade)"
    candidate ||--o{ skill               : "1 → N (cascade)"
    candidate ||--o{ persona_template    : "1 → N (owned only)"
    candidate ||--o{ application         : "1 → N (cascade)"
    candidate ||--o{ clarification       : "1 → N (cascade)"

    experience ||--o{ experience_title   : "1 → N (cascade)"
    experience ||--o{ bullet             : "1 → N (cascade)"

    bullet ||--o{ bullet_tag             : "1 → N (cascade)"
    experience_title ||--o{ experience_title_tag : "1 → N (cascade)"
    summary_item ||--o{ summary_item_tag : "1 → N (cascade)"

    tag ||--o{ bullet_tag                : "1 → N"
    tag ||--o{ experience_title_tag      : "1 → N"
    tag ||--o{ summary_item_tag          : "1 → N"
    tag ||--o{ persona_template          : "1 → N (primary_role_tag_id)"

    application ||--o{ application_run   : "1 → N (cascade); parent_run_id chains iterations"
    application_run ||--o| application_run : "parent_run_id (self, SET NULL)"
    application_run ||--o{ application_bullet : "1 → N (cascade)"
    application_run }o--o| persona_template   : "N → 1 (SET NULL)"

    bullet ||--o{ application_bullet     : "1 → N (NO CASCADE; soft-retire only)"

    application ||--o{ clarification     : "1 → N (cascade)"
    bullet ||--o| clarification          : "promoted_to_bullet_id"
```

*(Source: [`docs/diagrams/persistence.mmd`](diagrams/persistence.mmd). Embedded above so the diagram renders inline on GitHub; edit either copy and keep both in sync.)*
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

```mermaid
%% LLM routing — every _call_llm site in analyzer.py, with model
%% assignment and cache-prefix usage.
%%
%% Source: analyzer.py `_call_llm(...)` invocations + the SONNET_MODEL
%% / HAIKU_MODEL constants. Cost / latency numbers from
%% docs/dev/perf/PERF_ANALYZE.md (real production data across 83+ runs);
%% two-pass analyze + clarify→Haiku figures from
%% docs/dev/perf/R1_PHASE2_RESULTS.md (R1 Phase 2 / v1.0.3, 2026-06-02).
%%
%% Two model tiers:
%%   - Sonnet 4.6: heavy reasoning, JSON-structured output, costlier
%%   - Haiku 4.5:  structured selection / classification, cheap, fast
%%
%% A call uses the "cached_user_prefix" trick when it can re-use a long
%% static user-message block across attempts within the same run (the
%% retry path shares the cache). analyze_synthesis runs under the shared
%% SYSTEM_PROMPT and WRITES the [SYSTEM_PROMPT][corpus+resume] prefix that
%% generate READS; the Haiku analyze_extraction pass has its own
%% EXTRACTION_SYSTEM_PROMPT (separate cache pool). The clarify variants
%% override the system prompt, so they pay one extra cache-miss on the
%% system block.

graph LR
    subgraph SO[Sonnet 4.6 — heavy reasoning]
        direction TB
        A1[analyze_synthesis<br/>p50 = 58 s<br/>median out: 2600 tok<br/>cache writer]
        A3[iterate_clarify<br/>p50 = 14 s<br/>median out: 665 tok]
        A4[generate<br/>p50 = 50 s<br/>median out: 2268 tok]
        A5[generate_cover_letter<br/>p50 = 17 s<br/>median out: 732 tok]
    end

    subgraph HK[Haiku 4.5 — structured selection]
        direction TB
        A0[analyze_extraction<br/>p50 = 10 s<br/>median out: 1100 tok]
        A2[clarify<br/>p50 = 7.5 s<br/>median out: 630 tok]
        H1[recommend bullets<br/>p50 = 5 s<br/>median out: 417 tok]
        H2[recommend_summary<br/>p50 = 3 s<br/>median out: 164 tok]
        H3[critique_proposal<br/>p50 = 5 s<br/>median out: 387 tok]
        H4[promote_clarification_to_bullet<br/>per-promotion]
        H5[extract_experiences<br/>onboarding/corpus_import]
    end

    %% Routes that fire each call
    R_AN[/POST /api/analyze/] --> A0
    R_AN --> A1
    R_CL[/POST /api/clarify/] --> A2
    R_IT[/POST /api/iterate-clarify/] --> A3
    R_GE[/POST /api/generate/] --> A4
    R_CO[/POST /api/generate-cover-letter/] --> A5

    R_RC[/POST /api/applications/&lt;id&gt;/recommend/] --> H1
    R_RS[/POST /api/applications/&lt;id&gt;/recommend-summary/] --> H2
    R_PC[/POST /api/proposals/&lt;id&gt;/critique/] --> H3
    R_PR[/POST /api/clarifications/&lt;id&gt;/promote-to-bullet/] --> H4
    R_IM[/POST /api/users/&lt;u&gt;/corpus/ingest-resume/] --> H5

    %% Cache-prefix usage. analyze_synthesis (A1) runs under the shared
    %% SYSTEM_PROMPT, so its cached prefix [SYSTEM_PROMPT][corpus+resume]
    %% is byte-identical to generate's — synthesis WRITES the prefix and
    %% generate READS it. The Haiku analyze_extraction pass (A0) uses its
    %% own EXTRACTION_SYSTEM_PROMPT (separate cache pool). clarify variants
    %% override the system prompt, reusing the heavy user prefix.
    classDef cached fill:#0f172a,stroke:#10b981,color:#d1fae5
    classDef nocache fill:#0f172a,stroke:#ef4444,color:#fecaca

    class A1,A4 cached
    class A0,A2,A3,A5,H1,H2,H3,H4,H5 nocache

    %% Legend (rendered as a subgraph that visually clarifies the colors)
    subgraph Legend["legend"]
        L1[green border = uses cached_user_prefix]:::cached
        L2[red border = no cache prefix, cache_read=0]:::nocache
    end

    %% Retry attribution — every call kind has a sibling "<kind>_retry"
    %% call_kind for dashboard breakdowns. Implementation:
    %% analyzer.py:_parse_or_retry() line 730 sets the retry call_kind.
```

*(Source: [`docs/diagrams/llm-routing.mmd`](diagrams/llm-routing.mmd). Embedded above so the diagram renders inline on GitHub; edit either copy and keep both in sync.)*
Latency data from real production usage in
[`docs/dev/perf/PERF_ANALYZE.md`](dev/perf/PERF_ANALYZE.md).

**Sonnet 4.6** (`claude-sonnet-4-6`) handles heavy reasoning:
`analyze_synthesis`, `iterate_clarify`, `generate`,
`generate_cover_letter`. These calls produce large JSON
responses. `analyze` is now a **two-pass** call — a Haiku
extraction pass feeds the Sonnet synthesis pass (combined
p50 ~67.7 s, down from ~103 s as a single Sonnet call).

**Haiku 4.5** (`claude-haiku-4-5-20251001`) handles structured
selection / classification: `analyze_extraction` (JD signals),
`clarify`, `recommend` (bullets), `recommend_summary`,
`critique_proposal`, `promote_clarification_to_bullet`,
`extract_experiences`. ~5-second median, ~$0.002 per call.

**Cache prefix.** `analyze_synthesis` and `generate` share a heavy
cached user prefix (corpus + résumé blocks): synthesis runs under
the shared `SYSTEM_PROMPT` and WRITES the prefix that `generate`
READS. The Haiku `analyze_extraction` pass uses its own
`EXTRACTION_SYSTEM_PROMPT` (separate cache pool). The clarify
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

```mermaid
%% Data flow — context_set lifecycle.
%%
%% Shows how the JSON `context_set` artifact is built, mutated, and
%% chained across the wizard steps and iterations. The context file is
%% the single source of truth between LLM calls — every route that
%% touches it does so through `hardening.py:build_context_set` or
%% `save_iteration_context`, and validates containment under OUTPUT_DIR
%% via `_within()`.
%%
%% A NEW timestamped child file is written on every /api/generate so
%% the parent_context_path chain is the iteration audit trail.
%%
%% Source: hardening.py (ContextSet TypedDict, save_iteration_context),
%% app.py route handlers, CLAUDE.md "context_set lifecycle" diagram.

flowchart TD
    %% On-disk artifacts (rectangles)
    %% Routes (rounded)
    %% LLM-touching nodes (yellow)
    %% Deterministic Python (blue)

    classDef onDisk fill:#1f2937,stroke:#9ca3af,color:#f3f4f6
    classDef route fill:#374151,stroke:#60a5fa,color:#e5e7eb
    classDef llm fill:#78350f,stroke:#fbbf24,color:#fef3c7
    classDef det fill:#1e3a8a,stroke:#60a5fa,color:#dbeafe

    Start([User picks JD]) --> R1
    R1[/POST /api/analyze/]:::route --> BCS[build_context_set<br/>candidate + experience + bullet snapshot]:::det
    BCS --> LLM1{{analyze<br/>Haiku extract → Sonnet synth}}:::llm
    LLM1 --> SCS[save_context_set<br/>writes iter 0]:::det
    SCS --> CTX0[(output/&lt;u&gt;/context_TS.json<br/>iter=0)]:::onDisk

    CTX0 --> R2{Clarify?}:::route
    R2 -->|skip| R3
    R2 -->|/api/clarify| LLM2{{clarify<br/>Haiku 4.5}}:::llm
    LLM2 --> M1[merge clarification_questions]:::det
    M1 --> CTX0
    CTX0 --> R2A[/POST /api/answer-clarifications/]:::route
    R2A --> M2[merge clarifications]:::det
    M2 --> CTX0

    CTX0 --> R3[/POST /api/applications/&lt;id&gt;/recommend/]:::route
    R3 --> LLM3{{recommend_bullets<br/>Haiku 4.5}}:::llm
    LLM3 --> M3[merge llm_recommendations]:::det
    M3 --> CTX0
    CTX0 --> R3A[/POST /api/applications/&lt;id&gt;/recommend-summary/]:::route
    R3A --> LLM3A{{recommend_summary<br/>Haiku 4.5}}:::llm
    LLM3A --> M3A[merge llm_summary_recommendation]:::det
    M3A --> CTX0

    CTX0 --> R4[/POST /api/applications/&lt;id&gt;/composition<br/>user pins / excludes / adds/]:::route
    R4 --> M4[merge composition_overrides]:::det
    M4 --> CTX0

    CTX0 --> R5[/POST /api/generate/]:::route
    R5 --> ACS[_apply_chosen_summary<br/>resolve pin > rec > default]:::det
    ACS --> LLM4{{generate<br/>Sonnet 4.6}}:::llm
    LLM4 --> SIC[save_iteration_context<br/>writes NEW child file]:::det
    LLM4 --> RUNDB[persist_corpus_generation<br/>resume md + bullets/titles → run row]:::det
    SIC --> CTX1[(output/&lt;u&gt;/context_TS_iter1.json<br/>parent_context_path → iter 0)]:::onDisk
    SIC --> ARTOUT[(output/&lt;u&gt;/resume_TS.docx /<br/>.pdf / .md / .jsonresume.json)]:::onDisk

    CTX1 --> R6{Iterate?}:::route
    R6 -->|/api/save-edits| M5[merge edited_resume_text / edited_cover_letter_text<br/>NO iteration advance]:::det
    M5 --> CTX1
    R6 -->|/api/iterate-clarify| CIS[compute_iteration_signals<br/>verb diversity + grounding + edits]:::det
    CIS --> LLM5{{clarify_iteration<br/>Sonnet 4.6}}:::llm
    LLM5 --> M6[append iter_qN questions]:::det
    M6 --> CTX1
    R6 -->|/api/generate again| ACS2[_apply_chosen_summary]:::det
    ACS2 --> LLM6{{generate iter ≥ 1<br/>Sonnet 4.6<br/>historical_resumes block}}:::llm
    LLM6 --> SIC2[save_iteration_context]:::det
    SIC2 --> CTX2[(output/&lt;u&gt;/context_TS_iter2.json<br/>parent_context_path → iter 1)]:::onDisk

    CTX2 --> R7{Cover letter?}:::route
    R7 -->|/api/generate-cover-letter| LLM7{{generate_cover_letter<br/>Sonnet 4.6}}:::llm
    LLM7 --> AROUTCL[(output/&lt;u&gt;/cover_TS.docx /<br/>.pdf / .md)]:::onDisk
    LLM7 --> CLDB[persist_cover_letter_md<br/>cover-letter md → same run row]:::det

    R7 -->|done| Done([Download])
```

*(Source: [`docs/diagrams/data-flow.mmd`](diagrams/data-flow.mmd). Embedded above so the diagram renders inline on GitHub; edit either copy and keep both in sync.)*

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

Every résumé output also writes a sidecar
`resume_TS.jsonresume.json` (canonical JSON Resume v1.0
intermediate) for downstream tooling and re-render. Best-effort
write; failures don't block the primary output.

**Cover letters share the same three formats** (`generate_cover_letter(content, ..., output_format)`):
`.md` is normalized markdown; `.pdf` renders through the shared
`personas/cover_letter.html` business-letter shell via Playwright
(`pdf_render.render_cover_letter_pdf`), byte-faithful to the Step-6
preview; `.docx` uses `_write_cover_letter_docx()` (persona font, dense
single-spaced body, no name banner, inline addressee — the business-letter
styling decisions). No JSON Resume sidecar — a cover letter is not a résumé.

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
  [`docs/dev/perf/PERF_ANALYZE.md`](dev/perf/PERF_ANALYZE.md); reproduce the
  audit query against your own `logs/llm_calls.jsonl`.
