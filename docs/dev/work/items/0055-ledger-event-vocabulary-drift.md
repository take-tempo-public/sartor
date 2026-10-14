```toml
schema = 1
id = 55
kind = "item"
title = "Ledger event vocabulary has drifted from docs/dev/prov/SPEC.md without amendment"
status = "closed"
decision_owner = "agent"
branches = ["fix/recurrence-guardrails"]
refs = [
  "docs/dev/prov/SPEC.md",
  "scripts/enforcement/adapters/claude_context_hook.py",
  "hooks/lib/retire-approved-plan.sh",
  "docs/dev/blast-radius/recurrence-guardrails.md",
]
summary = "compacted (2026-07) and plan-archived (2026-08-07) both ship as ledger events SPEC.md's own vocabulary list never names."
resolution = "2026-10-14, fix/recurrence-guardrails. docs/dev/prov/SPEC.md section 3 now names compacted and plan-archived, their fields, and where a hook-originated receipt goes, under a C-10 dossier (docs/dev/blast-radius/recurrence-guardrails.md). A scan test makes the next hook-emitted event without a SPEC entry fail."
verified_by = ["tests/test_ledger_spool.py::TestSpecNamesTheHookEvents"]
```

`docs/dev/prov/SPEC.md` §3 documents the ledger's event vocabulary as
`generated`, `consumed`, `failed`, `blocked`. Two emitting modules have since
added an event without amending that list:

1. `scripts/enforcement/adapters/claude_context_hook.py`'s `record_compaction()`
   writes `"event": "compacted"` (charter C-12, landed
   `feat/enforcement-first-governance`).
2. `hooks/lib/retire-approved-plan.sh`'s `retire_approved_plan()` writes
   `"event": "plan-archived"` (item 45's fix, `fix/plan-approval-marker-pr-merge`,
   2026-08-07) — the archive-not-delete reconciler's receipt.

Both were deliberate, reasoned decisions **at the time**, not oversights: SPEC.md
is itself a C-10 **gated surface**
(`scripts/enforcement/blast_radius.py:98-103`, "provenance stamp + ledger
schema; every ledger shard and scripts/verify_doc_template.py are written
against it"), so amending it drags `require-consumer-enumeration` across every
ledger consumer — a real cost that was each time judged disproportionate to a
bugfix branch adding one narrow, well-scoped event. `plan-archived` explicitly
followed `compacted`'s own precedent rather than re-deciding the trade-off.

**The drift itself is the finding.** Two independent branches making the same
locally-reasonable call means the vocabulary list in SPEC.md is no longer a
reliable enumeration of what a ledger reader might see — a future consumer
(a script, a dashboard, an audit) that trusts SPEC.md's four-item list as
exhaustive will silently miss two real event kinds already in production
shards. Filed per C-11/C-12 ("declare the gap; never fill it silently") rather
than absorbed into either originating branch's own scope.

**Not fixed here.** A proper fix is itself the C-10 enumeration this item is
flagging the cost of — grep every ledger reader (`scripts/verify_doc_template.py`,
any dashboard/audit tooling) for its own assumptions about the event set before
amending SPEC.md, on a dedicated branch with a `docs/dev/blast-radius/` dossier.

## Updates

### 2026-08-07 — filed during `fix/plan-approval-marker-pr-merge` (found while adding `plan-archived`)

### 2026-10-14 — closed on `fix/recurrence-guardrails`

Closed by item 165's SPEC amendment. The reader enumeration this item asked for is in
`docs/dev/blast-radius/recurrence-guardrails.md` (the ledger-dir and `compacted` rows): the one
reader of the shards, `scripts/verify_doc_template.py` (`read_ledger` and
`latest_generated_fingerprint`), filters on the document events and ignores the two hook
events, so no reader assumption broke.
