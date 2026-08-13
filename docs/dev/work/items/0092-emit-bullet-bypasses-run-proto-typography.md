```toml
schema = 1
id = 92
kind = "item"
title = "generator.emit_bullet bypasses run-proto typography — bullets inherit no template fonts at all"
status = "watching"
decision_owner = "agent"
branches = ["fix/b1-education-render"]
refs = [
  "generator.py",
  "docs/dev/blast-radius/b1-education-render.md",
]
summary = "Bullets bypass the run-proto path, so no captured template typography (size/bold/font) applies to them."
```

**Origin.** Observed by B1b's implementer while closing the font-name
capture gap (blast-radius dossier `## Deferred` via the implementer report),
handed to the closer for filing, filed by the invoking session at the sprint
gate (closer's `itemsFiled` was empty — recorded in item 84's run evidence).

**The gap.** `generator.emit_bullet` calls `_add_inline_runs`, not
`_add_inline_runs_with_proto`, so bullet paragraphs inherit no template
typography — this predates B1b (size/bold were already not applied) and now
also means bullets get none of the captured `run_font_name`. B1b's font
tests deliberately assert nothing about bullets.

**Why deferred rather than fixed in B1b.** Extending proto application to
bullets changes which paragraphs receive template typography — a
rendering-policy change with visible output differences across every
persona, not a capture-gap fix. It needs its own before/after review of
rendered output, not a ride-along on an evidence-first `fix/*` branch.

## Updates

### 2026-08-13 — filed during `fix/b1-education-render` (B1b) by the invoking session
