<!-- provenance: schema=1 session=17250fd2-0a36-462c-bffa-f8cc14d5c63e branch=fix/heredoc-escape-guard commit=c455ee8 actor=amodal1 agent=anthropic/claude-opus-5-5 generated_at=2026-10-08 -->

# Agent handoff — doubled-backslash guard (`fix/heredoc-escape-guard`) → Bash-tool transport (items 157 + 158)

**Branch to create:** `fix/bash-tool-transport` (branch off `main`)
**Base branch:** `main`

> **This session closed item 142.**
> - The C-7 instrument found the layer. On Windows, Claude Code starts the Bash tool's Git
>   Bash as a native program, and Git Bash's argv rebuild **halves every doubled backslash**
>   before bash parses anything. A single backslash survives, and so does the same text on
>   stdin or with `MSYS=noglob` set.
> - It was never about heredocs. `grep` and `sed` commands collapse too.
> - The new Bash guard `block-doubled-backslash` refuses any `\\` on win32 and allows
>   everything elsewhere (owner decision). It was verified live in this session.
>
> **The owner chose the next branch (2026-10-08): items 157 + 158 together**, both about the
> Bash tool's transport layer:
> - 157: `MSYS=noglob` as the root-cause fix;
> - 158: bash refusing whole commands with `unexpected EOF while looking for matching '`.
>
> **CI is still the gate.** Free RAM was 0.47 GB at close, below the gate's 1.0 GB preflight.

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
5. `docs/dev/architecture.md` — module map and LLM routing
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

**Stream:** Epic E, `epic/e-release` (board 40). The Open-item drawdown before 1.1.0 alpha staging
(owner's 2026-10-02 sequence on item 40).
**Sequencing rule:** strictly sequential — one branch at a time.
**Blocked until this stream tags:** the 1.1.x epic series.

- ~~`fix/hook-guard-false-blocks`~~ ✓ (#157): items 123/124/136/148–151 closed, 153 filed.
- ~~`fix/console-run-lock-hardening`~~ ✓ (#158): items 112/117–121 closed, 154 filed.
- ~~`fix/wiki-relevance-cited-scripts`~~ ✓ (#159): item 153 closed, 155 filed.
- ~~`fix/python-direct-hooks-plan-gate`~~ ✓ (#160): items 152/111/154/143 closed, 156 filed.
- ~~`fix/heredoc-escape-guard`~~ ✓ (PR pending): item 142 closed, items 157 and 158 filed.
- **`fix/bash-tool-transport`** ← next (owner's pick, 2026-10-08): items 157 and 158 only.
- Not started: item 7 memory-consolidation apply (Deferred), item 30's C-7 probe branch,
  launcher items 145–147, item 155 (UX flake), and item 156 (Windows concurrent-writer test).

**Don't start the cut, the version bump or the CHANGELOG cut.** Item 10 still depends on 3, 7
and 19, and on the owner's alpha approval. Don't fold any other item into the 157/158 branch.

---

## What just landed on `main`

Once the owner confirms the PR (merge commit; never squash or rebase),
`fix/heredoc-escape-guard`:
- **`7f33c45`: the C-7 instrument.** No production code.
  - `docs/dev/diagnosis/heredoc-escape-guard.md` holds O1–O5:
    - the Bash-tool probe;
    - bash's own argv;
    - the PowerShell control arm;
    - a standalone repro (`bash.exe -c` halves `[2,1,4]` to `[1,1,2]`; stdin and
      `MSYS=noglob` stay intact);
    - ten incidents re-decoded from the transcripts, all holding the intended count.
  - `tests/test_bash_backslash_collapse.py` pins the collapse. It is Windows-only and skips
    without Git Bash. If it ever fails, the guard has lost its premise.
  - The C-10 dossier `docs/dev/blast-radius/heredoc-escape-guard.md`, and this session's
    consumed-ledger file.
- **`5af9996`: the guard.**
  - `scripts/enforcement/guards/block_doubled_backslash.py` is a plain substring test, with
    nothing to parse and no subprocess.
  - It is registered in `claude_hook._GUARD_MODULES` and `bash_dispatcher._GUARD_ORDER`.
    `settings.json` is unchanged.
  - Governance: the 13th enforced blocker rule (with a dated amendment in
    `tests/test_governance_hooks_gate.py`), the Bash dispatched set, and the extraction gap
    (Claude Code only by nature).
  - Docs: `enforcement.md`, `tooling.md`, `CLAUDE.md`.
  - Tests: `TestBlockDoubledBackslashUnit`, plus two `TestBashDispatcher` cases (block on
    win32; allow off it, which Linux CI runs).
- **`f2c0d75`:** item 142 closed with `verified_by`, and its `refs` no longer cite the deleted
  `hooks/bash-dispatcher.sh`. Items 157 and 158 were filed, and the board regenerated.
- **`c455ee8`:** a scoped wiki pass over two pages (owner-authorized; auditors 8/0/0 and
  5/1/0, where the one DRIFTED flag was checked and is a false positive; checkpoint not
  advanced).
- This handoff's commit.
- **Tests** (all `-p no:rerunfailures`, local Windows, one file per run):
  - `test_enforcement_core.py`: 170 passed, 1 skipped (the off-Windows case);
  - governance, coverage, doc-lint, settings-shape, evidence, consumer-enumeration and
    wiki-relevance suites: all green;
  - 12 further related suites: all green;
  - `test_doc_links` and `test_wiki_freshness_gate`: green;
  - `check_doc_links`: OK (619 files);
  - `mypy .`: clean (409 files), and ruff clean.
- **Live:** in this session, the Bash command `printf '%s\n' 'live-probe A\\b'` was refused with
  `BLOCKED (block-doubled-backslash)`, and a single-backslash command ran.
- **Gate:** `python -m scripts.gate` was not run, because free RAM was 0.47 GB, below its
  1.0 GB preflight. **CI on the PR is the gate:** `python -m scripts.ci_wait <n>`, and exit 3
  means stop.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

The authoritative home is `docs/dev/work/BOARD.md`. **Header: "Open 30 / 10 ceiling -- OVER"**
(it was 29 at this branch's start: item 142 closed, items 157 and 158 filed). The owner's
drawdown direction stands: down to 0 if possible, before alpha staging. Well past the ~8–10
reduction-sprint threshold.

`## Open` (28 items; the header also counts open epics). Generated from the board;
owner-decision items are marked *(owner)*:
- **50** *(owner)*: C-7 and C-10's guards are not routed by git_hook.py, so only Claude Code enforces them; prose binds other agents.
- **98**: Drift only grows between full ingests; agents report commits, not the gate. Build: coverage ledger + generated figure.
- **99**: install.md documents a GHCR image and a PyPI wheel that have never been published; every documented path fails. [depends on: 3]
- **105**: Corpus import produced bullets and skills but no education rows; parse-vs-persist not yet distinguished.
- **106**: Bullet-text edit in Compose never re-freezes; preview/generate/download keep serving the pre-edit snapshot.
- **107**: No first-run step to name the account; it defaults to the email address while settings shows the real name.
- **115**: Add a getComputedStyle assertion for .err-link's danger color; F3's fix was verified by reading rules, not measuring.
- **116**: Post-Collate help circle is wired at runtime; C3's UX test never reaches it, only render-with-no-error is verified.
- **122**: Three C3 assertions survive plausible mutants; tighten each to fail on the regression it names.
- **128** *(owner)*: Stray python3.13 processes from earlier sessions. **New data:** 27 python processes were alive at this session's start (2026-10-07), none of them this session's.
- **129** *(owner)*: Owner: project docs shouldn't carry personal reviewer/interviewer framing; 2 records still do. Edit records or leave?
- **130**: Settings saves to the config file, but prompts read Candidate.notes, filled only on creation or when empty.
- **131**: Retire dialog cites a "Show retired" toggle Pipeline lacks; its query drops retired apps.
- **132**: Follow-up answers save, but regenerate re-assembles the frozen composition with no AI call. UNVERIFIED.
- **133** *(owner)*: No route, UI or script removes a user. Product decision: wanted, and when?
- **134**: Tuning smoke says ~$0.20 for TWO suite runs; Quality smoke says ~$0.35-0.40 for ONE. At most one is right.
- **135** *(owner)*: Template close-out step 1 says ruff+mypy+pytest (gate runs 6); charter:206 cites step 4 for a step-5 rule.
- **137**: Short review: are the pinned models and call settings (thinking, caching, routing) still the best performance/cost fit?
- **138** *(owner)*: _initHelp attaches only to .cb-panel; Settings is a drawer, so it gets no (i) bubble or Learn more link.
- **139**: cleanup() runs only on success; demo DB rows are never removed, so a stale import blocks later runs.
- **140**: Prompts hand bullets to the model as id="b{id}"; the model echoes the handle into prose. Letter date is ungrounded.
- **145**: Owner pre-launch requirement (2026-08-16), unfiled till now: stdlib launcher, two backends, per-OS one-click wrappers.
- **146**: A second launch starts a second server attempt on :5000; nothing identifies a running sartor or stops it cleanly.
- **147**: Closing the tab leaves the server running (correct), but there is no in-app way to stop it and no idle exit.
- **155**: A CI attempt saw 'Notes saved', never 'Company saved', for 5 s after the company blur. Retry passed; cause unverified.
- **156**: On Windows a writer thread's own pre-read hit PermissionError mid-replace; its delta was lost. Test or code: unverified.
- **157** (new, this branch): MSYS=noglob stopped Git Bash halving doubled backslashes in a standalone repro; untested inside Claude Code. ← **next branch**
- **158** (new, this branch): Bash refused whole commands with 'unexpected EOF while looking for matching' in about 6 sessions; cause unknown. ← **next branch**

`## Blocked` (4): **3**, **5**, **8**, **97**.

`## Deferred` (9): **4**, **7**, **24**, **25**, **41**, **42**, **43**, **113**, **114**.

Plus `## Watching` and `## Epics` in `BOARD.md`.

Declared, not filed (carried from the previous handoff unless marked new; **not re-verified this
session** unless stated):
- **A stale comment** at `db/build_context.py:92`. Fold it into any branch that touches that file.
- **The doc-writing skill's evaluation plan has not been run.** When to run it is the owner's call.
- **32 one-way wiki backlinks** (WARN), as counted by an earlier `/wiki-lint`.
- **`sartorEval.run()` returns no handle on its success path** (`dashboard.html`); no caller reads
  it. Deferred in `docs/dev/blast-radius/console-run-lock-hardening.md`.
- **One UX test took 301 s alone** before the console fix, at about 1 GB free; not investigated.
- **`docs/dev/diagnostics.md` cites code by line number**, which rots on every edit.
- **The derived-set test's `git ls-files` costs 1.8–5.2 s on this machine** under 0.5–0.8 GB
  free.
- **Transitive wiki relevance is not modelled** (`PERFORMANCE_HISTORY.md` →
  `scripts/perf_baseline.py`).
- **`python3` resolution on hypha and the homelab is unchecked.** On a machine without `python3`
  on PATH no hook starts and the gates fail open (`docs/governance/enforcement.md`).
- **`tests/test_plan_approval_scoping.py` takes about 6 minutes locally.** Split it by `-k`
  class.
- **New, pre-existing drift found by this branch's C-10 grep** (each is deferred in
  `docs/dev/blast-radius/heredoc-escape-guard.md`):
  - `docs/governance/enforcement.md:29-31` says "8 exist" (there are 13 rules);
  - `tests/test_enforcement_core.py`'s section comment and `TestBashDispatcher` docstring say
    "all four guards" (there are six);
  - `scripts/enforcement/blast_radius.py`'s `result.py` entry says "10 non-test importers"
    (an explorer counted 16; not re-verified).
- **New: `tests/test_bash_backslash_collapse.py` takes about 27 s locally**: three Git Bash
  starts at about 0.5–1.2 GB free. It is skipped on Linux CI.
- **New: the interrogative-witness pause re-armed four times this session** after
  background-agent notifications and subagent hand-backs, not only after user prompts. Each
  cost one re-run. `enforcement.md` already names the hand-back case; the task-notification
  case is not named.

---

## Recurrences observed this session → guardrail authored

1. **A doubled backslash in a Bash-tool command silently lost one backslash** (item 142's
   class).
   - **Recognized as a recurrence:** at least ten recorded incidents (2026-08-05 to
     2026-10-07), and the owner's memory has held it since 2026-08-05. This session
     reproduced it on purpose (dossier O1, O4).
   - **Mechanism, fails closed:**
     - `scripts/enforcement/guards/block_doubled_backslash.py`, run in `bash-dispatcher`;
     - `tests/test_enforcement_core.py::TestBlockDoubledBackslashUnit` and the two
       `TestBashDispatcher` cases;
     - `tests/test_bash_backslash_collapse.py` pins the premise.
   - **Known limit:** it assumes every win32 Bash tool collapses (item 157 revisits this).
2. **A subagent's or tool's report carried facts that were wrong or went beyond its brief**
   (the previous handoff's recurrence 8). This session:
   - the transcript explorer's line numbers were 0-based;
   - a `wiki-scribe` removed an existing cite it was not asked to touch;
   - a `wiki-grounding-auditor` flagged a correct date as DRIFTED.

   All three were caught by re-verification: a re-decode script, `git diff` before the audit,
   and `git log`.
   - **No new mechanism authored.** The gap is that an auditor audits what is on the page, so a
     **removed** cite is invisible to it; only the orchestrator's diff check caught it. A
     deterministic "cites removed by this pass" check in `/wiki-self-update` would close it.
     That is out of item 142's scope, and it is **surfaced to the owner** here and in the close
     summary. **Unenforced.**
3. **A binary was called by bare name when it was not on PATH** (`ruff`; the
   `verify-binary-on-path` class).
   - **Mechanism:** the existing `verify-binary-on-path` guard refused it before it ran, and
     `python -m ruff` was used. No new mechanism needed.
4. **Low RAM kept the local gate from running** (the owner's standing condition; memory
   `project-laptop-memory-pressure-is-transitional`).
   - **Mechanism:** the gate's own memory preflight, plus `ci_wait` on the PR. No new one
     needed.

---

## What this branch should build

`fix/bash-tool-transport`, items **157** and **158** only. This is the owner's pick
(2026-10-08), under item 40's drawdown direction. The filed items are
`docs/dev/work/items/0157-msys-noglob-root-cause-for-backslash-collapse.md` and
`docs/dev/work/items/0158-bash-unexpected-eof-matching-quote.md`.

1. **C-7 instrument first**, into `docs/dev/diagnosis/bash-tool-transport.md`. Neither
   mechanism is verified.
   - **Item 158:** decode the commands that drew `unexpected EOF while looking for matching`.
     - The transcripts are under `~/.claude/projects/C--Dev-sartor/`: `2b79cef7`,
       `d3d2e857`, `dde107cd`, `f0c731c3`, `ec0ddb33` and `0ea1b8bf`.
     - For each, decode the `tool_use` `input.command` with `json.loads`, find its
       `tool_result`, and confirm that bash really refused it (rather than the string being
       quoted in text).
     - Record each command's quote structure, length and backslash content.
     - The decode pattern is in `docs/dev/diagnosis/heredoc-escape-guard.md` O5. Write the
       script with the Write tool.
   - Reproduce one through a standalone `bash.exe -c` and through stdin. The helpers to reuse
     are `tests/test_bash_backslash_collapse.py::_git_bash` and `_run`.
   - **Item 157 has a bootstrapping problem.** The new guard refuses any Bash-tool command
     containing `\\` on win32, so the dossier's O1 probe cannot be sent through the Bash tool
     while the guard is live. Decide how to observe before changing anything.
     - `echo "${MSYS-unset}"` through the Bash tool, after a settings change and a session
       restart, shows whether the env reaches bash. That is indirect evidence.
     - The standalone repro shows what `MSYS=noglob` does.
     - **Not verified:** whether a user-typed `! <command>` passes through PreToolUse hooks.
2. **Then the change, shaped by what the instrument shows.**
   - If `.claude/settings.json` `env` `MSYS=noglob` reaches the Bash tool and stops the
     collapse, decide with the owner whether to retire `block-doubled-backslash` or key it on
     the measured behaviour.
   - Update `tests/test_bash_backslash_collapse.py` in the same diff.
   - Check what `MSYS=noglob` changes for child processes (tests, hooks, git) by running the
     suites.
   - Fix item 158 only as far as its evidence shows.
3. **C-10.** `.claude/settings.json` is read by:
   - `tests/test_settings_hooks_python_direct.py`;
   - `tests/test_governance_hooks_gate.py` (`_wired_by_event`);
   - and possibly others.

   Re-derive the list grep-complete into `docs/dev/blast-radius/bash-tool-transport.md` before
   the first edit. If the guard changes, its consumer list is in
   `docs/dev/blast-radius/heredoc-escape-guard.md`; re-derive it rather than trusting it.

Scope is bounded to items 157 and 158 as filed in `docs/dev/work/items/`. Do not expand beyond
them.

---

## First move

Create branch `fix/bash-tool-transport` off `main`, write a plan
at `~/.claude/plans/<slug>.md`, and show it to the user before touching any
code. **Do not code first.**

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
