# Blast radius — experience-soft-retire

> **Branch:** `fix/experience-soft-retire`
> **Status:** enumeration complete — re-derived by grep at `b8381f5` (the reproduction commit).

**Provenance note (C-10 rule 3).** `docs/dev/epic-a-chain-design-corrections.md`
carries a `[REPORTED]` appendix with a head-start consumer list. It was **not** used
as the source for this dossier — every row below comes from the greps receipted in
`## Enumeration`. The appendix was read only *after* this table was built, as a
cross-check; the four places it and this enumeration disagree are recorded in
`## Cross-check against the [REPORTED] appendix`.

---

## Surface

Gated surfaces this branch edits (per `scripts/enforcement/blast_radius.py`;
`is_gated()` confirmed `True` for both):

- **`db/models.py`** — class `Experience` (`:88-124`), adding one column
  `is_active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)`.
  No other model changes; the composite index `ix_experience_candidate_order`
  (`:124`) is left alone.
- **`db/migrations/versions/0016_experience_is_active.py`** — new alembic revision,
  `down_revision = "0015"`. Native `op.add_column` behind a `PRAGMA table_info`
  guard; native `op.drop_column` on downgrade. **Not** `batch_alter_table`.

Ungated files this branch also edits (listed for completeness, not for the gate;
re-derived from `git diff --cached --name-only`, not from the plan):
`blueprints/applications.py`, `blueprints/corpus/experiences.py`,
`blueprints/corpus/_shared.py`, `blueprints/corpus/curation.py`,
`blueprints/corpus/skills.py`, `db/build_context.py`, `corpus_to_json_resume.py`,
`onboarding/corpus_import.py`, `onboarding/review_cli.py`, `evals/seed_import.py`,
`scripts/export_corpus_seed.py`, `web_infra/openapi.py`, `static/app.js`,
`static/style.css`, `CHANGELOG.md`, `docs/architecture.md`, this dossier, the
session provenance ledger, and tests.

**`templates/index.html` is NOT edited.** Sites 39 and 40 both decided "no change
to markup", and the diff confirms it — the markup surface came out untouched.

---

## Enumeration

Run from the repo root at `b8381f5`. Counts are the raw match counts.

| Command | Count |
|---|---|
| `grep -rn --include='*.py' 'Experience(' .` minus `ExperienceTitle(` / `ExperienceSummaryItem(` / `ExperienceTitleTag(` / `ExperienceSummaryItemTag(` | **57** (50 under `tests/`, 7 elsewhere) |
| `grep -rn --include='*.py' -E 'query\(Experience\)\|select\(Experience\)' .` | **68** (46 non-test) |
| `grep -rn --include='*.py' -E 'Experience\.is_active\|\bexp\.is_active\|\be\.is_active' .` | **0** |
| `grep -rn --include='*.py' -E 'Experience\.retired\|exp\.retired' .` | **0** |
| `grep -rnE '(FROM\|JOIN\|INTO\|UPDATE) experience\b' --include='*.py' .` | **2** — see the negative-results correction below |
| `git ls-files '*.sql'` | **0** |
| `git ls-files 'templates/*.html'` | **1** (`templates/index.html`) |
| `grep -rnE 'def (to_dict\|__json__\|serialize)' db/models.py` | **0** |
| `grep -rn -i experience recall/` | **0** |
| `grep -rn 'Experience' generator.py pdf_render.py docx_to_persona_html.py parser.py scraper.py` | **2**, both the literal heading string `"Experience"`, not the model |
| `grep -rn -E 'exp\.is_active\|experience.*is_active' static/` | **1** (`static/app.js:5060`, an *experience-title* restore `PUT`, not the role) |
| `grep -rn '\.experiences\b' --include='*.py' .` | **6**, all in `tests/test_build_context_db.py` + one docstring in `web_infra/openapi.py` |
| `grep -rn 'corpusShowRetired\|toggleCorpusRetired\|corpusCount\|_corpusExperiences'` | 20 live code hits across `templates/index.html` + `static/app.js` |
| `grep -rn 'include_retired\|includeRetired\|showRetired'` | route + JS + test hits, tabulated below |
| `python -c "import scripts.enforcement.blast_radius as br; br.is_gated(p)"` | `db/models.py` → `True`; `db/migrations/versions/*` → `True`; `ui_pages/selectors.py` → `True`; every other file this branch touches → `False` |

Names searched for, so the negative results are meaningful: the symbol
`Experience`, the attribute forms `exp.is_active` / `e.is_active` /
`Experience.is_active`, the alternative spelling `retired` / `Experience.retired`,
the table name `experience` in raw SQL (`FROM` / `JOIN` / `INSERT INTO` / `UPDATE`),
the relationship name `.experiences`, the JS carrier `_corpusExperiences`, the DOM
ids `corpusShowRetired` / `corpusCount` / `corpusExperienceList`, the query
parameter `include_retired`, and the seed keys `retired` / `is_active` in
`evals/seed_import.py`.

### Negative results (findings, not absences of work)

- **`Experience.is_active` / `exp.retired` do not exist today — 0 hits.** `Bullet`
  (`db/models.py:181`), `ExperienceTitle` (`:144`) and `Application` (`:764` region)
  each carry a soft-retire flag; `Experience` is the only one of the four that does
  not. Confirms the column is genuinely new, not a re-derivation of something latent.
- **No `.sql` files in the repo (0 tracked).** No standing SQL asset to patch.
- **Exactly one HTML template.** `templates/index.html` is the whole template
  surface; there is no second page to update.
- **No `to_dict` / `__json__` / `serialize` on any model.** Serialization lives
  entirely in `blueprints/corpus/_shared.py`, `corpus_to_json_resume.py`,
  `db/build_context.py`, `scripts/export_corpus_seed.py` and `web_infra/openapi.py`
  — those five are the complete serializer surface.
- **No `Experience` coupling in `recall/` (0 hits)** or in the five other
  deterministic modules (`generator.py`, `pdf_render.py`, `docx_to_persona_html.py`,
  `parser.py`, `scraper.py`) — their 2 hits are the literal section-heading string
  `"Experience"`.
- **`Candidate.experiences` (`db/models.py:67`) has no production consumer.** All 6
  `.experiences` hits are in `tests/test_build_context_db.py` plus one docstring.
  A relationship-level `primaryjoin` filter would therefore buy nothing and would
  change test-visible behavior — the repo's filter-at-call-site convention stands.
- **`docs-site/openapi.json` is a build artifact, not tracked** (`git ls-files`
  returns no `openapi.json`). No committed spec file to regenerate in this branch.

### Correction to a prior claim

The `[REPORTED]` appendix asserts: *"No raw SQL touching the `experience` table — no
`FROM` / `INSERT INTO` / `UPDATE` / `JOIN experience` in any `text()` call or `.sql`
file. No raw-SQL consumer to patch."* **That is wrong. There are two, and one of
them breaks.** See rows 31–32 in `## Consumers` and the probe under `## Verification`.

---

## Consumers

Decision taken for **every** site before the first production edit.

### Gated surfaces

| # | Site (`path:line`) | Decision | Rationale |
|---|---|---|---|
| 1 | `db/models.py:88-124` (`Experience`) | **update** | Add `is_active`, `nullable=False, default=1`. Named `is_active` not `retired` — `db/models.py:140` states the parity-with-`Bullet.is_active` convention, and three siblings already use it. |
| 2 | `db/models.py:124` (`ix_experience_candidate_order`) | no change | The 0015 precedent widened an index because the *query* filters on `is_active` alongside the indexed columns. Neither filter site added here (`db/build_context.py`, `corpus_to_json_resume.py`) orders by `display_order`; both order by `start_date desc`. Widening this index would not serve either query. |
| 3 | `db/migrations/versions/0016_experience_is_active.py` (new) | **create** | Follows `0011_experience_title_is_active.py` exactly: `PRAGMA table_info` guard + native `op.add_column(..., server_default="1")`, native `op.drop_column` on downgrade. **Never `batch_alter_table`** — `experience` is the parent of `experience_title`, `bullet` and `experience_summary_item`; a batch recreate cascade-deletes all three. |
| 4 | 0016 backfill | **no backfill, stated in the docstring** | Unlike 0011 there is no prior retire intent recorded anywhere: retire only ever wrote `bullet.is_active`, and "all bullets retired" is indistinguishable from "role never had bullets". Inferring retirement from it would silently hide live roles. |
| 5 | `ui_pages/selectors.py` | **no change** — see `## Deferred` | Gated, but this branch adds no UX-tier test, so no selector is needed. Not editing it means the gate does not fire on it. |

### Generation chokepoints — the concentration result

| # | Site (`path:line`) | Decision | Rationale |
|---|---|---|---|
| 6 | `db/build_context.py:85-91` | **update** | The single `select(Experience)` feeding `build_context_set_from_db`. Filtering here transitively covers `_synthesize_resume_markdown` (`:114-120`, `:332+`), `_select_corpus_snapshot` (`:160-163`) and `_build_career_corpus_payload` (`:180`, `:282+`) — all take the same already-filtered list. Reproduced as failing before the change (diagnosis, layer 2). |
| 7 | `corpus_to_json_resume.py:176-181` | **update** | The query feeding the `work[]` loop. Filtering **the query**, not the loop body, keeps `work[]` and the order-aligned `work_provenance` (`:183-185`, `:272-279`) in lockstep by construction — a second, separate filter is exactly how provenance would silently misalign. Reproduced as failing before the change (layer 3). |
| 8 | `hardening.py:106` `CorpusExperience` / `:202` `career_corpus` | **no change — decision recorded** | Adding `is_active` to the payload would be a `context_set` **schema** change with a frozen-snapshot consumer, for zero benefit: site 6 filters upstream, so a retired role never reaches the payload. See `## Decision — hardening.py` below. |

### Blueprints

| # | Site (`path:line`) | Decision | Rationale |
|---|---|---|---|
| 9 | `blueprints/corpus/experiences.py:236-263` (`delete_experience`) | **update** | Set `exp.is_active = 0` **and** keep the bullet cascade. Correct the docstring (`:238-243`), which claims a vanishing the diagnosis disproves. |
| 10 | `blueprints/corpus/experiences.py:185-233` (`update_experience`) | **update** | Accept `is_active` so a role can be un-retired — the acceptance bar requires it. Mirrors `update_bullet:509-510` and `update_experience_title:891-897`. |
| 11 | `blueprints/corpus/experiences.py:78-86` (`list_experiences`) | **update** | Filter to active by default; honor `?include_retired=1`, matching `list_applications` (`blueprints/applications.py:169-170`) and `get_experience` (`:171`). |
| 12 | `blueprints/corpus/experiences.py:136-142` (`create_experience` order seed) | **update** | `.count()` over all rows inflates `display_order` once retired rows exist. Count active only. |
| 13 | `blueprints/corpus/experiences.py:163-182` (`get_experience`) | no change | Already takes `include_retired`; loads by id, so it must keep resolving a retired role (that is how the UI renders it under Show retired). |
| 14 | `blueprints/corpus/_shared.py:128-142` (`_load_experience_for_candidate`) | **no change — deliberate** | A filter here would 404 every mutation on a retired role **including the restore route at site 10**, which is the exact failure the acceptance bar forbids. Verified by reading its 11 callers (all by-id ownership lookups), not assumed. |
| 15 | `blueprints/corpus/_shared.py:35-53` (`_experience_summary_dict`) | **update** | Emit `is_active`. Without it the list JSON has nothing for the toggle to branch on — observed as `KeyError: 'is_active'` in the reproduction. |
| 16 | `blueprints/corpus/_shared.py:74-125` (`_experience_detail_dict`) | **update** | Emit `is_active` for symmetry with the titles/bullets it already flags. Its `include_retired` parameter governs child rows and is unchanged. |
| 17 | `blueprints/corpus/experiences.py:266-391` (`merge_experience`) | no change | Merge is initiated from a card the user can see; a retired source is reachable only under Show retired and merging it is coherent. Excluding it would need new UI affordances beyond this brief. |
| 18 | `blueprints/corpus/curation.py:162-166` (pending-review listing) | **update** | Lists roles for the corpus review UI; a retired role must not appear in the review queue. |
| 19 | `blueprints/corpus/curation.py:341-343` (merge suggestions) | **update** | Proposing a merge with a retired role is noise the user just dismissed. |
| 20 | `blueprints/corpus/curation.py:417` (dismiss-ownership set) | no change | Ownership check by explicit id pair; a filter would 404 a legitimate dismissal. |
| 21 | `blueprints/corpus/curation.py:553`, `:585` | no change | `filter_by(id=...)` ownership hops from a bullet/title to its parent role. |
| 22 | `blueprints/corpus/skills.py:285-290` | **update** | Feeds `_build_career_corpus_payload` for skill suggestion — a retired role must not seed skill proposals. Same reasoning as site 6, different entry point. |
| 23 | `blueprints/corpus/proposals.py:365-373` | no change | `filter_by(id=..., candidate_id=...)` ownership check on an explicit target. |
| 24 | `blueprints/corpus/proposals.py:67`, `:79`, `:231`, `:244`; `blueprints/corpus/tags.py:172` | no change | By-id parent hops for ownership/labelling. **Not in the `[REPORTED]` appendix.** |
| 25 | `blueprints/applications.py:1048-1059` (composition build) | **update** | Builds the per-application experience list the Compose UI renders; a retired role must drop out of new compositions. |
| 26 | `blueprints/applications.py:2881-2886` (role-intro staging) | **update** | Stages `ExperienceSummaryItem` variants per role for `recommend_experience_summaries`; a retired role must not be offered. |
| 27 | `blueprints/applications.py:2230-2231` (owned-experience id set for gap-fill) | **update** | Gates which LLM bullet proposals are accepted; proposals against a retired role should be dropped. |
| 28 | `blueprints/applications.py:1557-1601` (pin validation), `:2448-2452`, `:2606`, `:2727` | no change | By-id ownership validation of ids the client already holds. Filtering would 400/404 a *saved* composition whose role was retired afterwards — a data-loss-shaped failure, not a fix. **`:1557`/`:1581`/`:1601` are not in the `[REPORTED]` appendix.** |
| 29 | `db/persist_run.py:194`, `:288`, `:373` | no change | Writes back the LLM's selections/proposals for a run already in flight, by explicit `id` + `candidate_id`. A filter would silently drop audit rows if the user retired a role mid-run. **This entire file is absent from the `[REPORTED]` appendix.** |

### Deterministic / onboarding / scripts

| # | Site (`path:line`) | Decision | Rationale |
|---|---|---|---|
| 30 | `onboarding/corpus_import.py:645-655` | **update** | Duplicate detection matches on `(candidate_id, company, start_date)`. Without a filter a résumé re-import silently merges into — and resurrects — a retired role, with no user-visible signal. Restrict the match to active rows so the re-import creates a fresh live role instead. |
| 31 | `db/migrations/versions/0008_experience_summary_item.py:126` (`FROM experience e`) | no change | Historical raw SQL selecting only `e.id` / `e.summary`. A later-added column cannot affect it. **Contradicts the appendix's "no raw SQL" claim, but harmless.** |
| 32 | `tests/test_experience_summary_item_routes.py:220-230` (`INSERT INTO experience (...)`) | **update — this one breaks** | Raw insert with an explicit column list that omits the new column. `create_all` emits `is_active INTEGER NOT NULL` with **no** DEFAULT (the model uses a Python-side `default=1`, matching all three siblings), so the insert raises `IntegrityError: NOT NULL constraint failed: experience.is_active`. Probe under `## Verification`. Add `is_active` to the column list rather than deviating from the model convention with a `server_default`. |
| 33 | `onboarding/review_cli.py:117-125`, `:394-402` | **update** | The pending-review loop; a retired role must not be queued for review. |
| 34 | `evals/seed_import.py:148-160` | **update** | Add `is_active=_flag(exp.get("is_active", 1))` — back-compat for fixtures written before the column existed. `SUPPORTED_SEED_SCHEMA_VERSIONS` (`:40`) stays `{1}`: a defaulted optional key is a backward-compatible read. |
| 35 | `scripts/export_corpus_seed.py:80-83` + `_experience_row` | **update, but do NOT filter** | Its docstring promises a *faithful* snapshot of all rows. Carry the new column into the exported row; leave the query unfiltered. `SEED_SCHEMA_VERSION` (`:38`) left at 1 — the reader defaults the key, so old seeds still load and new seeds still load in old readers. |
| 36 | `scripts/bench_corpus_scale.py:117`, `:451-453` | no change | Benchmark seeding + counting; the model default supplies the column. |
| 37 | `web_infra/openapi.py:128-141` (`ExperienceSummaryItem`) | **update** | Its docstring says it "Mirrors `_experience_summary_dict`". Adding the field there without this is drift. **Negative result on the query param:** this module models response shapes only — all 245 lines declare zero request parameters (its own header, `:3-8`, scopes the module to `resp=` only and records that `json=`/`query=`/`headers=` validation is deliberately excluded), so there is no `include_retired` query-param surface here to add. |
| 38 | `onboarding/extract_experiences.py:48` (`ExtractedExperience`) | no change | An LLM-extraction TypedDict, not the ORM model. |

### Templates + JS

| # | Site (`path:line`) | Decision | Rationale |
|---|---|---|---|
| 39 | `templates/index.html:730` (`#corpusCount`) | no change to markup | The count is written by JS (site 41/44); the element itself is fine. |
| 40 | `templates/index.html:732` (`#corpusShowRetired` + `toggleCorpusRetired`) | no change to markup | The checkbox already exists and is already wired. Only its handler's behavior widens (site 43). |
| 41 | `static/app.js:3712-3742` (`refreshCorpus` list fetch) | **update** | Append `?include_retired=1` when `_corpusShowRetired`, so the list respects the toggle the way `_loadCorpusDetail:4929` already does. |
| 42 | `static/app.js:4862-4891` (`_renderCorpusList` / `_renderCorpusSummary`) | **update** | `corpusCount` must count active roles only; a retired card gets a `retired` class + flag so "visibly retires" is actually visible. |
| 43 | `static/app.js:5290-5296` (`toggleCorpusRetired`) | **update** | Today it only reloads expanded card bodies. It must also refresh the list, or ticking Show retired reveals retired *rows* but never retired *roles*. |
| 44 | `static/app.js:5480-5503` (`refreshCorpusSummaryFor`) | **update** | Second list fetch; same query-param and count treatment as site 41/42 or the count desyncs after an inline edit. |
| 45 | `static/app.js:5506-5517` (`deleteExperience`) | **update** | The confirm copy ("All its bullets become inactive") and the toast (`Retired ${r.retired_bullets} bullet(s)`) both describe the old bullets-only behavior, and the toast reads "Retired 0 bullet(s)" for exactly the case being fixed. |
| 46 | `static/app.js:5060` | no change | An *experience-title* restore `PUT`, unrelated to the role flag. |
| 47 | `static/app.js:2533`, `:3635`, `:3639`, `:5743`, `:5879-5918`, `:5956-5983`, `:6047-6059`, `:7366-7384`, `:7674` | no change | Readers of `_corpusExperiences` downstream of sites 41/44. Once the carrier holds the filtered list they are correct without edits. Recorded so the exclusion is a decision, not an omission. |

### Docs

| # | Site (`path:line`) | Decision | Rationale |
|---|---|---|---|
| 48 | `docs/architecture.md:354-355` | **update** | The ER diagram claims `experience` has **both** `is_active "soft-retire"` **and** `is_pending_review`. Neither exists at `b8381f5`. This change makes `is_active` real; `is_pending_review` must be removed — it was never a column. |
| 49 | `CHANGELOG.md` | **update** | Schema + behavior change. |

### Tests

| # | Site | Decision | Rationale |
|---|---|---|---|
| 50 | 50 `Experience(...)` constructions under `tests/` | **update — one site; this decision was WRONG as first written** | The original reasoning ("`default=1` applies on every ORM construction; the one exception is the raw-SQL insert at site 32") is **falsified**. `default=1` is exactly the problem: it makes the ORM *always emit the column*, so any test that pins the DB to a revision **older than 0016** and then seeds through the live ORM now fails. Caught by the gate, not by this enumeration — see `## Verification` finding 6. |
| 51 | `tests/test_corpus_merge_and_retire.py:130-196` (`TestRetireVisibility`) | **update** | The only tests asserting `include_retired` semantics — the natural home for role-level coverage. |
| 52 | `tests/test_migrations_data_safety.py:332-354`, `:440-519` | **update** | Replicate the no-row-loss / downgrade / fresh-DB / already-at-head pattern for 0016, asserting the child tables (`experience_title`, `bullet`, `experience_summary_item`) survive — the precise hazard the no-batch choice avoids. |
| 53 | `tests/test_experience_soft_retire.py` | already added (`b8381f5`) | The reproduction; must go 4-passed after the fix. |
| 54 | `tests/test_openapi_spec.py` | verify | Guards the generated spec against the models at site 37. |
| 55 | `tests/ux/regression/test_20260629_corpus_retire_and_busy.py` | verify only | Pins row-level retire (`.corpus-row.retired`), which this change does not alter. |
| 56 | `tests/test_export_corpus_seed.py`, `tests/test_seed_import.py` | verify | Round-trip coverage for sites 34/35. |

---

## Deferred

- **`ui_pages/selectors.py` (site 5) — no retired-role selector added.** Adding one
  would be a gated edit taken purely on speculation: this branch adds no UX-tier
  test, and the acceptance bar is met by the four Python tests in
  `tests/test_experience_soft_retire.py`. Whoever adds the Playwright coverage
  should add `Corpus.CARD_RETIRED = "#corpusExperienceList .corpus-card.retired"`
  then, with their own dossier row. The class itself *is* emitted by site 42, so the
  selector is a one-liner when someone needs it.
- **`hardening.py:106` / `:202` (site 8)** — deliberately excluded; the full
  reasoning is the next section rather than a one-line cell.
- **Index widening (site 2)** — not done, reason in the table. If a future query
  filters `is_active` alongside `display_order`, revisit against the 0015 precedent.
- **`merge_experience` with a retired source (site 17)** — left working. It needs a
  UI decision (hide the merge affordance on a retired card? warn?) that is outside
  this brief.

---

## Decision — `hardening.py` `CorpusExperience` (site 8)

**Decision: do not add the flag to the payload. Filter upstream, leave the
`context_set` shape unchanged.**

- `career_corpus` is part of the `context_set` contract
  (`hardening.py:202`), which is **persisted** — every `/api/generate` writes a
  timestamped child context and `application_run.corpus_snapshot_json` freezes a
  copy. A new key would appear in new snapshots and be absent from old ones, so
  every reader would need an absence-tolerant branch, forever, to describe a state
  the payload can no longer be in.
- It buys nothing. The only producer of `career_corpus` in corpus mode is
  `_build_career_corpus_payload`, fed by the query at site 6. Once that query
  filters, a retired role cannot reach the payload — there is no consumer left that
  would read the flag.
- The prompt has no use for it. `analyzer.py`'s `<career_corpus>` block would have
  to be taught to ignore roles it was handed and told not to use — strictly worse
  than not handing them over.
- **Consequence, stated plainly:** a frozen snapshot taken *before* a role was
  retired still contains that role, and re-rendering that application from its
  frozen snapshot will still show it. That is the intended semantics of a freeze
  (the audit trail records what was actually generated), and it is the same
  behavior a retired *bullet* already has. It is recorded here so it is a decision,
  not a surprise.

This keeps `hardening.py` off the change list entirely, so no `context_set` schema
change ships on this branch.

---

## Verification

**How a missed consumer surfaces**, per class:

1. **Generation leak.** `tests/test_experience_soft_retire.py` asserts the retired
   role's absence at four layers in one comparison, including the `work[]` ↔
   `work_provenance` length-and-id alignment. A filter applied to one and not the
   other fails on the id list, not just on a length.
2. **Schema/migration damage.** The 0016 tests (site 52) assert child-row counts in
   `experience_title`, `bullet` and `experience_summary_item` survive upgrade *and*
   downgrade, plus `PRAGMA integrity_check` and `PRAGMA foreign_key_check`. An
   accidental `batch_alter_table` fails these loudly.
3. **Raw-SQL breakage.** Already found and probed rather than discovered in CI:

   ```
   $ python - <<'PY'   # experience table built in the create_all shape, + is_active
   ... INSERT INTO experience (id, candidate_id, company, start_date,
                               display_order, summary, created_at, updated_at) ...
   PY
   PROBE: raw INSERT FAILED -> IntegrityError (sqlite3.IntegrityError) NOT NULL constraint failed: experience.is_active
   ```

   Confirming the DDL the probe is built on:

   ```
   $ python -c "... CreateTable(Base.metadata.tables[t]) ..."
   CREATE TABLE experience_title (
        is_active INTEGER NOT NULL,      <- no DEFAULT
   CREATE TABLE bullet (
        is_active INTEGER NOT NULL,      <- no DEFAULT
   ```

   So this is a property of the existing convention, not of my column. Site 32 is
   updated accordingly.
4. **Serializer / spec drift.** `tests/test_openapi_spec.py` compares the emitted
   spec to the pydantic models; a serializer field added without site 37 shows up
   there.
5. **Whole-suite.** `python -m scripts.gate` on the **committed** tree (a staged
   tree passes several checks vacuously — `docs/dev/epic-a-chain-design-corrections.md`
   finding 10).

6. **Downgrade-then-seed tests — the class this enumeration MISSED.** Found by
   `python -m scripts.gate`, not by any grep above. Verbatim:

   ```
   FAILED tests/test_proposal_review_bridge.py::TestBackfillMigration0014::test_orphan_shape_resolved_control_untouched
   FAILED tests/test_proposal_review_bridge.py::TestBackfillMigration0014::test_rerun_is_idempotent
   sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) table experience has no column named is_active
   [SQL: INSERT INTO experience (candidate_id, company, location, start_date, end_date,
    display_order, summary, is_active, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)]
   2 failed, 2385 passed, 1 skipped in 457.18s
   ```

   **Mechanism.** Both tests do `command.upgrade(cfg, "head")` then
   `command.downgrade(cfg, "0013")` to rewind the version pointer, then seed via
   `_seed_orphan_shape`, which builds rows through the **live ORM**. Until this branch,
   walking back to `0013` ran no structural DDL on `experience`, so the schema stayed
   fully built — `_seed_orphan_shape`'s docstring says so explicitly: *"Schema is fully
   built already (0014 adds no columns), so this runs against the ORM directly regardless
   of which revision `alembic_version` currently points at."* `0016` is the first revision
   whose `downgrade()` **removes a column the live ORM still writes**, so that assumption
   and the caller's comment (*"this only moves alembic_version, not the rows below"*) are
   both now false.

   **This is the exact inverse of site 32.** There, a raw INSERT omitted a column the
   schema required. Here, the ORM emits a column the (downgraded) schema lacks. Site 50
   dismissed the whole `tests/` population on the strength of `default=1` — which is the
   very mechanism that breaks these two.

   **Fix taken:** rewind with `command.stamp(cfg, "0013")` rather than
   `command.downgrade`, which moves the version pointer without running any downgrade DDL
   — restoring the behavior both comments already claim. Safe because every re-run
   upgrade in the walk is idempotent, verified by reading: `0014` is `UPDATE`-only scoped
   to `decision='pending'`, `0015` drops-then-creates its index behind an existence check,
   `0016` skips behind its `PRAGMA table_info` guard.

**Stated limit (C-0).** Items 1–4 catch a *missed filter* at a site that has a test.
Sites 47 (nine JS readers) and 24/28/29 (by-id ownership hops) are decided
"no change" by reading, and the JS ones sit in C-10's own declared blind spot — the
computed audit covers first-party Python import fan-in only. I did not exercise the
nine JS readers in a browser, and I am not claiming they are verified beyond the
reading recorded above.

---

## Cross-check against the `[REPORTED]` appendix

Run after this dossier was built, per the provenance note. Four disagreements:

1. **Wrong — "no raw SQL touching the `experience` table."** There are two
   (sites 31, 32), and one of them **fails** after the change. This is the single
   most expensive thing the appendix would have cost, because "no raw-SQL consumer
   to patch" reads as a completed search.
2. **Missing — `db/persist_run.py` entirely** (`:194`, `:288`, `:373`, site 29).
   Three `query(Experience)` sites in the run-persistence path, in no section of
   the appendix.
3. **Missing — 9 further blueprint sites:** `blueprints/applications.py:1557`,
   `:1581`, `:1601`; `blueprints/corpus/curation.py:417`, `:553`, `:585`;
   `blueprints/corpus/proposals.py:67`, `:79`, `:231`, `:244`;
   `blueprints/corpus/tags.py:172`. All decided "no change", but each was a decision
   that had not been taken.
4. **Missing — `onboarding/review_cli.py`'s two concrete line ranges** (`:117-125`,
   `:394-402`; the appendix names the file but not the sites) and
   **`web_infra/openapi.py:128-141`**, which is a real serializer surface the
   appendix's own "complete serializer surface" list omits (it names four; there are
   five).

Where the appendix was **right and useful**: the two-site concentration result
(sites 6, 7) is correct and is the load-bearing insight; the `work_provenance`
order-alignment warning is correct; the `_load_experience_for_candidate` restore-404
trap (site 14) is correct; the `corpus_import.py` silent-resurrection risk (site 30)
is correct and is the subtlest item in the whole enumeration; and the 0011
no-`batch_alter_table` precedent is correct.

Two of its claims I did **not** independently confirm and am not relying on: the
"49 sites construct `Experience(...)`" count (my grep says 57 total / 50 under
`tests/`, but I did not reconcile the difference site-by-site — it does not change
any decision, since all of them get the column by default), and the list of
"known false positive" test files, which I did not re-check because no decision
depends on it.
