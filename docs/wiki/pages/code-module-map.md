# Code module map

> **Audience:** `dev`
> **Concept:** the top-level module inventory and the inward-dependency shape —
> everything points toward Production, and Production answers only upward to
> Governance. The navigational hub for every code page (the code analogue of
> [[excellence-walk]]).
> **Sources:** [`docs/dev/architecture.md`](../../dev/architecture.md) §"System overview" +
> §"Module map"; the root modules ([`analyzer.py`](../../../analyzer.py),
> [`hardening.py`](../../../hardening.py), [`config.py`](../../../config.py),
> [`app.py`](../../../app.py), [`generator.py`](../../../generator.py), the `db/` +
> `evals/` + `dashboard/` + `blueprints/` + `web_infra/` + `ui_pages/` + `scripts/`
> packages, [`static/app.js`](../../../static/app.js) +
> [`templates/index.html`](../../../templates/index.html)).
> **Grounding:** per [`SCHEMA.md`](../SCHEMA.md); conclusions tagged `[synthesis]`.

---

## The shape

Each root Python file has **one stated job**, and the import edges only ever
point *inward* toward the LLM core — never back out. Verified at HEAD:
[`hardening.py`](../../../hardening.py) imports neither `analyzer` nor `app`, and
[`analyzer.py`](../../../analyzer.py) does not import `app` — so the dependency
arrows are `app → blueprints → analyzer → hardening`, and they never reverse.
The architecture doc states this rule as prose; the absence of those import
lines is the enforcement `[synthesis]`. This is the **Production → Governance
answers-upward** posture in code form: the deterministic modules are the
load-bearing floor, the LLM brain sits above them, and the route layer composes
both `[synthesis]`.

Since the Sprint 8.3a–h WS-1 split (see [[engineering-workstreams]]), the route
layer itself has two tiers: the domain **blueprints** (which may import
`analyzer`, DB models, and the deterministic modules) and the **`web_infra/`
leaf** they all share, which is asserted — by
[`tests/test_web_infra_is_leaf.py`](../../../tests/test_web_infra_is_leaf.py) —
to never import `app.py`, any blueprint, or `config.py`
([`web_infra/__init__.py`](../../../web_infra/__init__.py) docstring). So the
full arrow is `app.py → blueprints/ → {analyzer.py, hardening.py, db/}`, with
`web_infra/` sitting off to the side as infrastructure every layer above it can
import freely `[synthesis]`.

The deterministic / LLM boundary itself is canonical in
[`AGENTS.md`](../../../AGENTS.md) (the P1 hardening rule) — see
[[deterministic-llm-boundary]] for the wiki treatment; this page only inventories
who lives where.

## The LLM brain (one module)

| Module | Job | Anchor |
|---|---|---|
| [`analyzer.py`](../../../analyzer.py) | **All LLM calls**; system-prompt family; response parsing + retry. The only module that opens the raw Anthropic client (`.stream` in `_call_llm_streaming` — every call site, including `check_refinement_scope`, funnels through it as of item 21). | [`analyzer.py:_call_llm`](../../../analyzer.py), [`analyzer.py:_parse_or_retry`](../../../analyzer.py), [`analyzer.py:SYSTEM_PROMPT`](../../../analyzer.py), [`analyzer.py:PROMPT_VERSION`](../../../analyzer.py) |

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
| [`preflight.py`](../../../preflight.py) | Machine capability probes — Python, OS, API key, Chromium/PDF, semantic-recall index, container engine. Deterministic and stdlib-only, but **not** one of the eight modules on `AGENTS.md`'s enumerated C-6 boundary list — it sits here as a fellow no-LLM module, not as a member of that governed set `[synthesis]`. | [`preflight.py:probe_all`](../../../preflight.py), [`preflight.py:chromium_capability`](../../../preflight.py), [`preflight.py:pdf_available`](../../../preflight.py), [`preflight.py:run_doctor`](../../../preflight.py) |
| [`hardening.py`](../../../hardening.py) | Keyword/ATS checks, the `context_set` lifecycle, post-generation metrics. | [`hardening.py:build_context_set`](../../../hardening.py), [`hardening.py:save_iteration_context`](../../../hardening.py), [`hardening.py:ContextSet`](../../../hardening.py), [`hardening.py:compute_iteration_signals`](../../../hardening.py) |
| [`generator.py`](../../../generator.py) | Document output `.md` / `.docx` / `.pdf`. | [`generator.py:generate_resume`](../../../generator.py), [`generator.py:_write_docx_from_json_resume`](../../../generator.py), [`generator.py:BULLET_RE`](../../../generator.py) |
| [`parser.py`](../../../parser.py) | Résumé file → structured dict. | [`parser.py:parse_resume`](../../../parser.py) |
| [`pdf_render.py`](../../../pdf_render.py) | Jinja2 + Playwright PDF / live-preview render. | [`pdf_render.py:render_pdf`](../../../pdf_render.py), [`pdf_render.py:html_template_path_for`](../../../pdf_render.py) |
| [`json_resume.py`](../../../json_resume.py) | Markdown → JSON Resume v1.0 normalizer; font mapping and education/work text rendering. | [`json_resume.py:md_to_json_resume`](../../../json_resume.py), [`json_resume.py:APPROVED_FONTS`](../../../json_resume.py), [`json_resume.py:map_to_approved_font`](../../../json_resume.py), [`json_resume.py:needs_month_precision`](../../../json_resume.py), [`json_resume.py:education_position_text`](../../../json_resume.py) |
| [`corpus_to_json_resume.py`](../../../corpus_to_json_resume.py) | JSON Resume doc straight from corpus rows + overrides. | [`corpus_to_json_resume.py:build_json_resume_from_corpus`](../../../corpus_to_json_resume.py) |
| [`scraper.py`](../../../scraper.py) | Best-effort URL / portfolio text fetch. | [`scraper.py:fetch_url_content`](../../../scraper.py), [`scraper.py:fetch_profile_content`](../../../scraper.py) |

The
`context_set` artifact these modules pass around is [[context-set-contract]]; its
per-iteration chaining is [[iteration-audit-chain]]; document output is
[[document-rendering]].

## The route + frontend surface

**`app.py` is no longer where the routes live.** The Sprint 8.3a–h WS-1 split
(see [[engineering-workstreams]]) moved every `@app.route` onto domain
blueprints and moved the security/config/HTTP helpers into a new `web_infra/`
leaf package. At HEAD `app.py` is a 392-line composition root carrying
**zero** route decorators:

| Module | Job | Anchor |
|---|---|---|
| [`app.py`](../../../app.py) | Composition root: the `create_app(Config)` application factory, `register_blueprints()`, the module-level WSGI/console handle (`app = create_app()`), and `main()` with `--setup` / `--doctor` flags. CLI helpers: `_run_setup` (Chromium + vector index bootstrap), `_prompt_for_api_key` (item 104), `_write_api_key`. No route handlers, path globals, or per-request helpers remain — they moved to `blueprints/` + `web_infra/` (Sprint 8.3a–h). | [`app.py:create_app`](../../../app.py), [`app.py:register_blueprints`](../../../app.py), [`app.py:main`](../../../app.py), [`app.py:_run_setup`](../../../app.py), [`app.py:_prompt_for_api_key`](../../../app.py), [`app.py:_write_api_key`](../../../app.py) |
| [`config.py`](../../../config.py) | Typed configuration: the `Config` dataclass, `TEMPLATES_DIR` + `STATIC_DIR` path constants. Deterministic (P1 hardening, no LLM calls); injected into `create_app()` so `blueprints/` + `tests/` reach the same root `base_dir` without monkeypatching globals. Lives top-level (not in `web_infra/`) so `app.py` and test fixtures import it freely; `web_infra/` itself does not import this module (charter C-6). | [`config.py:Config`](../../../config.py), [`config.py:TEMPLATES_DIR`](../../../config.py), [`config.py:STATIC_DIR`](../../../config.py) |
| [`blueprints/`](../../../blueprints/) | Every Flask route, split into eight domain seams: `analysis.py` (5 routes, 8.3b), `generation.py` (7, 8.3c), `corpus/` (a 7-submodule sub-package on one `corpus_bp`, 8.3d), `templates.py` (13, 8.3e), `applications.py` (22, 8.3f), `users.py` (7, 8.3g), `diagnostics.py` (9, 8.3h — the last seam), `assistant.py` (1, the doc-grounded assistant, predates the split). 118 route decorators total; each of the seven monolith-origin seams registers with **no** `url_prefix` so every URL stays byte-identical. Full route inventory is [[route-surface]]. | [`blueprints/__init__.py`](../../../blueprints/__init__.py) |
| [`web_infra/`](../../../web_infra/) | The **leaf** helper package `app.py` and every blueprint share instead of re-inlining: `security.py` (`_safe_username`/`_within`), `http.py` (`_sse`, `_error_detail_payload`), `request_gates.py` (`_is_localhost_request`), `clients.py` (`_get_client`), `config_io.py` (`_load_config`/`_save_config`), `provisioning.py` (`_get_or_provision_candidate`), `openapi.py` (`spec` — the spectree OpenAPI-emission instance five routes decorate; see [[openapi-api-reference]]). Never imports `app.py`, any blueprint, or `config.py` — enforced by `tests/test_web_infra_is_leaf.py`. | [`web_infra/security.py:_safe_username`](../../../web_infra/security.py), [`web_infra/security.py:_within`](../../../web_infra/security.py) |
| [`static/app.js`](../../../static/app.js) + [`templates/index.html`](../../../templates/index.html) | The single-page wizard front-end. | — |

`app.py`'s `register_blueprints()` mounts all nine — the eight `blueprints/`
seams plus the pre-existing read-only `dashboard/` blueprint
([`app.py:register_blueprints`](../../../app.py) calls
`app.register_blueprint(dashboard_bp, url_prefix="/_dashboard")`). The route
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
| [`dashboard/`](../../../dashboard) | Read-only Flask blueprint at `/_dashboard` with two GET routes: `index` and `/api/run/<run_id>` for eval results, cost cards, failure-mode heatmap. Write routes (`/api/eval/run`, `/api/tune/run`, `/api/annotation/...`) live in `blueprints/diagnostics.py` `[synthesis]`. | [`dashboard/routes.py:dashboard_bp`](../../../dashboard/routes.py), [`dashboard/routes.py:index`](../../../dashboard/routes.py), [`dashboard/routes.py:run_detail`](../../../dashboard/routes.py), [`blueprints/diagnostics.py`](../../../blueprints/diagnostics.py) |
| [`ui_pages/`](../../../ui_pages/) | Framework-free Page Object Model for the wizard UI — shared navigation + selectors, `base_url` injected. Single source of truth for both `tests/ux/` (the Playwright UX tier) and `scripts/capture_screenshots.py`; redesign-resilient by construction (selectors centralized in `ui_pages/selectors.py`, anchored to stable IDs/ARIA roles, never styling-only CSS classes). One POM per surface: `BasePage` + `CorpusPage`, `DashboardConsolePage`, `PipelinePage`, `PriorAppsPage`, `UserPickerPage`, and the six `Wizard*Page` classes. | [`ui_pages/base.py:BasePage`](../../../ui_pages/base.py), [`ui_pages/__init__.py`](../../../ui_pages/__init__.py) |

The harness is [[eval-harness]]; the console is [[diagnostics-console]]. Both read
production artifacts (logs, eval JSON); `ui_pages/` reads nothing production but
*drives* it through Playwright. `app.py` (the composition root) *does* import the
dashboard blueprint at
[`app.py:register_blueprints`](../../../app.py) — but the **core
resume-generation pipeline** (`analyze`→`generate`→`iterate` in `analyzer.py` +
`hardening.py`) never depends on `evals`, `dashboard`, or `ui_pages`: the arrow
is `app → eval/dashboard`, `tests/ux → ui_pages`, never
`pipeline → eval/dashboard/ui_pages` `[synthesis]`.

## Build and tooling infrastructure

| Module | Job | Anchor |
|---|---|---|
| [`scripts/gate.py`](../../../scripts/gate.py) | Unified quality gate (PX-55): the single definition of "gate green" that runs locally and in CI. **Two preflights first:** the hooksPath preflight [`scripts/gate.py:_check_hooks_path`](../../../scripts/gate.py) (item 150: refuses unless `core.hooksPath` is `.githooks`; skipped when `CI` is set), then the memory preflight [`scripts/gate.py:_check_memory_preflight`](../../../scripts/gate.py) (item 108: refuses below [`scripts/gate.py:_MEMORY_FLOOR_GB`](../../../scripts/gate.py) = 1.0 GB to prevent mid-run xdist OOM kills). It then runs in order: `ruff check .` + `ruff format --check .` + `mypy .` + `pytest -m "not ux" -n auto` (non-UX tier parallelized via pytest-xdist) + `pytest -m ux` (UX tier deliberately serial) + `work_items check`, returning the first failing step's exit code. Every run, a refusal or an interrupt included, writes `gate-result.json` in the git dir, and `python -m scripts.gate --result` checks it against the current `HEAD` and tree (item 151; [`scripts/gate.py:check_result`](../../../scripts/gate.py)). Consolidates what was scattered across `.github/workflows/ci.yml`'s `quality` job, `AGENTS.md`, and `CONTRIBUTING.md` before this module existed. | [`scripts/gate.py:_STEPS`](../../../scripts/gate.py), [`scripts/gate.py:_run_step`](../../../scripts/gate.py), [`scripts/gate.py:_check_memory_preflight`](../../../scripts/gate.py), [`scripts/gate.py:_MEMORY_FLOOR_GB`](../../../scripts/gate.py), [`scripts/gate.py:_check_hooks_path`](../../../scripts/gate.py), [`scripts/gate.py:check_result`](../../../scripts/gate.py) |
| [`scripts/work_items.py`](../../../scripts/work_items.py) | Work-item backlog validator and board generator (vendored from `spolia`); schema authoritative at [`docs/dev/work/SCHEMA.md`](../../../docs/dev/work/SCHEMA.md). Two subcommands: `check` validates every item file + confirms board freshness; `board --write` regenerates `docs/dev/work/BOARD.md`. Wired into `scripts/gate.py` as the final step. Stdlib-only. **Also carries the charter C-11 closure bar** (2026-08-05): `status = "closed"` requires a falsifiable `verified_by` artifact or an owner-named `closure_exception`, and an item carrying `resolution` while *not* closed — i.e. reopened — requires a `guardrail`. Because it runs in both `gate.py` and CI, this is the one C-11/C-12 mechanism that binds **every** agent rather than only Claude Code `[synthesis]`. | [`scripts/work_items.py:check`](../../../scripts/work_items.py), [`scripts/work_items.py:_CLOSURE_BAR_GRANDFATHERED`](../../../scripts/work_items.py) |
| [`scripts/release_version.py`](../../../scripts/release_version.py) | Version discipline enforcement (charter D-7): ensures git tag (semver 2.0.0) and `pyproject.toml` version (PEP 440) agree after normalization. Codifies the sanctioned ladder (`alpha.N < beta.N < rc.N < final`) — a deliberate SUBSET of semver that stays compatible with pip's ordering. | [`scripts/release_version.py:SEMVER_RE`](../../../scripts/release_version.py), [`scripts/release_version.py:_PEP440_RUNG`](../../../scripts/release_version.py) |
| [`scripts/project_docs_to_mdx.py`](../../../scripts/project_docs_to_mdx.py) | Deterministic L1→Fumadocs MDX projection adapter (stdlib-only, no LLM). Projects only docs registered in `scripts/doc_registry.py:PUBLISHED` to `docs-site/content/docs/`, parsing their `**Purpose:** / **Audience:** / **Authoritative for:**` headers into MDX frontmatter and ordering pages by registry entry order within each tier. Stamps each projected page's `sourceCommit` via [`scripts/project_docs_to_mdx.py:source_commit`](../../../scripts/project_docs_to_mdx.py) (the commit it was projected from, with `+uncommitted` if sources have local edits) and points local images at their copied `./screenshots/` directory via [`scripts/project_docs_to_mdx.py:rewrite_local_images`](../../../scripts/project_docs_to_mdx.py). | [`scripts/project_docs_to_mdx.py:collect_pages`](../../../scripts/project_docs_to_mdx.py), [`scripts/project_docs_to_mdx.py:build_meta_pages_order`](../../../scripts/project_docs_to_mdx.py), [`scripts/project_docs_to_mdx.py:source_commit`](../../../scripts/project_docs_to_mdx.py), [`scripts/project_docs_to_mdx.py:rewrite_local_images`](../../../scripts/project_docs_to_mdx.py) |
| [`scripts/doc_registry.py`](../../../scripts/doc_registry.py) | The single definition of which docs the site publishes: its `PUBLISHED` tuple is the registry that `project_docs_to_mdx.py` projects, and `RECORD_PREFIXES` defines which paths are frozen records (handoffs, diagnosis, reviews) never published. Data-only, stdlib-only, no I/O at import. | [`scripts/doc_registry.py:PUBLISHED`](../../../scripts/doc_registry.py), [`scripts/doc_registry.py:RECORD_PREFIXES`](../../../scripts/doc_registry.py) |
| [`scripts/doc_corpus.py`](../../../scripts/doc_corpus.py) | The shared doc corpus — tracked paths, file text, and unfenced lines, each computed once. The one shared pass over all registered docs (instead of one scan per lint), feeding [`scripts/doc_lints.py`](../../../scripts/doc_lints.py) and the check-doc-links family. Lazy by default: nothing is listed or read at construction; each property is computed on first use and cached. Link targets are resolved lexically via `posixpath.normpath` over the tracked set; deleted-but-indexed files are filtered. Stdlib only, no I/O at import. | [`scripts/doc_corpus.py`](../../../scripts/doc_corpus.py) |
| [`scripts/doc_lints.py`](../../../scripts/doc_lints.py) | The §5 doc lints (`docs/dev/docs-ia-design.md` §5, rows 5.3–5.9 [synthesis]), over the shared corpus — each lint is one function `(corpus) -> list[Finding]`; a finding is a **block** (fails the gate) or a **warn** (printed, never fails). Gated by `tests/test_doc_lints.py`, which runs every lint on the real tree and gives each one a seeded violation it must catch `[synthesis]`. The lints ride the gate (`python -m scripts.gate`, the `pytest -m "not ux"` step) without adding a dedicated step. | [`scripts/doc_lints.py`](../../../scripts/doc_lints.py) |
| [`scripts/check_docs_site_mermaid.py`](../../../scripts/check_docs_site_mermaid.py) | Check the built docs site in a real browser: every diagram renders, every local image loads. Serves the static export on a loopback port, loads every published page in headless Chromium, waits until no diagram is still `data-mermaid="pending"`, and fails if a page has a `failed` diagram, or fewer `ok` diagrams than its source doc has ```mermaid fences, or a same-origin `<img>` whose URL doesn't return 200 `[synthesis]`. External images (badges) aren't checked. Wired into `.github/workflows/docs-deploy.yml`. | [`scripts/check_docs_site_mermaid.py`](../../../scripts/check_docs_site_mermaid.py) |
| [`scripts/check_docs_projection_fresh.py`](../../../scripts/check_docs_projection_fresh.py) | Is the local docs-site projection current? (item 126). Each projected page carries `sourceCommit` (the commit it was projected from, with `+uncommitted` if sources have local edits). Compares the stamps to HEAD; fails if pages are stale, unstamped (projected before item 126), or mixed. Solves the risk that a local copy can be months old and still look like the live site. | [`scripts/check_docs_projection_fresh.py`](../../../scripts/check_docs_projection_fresh.py) |
| [`scripts/ci_wait.py`](../../../scripts/ci_wait.py) | The single definition of "the PR is green" — `scripts/gate.py`'s sibling for the other half of close-out, named by [`docs/dev/maintainer-lane.md`](../../dev/maintainer-lane.md) step 4 which forbids hand-rolled watchers. Wraps `gh pr checks --watch --required --fail-fast`. It takes "required" from the base branch's **protection contexts**, not from whatever checks have registered: an unregistered protected context counts as pending, and it re-enters the watch until the deadline. An unreadable protection rule exits `2`, never green (item 109). It partitions required from advisory checks, prints a failing job's `--log-failed` tail, and scans the required runs' logs for the `ux` tier's existing rerun-rate alarm so **green-after-retries cannot read as green** (charter C-7 rule 3): exit `3` for that case, distinct from `0`. Prints exactly one terminal verdict line from a `finally` block — a silent watcher reporting health while a check was red is the failure it was built to remove. | [`scripts/ci_wait.py:classify`](../../../scripts/ci_wait.py), [`scripts/ci_wait.py:scan_reruns`](../../../scripts/ci_wait.py) |

The gate and release scripts are invoked by CI; `project_docs_to_mdx.py` is a manual build step for the documentation site; `ci_wait.py` is an agent/maintainer tool that *reads* CI rather than running inside it. None of these scripts depend on the production pipeline — the arrow is `CI → scripts`, never `pipeline → scripts` `[synthesis]`.

## Related

- [`overview`](../overview.md) — the front door this map sits under.
- [[engineering-workstreams]] — WS-1 (the `app.py`→blueprints split) **shipped** (Sprint 8.3a–h); this inventory is the split's post-state, not the pre-split gap anymore.
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
- [[route-surface]] — the `blueprints/` route inventory + the `web_infra/` security gate.
- [[openapi-api-reference]] — `web_infra/openapi.py`'s `spec` instance in depth.
- [[frontend-wizard]] — `static/app.js` + `templates/index.html`.
- [[document-rendering]] — `generator.py` / `pdf_render.py` / the JSON Resume intermediate.
- [[machine-capability-preflight]] — `preflight.py`.
- [[eval-harness]] — `evals/runner.py`.
- [[diagnostics-console]] — the `/_dashboard` blueprint + `blueprints/diagnostics.py`.
- [[docs-information-architecture]] — what the docs-toolchain scripts above are for.
