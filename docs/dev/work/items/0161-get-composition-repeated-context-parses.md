```toml
schema = 1
id = 161
kind = "item"
title = "GET /composition parses the same context file about eleven times per request"
status = "open"
decision_owner = "agent"
branches = ["fix/frozen-composition-staleness"]
refs = [
  "blueprints/applications.py",
  "docs/dev/blast-radius/frozen-composition-staleness.md",
]
summary = "Each _read_* helper re-reads and re-parses the context JSON; one parse could serve them all."
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
