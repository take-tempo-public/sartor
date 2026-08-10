<!-- provenance: schema=1 session=ce768599-40ad-4c65-b996-cf7398315b19 branch=fix/plan-approval-marker-pr-merge commit=8844c9c actor=amodal1 agent=anthropic/claude-sonnet-5 generated_at=2026-08-07 -->

# Agent handoff: after `fix/plan-approval-marker-pr-merge` (item 45 closed)

**Branch to create:** none — owner decision, not this handoff's to make. See "First move" below.
**Base branch:** `main` (this branch's own base; `main` was at `ae7e0fa` when this branch started).

**This branch closed item 45** (plan-approval marker survives a PR-channel merge).
The prior session's staged design (D3(b), a `SessionStart` reconciler) was disproven
before being built; this session pivoted to a design that lives inside the existing
`check-plan-approved.sh` PreToolUse blocker, built it, found and fixed two further
genuine defects while doing so, and landed with a green gate.

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

- ~~`chore/v11-march-kickoff`~~ ✓ · ~~`feat/consumer-enumeration-gate`~~ ✓ (C-10)
- ~~`fix/ux-scroll-spy-overlapping-refresh`~~ ✓ — item 44
- ~~`feat/ci-wait-wrapper`~~ ✓ — `scripts/ci_wait.py` (PR #102)
- ~~`feat/enforcement-first-governance`~~ ✓ — C-11 + C-12 (PR #103)
- ~~`feat/flake-rate-measurement`~~ ✓ — `scripts/flake_rates.py` + `docs/dev/flake-rates/`
- ~~`chore/dependabot-groups`~~ ✓ — `groups:` key added to `.github/dependabot.yml`
- ~~`feat/verify-dont-assume-guard`~~ ✓ — `verify-binary-on-path` PreToolUse guard +
  Bash-matcher hooks folded into one dispatcher
- ~~`fix/plan-approval-marker-pr-merge`~~ (first occupancy) — item 45 dossier written,
  root cause proven, neither candidate fix shape implemented
- ~~`fix/chain-gate-integration`~~ ✓ — F1 + F2 fixed; chain-level push-blocker resolved
- ~~The pre-march chain merged as PR #105 (`c15d080`)~~ ✓
- ~~`docs/wiki-enforcement-catchup`~~ ✓ — pruned chain branches, scoped
  `/wiki-self-update`, 0 pages needed editing (PR #110, `ae7e0fa`)
- **`fix/plan-approval-marker-pr-merge` (second occupancy)** ← this branch — item 45
  CLOSED. D3(b) refuted, D3(c) built, two implementation-time defects found and
  fixed, gate green.
- **Next: sprint A1, OR an owner-directed alternative — owner decision, not this
  handoff's to make.** See "First move" below.

**The march is still deliberately paused before epics B–E.**

**Item 10's release chain is still gated on epic 19** — untouched this session.

---

## What just landed on `main`

`main` was at `ae7e0fa` (PR #110) when this branch started. This branch's own tip is
`8844c9c` (one commit — the branch was small enough that the pre-close sweep folded
into the same commit as the fix rather than a separate close-out commit; the handoff
you are reading and the item/CHANGELOG updates are part of that same commit).

**What the commit does:**

1. **Refuted the prior session's staged D3(b) design** before writing any code for
   it, verified directly against this repo's own artifacts (not re-derived from the
   dossier's prose): `.approved-C--Dev-sartor`'s mtime is the `ExitPlanMode` write;
   `git reflog` shows the feature branch was created 3m42s *after* that write, so
   `ExitPlanMode` fires on `main`, not on the feature branch the dossier's own
   hand-trace assumed. An approval-time stamp would record `branch=main, sha=<main's
   own tip>`, trivially an ancestor of `main` forever — the reconciler would archive
   a legitimately-armed marker at the first `startup/resume/compact` after every
   approval. Full evidence: `docs/dev/diagnosis/plan-approval-marker-pr-merge.md`
   "D3(b) refuted".
2. **Pivoted (owner-approved) to D3(c):** the same channel-independent ancestry
   check, moved into the existing `check-plan-approved.sh` PreToolUse blocker with a
   **late-bound** stamp (written on the first production edit after approval, the
   moment `require-feature-branch` guarantees HEAD is a real feature branch). No new
   hook file, no `.claude/settings.json` change, no
   `tests/test_governance_hooks_gate.py` edit — verified those stayed untouched.
3. **Owner directive (archive, never delete) implemented** via a new shared
   `hooks/lib/retire-approved-plan.sh`, sourced by both `check-plan-approved.sh` and
   `cleanup-plan-on-merge.sh` (switched from `rm -f`).
4. **Two further genuine defects found and fixed while BUILDING the mechanism**, both
   root-caused by direct reproduction (not guessed at): a `$HOME`-derived path handed
   to `python3` as an argv string is silently wrong on Windows/Git-Bash (MSYS
   auto-translates `$HOME` to POSIX form, which a native `python3.exe` misresolves —
   fixed via `cygpath -m`); and the archive directory name embedded the entire
   sanitized project path, which for a sufficiently long real path pushes
   `manifest.json` past Windows' 260-char `MAX_PATH` (reproduced exactly: `plan.md`
   stayed under, `manifest.json` tipped it over — fixed by hashing the project key to
   12 hex chars for the directory name). New reference memory:
   `reference-bash-to-python3-path-gotchas-windows`.
5. **18 new regression tests** in `tests/test_plan_approval_scoping.py`, confirmed
   RED against the pre-fix hooks (`git stash` the two hook files, rerun, confirm
   failure, restore) before the fix landed, then GREEN after.
6. **Item 45 closed** with `verified_by` naming the six most load-bearing tests.
   **Item 55 filed** (carry-forward, `status=watching`) for the `plan-archived`
   ledger-event vocabulary drift this receipt introduces into
   `docs/dev/prov/SPEC.md` — deliberately not amended on this branch (SPEC.md is
   itself a C-10 gated surface; amending it would drag `require-consumer-enumeration`
   across every ledger consumer for a bugfix branch).

**Full gate at this branch's tip, no reruns anywhere:**
- `python -m ruff check .` → all checks passed
- `python -m ruff format --check .` → 342 files already formatted
- `python -m mypy .` → Success: no issues found in 357 source files
- `python -m pytest -m "not ux"` → this machine's background test runner exhibited
  **five consecutive kills** this session (`[gwN] node down: Not properly
  terminated`, the same signature `reference-shared-machine-oom-kills-bg-runs`
  already documents; `wmic OS get FreePhysicalMemory` confirmed ~1.5–1.9GB free of
  16.5GB throughout, external pressure, not a leak of this session's own — orphan
  sweep found only one unrelated `C:\Dev\spolia` process). **Assembled a complete,
  verified result from 8 kill-resistant foreground batches** (`split -n l/8` over the
  139 top-level test files) instead: **2375 passed / 1 skipped / 0 failed / 0
  reruns** — an exact match for the pre-branch baseline (2357) plus this branch's own
  18 new tests. Both memories updated with this session's data (see
  "Recurrences" below).
- `python -m scripts.work_items check` → OK (55 files)
- `python -m scripts.wiki_freshness` → OK — 20 file(s) changed since the last ingest
  (< 75-file block threshold), unchanged from the prior session's figure — this
  branch added no wiki-relevant paths (checked: none of its 10 changed files
  classify as wiki-relevant per `scripts/wiki_relevance.py`).

**Wiki-relevance check (pre-close sweep item 0):** none of this branch's changed
files (`hooks/*`, `tests/*`, `docs/dev/diagnosis/*`, `docs/dev/work/*`,
`CHANGELOG.md`) classify as wiki-relevant. Stated explicitly per the required
discipline, not silently skipped.

**No dev server or long-lived background process from this session's own sartor
work left running** — every test run (chunked or otherwise) completed and exited.
**Separately observed, not this branch's to fix:** `C:\Dev\spolia\.venv\...python.exe
-m http.server 8971` — a different project's own orphan, same class the last two
handoffs flagged; not started by this session or this repo.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

`docs/dev/work/BOARD.md` is the authoritative live-item source (regenerate with
`python -m scripts.work_items board --write`; not hand-edited). Reproduced verbatim
from the board at this branch's tip, not re-derived.

**Open (1, down from 2 — item 45 closed this session):**
1. **50** — C-7 and C-10 are enforced by Claude Code hooks only — the clauses do not
   travel to other agents or an extracted governance package. Guards are not routed
   by `git_hook.py`, so only Claude Code enforces them; prose binds other agents.

**Blocked (3):** item 3 ([HUMAN] GitHub toggles), item 5 (grounding-score persistence
gap), item 8 (Compose-time rewrite latitude dial).

**Deferred (7):** items 4, 7, 24, 25, 41, 42, 43 — all owner-gated or explicitly
post-1.1.0-scheduled; see `BOARD.md` for each.

**Watching (13, up from 12 — item 55 filed this session):** items 2, 16, 18, 23, 46,
47, 48, 49, 51, 52, 53, 54, **55 (new — ledger event vocabulary drift, this branch's
own finding, see above)**; see `BOARD.md` for each.

**Epics (6):** 19 (UX-suite flakiness umbrella, children 27–31), 36 (Final March epic A,
children 20, 34 — open), 37/38/39/40 (Final March epics B/C/D/E — blocked, sequenced
after A per the march plan). Epic 39 carries item 9 (stale screenshots); epic 40 carries
item 10 (the v1.1.0 tag itself, `depends on: 3, 6, 7, 9, 19`).

**Closed (20, up from 19 — item 45 this session):** unchanged otherwise — see
`BOARD.md` for the full list.

Open-only count stays **1**, well under the reduction-sprint threshold.

---

## Recurrences observed this session → guardrail authored

**Three recognized recurrences this session.**

1. **`ScheduleWakeup` called to poll a background Bash task's completion, twice, and
   the flawed `stop:true` "recovery" also recurred.** Despite the durable memory
   (`feedback-schedulewakeup-not-for-background-bash`) being present in the
   auto-loaded MEMORY.md index, AND despite this session's own consumed handoff
   explicitly narrating the *prior* session's identical recurrence as "recognized,
   no mechanism possible" in its own C-11 section — this session repeated it anyway
   (occurrence 20 of the trigger, occurrence 4 of the flawed `stop:true` recovery
   specifically) minutes after reading that exact narration. **No new mechanism
   authored** — `ScheduleWakeup` is a harness tool outside this repo's own
   hooks/enforcement surface, and the memory file itself now states plainly (per its
   own occurrence-7 conclusion, reaffirmed) that in-context recall has been proven
   insufficient 20 times running and this needs harness-level enforcement, not
   another memory reinforcement. Surfaced here rather than left implied.
2. **Background pytest/gate runs killed by (likely) shared-machine memory pressure —
   recurrence of a known class, but with a NEW, partially-contradicting data point.**
   `reference-shared-machine-oom-kills-bg-runs` already documented this failure mode
   and explicitly claimed chunking does NOT help ("smaller chunk size didn't
   matter"). This session found the opposite: chunking into 8 foreground batches
   rescued a run that failed 5 times running in every un-chunked shape tried
   (`-n auto`, `-n 4`, serial). **Mechanism: the memory itself, updated with both data
   points** rather than only the more emphatic one — this is exactly the kind of
   external-tooling limitation this repo's own C-11 exempts from requiring an
   in-repo gate (the tool is outside `sartor.`'s own hooks/gate surface), so the
   guardrail is the corrected record, stated as such.
3. **A design characterized by hand-trace, then treated as sound, without being
   built and run — the SAME failure class `docs/dev/diagnosis/plan-approval-marker-
   pr-merge.md`'s own "Known limit" paragraph predicted for itself.** Recognized as a
   member of failure pattern 5f ("guessing the mechanism") the moment the dossier's
   own reflog evidence contradicted its hand-trace premise. **Mechanism authored:**
   `tests/test_plan_approval_scoping.py::TestBranchMergeReconciliation::
   test_stamp_is_late_bound_on_the_first_production_edit` and
   `test_no_stamp_is_written_while_head_is_main` pin *when* the stamp is bound as a
   committed, falsifiable test — any future reversion to approval-time stamping goes
   red rather than shipping plausible-but-wrong again.

**Everything else this session** (the `cygpath`/MSYS path-translation defect and the
`MAX_PATH` defect) — both were first sightings of their specific mechanism in this
repo, not recognized recurrences of a prior class; recorded as a new reference memory
(`reference-bash-to-python3-path-gotchas-windows`) rather than framed as C-11
recurrences.

---

## What this branch should build

**Nothing further — item 45 is this branch's complete scope, and it is done.**

Do not expand beyond item 45's own fix. Sprint A1 and any other next-branch work is
explicitly the next session's own scoped branch, not a continuation of this one.

---

## First move

**There is no single prescribed first move — item 45 being closed does not
auto-select the next branch; that is still an owner decision:**

- **Sprint A1** (`feat/corpus-polish` + `fix/experience-soft-retire`, epic 36) — per
  `RELEASE_ARC.md`'s Final March cadence, "the next session starts from the epic
  branch with the owner's plan-approval click." Model prescription: **Opus** (schema
  migration + retired-role blast-radius audit). This is the march's own next
  scheduled sprint and the most likely default absent other direction.
- **Item 50** (C-7/C-10 enforcement is Claude-Code-only) — `status=open`, the sole
  remaining Open-ledger item, but `decision_owner = "user"` and no fix shape has been
  proposed; not actionable without an owner scoping decision first.
- **Anything else the owner directs.**

Whichever the owner picks: write a plan at `~/.claude/plans/<slug>.md` and show it to
the user before touching any code. **Do not code first.**

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
