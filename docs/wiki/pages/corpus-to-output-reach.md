# Corpus-to-output reach

> **Audience:** `dev`
> **Concept:** how a user's curation in Compose reaches the deliverable — the
> corpus→JSON Resume build, the `composition_overrides` shape (pins / exclusions /
> ordering across bullets, titles, summaries, role intros, skills), and the
> shared resolver that keeps the live preview and the generated download in
> agreement.
> **Sources:** [`corpus_to_json_resume.py`](../../../corpus_to_json_resume.py),
> [`db/build_context.py`](../../../db/build_context.py),
> [`app.py`](../../../app.py) (the `/api/applications/<id>/composition` GET+POST
> handlers, `_apply_recommended_skills`).
> **Grounding:** per [`SCHEMA.md`](../SCHEMA.md); conclusions tagged `[synthesis]`.

---

## Two reach paths, one resolver

A user's curation reaches two distinct deliverables, and the design's central
move is that both consume the *same* `composition_overrides` block off the same
context file so the on-screen preview matches the generated download `[synthesis]`:

1. **Live preview / PDF** — deterministic. [`build_json_resume_from_corpus`](../../../corpus_to_json_resume.py)
   reads the DB *live*, applies the overrides, and emits a JSON Resume v1.0 dict.
   Called from the preview route, where the corpus-direct build only runs once
   `llm_recommendations` exist on the context (else a placeholder is served)
   ([`app.py`](../../../app.py), preview handler).
2. **Generated download** — the curation is folded into `context_set` *before the
   LLM sees it*, via in-memory patches at generate time:
   `_apply_chosen_summary`, `_apply_chosen_experience_summaries`, and
   [`_apply_recommended_skills`](../../../app.py) ([`app.py`](../../../app.py)).

The skill curation in both paths routes through one pure function,
[`resolve_skill_selection`](../../../corpus_to_json_resume.py) — shared by the
preview's [`_collect_skills`](../../../corpus_to_json_resume.py), the generate-time
`_apply_recommended_skills`, and the Compose GET handler — so all three agree
exactly on the effective ordered skill set `[synthesis]`.

## The `composition_overrides` shape

The block lives under `composition_overrides` on the context file. The
authoritative producer is the POST `/api/applications/<id>/composition` handler,
which **rebuilds the whole block wholesale on every save** — so the debounced
autosave must send the full composition state each time, or an omitted field is
dropped ([`app.py`](../../../app.py), `save_application_composition`) `[synthesis]`.
Verified keys (each persisted only when non-empty, keeping the default path
byte-identical):

| Key | Shape | Governs |
|---|---|---|
| `pinned` / `excluded` / `added` | `[bullet_id]` | bullet inclusion |
| `bullet_order` | `{experience_id: [bullet_id]}` | per-role bullet order |
| `pinned_title_ids` | `{experience_id: title_id}` | per-role title pick |
| `pinned_summary_id` | `int` | candidate summary variant pin |
| `use_experience_summaries` | `bool` | "Add role intros" opt-in toggle |
| `chosen_experience_summary_ids` | `{experience_id: item_id}` | per-role intro pick |
| `pinned_skill_ids` / `excluded_skill_ids` | `[skill_id]` | skill pin / drop |
| `skill_order` | `[skill_id]` | explicit skill ranking |

JSON persists object keys as strings, so every reader coerces keys + ids back to
`int` and skips malformed entries rather than failing (see `_read_*` helpers in
[`corpus_to_json_resume.py`](../../../corpus_to_json_resume.py) and the
OUTPUT_DIR-gated `_read_*_overrides` mirrors in [`app.py`](../../../app.py)).

## How each override resolves into work[] / skills[] / basics

Inside `build_json_resume_from_corpus`:

- **Summary** ([`_resolve_chosen_summary_text`](../../../corpus_to_json_resume.py)):
  priority chain `pinned > recommended > first-active SummaryItem >
  Candidate.profile_text`, reporting a `summary_source` of
  `pinned|recommended|first_active|candidate_default|none`.
- **Title** per role: `_pinned_title_text` (the user's pick, only while still
  `is_official OR truthful_enough_to_use`) `→ _official_title_text →
  _first_title_text` ([`corpus_to_json_resume.py`](../../../corpus_to_json_resume.py)).
- **Role intro** ([`_resolve_chosen_experience_summary_text`](../../../corpus_to_json_resume.py)):
  strictly opt-in — `work[].summary` is emitted *only* when the toggle is on AND
  the role has an explicit pick; there is deliberately **no** fallback to the
  legacy `Experience.summary` (it survives as a backfilled variant, surfaced only
  when chosen).
- **Bullets**: active bullets sorted by `(display_order, id)`, then the effective
  set is `(recommended ∪ added ∪ pinned) − excluded`; with no
  `llm_recommendations` for that experience it degrades to all-active-minus-excluded
  ([`corpus_to_json_resume.py`](../../../corpus_to_json_resume.py)).
- **Skills** ([`_collect_skills`](../../../corpus_to_json_resume.py)): the universe
  is the candidate's `is_active=1, is_pending_review=0` Skill rows in display
  order — pending and retired skills can never appear — then
  `resolve_skill_selection` seeds from the recommendation ids (or all-active when
  none), appends pinned-not-present, drops excluded, and applies `skill_order` as
  a stable ranking. An empty/degenerate recommendation maps to `None` so it never
  blanks the section.

sartor-specific resolution state (`chosen_summary_id`, `summary_source`,
`use_experience_summaries`, `skill_curation_active`, …) is stamped under
`meta.sartor.*` so standard JSON Resume themes ignore it.

## Where the curated context_set comes from

The context the overrides decorate is built by
[`build_context_set_from_db`](../../../db/build_context.py): it projects the
candidate's DB rows into a `ContextSet` whose shape matches the legacy
file-based one, synthesizes a markdown résumé for the prompt, and creates the
`Application` + `ApplicationRun` audit anchors. The structured `career_corpus`
payload it emits is the *frozen snapshot* the generate prompt reads — so a title
pinned in Compose *after* analyze is re-synced into `eligible_titles` for exactly
the pinned experiences by the POST handler (the live-DB preview is unaffected)
([`app.py`](../../../app.py), `save_application_composition`).

The deterministic/LLM boundary (`corpus_to_json_resume.py` and `build_context.py`
take no LLM calls) and the route security gate are canonical in
[`AGENTS.md`](../../../AGENTS.md) — referenced, not restated here (D5).

## Related

- [[corpus-data-model]] — the Candidate / Experience / Bullet / SummaryItem rows this reads.
- [[document-rendering]] — how the JSON Resume dict becomes HTML / PDF / docx.
- [[code-module-map]] — where `corpus_to_json_resume` / `build_context` sit in the module graph.
- [[route-surface]] — the `/api/applications/<id>/composition` GET+POST + preview routes.
- [[frontend-wizard]] — the Compose UI whose `_collectCompositionState()` produces the override payload.
