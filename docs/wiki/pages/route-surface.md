# The Flask route surface

> **Audience:** `dev`
> **Concept:** the HTTP surface, now spread across eight `blueprints/` modules
> (one a 7-submodule sub-package) — the mandatory security gate every
> filesystem route shares (now centralized in `web_infra/security.py`), and
> the four route families it carries (wizard, composition, the B.4/B.5
> corpus-completer routes, the applications tracker).
> **Sources:** [`blueprints/`](../../../blueprints/),
> [`web_infra/security.py`](../../../web_infra/security.py),
> [`app.py`](../../../app.py),
> [`docs/architecture.md` §Module map](../../architecture.md),
> [`scripts/enforcement/guards/route_security_lint.py`](../../../scripts/enforcement/guards/route_security_lint.py).
> **Grounding:** per [`SCHEMA.md`](../SCHEMA.md); conclusions tagged `[synthesis]`.

---

The route surface is no longer one file. Sprint 8.3a–h (the WS-1
monolith-to-blueprints split, see [[engineering-workstreams]]) moved every
`@app.route` off `app.py` onto eight domain blueprints under
[`blueprints/`](../../../blueprints/) — `analysis.py`, `generation.py`,
`corpus/` (a 7-submodule sub-package), `templates.py`, `applications.py`,
`users.py`, `diagnostics.py`, `assistant.py` — plus the pre-existing read-only
`dashboard/` blueprint. At HEAD, `app.py` is a ~296-line composition root
(`create_app()` factory + `register_blueprints()` + `main()`) carrying **zero**
`@app.route` decorators [`app.py`](../../../app.py); the route count that used
to live in one file (93 at the walk's 2026-06-07 reading) is now **117**
`@<bp>.route` decorators spread across the nine blueprint modules
`[synthesis]`. The seven blueprints that moved out of the monolith
(analysis/generation/corpus/templates/applications/users/diagnostics) register
with **no** `url_prefix`, so every URL they carry stays byte-identical to the
monolith; `assistant_bp` (`/api/assistant`) and `dashboard_bp` (`/_dashboard`)
predate the split and keep their own prefixes
([`app.py:register_blueprints`](../../../app.py)) — see [[code-module-map]] for
the full per-blueprint inventory.

## The security gate (mandatory, enforced) — now centralized in `web_infra`

Every route that reaches the filesystem runs the same trio. The canonical statement
of *why* lives in [`AGENTS.md` §Key patterns / Security](../../../AGENTS.md) and
[`docs/architecture.md` §Security model](../../architecture.md) — cited here, not
restated (design fork D5). The guards themselves moved out of `app.py` (Sprint
8.3a) into the leaf package `web_infra/` so `app.py` and every blueprint share
one definition instead of each carrying (or re-inlining) a copy — `web_infra/`
is asserted never to import `app.py`, any blueprint, or `config.py`
([`web_infra/__init__.py`](../../../web_infra/__init__.py) docstring):

- [`web_infra/security.py:_safe_username`](../../../web_infra/security.py) —
  `secure_filename`-strips traversal, then confirms `<configs_dir>/<user>.config`
  exists; returns `None` for invalid/unknown users. Takes `configs_dir` as an
  explicit keyword-only arg (not a module global) — the seam that lets a test
  call it with a `tmp_path`, no Flask app context; blueprints pass
  `current_app.config["CONFIGS_DIR"]` at the call site `[synthesis]`.
- [`web_infra/security.py:_within`](../../../web_infra/security.py) — resolves a
  request-sourced path and confirms it is a child of a parent dir
  (`.resolve().relative_to(...)`), `False` on `ValueError`. Pure (path + parent
  args only), unchanged in shape from the pre-split version.
- `secure_filename` (werkzeug, imported at
  [`web_infra/security.py`](../../../web_infra/security.py)) — strips traversal
  from any filename before it joins a path.

This is uniform **because a hook guards it**, and the hook's scope widened with
the split (PX-21): [`route_security_lint.py`](../../../scripts/enforcement/guards/route_security_lint.py)
(run via `hooks/edit-write-dispatcher.sh` since PX-37) now runs on an `Edit`/`Write` to
**`app.py` OR any `blueprints/**.py`** module
that adds or modifies a route touching the filesystem (detected by
`open(`/`send_file(`/`Path(`/`OUTPUT_DIR`/etc.) unless **both** `_safe_username`
and `_within` appear in the same content; the read-only `dashboard/` surface is
deliberately excluded (localhost-gated, no `<username>`, fixed diagnostic dirs —
see [[diagnostics-console]]). A committed whole-tree gate,
[`tests/test_route_containment_gate.py`](../../../tests/test_route_containment_gate.py)
(PX-29), backstops the hook with an AST-based do-not-regress assertion across
the blueprint tree. So "consistency tracks enforcement" applies literally to
this surface ([[consistency-tracks-enforcement]]). The download route
[`blueprints/generation.py:download_file`](../../../blueprints/generation.py)
(`GET /api/download/<path:filepath>`) now **calls the canonical `_within` helper
directly** rather than inlining an equivalent check — the pre-split page noted an
older inline idiom here; that idiom is gone `[synthesis]`. The PX-02 opt-in
scrape route [`blueprints/users.py:fetch_profile`](../../../blueprints/users.py)
(`POST /api/users/<username>/profile/fetch`) runs the same gate — `_safe_username`,
then a defensive `_within(config_path, configs_dir)` on the user's `.config`
file — before reading the saved URLs and scraping them via the deterministic
[`scraper.fetch_profile_content`](../../../scraper.py) (no network library
imported here — egress lives in `scraper.py`, on the PX-08 allowlist), caching
the result into `Candidate.online_profile_text` (see [[corpus-data-model]])
`[synthesis]`.

DB-only routes (no request-sourced path) drop `_within` but still validate
ownership via `_safe_username` — e.g.
[`blueprints/applications.py:update_application_status`](../../../blueprints/applications.py)
loads the candidate and rejects with 403 if `_safe_username(candidate.username, …)`
is falsy. Routes acting on an `application_id` centralize this in
[`blueprints/applications.py:_load_application_owned`](../../../blueprints/applications.py),
which returns `(None, None)` unless the owning candidate passes `_safe_username`
`[synthesis]`.

## Wizard routes (the generate pipeline) — `blueprints/analysis.py` + `blueprints/generation.py`

The pipeline stages are driven by a POST per stage (see [[pipeline-stages]] for the
sequence). Each gates on `_safe_username` at entry:

- [`blueprints/analysis.py:run_analysis`](../../../blueprints/analysis.py)
  (`POST /api/analyze`) — P8 human gate #1; reads the DB corpus, 400s on invalid
  user, delegates to `_run_analysis_corpus_backed`.
- [`blueprints/analysis.py:run_analysis_stream`](../../../blueprints/analysis.py)
  (`POST /api/analyze/stream`), plus `run_clarify` (`/api/clarify`),
  `submit_clarifications` (`/api/answer-clarifications`), and
  `run_iterate_clarify` (`/api/iterate-clarify`) — all five analysis-family routes
  live in [`blueprints/analysis.py`](../../../blueprints/analysis.py) (Sprint
  8.3b, the first domain seam extracted from `app.py`).
- [`blueprints/generation.py`](../../../blueprints/generation.py) (Sprint 8.3c) —
  `POST /api/save-edits`, `POST /api/generate` +
  `POST /api/generate/stream`, `POST /api/validate-refinement`,
  `POST /api/generate-cover-letter`, `GET /api/download/<path:filepath>`
  (`download_file`), `POST /api/download-edited`.

These call into `analyzer.py`; the blueprints themselves stay request glue,
reading paths from `current_app.config` rather than a module global — the
deterministic/LLM boundary is owned elsewhere (see
[[deterministic-llm-boundary]]).

## Composition (the Compose step) — `blueprints/applications.py`

A GET/POST pair on the application's context file:

- [`blueprints/applications.py:get_application_composition`](../../../blueprints/applications.py)
  (`GET /api/applications/<id>/composition`) — fit-ranks bullets + eligible titles
  via `score_corpus_bullet`, reading pin/exclude/added/summary/title overrides out
  of the context file named by the `context_path` query param (validated with
  `_within(cp, current_app.config["OUTPUT_DIR"])`).
- [`blueprints/applications.py:save_application_composition`](../../../blueprints/applications.py)
  (`POST /api/applications/<id>/composition`) — persists `{context_path, pinned[],
  excluded[], added[], bullet_order, pinned_summary_id, pinned_title_ids}` back into
  the context file in place. The handler **rebuilds `composition_overrides`
  wholesale**, so the debounced autosave sends the full state each time
  `[synthesis]` — this is the clobber surface tracked in the compose memory.
  Ownership rides `_load_application_owned`; `_within` gates `context_path`.

## Corpus-completer routes (Sprint 6.6 B.4 / B.5) — `blueprints/applications.py`

Fired from the Compose step; each takes `{context_path}`, validates it with
`_within(cp, current_app.config["OUTPUT_DIR"])`, checks `ctx["application_id"]`
matches, runs one Haiku call, and writes the result back into the context file —
all three now live alongside the composition routes in
[`blueprints/applications.py`](../../../blueprints/applications.py) (Sprint 8.3f):

- [`blueprints/applications.py:recommend_application_experience_summaries`](../../../blueprints/applications.py)
  (`POST /api/applications/<id>/recommend-experience-summaries`, B.4) — picks the
  best per-role intro variant, batched; persists
  `llm_experience_summary_recommendations`. Short-circuits with no LLM call when
  no role has 2+ active variants. Suggests only — nothing auto-applies.
- [`blueprints/applications.py:recommend_application_skills`](../../../blueprints/applications.py)
  (`POST /api/applications/<id>/recommend-skills`, B.5) — orders/curates the
  candidate's **active, approved** skills (`is_active=1, is_pending_review=0`);
  persists `llm_skill_recommendations`. Pending/inactive skills can never be
  recommended.
- [`blueprints/applications.py:suggest_application_skills`](../../../blueprints/applications.py)
  (`POST /api/applications/<id>/suggest-skills`, B.5) — proposes NEW skills
  grounded in JD ∩ corpus, inserting each as a **pending** Skill
  (`source="llm_proposed"`, `is_pending_review=1`). Pending skills never reach the
  recommend set, the preview, or the generate prompt until a human approves — the
  approve/deny gate is the grounding backstop `[synthesis]` (see [[corpus-to-output-reach]]).

A corpus-wide variant, [`blueprints/corpus/skills.py:suggest_skills_from_corpus_route`](../../../blueprints/corpus/skills.py)
(`POST /api/users/<u>/skills/suggest-from-corpus`, owner feature ask F-02), runs
the same machinery independent of a JD so candidates can populate skills before
starting applications — evidence-only gate (no JD ∩ corpus AND), persisting as pending
Skills identical to the per-application route `[synthesis]`.

Corpus CRUD (the curation surface these read) moved to its own sub-package,
[`blueprints/corpus/`](../../../blueprints/corpus/) — a single
`corpus_bp = Blueprint("corpus", __name__)`
([`blueprints/corpus/_bp.py`](../../../blueprints/corpus/_bp.py)) that seven route
submodules attach to: `experiences.py` (experiences + bullets + titles +
experience-summaries), `summaries.py`, `skills.py` — e.g.
[`blueprints/corpus/skills.py:create_skill`](../../../blueprints/corpus/skills.py)
(`POST /api/users/<u>/skills`) — `career_assets.py` (education + certifications),
`tags.py` (tag suggest + link/unlink — `_link_tag_route` / `_unlink_tag_route`,
e.g. [`blueprints/corpus/tags.py:link_bullet_tag`](../../../blueprints/corpus/tags.py)
and siblings for title/skill), `curation.py` (upload + list-résumés + duplicates +
ingest + accept), and `proposals.py` (critique / decide / promote-to-bullet — the
only corpus submodule on the `anthropic` egress allowlist). Cross-cutting
serializers (`_skill_to_dict`, `_tag_list`) live in
[`blueprints/corpus/_shared.py`](../../../blueprints/corpus/_shared.py) and are
re-exported for `blueprints/applications.py` to import `[synthesis]`.

## Applications tracker — `blueprints/applications.py`

The lifecycle layer over generated applications:

- [`blueprints/applications.py:list_applications`](../../../blueprints/applications.py)
  (`GET /api/users/<u>/applications`) — newest-first, optional `?status=` filter
  validated against `_VALID_APP_STATUSES` (unknown → 400); returns
  `{applications:[], needs_onboarding:true}` when the user has no candidate row.
- [`blueprints/applications.py:get_application`](../../../blueprints/applications.py)
  (`GET /api/applications/<id>`) — full detail: metadata + runs + pending-proposal
  counts.
- [`blueprints/applications.py:update_application_status`](../../../blueprints/applications.py)
  / `update_application_notes` / `update_application_meta` (PUT) — status stamps
  `sent_at` / `outcome_at` on the right transitions; all three are DB-only and
  ownership-gated.

The status/run history these expose is the application audit trail (see
[[application-audit-chain]]).

## OpenAPI spec emission on five GET routes (spectree Layer B)

Five read-only `GET` routes across three blueprint files —
`users.list_users` + `users.get_config`
([`blueprints/users.py`](../../../blueprints/users.py)),
`corpus.experiences.list_experiences`
([`blueprints/corpus/experiences.py`](../../../blueprints/corpus/experiences.py)),
and `applications.list_applications` + `applications.get_application`
(above) — additionally carry an `@spec.validate(resp=..., skip_validation=True,
tags=[...])` decorator against the shared `web_infra/openapi.py:spec`
instance. `skip_validation=True` means this is documentation-only: the
routes' request handling, security gate, and response bodies are unchanged
`[synthesis]`. See [[openapi-api-reference]] for the full treatment (the
response models, the `mode="strict"` scoping, and the
`scripts/generate_openapi_spec.py` generator this decoration feeds).

## Other blueprints (not re-catalogued here)

Three more domain blueprints round out the nine-module surface; each has its own
wiki treatment or is a small enough seam not to need a dedicated route-by-route
section on this page — see [[code-module-map]] for the full per-blueprint
inventory:

- [`blueprints/templates.py`](../../../blueprints/templates.py) (Sprint 8.3e) —
  persona-template + live-preview routes; the canonical home of the
  `_resolve_persona_*` resolvers `generation.py` imports.
- [`blueprints/users.py`](../../../blueprints/users.py) (Sprint 8.3g) — the SPA
  shell (`GET /`) + user/config CRUD + `fetch_profile` (above).
- [`blueprints/diagnostics.py`](../../../blueprints/diagnostics.py) (Sprint
  8.3h, the last seam) — annotation/bootstrap/eval/tune, incl. the SSE
  self-tuning loop; see [[diagnostics-console]].
- [`blueprints/assistant.py`](../../../blueprints/assistant.py) — the one-route
  doc-grounded-assistant seam (`POST /api/assistant/ask`), the first blueprint to
  exist (Sprint 7.5, predates the WS-1 split).

## Related

- [[code-module-map]] — where `blueprints/` and `web_infra/` sit among the modules.
- [[engineering-workstreams]] — WS-1, the monolith-to-blueprints split this page now reflects.
- [[pipeline-stages]] — the stage sequence the wizard routes drive.
- [[frontend-wizard]] — the client that calls this surface.
- [[corpus-to-output-reach]] — how the B.4/B.5 routes feed the generate prompt.
- [[application-audit-chain]] — the runs/status history behind the tracker routes.
- [[diagnostics-console]] — the diagnostics blueprint's SSE write surface.
- [[consistency-tracks-enforcement]] — why the security gate is uniform (the hook).
- [[openapi-api-reference]] — the spectree OpenAPI decoration on five of these GET routes.
