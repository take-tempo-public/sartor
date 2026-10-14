```toml
schema = 1
id = 166
kind = "item"
title = "The wiki scribe/auditor pair keeps passing defects that review then catches, including mechanically checkable ones"
status = "closed"
decision_owner = "agent"
branches = ["fix/recurrence-guardrails"]
refs = [
  "agents/wiki-grounding-auditor.md",
  "agents/wiki-scribe.md",
  "commands/wiki-self-update.md",
  "docs/wiki/log.md",
  "docs/wiki/SCHEMA.md",
  "tests/test_wiki_relevance_classification.py",
  "docs/dev/diagnosis/recurrence-guardrails.md",
]
summary = "No deterministic cite check exists; review, not the auditor, caught line cites, a removed cite and a false claim."
resolution = "2026-10-14, fix/recurrence-guardrails (owner decision: all three parts). scripts/wiki_cites.py is a deterministic, stdlib-only check: a cited symbol the file does not contain (E3) and a line cite past the end of its file (E2) fail, bare line cites are ratcheted per page (E1, 25 existing across 8 pages, exact counts), and a symbol cite removed while its target still exists is listed (E4, --base). E1-E3 ride the pytest gate; E4 runs in /wiki-self-update, where the orchestrator can restore it. The auditor moved to Sonnet 5 with four explicit checks, and the command gained an explicit review step that is prose and labeled unenforced. Semantic misses (inversions, intent, placement, false evidence) are not mechanically checkable."
verified_by = [
  "tests/test_wiki_cites.py::TestE3SymbolCites",
  "tests/test_wiki_cites.py::TestE2LineRange",
  "tests/test_wiki_cites.py::TestE1LineCitesAreCounted",
  "tests/test_wiki_cites.py::TestE4RemovedCites",
  "tests/test_wiki_cites.py::TestTheRealTree",
]
```

**Observed** (`docs/dev/diagnosis/recurrence-guardrails.md` O4). Three consecutive scoped
passes (`docs/wiki/log.md:2699`, `:2737`, `:2784`) record orchestrator review catching defects
the auditor passed, each with a "Retune signal". Both agents are pinned to `claude-haiku-4-5-20251001`
(`agents/wiki-grounding-auditor.md:4`, `agents/wiki-scribe.md:4`). `/wiki-lint` checks only
that a cited file exists; `scripts/check_doc_links.py` does not cover `docs/wiki/`.

**Owner decision (2026-10-14):** three parts. A deterministic cite check
(`scripts/wiki_cites.py`), the auditor moved to Sonnet 5, and an explicit orchestrator review
step in `commands/wiki-self-update.md`. The review step is prose and is declared
**unenforced** (C-11); semantic misses (inverted behavior, invented UI, false evidence) are
not mechanically checkable (C-0).

## Updates

### 2026-10-14 — filed on `fix/recurrence-guardrails`

The retune rule in `commands/wiki-self-update.md:121` has fired three times running without a
response (`docs/wiki/log.md` records each); this is the response.

### 2026-10-14 — closed on `fix/recurrence-guardrails`

Built and measured on the real tree (`docs/dev/diagnosis/recurrence-guardrails.md` O15, O16):
44 pages, 727 symbol cites (every one resolved to a tracked file), 25 bare line cites across 8
pages (11 `path:N` and 14 prose `line N`; now the exact ratchet), and no real E2 or E3
violation. The first run produced six false E3 hits
(a link whose label is a file name, such as `parser.py`, read as a symbol), fixed and pinned
by a test. A
violation seeded into a real page in memory fired E1, E2 and E3.

**What the check does not do (C-0), and what carries it instead:** whether a sentence is true.
The three logged passes' semantic misses (an inverted effect, an invented UI placement, a
false piece of evidence, a branch claim) are for the auditor's four new explicit checks and for
step 6 of `commands/wiki-self-update.md`, which is prose and labeled **unenforced**. Not
measured: whether Sonnet 5 catches more than Haiku did, or what it costs per pass; the next
pass's three separately-logged catch counts are how that gets answered.

**Deviation from the plan:** no separate `scripts/gate.py` step. The check is a pytest test, so
the gate's `pytest` step and CI already run it, as for `wiki_freshness`.
