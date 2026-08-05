<!-- provenance: schema=1 session=f67c3bb5-c93f-40f0-993c-118c4a2034f6 branch=fix/ux-scroll-spy-overlapping-refresh commit=19cc263 actor=amodal1 agent=anthropic/claude-opus-5 generated_at=2026-08-04 -->

# Agent handoff: after `fix/ux-scroll-spy-overlapping-refresh` (item 44 fixed AND closed; next: the deterministic CI-wait wrapper)

**Branch to create:** `feat/ci-wait-wrapper` off `main`
**Base branch:** `main`

> **READ THIS FIRST — the march is still paused, and your branch is still not sprint A1.**
> Item 44 is **closed on CI evidence** — you inherit no unfinished business from it. Your
> branch is owner-directive 1: the deterministic CI-wait wrapper. Do not start sprint A1
> (`fix/experience-soft-retire`) without checking in with the owner first.

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

**Read for this handoff specifically:** `RELEASE_ARC.md` §"v1.1.0 Final March (2026-08-04 —
owner-approved epic sequence)" for the governing plan, and agent memory
`project-ci-infrastructure-sprint-sequence` — the **later, owner-directed** sequencing that
supersedes the queue ordering in the previous handoff. Both agree item 44 came first;
the memory adds the dependabot layer behind it. `docs/dev/work/BOARD.md` is the live-status
source.

**Stream:** v1.1.0 Final March — enforcement/CI-infrastructure pass, ahead of epic A.
**Sequencing rule:** strictly sequential — one branch at a time.
**Blocked until this stream tags:** the public v1.1.0 cut (epic E / item 10).

- ~~`chore/v11-march-kickoff`~~ ✓ — march plan + board filing (PR #98)
- ~~`feat/consumer-enumeration-gate`~~ ✓ — charter C-10 + the guard (PR #99)
- ~~`fix/ux-scroll-spy-overlapping-refresh`~~ ✓ — item 44, this handoff's branch
- **`feat/ci-wait-wrapper`** ← next (owner directive 1)
- Then: dependabot hygiene (`groups:` config) → dependency upgrades (#63 ruff first,
  then #50, #84) → verify-don't-assume Bash guard → items 45, 46
- `fix/experience-soft-retire` ← sprint A1, only AFTER the above, and only after checking in
- `feat/corpus-polish`, then A2–A4, then epics B–E

**The march is still deliberately paused.** Do not touch epics B–E.

---

## What just landed on `main`

**Nothing yet — this branch is not merged as of writing.** Read this section as "what is on
the branch awaiting the PR channel." Three commits: `cea3e29`, `e688623`, `19cc263`.

**Item 44 — root cause proven and fixed. It is a TEST-HARNESS defect; `static/app.js` is
untouched and no production code changed on this branch.**

The scroll-spy timeline was cleared once `refreshCorpus-exit` appeared. But
`_SCROLL_SPY_NAMED_HOOKS_JS`'s own header has recorded since Chip 1a that `_restoreScrollY`
is a fire-and-forget `requestAnimationFrame` that `refreshCorpus` never awaits, so an
invocation is marked closed *"a full microtask-drain before the rAF actually fires."*
`refreshCorpus-exit` therefore could never signal that the invocation had stopped emitting
records — the Corpus tab click's own restore lands in the freshly-emptied timeline and is
counted as a third event. Fixed by gating the clear on that invocation's own
`_restoreScrollY-fired` too, in a shared `_settle_and_clear_spy_timeline()` helper.
`assert len(fired) == 2` is unchanged.

**⚠ Item 44's own filing named the wrong event, and the previous handoff inherited it.**
Both described the anomaly as "an `ordinal: 2` landing after `ordinal: 3`". That row is what
the test's final assertion *requires* — invocation A's fetch is deliberately held open, so A
must restore last (`assert last_fired["scheduledDuring"] == [id_a]`). The real intruder was
`ordinal 1 / scheduledDuring [1]`, from the tab-click invocation the test does not track:
the spy's `_rcCounter` is a closure variable the clear does not reset, so the tracked pair is
ids **2 and 3**. Corrected in item 44, `CHANGELOG.md`, and agent memory
`reference-ux-flake-ci-runner-not-local-load`. **Had it not been caught, the obvious next
move was to investigate `_restoreScrollY`'s supersede guard — which is working correctly.**

- **Evidence:** it does not reproduce locally at all — **20/20 pass**, against CI's measured
  ~67% per attempt (~6e-7 if the rates matched). So the rate lottery was not an available
  instrument and the ordering is forced by construction instead — the O-10/O-11 method from
  `ux-scroll-position-flake.md`. New probe
  `test_settle_gate_clears_the_timeline_without_leaking_a_pending_restore` holds only
  invocation 1's own rAFs (wall-clock), leaving Playwright's polling cadence untouched.
- **A/B** (revert the `_restoreScrollY-fired` clause in `_settle_and_clear_spy_timeline()`
  to reproduce the A-arm): gate on `-exit` only → **FAIL on the subject assertion**, controls
  green, leaks `ordinal 1 / scheduledDuring [1]`; gate on `-exit`+`-fired` → **PASS**.
- **The probe's control arm caught its own first version passing VACUOUSLY** — the hold never
  released, so nothing could leak, and that read identically to a clean result. This is the
  O-4 inert-instrument trap, hit again. Any test whose subject is "X did not happen" needs a
  control proving X had the opportunity to happen.
- **Measured incidentally, and load-bearing:** headless Chromium in this harness runs at
  **~11-13fps**, not ~60. A frame-count delay is not a portable unit here.
- **Local gate:** `python -m scripts.gate` **green, `GATE_EXIT=0`** — ruff, ruff format,
  mypy (348), `pytest -m "not ux"` 2230 passed/1 skipped, `pytest -m ux` **138 passed**
  (137 + the new probe) /1 xfailed/1 xpassed, `work_items check` passed. **Zero `RERUN`
  markers and zero `[ux] rerun-rate alarm` lines** in the whole log.

- **CI confirmed it, and item 44 is CLOSED.** PR #100, run `30968745766`, ux job
  `92188295433`. Verified in the **job log**, not the `gh pr checks` bucket — the bucket is
  exactly what misreported two PR #99 runs: **0 `RERUN` markers, 0 rerun-rate alarm lines**,
  and `test_scroll_spy_attributes_overlapping_refresh_corpus_calls` **PASSED on its first
  attempt**. That is the **first clean run in five** (#98: 3/3 attempts failed; #99 run 2:
  3/3; #99 run 3: 1/3; #99 run 4: 1/3; #100: 0/1).
  - **Scoped honestly:** one clean run is one sample, and at the pre-fix ~67% per-attempt
    rate a single clean attempt happens by chance about a third of the time. What makes the
    closure sound is not the sample — it is that the mechanism was *proven* by deterministic
    reproduction and A/B **before** the fix was written, with three rivals falsified. A second
    sample was taken deliberately from the closing commit's own pre-merge CI run.

**Operational note (cost the session ~15min):** the first `scripts.gate` run was **killed** at
56% of the ux tier by this environment's background-task management. Free RAM was 2.07GB and
no orphans of mine survived. I attributed it to memory pressure and surfaced a decision to the
owner on that basis — **the re-run then completed green and faster (4:08 vs 7:00 for the
non-ux half), which is evidence against that attribution.** Correlation was treated as cause;
the right move was to wait for the in-flight run. Recorded in
`reference-shared-machine-oom-kills-bg-runs`. **The tell that a run was killed rather than
failed is an absent exit-code line** — always append one after the command, outside any pipe.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

**Adaptation note (same as predecessors):** `docs/dev/work/BOARD.md`'s full still-open subset
is rendered below; `RELEASE_CHECKLIST.md`'s Carry-forward ledger is superseded.

**Open (1 / 10 ceiling):**
1. Item 45 — plan-approval marker survives a PR-channel merge.
   `hooks/cleanup-plan-on-merge.sh:21-29` fires only when the Bash command text contains all
   three of `git merge`, `--no-ff`, `Merge made by`; close-out uses `gh pr merge <n> --merge`,
   which contains none of them. **Confirmed again this session** — a stale
   `.approved-C--Dev-sartor` from 10:42 was present at session start and was not ridden.

*(Epic 36 and items 9/20 sit under the epics below rather than as standalone Open rows; see
BOARD.md for the authoritative rendering.)*

**Blocked (3 + the sequenced epics):**
3. Item 3 — [HUMAN] GitHub toggles (repo rename, PyPI Trusted Publisher, GHCR,
   `enforce_admins`) — owner-gated. Memory `project-ci-infrastructure-sprint-sequence`
   recommends splitting `enforce_admins` out of epic E and gating it on "item 44 fixed AND
   the CI-wait wrapper reports rerun-rate" — **your branch is half of that condition.**
4. Item 5 — grounding-score persistence gap.
5. Item 8 — compose-time rewrite dial, pending owner direction.
6. Epics 37–40 — B (render/ATS), C (diagnostics), D (docs IA), E (release).

**Deferred (7):** items 4, 7, 24, 25, 41, 42, 43 — see BOARD.md.

**Watching (6):**
7. Item 2 — wordmark sweep, opportunistic only.
8. Item 16 — `evals/runner.py --suite real` non-functional.
9. Item 18 — judge-score run-to-run variance, n=2.
10. Item 23 — PX-52 analyzer.py split.
11. Item 46 — `test_reader_never_observes_a_partial_file`'s CONTROL arm flaked on PR #99.
    **Do not "fix" it by weakening the control** — this session's own probe is a worked
    example of why the control is what makes the subject assertion mean anything.
12. **Item 47 — audit sibling scroll-spy tests for the same settle-gate hole (NEW, this
    session).** `_settle_and_clear_spy_timeline()` was extracted from exactly one test; any
    sibling that clears the timeline on an event preceding a still-pending record has the
    same hole. Filed `watching`, not `open` — no second instance observed.

Also standing, not a numbered item: the 12 genuinely wiki-relevant files with accumulated
drift since the last real ingest. Item 19 remains inside the release chain via item 10's
`depends_on`.

Open-only count is 2, well under the reduction-sprint threshold — down from 5, because this
session closed out item 44's investigation rather than adding to the pile.

---

## What this branch should build

**Owner directive 1 — the deterministic CI-wait wrapper.** *"the wrapping and check process
should be deterministic."* Stop agents burning wall-clock on hand-rolled watchers: two
30-minute `Monitor` watches on PR #99 emitted **zero** events while a required check was red,
and the silence read as health.

1. **Build on `gh pr checks <n> --watch --required --fail-fast`** — it already exists
   (gh 2.96.0). Do not write a poll loop.
2. **Shape it like `scripts/gate.py` did for "gate green"**: one script that is the single
   definition of "the PR is green", printing the failing job's `--log-failed` tail so there is
   no second round-trip, and **structurally unable to exit silent**.
3. **It MUST distinguish green-after-retries from green** (C-7 rule 3 applied to the wrapper).
   `gh pr checks` reports bucket `pass` for a fail-then-pass — that already cost accuracy on
   PR #99, twice. Grep the job log for `RERUN` / `needed a retry` and surface it.
   - **The repo already emits the signal and nobody reads it:** the ux tier prints
     `[ux] rerun-rate alarm: N test(s) needed a retry this run` into the job log on every
     affected run. **Route that existing alarm into the wrapper's output rather than building
     a second mechanism.**
4. Must distinguish required from advisory checks — this repo has both.
5. **Never pipe to the `jq` binary — it does not exist on this machine** (`gh --jq` works; gh
   embeds gojq). That gap is owner directive 2's motivating case.

Reuse: `scripts/gate.py` for the "single definition of green" shape and its `_STEPS`/exit-code
convention. Authorized by memory `project-deterministic-ci-wait-governance` and
`project-ci-infrastructure-sprint-sequence` step 2.

**Scope is bounded to the CI-wait wrapper.** Do not also take dependabot `groups:`, the
verify-don't-assume guard, item 45, or item 46 on this branch — one branch, one item.

---

## First move

**Owner, at launch:** approve the session plan when asked.

Agent: FIRST action is `python scripts/check_handoff_pointer.py "<the pointer line you were
given>"`; once it passes, consume this file
(`python scripts/verify_doc_template.py docs/dev/handoffs/fix-ux-scroll-spy-overlapping-refresh.md
docs/dev/AGENT_HANDOFF_TEMPLATE.md --event consumed --agent <agent>`).

**You inherit no unfinished business.** Item 44 is closed on CI evidence and the board is
regenerated. If the scroll-spy test ever flakes again, do not re-open item 44 blind — read
`docs/dev/diagnosis/ux-scroll-spy-overlapping-refresh.md` "Still open" first, which states
plainly that one mechanism was proven and fixed and that a second contributor was never
excluded. Item 47 is the most likely place to look.

Then create `feat/ci-wait-wrapper` off `main`, write a plan at `~/.claude/plans/<slug>.md`,
and show it to the user before touching any code. **Do not code first.**

**Do not trust a pre-existing plan-approval marker** (item 45). If
`~/.claude/plans/.approved-<project-key>` exists at session start it is stale — the PR-channel
merge does not wipe it — and it is NOT approval for your work. Earn a fresh one via
`EnterPlanMode` → write the plan → `ExitPlanMode`. This was verified again this session.

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
   the user the URL) → **wait for all required checks to go green** →
   `gh pr merge <n> --merge` (never `--squash` / `--rebase`) →
   `git checkout main && git pull --ff-only`. Use `--ff-only` so an unexpected
   divergence fails loudly instead of silently manufacturing a merge commit.
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
