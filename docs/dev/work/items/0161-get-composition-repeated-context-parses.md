```toml
schema = 1
id = 161
kind = "item"
title = "GET /composition parses the same context file about eleven times per request"
status = "closed"
decision_owner = "agent"
branches = ["fix/frozen-composition-staleness", "fix/compose-single-context-parse"]
refs = [
  "blueprints/applications.py",
  "docs/dev/blast-radius/frozen-composition-staleness.md",
  "docs/dev/diagnosis/compose-single-context-parse.md",
  "tests/test_composition_single_context_read.py",
]
summary = "Each _read_* helper re-reads and re-parses the context JSON; one parse could serve them all."
resolution = "2026-10-15, fix/compose-single-context-parse: measured first (11 reads per GET at the p50, p90 and max local context sizes, 67 / 131 / 205 KB), then one _load_compose_context per GET feeding eleven pure helpers. Same instrument, before to after: reads 11 to 1; the helper block 12.5 / 19.9 / 23.2 ms to 2.0 / 1.7 / 1.9 ms median; the whole GET on an empty-corpus fixture 21.5 / 29.9 / 29.0 ms to 6.3 / 7.8 / 7.2 ms (one run each, not interleaved). A context that is valid JSON but not an object no longer 500s. Declared limit: the share of a real GET the block was is overstated by the fixture's empty database; the absolute block figures are the ones to trust."
verified_by = [
  "tests/test_composition_single_context_read.py::test_get_composition_reads_the_context_file_exactly_once",
  "tests/test_composition_single_context_read.py::test_get_composition_degrades_on_a_non_object_context",
]
```

`get_application_composition` (`blueprints/applications.py`) calls a dozen `_read_*` helpers
(`_read_composition_overrides`, `_read_bullet_order`, `_read_recommendations_and_added`,
`_read_summary_overrides`, `_read_summary_draft`, `_read_gap_fill`, `_read_title_overrides`,
`_read_experience_summary_overrides`, `_read_experience_summary_drafts`,
`_read_skill_composition`, and `fix/frozen-composition-staleness`'s `_read_freeze_state`), and each
validates, reads and `json.loads` the same context file. Compose calls this route on every
arrival and after most Compose actions (the re-render cascade), so the cost repeats.

Counted from the code, not measured. A measurement (parse time × count at a realistic context
size) belongs with the fix. The fix shape: read once with the containment check, pass the dict
to the helpers.

## Updates

### 2026-10-10 — filed on `fix/frozen-composition-staleness`

That branch added the eleventh parse (`_read_freeze_state`, about one context read) and
deferred the consolidation rather than widening its scope (blast-radius dossier, `## Deferred`).

### 2026-10-15 — closed on `fix/compose-single-context-parse`

Measured before fixing (C-7), per this item's own note that the count was from the code: **11
reads per GET at all three sizes**. The block cost 1.4–2.3× eleven bare read+parse units, so the
item's "eleven parses" framing under-described it; the remainder is not attributed. The fix is
one `_load_compose_context` and eleven helpers that take the loaded dict. After: 1 read, block
about 2 ms. The guard test fails on `main` (`11 != 1`) and fails again if a twelfth helper opens
the file itself. Full record, instrument source and the pre-registered predictions:
`docs/dev/diagnosis/compose-single-context-parse.md`.

Not claimed: that the response is now a consistent snapshot of the file under a concurrent POST
(dossier I-1, inferred only).
