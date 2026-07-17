# Ledger

Append-only JSONL, one shard file per **writing session** —
`<session-uuid>.jsonl` — never a single shared file (concurrent sessions
would merge-conflict on it). Written and read exclusively by
`scripts/verify_doc_template.py`; see `docs/dev/prov/SPEC.md` §3 for the
exact event schema and `docs/dev/handoffs/README.md` for how handoff
generation/consumption drives these events.

Reads join across every shard on demand (`docs/dev/ledger/*.jsonl`) —
there is no second, aggregated copy of this data anywhere.

Full schema and rationale: `docs/dev/prov/SPEC.md`. Design record + why
this exists: `docs/dev/handoff-integrity-design.md`.
