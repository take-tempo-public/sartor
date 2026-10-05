# Diagnosis — enforcement-layer fixes: brace groups, bare `ruff`, merge text and options, worktree root, native hooks, gate result (items 123, 124, 136, 148, 149, 150, 151)

> **Status:** each defect reproduced by a test that fails on `main` (d270506); fixes follow.
> **Branch:** `fix/hook-guard-false-blocks`

---

## Symptom

Four guard misfires, three of them recurrences that stopped real work: a brace group blocked
as missing binaries `{`/`}` (123); a bare `ruff` block that gives no steering (124); a merge
guard that blocks on merge *text* in a grep pattern (136); and the C-7/C-10 guards judging a
worktree edit by the main checkout's dossier (148).

---

## Observed

Runs on the `fix/hook-guard-false-blocks` worktree at `main` d270506 with only the new tests
added (Windows 11, Python 3.13.14). Command:
`python -m pytest tests/test_enforcement_core.py tests/test_evidence_gate.py tests/test_consumer_enumeration_gate.py -k "brace or python_dash_m or no_python_hint or merge_text or real_merges or without_target or worktree"`
→ `14 failed, 15 passed`. The failures:

- **123.** `TestVerifyBinaryOnPathUnit::test_brace_group_braces_are_not_binaries` and
  `::test_brace_group_first_command_is_still_checked` fail: `decide("{ python -V; python --version; } | python -V")`
  is blocked. `{`/`}` are absent from `_BUILTINS_AND_KEYWORDS`
  (`scripts/enforcement/guards/verify_binary_on_path.py:78-142`) and `_leading_binary_token`
  returns the first shlex token (`:306-317`).
- **124.** `::test_missing_python_tool_message_names_python_dash_m` fails: with `ruff` and
  `pytest` off PATH, the block names them but no message line contains `python -m ruff`
  (`_MESSAGE_FOOTER`, `:163-171`, is generic).
- **136, over-block.** `TestBlockMergeToMainUnit::test_merge_text_in_arguments_is_not_a_merge`
  fails on all 5 cases, cwd on `main`, including `grep -E 'git merge --no-ff|main' docs/dev/work/BOARD.md`,
  `echo 'never git merge main locally' >> notes.md`, and the item's observed shape (a python
  heredoc plus a grep holding the phrase). `targets_main()` runs three regexes over the raw
  command string (`scripts/enforcement/guards/block_merge_to_main.py:90-92`, `:134-141`).
- **136, under-block (new finding, not in the item).** `::test_real_merges_still_block` fails on
  2 of 14 cases: `git -C . merge main` and `git -c core.editor=true merge main` are **allowed**
  today. `_MERGE_MAIN_RE` requires `merge` to follow `git` directly (`\bgit\s+merge`), so any
  global git option in between hides a real merge to main.
- **148.** `test_evidence_gate.py::…::test_reads_the_dossier_from_the_edited_files_worktree`,
  `::test_a_main_checkout_dossier_does_not_cover_a_worktree_edit` and
  `test_consumer_enumeration_gate.py::…::test_reads_the_dossier_from_the_edited_files_worktree` fail.
  Live occurrence, same session: an `Edit` in worktree `C:\Dev\sartor-wt-console` was refused with
  `BLOCKED (require-evidence-before-fix): on 'fix/console-run-lock-hardening', but docs/dev/diagnosis/console-run-lock-hardening.md does not exist.`
  although that worktree held the filled dossier. `_repo_root_for` returns `CLAUDE_PROJECT_DIR`
  when set (`require_evidence_before_fix.py:57-61`, `require_consumer_enumeration.py:107-110`),
  while the branch is read from the edited file's directory (`require_evidence_before_fix.py:141-144`).
  The second evidence test shows the unsafe direction: a dossier for the same slug in the
  project dir licensed an edit in a worktree that had none.
- **150 (added 2026-10-03, owner: "add to fixes").** `git -C C:\Dev\sartor config --get core.hooksPath`
  prints nothing on the owner's clone (and on this worktree), so `.githooks/pre-merge-commit` and
  `.githooks/pre-push` never run. `scripts/gate.py` has no `hooksPath` check (`Select-String
  -Pattern hooksPath scripts/gate.py` → `False`); only `CONTRIBUTING.md:120` mentions enabling them.
- **151 (added 2026-10-03, owner: "add to fixes").** Background task `b32w6qi12` (gate via
  Git Bash, redirected to a log) was reported `completed (exit code 0)` while its log ended
  `gate: FAILED at \`mypy .\` (exit 1)` / `exit=1`. Task `b5kuyio3f` did the same with
  `gate: FAILED at \`memory preflight\` (exit 1)`. The gate writes no result of its own, so only
  the log can contradict the notification.
- **Not this branch:** `TestBlockMergeToMainEquivalence::test_defect_ii_regression_cross_worktree_cwd`
  also failed in this PowerShell-launched run (`assert 127 == 2`: the OLD shell hook it runs as a
  subprocess got "command not found"). It is selected only because its name contains
  "worktree"; this branch does not touch it. Expected to pass under the gate's Git Bash launch.

---

## Falsified

- **"`.*` not crossing a newline is why a later heredoc went through" (item 136's own note)**
  is consistent with the code but is not the whole story: the under-block above shows the
  regex also misses real merges on a single line.

---

## Inferred

- `claude_context_hook.py:82-83` (`restore-evidence`) prefers `CLAUDE_PROJECT_DIR` over the
  payload `cwd` the same way, so a worktree session would not get its evidence replayed after a
  compaction. **I have not reproduced this one**; it is fixed on the same reasoning and covered
  by a unit test of the root resolution, not by a live compaction.

---

## Falsification

The tests named under `## Observed` are the experiment; each failed on `main` as quoted. A fix
is accepted only when they pass unchanged and every pre-existing guard test still passes.

---

## The fix

- **123:** `_leading_binary_token` drops a leading `{` (a brace group's first command is still
  checked) and treats a lone `}` as a reserved word.
- **124:** for each missing name that this interpreter can import as a module
  (`importlib.util.find_spec`), the block adds "run `python -m <name>` instead". The claim is
  checked, not listed: a missing name with no importable module gets no hint.
- **136:** `targets_main()` parses the command into top-level segments and judges each segment by
  its command word. A `git` segment is parsed past global options (`-C`, `-c`, `--git-dir`, …)
  to its subcommand. Text-only commands (`grep`, `rg`, `echo`, `printf`, `cat`, …) and git
  subcommands other than merge/push are ignored. **Everything else falls back to the old
  raw-text regexes on that segment, widened to allow global options**: interpreters
  (`bash -c`, `eval`, `xargs`, …), any segment the parser is unsure of, and every heredoc
  body (a body may be executed by whatever reads it). So the change can stop over-blocking only
  where the text is provably an argument; it cannot newly allow a merge.
- **148:** both guards resolve the repo root from the edited file (walk up to the directory
  holding `.git`, file or folder) and use `CLAUDE_PROJECT_DIR` only when the file is in no repo.
  `restore-evidence` prefers the payload `cwd`. The resolution lives once, in
  `scripts/enforcement/gitutil.py` (a gated surface: C-10 dossier first), and a test fails if any
  guard reads `CLAUDE_PROJECT_DIR` directly. One end-to-end test runs `git worktree add` and calls
  the real hook script.
- **149:** covered by the 136 parser above (global options are skipped before the subcommand), plus
  widening the raw-text fallback regexes to allow options between `git` and `merge`/`push`.
- **150:** a gate step fails when `core.hooksPath` is not `.githooks` and prints the one command
  that fixes it. It is skipped in CI, which never merges or pushes locally, and CI's log says so.
- **151:** `scripts/gate.py` writes a result file on every terminal path (exit code, failing step,
  times, `HEAD`, dirty-tree flag), and `python -m scripts.gate --result` is the one check of "the
  last local gate passed on this tree". Commits and handoffs cite it, not a notification.

---

## Acceptance bar

The 14 new tests pass, every pre-existing test in the three files passes, and the full gate is
green with no reruns.
