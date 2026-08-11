<!-- provenance: schema=1 session=24889186-748a-46ce-936c-8fcdf3e7fea6 branch=feat/prior-apps-pipeline commit=6917d30 actor=amodal1 agent=anthropic/claude-opus-5 generated_at=2026-08-10 -->

# Handoff — the governance interval between Epic A merging and Epic B starting

> **This is neither a sprint handoff nor an Epic B kickoff.** It hands over the
> governance/design work the owner's own directives (§12.0 in
> `docs/dev/epic-a-chain-design-corrections.md`) require to happen **after** Epic A
> lands on `main` and **before** any Epic B code sprint (`B1`) starts. Nothing here
> authorizes writing a line of Epic B application code. If you find yourself about
> to touch `templates/`, `static/app.js`, or a `blueprints/**` route for Epic B's
> own sake, you have left this handoff's scope — stop and re-read "What this branch
> should build" below.

**Branch to create:** `docs/pre-epic-b-review` (branch off `main`) — but **do not
create it as your first action.** The literal first move is reading, and putting
the item-1 question to the owner; branch only once there is something to commit
(a recorded decision, a review write-up, or the item-75 fix, which may want its
own separate `fix/*` branch — see "What this branch should build" #5).
**Base branch:** `main` — **but only once Epic A has actually landed there.** As of
this handoff's authoring (commit `6917d30`, branch `feat/prior-apps-pipeline` /
`epic/a-app-core`), Epic A is complete and PR-ready but **has not been pushed,
opened as a PR, or merged.** Do not assume the merge happened because this
document exists — confirm it (see "First move" step 0).

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

**Epic-A-specific reading, on top of the numbered list above — read every section
named, not a summary of it:** `docs/dev/epic-a-chain-design-corrections.md` §11
(the authorization envelope), §12.7 (stop 4 — the run stalled at a boundary the
vector doesn't end at), §14.7 (the delegation-seam probe result), and §15 in full
(the owner-scoped plan for Epic A's second half, including §15.6.1's recorded
hypothesis outcomes and §15.7's four preconditions). This handoff exists to check
those documents against the repo, not to restate them from memory.

**Stream:** v1.1.0 Final March (`docs/dev/RELEASE_ARC.md:1645`) — five epics, A→E,
strictly sequential.
**Sequencing rule:** strictly sequential — one epic at a time, code first (A–C),
docs after (D), release last (E). This handoff's work is **not itself an epic** and
carries no A/B/C/D/E label; it is the interval the owner's §12.0 directives created
between two epics.
**Blocked until this stream lands on `main`:** nothing new — Epics C, D, E (board
items 38/39/40) stay `blocked` behind B regardless of this interval's outcome. What
this interval actually gates is narrower and sharper: **Epic B's first code sprint
(`B1`) must not start until the owner has explicitly resolved item 1 below** (Epic
B has no authorization envelope), independent of whether Epic A has merged.

- ~~Epic A (`epic/a-app-core`, board 36)~~ — **pending merge confirmation, see
  First move step 0.** Four sprints (A1–A4) plus item 20's own `fix/*` branch, run
  as a six-branch stacked chain per the 2026-08-08 amendment to the cadence rule.
  32 commits, 124 files, +15,991/−798 (`git diff --shortstat main...HEAD` at commit
  `6917d30` against merge-base `52c821e`, re-verified by this session — exact
  match). Sprint tips: A1a `7c15c2e`, A1b `b8381f5` (repro) + `5474763` (fix), A2
  `2a0b37a`, item 20 `3e2b8a5`, A3 `7d3ff33`, A4 `3cfb98d`, plus `543917c` (the
  `BOARD_DEFERRAL.md` mechanism, built mid-epic and **retired at the epic close** —
  confirmed absent from `docs/dev/work/` by this session's own `find`).
- **This handoff** ← the governance/design interval. Not a Final March branch.
- Epic B (`epic/b-render-ats`, board 37) ← **blocked on item 1's resolution**, not
  just on Epic A landing. Do not start `B1` or any Epic-B branch from this handoff.
- Epics C, D, E (board 38/39/40) ← unchanged, still sequenced behind B.

**What must NOT be started on this branch:** any Epic B code (`B1` template
rendering work, `B2` ATS conformance); a new §11-shaped authorization envelope for
Epic B invented by analogy without the owner's sign-off (item 1); any instrument
from the withdrawn §14.1/§14.2 shape without re-litigating why they were withdrawn
(§14.5).

---

## What just landed on `main`

**Not landed yet as of this commit — this section describes Epic A's expected
shape, to be confirmed against the real merge commit, not assumed from this doc.**

Epic A (`epic/a-app-core`, board item 36): four sprints (A1–A4) plus item 20's own
evidence-gated `fix/*` branch, run as a six-branch stacked chain under the
2026-08-08 cadence amendment (`docs/dev/RELEASE_ARC.md:1675-1728`) and the §11
authorization envelope. **Independently re-verified by this session, not copied
from a prior summary:**

- `git diff --shortstat main...HEAD` at commit `6917d30`: **124 files changed,
  15,991 insertions(+), 798 deletions(-)**. Exact match to the incoming context.
- **32 commits** ahead of `main` (`git log --oneline main..HEAD | wc -l`).
- Sprint commits verified present with matching subjects: `7c15c2e` (A1a corpus
  reorder), `b8381f5` + `5474763` (A1b soft-retire repro + fix), `2a0b37a` (A2
  compose wait gate), `3e2b8a5` (item 20 rail gate), `7d3ff33` (A3 role-summary
  drafting), `3cfb98d` (A4 prior-apps → Pipeline), `543917c` (the `BOARD_DEFERRAL`
  mechanism).
- **The production/test/docs three-way split is only partially reconciled.** The
  incoming context claimed 2,565 production / 3,485 tests / 9,064 docs. This
  session's own re-categorization by path (`tests/` → tests, `docs/**` or `*.md` →
  docs, everything else `.py` → production, `static/`/`templates/` → other) gives
  **1,955 production(.py) / 3,485 tests / 9,389 docs / 1,162 other(static+templates)
  — insertions only, summing correctly to 15,991.** The tests figure matches
  exactly. The production/docs split does not reconcile cleanly against a
  by-path re-categorization (plausibly a different bucketing of `scripts/`,
  config, or non-`.py` production files in the original count). **Treat
  2,565/9,064 as approximate, not independently re-verified to the exact figure —
  the 124/15,991/798/32-commit/3,485-test facts above are the ones this session
  confirmed precisely.**
- Two confirmed findings from the final full-epic adversarial review: item 75
  (retired roles reach the A3 drafting prompt — see #5 below) and item 76
  (`BOARD_DEFERRAL.md`'s `declared` field had no expiry bound — filed and the
  marker itself retired at epic close).
- `epic/a-app-core` and `feat/prior-apps-pipeline` currently point at the same
  commit (`6917d30`) — the epic branch is cut but not pushed, per `git rev-parse`
  on both refs during this session.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

`docs/dev/work/BOARD.md` is the authoritative live-item source (regenerate with
`python -m scripts.work_items board --write`; `RELEASE_CHECKLIST.md`'s own former
prose ledger was formally superseded by it on 2026-07-28 — confirmed by reading
that file's own "Carry-forward ledger" section, which now points here). Reproduced
from the board **as this session read it at `6917d30`**, cross-checked against the
already-committed `docs/dev/handoffs/prior-apps-pipeline.md`'s own accounting
(written the same session as this HEAD commit) rather than re-deriving from
scratch, since the two are the same point in time.

**Open (4, under the 10 ceiling):** **9** (release/visual-assets refresh — stale
screenshots, under epic 39), **19** (UX-suite flakiness umbrella epic, children
27–31/57), **36** (Epic A itself — child 20 closed, child 34 still open), **50**
(C-7/C-10 are enforced by Claude Code hooks only — do not travel to other agents or
an extracted governance package).

**Blocked (8):** **3** ([HUMAN] GitHub toggles — repo rename, PyPI Trusted
Publisher, GHCR visibility, `enforce_admins`), **5** (grounding-score persistence
gap blocks calibrated L1/L2 metric layers), **8** (Compose-time rewrite latitude —
design landed, nothing built), **10** (the v1.1.0 release cut, depends on
3/6/7/9/19), and epics **37/38/39/40** (B/C/D/E — 37 depends on 36 and its
`blocked_on` reads "sequenced after epic A"; **verified this is prose only, not a
gate** — see item 1's own note below).

**Deferred (7):** **4** (in-app citation viewer), **7** (PX-46 selective memory
consolidation, owner sign-off required), **24** (template-preview fidelity spike),
**25** (`app.run(threaded=True)` governance decision, C-1-sensitive), **41**
(domain-vocabulary library, post-1.1.0), **42** (template-format investigation,
post-1.1.0), **43** (approved-fonts expansion, post-1.1.0). All owner-gated or
explicitly post-1.1.0.

**Watching (36 by frontmatter status — 8 new at Epic A's close):** items **2, 16,
18, 23, 30, 34, 46, 47, 48, 49, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63,
64, 65, 66, 67, 68**, plus **69–76 (new, filed across A3/A4/the epic close)**.
**Note on this session's own re-count:** `BOARD.md`'s rendered `## Watching`
section lists only 33 — it excludes items rendered nested under an epic heading
(30 under epic 19, 34 under epic 36), which are still `watching` by frontmatter but
not repeated in the flat section (documented behavior, not a bug: "an item filed
under an epic renders only inside that epic's own section"). 33 + {30, 34} = 35,
one short of 36 by this session's own recount — **not independently reconciled to
36 exactly; treat the flat-section 33 plus the two named epic-nested items as
independently confirmed, and the exact 36 as carried from the prior handoff's own
count rather than re-derived bit-for-bit here.**

- **Items 69–76 are new this epic.** 75 and 76 are the two confirmed findings from
  the final adversarial review (see #5 below and "What just landed"). 71 is the
  post-Epic-A review's own data-gathering pointer item (see #3 below).
- **Item 34 (corpus blueprints' `_get_client` unpatched in the UX harness) is still
  open, parented under Epic A (36).** Folded into the A3 brief but not confirmed
  closed — verify before treating Epic A as fully clean.
- **Item 58 carries a C-11 clock: a handoff amended after its `generated` stamp
  blocks the next session with no authoring-time warning.** This is exactly why
  this document is a **new** file rather than an edit to
  `docs/dev/handoffs/prior-apps-pipeline.md`.
- **Item 65 is the wiki-counter class** (measures "changed since checkpoint," not
  "coverage current"). See #3 below — directive 2(b) revisits this.
- **Item 52 is the gate-window-gap class** — the tree that lands is never quite the
  tree the gate examined. Six instances documented; still open.
- **The `watching` bucket is the item to flag hardest, again.** Growth across Epic
  A: 16 → 22 → 25 → 28 → **36**, per the already-committed epic-close handoff's own
  count — this session did not re-derive that five-point progression independently
  (no per-sprint board snapshots were re-read), only the current endpoint. It is
  not itself the reduction-sprint trigger (that ceiling applies to `open`, healthy
  at 4), but a bucket that has only grown, never been triaged, across an entire
  epic is exactly what charter W-1's carry-forward discipline exists to catch.
  Worth a triage pass on its own, independent of anything else in this handoff.

---

## Recurrences observed this session → guardrail authored

**One recurrence recognized; no mechanism authored, and here is why, stated
plainly rather than left implicit.**

While verifying item 1 (Epic B's missing authorization envelope) this session
checked `scripts/work_items.py`'s handling of `blocked_on` and `depends_on`
(`:290-292`, `:405-408`) to see whether board item 37 (Epic B) is actually
gate-prevented from being flipped to `open` before Epic A merges. It is not:
`blocked_on` is validated only for non-empty presence when `status` is
`blocked`/`deferred` (`:291-292`), and `depends_on` is validated only for
referential existence (`:406-408`) — nothing checks that a `depends_on` target is
`closed` before its dependent may leave `blocked`. **This is the same shape as
three things already on the board**: item 76 (`BOARD_DEFERRAL.md`'s `declared`
field asserted but never checked as a date), item 65 (the wiki-freshness counter
measuring the wrong proxy), and §11.12's own finding (halt points 2–5 have no hook
backing, only prose). A metric or a status field that *reads* as gated but is
enforced by nothing but the discipline of whoever edits it next — recognized here
as a fourth instance of a named recurring class, not a first sighting.

**No mechanism was authored on this branch.** This session's task explicitly
excludes modifying production code, tests, or any existing handoff — a
`work_items.py` guard (e.g., refusing a `blocked`→`open` transition while an unmet
`depends_on` target is not `closed`) is exactly the kind of change that scope
excludes. Per C-11: an undeclared gap is counted as protection by whoever reads
next, so it is surfaced here explicitly rather than silently left for the next
session to rediscover. **Recommendation, not an action taken:** the next agent
(or the owner) should decide whether this belongs in item 71's data-gathering
(same *asserted-but-unverified-precondition* shape item 71's own data point 2
already names) or as its own new work item — this document does not file one,
to avoid regenerating `BOARD.md` outside this task's stated scope.

---

## What this branch should build

**Nothing that is Epic B application code.** This interval's deliverables are
decisions and review write-ups, in the priority order the owner's directives set.

1. **Resolve the blocking question — owner-only, first.** Epic B has no
   authorization envelope. `docs/dev/epic-a-chain-design-corrections.md` §11 is
   self-described as a bounded **Epic-A** experiment (§15's own framing: "They
   remain **Epic-A-scoped**; lifting any of them into standing governance is the
   post-Epic-A decision," §15.1 preamble). §12.4 gates generalizing §11 on "a run
   completes with no stop" — Epic A took **four** stops (§12.1, including stop 4 in
   §12.7, and H-9 is recorded FALSIFIED at §15.6.1). **Do not start Epic B until
   the owner resolves this, and do not infer an envelope by analogy** — that is
   precisely the reasoning §11.3 already identifies as the defect behind stops 1
   and 2 (the design waiving the owner's own halt-point vocabulary). Nothing in the
   tooling blocks a premature start: verified this session (see "Recurrences"
   above) that item 37's `blocked_on`/`depends_on` fields are prose-and-existence
   checks only, not an enforced gate — **this is a discipline-only guard, and this
   handoff states that explicitly rather than letting an agent discover it by
   testing whether the edit is allowed.**
2. **§15.7's two still-unmet preconditions** (2 of 4 — PR-ready and H-6…H-9 are
   done per §15.6.1, already recorded):
   - **§14.7's adversarial pass on the delegation seam.** §14.7 overturns §11.9's
     stated reason for being unenforced: the PreToolUse payload *does* carry
     `agent_id`/`agent_type` inside a subagent (documented Claude Code hook
     fields), so the seam — "the orchestrator does not touch the working tree" —
     **is gateable**. §15.7 item 3 calls this "the highest-value unbuilt item," and
     requires its own adversarial pass before anyone writes a guard: at minimum,
     would an `agent_id`-gated guard have prevented any of the four stops, and what
     would it do to ordinary non-chain workflow. **Record the orchestrating
     session's own read here, for the reviewer to attack rather than silently
     inherit as settled: on this run's own evidence, no — stop 1 was hand-implementing
     plus a downgraded reviewer (a discipline failure a working-tree gate
     would not have stopped, since the orchestrator's OWN edits are exactly what
     it would have blocked, and it self-selected out of the envelope entirely by
     not reading it); stop 2 was ceremony consuming a whole session (a working-tree
     gate does nothing to close-out cost); stops 3 and 4 were a
     self-predicted context limit and a silent stall at a sprint boundary,
     neither of which touches the working tree at all. None of the four stops is
     addressed by a seam gate.** §14.6's own "standing caution" applies here too:
     a green path-level attribution check would acquire more authority than a
     line-level verification actually earned, and is least reliable exactly when a
     run is worst — any proposal in this space has to answer that, not just this
     session's read of the four stops.
   - **§15.3 lifted into `RELEASE_ARC.md`'s epic-planning section.** Verified
     absent as of commit `6917d30`: `grep -n "intra-epic close-out"
     docs/dev/RELEASE_ARC.md` returns nothing (exit 1). A chain epic's design must
     declare its intra-epic close-out intervals, or argue in writing for having
     none — Epic B's own design cannot satisfy a rule that does not yet exist in
     the planning document it would need to satisfy it in.
3. **The post-Epic-A review the owner scheduled (§12.0 directives 1–4, tracked by
   board item 71 — read that item's file in full, not just its one-line
   summary).** Due now:
   - **§11 generalization** (directive 1) — still gated by item 1 above; do not
     resolve this independently of it.
   - **Cite-rot governance + the false-drift log** (directive 2(a)) — §12.5's case
     log carries real rows now (7 entries as of this commit: 4 real drift, 2 false
     drift, 1 attribution-not-drift). Read them; the directive was explicit that
     governance should be written *from* the aggregated cases, not designed first
     and back-filled.
   - **The full wiki-freshness policy review** (directive 2(b)) — `.last_ingest_sha`
     is genuinely at HEAD for the first time in this document's own memory (advanced
     to `f42b2ea` at the epic close per the already-committed handoff; confirm the
     current value against `6917d30` before treating it as still zeroed — this
     session did not re-check it independently past reading that commit's own
     assertion). A working, un-backlogged baseline is exactly the condition
     directive 2(b) said this review should wait for.
   - **The delegation-seam write-up** (directive 3) — now informed by §14.7's probe
     result; see #2 above. Do not write this without item #2's adversarial pass
     first, since the write-up's central claim (gateable vs. not) is what #2 is
     testing.
4. **§14.6's corrected build order, if anything gets built at all.** F6
   (compaction telemetry) first and cheapest — a reporting script over `compacted`
   ledger rows already on disk (`docs/dev/ledger/*.jsonl`), not a new enforcement
   surface. **This session's own predecessor (the epic-close session) alone wrote
   at least 7 such rows** across the commits `0435e68`, `ade7b39`, `fab794d`,
   `f35b22d`, `f42b2ea`, and two more in the final commits (`937d91e`'s work and
   the immediately preceding `chore(prov)` commit) — count precisely before
   building, do not reuse "7+" as a citation. **Both instruments proposed in §14
   (`require-chain-briefing`, delegation attribution) were adversarially reviewed
   and WITHDRAWN (§14.5)** — a future proposal in this space must answer, in
   writing, why it is not the same shape as either rejected draft (§14.5's four
   numbered reasons each proposal died, and the two findings about the proposals'
   own honesty at the end of that section).
5. **Item 75 is the fix-first defect, and it is its own small `fix/*` branch, not
   part of this document.** A soft-retired role's text still reaches the A3
   drafting prompt: `blueprints/applications.py`'s
   `_build_experience_summary_targets` (docstring at `:2709-2710`, function at
   `:2699` as of this commit — re-verify line numbers before citing them, this
   file will have moved once Epic A merges) reads the **frozen** analyze-time
   `career_corpus` snapshot and never intersects it against live
   `Experience.is_active`. The sibling gap-fill lane
   (`draft_application_gap_fill`) filters on live `is_active=1` at the same seam;
   A3's lane did not get the same treatment. **The docstring's claim that the
   effective-bullet rule "mirrors `corpus_to_json_resume.build_json_resume_from_corpus`
   exactly" is false as written — confirmed by this session reading both
   functions — because that function reads the live DB and this one reads the
   frozen snapshot.** Per the item's own filed instruction: **the docstring must
   not be corrected alone.** The docstring describes the intended, correct
   behavior; the code is what's wrong. Fix both together, in the same commit,
   by intersecting the frozen snapshot against live `is_active` (mirroring the
   `cand_exp_ids` pattern already proven in the gap-fill lane). Blast radius is
   traced and bounded in the item's own filing — a retired role never renders a
   card and cannot be kept, so the live defect is wasted Sonnet tokens and an
   inert prompt entry, not a user-visible leak. Not urgent, but real, and it is a
   normal `fix/*` branch (its own diagnosis dossier, C-7 evidence — the defect is
   traceable by reading, but write a failing test demonstrating a retired role
   reaching the prompt before fixing it, not just a plausible-mechanism narrative).
6. **Flag the `watching`-bucket trend to the owner** (see Carried-forward
   observations above) as a standing recommendation, not a task this branch
   executes unilaterally — a triage/reduction session, scoped separately.

**Scope is bounded to items 1–5 above** (§11/§15.7's blocking question and its two
preconditions, item 71's post-Epic-A review directives, and item 75's fix as its
own branch) **plus item 6 as an escalation, not an execution.** Do not expand
beyond what is listed here — in particular, do not begin any Epic B sprint
(`B1`/`B2`, board item 37 or its children) on this branch or any branch spawned
from it.

---

## First move

0. **Confirm Epic A actually landed on `main` before treating anything above as
   settled fact.** This handoff was authored while Epic A was still on
   `feat/prior-apps-pipeline` / `epic/a-app-core`, unpushed. Check
   `git log --oneline -1 main` and `git branch --contains <epic/a-app-core tip>`
   (or the equivalent PR-merge record) — if the merge has not happened, that is
   itself the first surfaced fact, and this handoff's "What just landed on `main`"
   section is a forward description, not a confirmed state.
1. If this handoff arrived via a pointer, run
   `python scripts/check_handoff_pointer.py "<pointer line>"`, then
   `python scripts/verify_doc_template.py docs/dev/handoffs/pre-epic-b-intermediate-steps.md
   docs/dev/AGENT_HANDOFF_TEMPLATE.md --event consumed --agent <your-agent-id>`. A
   `blocked` result is your **first output** — STOP (charter C-9).
2. Read `docs/dev/epic-a-chain-design-corrections.md` §11, §12.7, §14.7, and §15 in
   full — not a summary, not this handoff's citations of them.
3. **Put the envelope question (item 1 above) to the owner before doing anything
   else.** Do not draft a candidate envelope, do not start §15.7 item 2's
   adversarial pass, and do not start the post-Epic-A review write-ups until the
   owner has responded. Silence on this question is a stop, not a licence to
   proceed by the same reasoning §11.4 and §12.7 already state for the chain
   itself.

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
