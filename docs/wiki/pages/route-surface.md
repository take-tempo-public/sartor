# The Flask route surface

> **Audience:** `dev`
> **Concept:** the one-file HTTP surface in `app.py` — the mandatory security gate
> every filesystem route shares, and the four route families it carries (wizard,
> composition, the B.4/B.5 corpus-completer routes, the applications tracker).
> **Sources:** [`app.py`](../../../app.py), [`docs/architecture.md` §Security model](../../architecture.md),
> [`.claude-plugin/hooks/route-security-lint.sh`](../../../.claude-plugin/hooks/route-security-lint.sh).
> **Grounding:** per [`SCHEMA.md`](../SCHEMA.md); conclusions tagged `[synthesis]`.

---

The web app is a single Flask module: `app.py` holds over 90 routes (92 `@app.route`
decorators at HEAD) plus the security helpers and request/response glue, and the
dashboard blueprint mounts more on top
`[synthesis]` (the architecture map lists `app.py` as "Flask routes, security
helpers, request/response glue", see [`docs/architecture.md` modules table](../../architecture.md)).
That monolith size — one file, all routes — is the WS-1 navigability cost named in
[[consistency-tracks-enforcement]]; it is a known gap, not an accident `[synthesis]`.

## The security gate (mandatory, enforced)

Every route that reaches the filesystem runs the same trio. The canonical statement
of *why* lives in [`AGENTS.md` §Key patterns / Security](../../../AGENTS.md) and
[`docs/architecture.md` §Security model](../../architecture.md) — cited here, not
restated (design fork D5). The shape:

- [`app.py:_safe_username`](../../../app.py) — `secure_filename`-strips traversal,
  then confirms `configs/<user>.config` exists; returns `None` for invalid/unknown
  users.
- [`app.py:_within`](../../../app.py) — resolves a request-sourced path and confirms
  it is a child of a parent dir (`.resolve().relative_to(...)`), `False` on `ValueError`.
- `secure_filename` (werkzeug, imported at [`app.py`](../../../app.py)) — strips
  traversal from any filename before it joins a path.

This is uniform **because a hook guards it**: [`route-security-lint.sh`](../../../.claude-plugin/hooks/route-security-lint.sh)
blocks an `Edit`/`Write` to `app.py` that adds a `@app.route` touching the filesystem
(detected by `open(`/`send_file(`/`Path(`/`OUTPUT_DIR`/etc.) unless **both**
`_safe_username` and `_within` appear in the same content `[synthesis]`. So
"consistency tracks enforcement" applies literally to this surface
([[consistency-tracks-enforcement]]). The legacy [`app.py:download_file`](../../../app.py)
inlines the `_within` check rather than calling the helper — same containment, older
idiom `[synthesis]`.

DB-only routes (no request-sourced path) drop `_within` but still validate ownership
via `_safe_username` — e.g. [`app.py:update_application_status`](../../../app.py) loads
the candidate and rejects with 403 if `_safe_username(candidate.username)` is falsy.
Routes acting on an `application_id` centralize this in
[`app.py:_load_application_owned`](../../../app.py), which returns `(None, None)` unless
the owning candidate passes `_safe_username` `[synthesis]`.

## Wizard routes (the generate pipeline)

The pipeline stages are driven by a POST per stage (see [[pipeline-stages]] for the
sequence). Each gates on `_safe_username` at entry:

- [`app.py:run_analysis`](../../../app.py) (`/api/analyze`) — P8 human gate #1; reads
  the DB corpus, 400s on invalid user, delegates to `_run_analysis_corpus_backed`.
- `/api/analyze/stream`, `/api/clarify`, `/api/answer-clarifications`,
  `/api/iterate-clarify`, `/api/save-edits`, `/api/generate` + `/api/generate/stream`,
  `/api/generate-cover-letter` — the staged wizard surface, all in
  [`app.py`](../../../app.py).

These call into `analyzer.py`; `app.py` itself stays request glue — the
deterministic/LLM boundary is owned elsewhere (see [[deterministic-llm-boundary]]).

## Composition (the Compose step)

A GET/POST pair on the application's context file:

- [`app.py:get_application_composition`](../../../app.py) (GET) — fit-ranks bullets +
  eligible titles via `score_corpus_bullet`, reading pin/exclude/added/summary/title
  overrides out of the context file named by the `context_path` query param (validated
  with `_within(cp, OUTPUT_DIR)`).
- [`app.py:save_application_composition`](../../../app.py) (POST) — persists
  `{context_path, pinned[], excluded[], added[], bullet_order, pinned_summary_id,
  pinned_title_ids}` back into the context file in place. The handler **rebuilds
  `composition_overrides` wholesale**, so the debounced autosave sends the full state
  each time `[synthesis]` — this is the clobber surface tracked in the compose memory.
  Ownership rides `_load_application_owned`; `_within` gates `context_path`.

## Corpus-completer routes (Sprint 6.6 B.4 / B.5)

Fired from the Compose step; each takes `{context_path}`, validates it with
`_within(cp, OUTPUT_DIR)`, checks `ctx["application_id"]` matches, runs one Haiku call,
and writes the result back into the context file:

- [`app.py:recommend_application_experience_summaries`](../../../app.py)
  (`/recommend-experience-summaries`, B.4) — picks the best per-role intro variant,
  batched; persists `llm_experience_summary_recommendations`. Short-circuits with no
  LLM call when no role has 2+ active variants. Suggests only — nothing auto-applies.
- [`app.py:recommend_application_skills`](../../../app.py) (`/recommend-skills`, B.5) —
  orders/curates the candidate's **active, approved** skills (`is_active=1,
  is_pending_review=0`); persists `llm_skill_recommendations`. Pending/inactive skills
  can never be recommended.
- [`app.py:suggest_application_skills`](../../../app.py) (`/suggest-skills`, B.5) —
  proposes NEW skills grounded in JD ∩ corpus, inserting each as a **pending** Skill
  (`source="llm_proposed"`, `is_pending_review=1`). Pending skills never reach the
  recommend set, the preview, or the generate prompt until a human approves — the
  approve/deny gate is the grounding backstop `[synthesis]` (see [[corpus-to-output-reach]]).

Corpus CRUD (the curation surface these read) sits in the same file: experiences,
bullets, summaries, skills, experience-summaries, titles — e.g.
[`app.py:create_skill`](../../../app.py) (`/api/users/<u>/skills`) — plus tag
link/unlink endpoints that all funnel through `_link_tag_route` /`_unlink_tag_route`
([`app.py:link_bullet_tag`](../../../app.py) and siblings for title/skill).

## Applications tracker

The lifecycle layer over generated applications:

- [`app.py:list_applications`](../../../app.py) (`/api/users/<u>/applications`) —
  newest-first, optional `?status=` filter validated against `_VALID_APP_STATUSES`
  (unknown → 400); returns `{applications:[], needs_onboarding:true}` when the user has
  no candidate row.
- [`app.py:get_application`](../../../app.py) — full detail: metadata + runs + pending-
  proposal counts.
- [`app.py:update_application_status`](../../../app.py) /
  [`update_application_notes`](../../../app.py) /
  [`update_application_meta`](../../../app.py) (PUT) — status stamps `sent_at` /
  `outcome_at` on the right transitions; all three are DB-only and ownership-gated.

The status/run history these expose is the application audit trail (see
[[application-audit-chain]]).

## Related

- [[code-module-map]] — where `app.py` sits among the modules.
- [[pipeline-stages]] — the stage sequence the wizard routes drive.
- [[frontend-wizard]] — the client that calls this surface.
- [[corpus-to-output-reach]] — how the B.4/B.5 routes feed the generate prompt.
- [[application-audit-chain]] — the runs/status history behind the tracker routes.
- [[consistency-tracks-enforcement]] — why the security gate is uniform (the hook).
