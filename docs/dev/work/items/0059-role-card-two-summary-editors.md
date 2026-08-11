```toml
schema = 1
id = 59
kind = "item"
title = "A corpus role card shows two different summary editors — the legacy denormalized field and the canonical variants section"
status = "watching"
decision_owner = "user"
refs = [
  "static/app.js",
  "db/models.py",
]
summary = "A role card offers two summary editors: the legacy Experience.summary cache and the canonical variants section."
```

**Observed while reordering the role card in Epic A sprint A1a.** One expanded
corpus role card contains two places to write a role summary:

1. **A `Summary` textarea inside the identity field group** —
   `_renderExperienceFieldGroup` lists it alongside Company / Location / Start /
   End, writing `Experience.summary`.
2. **A "per-role intro variants" section** — `_renderExperienceSummarySection`,
   editing `ExperienceSummaryItem` rows.

`db/models.py:115-119` is explicit that the first is legacy:

> The single `summary` column above is now the legacy denormalized cache —
> alembic 0008 backfills it into one `ExperienceSummaryItem` row.

So the canonical store is the variants section, and the field-group textarea
edits a cache of it. Nothing in the UI says so. A user who edits the top textarea
has no way to know whether it wins over, loses to, or silently diverges from the
variants below it.

**Not investigated on this branch, and the severity is genuinely unknown.** A1a
was a presentational reorder and deliberately did not touch either editor or the
save path. What is *not* yet established, and would need to be before anything is
changed:

- whether editing the field-group textarea updates the backing
  `ExperienceSummaryItem`, overwrites it, or diverges from it;
- which of the two the generation pipeline actually reads;
- whether alembic 0008's backfill is still the only writer of the legacy column.

Those are three checkable questions, none of them answered here. Filed as an
observation, not as a diagnosis — the mechanism above is read off a model
comment, not off executed behavior (C-7: reading code is a hypothesis).

**Related:** sprint A1b adds `Experience.is_active` and touches the same
serializers; if the answer is "the legacy column should stop being user-editable,"
that is a UI decision for the owner, not a fold-in.

## Updates

### 2026-08-08 — filed on `feat/corpus-polish` (found while reordering the role card)
