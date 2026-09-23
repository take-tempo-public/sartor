<!-- provenance: schema=1 session=0ea1b8bf-913f-48d6-a7f1-5e54cf8769b3 branch=docs/epic-c-kickoff commit=1e2500c actor=amodal1 agent=anthropic/claude-opus-5-5 generated_at=2026-09-22 -->

# Agent handoff: `docs/epic-c-kickoff`

**Branch to create:** none. The next session is the **Epic C invoker**: it works on `epic/c-diagnostics` (created and pushed at this branch's close) and cuts `fix/dashboard-run-lock-gaps` from its tip per runbook step 0.
**Base branch:** `epic/c-diagnostics` (= `main` after this branch merges)

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

**Stream:** v1.1.0 final march. Epics A and B are merged. Owner direction 2026-09-22:
Epics C/D/E finish as **long runs** under the original epic design, not as factory cards
(item 97's update).

**Epic C is unblocked.** This session (`0ea1b8bf`, 2026-09-22/23) landed all three
prerequisite branches in sequence. The owner waived one-branch-per-session for the night.

- ~~`fix/witness-subagent-scope`~~ ✓ (item 94, PR #143, `f755920`)
- ~~`fix/plan-approval-retired-mid-branch`~~ ✓ (item 110, PR #144, `a078ca1`)
- ~~**`docs/epic-c-kickoff`**~~ ← this branch (items 93, 95, 96 + Epic C design)
- **next: the Epic C long run on `epic/c-diagnostics`**, in a fresh invoker session.
  `epic/c-diagnostics` is created off `main` and pushed as this branch's last act.

---

## What just landed on `main`

PR #144 (`a078ca1`), item 110: plan-approval retirement is kill-safe, and a fresh approval
clears the stale stamp. **Live check passed:** the first edit on this branch drew a clean
`PLAN RETIRED` with manifest and ledger receipt, and the fresh approval that followed held
for the whole branch.

---

## What this branch built

- **Item 96 closed.** `n1-baseline.mjs` has no `implementerModel` default. A sprint stage
  without it is rejected by name, and the guard sits after the position guards so their
  diagnostics are unchanged. The new test arm failed on `a078ca1`.
  `EPIC_SPRINT_BRIEF_TEMPLATE.md`'s First move now carries a copy-paste invocation with
  the model, and the runbook's Roles row and Args reference are updated.
- **Runbook step 9 corrected (found this session, not filed as an item).** The bullet said
  "ff-merge … **then prune the sprint branch**". That contradicts the run-6 correction
  further down, and with item 110's fix the retirement it triggers now completes, so the
  next sprint's first subagent edit would hit `PLAN RETIRED` → `hook_block` → stop.
  **Sprint branches are now kept until the epic PR merges.** Both behaviors are pinned by
  `test_epic_sprint_boundary_late_binds_when_sprint_branch_is_kept` and
  `…_retires_if_sprint_branch_is_pruned`.
- **`docs/dev/handoffs/epic-c-design-brief.md`**: the authorization record.
  - Owner decisions 2026-09-22: continuous window (item 93, closed); the amended witness
    recovery (item 95, closed; its text lives in the runbook §Escalation).
  - **The owner-ratified scope sentence**: its single home; cite it, never restate it.
  - The sprint table with explicit `implementerModel`: C1a `sonnet`, C1b `sonnet`,
    C2 `sonnet`, C3 `opus`.
  - The no-prune topology, cadence (wiki backstop at drift 60), and acceptance criteria.
- **UX audit** at `docs/dev/reviews/epic-c-console-ux-audit.md` (subagent, verified at
  `a078ca1`).
  - 22 in-scope findings are folded into the sprint rows. I spot-checked 25 of their
    cites at HEAD, and all matched.
  - UX-22 (the Since filter raises TypeError) was **reproduced independently** and is
    item 112.
  - The other 19 out-of-scope findings are item 113 (deferred, for owner triage).
- **`docs/dev/handoffs/epic-c-c1a-brief.md`**: run 1's brief, including the exact
  invocation.
- **Records:** item 97 (the long-run direction; stays blocked), item 110 (live check),
  item 84 (supersession of the old pre-authorization), RELEASE_ARC §Epic C
  (execution-mode pointer), CHANGELOG, `.gitignore` (`.isidium/`, `.agents/`), and the
  wiki log (verified no-edit).

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

The one authoritative home is `docs/dev/work/BOARD.md` (charter W-1.4). Still open:
**11 against a ceiling of 10, still over by one** (the board header is the authority):

- **50**: C-7 and C-10 are enforced by Claude Code hooks only (`user`)
- **98**: wiki freshness measures checkpoint-staleness (`agent`). Drift is **39 of 75**
- **99**: install.md documents unpublished distribution paths (`agent`). Kept open until a tag ships
- **105**: corpus import produced no education entries (`agent`)
- **106**: Compose bullet-text edits don't reach a frozen application (`agent`)
- **107**: no first-run account-naming step (`agent`)
- **111**: plan-approval hook fork cost, ~2 s per edit and 8–21 s per retire (`agent`)
- **112**: the console's Since filter raises TypeError on any date (`agent`). **New**, reproduced

Plus open epics (the board renders them, including 38 = Epic C). Deferred **113**
(19 console UX findings) awaits owner triage.

**Still carried (not filed, unchanged):** the `preflight.py` C-6 question (owner); two
unverified container claims (blocked by item 99); the macOS API key rotation (not repo
work); the gate-from-PowerShell fail-closed check (proposed, not filed).

---

## Recurrences observed this session → guardrail authored

1. **The witness pause re-armed by non-user events** (hand-backs, task notifications),
   seen many times. **Guardrail:** item 94's fix, merged. It now costs the main agent one
   re-run and never touches a subagent. The UX-audit subagent's `Write` this session was
   not refused by any hook, which is consistent with the fix. Whether the pause was armed
   at that moment was not checked, so it is not counted as verification.
2. **Plan approval lost mid-work** (item 56's class): **guardrail authored**, item 110.
3. **A runbook contradicting its own later correction** (step 9 "then prune" vs run 6's
   "prune after"): **guardrail authored**, two tests pin the behavior the runbook now
   states. The runbook text itself has no fail-closed check; stated here (C-11).
4. **An instrument polluted the live ledger** (first instance, branch 2): fixed in
   `889866c`. No mechanism owed yet.

---

## What this branch should build

Nothing further. **Next: the Epic C long run.**

---

## First move

**Model for the invoking session: the owner's choice, stated at launch.** The record
says epics run on Opus/Sonnet without Fable, and the invoker is the owner's call. Opus is
the natural fit.

1. Verify this pointer, then `--event consumed` on this file (C-9).
2. Read, **in full, and do not delegate the reading**: `docs/dev/handoffs/epic-c-design-brief.md`
   (the authorization record, and the scope sentence verbatim from its single home),
   `docs/dev/handoffs/epic-c-c1a-brief.md`, `docs/dev/n1-baseline-pipeline.md`, and
   `docs/dev/AGENT_FAILURE_PATTERNS.md` §5f. That is the invoker's kickoff reading (runbook
   step 0a); the generic "Documents to read" list below binds ordinary branch sessions.
3. Runbook **step 0 + 0a**:
   - preconditions (a live plan-approval marker, which means one owner
     ExitPlanMode for the run; `epic/c-diagnostics` checked out; the sprint branch cut
     from its tip);
   - the structural gate
     `python -m pytest tests/test_n1_pipeline.py tests/test_gitattributes_coverage.py -q`;
   - the live dispatch probe `n1-agent-probe.mjs` → **`ok_to_run` or STOP**;
   - scope reconciliation;
   - **one** preflight batch to the owner (run opt-in; whether any out-of-scope finding,
     such as UX-24 or item 112, joins a sprint);
   - deliberate witness-pause consumption.
4. Invoke run 1 **exactly** as `epic-c-c1a-brief.md` §"First move" shows (with
   `implementerModel: 'sonnet'`), then follow step 9 across the four sprints.
   **Do not prune sprint branches until the epic PR merges.**

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
