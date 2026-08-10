<!-- provenance: schema=1 session=c764076e-42dc-466a-ba56-55bc3604f59e branch=fix/plan-approval-branch-switch-gap commit=1700cf0 actor=amodal1 agent=anthropic/claude-sonnet-5 generated_at=2026-08-07 -->

# Agent handoff: after `fix/plan-approval-branch-switch-gap` (item 45 reopened-and-reclosed)

**Branch to create:** none — owner decision, not this handoff's to make. See "First move" below.
**Base branch:** `main` (this branch's own base; `main` was at `efa5994` — PR #111 — when this branch started).

**This branch is an unplanned interstitial fix**, not a scheduled march sprint: found
while scoping an Epic-A multi-branch orchestration design (a chat-only conversation, not
yet a durable doc — see "First move" below for what that means for continuity), not
while chasing item 45. Closed the same day item 45 itself closed.

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

**Stream:** v1.1.0 Final March — CI-infrastructure pass complete, ahead of epic A.
**Sequencing rule:** strictly sequential — one branch at a time.
**Blocked until this stream tags:** the public v1.1.0 cut (epic E / item 10).

- ~~`fix/plan-approval-marker-pr-merge`~~ ✓ — item 45 closed (D3(c), late-bound stamp,
  archive-not-delete)
- **`fix/plan-approval-branch-switch-gap`** ← this branch — item 45 reopened same day,
  a genuine gap found in D3(c)'s own reconciliation ordering, refixed, reclosed
- **Next: resume the Epic-A wave-orchestration design conversation, OR sprint A1
  directly, OR an owner-directed alternative — owner decision, not this handoff's to
  make.** See "First move" below.

**The march is still deliberately paused before epics B–E.**

**Item 10's release chain is still gated on epic 19** — untouched this session.

---

## What just landed on `main`

`main` was at `efa5994` (PR #111, item 45's original closure) when this branch started.
This branch's own tip is `1700cf0` (one commit — fix + test + dossier + item-45 update +
CHANGELOG + BOARD.md + this session's own ledger shard, all folded together; this
handoff file is a separate, following commit per `docs/dev/prov/SPEC.md` §1's "usually
HEAD at generation time, before this doc's own commit exists").

**What the commit does:**

1. **Found (not chased) while scoping an unrelated Epic-A orchestration design:** the
   owner asked to reuse a prior chain-execution method (stacked branches, per-sprint
   adversarial review, Opus-orchestrated) for Epic A. Verifying whether one
   `ExitPlanMode` approval legitimately covers a stacked branch chain led to reading
   `hooks/check-plan-approved.sh`'s D3(c) reconciliation closely, then reproducing it
   directly rather than trusting the read.
2. **Root cause, evidenced twice in isolation plus once for real:** the reconciliation
   ran its "late-bind the stamp to the current branch" block *before* its "reconcile
   whatever was previously stamped" block, so a transition straight from an
   already-merged branch to a brand-new one — the *only* shape `require-feature-branch`
   actually allows, since it never permits an edit while `HEAD == main` — silently
   overwrote the stamp before the old branch was ever checked. Two throwaway repros
   confirmed it; it then fired for real on this session's own actual marker while
   writing the diagnosis dossier (this session had never called `ExitPlanMode`, yet a
   brand-new branch's first edit was allowed). Full evidence:
   `docs/dev/diagnosis/plan-approval-branch-switch-gap.md`.
3. **This is the same original symptom item 45 was filed against, not a new defect
   class** — item 45's own committed regression suite only ever exercised
   same-branch-continuation (`test_pr_channel_merge_blocks_the_next_edit`) and
   `HEAD == main` (`test_deleted_branch_blocks_the_next_edit`) shapes, never a branch
   switch. Item 45 was reopened, refixed, and reclosed same day with an updated
   `resolution`, a `guardrail` field, and the new test added to `verified_by`.
4. **Fixed** by reordering the two blocks in `hooks/check-plan-approved.sh` so the
   previously-stamped branch is reconciled — archived + `exit 2` if warranted — before
   it can be overwritten. **A candidate extra safeguard was tried and dropped**: forcing
   a reconciliation pass on every branch switch, independent of the existing mtime
   pre-filter. Empirically unnecessary (the existing `refs/heads/main -nt $STAMP`
   condition already catches every real case, since a merge always advances `main`'s
   ref-file mtime) — confirmed by running the full suite without it rather than kept
   "to be safe," per the standing efficiency-is-a-first-class-concern instruction.
5. **New regression test** `test_new_branch_after_merge_requires_fresh_approval`:
   confirmed RED against the just-reopened code (`returncode == 0` where `2` was
   required) before the fix, GREEN after.

**Full gate at this branch's tip, no reruns anywhere:**
- `python -m ruff check .` → all checks passed
- `python -m ruff format --check .` → 342 files already formatted
- `python -m mypy .` → Success: no issues found in 357 source files
- `python -m pytest -m "not ux" -n auto` → 2376 passed, 1 skipped, 0 failed, 0 reruns
- `python -m pytest -m ux` → 138 passed, 2377 deselected, 2 xfailed, 0 failed, 0 reruns
- `python -m scripts.work_items check` → OK (55 files)
- `python -m scripts.gate` (the wrapper, run as one command) → all steps passed
- `tests/test_plan_approval_scoping.py` specifically: 26 passed (up from 18), 0 reruns

**Wiki-relevance check (pre-close sweep item 0):** none of this branch's 7 changed files
(`hooks/check-plan-approved.sh`, `tests/test_plan_approval_scoping.py`,
`docs/dev/diagnosis/plan-approval-branch-switch-gap.md`,
`docs/dev/work/items/0045-*.md`, `docs/dev/work/BOARD.md`, `CHANGELOG.md`,
`docs/dev/ledger/*.jsonl`) classify as wiki-relevant per `scripts/wiki_relevance.py`
(checked directly, not assumed).

**No dev server or long-lived background process from this session's own sartor work
left running** — `tasklist` showed one `python.exe` mid-session (the gate task itself,
then-running); nothing orphaned at close. Not independently re-checked at the exact
moment of writing this handoff — re-verify before closing the window if this session
continues past this point.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

`docs/dev/work/BOARD.md` is the authoritative live-item source (regenerate with
`python -m scripts.work_items board --write`; not hand-edited). Reproduced verbatim
from the board at this branch's tip, not re-derived.

**Open (1, unchanged — item 45 reopened AND reclosed this session, net zero):**
1. **50** — C-7 and C-10 are enforced by Claude Code hooks only — the clauses do not
   travel to other agents or an extracted governance package. Guards are not routed
   by `git_hook.py`, so only Claude Code enforces them; prose binds other agents.

**Blocked (3):** item 3 ([HUMAN] GitHub toggles), item 5 (grounding-score persistence
gap), item 8 (Compose-time rewrite latitude dial).

**Deferred (7):** items 4, 7, 24, 25, 41, 42, 43 — all owner-gated or explicitly
post-1.1.0-scheduled; see `BOARD.md` for each.

**Watching (13):** items 2, 16, 18, 23, 46, 47, 48, 49, 51, 52, 53, 54, 55; see
`BOARD.md` for each. Item 52 (the gate-window class study) is directly relevant to the
Epic-A wave design under discussion — see "First move" below.

**Epics (6):** 19 (UX-suite flakiness umbrella, children 27–31), 36 (Final March epic A,
children 20, 34 — open), 37/38/39/40 (Final March epics B/C/D/E — blocked, sequenced
after A per the march plan). Epic 39 carries item 9 (stale screenshots); epic 40 carries
item 10 (the v1.1.0 tag itself, `depends on: 3, 6, 7, 9, 19`).

**Closed (20, unchanged — item 45 reopened+reclosed nets to no change in count):** see
`BOARD.md` for the full list.

Open-only count stays **1**, well under the reduction-sprint threshold.

---

## Recurrences observed this session → guardrail authored

**One recognized recurrence this session.**

1. **Item 45's own fix shipped with an uncovered transition, and that transition turned
   out to be the dominant real-world shape (not an edge case).** Recognized as the SAME
   symptom class item 45 was filed against — not a new defect — the moment the throwaway
   repro showed a brand-new branch inheriting a stale approval with no `ExitPlanMode`.
   **Mechanism authored:** `tests/test_plan_approval_scoping.py::TestBranchMergeReconciliation::
   test_new_branch_after_merge_requires_fresh_approval` pins the exact transition
   (branch merges, then a DIFFERENT brand-new branch is checked out and edited) as a
   committed, falsifiable test — any future reordering that reintroduces
   stamp-overwrite-before-reconcile goes red rather than shipping plausible-but-wrong
   again. Named explicitly in item 45's own `guardrail` field, not left as a note.

**Nothing else recurred this session** — the reordering fix itself was a first-of-its-kind
mechanism change (no prior instance of "stamp-overwrite-before-reconcile" to recognize
as a class); the dropped "force reconciliation on every switch" candidate was an idea
tried and discarded via empirical test, not a recurrence.

---

## What this branch should build

**Nothing further — this branch's scope is the reconciliation-ordering fix, and it is
done.**

Do not expand beyond this fix. The Epic-A wave-orchestration design (see "First move")
is explicitly the next session's own scoped work, not a continuation of this one.

---

## First move

**There is no single prescribed first move, and — unusually — the most likely
continuation exists only in this session's own chat history, not in a durable doc yet.**
Read this section carefully before assuming either path:

- **If this is the SAME session that authored this branch:** the Epic-A
  wave-orchestration design conversation (Opus orchestrating, stacked-branch method,
  per-sprint Sonnet adversarial review folding in item 52's structural re-check,
  Opus `xhigh`-effort final epic review, right-sized models matching
  `RELEASE_ARC.md`'s existing A1–A4 table, governance write-up deferred to the end as
  an optional-method addition if the run succeeds) is still open and unresolved —
  resume it directly; nothing here supersedes it.
- **If a DIFFERENT/NEW session inherits this handoff pointer:** that design
  conversation is **not** captured in any durable doc as of this branch's tip — it
  lives only in the authoring session's own chat transcript. Per charter C-12
  ("declare the gap, never fill it"), **do not reconstruct or guess at its content.**
  Tell the user plainly that the wave-design conversation needs to be restated, and
  ask whether to proceed with sprint A1 directly instead (per `RELEASE_ARC.md`'s own
  default cadence: "the next session starts from the epic branch with the owner's
  plan-approval click," model prescription **Opus**) or resume the orchestration
  design from scratch.
- Whichever path: write a plan at `~/.claude/plans/<slug>.md` and show it to the user
  before touching any code. **Do not code first.**

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
