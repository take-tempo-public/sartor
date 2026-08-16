```toml
schema = 1
id = 98
kind = "item"
title = "Wiki freshness measures checkpoint-staleness, not page-staleness: scoped close-outs never credit the checkpoint, and agents report commit counts instead of the gate's figure"
status = "open"
decision_owner = "agent"
branches = ["epic/b-render-ats"]
refs = [
  "scripts/wiki_freshness.py",
  "scripts/wiki_relevance.py",
  "docs/wiki/.last_ingest_sha",
  "docs/wiki/log.md",
  "commands/wiki-self-update.md",
  "docs/dev/AGENT_HANDOFF_TEMPLATE.md",
  "scripts/verify_doc_template.py",
  "docs/dev/handoffs/feat-ats-conformance-b2-landed.md",
]
summary = "Drift only grows between full ingests; agents report commits, not the gate. Build: coverage ledger + generated figure."
```

**Owner direction (2026-08-15, design-sprint sync):** "1 & 3 it is. add it to the board and we
can test with it and some open ledger items before running the epics." — i.e. this item is
one of the first cards the factory runs against sartor, ahead of Epics C/D/E.

## The defect, measured (not reasoned)

Two wiki-update mechanisms exist and **only one moves `.last_ingest_sha`**:

- The **full loop** (`/wiki-ingest`, full `/wiki-self-update`) diffs `.last_ingest_sha..HEAD`,
  edits pages, and advances the checkpoint.
- The **scoped per-branch close-out check** — the "incremental" step the close-out checklist
  mandates — diffs only the branch's own slice, edits pages, logs a verdict to `log.md`, and
  **by its own rule never advances the checkpoint** ("advancing would misrepresent the backlog
  as checked", C-12 — see every `log.md` entry from 2026-07-30 `65b0f88` onward, including the
  2026-08-14 B2 entry).

Consequence: **drift is monotonic by design.** Scoped passes keep the *pages* current but never
credit their coverage back to the checkpoint, so `wiki_freshness.py`'s count only grows until a
full pass. Verified at `a85a559`: `python scripts/wiki_freshness.py` → `OK — 33 file(s) changed
since the last ingest (< 75-file block threshold)`; the 33 (listed via
`git diff --name-only f42b2ea HEAD` piped through `is_wiki_relevant()`) are every relevant path
touched since the 2026-08-10 full pass — **all of which the scoped passes already inspected**
(B2's alone edited 7 pages against them). The number is true for what it measures
(checkpoint-staleness) and misleading for what every reader takes it as (page-staleness).

**Coupled reporting defect:** agents report a raw commit count (`git rev-list --count
<sha>..HEAD`) as if it were the gate's measure — "64-commit un-ingested window"
(`feat-ats-conformance-b2-landed.md`), "73 commits behind" (2026-08-15 sync chat) — and predict
the gate will fire on the Epic B PR. It will not (33 < 75, exit 0). `log.md` 2026-08-08 records
the same class ("predicting a drift count instead of running the classifier"), so this is a
**recurrence** and under charter C-11 obligates a mechanism, not a note. Cost: catch-up ingests
run against a misread number that then report they weren't needed.

**Owner's assumptions, checked:** (a) "incremental should mean the gate never fires unless
something is wrong" — correct as a goal, not how it is built. (b) "33 accumulated = incremental
is missing things" — no: not evidence of misses; evidence that coverage is recorded in prose no
gate reads. (c) "`.last_ingest_sha` is poorly configured; the close-out steps on its own toes" —
yes: a scalar SHA cannot represent per-slice coverage.

## What to build (owner-selected: options 1 + 3)

1. **Coverage ledger replaces the scalar checkpoint as the gate's source of truth.** Each scoped
   close-out appends a schema-versioned record — branch range (`base..tip`), relevant paths
   inspected, per-path verdict (`edited` / `verified-no-edit`), pages touched — to a JSONL under
   `docs/wiki/` (charter I-14-style: schema before tool). `wiki_freshness.py` computes drift as
   *relevant paths since the last full ingest **minus** paths covered by ledger records* and
   prints `N relevant / M covered / K un-inspected` — the count finally means "un-inspected
   relevant paths", and a clean incremental close-out drives it to ~0. `.last_ingest_sha` stays
   as the full-pass anchor.
2. **Generated, never hand-typed drift figure (the C-11 mechanism for the reporting recurrence).**
   `wiki_freshness.py --json`; the handoff template's wiki-freshness line is *generated* from it
   (the same discipline as `print_handoff_pointer.py`), and `verify_doc_template.py` refuses a
   hand-typed drift number. Any agent statement of drift that is not the tool's output is
   non-committable.

**Consumers to enumerate before the first edit (C-10):** `wiki_freshness.py` is imported by
`scripts/enforcement/guards/block_merge_to_main.py` and re-run by
`tests/test_wiki_freshness_gate.py`; the reminder hook `hooks/wiki-freshness-reminder.sh`
computes the same drift; `commands/wiki-self-update.md` / `wiki-ingest.md` / `wiki-lint.md`
write the log and checkpoint; the handoff template + `verify_doc_template.py` carry the
reported figure. Blast-radius dossier owed on the implementing branch.

## Updates

### 2026-08-15 — filed during the item-97 design-sprint sync (on `epic/b-render-ats`)

Filed at the owner's direction after the measurement above. Diagnosis also captured in session
memory `reference-wiki-checkpoint-ratchet-defect`. Not implemented; queued as an early factory
test card alongside other open ledger items, ahead of Epics C/D/E.
