# skills/

Mirrors the `commands/`/`agents/`/`hooks/` root-level convention (kit-adoption
commitment 3, `KIT-5`). No plugin-manifest entry is needed — this family
auto-discovers from the root dir the same way `commands/`/`agents/` do.

- **`context-structure-review/`** — audits a repo's markdown/agent-instruction
  files against context-engineering best practices (progressive disclosure,
  just-in-time loading, document structure, instruction-file hygiene,
  freshness, secrets hygiene). Imported from the external agent-coding-practices
  kit (see [`docs/dev/kit-adoption-design.md`](../docs/dev/kit-adoption-design.md)
  §3 Decision 5, §4 Phase 5); kit source path recorded in `CLAUDE.local.md`.
