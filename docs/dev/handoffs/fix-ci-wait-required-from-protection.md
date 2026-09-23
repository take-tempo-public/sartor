<!-- provenance: schema=1 session=ec0ddb33-cd75-400e-914a-3bedae27dbb7 branch=fix/ci-wait-required-from-protection commit=bd3409c actor=amodal1 agent=anthropic/claude-opus-5-5 generated_at=2026-09-22 -->

# Agent handoff: `fix/ci-wait-required-from-protection`

**Branch to create:** none directed by this session. The open backlog is at
`docs/dev/work/BOARD.md`; see "What this branch should build" for this
session's recommendation.
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

**Stream:** v1.1.0 final march. Epic A and Epic B are both merged.
**Owner direction, 2026-09-22 (chat, recorded by the previous handoff):** Epics C/D/E
finish as **long runs** under the original epic design (`RELEASE_ARC.md` §"v1.1.0 Final
March" cadence + the chain/N=1 epic construction), **not** as factory cards. Item 97's
factory-card framing is still unreconciled. That reconciliation is owed.
**Sequencing rule:** strictly sequential, one branch at a time.

This branch is **not** part of the arc sequence. It is a single-item defect fix (item
109), chosen by the owner at session start over item 96, the Epic C prerequisites and
item 106. The reason: `ci_wait` is the merge gate every later branch lands through, so a
false GREEN from it undermines everything downstream.

- ~~`feat/install-onboarding-preflight`~~ ✓ (items 99-104, PR #135)
- **`fix/ci-wait-required-from-protection`** ← this branch (item 109)
- next ← the user's call; see "What this branch should build"

---

## What just landed on `main`

Commit `b48dc70` (PR #135), items 100-104 closed, item 99's docs half. **Gate status on
that merge: every check SUCCESS.** Verified this session with
`gh pr view 135 --json statusCheckRollup` (smoke eval SKIPPED, label-gated). That
settles the previous handoff's "full local gate NOT green on the final tip" caveat.

---

## What this branch built

**Item 109: closed.** Open count 12 → 11 (ceiling 10, **still over by one**).

- **Root cause (observed, not inferred):** `scripts/ci_wait.py` took "required" from
  `gh pr checks --required`, which only knows check runs **already registered** on the PR.
  On PR #135 the CI workflow's jobs registered minutes after `gh pr update-branch`, the
  watch returned once the four `Analyze` jobs passed, and the verdict was GREEN with 4 of
  6 protected contexts pending.
- **C-7 order was kept.** `df61126` is the reproduction: PR #135's payload shape through
  the real `_run()`, committed as `xfail(strict=True)` after it returned GREEN on HEAD.
  `4838afc` is the fix, which removes the marker.
- **The fix:**
  - "Required" = the base branch's protection contexts
    (`gh api …/protection/required_status_checks`), read once per run.
  - Pure `reconcile_required` adds a synthetic `pending` row per unregistered protected
    context.
  - `_run` re-enters `gh --watch` while anything required is unsettled, bounded by the one
    deadline with a 30 s pause floor.
  - An unreadable rule exits 2, never green. Exit codes unchanged.
- **Live check, read-only:** `python -m scripts.ci_wait 135` printed
  `6 required context(s) from branch protection` and `GREEN (exit 0)`.
- **Side fix:** the pre-watch line is `flush=True`. Piped output used to print the
  wrapper's preview *after* `gh`'s watch output.
- **Dossier:** `docs/dev/diagnosis/ci-wait-required-from-protection.md`. It also records
  a deliberate deviation from the plan: AGENTS.md step 4 and the TEMPLATE's verbatim block
  were **not** edited. Neither sentence is false after the fix, and the definition's
  canonical home is `ci_wait.py`'s docstring.
- **Wiki:** `ci_wait.py` is not wiki-relevant per `is_wiki_relevant()`, but the
  `code-module-map.md` row claimed "no poll loop of its own". That row was corrected
  directly and logged in `docs/wiki/log.md`.

**Known limit, stated, not verified:** the protection endpoint is documented as needing
repository administration access. Only the maintainer's token was tested. A non-admin
caller would get exit 2 on every run: fail-closed, but it means the wrapper certifies green
only for a maintainer.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

The one authoritative home is `docs/dev/work/BOARD.md` (charter W-1.4). Full still-open
subset: **11 open against a ceiling of 10, still over by one** (the board header's count
is the authority):

- **50**: C-7 and C-10 are enforced by Claude Code hooks only; the clauses do not travel to other agents (`user`)
- **94**: the item-87 interrogative-witness pause kills N=1 pipeline runs (`user`)
- **96**: sprint briefs prescribe an implementer model in prose while their First-move block omits the arg (`agent`)
- **98**: wiki freshness measures checkpoint-staleness, not page-staleness (`agent`)
- **99**: install.md documents two distribution paths that have never been published (`agent`). Docs half landed; kept open by owner decision until a tag ships and both publish workflows are green
- **105**: corpus import produced bullets and skills but no education entries (`agent`)
- **106**: Compose bullet-text edits don't reach an already-frozen application's preview, generate, or download (`agent`)
- **107**: first run offers no account-naming step; the account is named after the email address (`agent`)

Plus three open **epics** (19, 36, and the third the board renders). `BOARD.md` is the
authoritative render, not this list.

**Still carried from the previous handoff (not filed as items, unchanged):**

- `preflight.py` is deterministic but not on AGENTS.md's enumerated C-6 list. This is an
  owner-gated governance question, still unanswered.
- Two container claims in `docs/install.md` remain unverified: rootless-Podman bind-mount
  writability for uid 10001, and `/app/db` shadowing the baked recall index. Blocked by
  item 99.
- `.last_ingest_sha` is still stale and was not advanced here (item 98).
- Not repo work: the borrowed macOS machine's API key rotation is still owed on handback.

**New this session:** none beyond item 109's own known limit (above).

---

## Recurrences observed this session → guardrail authored

**1. Heredoc-delivered content mangled: 5th instance.** A Bash heredoc carrying a
multi-edit Python script failed to parse (`unexpected EOF while looking for matching
'`), and nothing ran. This is a recognized recurrence of memory
`reference-heredoc-escaping-and-first-match-anchors` (Trap 1b). **The guardrail was
applied, not authored:** the memory's recorded workaround (write the script with `Write`,
then run it) worked first time. **No repo-level fail-closed gate is possible.** This is
harness command parsing, with no project surface to gate. That was stated in-session
(C-11).

**2. PowerShell here-string swallowed as a pathspec.** `git commit -q -F - @'…'@`
passed the message as a positional pathspec, and the commit failed loudly with nothing
committed. This is a first instance, so no mechanism is owed. The form that worked:
assign the here-string to `$msg`, then `git commit -m $msg`.

**3. The fix bypassed its own hook's trigger.** The main `ci_wait.py` change was
applied by a Python script, not `Edit`/`Write`, so `require-evidence-before-fix` never
evaluated it. The dossier's `## Observed` was already filled, and a later `Edit` to the
same file passed the hook. **This is a known limit of the hook (it keys on the Edit/Write
tool), not a new mechanism**, and it was surfaced in-session. Whether the hook should
also gate script-applied writes is an open question, not filed.

**4. Gate launched from PowerShell hit WSL bash.** The first full gate run was started
from the PowerShell tool. There, `bash` resolves to
`C:\Users\iam\AppData\Local\Microsoft\WindowsApps\bash.exe`, the WSL launcher, which strips
the backslashes out of Windows paths. About 45 hook tests in `test_enforcement_core.py` and
`test_plan_approval_scoping.py` failed with
`/bin/bash: C:UsersiamAppDataLocalTemp…block-secrets.sh: No such file or directory`. The same
test passed under Git Bash, and the gate was re-run from Git Bash. This is a first
instance, so a new memory (`reference-gate-from-powershell-hits-wsl-bash`) records it.
**A fail-closed check is possible and was not built:** `scripts/gate.py` could refuse
when `shutil.which("bash")` sits under `WindowsApps`. That was proposed to the owner, not
filed.

---

## What this branch should build

Nothing further. Item 109 is closed.

Recommendations for the next session, in priority order (carried from the previous
handoff; item 109 is removed from them):

0. **Epic C prerequisites** (owner direction 2026-09-22: C/D/E run as long runs):
   - **93** (owner decision): per-sprint fresh sessions vs a continuous window with the
     step-9 tripwire.
   - **95** (owner): restate the `resumeFromRunId` pre-authorization.
   - **94**: the witness pause kills pipeline runs.
   - **96**: see 1.

   Reconcile item 97's factory-card framing at the same time.
1. **The backlog is 11 vs 10.** Item 96 is the cheapest honest reduction.
2. **Items 105, 106, 107** each need an instrument before a fix. The first commit on
   that branch is the instrument.
3. **The C-6 / `preflight.py` question** for the owner.
4. **Item 98**: needs the coverage-ledger redesign, not another scoped pass.

**This PR is the first live use of the fixed `ci_wait`.** If its first announce line did
not list six protected contexts, treat that as a regression of this fix.

Scope is bounded to what is filed in `docs/dev/work/items/`. Do not expand beyond it,
and do not start an item without the user naming it.

---

## First move

Create the branch the user names, off `main`, write a plan at
`~/.claude/plans/<slug>.md`, and show it to the user before touching any code.
**Do not code first.**

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
