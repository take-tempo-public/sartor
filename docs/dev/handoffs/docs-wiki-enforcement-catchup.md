<!-- provenance: schema=1 session=2859b199-f3c9-4030-a8c7-d3e7548831dd branch=docs/wiki-enforcement-catchup commit=3ac5ed8 actor=amodal1 agent=anthropic/claude-sonnet-5 generated_at=2026-08-06 -->

# Agent handoff: after `docs/wiki-enforcement-catchup` (scoped wiki update over the chain's own diff — 0 pages edited)

**Branch to create:** none — the two candidate next branches (item 45's fix, or sprint A1)
both need an owner decision first; neither starts automatically from this handoff. See
"First move" below.
**Base branch:** `main` (this branch's own base; `main` was already at `c15d080` — the
merged pre-march chain — when this branch started).

**This branch is small and complete.** It executed exactly what
`docs/dev/handoffs/fix-chain-gate-integration.md`'s own "Post-chain addendum" queued: prune
the chain's now-merged branches, then run a scoped `/wiki-self-update` against the chain's
own diff. Both done. Nothing else was touched.

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
- ~~`feat/flake-rate-measurement`~~ ✓ — `scripts/flake_rates.py` + `docs/dev/flake-rates/`
- ~~`chore/dependabot-groups`~~ ✓ — `groups:` key added to `.github/dependabot.yml`
- ~~`feat/verify-dont-assume-guard`~~ ✓ — `verify-binary-on-path` PreToolUse guard +
  Bash-matcher hooks folded into one dispatcher
- ~~`fix/plan-approval-marker-pr-merge`~~ ✓ — item 45 dossier written, root cause
  proven, neither candidate fix shape implemented (item stays open by design)
- ~~`fix/chain-gate-integration`~~ ✓ — F1 (`hooks/bash-dispatcher.sh` re-gated
  executable) + F2 (doc-link regex-literal false positive) fixed; chain-level
  push-blocker resolved
- **The whole chain merged as PR #105 (`c15d080`)** — landed by the orchestrator
  between that handoff and this session; found already merged at session start,
  not this session's own act (verified via `git log`/`git branch --merged main`,
  not assumed from the handoff's own "not yet pushed" framing, which predates
  the merge)
- ~~**`docs/wiki-enforcement-catchup`**~~ ✓ ← this branch — pruned the chain's
  5 now-merged branches (3 local, 2 remote-stale-ref); ran a scoped
  `/wiki-self-update --since 55f7c1e` over the chain's own diff; **0 pages
  needed editing** (see "What just landed" below)
- **Next: item 45's fix branch OR sprint A1 — owner decision, not this
  handoff's to make.** See "First move" below. **Do not start either without
  the owner's explicit go.**

**The march is still deliberately paused. Do not touch epics B–E.**

**Item 10's release chain is still gated on epic 19** — untouched this session.

---

## What just landed on `main`

`main` was already at `c15d080` (PR #105, the pre-march chain merge) when this branch
started — verified, not assumed: `git branch --merged main` showed the chain's own case
branches (`chore/dependabot-groups`, `feat/verify-dont-assume-guard`,
`fix/plan-approval-marker-pr-merge` locally; `feat/flake-rate-measurement`,
`fix/chain-gate-integration` on the remote) already merged. **This session pruned all
five** (`git branch -d` locally; `git fetch --prune` cleaned the two stale remote-tracking
refs — GitHub had already auto-deleted the actual remote branches on merge).

**One git-mechanics correction worth carrying forward:** `c15d080` is a merge commit;
`git show --format=%P c15d080` lists its two parents as `55f7c1e f67943c` **in that
order**, and it is tempting to read the first-listed hash as the base (`main`) tip and the
second as the merged-in branch. That reading is backwards here — `git log --first-parent`
proved `55f7c1e` (PR #104, `main`'s own prior tip) is the true base, and `f67943c` is
actually the chain branch's own final commit. Diffing the wrong-order guess
(`f67943c..c15d080`) came back **empty** — a silent wrong answer, not an error — while the
correct `55f7c1e..c15d080` showed the real ~3,900-line chain diff. Recorded as
[[reference-merge-commit-parent-order-gotcha]] in durable memory since this project
mandates merge commits (squash/rebase disabled) and this will recur at every future
chain/PR close-out that needs to scope a diff off one.

**This branch's own two commits:**
1. `c69abee` — this session's own `consumed`-event provenance-ledger row
   (`docs/dev/ledger/2859b199-….jsonl`), folded in early per `docs/dev/prov/SPEC.md` §5
   step 3.
2. `3ac5ed8` — the scoped `/wiki-self-update --since 55f7c1e` result: **0 pages edited**,
   logged to `docs/wiki/log.md`. `scripts/wiki_relevance.py` classified exactly 2 of the
   chain's 32 changed paths as wiki-relevant (`CLAUDE.md`, `docs/governance/enforcement.md`)
   — confirming, not contradicting, the inherited handoff's claim (which named the
   *concepts* those two files carry — the `verify-binary-on-path` guard, the
   Bash-dispatcher fold, the `enforcement.md` reach declaration — not the guard/dispatcher
   source itself, which classifies irrelevant: `hooks/` and most of `scripts/` are
   wholesale agent-tooling, not product surface). Grepped every `docs/wiki/pages/*.md` for
   every name this content goes by (`verify-binary-on-path`, `verify_binary_on_path`,
   `bash-dispatcher`, `bash_dispatcher`, `claude_hook`, `PreToolUse`, `adapters/`) — no page
   cites any of it, so nothing to re-anchor, and per design-fork D5 a `CLAUDE.md` /
   `docs/governance/` change usually maps to no page. $0 scribe/auditor spend.
   `docs/wiki/.last_ingest_sha` **deliberately left unadvanced** (stays `65b0f88f…`,
   2026-07-30) — this run only covered the chain's own slice (`55f7c1e..HEAD`), not the
   full 93-commit gap back to the checkpoint, which prior branches have covered piecemeal
   via the lighter per-branch "scoped close-out relevance check" convention (log entries
   above this run's own) that inspects a branch's own diff without moving the formal
   checkpoint. Advancing it here would have misrepresented that gap as fully checked.
   Freshness verified still green: `python -m scripts.wiki_freshness` → **20 file(s)
   changed since the last ingest (< 75-file block threshold)** — exactly matches the
   inherited handoff's own "20/75 at chain close" figure; this branch's commits added no
   further wiki-relevant paths.

**Full gate at this branch's tip (foreground where possible; two steps exceeded the 600s
cap and ran backgrounded, sanctioned per RELEASE_ARC.md's march cadence — full read-back
below, not a skipped step), no reruns anywhere:**
- `python -m ruff check .` → all checks passed
- `python -m ruff format --check .` → 342 files already formatted
- `python -m mypy .` → Success: no issues found in 357 source files
- `python -m pytest -m "not ux" -n auto` → **2357 passed, 1 skipped** in 324.45s, grepped
  the full 15-line output for `rerun`/`RERUN` — zero matches
- `python -m pytest -m ux` (from the same background `python -m scripts.gate` run that
  first exceeded 600s) → **138 passed, 2358 deselected, 1 xfailed, 1 xpassed** in 578.66s
  (0:09:38), zero rerun markers in the captured tail
- `python -m scripts.work_items check` → OK (54 files)

**Wiki-relevance check (pre-close sweep item 0):** this branch's own diff IS the wiki-check
— see above. No further action needed.

**No dev server or long-lived background process from this session's own sartor work left
running** (both backgrounded gate steps completed and were read back). **Separately
observed, not this branch's to fix:** `tasklist` shows 4 `C:\Dev\spolia\.venv\...python.exe`
processes (`scripts/gate.py` ×2, `-m pytest` ×2) — a different project's own orphans, same
shape the prior handoff flagged (then just 1); confirmed via `wmic process ... get
CommandLine`, none started by this session or this repo.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

`docs/dev/work/BOARD.md` is the authoritative live-item source (regenerate with
`python -m scripts.work_items board --write`; not hand-edited). **Unchanged this
session** — this branch touched no work item, filed none, and closed none. Reproduced
verbatim from the board, not re-derived:

**Open (2):**
1. **45** — Plan-approval marker survives a PR-channel merge, leaving the plan gate open
   into the next session. `cleanup-plan-on-merge` fires only on local `git merge --no-ff`;
   close-out moved to `gh pr merge`, so the marker survives. Root cause proven, fix
   staged-not-built — owner sign-off required before a fix branch starts (see "First
   move").
2. **50** — C-7 and C-10 are enforced by Claude Code hooks only — the clauses do not
   travel to other agents or an extracted governance package. Guards are not routed by
   `git_hook.py`, so only Claude Code enforces them; prose binds other agents.

**Blocked (3):** item 3 ([HUMAN] GitHub toggles), item 5 (grounding-score persistence
gap), item 8 (Compose-time rewrite latitude dial).

**Deferred (7):** items 4, 7, 24, 25, 41, 42, 43 — all owner-gated or explicitly
post-1.1.0-scheduled; see `BOARD.md` for each.

**Watching (12):** items 2, 16, 18, 23, 46, 47, 48, 49, 51, 52, 53, 54 — see `BOARD.md`
for each; none touched this session.

**Epics (6):** 19 (UX-suite flakiness umbrella, children 27–31), 36 (Final March epic A,
children 20, 34 — open), 37/38/39/40 (Final March epics B/C/D/E — blocked, sequenced
after A per the march plan). Epic 39 carries item 9 (stale screenshots); epic 40 carries
item 10 (the v1.1.0 tag itself, `depends on: 3, 6, 7, 9, 19`).

**Closed (19):** unchanged this session — see `BOARD.md` for the full list.

Open-only count stays **2**, well under the reduction-sprint threshold.

---

## Recurrences observed this session → guardrail authored

**One recognized recurrence — a tool-usage habit, not a code defect, so the mechanism this
project can author is limited, and that limit is stated plainly rather than papered over
(C-11's own escape valve).**

1. **`ScheduleWakeup` called to poll a background Bash task's completion.** This session
   called `ScheduleWakeup` while waiting on a backgrounded `pytest -m "not ux"` run —
   despite an existing durable memory
   (`feedback-schedulewakeup-not-for-background-bash`, this project's own prior session)
   stating plainly that `ScheduleWakeup` is for `/loop` dynamic-pacing only, and that a
   background Bash task already notifies on completion without it. Recognized as a
   recurrence, not a first sighting, the moment it was reviewed. **No new mechanism
   authored — stated explicitly, per C-11, because this is not this repo's code to gate.**
   `ScheduleWakeup` is a harness tool outside `sartor.`'s own hooks/gate surface; nothing
   in `hooks/` or `scripts/enforcement/` can intercept a tool call the harness itself
   dispatches, and authoring one here would be scope creep on this branch besides. The
   honest answer is that a memory alone already proved insufficient once and remains the
   only mechanism available at this layer — surfaced to the user rather than silently
   left as "handled."

**Everything else this session** — the merge-commit parent-order confusion (a first
sighting, recorded as a new memory, not a recurrence), the wiki-checkpoint staleness gap
(already self-documented by the two-mechanism design log entries, not a new failure) —
was inspected and is not a recognized recurrence of a prior class.

---

## What this branch should build

**Nothing further — this branch's two deliverables are its complete scope, both done.**

1. **Prune the chain's now-merged branches** (queued by
   `fix/chain-gate-integration`'s own "Post-chain addendum," with the user's explicit
   confirmation this session): done — 3 local (`git branch -d`) + 2 remote-stale-refs
   (`git fetch --prune`, GitHub had already auto-deleted the actual remote branches).
2. **Run a scoped `/wiki-self-update` against the chain's own wiki-relevant diff**
   (same addendum): done — `--since 55f7c1e`, 2 relevant paths classified, 0 pages edited,
   logged to `docs/wiki/log.md`, committed at `3ac5ed8`.

**Scope is bounded to exactly these two items from `fix/chain-gate-integration`'s own
Post-chain addendum. Do not expand beyond what is listed there** — item 45's fix design
and sprint A1 are both explicitly deferred to the owner's decision, not folded in here.

---

## First move

**There is no single prescribed first move — the choice between two owner-gated paths is
not this handoff's to make:**

- **Item 45's fix branch** — only after the owner signs off on a fix design (see the
  staged proposal in `docs/dev/diagnosis/plan-approval-marker-pr-merge.md` §"The fix"; the
  owner has additionally directed that any reconciler must not silently *delete* approval
  state — favor archival + a ledger receipt over `rm`, preserving decision provenance).
- **Sprint A1** (`feat/corpus-polish` + `fix/experience-soft-retire`, epic 36) — per
  RELEASE_ARC.md's Final March cadence, "the next session starts from the epic branch with
  the owner's plan-approval click." Model prescription: **Opus** (schema migration +
  retired-role blast-radius audit).

Whichever the owner picks: write a plan at `~/.claude/plans/<slug>.md` and show it to the
user before touching any code. **Do not code first.**

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
