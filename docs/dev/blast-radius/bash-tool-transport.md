# Blast radius — bash-tool-transport

> **Branch:** `fix/bash-tool-transport`
> **Status:** enumeration complete, written before the first production edit (2026-10-08).

---

## Surface

A new Bash guard, `block-long-bash-command` (item 158). It grows the Bash dispatcher's roster
from six to seven and the enforced blocker rules from 13 to 14.

- **New** `scripts/enforcement/guards/block_long_bash_command.py` (`decide`, `claude_check`).
- `scripts/enforcement/adapters/claude_hook.py`, `_GUARD_MODULES`: one entry.
- `scripts/enforcement/adapters/bash_dispatcher.py`, `_GUARD_ORDER`: one name appended, plus
  the docstring and comment that name the guards.
- The governance tests that pin the guard sets and counts, and the docs that list the guards.
- `scripts/enforcement/guards/block_doubled_backslash.py`: the docstring's "Known limits" only.
  The decision logic does not change.

**`.claude/settings.json` does not change.** Item 157's proposed `env` `MSYS=noglob` is
falsified (`docs/dev/diagnosis/bash-tool-transport.md` O3). The single `bash-dispatcher` entry
already runs everything in `_GUARD_ORDER`. No entry in `scripts/enforcement/blast_radius.py`
`GATED` or `GATED_PREFIXES` is edited: `guards/result.py` is imported only.

---

## Enumeration

Run 2026-10-08 on `fix/bash-tool-transport` at `38cec69` (no commits yet), with ripgrep through
Claude Code's Grep, over the whole tree. History-only paths were excluded:
`docs/dev/handoffs/**`, `docs/dev/diagnosis/**`, `docs/dev/blast-radius/**`,
`docs/dev/ledger/**` and `docs-site/**` (generated). The item-142 dossier's searches were the
starting point, re-run rather than trusted.

1. **The registry symbols:**
   `_GUARD_ORDER|_GUARD_MODULES|_GUARD_NAMES|BLOCKER_RULE_NAMES|BASH_DISPATCHED_GUARD_NAMES|_BINDS_NON_CLAUDE_AGENTS|EXTRACTION_GAP`.
   60 hits in 13 files:
   - live code: `claude_hook.py` (6), `claude_dispatcher.py` (4), `bash_dispatcher.py` (5),
     `interrogative_witness.py` (1);
   - tests: `test_governance_hooks_gate.py` (19), `test_enforcement_coverage.py` (8),
     `test_enforcement_core.py` (3), `test_evidence_gate.py` (3),
     `test_consumer_enumeration_gate.py` (3);
   - prose: `docs/dev/tooling.md` (1);
   - history: `epic-a-chain-design-corrections.md` (5), `RELEASE_ARC.md` (1), item 0094 (1).
2. **The sibling guard's names:** `block-doubled-backslash|block_doubled_backslash`. These are
   the closest precedent, a Claude-only, win32-only Bash guard. Live registers:
   - `CLAUDE.md` 156 and 185;
   - `claude_hook.py:58`;
   - `bash_dispatcher.py` 7 and 57;
   - `docs/governance/enforcement.md` 142 and 180;
   - `docs/dev/tooling.md:76`;
   - the wiki pages `consistency-tracks-enforcement.md:139` and `governance-extraction.md:151`;
   - `test_enforcement_core.py` (42, 1222-1294);
   - `test_enforcement_coverage.py` 59 and 126;
   - `test_governance_hooks_gate.py` 132, 178, 216 and 309.

   Records, not registers: `docs/wiki/log.md:2594`, `BOARD.md:207`, items 0142 and 0157, and
   `tests/test_bash_backslash_collapse.py:18`, which this branch already updated to name the
   new guard.
3. **The counts:**
   `(six|6) (Bash|bash)|six Bash-matcher|dispatcher runs six|[Tt]hirteen|THIRTEEN|13 (enforced|blocker)|== 13|all (four|five|six) guards|(four|five|six) guards`.
   - Relevant:
     - `CLAUDE.md:183`;
     - `docs/dev/tooling.md:47`;
     - `docs/governance/enforcement.md:229`;
     - `test_governance_hooks_gate.py` 132, 162 and 305-306.
   - Not related:
     - `blueprints/applications.py:13` ("thirteen routes");
     - `static/vendor/paged.polyfill.js:4292`;
     - `test_enforcement_core.py:1066` (the Edit|Write dispatcher's comment);
     - item 0050:23, which counts `git_hook.py`'s six guards, not the Bash dispatcher's;
     - `docs/wiki/log.md:2594`, a dated record.
4. **The tooling-roster lint:** `scripts/doc_lints.py:477` derives each guard's name as
   `p.stem.replace("_", "-")` from `scripts/enforcement/guards/*.py`. So
   `tests/test_doc_lints.py` fails until `docs/dev/tooling.md` has a `block-long-bash-command`
   row.
5. **The CHANGELOG precedent:** `CHANGELOG.md:131` has an "Added" bullet for
   `block-subagent-git-stash`. Item 142's `block-doubled-backslash` has none: 0 hits for
   `item 142|doubled backslash` in `CHANGELOG.md`.
6. **Readers of `CLAUDE_PROJECT_DIR`** (`test_evidence_gate.py:308-337` pins that reader set):
   the new guard reads only `tool_input.command` and `sys.platform`.
7. **Other routing:**
   - `git_hook.py`, `.githooks/*` and CI never receive a Bash-tool command (unchanged since
     the item-142 dossier's search 6, re-read: `git_hook.py` imports six guards, item 0050:26).
   - `.claude/settings.json` has the single PreToolUse `Bash` entry
     `hook.py bash-dispatcher` (read in full, lines 38-47).

---

## Consumers

| # | Site (`path:line`) | Decision | Rationale |
|---|---|---|---|
| 1 | `scripts/enforcement/guards/block_long_bash_command.py` (new) | create | The guard: `len(command) + 4 × command.count("'")` against a budget, O(n), with no subprocess and nothing to parse. It does not import `shell_split` and does not read `CLAUDE_PROJECT_DIR`. |
| 2 | `scripts/enforcement/adapters/claude_hook.py:45-59` | update | Add the `_GUARD_MODULES` entry, which `dispatch()` imports lazily. |
| 3 | `scripts/enforcement/adapters/bash_dispatcher.py:47-58` | update | Append to `_GUARD_ORDER`, with a dated comment. There is no short-circuit, so order only affects message order. |
| 4 | `scripts/enforcement/adapters/bash_dispatcher.py:5-7` | update | The docstring names the Bash guards. |
| 5 | `tests/test_governance_hooks_gate.py:164-180` `BLOCKER_RULE_NAMES` | update | Add the name. |
| 6 | `tests/test_governance_hooks_gate.py:305-311` (and comment `:162`) | update | 13 → 14, and say why. A deliberate governance change, owner-directed (item 158, 2026-10-08). |
| 7 | `tests/test_governance_hooks_gate.py:131-137` | update | A dated "Amended 2026-10-08" paragraph after item 142's, following convention. |
| 8 | `tests/test_governance_hooks_gate.py:209-218` `BASH_DISPATCHED_GUARD_NAMES` | update | Add the name. `:351` (set equality with `_GUARD_ORDER`) and `:316` (superset) then pass. |
| 9 | `tests/test_enforcement_core.py:41-51` | update | Import the module for its unit tests. |
| 10 | `tests/test_enforcement_core.py:1265-1273` | update | The exact Bash set. |
| 11 | `tests/test_enforcement_core.py` (new class, plus dispatcher cases in `TestBashDispatcher`) | create | `TestBlockLongBashCommandUnit`. Dispatcher cases: block on win32, allow off it (Linux CI runs the allow path). |
| 12 | `tests/test_enforcement_coverage.py:41-61` `_BINDS_NON_CLAUDE_AGENTS` | update | `False`, Claude Code only by nature: the cut is in how the Bash tool starts bash, which no git hook sees. |
| 13 | `tests/test_enforcement_coverage.py:125-132` `EXTRACTION_GAP` | update | Insert the stem in sorted order. |
| 14 | `docs/governance/enforcement.md:142` | update | The Claude-only row must contain the stem literally (`test_enforcement_coverage.py:134-142`). |
| 15 | `docs/governance/enforcement.md` (after `:180-191`) | update | A per-guard paragraph, following the item-142 precedent: what it catches and its known limits. |
| 16 | `docs/governance/enforcement.md:229` | update | "a Bash dispatcher runs six" → "seven". |
| 17 | `docs/dev/tooling.md:76` | update | A new row after `block-doubled-backslash`, which the roster lint requires. |
| 18 | `docs/dev/tooling.md:47` | update | "the six Bash guards" → "seven". |
| 19 | `docs/dev/tooling.md:15` | update | The re-derivation stamp → this branch. |
| 20 | `CLAUDE.md:156-162` | update | A hook-list bullet after `block-doubled-backslash`. |
| 21 | `CLAUDE.md:183-185` | update | "The six Bash-matcher guards (…)" → seven, and add the name. |
| 22 | `scripts/enforcement/guards/block_doubled_backslash.py:28-31` | update (docstring only) | Its "Known limits" says `MSYS=noglob` reaching the harness would remove the guard's premise. O3 shows it would break quoting instead. The decision logic is unchanged. |
| 23 | `CHANGELOG.md` `[Unreleased]` | update | A section for this branch, following `:131`'s precedent for a new Bash guard. |
| 24 | `scripts/enforcement/guards/result.py` | no change | Imported only (`GuardResult`). It is a GATED surface, and this branch does not edit it. |
| 25 | `scripts/enforcement/shell_split.py` | no change | The new guard does not import it. |
| 26 | `.claude/settings.json` | no change | Item 157 falsified (dossier O3). It already runs everything in `_GUARD_ORDER`. |
| 27 | `scripts/enforcement/adapters/hook.py` (`HOOKS`) | no change | `bash-dispatcher` is unchanged. |
| 28 | `scripts/enforcement/adapters/claude_dispatcher.py`, `interrogative_witness.py:28` | no change | The Edit/Write roster and its prose. |
| 29 | `test_evidence_gate.py`, `test_consumer_enumeration_gate.py` | no change | They assert other names' membership, and the `CLAUDE_PROJECT_DIR` reader set (search 6). |
| 30 | `AGENTS.md` | no change | It does not list Bash guards. |
| 31 | `docs/wiki/pages/consistency-tracks-enforcement.md:139`, `governance-extraction.md:151` | decided by the scoped wiki pass at close-out | These list the Claude-only guards. Any mention uses the guard's bare name (the item-142 precedent), so `scripts/wiki_relevance.py` stays untouched. |
| 32 | `tests/test_bash_backslash_collapse.py` | update (already, in the instrument) | Its docstring names the new guard as the second guard whose premise it pins. Commit 2 adds a cross-check that the guard's cut constant equals the measured 8,186. |

---

## Deferred

Pre-existing drift, outside items 157 and 158. Each goes into the handoff's declared-not-filed
list:

- **`docs/governance/enforcement.md:29-31` says "8 exist"**, carried from the item-142 dossier.
  There are 13 rules, 14 after this branch. No test checks it.
- **`tests/test_enforcement_core.py`'s `TestBashDispatcher` docstring (`:1261-1263`)** names
  four guards, carried. It is a comment only.
- **`scripts/enforcement/blast_radius.py`'s `result.py` entry says "10 non-test importers"**,
  carried. This branch adds one more importer. Editing `blast_radius.py` is itself a gated
  surface, and the count is incidental here.
- **Item 142's `block-doubled-backslash` has no CHANGELOG entry** (search 5). New this branch.
  Back-filling another item's record is outside 157/158; it is flagged to the owner.
- **`scripts/wiki_relevance.py` `RELEVANT_OVERRIDES`.** It changes only if the scoped wiki pass
  needs a by-path cite, and gets a row here before any edit.

---

## Verification

- **Exact-set assertions fail loudly on a missed registry site:**
  - `test_governance_hooks_gate.py`: the :305 count, the :351 set equality and the :316
    superset;
  - `test_enforcement_core.py`'s exact Bash set;
  - `test_enforcement_coverage.py`: `TestClassificationIsComplete` (every `guards/*.py`
    classified), `TestTheExtractionGapIsPinned`, and the literal-in-`enforcement.md` check.
- **The tooling roster:** `tests/test_doc_lints.py::test_real_tree_has_no_blocks`.
- **The command shape:** `tests/test_settings_hooks_python_direct.py` proves `settings.json` was
  correctly left alone.
- **The prose counts** (rows 16, 18 and 21) have no test. They are checked by re-running search 3
  after the edit.
