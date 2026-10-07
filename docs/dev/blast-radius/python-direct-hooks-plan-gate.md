# Blast radius — python-direct-hooks-plan-gate

> **Branch:** `fix/python-direct-hooks-plan-gate`
> **Status:** enumeration complete. Written before the first production edit.

---

## Surface

- **`.claude/settings.json` `hooks`**: every command. It moves from
  `${CLAUDE_PROJECT_DIR}/hooks/<name>.sh` to
  `python3 "${CLAUDE_PROJECT_DIR}/scripts/enforcement/adapters/hook.py" <name>`, where `<name>`
  keeps the old hook identity:
  - `check-plan-approved` is folded into `edit-write-dispatcher`;
  - `cleanup-plan-on-merge` is removed (owner decision, 2026-10-06);
  - a new PreToolUse `ExitPlanMode` entry `plan-write-landed` (item 143);
  - a new SessionStart entry `shell-probe` (item 152).
- **`hooks/*.sh` and `hooks/lib/retire-approved-plan.sh`**: deleted. Their logic moves to the
  new `scripts/enforcement/plan_gate.py`, and the wrappers become `hook.py` names.
- **`scripts/enforcement/adapters/claude_hook.py` `dispatch()`**: guard modules import lazily
  instead of all at load. The call shape is unchanged.
- **`scripts/enforcement/adapters/claude_dispatcher.py`**: runs the plan gate first, in-process.
- **Plan-gate state files** under `~/.claude/plans/`: `.approved-<key>`, `.current-<key>` and
  `.approved-branch-<key>` keep the **same names, `PROJECT_KEY` derivation and contents**. New:
  `.plan-attempt-<key>`.
- **`plan-archived` ledger receipt**: the same fields, written by Python instead of a bash heredoc.
- **`scripts/doc_lints.py:468` `tooling_tree()`**: derives a hook's name from its command.

---

## Enumeration

Live tree only. The excluded historical paths are listed under `## Deferred`.

```
git grep -n -E 'check-plan-approved|mark-plan-approved|cleanup-plan-on-merge|retire-approved-plan|retire_approved_plan|edit-write-dispatcher|bash-dispatcher\.sh|restore-evidence\.sh|capture-before-compact\.sh|interrogative-prompt-witness\.sh|wiki-freshness-reminder|HOOKS_DIR|_hook_stems|hooks/lib|CLAUDE_PROJECT_DIR\}?/hooks|\.approved-branch-|\.current-|plan-archived|root `hooks/`|`hooks/`' -- . ':!docs/dev/handoffs' ':!docs/dev/reviews' ':!docs/dev/archive' ':!docs/dev/diagnosis' ':!docs/dev/blast-radius' ':!docs/dev/work/items' ':!docs/dev/ledger' ':!CHANGELOG.md' ':!docs/wiki/log.md' ':!docs/governance/compliance-log.md' ':!hooks'
```

That gave 190 lines across 37 files (2026-10-07). With the exclusions dropped, the same names
hit 415 lines across 122 files.

Readers of the settings `hooks` block:
`git grep -n 'settings\.json' -- 'tests/*.py' 'scripts/*.py' 'scripts/**/*.py'`. Five
parsers: `scripts/doc_lints.py:468`, `tests/test_evidence_gate.py:245/255/285`,
`tests/test_governance_hooks_gate.py:132`, `tests/test_consumer_enumeration_gate.py:25`,
`tests/test_plan_approval_scoping.py:892/1096`.

Negative results:
- `docs-site/`: 0 hits for `hooks/` or `.claude/settings`.
- `scripts/gate.py`, `scripts/doc_registry.py`: 0.
- `docs/dev/prov/SPEC.md` (gated) does not name `plan-archived` (item 55, the vocabulary drift).

---

## Consumers

| # | Site | Decision | Rationale |
|---|---|---|---|
| 1 | `.claude/settings.json:27-115` | update | the change itself |
| 2 | `hooks/*.sh` (9 files), `hooks/lib/retire-approved-plan.sh` | delete | logic ported to `scripts/enforcement/plan_gate.py`; wrappers replaced by `hook.py` names |
| 3 | `scripts/enforcement/adapters/claude_dispatcher.py` (`_GUARD_ORDER`, docstring) | update | runs the plan gate first; docstring said check-plan-approved "stays its own separate top-level hook" |
| 4 | `scripts/enforcement/adapters/claude_hook.py:10-35` docstring, eager guard imports | update | lazy import per dispatched guard (efficiency, measured); docstring names `.sh` wrappers |
| 5 | `scripts/enforcement/adapters/bash_dispatcher.py` | no code change | routes through `claude_hook.dispatch`, so lazy imports apply automatically; docstring checked |
| 6 | `scripts/enforcement/adapters/claude_context_hook.py:30` | update docstring | "Invoked by the thin wrappers in root `hooks/`" |
| 7 | `scripts/enforcement/adapters/prompt_witness_hook.py:17` | update docstring | names `hooks/interrogative-prompt-witness.sh` |
| 8 | `scripts/enforcement/__init__.py:8,20-22` | update docstring | says the plan hooks "stay standalone scripts" in `hooks/` |
| 9 | `scripts/enforcement/evidence.py:102` | check, then update the wording if it names the `.sh` | prose mention of check-plan-approved |
| 10 | `scripts/enforcement/guards/block_merge_to_main.py:48` | update comment | names `wiki-freshness-reminder.sh` |
| 11 | `scripts/wiki_freshness.py:10,14,36` | update docstring | names the `.sh` reminder and its `THRESHOLD` |
| 12 | `scripts/wiki_relevance.py:6,65` (**gated**) | no change | `:6` is past-tense history. `:65`'s `hooks/` prefix: see Deferred |
| 13 | `scripts/doc_lints.py:468` `tooling_tree()` | update | `Path(command.split()[0]).name` would name every new hook `python3`. Name a hook by its `hook.py` argument instead |
| 14 | `tests/test_plan_approval_scoping.py` | update | re-target `_run` from `bash hooks/*.sh` to `python3 …/hook.py <name>`. Drop the `cleanup-plan-on-merge` tests and re-target the local-`--no-ff` ones to the reconciler. `TestLibHelperExemption` is removed (its subject is gone). `test_killed_retire_never_leaves_a_live_marker` (python3 shim) becomes an in-process fault-injection test |
| 15 | `tests/test_governance_hooks_gate.py` | update | hook identity from the `hook.py` argument, not `hooks/*.sh` stems. Textual `exit 2` checks become behavioral. `check-plan-approved` leaves `BLOCKER_HOOKS` (it is now inside `edit-write-dispatcher`) but stays a RULE. New rule and hook `plan-write-landed`. Witnesses go from 3 to 2 |
| 16 | `tests/test_evidence_gate.py:240-258,285,357` and the executable-bit test | update | wiring by hook name; runs the dispatcher through `hook.py` |
| 17 | `tests/test_enforcement_core.py` `HOOKS_DIR`, `GUARD_FILES`, `_run_hook` | update | run `hook.py <dispatcher>` instead of the `.sh` |
| 18 | `tests/test_consumer_enumeration_gate.py:229` | update | asserts `edit-write-dispatcher.sh` is wired |
| 19 | `tests/conftest.py:56` | update comment | names the `.sh` |
| 20 | `tests/test_verify_doc_template.py:297,331` | update | its list of ledger writers names `hooks/lib/retire-approved-plan.sh`; it becomes `scripts/enforcement/plan_gate.py` |
| 21 | `tests/test_agent_tool_grant_consistency.py:51` | check | item 54's hook-path test; update if it reads `hooks/` |
| 22 | `CLAUDE.md:72,93,151,170-172` | update | hook list and wiring note |
| 23 | `CLAUDE.local.md` (machine-local, untracked) | update locally, not committed | names `hooks/check-plan-approved.sh` |
| 24 | `AGENTS.md:71` | update | points at `hooks/` for route-security-lint |
| 25 | `CONTRIBUTING.md:104` | update | "Hooks in `hooks/`" |
| 26 | `SECURITY.md:272` | update | names `hooks/edit-write-dispatcher.sh` |
| 27 | `agents/git-flow.md:23` | update | names `hooks/bash-dispatcher.sh` |
| 28 | `commands/compliance-witness.md:108`, `commands/wiki-self-update.md:26` | update | link targets `../hooks/wiki-freshness-reminder.sh`, which would be dead links |
| 29 | `agents/compliance-witness.md:129`, `docs/dev/EXTRACTION.md:93` | no change | the bare name `wiki-freshness-reminder` stays the hook's identity |
| 30 | `.claude/workflows/n1-baseline.mjs:55` | update | prompt text names `check-plan-approved.sh` |
| 31 | `.githooks/README.md:23-29` | update | says the plan hooks "stay standalone scripts under root `hooks/`" |
| 32 | `docs/dev/tooling.md:17,38,42-52,75` | update | the hooks roster (and `doc_lints` checks it against settings) |
| 33 | `docs/governance/enforcement.md:256-259` | update | adds the Python-direct note and the stated `python3` limit (C-0) |
| 34 | `docs/governance/enforcement.md:100,125,222`, `docs/governance/charter.md:452,512` | no change | historical rows and narrative |
| 35 | `docs/dev/n1-baseline-pipeline.md:111` | update | "`hooks/check-plan-approved.sh` blocks every subagent Edit/Write" |
| 36 | `skills/README.md:3` | update | "Mirrors the `commands/`/`agents/`/`hooks/` root-level convention"; `hooks/` is gone |
| 37 | `docs/wiki/pages/route-surface.md:66` | update in the close-out wiki step | "run via `hooks/edit-write-dispatcher.sh`" |
| 38 | `docs/dev/work/BOARD.md` | regenerate | generated from items |
| 39 | State files `.approved-*`, `.current-*`, `.approved-branch-*` | no format change | byte-compatible; live pointers from before the switch keep working. Asserted by a test that writes them with the old key derivation |
| 40 | `plan-archived` receipt fields | no change | same `event`, `session`, `branch`, `archive_id`, `plan`, `ts`; same `newline="\n"` |
| 41 | `tests/test_enforcement_core.py:1080` `test_guard_order_is_exactly_the_edit_write_guards` | update (**found late**) | pins `claude_dispatcher._GUARD_ORDER` exactly. **Missed by the enumeration**: it searched hook and file names, not the `_GUARD_ORDER` symbol this branch also changed. Surfaced by the targeted pytest run (`1 failed, 117 passed`), then fixed. A follow-up `git grep -n _GUARD_ORDER` found 9 sites; the other readers check membership only (unaffected). `claude_hook`'s removed guard-module attributes: `git grep 'claude_hook import'` shows only `_GUARD_NAMES`, which remains |

---

## Deferred

- **Historical records** are not rewritten: `docs/dev/handoffs/`, `docs/dev/reviews/`,
  `docs/dev/archive/`, `docs/dev/diagnosis/` (other than this branch's),
  `docs/dev/blast-radius/` (others), `docs/dev/work/items/` (other than 111/143/152/154),
  `CHANGELOG.md` history, `docs/wiki/log.md`, `docs/governance/compliance-log.md`,
  `docs/dev/RELEASE_ARC.md`, `docs/dev/RELEASE_CHECKLIST.md` history rows,
  `docs/dev/epic-a-chain-design-corrections.md`, `docs/dev/handoff-integrity-design.md:270` and
  `docs/dev/keep-ledger.md:119`. They record what was true when written, and their prose is
  not rewritten.
  - **Correction (found by the link gate):** the claim first written here, "their
    `path:line` cites into `hooks/` stay resolvable through git history", was **false** for
    six sites. `scripts/check_doc_links.py` requires the target to exist, and it failed with
    `6 broken link(s)/cite(s)`.
  - Those six were re-pointed, text unchanged, to GitHub permalinks pinned at a commit where
    the file exists: `CHANGELOG.md:6923` and three in
    `docs/dev/archive/self-documenting-loop-design.md` (at `b5c9ddf`), and two `path:line`
    cites in `docs/dev/epic-a-chain-design-corrections.md:67,229`.
  - The last two are pinned at `fced8e9`, the commit that record was written at. A
    `git show fced8e9:hooks/lib/retire-approved-plan.sh` confirms lines 84 (`mv -f`) and 161
    (`rm -f` pointers) are what the record describes.
  - The `moved-paths.json` map was not used: it is for docs that moved, and pointing it at
    ported code would send line cites to unrelated lines.
  - Re-run: `check_doc_links: OK — 613 tracked markdown files`.
- **`.githooks/*`** is unchanged. Git requires an executable hook file, and each one is already
  a one-line `exec python3 …/git_hook.py`. Item 152's rule covers `.claude/settings.json` only.
- **`scripts/wiki_relevance.py:65` (`"hooks/"` in the irrelevant prefixes)** stays. With the
  directory deleted, the entry matches nothing. Removing it changes no classification, and it
  would touch a merge-blocking gated classifier for zero behaviour change. If a `hooks/`
  directory ever returns, the entry still describes it correctly.
- **`docs/dev/prov/SPEC.md`** (gated): `plan-archived` is still undocumented there. That is
  item 55, out of scope; the receipt is unchanged.

---

## Verification

- **`tests/test_settings_hooks_python_direct.py`** (new) fails if any settings command is not
  `python3 "${CLAUDE_PROJECT_DIR}/scripts/enforcement/adapters/hook.py" <name>`, or names a
  `.sh` or a shell interpreter, or if `<name>` is not in `hook.py`'s registry. It also fails if
  a registry name is left unwired.
- **`tests/test_governance_hooks_gate.py`** pins the exact set of wired hook names per event,
  both directions.
- **`scripts/doc_lints.py`'s tooling roster lint** fails if `tooling.md` lists a hook the
  settings lack, or the reverse.
- **Dead links**: the doc link lint catches any remaining `../hooks/*.sh` link.
- **A residual grep after the change**: the Enumeration command above, re-run, must return only
  rows decided "no change" or Deferred here.
