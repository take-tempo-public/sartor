<!-- provenance: schema=1 session=b7fe246e-c3d0-49bd-98bf-939560ebb497 branch=feat/enforcement-first-governance commit=77d837c actor=amodal1 agent=anthropic/claude-opus-5 generated_at=2026-08-05 -->

# Agent handoff: after `feat/enforcement-first-governance` (C-11/C-12 adopted with four mechanisms; next branch is OWNER-GATED)

**Branch to create:** `<!-- owner decides — see First move -->` (branch off `main`)
**Base branch:** `main`

> **READ THIS FIRST — the governing posture changed on this branch.**
> **A constraint with no mechanism that fails closed is not a constraint.** Charter **C-11**
> now makes "write a note about it" a **non-compliant** response to a recurrence, and
> **C-12** makes an undeclared information gap a C-0 violation. Four mechanisms enforce
> this; three of them can block you. Read `AGENTS.md` §C-11 and §C-12 before you plan.
>
> **Your handoff will not validate unless you answer C-11's question** — the template now
> carries a required recurrences-and-guardrails section, and `verify_doc_template.py`
> refuses a handoff without it.

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

**Stream:** v1.1.0 Final March — enforcement/CI-infrastructure pass, ahead of epic A.
**Sequencing rule:** strictly sequential — one branch at a time.
**Blocked until this stream tags:** the public v1.1.0 cut (epic E / item 10).

- ~~`chore/v11-march-kickoff`~~ ✓ · ~~`feat/consumer-enumeration-gate`~~ ✓ (C-10)
- ~~`fix/ux-scroll-spy-overlapping-refresh`~~ ✓ — item 44
- ~~`feat/ci-wait-wrapper`~~ ✓ — `scripts/ci_wait.py` (PR #102)
- ~~`feat/enforcement-first-governance`~~ ✓ — C-11 + C-12, this handoff's branch
- **next ← OWNER-GATED, see First move**
- Still queued: dependabot `groups:` → dependency upgrades (#63 ruff, then #50, #84) →
  verify-don't-assume Bash guard → items 45, 46
- `fix/experience-soft-retire` ← sprint A1, only after the above **and** a check-in

**The march is still deliberately paused.** Do not touch epics B–E.

**Item 10's release chain is gated on epic 19 again** — 19 was reopened this session because
child 30 recurred. That is the correct signal; do not route around it by re-closing 19
without evidence (and the closure bar will now refuse a prose-only closure anyway).

---

## What just landed on `main`

**Nothing yet — not merged as of writing.** Five commits on the branch: `c3bd546`,
`35c4e66`, `2e670d4`, `1524ad7`, `77d837c`.

**Charter C-11 + C-12 adopted, with four mechanisms.** The posture: **new governance
defaults to a gate; prose discipline is the exception and is labeled unenforced where used.**

- **C-11 — Enforcement before discipline.** The *first* time a failure mode is recognized as
  a recurrence, the response is a mechanism that fails closed, authored on that branch. A
  note/memory/ledger row/prose rule is **not compliant on its own**.
- **C-12 — Declare the gap; never fill it.** Lost information is surfaced as missing before
  anything depends on it. Compaction is a data-loss event **to be announced**.

| # | Mechanism | Where it blocks |
|---|---|---|
| M1 | Closure bar — `closed` needs `verified_by` (falsifiable artifact) or an owner-named `closure_exception`; a **reopened** item needs a `guardrail` | `scripts/work_items.py` → runs in `scripts/gate.py` **and CI**, so it binds every agent |
| M2 | `## Observed` citing **nothing** blocks the production edit | `scripts/enforcement/evidence.py` + `require-evidence-before-fix` (PreToolUse) |
| M3 | PreCompact writes a durable `compacted` receipt; SessionStart(`compact`) always injects an information-loss declaration | `scripts/enforcement/adapters/claude_context_hook.py` |
| M4 | A handoff missing the recurrences section is a hard `failed` | `docs/dev/AGENT_HANDOFF_TEMPLATE.md` + `verify_doc_template.py` |

**Every mechanism was proven RED-then-GREEN**, several against real artifacts rather than
fixtures: M1's reopen rule fired on exactly items 19 and 30; M4's RED is the previous
branch's own committed handoff now failing validation; M3's RED is `restore_evidence()`
returning `""` on a non-`fix/*` branch after a compaction — i.e. **most branches got no
notice at all that they had lost information.**

**Stated limits, and they are load-bearing (C-0):** none of this detects invention. M2/M4
enforce *shape* — a fabricated run id passes both. `verified_by` is not existence-checked.
`closure_exception` is a real escape, deliberately **named and attributed** rather than
silent; routine use is itself the signal and is visible in the diff. M2/M3 are Claude Code
hooks and do **not** bind Codex/Cursor/Aider — only M1 binds every agent.

**Local gate green**, assembled as the sanctioned split (foreground; see the operational
note below): ruff ✓ · ruff format ✓ · mypy ✓ **352 files** · `pytest -m "not ux"` **2282
passed / 1 skipped** (2210 + 72 `test_enforcement_core`) · `pytest -m ux` **138 passed / 1
xfailed / 1 xpassed** across three chunks (11 + 59 + 68), matching the established baseline
exactly · `work_items check` ✓ 48 files. **Zero reruns are possible locally** — `--reruns` is
CI-only, so every pass here is a first-attempt pass by construction.

**Operational note (cost ~40 min this session).** Long test runs could not complete in this
environment: three backgrounded runs were killed, and the foreground 10-minute cap was
exceeded three more times. **The tell for killed-vs-failed is the absent exit-code line** —
always append `; echo "EXIT: $?"` outside any pipe. Measured mid-session: ~2 GB free RAM and
diffuse CPU load (no single runaway process; an instantaneous "100%" reading was
misleading). **Do not attribute a kill to memory pressure without measuring** — a previous
session did and was wrong. What worked: **foreground chunks** — `-m "not ux"` minus
`test_enforcement_core`, then that file alone, then ux as `a11y+flows` /
`regression[:26]` / `regression[26:]`.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

**Open (2 / 10 ceiling):**
1. **Item 19 — UX-suite flake epic, REOPENED this session** (child 30 recurred). Carries a
   `guardrail` naming what was built *and* stating plainly that the flake class itself
   remains unguarded — no mechanism prevents the next flake, only the next premature closure.
2. Item 45 — plan-approval marker survives a PR-channel merge. **Third consecutive
   confirmation** this session; the marker was found stale at startup and **not ridden**.

**Blocked (3 + the sequenced epics):** item 3 ([HUMAN] GitHub toggles — note `enforce_admins`
is now unblocked: both halves of its precondition are met), item 5, item 8, epics 37–40.

**Deferred (7):** items 4, 7, 24, 25, 41, 42, 43 — see BOARD.md.

**Watching (6):**
- Item 2 (wordmark sweep) · Item 16 (`--suite real` non-functional) · Item 18 (judge
  variance, n=2) · Item 23 (PX-52 analyzer split)
- **Item 30 — REOPENED**, with the first captured artifact this failure mode has ever
  produced (a 30s timeout while `composeReady=True`, zero pending requests, iframe
  `complete`). **Do not fix from it — n=1.**
- Item 46 — torn-read control arm; its own dossier says the mechanism is **"inferred, not
  proven… no instrumented run was made."** Do not weaken the control.
- Item 47 — sibling scroll-spy settle-gate audit, still never done.
- Item 48 — ux CI job 14m49s vs a ~5m1s baseline; green, zero reruns, uncharacterized.

Open-only count is 2, under the reduction-sprint threshold. **But the honest signal is not
the count** — it is that the flake backlog (19/30/46/47/48) has now survived ~40 days and
~20 branches, and **nothing landed this session fixes a single flake.** This branch changed
how the *next* one must be handled, and nothing more.

---

## Recurrences observed this session → guardrail authored

**Four recurrences. Two got mechanisms; two did not, and that is stated plainly rather than
left implied — which is exactly what C-11 requires of a null answer.**

1. **Closing an item on evidence weaker than the closure claimed.** Recognized as a
   recurrence, not a first sighting: item 30 recurred in CI five days after closure, and
   auditing epic 19 showed **three of five** children closed this way (27
   already-fixed-before-filing, 28 *not reproduced*, 30 on a fix its own text called "not
   confirmed as the historical cause").
   → **Guardrail authored: M1**, the closure bar in `scripts/work_items.py`. Gate + CI.

2. **Asserting an unsourced reconstruction as an observation.** Recognized as a class from
   this repo's own record — items 13, 15 and 31 each filed a plausible mechanism later
   falsified, and each became a premise before it was caught.
   → **Guardrails authored: M2** (citation floor) **and M3** (compaction disclosure).

3. **Long test runs killed / capped, and the kill misread as a failure.** Six occurrences
   *this session alone*. On the second, I initially read a worker's `node down` as a real
   test failure and began diagnosing a test that was fine.
   → **NO GUARDRAIL AUTHORED**, and the reason: the constraint is the agent-harness
   execution cap, not repo code, so nothing in this repository can fail closed on it. A
   `scripts/` runner that chunks the gate to fit the cap is a plausible mechanism and is
   **explicitly out of scope here** (one branch, one item). **Surfaced to the owner
   in-session rather than filed silently.** If you hit this, the working method is in the
   operational note above — do not re-derive it.

4. **My own tooling error: `\n` escaping collapsing inside a `python - <<'PY'` heredoc.**
   Recurred **three** times within the session — first as a silently non-matching anchor (0
   replacements, caught only by an `assert`), then as a **syntactically broken file written
   to disk**, then as a string-index match against the wrong occurrence that **corrupted a
   draft of this very handoff** (discarded and rewritten; it was never committed).
   → **NO GUARDRAIL AUTHORED.** Reason: this is an agent-technique failure with no repo
   surface to gate — a hook cannot inspect how I construct a heredoc. Recorded here because
   C-11 forbids leaving a recognized recurrence implied. **Practical mitigation for the next
   session: prefer `Edit` over a Python rewrite script; when a rewrite script is genuinely
   needed, build `\n` as `chr(92) + "n"` and anchor on a string you have confirmed is
   unique — `t.index()` silently takes the first match.**

---

## What this branch should build

**OWNER-GATED — do not pick this yourself.** The owner is weighing two directions, and the
session's plan must start from their answer:

- **(a) Flake-rate measurement.** Extract true per-attempt failure rates per test from CI job
  logs — `scripts/ci_wait.py` already parses the rerun alarm, and `gh` returns per-job elapsed
  time that it currently discards, so this is additive and costs no extra API calls.
  Converts "flaky" into a ranked list with numbers, and answers whether this is one mechanism
  or seven **before** anyone commits to a fix shape.
- **(b) The queued CI-infra work** — dependabot `groups:` (11 open PRs, and no `groups:` key
  anywhere in `.github/dependabot.yml`; verified 2026-08-05), then the upgrades.

**Owner context you must not lose:** they are actively considering **redesigning the UX suite
or the system around it**, on the grounds that a month of flake work produced repeated
closures that did not hold. A prior session's read — offered as opinion, **not** established
fact — is that the tests are correctly detecting that the app has no defined quiescence
contract (seven bespoke synchronization primitives, 79 occurrences, 14 files), and that one
app-owned in-flight-operation counter would replace them. **That is unverified. Do not
present it as a finding.**

**Scope is bounded to one item.** Do not also take items 45/46/47, sprint A1, or the flake
fixes themselves.

---

## First move

**Owner, at launch:** choose (a) or (b) above, and approve the session plan when asked.

Agent: FIRST action is `python scripts/check_handoff_pointer.py "<the pointer line you were
given>"`; once it passes, consume this file
(`python scripts/verify_doc_template.py docs/dev/handoffs/feat-enforcement-first-governance.md
docs/dev/AGENT_HANDOFF_TEMPLATE.md --event consumed --agent <agent>`).

Then create the branch the owner chose off `main`, write a plan at
`~/.claude/plans/<slug>.md`, and show it before touching code. **Do not code first.**

**Do not trust a pre-existing plan-approval marker** (item 45). Earn a fresh one via
`EnterPlanMode` → plan → `ExitPlanMode`. Verified three sessions running.

**When your PR is up, wait on it with `python -m scripts.ci_wait <n>`.** Never hand-roll a
watcher. **Exit 3 is not success** — it means every required check passed but a test needed a
retry, and on PR #102 that is exactly how item 30's recurrence was caught.

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
