<!-- provenance: schema=1 session=0ea1b8bf-913f-48d6-a7f1-5e54cf8769b3 branch=fix/plan-approval-retired-mid-branch commit=889866c actor=amodal1 agent=anthropic/claude-opus-5-5 generated_at=2026-09-22 -->

# Agent handoff: `fix/plan-approval-retired-mid-branch`

**Branch to create:** `docs/epic-c-kickoff` (items 96 + 93/95/97 records + Epic C design; owner-sequenced).
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
Epics C/D/E finish as **long runs** under the original epic design.

**Tonight's sequence (owner-approved 2026-09-22; one-branch-per-session waived for
tonight):**

- ~~`fix/witness-subagent-scope`~~ ✓ (item 94, PR #143, `f755920`)
- **`fix/plan-approval-retired-mid-branch`** ← this branch (item 110)
- next: `docs/epic-c-kickoff`: item 96, the Epic C design brief + C1a brief, the UX audit,
  the item 93/95/97 records, and `.gitignore` for `.isidium/` + `.agents/`.
- then the Epic C long run (`epic/c-diagnostics`), in a fresh invoker session.

**Owner decisions already recorded (2026-09-22 AskUserQuestion selections; they land in
the repo on the kickoff branch):**
- item 93 → (b) continuous window;
- item 95 → adopt the proposed amendment;
- the UX audit happens in the kickoff branch;
- `.isidium/` + `.agents/` get gitignored;
- item 110 gets fixed before the run.

The Epic C scope sentence is still owed: the owner ratifies it verbatim.

---

## What just landed on `main`

PR #143 (`f755920`), item 94: the interrogative-witness pause no longer lands on subagents.
`ci_wait` announced 6 protected contexts and returned GREEN.

---

## What this branch built

**Item 110: closed.** C-7 order was kept. `a180ad2` is the reproduction:
`TestStaleStampAndKilledRetire`, both tests `xfail(strict=True)` on HEAD. `8627411` is the
fix. Evidence: `docs/dev/diagnosis/plan-approval-retired-mid-branch.md`.

- **Cause 1 (measured).** `check-plan-approved.sh`'s retire path took 5.66–14.72 s (4/4
  runs) against its 5 s hook timeout. A timed-out hook doesn't block. It was killed after
  the plan `mv` and before the pointer `rm`, which left a live marker over a moved plan
  (observed live 4 times this session).
  - **Fix:** `retire_approved_plan` reads the pointers with builtins and removes them
    **first**, so any kill fails closed. The timeout goes from 5 to 20.
- **Cause 2 (test-proven).** `mark-plan-approved.sh` never cleared `.approved-branch-*`, so
  a merged branch's stamp retired the next fresh approval. That was this session's first
  instance.
  - **Fix:** approval removes the stamp.
- **Stated limit.** Speed is not fixed. Post-fix, the retire path measured 8.53–21.45 s
  under load, so one edit can slip through a killed hook, but the approval never survives.
  **Item 111** is filed for the fork cost, which also covers the ~2 s every Edit/Write pays.
- **Live check still owed.** The first edit on the kickoff branch should draw a clean
  `PLAN RETIRED`. The fresh approval after it should survive its first edit. Record both
  in the kickoff handoff.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

The one authoritative home is `docs/dev/work/BOARD.md` (charter W-1.4). Still open after
this branch (110 closed, 111 opened): **11 against a ceiling of 10** (the board header is
the authority):

- **50**: C-7 and C-10 are enforced by Claude Code hooks only (`user`)
- **96**: sprint briefs' First-move blocks omit the model arg (`agent`). Next branch
- **98**: wiki freshness measures checkpoint-staleness (`agent`)
- **99**: install.md documents unpublished distribution paths (`agent`). Kept open until a tag ships
- **105**: corpus import produced no education entries (`agent`)
- **106**: Compose bullet-text edits don't reach a frozen application (`agent`)
- **107**: no first-run account-naming step (`agent`)
- **111**: plan-approval hook fork cost, ~2 s per edit and 8–21 s per retire (`agent`). New

Plus open epics (the board renders them). Items 93 and 95 are owner-decided and get
recorded on the next branch.

**Still carried (not filed, unchanged):** the `preflight.py` C-6 question (owner); two
unverified container claims (blocked by item 99); stale `.last_ingest_sha` (item 98); the
macOS API key rotation (not repo work); the gate-from-PowerShell fail-closed check
(proposed, not filed).

---

## Recurrences observed this session → guardrail authored

**1. The plan-approval approval retired without a clean record: item 56's class,
recurring.** **Guardrail authored:** kill-safe ordering plus the stale-stamp clear,
proven by two tests that failed on HEAD.

**2. An instrument polluted the durable record (first instance).** Timing
`check-plan-approved.sh` directly with `CLAUDE_PROJECT_DIR` set to the real repo wrote
three fabricated `plan-archived` receipts (`plan: "p.md"`) into this session's ledger
shard. They were committed in `8627411`, found by inspecting the ledger diff, and removed
in the next commit. It is a first instance, so no mechanism is owed. Lesson: point
instrument runs of hooks at a throwaway repo, never the live one.

**3. The witness pause re-armed by background-task notifications.** Seen again. This is
expected behavior after item 94 (one re-run on the main agent).

---

## What this branch should build

Nothing further; item 110 is closed. Next: `docs/epic-c-kickoff` (see the arc section).
It needs its own ExitPlanMode approval: the hook retires approval per branch, and that
is correct behavior.

---

## First move

This session continues directly (owner waiver). A fresh session instead: verify the
pointer, consume this file, create `docs/epic-c-kickoff` off `main`, and write a plan.

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
