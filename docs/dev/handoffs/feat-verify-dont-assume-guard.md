<!-- provenance: schema=1 session=c8caf603-88cf-46b6-b2aa-77d41a898d3c branch=feat/verify-dont-assume-guard commit=ee2ee0f actor=amodal1 agent=anthropic/claude-sonnet-5 generated_at=2026-08-06 -->

# Agent handoff: after `feat/verify-dont-assume-guard` (Bash-binary-on-PATH guard + Bash-matcher dispatcher fold landed; next is item 45's plan-approval-marker dossier)

**Branch to create:** `fix/plan-approval-marker-pr-merge` (branch off `feat/verify-dont-assume-guard`)
**Base branch:** `feat/verify-dont-assume-guard`

**This is not `main`.** This handoff's branch is one case in the same owner-sanctioned,
serialized experiment chain as its own predecessor — cases stack tip-to-tip on each
other's local, unmerged branch tips, not off `main`. Nothing in this chain has been
pushed, PR'd, or merged as of this writing; that is deliberate (see "What just landed"
below), and the close-out checklist's own step 4 ("Land it through the PR channel") is
reproduced verbatim below per template but was **not executed this session** — the
chain's own close-out (adversarial full-diff review + staged state for morning) is a
separate, later step, not this branch's job.

---

## Documents to read before any tool call (in this order)
<!-- verbatim -->

1. `docs/dev/RELEASE_ARC.md` — authoritative branch sequence,
   architectural decisions, and acceptance criteria for v1.0.2 → v1.1.0.
   The durable plan. Do not deviate without user sign-off.
2. `docs/dev/RELEASE_CHECKLIST.md` — what is open, closed,
   and deferred per release. Before proposing anything, check here first.
3. `docs/dev/AGENT_FAILURE_PATTERNS.md` —
   failure patterns to avoid. Read in full before writing any code.
   **§5f ("Guessing the mechanism") is the expensive one — it is why the
   Binding-rules block below exists.**
4. `docs/governance/charter.md` — the binding
   constitution. **C-7 (evidence before mechanism) and C-8 (durable before
   deep) are enforced by hooks, not by your judgment.**
5. `docs/architecture.md` — module map and LLM routing
   boundary. The deterministic / LLM split is load-bearing.
6. `evals/TUNING_LOG.md` — baseline floors and
   prompt change history.
7. **If this branch is a `fix/*`:** its diagnosis dossier at
   `docs/dev/diagnosis/<branch-slug>.md`, if one exists. It is the durable
   evidence record — what was **observed**, what was **falsified** (do not
   re-chase those; each one cost real money to kill), and what is still only
   **inferred**. The `restore-evidence` SessionStart hook replays it into your
   context automatically, including after a compaction.

---

## Where we are in the arc

**This next branch IS a `fix/*` branch (item 45).** No dossier exists yet at
`docs/dev/diagnosis/plan-approval-marker-pr-merge.md` (slug strips the `fix/`
prefix) — writing it, with a filled-in `## Observed` section, is this branch's
**first** action per C-7, before any production edit. `require-evidence-before-fix`
will block otherwise.

**Stream:** v1.1.0 Final March — CI-infrastructure pass, ahead of epic A.
**Sequencing rule:** strictly sequential — one branch at a time (within this
chain, "sequential" means tip-to-tip stacking, not each off `main`).
**Blocked until this stream tags:** the public v1.1.0 cut (epic E / item 10).

- ~~`chore/v11-march-kickoff`~~ ✓ · ~~`feat/consumer-enumeration-gate`~~ ✓ (C-10)
- ~~`fix/ux-scroll-spy-overlapping-refresh`~~ ✓ — item 44
- ~~`feat/ci-wait-wrapper`~~ ✓ — `scripts/ci_wait.py` (PR #102)
- ~~`feat/enforcement-first-governance`~~ ✓ — C-11 + C-12 (PR #103)
- ~~`feat/flake-rate-measurement`~~ ✓ — `scripts/flake_rates.py` + `docs/dev/flake-rates/`
- ~~`chore/dependabot-groups`~~ ✓ — `groups:` key added to `.github/dependabot.yml`
- ~~`feat/verify-dont-assume-guard`~~ ✓ — `verify-binary-on-path` PreToolUse guard +
  Bash-matcher hooks folded into one dispatcher, this handoff's branch
- **`fix/plan-approval-marker-pr-merge`** ← next (item 45 — the plan-approval marker
  survives a PR-channel merge, per `docs/dev/work/items/0045-plan-approval-marker-survives-pr-merge.md`)
- Still queued: dependency upgrades (#63 ruff, then #50, #84) → sprint A1
- `fix/experience-soft-retire` ← sprint A1, only after the above **and** a
  check-in

**The march is still deliberately paused. Do not touch epics B–E.**

**Item 10's release chain is still gated on epic 19** — untouched this
session (though see "Carried-forward observations" — epic 19's own `summary`
prose is now visibly stale against its `status` field; a discovery, not
chased here).

---

## What just landed on `feat/verify-dont-assume-guard`

**Nothing pushed, PR'd, or merged — same deliberate posture as the branch before
this one.** One commit (`ee2ee0f`) on this branch so far (this handoff's own commit
will follow).

### Deliverable A — the new guard

`scripts/enforcement/guards/verify_binary_on_path.py`: a PreToolUse guard for the
`Bash` matcher that extracts the leading binary of each top-level command segment
and checks it against `PATH` (`shutil.which`), blocking with `"BLOCKED
(verify-binary-on-path): 'X' not found on PATH."` — deliberately factual, never
"never assume" or any other overclaim (owner directive; charter C-0). Registered in
`scripts/enforcement/adapters/claude_hook.py`'s `_GUARD_NAMES`/`dispatch()`.

**Design, stated explicitly:**
- **Fails open on uncertainty.** Any command containing `$(...)`, a backtick,
  `(...)` (subshell/grouping), or a heredoc redirect (`<<`) is treated as
  unparseable and the WHOLE command is allowed unchecked (`_split_top_level`
  returns `None`). Within an otherwise-parseable command, a bare `$VAR` leading
  token, an unbalanced quote inside one segment, or a segment this guard cannot
  tokenize is skipped (allowed), never guessed at.
- **Deliberate exemptions:** shell builtins/keywords (`cd`, `if`, `test`, `[`, ...);
  `command`/`which`/`type`/`hash` (existence probes); a segment immediately
  followed by `||` (the command's own author already wrote a fallback for its
  possible failure); wrapper binaries (`env`, `sudo`, `time`, ...) are checked
  only for the wrapper itself, never the program they launch.

### Two real parsing bugs, caught by this branch's own tests before landing

Not found by inspection — found by writing the unit-matrix tests the repo's
existing `tests/test_enforcement_core.py` convention calls for, then running them:

1. **`shlex.split(segment, posix=False)` does not merge a quoted span with
   adjacent unquoted text into one token.** `FOO=bar BAZ="a b" python -c "..."`
   tokenized as `['FOO=bar', 'BAZ="a', 'b"', 'python', ...]` — the guard then
   checked `'b"'` as if it were a binary name and blocked it. Verified directly:
   ```
   >>> shlex.split('FOO=bar BAZ="a b" python -c "print(1)"', posix=False)
   ['FOO=bar', 'BAZ="a', 'b"', 'python', '-c', '"print(1)"']
   >>> shlex.split('FOO=bar BAZ="a b" python -c "print(1)"', posix=True)
   ['FOO=bar', 'BAZ=a b', 'python', '-c', 'print(1)']
   ```
   Fixed by routing through `posix=True` (correct merge + quote-stripping) after
   swapping every literal backslash for a sentinel byte first (so posix mode's
   own escape handling never touches the Windows-style backslash paths this
   repo's commands routinely carry), then swapping the sentinel back.
   Regression test: `TestVerifyBinaryOnPathUnit::test_allow_env_assignment_prefix`.

2. **A bare `2>&1`/`>&2`/`&>` fd-redirect was misread as the `&` background
   operator.** This live-blocked this branch's OWN gate command mid-session:
   ```
   PreToolUse:Bash hook error: [...bash-dispatcher.sh]: BLOCKED
   (verify-binary-on-path): '1' not found on PATH.
   ```
   from `python -m mypy . 2>&1 | tail -5 ; echo "EXIT: $?"` — the scanner split
   `2>&1` at the lone `&`, carving `1` out as its own segment and checking it as
   a binary name. Fixed: `&` immediately adjacent to `>`/`<` (either side) is
   now treated as redirect syntax, not an operator. Regression tests:
   `test_allow_stderr_redirect_fd_duplication`,
   `test_allow_combined_redirect_and_fd_dup_variants`,
   `test_block_still_reached_through_a_redirect` (a genuinely missing binary
   next to a redirect must still be caught),
   `test_allow_real_background_operator_still_splits` (a real trailing `&`
   must still split).

**This is itself a recognized recurrence, not a first sighting — see "Recurrences
observed this session" below**: the Windows/MSYS-path failure mode (below) is the
SAME class `reference-hook-manual-testing` memory's Gotcha #3 already named once,
in a different guard.

### Windows/Git-Bash path hand-testing (design constraint 3)

Hand-tested directly (not assumed) against real `shutil.which` behavior on this
machine:

```
>>> py = shutil.which("python")   # -> C:\Users\iam\AppData\Local\Microsoft\WindowsApps\python.EXE
>>> g.decide(f'"{py}" --version').blocked          # native Windows path, real binary
False
>>> g.decide(r'"C:\NoSuchDir\NoSuchTool.exe" --flag').blocked   # native Windows path, missing
True
>>> g.decide("/c/NoSuchDir/NoSuchTool.exe --flag").blocked      # MSYS path, missing (BEFORE fix)
True   # <- wrong: this path shape is never resolvable by this interpreter, so
       #    a BLOCK here is not evidence of anything
>>> msys_real = "/c/Users/iam/AppData/Local/Microsoft/WindowsApps/python.EXE"
>>> g.decide(f"{msys_real} --version").blocked      # MSYS path, REAL binary (BEFORE fix)
True   # <- a genuine false BLOCK: this exact command runs fine under Git Bash
```

The last case is the finding: under this hook's own native-Windows-Python
interpreter, `shutil.which("/c/Users/.../python.EXE")` returns `None` even
though the identical binary at its native path resolves — the mirror image of
the false-ALLOW this same path shape has caused in *other* guards'
`cwd`/`file_path` resolution (`gitutil.git_branch`, `require_feature_branch`,
2026-07-20). Fixed by adding `_MSYS_ABS_PATH_RE` (as defined in
`scripts/enforcement/guards/verify_binary_on_path.py`) and skipping the check
entirely for a token matching it — per the guard's own fail-open rule,
refusing to guess is the fix, not a cleverer path translation.
Re-run after the fix: both MSYS-path cases above now return `False`
(unchecked), which is the intended, disclosed trade — see "Recurrences" below
for the residual, un-generalized gap this leaves.

### Deliverable B — the Bash-matcher dispatcher fold

**Enumeration performed BEFORE any edit** (the C-10-spirit check this branch's
own brief required, even though `.claude/settings.json` is not on the formal
`blast_radius.py` registry): every Bash-matched hook entry in
`.claude/settings.json` as it stood at the start of this branch —

- **PreToolUse/Bash** (3 entries, all folded): `hooks/block-secrets.sh`,
  `hooks/block-merge-to-main.sh`, `hooks/ruff-changed.sh`.
- **PostToolUse/Bash** (2 entries, deliberately left untouched):
  `hooks/cleanup-plan-on-merge.sh`, `hooks/wiki-freshness-reminder.sh`. These
  are a different mechanism — a grep pre-filter + structural check directly on
  the raw hook-input JSON, not `scripts/enforcement/guards/*.claude_check()` —
  so they are not symmetric with the PreToolUse dispatcher pattern this fold
  mirrors. Folding them would be a genuinely different, riskier change; the
  brief's own "if in doubt, leave PostToolUse untouched and say why" applies.

New: `hooks/bash-dispatcher.sh` → `scripts/enforcement/adapters/bash_dispatcher.py`
(`_GUARD_ORDER = (block-secrets, block-merge-to-main, ruff-changed,
verify-binary-on-path)`), mirroring `hooks/edit-write-dispatcher.sh`'s PX-37
pattern exactly: one stdin read, no short-circuit, every blocked guard's
messages concatenated. `.claude/settings.json`'s `PreToolUse`/`Bash` array now
wires this one entry (30s timeout — the max of the three prior timeouts,
needed for `ruff-changed`'s subprocess call) instead of three. The three
folded-away standalone `.sh` files are **deleted**
(`hooks/block-secrets.sh`, `hooks/block-merge-to-main.sh`,
`hooks/ruff-changed.sh`); `block-secrets` is now dispatched by BOTH
`bash-dispatcher.sh` and `edit-write-dispatcher.sh` (its `decide()` reads both
the Bash `command` field and the Edit/Write `file_path`/`new_string`/`content`
fields), needing no standalone file for either matcher anymore.

**Sequencing followed exactly as the brief required:** the dispatcher script
was written and hand-tested FIRST; `.claude/settings.json` was switched only
AFTER that comparison passed and the old files were confirmed safe to remove
— never the other way around, so the live hooks kept working against every
in-progress edit.

**Hand-tests run, actual commands and outputs** (not "tested, works" — see
`C:\Users\iam\AppData\Local\Temp\claude\...\scratchpad\handtest_bash_dispatcher.py`
and `...\handtest_equivalence.py`, both throwaway, not committed):

| # | Scenario | Command fed | Result |
|---|---|---|---|
| 1 | binary on PATH | `python --version` | exit 0 (allow) |
| 2 | binary absent | `definitely_missing_tool_xyz --version` | exit 2, `BLOCKED (verify-binary-on-path): 'definitely_missing_tool_xyz' not found on PATH.` |
| 3 | uncertain/complex | `echo $(definitely_missing_tool_xyz)` | exit 0 (fail-open, command substitution) |
| 4 | Windows-style real path | `"<real python.EXE path>" --version` | exit 0 (allow — resolves correctly) |
| 5a | block-secrets trigger | `echo sk-ant-`+30 chars | exit 2, `BLOCKED (block-secrets): Anthropic API key detected...` |
| 5b | block-merge-to-main trigger | `git push origin main` | exit 2, `BLOCKED (block-merge-to-main): git merge/push targeting main or master.` |
| 5c | ruff-changed trigger | staged `bad.py` (`import os\nx=1\n`) + `git commit -m x` | exit 2, ruff `F401` diagnostic + `BLOCKED (ruff-changed): ...` |

OLD-vs-NEW byte-identical comparison (run before deleting the old files):
`echo sk-ant-`+30 via `block-secrets.sh` vs `bash-dispatcher.sh` → both exit 2,
identical first message line; `git push origin main` via
`block-merge-to-main.sh` vs `bash-dispatcher.sh` → both exit 2, identical first
message line; `git status` via either → both exit 0. No-short-circuit proof:
`definitely_missing_tool_xyz sk-ant-`+30 through `bash-dispatcher.sh` → exit 2
with BOTH `verify-binary-on-path` and `block-secrets` messages present.

### Test/doc updates, all directly required by this change

- `tests/test_enforcement_core.py`: `TestVerifyBinaryOnPathUnit` (19 cases,
  including the two bug-regression cases above and the Windows/MSYS path
  cases), `TestBashDispatcher` (aggregation + no-short-circuit through the
  real script), `GUARD_FILES` remapped for the three folded guards,
  `block-secrets` equivalence tests routed to whichever dispatcher a
  payload's `tool_name` actually takes in production (a new `file=` override
  on `_run_new`).
- `tests/test_enforcement_coverage.py`: `verify_binary_on_path` classified
  Claude-Code-only (no git-native path — a Bash command-string has no
  equivalent shape in a git `pre-commit`/`pre-push` hook's input), added to
  the pinned `EXTRACTION_GAP` list (now 3 members, was 2).
- `tests/test_governance_hooks_gate.py`: `BLOCKER_RULE_NAMES` grows to **nine**
  (deliberate governance-count bump, same shape C-7 got before it);
  `BLOCKER_HOOKS` drops the three folded files, gains `bash-dispatcher`;
  `CORE_DELEGATED_BLOCKERS` removed (now empty — every core-shared guard runs
  through one of the two dispatchers, none through its own lone file); new
  `BASH_DISPATCHED_GUARD_NAMES` + matching dispatcher-delegation tests
  mirroring the `edit-write-dispatcher` ones.
- `docs/governance/enforcement.md`: `verify_binary_on_path` added to the
  Claude-Code-only reach table and "the gap, named" — explicitly noting,
  unlike C-7/C-10, it has no planned git-native path at all (stated limit,
  charter C-0). **This edit is itself a narrow exception to this branch's own
  "no `*.md` outside your own handoff/notes" scope boundary** — made because
  `tests/test_enforcement_coverage.py::test_gap_is_documented_where_the_
  extraction_will_look` mechanically requires the new guard's name to appear
  in this specific file; the alternative (weakening that test) is explicitly
  forbidden by this branch's own brief.
- `tests/test_zero_pii_clone.py`: two docstring/message references to the
  now-deleted `block-secrets.sh` corrected to cite the guard module that still
  carries the pattern (a direct consequence of this branch's own file
  deletion, not unrelated drift-fixing).

**Local gate green**, run as individual steps (foreground, explicit timeouts,
`; echo "EXIT: $?"` on each): `ruff check .` ✓ · `ruff format --check .` ✓ ·
`mypy .` ✓ **357 files** · `pytest -m "not ux" -n auto` **2357 passed / 1
skipped** (293.73s, zero reruns) · `pytest -m ux` **138 passed / 2 xfailed**
(649.23s — exceeded the Bash tool's 600 000ms single-command cap, moved to the
sanctioned background path: started detached, polled the redirected output
file until its `EXIT:` line appeared, then read back the COMPLETE output and
confirmed the pass/xfail counts and zero rerun markers before trusting it) ·
`work_items check` ✓ **51 files**.

**Deviation, named:** `pytest -m ux`'s wall-clock (649.23s) again exceeded the
600s single-command cap — the third consecutive branch to hit this (the
immediately-prior handoff's own "716–818s across the last two sessions" note).
Not treated as a NEW C-11 recurrence in this handoff (the prior handoff already
recognized the pattern and explicitly filed a discovery about proactively
backgrounding rather than reactively hitting the cap); this session's own
execution — start detached, poll, full read-back before trusting the result —
is exactly the mitigation that discovery called for, executed for the first
time rather than filed again. Worth closing the loop on: whoever next revisits
this contract should fold "start it backgrounded from the first command" into
the close-out contract text itself, since three consecutive sessions is no
longer a coincidence.

**Two new `compacted` ledger events appeared this session**
(`docs/dev/ledger/c8caf603-....jsonl`, both `session=unknown`,
`trigger=unknown`, branch=`feat/verify-dont-assume-guard`, at 04:14:54Z and
04:26:47Z). Disclosed per C-8/C-12 rather than worked around quietly, same
framing as the immediately-prior two handoffs: this agent's own reasoning
trace shows no discontinuity at any point in this session, and every fact
cited above was re-verified directly against live tool output at the point of
use, not recalled from a prior summary. Unlike the prior two disclosures,
though, this session has **affirmative evidence of genuine concurrent activity
on this same machine** (see "Carried-forward observations" — a live
`C:\Dev\spolia` `gate.py`/`pytest` run, unrelated to this task, observed
running during this session's own gate run), which is exactly the
"concurrently running process sharing the same ledger path" uncertainty the
prior two disclosures could only gesture at. This is now the **third
consecutive session** disclosing this class — see "Recurrences observed"
below for why no new mechanism is authored.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

**Re-derived from `docs/dev/work/BOARD.md` directly this session (not copied
from the prior handoff), per C-10 rule 3 ("any hand-maintained consumer list is
stale until re-derived") — and that re-derivation found the prior handoff's own
copy was already incomplete: it omitted item 50, open since 2026-08-05 on
`feat/enforcement-first-governance`, two branches before the one that wrote
that copy.**

**Open (3 — was reported as 2 last handoff; +1 from the correction above, net
0 from anything this session did):**
1. **Item 19 — UX-suite flake epic, still open (reopened 2026-08-05).** Not
   touched this session. **New observation:** the item's own `summary` field
   still reads "...CLOSED." even though `status = "open"` — stale prose left
   over from the reopen, visible in `docs/dev/work/BOARD.md`'s rendering as a
   contradictory "(open)" heading over a "CLOSED." body line. Not fixed here
   (not this branch's item to edit); named so it isn't mistaken for a board
   bug.
2. **Item 45 — plan-approval marker survives a PR-channel merge.** **This is
   the next branch's own subject** — see "What this branch should build"
   below. Not touched by this branch's own implementation (deliberately: the
   next branch earns a fresh plan/dossier rather than inheriting this one's).
3. **Item 50 — C-7/C-10 are Claude-Code-only; the extraction gap.** Not
   touched this session's *decision* (still owner-gated, not an agent call —
   see the item file). **This branch's own guard widens the gap by one**:
   `verify_binary_on_path` is a THIRD Claude-Code-only guard, and — unlike
   C-7/C-10 — deliberately has no planned git-native path at all (a Bash
   command-string has no equivalent shape in a git hook's input). Recorded in
   `docs/governance/enforcement.md` and `tests/test_enforcement_coverage.py`'s
   pinned `EXTRACTION_GAP` this session; item 50's own file text (which
   enumerates "C-7 and C-10") was **not** updated to also name this guard —
   named here as a discovery per this branch's own "file, don't chase" scope
   rule, not silently left for the next reader of item 50 to rediscover.

**Watching (10, +1 new this session):**
- Item 30 — REOPENED, three dated CI occurrences, still not root-caused.
  **Do not fix from the rate alone.** Untouched this session.
- Item 46 — independently reproduced by `flake_rates.py`; still n=1,
  escalation signal not fired. Untouched this session.
- Item 47 — audit sibling scroll-spy tests for item 44's settle-gate hole;
  still not done. Untouched this session.
- Item 48 — pytest-step duration anomaly, still uncharacterized (n=1).
  Untouched this session.
- Item 49 — test suite leaves `tmp*.html` litter in tracked
  `personas/bundled/`. Untouched this session.
- Item 51 — `report --check` against a committed budget; deliberately
  unbuilt, not enough history yet. Untouched this session.
- Item 2 (wordmark sweep) · Item 16 (`--suite real` non-functional) · Item 18
  (judge variance, n=2) · Item 23 (PX-52 analyzer split) — untouched this
  session.
- **NEW, unfiled — the Git-Bash/MSYS-path resolution class has now hit
  `scripts/enforcement/` a second time** (`gitutil.git_branch`/
  `require_feature_branch`, 2026-07-20, false-ALLOW; `verify_binary_on_path`,
  this session, false-BLOCK — same root cause, opposite symptom, same fix
  shape: skip rather than guess). This branch fixed its OWN instance with a
  local regex + tests (`verify_binary_on_path._MSYS_ABS_PATH_RE`) but did
  **not** extract a shared helper into `scripts/enforcement/gitutil.py` that
  the next guard could reuse instead of re-deriving the regex a third time —
  a real, deliberate gap, named per C-11/C-12 rather than silently left,
  because building it touches a module several other guards import (its own
  C-10-shaped decision, orthogonal to both of this branch's two named
  deliverables) rather than a drive-by edit. Capture in whichever branch next
  touches `scripts/enforcement/gitutil.py` or adds a new PATH/filesystem-path
  guard — do not open a standalone branch just for this.
- **NEW, unfiled — carried from the prior handoff, still not checked:**
  verify the dependabot `groups:` PRs actually land grouped (post-merge
  morning work, nothing to check yet tonight).

**Blocked (3 + the sequenced epics, unchanged this session):** item 3
([HUMAN] GitHub toggles), item 5, item 8, epics 37–40 — untouched this
session.

**Deferred (7, unchanged this session):** items 4, 7, 24, 25, 41, 42, 43 — see
`BOARD.md`, untouched.

Open-only count is 3, still under the reduction-sprint threshold. The Watching
count (10) is at the point worth a look next time it grows — two of the ten
are this session's own new, unfiled discoveries, both explicitly scoped as
"someone else's branch," not silently dropped.

---

## Recurrences observed this session → guardrail authored

**Two recognized recurrences this session — one given no new mechanism
(precedent already covers it, explained below), one given a LOCAL mechanism
but not a class-level one (gap named, not silently filled).**

1. **A mid-session `compacted` ledger event, the same class disclosed by the
   two immediately-prior handoffs — now three consecutive sessions.** → **No
   new guardrail authored**, for the same reason stated twice already: the
   existing mechanism (the PreCompact hook writing a `compacted` receipt into
   the session's own ledger shard) is precisely what this class of event
   needs — a disclosure trigger, not a prevention mechanism, since compaction
   itself is not something a repo-side hook can prevent. A third redundant
   mechanism for an already-covered gap is exactly the failure C-11's own text
   names. **What IS new this time**: this session found direct, independent
   evidence of genuine concurrent activity on the shared machine (a live
   `C:\Dev\spolia` `gate.py`/`pytest` run, started 2026-08-05 21:35, well
   inside this session's own working window) — the first time the
   "concurrently running process" half of the `session=unknown` uncertainty
   has had anything concrete behind it rather than being a bare possibility.
   Not itself evidence that THIS session's compaction events came from that
   process (still genuinely unknown), but worth recording as the first
   corroborating data point.
2. **The Git-Bash/MSYS-path resolution failure mode, previously observed in
   `gitutil.git_branch`/`require_feature_branch` (2026-07-20, a false ALLOW),
   now recognized as the SAME class in `verify_binary_on_path` (this session,
   a false BLOCK).** → **A LOCAL mechanism was authored** (the
   `_MSYS_ABS_PATH_RE` skip-check inside this branch's own guard, plus five
   regression tests) that fails closed for THIS guard's own instance — not
   "a note," a real code check with test coverage proving it. → **No
   class-level mechanism was authored** (a shared `scripts/enforcement/
   gitutil.py` helper the next guard could import instead of re-deriving the
   same regex): named explicitly above under "Carried-forward observations"
   rather than silently left, with the reason (touches a shared module,
   deserves its own C-10 consumer pass, orthogonal to this branch's two named
   deliverables) stated rather than assumed obvious.

**Everything else surfaced this session** (the two shlex/redirect parsing
bugs, the stale item-19 summary text, item 50's own file not yet naming this
branch's guard, the `pytest -m ux` over-cap wall-clock) **was either a first
sighting with its own mechanism landed in the same commit (the two parsing
bugs — fixed, tested, not just noted) or an explicitly-named "someone else's
scope" discovery, not a recognized recurrence left ungoverned.**

---

## What this branch should build

**Next case, per the chain's own sequencing: item 45**
(`docs/dev/work/items/0045-plan-approval-marker-survives-pr-merge.md`) — the
plan-approval marker survives a PR-channel merge, leaving the plan gate open
into the next session.

1. **This is a `fix/*` branch — dossier FIRST, per charter C-7.** Create
   `docs/dev/diagnosis/plan-approval-marker-pr-merge.md` (slug strips the
   `fix/` prefix) from `docs/dev/diagnosis/TEMPLATE.md` with a filled-in
   `## Observed` section before any production edit —
   `require-evidence-before-fix` blocks otherwise, no escape hatch. Item 45's
   own file already carries three direct observations (not inference) from
   three independent sessions (2026-08-04, 2026-08-04, 2026-08-05) — read it
   in full and reproduce/re-verify those observations in the dossier rather
   than re-deriving from scratch, but re-verify them live (C-7 rule: reading
   a prior agent's claimed observation is not the same as observing it
   yourself) rather than copying them as already-proven.
2. **Two candidate fix shapes are already named in item 45's file — evaluate
   both, do not assume either is correct without evidence:**
   - **(a) A `PostToolUse` matcher on `gh pr merge`** — parallel to how
     `cleanup-plan-on-merge.sh` already matches on a local `git merge
     --no-ff`, but keyed on the PR-merge command shape instead (or on some
     signal the PR channel produces that a local merge does not).
   - **(b) A `SessionStart` reconciliation against HEAD** — check, at session
     start, whether the currently-approved plan's marker is stale against
     what actually landed on `main` since it was written, independent of
     which command produced that landing.
   Item 45's own file states these "have different failure modes" without
   further detail — characterizing that difference (what each shape catches
   that the other doesn't, and what either shape misses) is diagnosis work,
   not implementation work; do it before choosing.
3. **Do not trust the pre-existing plan-approval marker for this branch's own
   session.** Earn a fresh one via `EnterPlanMode` → plan → `ExitPlanMode` —
   the interim posture item 45's file already states, and the one every prior
   session finding this same stale-marker state has followed.

**Scope is bounded to item 45** as filed in
`docs/dev/work/items/0045-plan-approval-marker-survives-pr-merge.md`. Do not
also pick up the ruff/codeql/fumadocs dependency bumps, sprint A1, any flake
work, or the `gitutil.py` MSYS-path helper gap named above (that is its own,
separately-scoped decision) — those are sequenced elsewhere.

---

## First move

**This branch bases off `feat/verify-dont-assume-guard`, not `main`** — this
chain's cases stack tip-to-tip. Do not `git checkout main` first.

Agent: FIRST action is `python scripts/check_handoff_pointer.py "<the pointer
line you were given>"`; once it passes, consume this file
(`python scripts/verify_doc_template.py
docs/dev/handoffs/feat-verify-dont-assume-guard.md
docs/dev/AGENT_HANDOFF_TEMPLATE.md --event consumed --agent <agent>`).

Then create `fix/plan-approval-marker-pr-merge` off
`feat/verify-dont-assume-guard` (**not** `main`), write the C-7 diagnosis
dossier's `## Observed` section FIRST (see "What this branch should build"
above), then write a plan at `~/.claude/plans/<slug>.md` and show it before
touching code. **Do not code first.**

**This chain has not been pushed anywhere.** There is no PR to wait on yet
for this case or the ones before it — `scripts/ci_wait.py` only becomes
relevant once/if the chain's own close-out decides to push and open PRs.

---

## Binding rules — no discretion (copy verbatim — MANDATORY in every handoff)
<!-- verbatim -->

**These are not heuristics, and your judgment does not decide whether they apply
today.** Each one exists because an agent decided it did not apply, and was
expensively wrong. Read them as prohibitions, not as advice.

**1. Evidence before mechanism (charter C-7). If you did not SEE it, you did not
find it.**
- For a defect you cannot reproduce on demand, **the first commit on this branch
  is the instrument or the reproduction — never the fix.** The
  `require-evidence-before-fix` hook blocks production edits on a `fix/*` branch
  until `docs/dev/diagnosis/<branch-slug>.md` has a filled-in `## Observed`
  section. There is no escape hatch. `docs/**`, `tests/**` and `*.md` stay
  writable, so the way through is always open: **write down what you saw.**
- **Reading code and finding a plausible mechanism is a HYPOTHESIS.** Put it under
  `## Inferred` and label it as unproven. A fix for a real defect that isn't
  **the** defect still leaves the bug — and plausibility is exactly what makes you
  skip the check.
- **Never scope an instrument to the theory you are testing.** It will confirm
  your theory by hiding its rivals. Capture wider than you think you need.
- **Green CI is not evidence if the test needed a retry.** `pytest-rerunfailures`
  reports a fail-fail-pass as a bare `PASSED` with **no traceback anywhere in the
  log**.
- If you are not certain **from evidence**, say **"I have not verified this"** and
  **stop**. That sentence is always cheaper than the alternative.

**2. Durable before deep (charter C-8). The context window is not a store.**
- Write a hard-won fact — a measurement, a falsified hypothesis, an observed
  artifact — to its durable home **in the turn you learn it.** Not at close-out.
  The pre-close sweep *reconciles*; it must not *discover*.
- **Compaction is an unannounced data-loss event.** After one, reconcile against
  the repo and git — never continue from a summary as though it were the evidence.
- **A thin context is a handoff trigger, not a push-harder trigger.**

**3. Hooks are not obstacles (see `feedback_hook_discipline`).**
- **NEVER** bypass a hook on your own initiative. Never hand-create the file a hook
  checks for. Never skip a step that has no escape hatch. Escape hatches
  (`CLAUDE_ALLOW_MAIN_EDITS=1`, `CLAUDE_CONFIRM_MERGE=1`) are legitimate **only when
  the user explicitly directs their use** — never on your own judgment.
- If a hook blocks you: **surface the hook name and its message, and STOP.**

**4. Do not declare done. Verify done.** "Done" is the *output* of the pre-close
sweep, not an announcement. See the close-out checklist below.

**5. Corrupted input is a blocked gate (charter C-9).** Damaged, truncated, or
fingerprint-mismatched input is a blocked gate — surface it as your **first
output** and **STOP**; never silently reconstruct, however confident the
reconstruction feels. A `blocked` result from
`scripts/verify_doc_template.py --event consumed` on a handoff you're
consuming is exactly this case — three of the four confirmed silent
handoff-corruption events this rule exists for were an agent reconstructing
damaged text instead of saying so (see
`docs/dev/handoff-integrity-design.md` §2).

**6. Enumerate consumers before changing a contract (charter C-10).** Before
implementing any change to a **schema, a shared contract, or a widely-consumed
helper**, enumerate its consumers **grep-complete** — the whole tree, and every
name the thing goes by (symbol, string form, re-export, raw-SQL column, template
selector) — and **decide-and-document each site before the first edit.**
- **The ordering is the mechanism.** An enumeration written afterwards is a
  description of what you did. Written first, it is the thing that tells you the
  change is bigger than you thought.
- **A site you skip deliberately gets a written reason** under `## Deferred`. The
  same site skipped silently is a defect the next person finds.
- **Treat any hand-maintained consumer list as stale until you re-derive it** — it
  rots in *both* directions, naming sites already fixed and omitting sites that
  are not.
- The `require-consumer-enumeration` hook blocks edits to a gated surface (registry:
  `scripts/enforcement/blast_radius.py`) until
  `docs/dev/blast-radius/<branch-slug>.md` has a `## Consumers` section naming that
  surface. There is no escape hatch. That dossier's directory and `tests/**` stay
  writable, so the way through is always open: **write down who consumes it.**

---

## Hard constraints (copy verbatim — do not shorten)
<!-- verbatim -->

- Branch before any code edit (`require-feature-branch` hook enforces this)
- Quality gate before every commit: `ruff check .` + `mypy .` + `pytest`
- Every new Flask route: `_safe_username()` + `_within()` + `secure_filename()`
  — `route-security-lint` hook enforces this on `app.py` edits
- No LLM calls in `hardening.py`, `parser.py`, `generator.py`, `scraper.py`,
  `json_resume.py`, `corpus_to_json_resume.py`, or `pdf_render.py`
- `PROMPT_VERSION` must bump in the same commit as any prompt change
- New dependency = `pyproject.toml` entry + `CHANGELOG.md` entry
- If a hook blocks you: surface the hook name + error, do not bypass,
  wait for authorization
- Do not merge to `main` without explicit user confirmation
- One branch per session — close, merge, hand off before starting the next
- Capture-before-merge: land ALL of this branch's docs / memory / CHANGELOG /
  RELEASE_ARC-CHECKLIST / tracked-deferred / flaky-test captures **before** the merge.
  Never merge then open a follow-up branch for a one-file doc/memory edit — it
  re-triggers the `--no-ff` `.approved` marker-wipe ceremony. If a small item surfaces
  after you'd otherwise merge, the sweep isn't finished: fold it in and re-gate.

---

## Branch close-out checklist (do in this order before closing the window)
<!-- verbatim -->

0. **Pre-close sweep — BEFORE the gate, ON THE BRANCH (never post-merge).**
   Enumerate ALL close-out obligations and resolve each (or explicitly defer
   with the user) so the session closes ONCE: working changes consistent (no
   dangling refs); **session memory learnings written now** (post-merge
   memory/cleanup on `main` gets hook-blocked, forcing a repeat ceremony that
   steps on the next branch); loose ends resolved or deferred; **every trailing
   "track this" observation filed durably now OR written into the `Carried-forward
   observations` section above**; branches to prune identified; **this session's
   own `consumed`-event provenance-ledger file** (`docs/dev/ledger/<session>.jsonl`,
   written on `main` at session start when the incoming handoff pointer was
   consumed) **committed on this branch** — folded into an early commit, never
   left untracked and never given its own dedicated branch/PR (see
   `docs/dev/prov/SPEC.md` §5 step 3); **wiki-relevance check** — if this branch's
   own diff touches any path `scripts/wiki_relevance.py` (`is_wiki_relevant()`)
   classifies as wiki-relevant, run a scoped `/wiki-self-update` against just this
   branch's own diff and commit the wiki edit now, before opening the PR (same
   "committed before merge" discipline as memory/CHANGELOG, never a follow-up PR);
   if the touched file needed no page edit, say so explicitly rather than silently
   skipping the check; **any dev server or
   long-lived background process started this session terminated** before closing the
   window (check with `tasklist`/equivalent — an agent's own orphaned processes are
   exactly the failure mode carry-forward ledger item 20 documents). "Done" is the output
   of this sweep, not a declaration. NEVER merge and then open a follow-up branch for
   a doc / memory / note edit — that re-triggers the marker-wipe ceremony; fold it in
   before the merge.
1. Quality gate green: `ruff check .` + `mypy .` + `pytest`
2. Write the next-agent handoff at `docs/dev/handoffs/<branch-slug>.md` from
   this template (`docs/dev/AGENT_HANDOFF_TEMPLATE.md`), stamped per
   `docs/dev/prov/SPEC.md` §1, then validate it:
   `python scripts/verify_doc_template.py docs/dev/handoffs/<branch-slug>.md
   docs/dev/AGENT_HANDOFF_TEMPLATE.md --event generated --agent <agent>`. A
   `failed` result is authoring corruption in the handoff itself — fix the
   file, don't silence the check. **Do this ON THIS BRANCH, BEFORE the
   merge** — this is exactly what the Capture-before-merge hard constraint
   above already requires (the handoff is one of this branch's own docs),
   and `require-feature-branch` blocks writing it on `main` once this
   branch is gone, so there is no compliant way to do this step after
   merging.
3. Commit — message records what was done and why (or "no code change —
   verified" if the branch closed clean); the handoff file from step 2
   must be committed by this point too (its own commit or folded into this
   one — either way, both must exist before step 4)
4. **Land it through the PR channel — a local `git merge` to `main` is NEVER
   the flow.** `main` carries branch protection requiring a pull request plus
   six passing status checks (`strict: true`), so a local merge is rejected
   outright for a non-admin and, for an admin, silently bypasses those six
   checks. Squash and rebase merges are both disabled on the repo, leaving
   **merge commit** as the only method — deliberately: a squash rewrites SHAs
   and orphans the local commits it replaces (it already produced one zombie
   commit, `9f3c800`, before this was understood). Ask the user to confirm,
   then: `git push -u origin <branch>` → open the PR (`gh pr create`, or hand
   the user the URL) → **wait for the required checks with
   `python -m scripts.ci_wait <n>`** →
   `gh pr merge <n> --merge` (never `--squash` / `--rebase`) →
   `git checkout main && git pull --ff-only`. Use `--ff-only` so an unexpected
   divergence fails loudly instead of silently manufacturing a merge commit.
   **`scripts/ci_wait.py` is the single definition of "the PR is green" — never
   hand-roll a watcher, a poll loop, or a `gh pr checks … | jq` one-liner.** It
   exits **0** only when every required check passed *and* no test needed a
   retry; **3 = green-after-retries** (charter C-7 rule 3 — stop and look, do
   not merge on it reflexively), **1** a failing required check plus its log
   tail, **8** the deadline expiring, **2** a wrapper error. Two hand-rolled
   30-minute watches once ran to completion emitting *nothing* while a required
   check was already red — that silence is the failure this replaces.
   **Pushing is outward-facing on a public repo:** state what will become
   public — including any commits already on your local `main` that the remote
   does not have, since they ride along — and get explicit confirmation before
   the first push.
5. Prune the merged branch(es) with the user's OK — **but regenerate the
   pointer FIRST**, because it must cite `main`, and pruning a branch a
   pointer still names leaves the next session with an unresolvable
   reference (a correct C-9 halt, but a wasted first move). After the
   `pull --ff-only` in step 4: generate the one-line pointer with
   `python scripts/print_handoff_pointer.py
   docs/dev/handoffs/<branch-slug>.md` — never hand-type the branch or
   commit hash — then immediately verify that exact output with
   `python scripts/check_handoff_pointer.py "<output>"` before pasting
   anything (enforce the method, then check the result: a hand-typed hash
   was proven fabricated once — see
   `docs/dev/diagnosis/handoff-pointer-verification.md`). Then prune
   (`git branch -d <branch>`; the remote copy is auto-deleted on merge).
   Give the user the checked line **as copyable chat text**, as the
   **last act** before closing the window. Never paste the handoff file's
   content into chat; that reintroduces the corruption channel this
   pipeline exists to remove.
