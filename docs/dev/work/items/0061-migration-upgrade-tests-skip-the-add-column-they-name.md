```toml
schema = 1
id = 61
kind = "item"
title = "Migration \"upgrade adds column X\" tests never execute op.add_column — revision 0001 is create_all against the live models"
status = "watching"
decision_owner = "agent"
refs = [
  "tests/test_migrations_data_safety.py",
  "db/migrations/versions/0001_initial_schema.py",
]
summary = "Stopping the chain at N-1 yields today's full schema, so the guard skips and the ADD path goes unexercised."
```

**Found by the sprint A1b adversarial review; independently re-verified by the
orchestrator before filing.**

`db/migrations/versions/0001_*.py:31` builds the schema with
`Base.metadata.create_all(bind=op.get_bind())` — against the **live**
`db.models.Base.metadata`, i.e. whatever the models declare *today*, not a
snapshot of the schema as of revision 0001. Consequence: running the chain and
stopping at revision N-1 does **not** reproduce the pre-N schema. Every column a
later revision adds is already present from step 0001.

Verified directly (not inferred):

```
command.upgrade(cfg, "0015")          # stop one revision BEFORE 0016
PRAGMA table_info(experience)
is_active present after stopping at 0015 (BEFORE 0016 runs): True
```

So `test_upgrade_0015_to_head_adds_is_active_no_row_loss` reaches 0016's
`PRAGMA table_info` idempotency guard, takes the **skip** branch, and never runs
`op.add_column` — despite its name. The same holds for the equivalent tests on
revisions 0011, 0013 and 0015; this is a property of the migration harness, not
of anything sprint A1b introduced.

**This is a naming/claims-precision problem, not a coverage hole — for 0016.**
The paired downgrade test does exercise the real code: it runs the genuine
`op.drop_column`, which makes the column actually absent, then re-upgrades, at
which point the guard lets `op.add_column` execute for real — and it asserts
child-row survival in `experience_title`, `bullet` and `experience_summary_item`
either side. So the property the no-`batch_alter_table` choice exists to protect
**is** empirically verified, just by a test whose name is about the drop.

Whether the same holds for 0011/0013/0015 was **not** checked. That is the open
question here.

**Why it is worth fixing rather than just knowing:** a test named
`..._adds_..._no_row_loss` reads, to the next agent, as proof that the ADD path is
covered. It is exactly the "green means checked" inference C-7 rule 3 warns about,
one level up from a rerun-masked pass.

Candidate responses, in increasing cost:
1. Rename the affected tests to say what they verify (cheapest, no behavior claim
   changes).
2. Have the upgrade-direction tests drop the column first, so the ADD path is
   genuinely exercised under its own name — mirroring what the downgrade test
   already achieves incidentally.
3. Make 0001 build from a pinned historical schema rather than live metadata.
   Largest blast radius; almost certainly not worth it.

Filed as a first observation of this class. Under charter **C-11** a note is a
compliant response once; a second instance owes a mechanism that fails closed.

**Related:** `db/migrations/versions/0016_experience_is_active.py`'s own module
docstring already discloses the underlying `create_all` behavior in its
idempotency paragraph — the disclosure existed, its consequence for test naming
did not.

## Updates

### 2026-08-08 — filed on `fix/experience-soft-retire` (sprint A1b review finding, non-blocking)
