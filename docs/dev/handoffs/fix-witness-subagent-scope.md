<!-- provenance: schema=1 session=0ea1b8bf-913f-48d6-a7f1-5e54cf8769b3 branch=fix/witness-subagent-scope commit=f006d5e actor=amodal1 agent=anthropic/claude-opus-5-5 generated_at=2026-09-22 -->

# Agent handoff: `fix/witness-subagent-scope`

**Branch to create:** `fix/plan-approval-retired-mid-branch` (item 110; owner-sequenced before the Epic C run).
**Base branch:** `main` (once this branch has merged)

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
Epics C/D/E finish as **long runs** under the original epic design, not as factory cards.

**Tonight's sequence (owner-approved this session, 2026-09-22).** The owner waived
one-branch-per-session for tonight, so this session lands three branches in order, then
hands off to a fresh Epic C invoker session:

- **`fix/witness-subagent-scope`** ← this branch (item 94)
- `fix/plan-approval-retired-mid-branch` (item 110). Owner chose "fix before tonight's run".
- `docs/epic-c-kickoff`: item 96, the Epic C design brief + C1a brief, the UX audit, and
  the item 93/95/97 records.
- then the Epic C long run (`epic/c-diagnostics`), in a fresh invoker session.

**Owner decisions recorded this session (AskUserQuestion selections, 2026-09-22):**
item 93 → (b) continuous window; item 95 → adopt the proposed amendment (consume the pause
with an invoker edit, re-invoke the sprint stage fresh, never `resumeFromRunId` for a
`hook_block`); UX audit in the kickoff branch; `.isidium/` + `.agents/` gitignored; item
110 fixed before tonight's run. The Epic C scope sentence is still owed: the owner ratifies
it verbatim on the kickoff branch.

---

## What just landed on `main`

PR #142 (`9cafbde`), item 109: `ci_wait`'s required set now comes from branch protection.
This branch's PR is that fix's second live use.

---

## What this branch built

**Item 94: closed.** C-7 order was kept:

- **`9e457a1`, the instrument.** A key-only PreToolUse payload trace, plus the dossier
  `docs/dev/diagnosis/witness-subagent-scope.md`. **Observed:** a subagent's `Edit` payload
  carries `agent_id` + `agent_type`, and the main agent's carries neither.
- **`591253f`, the fix.** `claude_check` skips the pause when `agent_id` is truthy. Blank
  or absent still pauses, and the instrument is removed. Repro
  `TestSubagentScoping::test_subagent_edit_does_not_consume_the_main_agents_pause` failed
  on `9e457a1` and passes after the fix.
  - **Live re-probe:** with the state armed, a subagent `Edit` was allowed and the main
    agent's next `Edit` paused.
  - Docs updated: `CLAUDE.md`, `docs/governance/enforcement.md`, runbook step 0a, the
    CHANGELOG, and an item 87 note. Wiki verified no-edit, logged in `docs/wiki/log.md`.
- **Also observed, not changed:** subagent hand-backs and task notifications re-arm the
  pause. It now lands only on the main agent's own next edit (one re-run). Seen live three
  times this session.

**Item 110 filed: open** (`f006d5e` holds the observations). This session's approved plan
was archived at 19:53 with **no** `plan-archived` ledger receipt, and the approval marker
vanished within seconds of this session's 19:58 compaction, while this branch was
unmerged. Next edit: `NO EDIT APPROVAL`. The owner re-approved and work continued. The
mechanism is **unproven**; the item keeps Observed and Inferred apart.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

The one authoritative home is `docs/dev/work/BOARD.md` (charter W-1.4). Still-open subset
after this branch (item 94 closed, item 110 opened): **11 open against a ceiling of 10**
(the board header's count is the authority):

- **50**: C-7 and C-10 are enforced by Claude Code hooks only (`user`)
- **96**: sprint briefs' First-move blocks omit the model arg; the script default silently wins (`agent`). Next: `docs/epic-c-kickoff`
- **98**: wiki freshness measures checkpoint-staleness, not page-staleness (`agent`)
- **99**: install.md documents two unpublished distribution paths (`agent`). Kept open until a tag ships
- **105**: corpus import produced no education entries (`agent`)
- **106**: Compose bullet-text edits don't reach a frozen application (`agent`)
- **107**: first run offers no account-naming step (`agent`)
- **110**: plan approval retired mid-branch (`agent`). Next: `fix/plan-approval-retired-mid-branch`

Plus open epics (the board renders them). Blocked items 93 and 95 are owner-decided this
session. They get recorded on `docs/epic-c-kickoff`.

**Still carried (not filed as items, unchanged):**

- `preflight.py` is deterministic but not on AGENTS.md's C-6 list. Owner-gated, unanswered.
- Two container claims in `docs/install.md` remain unverified (blocked by item 99).
- `.last_ingest_sha` is still stale (item 98).
- Not repo work: the borrowed macOS machine's API key rotation is still owed.
- The gate from PowerShell hits WSL bash: a fail-closed check in `scripts/gate.py` was
  proposed last session and is still not filed.

**New this session:** the witness re-arm on non-user events (documented, accepted); item 110.

---

## Recurrences observed this session → guardrail authored

**1. The witness pause re-armed by non-user events: recurrence.** This is item 94's
`prompt_seq` observation, seen three more times live. **Guardrail authored:** the
subagent-scope fix on this branch. Re-arms now cost the main agent one re-run and can no
longer kill a pipeline agent.

**2. The plan-approval marker retired while its branch was live.** This may belong to item
56's class (retirement misbehaving). **Guardrail:** the owner sequenced a fix branch
(`fix/plan-approval-retired-mid-branch`) before tonight's run. Until it merges, nothing
fails closed on this, which I state here rather than leave implied (C-11).

---

## What this branch should build

Nothing further; item 94 is closed. Next: `fix/plan-approval-retired-mid-branch` (item
110). The first commit is the reproduction in a throwaway worktree (memory
`reference-hook-manual-testing`), never the fix.

---

## First move

This session continues directly (owner waiver). A fresh session picking this up instead:
verify the pointer, consume this file, create `fix/plan-approval-retired-mid-branch` off
`main`, and write a plan before touching code.

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
