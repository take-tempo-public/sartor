# skills/

Mirrors the `commands/`/`agents/` root-level convention (kit-adoption
commitment 3, `KIT-5`). No plugin-manifest entry is needed — this family
auto-discovers from the root dir the same way `commands/`/`agents/` do.

- **`doc-writing/`** — writes or revises a Sartor doc in the order the docs IA
  requires (tier and type, rung, header, cite-don't-restate, registration), then runs the
  doc lints. It orders the rules and restates none of them
  ([`docs/dev/docs-ia-design.md`](../docs/dev/docs-ia-design.md) §5.10).
- **`context-structure-review/`** — audits a repo's markdown/agent-instruction
  files against context-engineering best practices (progressive disclosure,
  just-in-time loading, document structure, instruction-file hygiene,
  freshness, secrets hygiene). Imported from the external agent-coding-practices
  kit (see [`docs/dev/archive/kit-adoption-design.md`](../docs/dev/archive/kit-adoption-design.md)
  §3 Decision 5, §4 Phase 5); kit source path recorded in `CLAUDE.local.md`.
