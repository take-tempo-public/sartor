# Handoffs

One file per branch, frozen once written — never edited after the closing
agent commits it. A correction is a new, explicitly superseding note, not
an edit to the original (append-only history).

- **Filename:** `<branch-slug>.md` (e.g. `feat-handoff-integrity-kit.md`).
- **Content:** built from `docs/dev/AGENT_HANDOFF_TEMPLATE.md`, stamped
  per `docs/dev/prov/SPEC.md` §1, validated with
  `python scripts/verify_doc_template.py <file> docs/dev/AGENT_HANDOFF_TEMPLATE.md --event generated ...`
  before commit.
- **The pointer.** The closing agent gives the user ONE line as copyable
  chat text — path + branch + short commit hash — never the file's full
  content. This is the transfer-by-reference fix for the handoff
  corruption `docs/dev/handoff-integrity-design.md` exists to prevent:
  content that must survive verbatim travels as a committed file, not
  through a clipboard.
- **Consumption.** The next agent reads the pointed-to file directly (not
  a chat paste) and runs the same validator with `--event consumed` as
  its first action. See `docs/dev/prov/SPEC.md` §5 for the full workflow
  and what a `blocked` result means.

Full schema and rationale: `docs/dev/prov/SPEC.md`. Design record:
`docs/dev/handoff-integrity-design.md`.
