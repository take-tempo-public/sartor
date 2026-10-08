<!-- provenance: schema=1 session=5f4fe262-d09f-45da-9268-e91d8a54335d branch=fix/bash-tool-transport commit=176ef94 actor=amodal1 agent=anthropic/claude-opus-5-5 generated_at=2026-10-08 -->

# Agent handoff — Bash-tool transport (`fix/bash-tool-transport`, items 157 + 158) → test reliability (items 155 + 156)

**Branch to create:** `fix/test-reliability` (branch off `main`)
**Base branch:** `main`

> **This session closed items 157 and 158.** Both are about how the Bash tool hands a command
> to Git Bash on Windows.
> - **The harness's form.** The harness runs every command as `bash -c "<setup> && eval '<cmd>'"`,
>   with each `'` rewritten as `'"'"'` and every `"` escaped as `\"` on the Windows command line.
> - **157 is falsified.** `MSYS=noglob` makes every quoted command in that form unparseable, so
>   it is no fix for item 142's halving. `settings.json` is unchanged, and
>   `block-doubled-backslash` stays.
> - **158 is mostly a second transport defect.** Git Bash silently cuts the command line at
>   8,186 characters, which accounts for 6 of the 7 recorded refusals. The new Bash guard
>   `block-long-bash-command` refuses an over-budget command on win32. It was verified live in
>   this session. The 7th refusal was a command malformed as written.
>
> **The owner chose the next branch (2026-10-08): items 155 + 156**, two unverified test flakes.
>
> **CI is the gate.** The local gate refused at its memory preflight (0.72 GB free).

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
- ~~`fix/heredoc-escape-guard`~~ ✓ (#161): item 142 closed, items 157 and 158 filed.
- ~~`fix/bash-tool-transport`~~ ✓ (PR pending): items 157 (falsified) and 158 closed.
- **`fix/test-reliability`** ← next (owner's pick, 2026-10-08): items 155 and 156 only.
- Not started: item 7 memory-consolidation apply (Deferred), item 30's C-7 probe branch,
  launcher items 145–147, and the owner-decision items (50, 128, 129, 133, 135, 138).

**Don't start the cut, the version bump or the CHANGELOG cut.** Item 10 still depends on 3, 7
and 19, and on the owner's alpha approval. Don't fold any other item into the 155/156 branch.

---

## What just landed on `main`

Once the owner confirms the PR (merge commit; never squash or rebase),
`fix/bash-tool-transport`:
- **`a00ed38`: the C-7 instrument.** No production code.
  - `docs/dev/diagnosis/bash-tool-transport.md`, O1–O7:
    - the harness wrapper, read through `/proc/$$/cmdline` (O1);
    - the raw Windows command line, read through `Win32_Process` (O2);
    - `noglob` breaking quoting on that exact form (O3);
    - the 8,186-character cut (O4), counted in characters (O5);
    - the cut reproduced inside the harness, with the wrapper measured at 408 characters
      (O6);
    - item 158's seven real failures, decoded and replayed safely (O7).
  - `tests/test_bash_backslash_collapse.py` now also pins O3 and O4. Its seven Git Bash arms
    start concurrently: 1.30 s against 4.28 s sequential, measured.
  - The C-10 dossier `docs/dev/blast-radius/bash-tool-transport.md`, and this session's
    consumed-ledger file.
- **`219ea83`: the guard.**
  - `scripts/enforcement/guards/block_long_bash_command.py` checks
    `len + 4 × '` against `CUT − RESERVE` = 8,186 − 1,024. It costs O(n), with no subprocess.
  - It is registered in `claude_hook._GUARD_MODULES` and `bash_dispatcher._GUARD_ORDER`.
    `settings.json` is unchanged.
  - Governance: the 14th enforced blocker rule (with a dated amendment), the Bash dispatched
    set, and the extraction gap.
  - Docs: `enforcement.md`, `tooling.md`, `CLAUDE.md`, `CHANGELOG.md`.
  - The `noglob` claims are corrected in the `block_doubled_backslash.py` docstring and the
    item-142 dossier.
- **`b0e9599`:** items 157 and 158 closed with `verified_by`. The board was regenerated: Open
  went from 30 to 28.
- **`176ef94`:** a scoped wiki pass over two pages (owner-authorized; audits 31/0/0 and 20/0/0;
  checkpoint not advanced).
- This handoff's commit.
- **Tests** (all `-p no:rerunfailures`, local Windows, one file per run):
  - `test_enforcement_core.py`: 92 passed and 2 skipped (the off-Windows cases) in the
    Bash-guard half; 92 passed in the other half;
  - governance 13, coverage 5, doc-lints 27, settings-shape 6, evidence 27,
    consumer-enumeration 22, wiki-relevance 6, and the premise test 5: all passed;
  - `check_doc_links`: OK (622 files); `work_items check`: OK; `mypy` and `ruff` clean on the
    changed files.
- **Live:**
  - an 8,340-character Bash command was refused with `BLOCKED (block-long-bash-command)`;
  - a short command ran, and re-measured the wrapper at 408 characters;
  - `printf '%s\n' 'LIVE-3 A\\b'` is still refused by `block-doubled-backslash`.
- **Gate:** `python -m scripts.gate` gave `FAILED at memory preflight (exit 1)` at 0.72 GB free.
  **CI on the PR is the gate:** `python -m scripts.ci_wait <n>`, and exit 3 means stop.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

The authoritative home is `docs/dev/work/BOARD.md`. **Header: "Open 28 / 10 ceiling -- OVER"**
(30 at this branch's start; items 157 and 158 closed). The owner's drawdown direction stands:
down to 0 if possible, before alpha staging. Well past the ~8–10 reduction-sprint threshold.

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
- **128** *(owner)*: Stray python3.13 processes from earlier sessions. **Still true at this close:** five python3.13 processes started 2026-09-18 to 10-06 are alive, none of them this session's.
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
- **155**: A CI attempt saw 'Notes saved', never 'Company saved', for 5 s after the company blur. Retry passed; cause unverified. ← **next branch**
- **156**: On Windows a writer thread's own pre-read hit PermissionError mid-replace; its delta was lost. Test or code: unverified. ← **next branch**

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
- **Pre-existing count drift**, each deferred again in
  `docs/dev/blast-radius/bash-tool-transport.md`:
  - `docs/governance/enforcement.md:29-31` says "8 exist"; there are now 14 rules;
  - `tests/test_enforcement_core.py`'s `TestBashDispatcher` docstring names four guards (there
    are seven);
  - `scripts/enforcement/blast_radius.py`'s `result.py` entry says "10 non-test importers"; this
    branch added one more.
- **The interrogative-witness pause re-arms after task notifications and subagent hand-backs.**
  It fired three more times this session: once after a background `pytest` notification and
  twice after subagent hand-backs. `enforcement.md` names the hand-back case; the
  task-notification case is still not named. (Recurrence; see below.)
- **New: item 142's `block-doubled-backslash` has no `CHANGELOG.md` entry** (0 hits; found by
  this branch's C-10 search 5). Back-filling it was outside items 157 and 158.
- **New: `test_enforcement_core.py`'s non-Bash half took 435 s locally** at about 1 GB free.
- **Updated:** `tests/test_bash_backslash_collapse.py` (previously about 27 s) now runs its seven
  Git Bash arms concurrently in 1.30 s. The whole file took 10–20 s, with the rest spent in
  pytest setup outside its arms.

---

## Recurrences observed this session → guardrail authored

1. **The Bash tool refused a whole long command with `unexpected EOF while looking for
   matching`** (item 158's class).
   - **Recognized as a recurrence:** six recorded failures across six sessions (2026-09-22 to
     2026-10-07), plus the owner's memory note. This session reproduced it inside the harness
     (dossier O6).
   - **Mechanism, fails closed:**
     - `scripts/enforcement/guards/block_long_bash_command.py`, run in `bash-dispatcher`;
     - `tests/test_enforcement_core.py::TestBlockLongBashCommandUnit` and the two
       `TestBashDispatcher` cases;
     - `tests/test_bash_backslash_collapse.py::test_the_command_line_cuts_at_8186`, which pins
       the guard's `CUT` to the runtime.
   - **Known limit:** `RESERVE` (1,024) estimates the harness's wrapper (408 measured). A
     harness release that grows it needs a re-measure.
2. **An instrument scoped to the hypothesis confirmed it** (C-7 rule 3; item 142's O4 `noglob`
   arm used a payload with no `"`).
   - **Recognized as a recurrence:** the binding rule exists because of this class. This
     session's wider instrument (the harness's own form, O3) falsified the conclusion.
   - **No new mechanism for the class.** How wide to scope an instrument is a judgment, and no
     gate can make it.
   - **The specific risk is pinned:** `test_msys_noglob_breaks_the_harness_quoting` fails if
     `noglob` ever starts carrying the harness's form intact, which would reopen 157.
   - Surfaced to the owner in the close summary.
3. **The interrogative-witness pause re-armed after a task notification and after subagent
   hand-backs** (the previous handoff's new observation).
   - **No new mechanism.** It is outside items 157 and 158, and each instance cost one re-run.
     The task-notification case is still not named in `enforcement.md`.
   - **Unenforced.** Surfaced to the owner in the close summary.
4. **Low RAM kept the local gate from running** (the owner's standing condition; memory
   `project-laptop-memory-pressure-is-transitional`).
   - **Mechanism:** the gate's own memory preflight (observed: `FAILED at memory preflight`),
     plus `ci_wait` on the PR. No new one needed.

---

## What this branch should build

`fix/test-reliability`, items **155** and **156** only. This is the owner's pick (2026-10-08),
under item 40's drawdown direction. The filed items are
`docs/dev/work/items/0155-company-save-toast-preempted-by-notes-blur.md` and
`docs/dev/work/items/0156-concurrent-writers-test-unguarded-read-windows.md`.

1. **C-7 instrument first**, into `docs/dev/diagnosis/test-reliability.md`. Neither mechanism is
   verified.
   - **Item 156** (`tests/test_hardening.py:1171`, `:1185`): run
     `test_concurrent_writers_do_not_erase_each_other` in a loop on Windows with
     `-p no:rerunfailures`. Record:
     - the failure rate over N runs;
     - for each failure, where the `PermissionError` lands: the test's own pre-call read
       (`:1171`, outside `context_transaction`), or a read inside `context_transaction`. The
       latter would make it a product defect on Windows.

     Memory `reference-atomic-context-write-windows` holds the related class.
   - **Item 155** (`tests/ux/regression/test_20260611_prior_app_resume_robustness.py:125`):
     loop the single test under CPU load (memory `reference-cpu-saturation-flake-repro`), and
     capture the focus and blur order and both PUTs on a failing attempt.
     - The notes blur toasts `Notes saved` on every blur (`static/app.js:6519-6534`). The
       company blur toasts only after its PUT (`:6571-6575`).
     - `ui_pages/prior_apps.py:54-62` is the selector side.
     - A deterministic capability probe beats a rate campaign where one is possible (memory
       `reference-deterministic-capability-probes-for-rival-hypotheses`).
   - Scope each instrument wider than its hypothesis: for 155, the test waiting on a shared
     toast, the app saving on an unchanged blur, or something else.
2. **Then the change, shaped by what the instrument shows**: test or code, per item. A UX-flake
   fix must be A/B'd against the real test in a loop (memory
   `feedback-ab-fix-against-real-test-not-just-instrument`), not only against the instrument.
3. **C-10:** if the fix touches `hardening.context_transaction`, `static/app.js`'s blur handlers
   or `ui_pages/`, enumerate their consumers grep-complete into
   `docs/dev/blast-radius/test-reliability.md` before the first edit.

Scope is bounded to items 155 and 156 as filed in `docs/dev/work/items/`. Do not expand beyond
them.

---

## First move

Create branch `fix/test-reliability` off `main`, write a plan
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
