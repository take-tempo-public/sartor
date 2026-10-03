<!-- provenance: schema=1 session=1712f657-d0d8-43fc-a659-be8f038070ec branch=chore/release-v1.1.0 commit=f66d3a9 actor=amodal1 agent=anthropic/claude-opus-5-5 generated_at=2026-10-02 -->

# Agent handoff — E1 pre-flight close (`chore/release-v1.1.0`)

**Branch to create:** none up front. The first move is planning the Open-item drawdown with the owner; the first drawdown branch comes off `main`.
**Base branch:** `main`

> **E1 stopped at its pre-flight. The release cut did not happen.** The owner set the path to the
> public cut on 2026-10-02:
> 1. **The version stays 1.1.0.** Relabeling as "1.0" was considered and withdrawn.
> 2. **Draw the board's Open items down, to 0 if possible.** 40 are open at this close, including the
>    launcher items 145–147.
> 3. **Stage a 1.1.0 alpha.** The owner runs an end-to-end test on a fresh clone.
> 4. **Public 1.1.0** comes only after the owner approves that alpha.
>
> Recorded on item 40 (2026-10-02 update).
>
> **Item 19 can't close on current evidence.**
> - Its child, item 30, fails at 3.3% per attempt.
> - It has 0 failures in the 47 runs since 2026-09-03, but nothing changed on its code path. At
>   3.3%, a clean streak that long happens about 21% of the time by chance.
> - So the item-30 `fix/*` branch (C-7) is one of the drawdown branches.
>
> The model for the next session is the owner's call; nothing prescribes one.

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

**Stream:** Epic E, `epic/e-release` (board 40), the public v1.1.0 cut. Its one sprint, E1, is
paused at pre-flight.
**Sequencing rule:** strictly sequential, one branch at a time.
**Blocked until this stream tags:** the 1.1.x epic series.

- ~~Epics A, B, C, D~~ ✓ merged to `main`. D landed as PR #150 (`f66d3a9`) this session.
- ~~**`chore/release-v1.1.0` (E1 pre-flight)**~~ ← this branch. It re-measured item 30, closed
  epics 37/38/39 and item 125, and recorded item 7's draft list.
- **Open-item drawdown** ← next: owner-ordered branches, grouped by area. Candidates include
  `fix/ux-keyboard-reorder-timeout-recurrence` (30 → 19), the item 7 memory-consolidation
  apply (approved), item 144 (slim and commit the flake shard), and groups such as
  117/119/120/121 (run lock), 118 (redaction), 123/124/136/142/143 (hooks).
- **1.1.0 alpha staging**, then the owner's fresh-clone e2e test, then the E1 cut (recreate
  `chore/release-v1.1.0` off `main`).

**Don't start the cut, the version bump or the CHANGELOG cut during the drawdown.** Item 10
still depends on 3, 7 and 19, and on the owner's alpha approval.

---

## What just landed on `main`

- **The Epic D PR, #150**, merged as `f66d3a9`.
  - `ci_wait` exit 0: 8/8 required checks, no absorbed reruns.
  - The handoff `docs-assets-enforcement.md` was consumed (ledger row `5c15e5a`).
  - The pointer had to be regenerated from the committed file because the original was lost;
    the owner confirmed.
- **This branch's PR** (if merged by the time you read this) carries:
  - **Item 30 re-measured** over 123 new runs (PARTIAL: 4 logs expired, 1 session
    unreconciled).
    - The shard `985e9282` is **held uncommitted** in `docs/dev/flake-rates/runs/` for slimming
      (item 144, owner decision). Don't delete it: it's the only copy, because CI logs expire.
    - 5/153 failed attempts, including two occurrences not previously filed: run `31449717508`
      (08-11) and run `33805467341` (09-03, raw-log verified).
    - The full table is in item 30's 2026-10-02 update.
  - **Item 19** gets a dated verdict: it can't close.
  - **Item 125 closed** on the owner's decision that an epic closes on its merge PR plus a green
    CI run.
    - Epics **37/38/39 closed** on that rule. Their PR runs have 0 reruns per the store.
    - 39's open children (134, 135, 138, 139, 141) were re-parented to Open, at the owner's
      direction.
  - **Item 7:** the keep/consolidate/delete list was **approved by the owner**. It is applied on
    its own branch, starting with a re-grep of every delete row.
  - **Item 128** has a process inventory. **Items 143 and 144** are new. Item 40 records the
    owner's cut sequence.
  - **Gate:** see the commit message for the run that preceded the commit.
    - The first attempt was refused by the memory preflight (0.99 GB free, floor 1.00 GB). No
      tests ran.
    - The background-task notification for that run reported exit 0. The log said exit 1.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

The authoritative home is `docs/dev/work/BOARD.md`. **Header: "Open 40 / 10 ceiling -- OVER".**
The owner has now directed the drawdown: to 0 if possible, before alpha staging.

`## Open` (40), one line each; full text in `docs/dev/work/items/`:
- **50** *(owner)*: C-7/C-10 are hook-only and don't travel to other agents.
- **98**: wiki freshness measures checkpoint staleness, not page staleness.
- **99**: install.md documents never-published distribution paths.
- **105**: corpus import produces no education entries.
- **106**: Compose bullet edits don't reach a frozen application.
- **107**: no account-naming step on first run.
- **111**: `check-plan-approved.sh` costs about 2 s per edit on Windows.
- **112**: the console's Since filter raises TypeError (naive vs aware dates).
- **115**: UX-8 needs a `getComputedStyle` assertion.
- **116**: the "Run this fixture" bubble was never browser-verified.
- **117**: paid diagnostics runs have no server-side single-flight lock.
- **118**: redaction misses quoted-key headers and Basic auth.
- **119**: the run lock has no owner; 3 `acquire()` sites ignore its result.
- **120**: a declined run leaves its button pulsing.
- **121**: `run_detail` reads the whole log; a non-object line gives a 500.
- **122**: weak C3 test assertions.
- **123**: `verify-binary-on-path` blocks brace groups.
- **124**: recurrence: bare `ruff` gets hook-blocked.
- **128** *(owner)*: stray python processes. Inventoried 2026-10-02: 13 stdin-reader hook
  helpers.
- **129** *(owner)*: personal framing in two frozen records.
- **130**: profile edits likely never reach `Candidate`.
- **131**: a retired application can't be found again.
- **132**: "Submit answers and regenerate" may not change a frozen résumé.
- **133** *(owner)*: no way to delete a candidate profile.
- **134**: the Tuning vs Quality smoke cost estimates contradict each other. Was a child of 39.
- **135** *(owner)*: close-out protocol copies drift from `maintainer-lane.md`. Was a child of 39.
- **136**: `block-merge-to-main` matches merge text anywhere in a command.
- **137**: review the models and call settings for performance and cost.
- **138** *(owner)*: the Settings drawer has no help bubble. Was a child of 39.
- **139**: `capture_screenshots` leaves its demo user behind. Was a child of 39.
- **140**: LLM output leaks bullet ids, and the cover letter invents its date. Two screenshots
  show it.
- **141**: `wiki-scribe` has no Write tool. Was a child of 39.
- **142**: recurrence: heredoc backslash escapes corrupt files.
- **143** *(new)*: a witness-paused plan Write batched with `ExitPlanMode` gets the stale plan
  approved.
- **144** *(new)*: in the flake shard, `skipped_nodeids` takes 63% of the bytes. The shard is
  held uncommitted until it's slimmed.
- **145** *(new, owner-directed)*: the stdlib launcher plus per-OS one-click launchers. These
  are the owner's 2026-08-16 pre-launch requirement, which was never filed until now.
- **146** *(new)*: a health endpoint, a single-instance launch and a pid file. A second
  launch currently just retries :5000, and macOS AirPlay also listens on :5000.
- **147** *(new)*: an in-app Quit, opt-in idle shutdown, and `beforeunload` only for
  unsaved edits. A tab close must not stop the server.
- Plus the two open epics: **19** (UX flake) and **36** (epic A).

`## Blocked` (4): **3** (owner GitHub toggles), **5**, **8**, **97**.

`## Deferred` (9): **4**, **7** (PX-46; list APPROVED 2026-10-02, apply on its own branch),
**24**, **25**, **41**, **42**, **43**, **113**, **114**.

Plus `## Watching` (45, including **30**). Full detail: `BOARD.md`.

Declared, not filed (still true):
- **A stale comment** at `db/build_context.py:92`. Fold it into any branch that touches that
  file.
- **The doc-writing skill's evaluation plan has not been run.** When to run it is the owner's
  call.
- **32 one-way wiki backlinks** (WARN).

---

## Recurrences observed this session → guardrail authored

1. **A background task's reported exit code disagreed with its log** (twice: `flake_rates
   collect` was reported 0 and was really 3; `scripts.gate` was reported 0 and was really 1).
   - **How it was recognized:** it is a known class, recorded in memory as
     `reference-background-task-exit-code-unreliable`.
   - **Caught by:** writing `exit=$?` into each log and reading the log.
   - **No mechanism authored:** this is harness behavior, outside the repo's hooks.
     **Surfaced to the owner.**
2. **A subagent's report carried a wrong fact** (C-12 class; the third handoff in a row to note
   it). The memory-classification agent said the `warn_unreachable` gotcha had no repo home; it
   does.
   - **Caught by:** spot-checking before relying on the report.
   - **No mechanism authored:** no deterministic check can verify a subagent's prose claim. The
     item 7 entry says to re-grep before applying. **Surfaced to the owner.**
3. **The interrogative-witness pause caused harm, not just friction, TWICE this session**
   (the second time, a batched Bash assembly ran on stale content; caught before commit) (handoff recurrence 4 was
   friction only).
   - **What happened:** batched with `ExitPlanMode`, the pause made the owner approve a stale
     plan.
   - **Recorded as:** item 143 and memory `reference-witness-pause-stale-plan-approval`. Item
     143 names two candidate mechanisms.
   - **No mechanism authored on this branch:** it's a hook change, outside an E1 docs branch's
     scope. **Surfaced to the owner.**
4. **Unfiled occurrences of a tracked flake.** Item 30 had two occurrences no session filed:
   08-11, and a Dependabot run on 09-03.
   - **The existing instrument caught them:** `scripts/flake_rates.py` plus its committed store
     (C-11 mechanism, `feat/flake-rate-measurement`).
   - **No new mechanism needed.**

---

## What this branch should build

1. **The drawdown plan, made with the owner.** Group the 40 Open items, plus the approved item 7
   apply, into branches by area and confirm the order with the owner. About 8 are owner
   decisions (50, 128, 129, 133, 135, 138, …), so ask those questions first; they may close
   without code.
2. **Each drawdown branch is one session with the full close-out.** A `fix/*` branch obeys C-7:
   the diagnosis dossier and an instrument come first.
   - **For item 30 specifically:**
     - `## Observed` takes its five occurrences (item 30's 2026-10-02 table): a 30 s
       `TimeoutError` in `ui_pages/wizard_compose.py` `_wait_settled` at reach 8–9, every
       quiescence signal ready, the retry passing within about 4 s.
     - `## Falsified` takes the 2026-07-31 `networkidle`/iframe mechanism
       (`docs/dev/diagnosis/ux-keyboard-reorder-timeout.md`).
     - Build a deterministic probe from the `[settle-instrument]` dumps; don't run a rate
       campaign. Proving a fix by CI rate alone would take about 90 clean runs.
3. **Item 144 early.** The uncommitted flake shard is the only copy of its measurement.

Scope is bounded to the owner's 2026-10-02 sequence on item 40 (the drawdown before alpha
staging). Do not expand beyond it.

---

## First move

Check the pointer and consume this handoff. Confirm with the owner that this branch's PR has
merged. Then draft the drawdown grouping as a plan at `~/.claude/plans/<slug>.md` and show it to
the user before creating any branch or touching any code. **Do not code first.**

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
