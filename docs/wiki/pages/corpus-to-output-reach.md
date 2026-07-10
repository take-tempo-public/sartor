# Corpus-to-output reach

> **Audience:** `dev`
> **Concept:** how a user's curation in Compose reaches the deliverable — the
> corpus→JSON Resume build, the `composition_overrides` shape (pins / exclusions /
> ordering across bullets, titles, summaries, role intros, skills), the
> **frozen `approved_composition`** snapshot (Generation-experience
> re-architecture Phase 4), and the shared resolver that keeps the live
> preview, the deterministic assemble, and the generated download in
> agreement.
> **Sources:** [`corpus_to_json_resume.py`](../../../corpus_to_json_resume.py),
> [`db/build_context.py`](../../../db/build_context.py),
> [`blueprints/applications.py`](../../../blueprints/applications.py) (the
> `/api/applications/<id>/composition` GET+POST handlers; `_apply_recommended_skills`
> itself lives in `blueprints/generation.py`),
> [`blueprints/generation.py`](../../../blueprints/generation.py) (`_frozen_composition`,
> `_assemble_from_frozen_composition`), [`blueprints/templates.py`](../../../blueprints/templates.py)
> (`preview_application_html`).
> **Grounding:** per [`SCHEMA.md`](../SCHEMA.md); conclusions tagged `[synthesis]`.

---

## Three reach paths, one resolver

A user's curation reaches three distinct deliverables now — preview, the
deterministic frozen assemble, and the legacy LLM-apply generate — and the
design's central move throughout is that everything consumes the *same*
`composition_overrides` (or, once frozen, the *same* `approved_composition`)
off the same context file so the surfaces never disagree `[synthesis]`:

1. **Live preview / PDF** — deterministic, three-tier priority inside
   [`blueprints/templates.py:preview_application_html`](../../../blueprints/templates.py)
   (`GET /api/applications/<id>/preview`): (a) if the context carries a frozen
   `approved_composition` (and the user hasn't since typed an edit), serve it
   verbatim — preview == the deterministic assemble == the eventual download;
   (b) else if `/api/generate` has already run, serve the cached
   `last_generated_json_resume` (WYSIWYG); (c) else, gated on `llm_recommendations`
   existing on the context, build fresh via
   [`build_json_resume_from_corpus`](../../../corpus_to_json_resume.py), which
   reads the DB *live* and applies `composition_overrides`. Missing
   `llm_recommendations` with no frozen/cached doc serves a placeholder rather
   than a silently-full-corpus render `[synthesis]`.
2. **Generated download, frozen-composition branch** (Phase 4, corpus mode
   post-freeze) — **zero résumé-body LLM calls**.
   [`blueprints/generation.py:_frozen_composition`](../../../blueprints/generation.py)
   returns `context_set["approved_composition"]` when present and non-empty;
   [`blueprints/generation.py:_assemble_from_frozen_composition`](../../../blueprints/generation.py)
   renders it straight through `generator.py:generate_resume_from_json_resume`
   (no markdown round-trip) `[synthesis]`.
3. **Generated download, legacy LLM-apply branch** (file-based contexts, or
   corpus contexts predating the freeze — byte-identical to pre-Phase-4
   behavior) — the curation is folded into `context_set` *before the LLM sees
   it*, via in-memory patches at generate time:
   `_apply_chosen_summary`, `_apply_chosen_experience_summaries`, and
   `_apply_recommended_skills` (all in
   [`blueprints/generation.py`](../../../blueprints/generation.py)).

The skill curation in paths 1 and 3 routes through one pure function,
[`resolve_skill_selection`](../../../corpus_to_json_resume.py) — shared by the
preview's [`_collect_skills`](../../../corpus_to_json_resume.py), the generate-time
`_apply_recommended_skills`, and the Compose GET handler — so all three agree
exactly on the effective ordered skill set `[synthesis]`. Path 2 doesn't need
it separately: the frozen doc's skills were already resolved through the same
function at freeze time (see "Freezing the composition" below).

## Freezing the composition (Phase 4)

The explicit **"Save and continue"** action on Compose — `POST
/api/applications/<id>/composition` with `freeze=true`, handled by
[`blueprints/applications.py:save_application_composition`](../../../blueprints/applications.py) —
calls [`corpus_to_json_resume.freeze_approved_composition`](../../../corpus_to_json_resume.py)
with the just-rebuilt in-memory `composition_overrides` (so the snapshot
reflects *this* save) and writes the result into
`context_set["approved_composition"]`. `freeze_approved_composition` is a
thin wrapper over `build_json_resume_from_corpus` — the same resolver the
live preview calls — that additionally stamps `meta.sartor.frozen = True` so
downstream consumers can tell a frozen snapshot from a live corpus-direct
render `[synthesis]`. Because the value is captured once, at freeze time, a
later edit to a corpus row cannot retroactively change an already-approved
application; every downstream surface (preview, deterministic assemble,
download) renders THIS snapshot without re-resolving. The debounced
autosave (no `freeze` flag) still rebuilds `composition_overrides` on every
save, same as before — only the explicit freeze also captures
`approved_composition`.

## The `composition_overrides` shape

The block lives under `composition_overrides` on the context file. The
authoritative producer is
[`blueprints/applications.py:save_application_composition`](../../../blueprints/applications.py)
(POST `/api/applications/<id>/composition`), which **rebuilds the whole block
wholesale on every save** — so the debounced autosave must send the full
composition state each time, or an omitted field is dropped `[synthesis]`.
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
| `summary_text` / `summary_text_edited` | `str` / `bool` | Compose-drafted (or hand-edited) 2-sentence positioning summary — resolved into `basics.summary` at freeze time, ahead of the legacy pin/recommend/first-active chain |
| `accepted_generated_bullet_ids` | `[bullet_id]` | gap-fill `Bullet` rows (source `llm_proposed:<hash>`) the user accepted at Compose; folded into the per-role effective set like corpus bullets |
| `retired_gap_fill_keys` | `[key]` | durable set of gap-fill proposal keys (`sha256(eid\|text)[:12]`) the user retired, so a retired proposal never resurfaces on a later `/draft-gap-fill` call |

These last three keys are Generation-experience re-architecture additions
(post-2026-07-02) — Compose-authored content, drafted via Sonnet
(`draft_application_summary` / `draft_application_gap_fill` in
`blueprints/applications.py`) — that resolve into the frozen composition
alongside the older pin/exclude overrides `[synthesis]`.

JSON persists object keys as strings, so every reader coerces keys + ids back to
`int` and skips malformed entries rather than failing (see `_read_*` helpers in
[`corpus_to_json_resume.py`](../../../corpus_to_json_resume.py) and the
OUTPUT_DIR-gated `_read_*_overrides` mirrors in
[`blueprints/applications.py`](../../../blueprints/applications.py)).

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
payload it emits is the *frozen snapshot* the (legacy, non-frozen-composition)
generate prompt reads — so a title pinned in Compose *after* analyze is
re-synced into `eligible_titles` for exactly the pinned experiences by the POST
handler (the live-DB preview is unaffected)
([`blueprints/applications.py:save_application_composition`](../../../blueprints/applications.py)).
Not to be confused with `approved_composition` (above) — `career_corpus` is the
eligible-item snapshot the LLM prompt sees; `approved_composition` is the fully
*resolved* JSON-Resume document produced once curation is frozen `[synthesis]`.

The deterministic/LLM boundary (`corpus_to_json_resume.py` and `build_context.py`
take no LLM calls) and the route security gate are canonical in
[`AGENTS.md`](../../../AGENTS.md) — referenced, not restated here (D5).

## Related

- [[corpus-data-model]] — the Candidate / Experience / Bullet / SummaryItem rows this reads.
- [[document-rendering]] — how the JSON Resume dict becomes HTML / PDF / docx.
- [[code-module-map]] — where `corpus_to_json_resume` / `build_context` sit in the module graph.
- [[route-surface]] — the `/api/applications/<id>/composition` GET+POST + preview routes.
- [[frontend-wizard]] — the Compose UI whose `_collectCompositionState()` produces the override payload.
- [[pipeline-stages]] — where Compose (Step 3) and Generate (Step 5) sit in the full apply-run sequence; Step 5's frozen-vs-legacy branch is this page's paths 2 and 3.
