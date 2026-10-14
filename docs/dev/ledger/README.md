# Ledger

Append-only JSONL, one shard file per **writing session** —
`<session-uuid>.jsonl` — never a single shared file (concurrent sessions
would merge-conflict on it). The document events (`generated`, `consumed`,
`failed`, `blocked`) are written and read by `scripts/verify_doc_template.py`.
Two hook-originated events, `compacted` and `plan-archived`, are appended by
`claude_context_hook.py` and `plan_gate.py`; while HEAD is on trunk those go to
an untracked spool under `.claude/state/ledger/` instead of this directory (item
165). See `docs/dev/prov/SPEC.md` §3 for the exact event schema and
`docs/dev/handoffs/README.md` for how handoff generation/consumption drives the
document events.

Reads join across every shard on demand (`docs/dev/ledger/*.jsonl`) —
there is no second, aggregated copy of this data anywhere.

Full schema and rationale: `docs/dev/prov/SPEC.md`. Design record + why
this exists: `docs/dev/handoff-integrity-design.md`.
