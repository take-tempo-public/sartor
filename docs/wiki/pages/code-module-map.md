# Code module map

> **Audience:** `dev`
> **Concept:** the top-level module inventory and the inward-dependency shape —
> everything points toward Production, and Production answers only upward to
> Governance. The navigational hub for every code page (the code analogue of
> [[excellence-walk]]).
> **Sources:** [`docs/architecture.md`](../../architecture.md) §"System overview" +
> §"Module map"; the root modules ([`analyzer.py`](../../../analyzer.py),
> [`hardening.py`](../../../hardening.py), [`app.py`](../../../app.py),
> [`generator.py`](../../../generator.py), the `db/` + `evals/` + `dashboard/`
> packages, [`static/app.js`](../../../static/app.js) +
> [`templates/index.html`](../../../templates/index.html)).
> **Grounding:** per [`SCHEMA.md`](../SCHEMA.md); conclusions tagged `[synthesis]`.

---

## The shape

Each root Python file has **one stated job**, and the import edges only ever
point *inward* toward the LLM core — never back out. Verified at HEAD:
[`hardening.py`](../../../hardening.py) imports neither `analyzer` nor `app`, and
[`analyzer.py`](../../../analyzer.py) does not import `app` — so the dependency
arrows are `app → analyzer → hardening`, and they never reverse. The architecture
doc states this rule as prose; the absence of those import lines is the
enforcement `[synthesis]`. This is the **Production → Governance answers-upward**
posture in code form: the deterministic modules are the load-bearing floor, the
LLM brain sits above them, and the route layer composes both `[synthesis]`.

The deterministic / LLM boundary itself is canonical in
[`AGENTS.md`](../../../AGENTS.md) (the P1 hardening rule) — see
[[deterministic-llm-boundary]] for the wiki treatment; this page only inventories
who lives where.

## The LLM brain (one module)

| Module | Job | Anchor |
|---|---|---|
| [`analyzer.py`](../../../analyzer.py) | **All LLM calls**; system-prompt family; response parsing + retry. The only module that opens the raw Anthropic client (`.stream` in `_call_llm_streaming`, plus one focused `.create` in `check_refinement_scope`). | [`analyzer.py:_call_llm`](../../../analyzer.py), [`analyzer.py:_parse_or_retry`](../../../analyzer.py), [`analyzer.py:SYSTEM_PROMPT`](../../../analyzer.py), [`analyzer.py:PROMPT_VERSION`](../../../analyzer.py) |

The public verbs — [`analyze`](../../../analyzer.py),
[`clarify`](../../../analyzer.py), [`clarify_iteration`](../../../analyzer.py),
[`generate`](../../../analyzer.py),
[`generate_cover_letter_against_resume`](../../../analyzer.py),
[`recommend_bullets`](../../../analyzer.py),
[`recommend_summaries`](../../../analyzer.py),
[`critique_proposal`](../../../analyzer.py),
[`promote_clarification_to_bullet`](../../../analyzer.py) — all funnel through
`_call_llm` / `_parse_or_retry`. One nuance the architecture doc rounds off:
`extract_experiences` actually lives in
[`onboarding/extract_experiences.py:extract_experiences`](../../../onboarding/extract_experiences.py),
but it imports `_parse_or_retry` + `HAIKU_MODEL` from `analyzer` and issues no
raw API call of its own — so the "every LLM call routes through analyzer's
machinery" invariant holds even though that one function lives off-root
`[synthesis]`. The full call roster is [[llm-call-catalog]]; the model-routing
tiers are in [[pipeline-stages]] and [[generation-and-grounding]].

## The deterministic floor (P1 hardening — no LLM calls)

| Module | Job | Anchor |
|---|---|---|
| [`hardening.py`](../../../hardening.py) | Keyword/ATS checks, the `context_set` lifecycle, post-generation metrics. | [`hardening.py:build_context_set`](../../../hardening.py), [`hardening.py:save_iteration_context`](../../../hardening.py), [`hardening.py:ContextSet`](../../../hardening.py), [`hardening.py:compute_iteration_signals`](../../../hardening.py) |
| [`generator.py`](../../../generator.py) | Document output `.md` / `.docx` / `.pdf`. | [`generator.py:generate_resume`](../../../generator.py), [`generator.py:_write_docx`](../../../generator.py), [`generator.py:BULLET_RE`](../../../generator.py) |
| [`parser.py`](../../../parser.py) | Résumé file → structured dict. | [`parser.py:parse_resume`](../../../parser.py) |
| [`pdf_render.py`](../../../pdf_render.py) | Jinja2 + Playwright PDF / live-preview render. | [`pdf_render.py:render_pdf`](../../../pdf_render.py), [`pdf_render.py:html_template_path_for`](../../../pdf_render.py) |
| [`json_resume.py`](../../../json_resume.py) | Markdown → JSON Resume v1.0 normalizer. | [`json_resume.py:md_to_json_resume`](../../../json_resume.py) |
| [`corpus_to_json_resume.py`](../../../corpus_to_json_resume.py) | JSON Resume doc straight from corpus rows + overrides. | [`corpus_to_json_resume.py:build_json_resume_from_corpus`](../../../corpus_to_json_resume.py) |
| [`scraper.py`](../../../scraper.py) | Best-effort URL / portfolio text fetch. | [`scraper.py:fetch_url_content`](../../../scraper.py), [`scraper.py:fetch_profile_content`](../../../scraper.py) |

(Note: the architecture-doc module table names the scraper entrypoint `scrape_url()`,
but at HEAD the public symbols are `fetch_url_content` / `fetch_profile_content` —
the doc is stale here; the wiki cites the real symbols `[synthesis]`.) The
`context_set` artifact these modules pass around is [[context-set-contract]]; its
per-iteration chaining is [[iteration-audit-chain]]; document output is
[[document-rendering]].

## The route + frontend surface

| Module | Job | Anchor |
|---|---|---|
| [`app.py`](../../../app.py) | Flask routes; the `_safe_username` / `_within` security gate; request/response glue. | [`app.py:_safe_username`](../../../app.py), [`app.py:_within`](../../../app.py) |
| [`static/app.js`](../../../static/app.js) + [`templates/index.html`](../../../templates/index.html) | The single-page wizard front-end. | — |

`app.py` imports the analyzer verbs when a route needs the LLM and the
deterministic modules for everything else; it registers the dashboard blueprint
([`app.py` `register_blueprint(dashboard_bp)`](../../../app.py)). The route
inventory is [[route-surface]]; the wizard is [[frontend-wizard]]. The security
gate is canonical in [`AGENTS.md`](../../../AGENTS.md) — cited, not restated (D5).

## Persistence (the `db/` package)

| Module | Job | Anchor |
|---|---|---|
| [`db/models.py`](../../../db/models.py) | SQLAlchemy 2.0 ORM models. | [`db/models.py:Candidate`](../../../db/models.py), [`db/models.py:Application`](../../../db/models.py), [`db/models.py:ApplicationRun`](../../../db/models.py) |
| [`db/session.py`](../../../db/session.py) | Engine + session factory; migration runner. | [`db/session.py:init_db`](../../../db/session.py), [`db/session.py:get_session`](../../../db/session.py) |
| [`db/build_context.py`](../../../db/build_context.py) | DB-backed `build_context_set` variant; corpus bullet scorer. | [`db/build_context.py:build_context_set_from_db`](../../../db/build_context.py), [`db/build_context.py:score_corpus_bullet`](../../../db/build_context.py) |

The corpus data model is [[corpus-data-model]]; how corpus rows reach output is
[[corpus-to-output-reach]]; the `Application` / `ApplicationRun` audit chain is
[[application-audit-chain]].

## Off the core pipeline (eval + diagnostics — read production, not depended on by it)

| Module | Job | Anchor |
|---|---|---|
| [`evals/runner.py`](../../../evals/runner.py) | LLM eval harness; 0.0–5.0 rubric scoring. | [`evals/runner.py:run_suite`](../../../evals/runner.py), [`evals/runner.py:_load_baseline_scores`](../../../evals/runner.py) |
| [`dashboard/`](../../../dashboard) | Read-only Flask blueprint at `/_dashboard` for eval results, cost cards, failure-mode heatmap. | [`dashboard/routes.py:dashboard_bp`](../../../dashboard/routes.py) |

The harness is [[eval-harness]]; the console is [[diagnostics-console]]. Both read
production artifacts (logs, eval JSON). `app.py` (the composition root) *does*
import them — the dashboard blueprint at
[`app.py` `register_blueprint(dashboard_bp)`](../../../app.py) and the
`evals.*` modules inside their localhost route handlers — but the **core
resume-generation pipeline** (`analyze`→`generate`→`iterate` in `analyzer.py` +
`hardening.py`) never depends on them: the arrow is `app → eval/dashboard`, never
`pipeline → eval/dashboard` `[synthesis]`.

## Related

- [`overview`](../overview.md) — the front door this map sits under.
- [[engineering-workstreams]] — WS-1 (the single-file `app.py` monolith) is the navigability cost this inventory makes visible.
- [[deterministic-llm-boundary]] — the P1 rule that fixes which column a module lands in.
- [[prompt-version-discipline]] — the `PROMPT_VERSION` bump that rides every `analyzer.py` prompt change.
- [[context-set-contract]] — the JSON contract the deterministic floor builds + passes.
- [[iteration-audit-chain]] — the per-iteration `context_*.json` chain.
- [[corpus-data-model]] — the `db/models.py` schema.
- [[corpus-to-output-reach]] — how corpus rows become résumé output.
- [[application-audit-chain]] — `Application` / `ApplicationRun` provenance.
- [[pipeline-stages]] — the analyze→generate→iterate sequence across these modules.
- [[llm-call-catalog]] — every `analyzer.py` LLM verb + its call_kind.
- [[generation-and-grounding]] — the `generate` call + the no-invention check.
- [[route-surface]] — the `app.py` route inventory.
- [[frontend-wizard]] — `static/app.js` + `templates/index.html`.
- [[document-rendering]] — `generator.py` / `pdf_render.py` / the JSON Resume intermediate.
- [[eval-harness]] — `evals/runner.py`.
- [[diagnostics-console]] — the `/_dashboard` blueprint.
