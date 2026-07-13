# Corpus data model

> **Audience:** `dev`
> **Concept:** the SQLite career-corpus schema and the one lifecycle
> (`is_active` / `is_pending_review` / `source` / `display_order` + a `*_tag`
> join) that `Bullet`, `Skill`, `SummaryItem`, and `ExperienceSummaryItem` all
> wear — the "unified Corpus Item" shape — plus the narrower `is_active`
> soft-retire pattern it later lent to `ExperienceTitle` and `Application`,
> and the alembic chain (head `0015`) that grew it.
> **Sources:** [`db/models.py`](../../../db/models.py),
> [`db/build_context.py`](../../../db/build_context.py),
> [`db/migrations/versions/0009_skill_corpus_item.py`](../../../db/migrations/versions/0009_skill_corpus_item.py),
> [`db/migrations/versions/0010_online_profile_text.py`](../../../db/migrations/versions/0010_online_profile_text.py),
> [`db/migrations/versions/0011_experience_title_is_active.py`](../../../db/migrations/versions/0011_experience_title_is_active.py),
> [`db/migrations/versions/0012_merge_dismissal.py`](../../../db/migrations/versions/0012_merge_dismissal.py),
> [`db/migrations/versions/0013_application_is_active.py`](../../../db/migrations/versions/0013_application_is_active.py),
> [`db/migrations/versions/0014_backfill_orphaned_proposal_reviews.py`](../../../db/migrations/versions/0014_backfill_orphaned_proposal_reviews.py),
> [`db/migrations/versions/0015_application_index_add_is_active.py`](../../../db/migrations/versions/0015_application_index_add_is_active.py),
> [`docs/architecture.md`](../../architecture.md) §Persistence model.
> **Grounding:** per [`SCHEMA.md`](../SCHEMA.md); conclusions tagged `[synthesis]`.

---

## The corpus backbone

The corpus is a single SQLite DB of ORM rows rooted at one
[`Candidate`](../../../db/models.py) per user (`username` unique). The
career-content spine is **Candidate → Experience → Bullet**, with
[`Experience`](../../../db/models.py) holding company/location/dates and a
`display_order`, and [`Bullet`](../../../db/models.py) the line-level achievement
rows. Per-role titles live in [`ExperienceTitle`](../../../db/models.py) (at most
one `is_official=1` per experience, enforced by a partial unique index
`ix_experience_title_official` with `sqlite_where=text("is_official = 1")`; migration
`0011` also gave it an `is_active` soft-retire flag — see below). A candidate's
"keep separate" decision on a pair of similar experiences the merge-suggestion scan
flagged is recorded in [`MergeDismissal`](../../../db/models.py) (migration `0012`) —
an order-normalized, uniqued `(candidate_id, exp_a_id, exp_b_id)` row that stops the
scan re-surfacing a dismissed pair; it cascades away if either experience is deleted
`[synthesis]`.
[`Tag`](../../../db/models.py) is one canonical per-candidate registry
(`kind IN ('role','domain','skill','tech')`, CHECK-constrained) reached from each
content table through its own junction row. The full FK/cascade picture is the ER
diagram in [`architecture.md` §Persistence model](../../architecture.md).

## The unified Corpus-Item lifecycle

The load-bearing pattern: four content types carry the **same four lifecycle
columns** so they share one recommend / pin / drop / curate / tag machinery
`[synthesis]`:

| Column | Meaning |
|---|---|
| `is_active` | soft-retire flag (`1`=live); rows are never hard-deleted when referenced — retire instead. |
| `is_pending_review` | `1` = LLM-proposed, awaiting the human approve/deny gate. |
| `source` | provenance string; CHECK `IN ('manual','imported','llm_proposed')` on the three new items. |
| `display_order` | stable per-parent ordering integer. |

Each item that wears this shape also gets a composite index over
`(parent_id, is_active, is_pending_review, display_order)` so the active-approved
slice is cheap to scan — e.g.
`ix_bullet_experience_active_pending_order` on
[`Bullet`](../../../db/models.py) and
`ix_skill_candidate_active_pending_order` on
[`Skill`](../../../db/models.py).

The four items and their parents:

- [`Bullet`](../../../db/models.py) — parent `Experience`; the original /
  reference Corpus Item. Adds `pattern_kind` (CHECK `xyz|star|car|manual`),
  `has_outcome`, plus `BulletMetric` children.
- [`Skill`](../../../db/models.py) — parent `Candidate`; promoted to a full
  Corpus Item in `0009` (B.5). Adds `category` / `proficiency` / `years`; unique
  per `(candidate_id, name)`.
- [`SummaryItem`](../../../db/models.py) — parent `Candidate`; one variant of the
  candidate's overall positioning summary (β.6). Adds `label` + `has_outcome`.
- [`ExperienceSummaryItem`](../../../db/models.py) — parent `Experience`; one
  variant of a single role's intro paragraph (B.4, Sprint 6.6). Mirrors
  `SummaryItem` but is **opt-in** per the model docstring (a role shows an intro
  only when the Tailor-time toggle is on).

Each has a parallel join table —
[`BulletTag`](../../../db/models.py),
[`SkillTag`](../../../db/models.py),
[`SummaryItemTag`](../../../db/models.py),
[`ExperienceSummaryItemTag`](../../../db/models.py) — every one a `(item_id, tag_id)`
PK pair with a `confidence float`, deliberately mirroring `BulletTag` so corpus-tag
operations treat all four identically `[synthesis]`. Note `SkillTag` (a Skill row
linked to any-kind tags) is distinct from a `Tag` of `kind='skill'` (a skill
keyword tagging a bullet/title), per the `SkillTag` docstring.

## The `is_active` soft-retire pattern spreads beyond the four items

Two non-Corpus-Item tables later borrowed just the `is_active` half of the shape
(soft-retire, never hard-delete a row other rows reference), not the full
four-column lifecycle — neither gained `is_pending_review`/`source`/`display_order`:

- [`ExperienceTitle`](../../../db/models.py) — migration `0011` adds `is_active`
  "parity with `Bullet.is_active`": the corpus "delete" on an
  alternate title was always a soft-retire (clearing `is_official` /
  `truthful_enough_to_use`), but nothing filtered the row out of the UI until this
  column existed. Retired titles are kept for the `application_run_title` /
  `proposal_review` audit FKs.
- [`Application`](../../../db/models.py) — migration `0013` (walkthrough J1) adds
  `is_active` "parity with `ExperienceTitle.is_active`" so the Prior Applications
  list can hide poor examples / abandoned drafts while keeping the application's
  runs + audit trail.

Both migrations use a **native `ADD COLUMN`**, not `batch_alter_table`, for the same
reason `0010` does (below): `experience_title` and `application` are each a PARENT
table (of `application_run_title` and `application_run` respectively), and a batch
recreate would cascade-delete those child rows while SQLite FK enforcement is on
`[synthesis]`.

## Denormalized caches the items supersede

Two scalar columns predate their multi-variant items and are kept as
denormalized caches for back-compat: `Candidate.profile_text` (superseded by
`SummaryItem` rows) and `Experience.summary` (superseded by
`ExperienceSummaryItem` rows). The model docstrings direct **new code to query
the item rows**; the legacy columns survive for code that reads them directly
`[synthesis]`. The persistence diagram annotates `profile_text` as
"legacy; SummaryItem variants are canonical post-v1.0"
([`architecture.md` §Persistence model](../../architecture.md)).

## How the lifecycle gates output

[`build_context_set_from_db`](../../../db/build_context.py) is the deterministic
projection from corpus rows into the `context_set` the LLM consumes. The
lifecycle columns are the filter: [`_build_career_corpus_payload`](../../../db/build_context.py)
emits only `b.is_active` bullets, and [`eligible_titles_for`](../../../db/build_context.py)
keeps a title only when `is_official OR truthful_enough_to_use`. Pending-review
rows are *included* in the synthesized résumé so a freshly-imported user can run
the pipeline before reviewing (the docstring frames review as a UI concern, not a
pipeline gate) — but for the newer LLM-proposed items the approve/deny gate is
the grounding backstop (a `Skill` with `is_pending_review=1` never reaches the
recommend set, per the [`Skill`](../../../db/models.py) docstring). The iteration-0
ID set is frozen by [`_select_corpus_snapshot`](../../../db/build_context.py) using
the deterministic [`score_corpus_bullet`](../../../db/build_context.py) fit score
(P1 hardening — no LLM), so the cached prompt prefix is reproducible across an
application's iterations `[synthesis]`. (The hardening / no-LLM boundary itself is
canonical in [`AGENTS.md`](../../../AGENTS.md) — cited, not restated, per
[`SCHEMA.md`](../SCHEMA.md) D5.)

## Migration chain — head `0015`

Schema evolution is alembic-driven; the current head is **`0015`**
([`0015_application_index_add_is_active.py`](../../../db/migrations/versions/0015_application_index_add_is_active.py),
`revision="0015"`, `down_revision="0014"`, verified). Five
migrations landed after `0010`:

- **`0011`** adds `ExperienceTitle.is_active` (see the `is_active` pattern section
  above); backfills prior "retired" titles (not official, not pending, marked
  not-truthful under the old semantics) to `is_active=0` so their retire intent
  survives the migration.
- **`0012`** creates the `merge_dismissal` table (see above) — a table-existence
  guard, not a column-existence one, since it's a new table rather than an ALTER.
- **`0013`** adds `Application.is_active` (see above); no backfill — every existing
  application starts active (`server_default '1'`).
- **`0014`** is a **data-only** backfill with no schema change: before this release,
  the corpus onboarding-review accept/retire routes
  (`blueprints/corpus/curation.py` / `blueprints/corpus/experiences.py`) cleared
  `is_pending_review`/`is_active` directly without ever touching
  `ProposalReview.decision`, leaving it `"pending"` forever for already-reviewed
  rows and over-counting the applications-list "N to review" badge. `0014`
  resolves those stale rows via idempotent `UPDATE ... WHERE decision = 'pending'`
  statements (mirroring what `/api/proposals/<id>/decide` would have recorded);
  `downgrade()` is a documented no-op since reverting would misrepresent
  already-resolved review history `[synthesis]`.
- **`0015`** (PX-38) is **index-only** with no schema or data change: the
  `ix_application_candidate_status_updated` index originally had only
  `(candidate_id, status, updated_at)`, omitting `is_active` even though
  `list_applications` filters both `candidate_id` and `is_active` on every
  call. The new column order `(candidate_id, is_active, status, updated_at)`
  adds a fully-covering equality prefix for the default query. Uses native
  `op.create_index` / `op.drop_index` only (metadata-only DDL in SQLite,
  zero row touch) — no `batch_alter_table` risk `[synthesis]`.

`0010` (PX-02) adds the nullable `Candidate.online_profile_text` column — the cached
opt-in profile/website scrape, a **distinct channel** from `profile_text` (the β.6
positioning summary); reusing `profile_text` would corrupt summaries, so the scrape gets
its own column. It uses a native `ADD COLUMN` (not a batch recreate) because `candidate`
is a PARENT table — a batch rebuild would cascade-delete child rows when PRAGMA
`foreign_keys` is on (it cannot be disabled inside alembic's transaction) `[synthesis]`.
The prior head `0009` is the Skill → Corpus-Item upgrade: it adds the lifecycle columns +
`ck_skill_source` CHECK + the composite index + the `skill_tag` join, then
backfills legacy rows to `source='imported', is_active=1, is_pending_review=0`
with `display_order` set to preserve the prior name-sorted order. Each ALTER is
guarded (PRAGMA column-exists / table-exists) so a fresh DB — where `0001`'s
`Base.metadata.create_all` already reflects the current model — skips the ALTER
and stays idempotent. The sibling backfills: `0004` seeds `SummaryItem` from
`profile_text`, `0008` seeds `ExperienceSummaryItem` from `Experience.summary`
(both per their model docstrings). Adding a new corpus item type follows the same
recipe — mirror `SummaryItem` / `Skill`: lifecycle columns, a `*_tag` join, a
composite index, and a backfill migration `[synthesis]`.

## Related

- [[code-module-map]] — where `db/models.py` + `db/build_context.py` sit in the module map.
- [[corpus-to-output-reach]] — how active/approved corpus rows travel from these tables into the generated document.
- [[context-set-contract]] — the `context_set` shape `build_context_set_from_db` populates from these rows.
- [[application-audit-chain]] — `Application` / `ApplicationRun` / `ApplicationBullet`, which reference (never cascade-delete) these corpus rows.
