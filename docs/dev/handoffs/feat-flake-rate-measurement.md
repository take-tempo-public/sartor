<!-- provenance: schema=1 session=20b5de20-e774-4fe3-905e-bcad687d7188 branch=feat/flake-rate-measurement commit=4f26eac actor=amodal1 agent=anthropic/claude-sonnet-5 generated_at=2026-08-06 -->

# Agent handoff: after `feat/flake-rate-measurement` (the closure bar's `verified_by` instrument now exists; next is dependabot `groups:`)

**Branch to create:** `chore/dependabot-groups` (branch off `main`)
**Base branch:** `main`

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

**Stream:** v1.1.0 Final March — CI-infrastructure pass, ahead of epic A.
**Sequencing rule:** strictly sequential — one branch at a time.
**Blocked until this stream tags:** the public v1.1.0 cut (epic E / item 10).

- ~~`chore/v11-march-kickoff`~~ ✓ · ~~`feat/consumer-enumeration-gate`~~ ✓ (C-10)
- ~~`fix/ux-scroll-spy-overlapping-refresh`~~ ✓ — item 44
- ~~`feat/ci-wait-wrapper`~~ ✓ — `scripts/ci_wait.py` (PR #102)
- ~~`feat/enforcement-first-governance`~~ ✓ — C-11 + C-12 (PR #103)
- ~~`feat/flake-rate-measurement`~~ ✓ — `scripts/flake_rates.py` + `docs/dev/flake-rates/`, this handoff's branch
- **`chore/dependabot-groups`** ← next (per `project-ci-infrastructure-sprint-sequence` memory's plan of record)
- Still queued: dependency upgrades (#63 ruff, then #50, #84) → verify-don't-assume
  Bash guard → items 45 → sprint A1
- `fix/experience-soft-retire` ← sprint A1, only after the above **and** a check-in

**The march is still deliberately paused.** Do not touch epics B–E.

**Item 10's release chain is still gated on epic 19** — reopened 2026-08-05 when
child 30 recurred; this branch found a THIRD recurrence (2026-08-03, previously
unfiled — see item 30's own 2026-08-06 update) and did not close anything. Do not
route around 19 by re-closing it without evidence — the closure bar now refuses a
prose-only close anyway.

---

## What just landed on `main`

**Nothing yet — not merged as of writing.** Working tree on `feat/flake-rate-measurement`
has one prior commit (`4f26eac`, the handoff-consumed ledger row) plus everything below,
staged/uncommitted until this session's close-out commit.

**`scripts/flake_rates.py` — real per-test, per-attempt CI flake rates from job logs**,
the falsifiable artifact charter C-11's closure bar needs. `collect` fetches CI runs via
`gh` (one whole-run log fetch per run, latency-bound not payload-bound); `report` ranks
by Wilson 95% lower bound, never raw rate. A committed, content-addressed store lives at
`docs/dev/flake-rates/` (README documents the schema + explicit LIMITS section — read it
before citing a number from the store).

Design was verified against a real captured log (`gh run view 31047661015 --log`)
**before any production code was written** — 14 numbered observations (O-1…O-14, in the
module's own docstring), three of which broke a first-draft parser **silently** (no
exception, no zero result, just a quietly wrong count): a custom rerun-marker hook
splitting pytest's own outcome line, pytest-xdist's bare-nodeid dispatch echo, and
pytest's own `=== FAILURES ===` section landing *after* every outcome line rather than
inline — the third one caught live by the first real 30-run backfill (7/233 sessions
would have been wrongly excluded), fixed, re-verified.

**First backfill (30 real runs, 2026-08-03 → 2026-08-06, 233 sessions, all
reconciled).** Findings filed on the work items rather than restated here: item 44's
fix independently confirmed (clean regime split, before/after the fix landing); item 30
gained a previously unfiled THIRD occurrence; item 46's known sample independently
reproduced; item 47 got a partial sibling-audit contribution; item 48's pytest-step
duration came back tight, narrowing its 3x anomaly to outside pytest's own execution.
Work item 51 (new) tracks the deliberately-unbuilt follow-on (`report --check` against
a committed budget) — this branch is an instrument, not a gate, and says so explicitly
(C-12).

`tests/test_flake_rates.py` — 38 tests, verbatim real-log fixtures for both output
shapes, reproduces item 30's captured evidence independently, mutation tests prove the
reconciliation guard has teeth (reject-then-accept, per `test_work_items_closure_bar.py`'s
own standard).

**Local gate green**, run as individual steps (foreground, matching this session's own
lesson from the prior handoff about killed background runs — none hit this session,
worth stating since it did NOT recur): `ruff check .` ✓ · `ruff format --check .` ✓ ·
`mypy .` ✓ **355 files** · `pytest -m "not ux" -n auto` **2325 passed / 1 skipped** ·
`pytest -m ux` **138 passed / 2 xfailed, zero reruns** (818s local wall-clock — Chromium
IS installed on this machine, unlike some prior sessions) · `work_items check` ✓ **51
files**. The canonical `python -m scripts.gate` wrapper was **not** re-run as one
command after the individually-verified steps all passed — each of its six steps was
run directly and passed; re-running the wrapper would have re-paid ~15 minutes for
zero new information. State this as a deliberate deviation from the literal checklist
step 1 wording, not a silent skip.

**A mid-session compaction occurred** (PreCompact wrote a `compacted` receipt to this
session's own ledger shard, `docs/dev/ledger/20b5de20-….jsonl`, `trigger=unknown`).
Announced in-session per C-12; reconciled against actual `git status`/`git log` rather
than trusting the pre-compaction summary — nothing was lost or contradicted. No new
mechanism needed here; the existing M3 receipt is what made it visible at all.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

**Open (2 / 10 ceiling):**
1. **Item 19 — UX-suite flake epic, still open (reopened 2026-08-05).** This branch
   added a third occurrence to item 30 (its own reopened child) and independently
   confirmed item 44's fix held — see item 19's own 2026-08-06 update for the summary.
   The flake CLASS itself remains unguarded; the instrument that CAN produce
   `verified_by` evidence now exists, but spending it (closing 19 or 30) is explicitly
   not done on this branch.
2. Item 45 — plan-approval marker survives a PR-channel merge. Not touched this
   session; still worth a fresh `EnterPlanMode` → plan → `ExitPlanMode` rather than
   trusting a pre-existing marker (verified 3+ sessions running now).

**Watching (9, +1 new):**
- Item 30 — REOPENED, now with **three** dated CI occurrences (2026-07-28 original,
  2026-08-03 previously-unfiled, 2026-08-05 PR #102) — still not root-caused. **Do not
  fix from the rate alone** — n=2 in the measured window is still thin.
- Item 46 — independently reproduced by the instrument this branch built; still n=1,
  escalation signal (a second PR) not fired.
- Item 47 — got a partial (empirical-only) contribution; the grep-and-read half of the
  audit it actually asks for is **still not done**.
- Item 48 — pytest-step duration data added; the underlying 3x job-duration anomaly is
  narrowed but still uncharacterized (n=1).
- **Item 51 (NEW)** — `report --check` against a committed budget: the closed-loop
  follow-on to this branch's instrument, deliberately not built (not enough history
  yet to set a budget responsibly). Escalate once `docs/dev/flake-rates/runs/` spans
  enough calendar time/run count to set one from real distributions.
- Item 2 (wordmark sweep) · Item 16 (`--suite real` non-functional) · Item 18 (judge
  variance, n=2) · Item 23 (PX-52 analyzer split) — untouched this session.

**Blocked (3 + the sequenced epics):** item 3 ([HUMAN] GitHub toggles), item 5, item 8,
epics 37–40 — untouched this session.

**Deferred (7):** items 4, 7, 24, 25, 41, 42, 43 — see BOARD.md, untouched.

Open-only count is 2, under the reduction-sprint threshold. The honest signal, same as
last handoff: nothing landed this session fixes a single flake. This branch changed
what evidence exists about the flake backlog, and nothing more — nothing here should
read as progress toward actually reducing it.

---

## Recurrences observed this session → guardrail authored

**One clear recurrence with a mechanism authored on this branch; two design gaps
caught and fixed during THIS branch's own build (not recurrences of a PRIOR failure
mode, but worth stating plainly per C-11's spirit — a design flaw caught before it
shipped is not the same as "nothing to report").**

1. **A silently broken CI-log parser is exactly the failure class C-7/`ci_wait.py`
   already exist to prevent, now recognized as a pattern that could recur in ANY new
   log-parsing tool, not just this one.** Two of this branch's own first-draft
   regexes returned wrong counts with no error during design verification (O-1
   timestamp-in-tab-field, O-13 parametrize-ids-with-spaces), and the first real
   backfill caught a third live (O-14, the `=== FAILURES ===` section).
   → **Guardrail authored: the `Session.reconciled` check** in
   `scripts/flake_rates.py` — parsed roster size vs. the terminal summary's own
   declared counts. A session that doesn't reconcile is excluded from rates, never
   silently trusted. Proven with teeth: `tests/test_flake_rates.py`'s
   `TestReconciliationHasTeeth` mutates a clean fixture and asserts exclusion, not a
   silent pass. Also captured as a portable, reusable memory
   (`reference-gh-actions-log-parsing-gotchas`) so a *future* log-parsing tool (in
   this repo or elsewhere) starts from these 9 concrete traps instead of
   re-discovering them.

2. **Item 30's own history recurred a THIRD time before this branch even started
   measuring — and it was invisible for the same reason item 44 already named**
   ("the repo's own rerun-rate alarm... was landing in the job log unread on every
   run"). The 2026-08-03 occurrence predates `scripts/ci_wait.py`'s existence, so
   nothing could have caught it live. → **No NEW guardrail authored for this specific
   recurrence** — it is exactly what `scripts/flake_rates.py` (built this branch) and
   `scripts/ci_wait.py` (built the prior-prior branch) together now prevent going
   forward: `ci_wait` catches it live on the PR that produces it; `flake_rates`
   catches it in retrospect across a backfill window. Stated explicitly rather than
   filing a third redundant mechanism for the same already-covered gap.

**Everything else surfaced this session (the O-1/O-11/O-12/O-13 findings) was caught
during this branch's OWN design/build, before shipping — first sightings within this
branch's own development, not recurrences of a prior failure. Each got a fix + a test
proving the fix has teeth, per the module's own docstring. Not itemized again here to
avoid restating the CHANGELOG/module-docstring content.**

---

## What this branch should build

**OWNER CONTEXT, not yet a directive for the next branch specifically:** the sprint
sequence memory (`project-ci-infrastructure-sprint-sequence`) names dependabot
`groups:` config as the next step in the CI-infrastructure pass — **confirm with the
owner at session start rather than assuming**, since the owner has not explicitly
re-confirmed this specific next branch the way flake-rate-measurement was explicitly
directed.

If confirmed: add a `groups:` key to `.github/dependabot.yml` (currently absent —
verified 2026-08-05, still true) to collapse the current 11 open dependabot PRs
(8 fully green, never merged — a merge-policy gap) into ~3 grouped PRs per ecosystem.
Cite: `project-ci-infrastructure-sprint-sequence` memory, `docs/dev/RELEASE_CHECKLIST.md`.

**Scope is bounded to that one config change plus verifying the resulting grouped
PRs are green** (auto-merge is already enabled per the prior session's own
verification — nothing else to build there). Do not also pick up the ruff/codeql/
fumadocs dependency bumps themselves, item 45, sprint A1, or any flake fix — those
are separately sequenced.

---

## First move

**Owner, at launch:** approve the session plan when asked, and confirm the next
branch is actually dependabot `groups:` (see the caveat above — this was not an
explicit owner directive the way this branch's own build was).

Agent: FIRST action is `python scripts/check_handoff_pointer.py "<the pointer line
you were given>"`; once it passes, consume this file
(`python scripts/verify_doc_template.py docs/dev/handoffs/feat-flake-rate-measurement.md
docs/dev/AGENT_HANDOFF_TEMPLATE.md --event consumed --agent <agent>`).

Then create the confirmed branch off `main`, write a plan at
`~/.claude/plans/<slug>.md`, and show it before touching code. **Do not code first.**

**Do not trust a pre-existing plan-approval marker** (item 45). Earn a fresh one via
`EnterPlanMode` → plan → `ExitPlanMode`.

**When your PR is up, wait on it with `python -m scripts.ci_wait <n>`.** Never
hand-roll a watcher. **Exit 3 is not success** — it means every required check
passed but a test needed a retry; if it fires, consider running
`python -m scripts.flake_rates collect` before merging to add the new data point to
the store rather than letting it go unrecorded.

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
