# Application audit chain (the DB record of every apply)

> **Audience:** `dev`
> **Concept:** the per-apply **database** audit chain — the `Application` job
> item, its `ApplicationRun` rows, the exact bullets/titles each run emitted,
> and the proposal-review trail. This is the relational sibling of the on-disk
> `context_*.json` chain in [[iteration-audit-chain]]; same intent, different
> substrate (SQLite rows, not timestamped files).
> **Sources:** [`db/models.py`](../../../db/models.py),
> [`db/build_context.py`](../../../db/build_context.py),
> [`db/persist_run.py`](../../../db/persist_run.py),
> [`blueprints/generation.py`](../../../blueprints/generation.py),
> [`blueprints/corpus/proposals.py`](../../../blueprints/corpus/proposals.py),
> [`blueprints/applications.py`](../../../blueprints/applications.py).
> **Grounding:** per [`SCHEMA.md`](../SCHEMA.md); conclusions tagged `[synthesis]`.

---

## What this records

Corpus-backed mode persists every job application as relational rows so the
question "which corpus facts went into this résumé, and what did the LLM
propose changing?" is answerable after the fact `[synthesis]`. The chain is:
`Application` (the job) → `ApplicationRun` (one generation pass) →
`ApplicationBullet` / `ApplicationRunTitle` (what was used) + `ProposalReview`
(what was proposed). Legacy file mode has no DB row; only corpus mode writes
here `[synthesis]`.

## `Application` — the job item

[`db/models.py:Application`](../../../db/models.py) holds one row per job: the
`jd_text`, a `jd_fingerprint` (`sha256[:16]` of the JD), an optional
`target_role_tag_id`, and a `status` constrained to
`draft | submitted | interview | rejected | withdrawn`
(`ck_application_status`). It belongs to a `Candidate` and owns its runs via a
`cascade="all, delete-orphan"` relationship. The row is created in
[`db/build_context.py:build_context_set_from_db`](../../../db/build_context.py),
which computes the fingerprint and inserts `status="draft"` before the first
run. `Application.is_active` (walkthrough J1) is a soft-retire flag — same
pattern as `ExperienceTitle.is_active` — flipped by
[`blueprints/applications.py:retire_application`](../../../blueprints/applications.py)
(`DELETE /api/applications/<id>`, sets `0`) and `restore_application` (`POST
.../restore`, sets `1`) via the shared `_set_application_active` body; a
retired application is hidden from the Prior Applications list but its runs +
audit trail are kept, never hard-deleted `[synthesis]`.

## `ApplicationRun` — one generation pass

[`db/models.py:ApplicationRun`](../../../db/models.py) is the heart of the
chain. Key columns:

- `run_id` — a unique 12-hex correlation primitive (`unique=True`); the same
  token threaded through telemetry and the prompt cache.
- `iteration` + `parent_run_id` (self-FK, `ondelete="SET NULL"`) — the
  in-DB iteration lineage, mirroring the file chain's `parent_context_path`
  `[synthesis]`.
- `prompt_version` — stamped at creation from
  [`analyzer.py:PROMPT_VERSION`](../../../analyzer.py) (imported into
  `build_context.py`), so a run's output is attributable to a prompt revision.
  The bump discipline itself is canonical in AGENTS.md — cited, not restated
  (D5).
- `corpus_snapshot_json` — the **frozen** set of eligible bullet/title IDs this
  application will see, selected by
  [`db/build_context.py:_select_corpus_snapshot`](../../../db/build_context.py).
  It keeps top-N active bullets per experience by `score_corpus_bullet`,
  tie-broken on `display_order` for a reproducible (cache-stable) prompt
  prefix; all official / `truthful_enough_to_use` titles are kept.
- Output columns: `generated_resume_md`, `generated_cover_letter_md`, the
  `edited_*` text variants, `analysis_json`, `clarification_questions_json`,
  `clarifications_json`, `deterministic_signals_json`, and `ats_roundtrip_json`
  (the C.3 ATS round-trip self-check).

The iteration-0 run is created in `build_context_set_from_db` with
`iteration=0, parent_run_id=None, prompt_version=PROMPT_VERSION` and the
freshly computed snapshot `[synthesis]`.

## `ApplicationBullet` / `ApplicationRunTitle` — what was actually used

[`db/models.py:ApplicationBullet`](../../../db/models.py) is the
"which bullets ended up in this run, in what order" record: one row per used
bullet with a `position` int and a `uq_application_bullet`
(`application_run_id`, `bullet_id`) uniqueness guard. Note the **deliberate absence of
CASCADE on `bullet_id`** — the comment states deleting a referenced bullet
must *fail*; retirement goes through `Bullet.is_active = 0` instead, so the
audit record can never dangle `[synthesis]`.
[`db/models.py:ApplicationRunTitle`](../../../db/models.py) records which
`experience_title` framing each experience used for the run.

Both are written by
[`db/persist_run.py:_persist_selected_bullets`](../../../db/persist_run.py),
which parses the LLM's prefixed IDs (`e3`, `t12`, `b41`) via `_strip_id_prefix`
and validates each against the candidate's own rows before inserting —
hallucinated or cross-candidate IDs are recorded in the `PersistReport` and
skipped, never inserted `[synthesis]`.

## `ProposalReview` — what the LLM proposed changing

The LLM may also propose *new* bullets/titles.
[`db/persist_run.py:_persist_proposed_bullets`](../../../db/persist_run.py) and
`_persist_proposed_titles` create the new `Bullet` / `ExperienceTitle` rows as
`is_pending_review=1, source="llm_proposed:<run_id>"`, then anchor each with a
[`db/models.py:ProposalReview`](../../../db/models.py) row at
`decision="pending"`. A `ck_proposal_review_subject_xor` CHECK enforces exactly
one of `bullet_id` / `experience_title_id`; `decision` is constrained to
`pending | accept_original | accept_edit | reject`. The user's verdict is
applied in the decide route
[`blueprints/corpus/proposals.py:decide_proposal_route`](../../../blueprints/corpus/proposals.py)
(`POST /api/proposals/<id>/decide`): accept flips
`is_pending_review=0` (and
`truthful_enough_to_use=1` for titles), `accept_edit` stores
`user_edited_text` + rewrites the row, `reject` retires the bullet
(`is_active=0`). The `llm_critique_json` column carries the Haiku
`critique_proposal` output, and `decided_at` timestamps closure.

## Persist entry points + the cover-letter carve-out

After the résumé step of [`blueprints/generation.py:run_generation`](../../../blueprints/generation.py)
completes — the LLM `generate()` call, OR (Phase 4) the zero-LLM deterministic
frozen-composition assemble; both return the same result-dict shape (see
[[corpus-to-output-reach]] / [[pipeline-stages]] Step 5) — 
[`blueprints/generation.py:_persist_corpus_generation_to_db`](../../../blueprints/generation.py)
looks up the run, re-validates `candidate_id`, calls
[`db/persist_run.py:persist_corpus_generation`](../../../db/persist_run.py)
(which writes the md, the bullet/title rows, the proposals, and one
`IterationLog` "generate" row), and commits. The detached cover-letter route
uses a separate write-back,
[`blueprints/generation.py:_persist_cover_letter_to_db`](../../../blueprints/generation.py) →
[`db/persist_run.py:persist_cover_letter_md`](../../../db/persist_run.py),
which writes **only** `generated_cover_letter_md` — routing it through the full
persist path would null the already-saved résumé md `[synthesis]`.

## Clarification — cross-application memory

[`db/models.py:Clarification`](../../../db/models.py) is candidate-scoped
(not run-owned): every Q&A pair the candidate has answered, with
`origin_application_id` / `origin_run_id` as `SET NULL` back-references rather
than owning FKs, so memory survives deleting the run that produced it
`[synthesis]`. `kind` is constrained (`experience_probe | scope_probe |
iteration_probe | outcome_probe | manual`) and `is_promoted_to_bullet` marks
answers already turned into corpus bullets.

## Related

- [[corpus-data-model]] — the `Candidate` / `Experience` / `Bullet` rows these audit rows reference.
- [[iteration-audit-chain]] — the on-disk `context_*.json` sibling chain (same intent, file substrate).
- [[code-module-map]] — where `db/` sits in the module map.
- [[route-surface]] — the Flask routes (`/api/generate`, proposal decide, cover-letter) that drive these writes.
- [[pipeline-stages]] — Step 5's frozen-vs-legacy generate branch, both of which feed the persist entry point above.
- [[corpus-to-output-reach]] — how Compose curation resolves into the result dict this chain persists.
