<!-- provenance: schema=1 session=08aa18b5-343e-407c-8277-8593ec0831e9 branch=fix/python-direct-hooks-plan-gate commit=a17fa19 actor=amodal1 agent=anthropic/claude-opus-5-5 generated_at=2026-10-07 -->

# Agent handoff — Python-direct hooks (`fix/python-direct-hooks-plan-gate`) → heredoc-escape guard (item 142)

**Branch to create:** `fix/heredoc-escape-guard` (branch off `main`)
**Base branch:** `main`

> **This session fixed items 152, 111, 154 and 143** as one group (the owner's pick).
> - Every Claude Code hook is now Python, launched as
>   `python3 "${CLAUDE_PROJECT_DIR}/scripts/enforcement/adapters/hook.py" <name>`.
>   `hooks/*.sh` are gone, and the plan gate is `scripts/enforcement/plan_gate.py`.
> - Item 154's cause was **observed**: hooks cancelled by their harness timeouts. A cancelled
>   PreToolUse hook does not block, so the gates were open. The rebase was not the cause.
> - Median timings: Edit|Write 18 s → 2.4 s, retire 36 s → 3.0 s.
> - The four items are closed, and the branch merges through its PR.
>
> **The owner chose the next branch (2026-10-07): item 142.** Its heredoc-escape corruption
> recurred **three more times** on this branch, once writing literal backspace bytes into a test
> file. Under C-11 a recurrence obliges a mechanism.
>
> **CI is still the gate** (owner-directed while RAM is 0.5–0.8 GB). This session also saw
> Claude Code kill a background pytest for low memory.

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
- ~~`fix/python-direct-hooks-plan-gate`~~ ✓ (PR pending): items 152/111/154/143 closed.
- **`fix/heredoc-escape-guard`** ← next (owner's pick, 2026-10-07): item 142 only.
- Item 7 memory-consolidation apply (Deferred); item 30 C-7 probe branch; launcher items
  145–147; item 155 (UX flake): not started.

**Don't start the cut, the version bump or the CHANGELOG cut.** Item 10 still depends on 3, 7
and 19, and on the owner's alpha approval. Don't fold any other item into the item 142 branch.

---

## What just landed on `main`

Once the owner confirms the PR (merge commit; never squash or rebase),
`fix/python-direct-hooks-plan-gate`:
- **`5431b83`: the C-7 instrument.** The dossier
  `docs/dev/diagnosis/python-direct-hooks-plan-gate.md` holds O1–O3 (transcript evidence)
  and the C-10 dossier `docs/dev/blast-radius/python-direct-hooks-plan-gate.md`.
  `TestKilledHookRetirements` gave **3 failed** against the `.sh` hooks.
- **`0fd590f`: the change.**
  - `scripts/enforcement/adapters/hook.py` is the one launcher.
  - `scripts/enforcement/plan_gate.py` is the port. It runs first inside the Edit|Write
    dispatcher, `mark` fails closed, and a newer unapproved plan blocks edits.
  - `plan-write-landed` (PreToolUse ExitPlanMode, item 143) and the `shell-probe`
    (SessionStart) are new.
  - `cleanup-plan-on-merge` was removed (owner decision).
  - The guard modules import lazily.
  - `tests/test_settings_hooks_python_direct.py` enforces the command shape.
  - `tests/conftest.py` isolates plan-gate state and `CLAUDE_CODE_SESSION_ID` per test (O7: a
    test had been writing fake `compacted` rows into the live ledger).
  - Six historical links into `hooks/` were re-pointed to commit-pinned permalinks.
- **`a17fa19`:** items 111/143/152/154 closed with `verified_by`, and an item 142 recurrence
  update. A scoped wiki pass edited `route-surface` (owner-authorized; auditor 15/0/0;
  checkpoint not advanced).
- This handoff's commit.
- **Tests** (all `-p no:rerunfailures`):
  - `test_plan_approval_scoping` 37/37;
  - `test_enforcement_core` 153/153;
  - nine more hook and doc suites, 170 (one failure on the first run, fixed);
  - doc gates 62/62;
  - `check_doc_links` OK.
- **Live:** Claude Code hot-reloaded the new `settings.json` mid-session. Since the switch,
  this session's hooks have had zero `hook_cancelled`; before it, 31 of 40 Edit/Writes had the
  dispatcher cancelled.
- **Gate:** ruff, format and mypy are green locally (`python -m scripts.gate` was not run: low
  RAM). **CI on the PR is the gate:** `python -m scripts.ci_wait <n>`, and exit 3 means stop.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

The authoritative home is `docs/dev/work/BOARD.md`. **Header: "Open 28 / 10 ceiling -- OVER"**
(it was 32 at this branch's start: items 111, 143, 152 and 154 closed). The owner's drawdown
direction stands: down to 0 if possible, before alpha staging. Well past the ~8–10
reduction-sprint threshold.

`## Open` (26 items; the header also counts open epics). Generated from the board;
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
- **128** *(owner)*: Stray python3.13 processes from earlier sessions. **New data this session:** 23 orphans from 2026-09-18 → 10-06 (about 0 MB each), mostly the old hooks' `python3 -c "import sys,json…"` stdin readers, left when the harness cancelled a hook. This session's own two were stopped by PID. The Python-direct hooks have no inner `python3 -c` child, so new orphans of that shape should stop.
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
- **142**: Heredoc python scripts with backslash escapes wrote a backspace char and a broken file; a Bash guard could refuse them. ← **next branch**
- **145**: Owner pre-launch requirement (2026-08-16), unfiled till now: stdlib launcher, two backends, per-OS one-click wrappers.
- **146**: A second launch starts a second server attempt on :5000; nothing identifies a running sartor or stops it cleanly.
- **147**: Closing the tab leaves the server running (correct), but there is no in-app way to stop it and no idle exit.
- **155**: A CI attempt saw 'Notes saved', never 'Company saved', for 5 s after the company blur. Retry passed; cause unverified.

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
  free (one subprocess, the minimum; the ambiguity check needs the whole tree).
- **Transitive wiki relevance is not modelled.** `docs/dev/perf/PERFORMANCE_HISTORY.md`
  (wiki-cited) mentions `scripts/perf_baseline.py`; the wiki does not, so it stays irrelevant.
- **New: `python3` resolution on hypha and the homelab is unchecked** (item 152's "Before
  building" bullet). It is no regression, since every retired wrapper `exec`-ed `python3`. On a
  machine without `python3` on PATH no hook starts and the gates fail open
  (`docs/governance/enforcement.md`). Check it on first use there.
- **New: `tests/test_plan_approval_scoping.py` takes about 6 minutes locally** (37 tests, each
  starting a Python process and running git). One file run with a 590 s `timeout` wrapper was
  killed by it. Split by `-k` class when running locally.
- **New: `scripts/wiki_relevance.py:65` still lists `hooks/`** as an irrelevant prefix. With the
  directory gone it matches nothing; it was kept so as not to touch a gated classifier for no
  behaviour change (blast-radius dossier `## Deferred`).

---

## Recurrences observed this session → guardrail authored

1. **Plan approval retired, or edits run unguarded, because a hook outran its timeout** (item
   110's class; item 154 was its recurrence). Recognized from the transcripts: O1 shows the same
   killed-retire and stale-stamp shapes item 110 proved.
   - **Mechanism, fails closed:**
     - `scripts/enforcement/plan_gate.py`: there is no fork on the steady path, `mark` drops
       the marker before writing, and a newer unapproved plan blocks edits.
     - `tests/test_plan_approval_scoping.py::TestKilledHookRetirements` holds the reproductions.
     - `tests/test_settings_hooks_python_direct.py`: no shell wrapper can return.
   - **Known limit:** a machine slow enough can still cancel a hook (a faster gate, not an
     instant one).
2. **A hook guard false-fired on text it should not read** (O2: the merge hook grepped tool
   output; the same class as `fix/plan-approval-hook-scope`'s 2026-07-17 incident).
   - **Mechanism:** the hook is removed, and
     `TestKilledHookRetirements::test_merge_phrases_in_tool_output_never_retire_on_a_pr_merge_head`
     runs every PostToolUse Bash command as wired, asserting none retires anything.
3. **Heredoc backslash escapes corrupted files, three times** (item 142's class; the owner's
   memory has recorded it since 2026-08-05).
   - **No mechanism on this branch:** out of the owner-named scope. **Surfaced to the owner**,
     who made it the next branch.
4. **A reader batched with the Write it depends on ran on missing or stale input**, twice
   (item 143's class, its 8th and 9th instances).
   - **Mechanism for the high-stakes half:** `plan-write-landed`, tested by
     `TestPlanWriteLanded`.
   - **For the general half, none is possible:** a per-call hook cannot cancel the rest of a
     batch. That is declared in `docs/governance/enforcement.md` and surfaced to the owner.
5. **A test wrote into live, tracked state** (O7: fake `compacted` rows in the session ledger;
   the same class as item 151's gate-result overwrite and item 33's `llm_calls.jsonl` leak).
   - **Mechanism, fails closed:** `tests/conftest.py::_no_live_session_id` and
     `_isolated_plan_gate_state`. Verified by an unchanged ledger sha256 across a re-run.
6. **A `timeout … | tail` wrapper hid a killed pytest as exit 0** (the previous handoff's
   `timeout 120` gate run is the same class).
   - **No mechanism:** it was caught by the missing summary line. Recorded in the owner's memory
     (`reference-pytest-exit-through-pipe`). Prose only, **unenforced**.
   - **Candidate for a later branch:** a `bash-dispatcher` guard refusing `pytest … | ` with no
     `PIPESTATUS`/redirect.
7. **The C-10 enumeration missed a consumer** (`test_enforcement_core.py:1080` pinned
   `_GUARD_ORDER`; the grep searched names, not that symbol). The same class as the
   `loadComposition()` case AGENTS.md cites.
   - **No new mechanism:** caught by the targeted test run, and recorded as row 41 "found late"
     in the blast-radius dossier.
8. **Subagent and tool reports carrying facts:** `wiki-scribe` and `wiki-grounding-auditor`
   reports. The scribe's edit was checked against `git diff` before the auditor ran, and the
   auditor's key claims match code read directly this session.

---

## What this branch should build

`fix/heredoc-escape-guard`, item **142** only: the owner's pick (2026-10-07), item 40's
drawdown direction, and `docs/dev/work/items/0142-heredoc-python-escape-corruption-guard.md`.

1. **C-7 instrument first.** The mechanism is **not verified**, and the item's candidate rests
   on an assumption this session's evidence doubts.
   - Every corrupting command on `fix/python-direct-hooks-plan-gate` used a **quoted**
     delimiter (`<<'PYEOF'` / `<<'EOF'`), which bash does not escape-process. The corrupted
     shapes were a script written by `cat > file <<'PYEOF'` and then run, and a
     `python - <<'EOF'` script. So the escapes were likely collapsed **before** bash, in how the
     command reaches the shell. **Inferred, unverified.**
   - Instrument: send a quoted-heredoc command whose body holds `\b`, `\n` and `\|`, through
     the Bash tool and through PowerShell. Byte-dump what lands (`od -c`), and record which
     layer changes the bytes. Write `docs/dev/diagnosis/heredoc-escape-guard.md` `## Observed`
     before any guard.
2. **Then the guard, shaped by what the instrument shows.** It is a `bash-dispatcher` guard
   module in `scripts/enforcement/guards/` (the same pattern as `verify_binary_on_path.py`; the
   registry is `claude_hook._GUARD_MODULES` and `bash_dispatcher._GUARD_ORDER`).
   - If the corruption is pre-bash, the item's `python -` candidate is too narrow. It must also
     catch `cat > X <<…` bodies holding backslashes.
   - The message: "write the script with the Write tool and run it by path".
   - Fail open on anything it cannot parse (the `shell_split` pattern).
3. **C-10.** Adding a Bash guard touches the governance count and its consumers:
   - `tests/test_governance_hooks_gate.py` `BLOCKER_RULE_NAMES` (12 → 13) and
     `BASH_DISPATCHED_GUARD_NAMES`;
   - `docs/dev/tooling.md`'s guard table (the doc lint checks it);
   - `docs/governance/enforcement.md`, CLAUDE.md's hook list, and
     `tests/test_enforcement_coverage.py`.
   Re-derive these grep-complete into `docs/dev/blast-radius/heredoc-escape-guard.md` before the
   first edit. **Grep the symbols too, not only the names** (row 41's lesson: `_GUARD_ORDER`).

Scope is bounded to item 142 as filed in `docs/dev/work/items/`. Do not expand beyond it.

---

## First move

Create branch `fix/heredoc-escape-guard` off `main`, write a plan
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
