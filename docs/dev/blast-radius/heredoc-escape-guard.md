# Blast radius — heredoc-escape-guard

> **Branch:** `fix/heredoc-escape-guard`
> **Status:** enumeration complete, written before the first production edit (2026-10-07).

---

## Surface

A new Bash guard, `block-doubled-backslash`, which grows the Bash dispatcher's roster from five
to six and the enforced blocker rules from 12 to 13:

- **New** `scripts/enforcement/guards/block_doubled_backslash.py` (`decide`, `claude_check`).
- `scripts/enforcement/adapters/claude_hook.py`, `_GUARD_MODULES`: one entry.
- `scripts/enforcement/adapters/bash_dispatcher.py`, `_GUARD_ORDER`: one name appended, plus
  the docstring and comment that name the guards.
- The governance tests that pin the guard sets and counts, and the docs that list the guards.

`.claude/settings.json` does **not** change. The single `bash-dispatcher` entry already runs
everything in `_GUARD_ORDER`. No gated surface in `scripts/enforcement/blast_radius.py`
`GATED` is edited; see `## Deferred` for `scripts/wiki_relevance.py`.

---

## Enumeration

Run 2026-10-07 on `fix/heredoc-escape-guard` at `e770281`. The tool was ripgrep through Claude
Code's Grep, over the whole tree. History-only paths were excluded:
`docs/dev/handoffs/**`, `docs/dev/diagnosis/**`, `docs/dev/blast-radius/**`, `CHANGELOG.md`,
`docs-site/**` (generated), `docs/dev/ledger/**`, and `docs/wiki/log.md`.

1. **The registry symbols:**
   `_GUARD_ORDER|_GUARD_MODULES|_GUARD_NAMES|BLOCKER_RULE_NAMES|BASH_DISPATCHED_GUARD_NAMES|_BINDS_NON_CLAUDE_AGENTS|EXTRACTION_GAP`.
   - Live code and tests: `claude_hook.py` (45, 59, 71-87), `claude_dispatcher.py` (52-70),
     `bash_dispatcher.py` (19, 47-64), `test_consumer_enumeration_gate.py` (20, 216, 219),
     `test_enforcement_core.py` (1081-1082, 1203), `test_enforcement_coverage.py` (41-139),
     `test_evidence_gate.py` (35, 237, 265), `test_governance_hooks_gate.py` (50-344).
   - Prose: `interrogative_witness.py:28`, `docs/dev/tooling.md:18`.
   - History: `epic-a-chain-design-corrections.md` (1548-1867), `RELEASE_ARC.md:1353`, item 0094.
2. **The sibling guard's names:** `block-subagent-git-stash|block_subagent_git_stash`, the
   closest precedent, a Claude-only Bash guard. It turned up these registers:
   - `CLAUDE.md` 150 and 178;
   - `docs/governance/enforcement.md` 142 and 171;
   - `docs/dev/tooling.md:75`;
   - `bash_dispatcher.py` 6 and 54;
   - `claude_hook.py:57`;
   - `scripts/wiki_relevance.py:137`;
   - `docs/wiki/pages/consistency-tracks-enforcement.md:139` and
     `docs/wiki/pages/governance-extraction.md:151`;
   - `test_enforcement_core.py` (44, 1164-1230);
   - `test_enforcement_coverage.py` 57 and 124;
   - `test_governance_hooks_gate.py` 107, 169, 206 and 298.
3. **`verify-binary-on-path|verify_binary_on_path`**, the other Claude-only Bash guard. It found
   the same registers as search 2, plus:
   - `shell_split.py` 3 and 8, and `block_merge_to_main.py:77`. These are callers of
     `shell_split`, which the new guard does not import.
   - `CLAUDE.md:144`, `enforcement.md:151` and `governance-extraction.md:152`.
4. **The counts:**
   `(five|5) (Bash|bash)|Bash[- ]matcher guards|bash-dispatcher runs|Bash dispatcher runs|[Tt]welve|twelve enforced|12 (enforced|blocker)|all four guards|four guards`.
   - Relevant: `CLAUDE.md:176`, `docs/governance/enforcement.md:216`, `docs/dev/tooling.md:47`,
     and `test_governance_hooks_gate.py` 154 and 296.
   - `bash_dispatcher.py:5` and `shell_split.py:1` matched but carry no count.
   - Not related to guards: `blueprints/templates.py:4`, `hardening.py:1729`,
     `context-set-contract.md:155`, `RELEASE_CHECKLIST.md` 896 and 922, evals fixtures,
     `test_hardening.py:1131`, `test_recommend_bullets.py:191`, the dependency-triage archive,
     `epic-a-chain-design-corrections.md:330`.
5. **The tooling-roster lint:** `scripts/doc_lints.py:477` derives each guard's name as
   `p.stem.replace("_", "-")` from `scripts/enforcement/guards/*.py`. `tests/test_doc_lints.py`
   (`test_real_tree_has_no_blocks`) fails until `docs/dev/tooling.md` has a row with that name.
   This forces `block_doubled_backslash.py` ↔ `block-doubled-backslash`.
6. **Other routing:**
   - `git_hook.py`, `.githooks/*` and `.github/workflows/ci.yml` never receive a Bash-tool
     command (read: `git_hook.py:27-79`; `ci.yml` runs only `ci_backstop`).
   - `.claude/settings.json` has a single PreToolUse `Bash` entry (`hook.py bash-dispatcher`).
     A second entry would break `test_governance_hooks_gate.py::test_wiring_matches_witness_blocker_split`.

---

## Consumers

| # | Site (`path:line`) | Decision | Rationale |
|---|---|---|---|
| 1 | `scripts/enforcement/guards/block_doubled_backslash.py` (new) | create | The guard. A plain substring test, with nothing to parse. It does not import `shell_split` and does not read `CLAUDE_PROJECT_DIR` (`test_evidence_gate.py:315-330` pins that reader set). |
| 2 | `scripts/enforcement/adapters/claude_hook.py:45-58` | update | Add the `_GUARD_MODULES` entry, which `dispatch()` imports lazily. |
| 3 | `scripts/enforcement/adapters/bash_dispatcher.py:47-55` | update | Append to `_GUARD_ORDER`. No short-circuit, so order only affects message order. |
| 4 | `scripts/enforcement/adapters/bash_dispatcher.py:5-7`, `:43-46` | update | The docstring and comment name the Bash guards. |
| 5 | `tests/test_governance_hooks_gate.py:156-171` `BLOCKER_RULE_NAMES` | update | Add the name. |
| 6 | `tests/test_governance_hooks_gate.py:295-300` (and comment `:154`) | update | 12 → 13, and say why. This is a deliberate governance change, owner-directed (item 142, 2026-10-07). |
| 7 | `tests/test_governance_hooks_gate.py:106-129` | update | A dated "Amended" paragraph, following convention. |
| 8 | `tests/test_governance_hooks_gate.py:200-208` `BASH_DISPATCHED_GUARD_NAMES` | update | Add the name. `:340` and `:305` then pass. |
| 9 | `tests/test_enforcement_core.py:41-50` | update | Import the module for its unit tests. |
| 10 | `tests/test_enforcement_core.py:1202-1209` | update | The exact Bash set. |
| 11 | `tests/test_enforcement_core.py` (new classes) | create | `TestBlockDoubledBackslashUnit`, plus dispatcher cases in `TestBashDispatcher`. |
| 12 | `tests/test_enforcement_coverage.py:41-59` `_BINDS_NON_CLAUDE_AGENTS` | update | `False`. It is Claude Code only by nature: the collapse happens in how the Bash tool starts bash, which no git hook sees. |
| 13 | `tests/test_enforcement_coverage.py:123-129` `EXTRACTION_GAP` | update | Insert the stem in sorted order. |
| 14 | `docs/governance/enforcement.md:142` | update | The Claude-only row must contain the stem literally (`test_enforcement_coverage.py:131-140`). |
| 15 | `docs/governance/enforcement.md` (after `:171-178`) | update | A per-guard paragraph, following the stash precedent: what it catches and its known limits. |
| 16 | `docs/governance/enforcement.md:216` | update | "a Bash dispatcher runs five" → "six". |
| 17 | `docs/dev/tooling.md:74-75` | update | A new row, which the doc lint requires. |
| 18 | `docs/dev/tooling.md:47` | update | "the five Bash guards" → "six". |
| 19 | `docs/dev/tooling.md:15` | update | The re-derivation stamp → this branch. |
| 20 | `CLAUDE.md:150-155` | update | A hook-list bullet after `block-subagent-git-stash`. |
| 21 | `CLAUDE.md:176-178` | update | "The five Bash-matcher guards (…)" → six, and add the name. |
| 22 | `scripts/enforcement/guards/result.py` | no change | Imported only. |
| 23 | `scripts/enforcement/shell_split.py:1-10` | no change | The new guard does not import it, so the caller list stays true. |
| 24 | `.claude/settings.json` | no change | It already runs everything in `_GUARD_ORDER` (enumeration 6). |
| 25 | `scripts/enforcement/adapters/hook.py:35-48` | no change | `HOOKS["bash-dispatcher"]` is unchanged. |
| 26 | `test_consumer_enumeration_gate.py:216-219`, `test_evidence_gate.py:237,265` | no change | They assert membership of other names. |
| 27 | `test_enforcement_core.py:1079-1091` | no change | It pins `claude_dispatcher._GUARD_ORDER` (Edit/Write), not the Bash dispatcher. |
| 28 | `AGENTS.md` | no change | It does not list Bash guards. Its hook mentions are other hooks. |
| 29 | `docs/wiki/pages/consistency-tracks-enforcement.md:139`, `governance-extraction.md:151-152` | decided by the scoped wiki pass at close-out | These list the Claude-only guards. Any mention uses the guard's bare name (the `verify_binary_on_path` precedent), so `scripts/wiki_relevance.py` stays untouched. |

---

## Deferred

These are pre-existing drift, outside item 142. Each goes into the handoff as a declared-not-filed
bullet:

- `docs/governance/enforcement.md:29-31` says "8 exist". There are already 12 rules (13 after
  this branch), and no test checks it. It was stale before this branch.
- `tests/test_enforcement_core.py:1129-1136` and `:1197-1200` say "all four guards". That was
  already stale at five; these are comments only.
- `scripts/enforcement/blast_radius.py`'s `result.py` entry says "10 non-test importers", but
  the explorer counted 16. Editing `blast_radius.py` is itself a gated surface, and the count
  is incidental to this change.
- **`scripts/wiki_relevance.py`** `RELEVANT_OVERRIDES` (`:137` lists the stash guard because the
  wiki cites it by path). It is changed only if the scoped wiki pass decides a by-path cite is
  needed. In that case it gets a row here before the edit, since it is a gated surface.

---

## Verification

- **Exact-set assertions fail loudly on a missed registry site:**
  - `test_governance_hooks_gate.py`: :295 count, :340 set equality, :305 superset;
  - `test_enforcement_core.py:1203`;
  - `test_enforcement_coverage.py` `TestClassificationIsComplete` (every `guards/*.py`
    classified), `TestTheExtractionGapIsPinned`, and the literal-in-`enforcement.md` check.
- **The tooling roster:** `tests/test_doc_lints.py::test_real_tree_has_no_blocks`.
- **The command shape:** `tests/test_settings_hooks_python_direct.py`, plus the wiring
  split test in `test_governance_hooks_gate.py`, prove `settings.json` was correctly left alone.
- **The prose counts** (rows 16, 18, 21) have no test. They are checked by re-running search 4
  after the edit.

**Ran, 2026-10-07, after the edits** (all `-p no:rerunfailures`, Windows, one file per run):
- `test_governance_hooks_gate.py`: 13 passed.
- `test_enforcement_coverage.py`: 5 passed.
- `test_doc_lints.py`: 27 passed.
- `test_settings_hooks_python_direct.py`: 6 passed.
- `test_enforcement_core.py`, run in two halves:
  - `-k "BlockDoubledBackslash or BashDispatcher or BlockSubagentGitStash or VerifyBinaryOnPath"`:
    78 passed, 1 skipped (the off-Windows allow case);
  - the rest: 92 passed.
- `test_evidence_gate.py`: 27 passed.
- `test_consumer_enumeration_gate.py`: 22 passed.
- `test_wiki_relevance_classification.py`: 6 passed.
- `mypy .`: no issues in 409 files.
- `ruff check` and `ruff format --check` on the changed files: clean.
- Search 4 re-run as
  `(five|5) (Bash|bash)|five Bash-matcher|dispatcher runs five|[Tt]welve enforced`, with the
  same exclusions: **0 hits**.
