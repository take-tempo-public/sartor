# Diagnosis — retiring a role with zero bullets silently does nothing

> **Status:** root cause PROVEN — reproduced deterministically, four layers, with a passing control arm.
> **Branch:** `fix/experience-soft-retire`

---

## Symptom

A user clicks Retire on a role that has no bullets yet (a role added to the corpus
but never fleshed out, or one whose bullets were all retired individually). The
request succeeds — no error, no warning — and the role stays exactly where it was:
still in the Career Corpus list, still fed to the LLM at generate time, still
rendered into the produced résumé's work history. There is no way to make it go
away short of a merge or a manual DB edit.

---

## Observed

All facts below were produced by `tests/test_experience_soft_retire.py` run against
HEAD `7c15c2e` (the sprint A1a tip this branch is stacked on), command verbatim:

```
python -m pytest tests/test_experience_soft_retire.py -p no:randomly -q
```

Result: `3 failed, 1 passed in 15.90s`.

- **The handler reports success while changing nothing.** `DELETE /api/experiences/2`
  (the 0-bullet role) returned `200` with body `{"experience_id": 2, "retired_bullets": 0}`.
  The `retired_bullets == 0` assertion in
  `tests/test_experience_soft_retire.py::test_retire_zero_bullet_role_hides_it_everywhere`
  passed, so zero rows were written; the 200 came back regardless.

- **The role survives every downstream layer.** The same test measures all four
  layers before asserting, so no single failing layer can hide the others (C-7 rule 4).
  Verbatim assertion output:

  ```
  AssertionError: retired 0-bullet role (id=2) survives downstream:
      observed={'1_corpus_list': ['Globex', 'Acme'], '2_career_corpus': ['Globex', 'Acme'],
                '2_resume_text_mentions_acme': True, '3_work_names': ['Globex', 'Acme'],
                '3_provenance_exp_ids': [1, 2]}
      expected={'1_corpus_list': ['Globex'], '2_career_corpus': ['Globex'],
                '2_resume_text_mentions_acme': False, '3_work_names': ['Globex'],
                '3_provenance_exp_ids': [1]}
  ```

  Layer by layer: `GET /api/users/alice/experiences` still lists it;
  `db.build_context.build_context_set_from_db` still puts it in `career_corpus`
  **and** in the synthesized `resume.text` the prompt consumes;
  `corpus_to_json_resume.build_json_resume_from_corpus` still emits it in `work[]`
  and in the order-aligned `meta.sartor.work_provenance`.

- **The control arm passes — the defect is specific to the zero-bullet case.**
  `test_control_bulleted_role_retire_already_leaves_generation` retires the
  *bulleted* role through the identical handler and asserts its bullet text is gone
  from the synthesized résumé and its `highlights` are gone from `work[]`. That test
  is the one `passed` in the run above. So retire's bullet cascade does work; what
  fails is that a role with nothing to cascade to has no other way to be marked.

- **The `experience` row carries no retire flag at all.** Read directly at
  `db/models.py:88-124`: the columns are `id, candidate_id, company, location,
  start_date, end_date, display_order, summary, created_at, updated_at` plus the
  relationships and `ix_experience_candidate_order`. There is no `is_active` and no
  `retired`. `ExperienceTitle.is_active` is at `:144`, `Bullet.is_active` at `:181` —
  both outside that range.

- **The retire handler only ever touches child bullets.**
  `blueprints/corpus/experiences.py:256` is
  `session.query(Bullet).filter_by(experience_id=exp.id).update({"is_active": 0})`,
  and the returned payload is that row count. Nothing in `delete_experience`
  (`:236-263`) writes to the `experience` row.

- **The serializer has no flag to emit either.**
  `test_retired_role_visible_with_include_retired` failed with
  `KeyError: 'is_active'` reading the corpus-list row for the retired role —
  `_experience_summary_dict` (`blueprints/corpus/_shared.py:35-53`) emits no such key,
  so the frontend's existing "Show retired" toggle has nothing to branch on for roles.

- **There is no restore path.** `test_retired_role_can_be_restored` fails at its
  first step (`['Globex', 'Acme'] == ['Globex']`) because the retire never took;
  `update_experience` (`:185-233`) accepts `company / location / start_date /
  end_date / summary / display_order` and no activity flag.

- **The handler's docstring states the opposite of the observed behavior.**
  `blueprints/corpus/experiences.py:238-243` claims the experience row "with no
  active bullets it vanishes from the corpus selection pool." Layer 1/2/3 above show
  it does not vanish, and for a 0-bullet role there were never any active bullets to
  begin with.

---

## Falsified

- **"Retire is broken in general / the bullet cascade doesn't work."** Killed by the
  control arm: the bulleted role's retire *does* remove its bullet text from the
  synthesized résumé and its `highlights` from `work[]`. Only the role's own
  identity row survives, which for a bulleted role leaves a mostly-empty husk and
  for a 0-bullet role leaves it fully intact.

- **"The corpus list is the only affected surface, so this is a UI-only fix."**
  Killed by layers 2 and 3 of the same run: `career_corpus`, `resume.text` and
  `work[]` all still carry the role. A list-route-only filter would leave the
  generated document wrong.

- **"`work[]` drops an experience with no highlights anyway, so generation is safe."**
  Killed by the observed `'3_work_names': ['Globex', 'Acme']`.
  `corpus_to_json_resume.py:270` emits the entry when
  `entry.get("name") or entry.get("position") or highlights` — company and title
  alone are enough, so a bullet-less role still renders as a work entry.

---

## Inferred

*Hypothesis, not fact — the mechanism proposed to explain the observations above.*

`Experience` was given soft-retire semantics by proxy: whoever wrote
`delete_experience` reasoned that a role with no live bullets is invisible in
practice, and encoded that as the bullet cascade instead of a row-level flag. That
holds only while "has ≥1 bullet" is an invariant. It is not one —
`create_experience` (`:99-160`) creates a role with zero bullets, and
`delete_bullet` can retire the last one. The three siblings that needed the same
semantics (`ExperienceTitle`, `Bullet`, `Application`) each got a real `is_active`
column; `Experience` is the one that did not.

**What I have not verified:** the above is a reading of intent from the docstring at
`:238-243` and the sibling-column pattern. I did not find a design note or commit
message stating it, and I did not look for one. Nothing in the fix depends on this
paragraph being right.

---

## Falsification

**The experiment, run before any production edit:** `tests/test_experience_soft_retire.py`,
four tests, no browser, no network, no timing dependence. Seeded corpus is one
bulleted role (`Globex`, control) and one 0-bullet role (`Acme`, subject), both with
an official title.

- **If the subject tests fail on HEAD and the control passes:** the mechanism is
  confirmed as "no experience-level retire flag", specific to the zero-bullet case —
  build the fix.
- **If the control ALSO fails:** the mechanism is not the missing flag; the bullet
  cascade itself is broken. Stop, do not add a column, widen and report.
- **If everything passes on HEAD:** the hypothesis is dead. Stop.

**Outcome (recorded above): 3 failed, 1 passed — subject failed on all four layers,
control passed.** Fix authorized.

---

## The fix

Give `Experience` the soft-retire flag its three siblings already have, and make the
two chokepoints that feed generation honor it.

1. `db/models.py:88-124` — `is_active: Mapped[int]`, `nullable=False, default=1`.
   Named `is_active`, not `retired`, for parity with `Bullet.is_active` — the
   convention `db/models.py:140` states explicitly.
2. A new alembic revision following `0011_experience_title_is_active.py` exactly:
   `PRAGMA table_info` idempotency guard + **native `op.add_column`**. Not
   `batch_alter_table` — `experience` is a parent of `experience_title`, `bullet` and
   `experience_summary_item`, and a batch recreate cascade-deletes them. No backfill:
   unlike 0011 there is no prior retire intent recorded anywhere to recover.
3. `blueprints/corpus/experiences.py:236-263` — set `exp.is_active = 0` **and** keep
   the bullet cascade; correct the docstring, which today asserts a vanishing that
   the observations above disprove.
4. `update_experience` — accept `is_active` so the role can be un-retired. The
   loader `_load_experience_for_candidate` (`_shared.py:128-142`) must NOT filter, or
   the restore route 404s on exactly the rows it exists to restore.
5. `db/build_context.py:85-91` and `corpus_to_json_resume.py:176-181` — filter to
   `is_active == 1`. These two close the whole generation blast radius transitively
   (prompt, synthesized résumé, snapshot, `work[]`, PDF/DOCX, ATS roundtrip). In
   `corpus_to_json_resume.py` the filter is applied to the query feeding the loop, so
   `work[]` and the order-aligned `work_provenance` (`:183-185`, `:272-279`) stay in
   lockstep by construction rather than by a second filter that could drift.
6. Serializers in `blueprints/corpus/_shared.py` emit `is_active`; the corpus list
   route gains `?include_retired=1`, wired to the existing `corpusShowRetired`
   checkbox / `toggleCorpusRetired()`; `corpusCount` excludes retired roles.

Full consumer enumeration and the per-site decisions:
[`docs/dev/blast-radius/experience-soft-retire.md`](../blast-radius/experience-soft-retire.md).

---

## Acceptance bar

`tests/test_experience_soft_retire.py` goes 4-passed **on a first attempt, with no
rerun** (`pytest-rerunfailures` reports a fail-fail-pass as a bare `PASSED` with no
traceback, so a retried green is not a bar) — specifically:

- the 0-bullet role disappears from the corpus list, `career_corpus`, `resume.text`,
  `work[]` and `work_provenance` in the single all-layers assertion;
- the control arm still passes, i.e. the bullet cascade was not traded away for the
  flag;
- `PUT /api/experiences/<id> {"is_active": true}` restores it and it reappears;
- `?include_retired=1` shows it with `is_active: false`.

Plus: the migration is covered by the no-row-loss / downgrade / fresh-DB /
already-at-head pattern in `tests/test_migrations_data_safety.py:332-354,440-519`, and
`python -m scripts.gate` is green on the **committed** tree (a staged tree passes
several checks vacuously — `docs/dev/epic-a-chain-design-corrections.md` finding 10).
