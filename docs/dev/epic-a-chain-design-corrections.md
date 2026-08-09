# Epic A chain — design corrections recovered from an interrupted session

> **Purpose:** the durable record of an adversarial review of the Epic A
> stacked-chain design, plus two supporting audits, recovered from a session
> that a Windows restart killed before any of it reached disk.
> **Audience:** whoever runs Epic A sprints A1–A4, and anyone auditing why
> `docs/dev/RELEASE_ARC.md`'s cadence rule was amended.
> **Authoritative for:** the eight corrections to the design captured in
> [`docs/dev/handoffs/docs-epic-a-wave-orchestration-design.md`](handoffs/docs-epic-a-wave-orchestration-design.md).
> That handoff remains the design's statement of intent; this file is the
> errata that supersedes it where the two disagree.

---

## Provenance — how this document exists

Session `5bf3d463-0b5d-47ae-bea6-b2682a77f56f` (2026-08-08, 05:50–06:16Z) consumed the
Epic A wave-orchestration handoff, entered plan mode, and ran three subagents: two
read-only `Explore` passes and one adversarial `Plan` reviewer instructed to refute. It
was mid-verification of the reviewer's first CRITICAL finding when a Windows restart
ended it. It never reached `ExitPlanMode`, so it produced **no branch, no commit, and no
document** — only an untracked `consumed` ledger row.

The findings below were recovered by a later session (`808060be-…`, same day) from the
dead session's own transcript at
`~/.claude/projects/C--Dev-sartor/5bf3d463-0b5d-47ae-bea6-b2682a77f56f.jsonl`, by
extracting the `tool_result` payloads for the three `Agent` calls.

**This is the second instance in two days of a design worked out in context and lost
before it was written down** — the first is recorded in that same handoff's own
"Recurrences observed this session" section, which was itself authored to fix instance
one. The recurrence is what motivates writing this file before anything else happens.

---

## Verification status — read this before citing anything below

Per charter **C-12**, every claim carries how it is known. Three levels are used:

| Tag | Meaning |
|---|---|
| **[VERIFIED]** | Re-checked directly against live state or source by the recovering session, independent of the subagent that first reported it. |
| **[REPORTED]** | Rests on the subagent's report alone. Plausible and specific, but *not* independently re-checked. Treat as a lead, not a fact. |
| **[INFERRED]** | A mechanism proposed to explain an observation. Unproven. Must not be cited as cause. |

A **[REPORTED]** finding is not evidence under C-7. Anything acted on in a sprint needs
its own confirmation first.

---

## The eight findings

### 1. CRITICAL — the inherited stamp destroys the single approval before A1 writes a line

**[VERIFIED]** — re-confirmed against live state during recovery:

```
.approved-branch-C--Dev-sartor  →  branch=docs/epic-a-wave-orchestration-design
                                   base=cd83a2b…
main ref mtime 22:48:35  >  stamp mtime 22:47:37        → NEED_CHECK=1
tip 96f3a4d: ancestor of main = YES   ancestor of base = NO (rc=1)
```

That drives `_should_archive` (`hooks/check-plan-approved.sh:132-160`) true, so the next
production edit fires `retire_approved_plan` and `exit 2`. Because the handoff's "First
move" orders the ceremony *before* the first edit, the marker at that moment points at
the **brand-new Epic A plan** — and `hooks/lib/retire-approved-plan.sh:84` does `mv -f`,
physically relocating it into `archive/`. The result is a second full ceremony and a plan
that has to be rewritten.

Pruning `docs/epic-a-wave-orchestration-design` does not help: `_should_archive` returns
true both for "branch gone" (`:139-140`) and for "merged past fork point" (`:156`).

**Correction — ordering, not a new mechanism.** Take one throwaway production edit
**before** `EnterPlanMode`. It is blocked with `PLAN RETIRED` — the designed behavior —
and flushes the stale stamp harmlessly. Then run the ceremony once. On the following edit
`_read_stamp` finds `STAMPED_BRANCH=""` (`:188`), skips reconciliation, and late-binds to
the current branch (`:228-235`).

**See finding 9 — the flush must happen on the branch, not on `main`.**

### 2. CRITICAL — the per-sprint loop commits the pre-fix tree

**[REPORTED]** — specific and checkable, but not independently re-run during recovery.

The design's loop is: gate → stage → review staged diff → fix findings → re-review →
commit. `Edit` writes the **working tree**; nothing re-stages; `git commit` without `-a`
commits the **index** — the snapshot taken before the reviewer's findings were fixed. The
guard that would normally catch this is blind to it:
`scripts/enforcement/guards/ruff_changed.py:84` calls `gitutil.staged_files()`, which runs
`git diff --cached` (`scripts/enforcement/gitutil.py:48`) — it lints the stale index and
passes.

Two further holes in the same window:

- The gate is never re-run after the fixes. `scripts/gate.py` runs everything against the
  **working tree**, never the index — so the tree that lands was never gated. This is
  verbatim item 52 (`docs/dev/gate-window-class-study.md`), which the design claims to
  fold in while reproducing it.
- Filing lower-severity findings to the board **after** the gate leaves a stale
  `BOARD.md`, and `scripts/work_items.py` fails on that inside `scripts/gate.py` — so the
  next sprint's gate, or the epic PR's CI, goes red on it.

**Correction — invert the last two steps and make staging total:**

1. implement → `git add -A`
2. adversarial review of the **staged** diff (+ the item-52 structural re-check)
3. fix confirmed findings → **`git add -A` again**
4. file deferred findings → `python -m scripts.work_items board --write` → `git add -A`
5. **now** run `python -m scripts.gate` (working tree == index)
6. assert the window is closed: `git diff --quiet` **and** an empty
   `git status --porcelain --untracked-files=all`
7. `git commit`

Step 6 is the actual mechanism. Without it this is vigilance, not enforcement.

### 3. HIGH — the topology contradicted a committed, owner-approved cadence rule

**[VERIFIED]** — `docs/dev/RELEASE_ARC.md:1671-1674` read directly and confirmed verbatim:

> **One sprint = one branch = one session**, owned end-to-end (charter W-1.3), with the
> full per-branch close-out checklist — no lightened ceremony. The sprint branch merges
> into its epic integration branch as the session's **final act**; the next session starts
> from the epic branch with the owner's plan-approval click.

The stacked design overrode both halves — zero intermediate merges, and one approval for
the whole chain — while citing only `:1681` ("One PR per epic to main"), which it does
match. The handoff's own reading order calls RELEASE_ARC "the durable plan. Do not
deviate without user sign-off."

**Resolution — owner decision, 2026-08-08:** amend `RELEASE_ARC.md` to sanction the
stacked shape for Epic A as a bounded experiment. Landed on this branch. This is *not* a
general reversal of W-1.

Also priced in, and still true after the amendment: `:1671`'s "full per-branch close-out
checklist — no lightened ceremony" means **five** close-outs — five handoff files, five
`verify_doc_template.py` runs, five gate runs. `AGENTS.md` states these steps have no
escape hatch. The per-sprint loop as originally described covered none of it.

### 4. HIGH — A2 and A4 hit an unanticipated C-10 block on `ui_pages/selectors.py`

**[REPORTED]**, with one **[VERIFIED]** supporting fact: `ui_pages/selectors.py` is
indeed in the gated registry in `scripts/enforcement/blast_radius.py`, and it is not
covered by the `tests/` exemption.

- **A2** changes the `data-compose-ready` settle contract — `ui_pages/selectors.py`
  `READY` / `SETTLED`.
- **A4** removes the Prior Applications panel — `class PriorApps`, which
  `tests/ux/regression/test_20260707_recruiter_roster_pipeline.py` imports directly.

`RELEASE_ARC.md` called out the dossier requirement for **A1 only**. A4 is the *Sonnet*
sprint — the least-equipped implementer meeting a no-escape-hatch gate with no brief
coverage.

**Correction:** write the requirement into each sprint's brief. A2 →
`docs/dev/blast-radius/compose-wait-ux.md`; A4 →
`docs/dev/blast-radius/prior-apps-pipeline.md`; both must literally name
`ui_pages/selectors.py` in `## Consumers`. Branch-slug derivation strips the first
`<type>/` and flattens the rest, and C-10 applies on **every** branch type, not just
`fix/*`.

### 5. HIGH — folding item 20 into `feat/compose-wait-ux` silently switches off C-7

**[REPORTED]**, mechanism specific: the evidence guard returns `allow()` unless the branch
name starts with `fix/`. On a `feat/*` branch the C-7 gate never runs — no diagnosis
dossier, no `## Observed`, no citation check — for a change `RELEASE_ARC.md` itself labels
an *evidence* fix. `:1678` is explicit that "integration fixes get their own `fix/*`
branch + diagnosis dossier."

Disabling a hook by choosing a branch name is the thing Binding rule 3 prohibits, whether
or not it was intended.

**Correction:** keep item 20 on its own `fix/*` branch stacked between
`feat/compose-wait-ux` and `feat/role-summary-drafting` — six branches, not five. Same
pattern A1 already uses.

### 6. MEDIUM — wiki drift is monotonic across the epic and can redden the gate

**[VERIFIED]** — `python -m scripts.wiki_freshness` re-run during recovery reports **20
files changed against a `BLOCK_THRESHOLD` of 75**.

With zero intermediate merges, HEAD accumulates all four sprints, so drift only grows.
Epic A touches `templates/index.html`, `static/app.js`, `db/models.py`,
`db/migrations/**`, `corpus_to_json_resume.py`, `blueprints/corpus/*`, `analyzer.py`,
`ui_pages/*` and eval fixtures. **[REPORTED]** estimate: plausibly 40–60 wiki-relevant
files, making a threshold crossing by A3/A4 a live risk — and it lands as a gate failure
with no code cause, mid-sprint.

`RELEASE_ARC.md:1693-1694` already mandates the countermeasure (the per-sprint
wiki-relevance close-out check); the per-sprint loop as described omitted it.

**Correction:** run the wiki-relevance check + scoped `/wiki-self-update` in every
sprint's close-out, and use `python -m scripts.wiki_freshness` as a cheap pre-commit
tripwire.

### 7. MEDIUM — `epic/a-app-core` cannot stay a bare ref through close-out

**[REPORTED]**. Creating the epic branch as a ref is fine, and a PR from it behaves
normally. But the epic's own close-out artifacts — the CHANGELOG entry, the final handoff,
the ledger row, any fix from the final review — have to be committed somewhere. Committing
them on `epic/a-app-core` makes it diverge from the last sprint tip, and `RELEASE_ARC.md`
forbids production-code edits on an `epic/*` branch, so a final-review finding needs
another stacked `fix/*` plus a `git branch -f` re-point that nothing in the design covers.

**Correction:** decide before the chain starts — either the epic close-out docs land on
the **last sprint branch** before the ref is cut, or `epic/a-app-core` is created early and
each sprint tip is fast-forwarded onto it, with the re-point step written down.

### 8. LOW — editing the approved plan file mid-chain hard-blocks every later edit

**[VERIFIED]** by reading `hooks/check-plan-approved.sh:57-61`: if the approved plan file
is newer than the marker, every production edit is blocked until a fresh `ExitPlanMode`.

`~/.claude/plans/**` is exempt from every *other* guard, so updating the plan with sprint
progress feels free. It is not.

**Correction:** the approved plan file is **frozen** for the duration of the chain.
Progress goes in the ledger, `BOARD.md`, and commit messages.

---

## 9. NEW — plan retirement half-completes on `main`, leaving the poison in place

Found while *executing* finding 1's correction, not by the original review.

**[VERIFIED] — observed:** attempting the flush `Write` while still on `main` created
`~/.claude/plans/archive/20260808T153444Z-142537ca4cdd` **empty**, while
`.approved-C--Dev-sartor`, `.current-C--Dev-sartor`, `.approved-branch-C--Dev-sartor` and
the plan file itself all survived. Since `hooks/lib/retire-approved-plan.sh:161` removes
all three pointer files unconditionally, the function was killed between the `mkdir` on
`:84` and that `rm`. The only block message reported was `require-feature-branch`.

**[VERIFIED] — observed contrast:** the identical `Write` **on the feature branch** retired
cleanly — archive dir containing `manifest.json` *and* the plan file, all three pointers
cleared, and a `plan-archived` ledger receipt written.

**[INFERRED] — unproven, must not be cited as cause:** the harness terminates the sibling
hook once one guard exits 2. The competing explanation is the 5 s hook timeout in
`.claude/settings.json`. Neither was tested.

**Consequence, regardless of mechanism:** on `main` the reconciler cannot complete. It
leaves the stale approval live and litters one empty archive dir per attempt.

**Correction:** create the branch **first**, then take the flush edit on it. Tracked as
work item 56.

---

## 10. NEW — gating a STAGED tree passes vacuously for every check that reads `HEAD`

Found by this branch's own CI going red after its own gate went green. **The only finding
in this document with a deterministic local reproduction rather than a report.**

**[VERIFIED] — observed, three times, in both directions:**

| Run | Tree state | `HEAD` | Result |
|---|---|---|---|
| Local `pytest -m "not ux"` | staged, uncommitted | `d9c9f6f` | 2376 passed — **vacuous** |
| CI (py3.11 / 3.12 / 3.13) | committed | `fced8e9` | **all three failed**, same assertion |
| Local `pytest -m "not ux"`, re-run | committed | `fced8e9` | **1 failed** — reproduced exactly |

The failure: `tests/test_wiki_relevance_classification.py::test_every_top_level_entry_is_classified`
— `Unclassified top-level entr(y/ies) for wiki-relevance:
['docs/dev/epic-a-chain-design-corrections.md']`.

**[VERIFIED] — mechanism, read from source, not inferred:** that test enumerates through
`_git_tree_entries()`, which shells out to **`git ls-tree HEAD:<dir>`**. It reads committed
`HEAD` — not the index, not the filesystem. A file that is staged but not committed is
invisible to it, so the check passes by finding nothing to complain about.
`scripts/wiki_freshness.py` has the same property via
`git diff --name-only <last_ingest_sha> HEAD`.

**Why this matters beyond one red build.** Finding 2 above prescribes a per-sprint sequence
ending "…gate → assert the window is closed → commit." That ordering is **insufficient**,
and this branch proved it by following it and shipping a red PR. The assertion it
recommends (`git diff --quiet` + empty `git status --porcelain`) is still correct and still
necessary — it just cannot catch this, because index and working tree genuinely *did*
match. The gap is between the index and `HEAD`.

**Correction — a second gate run, after the commit.** `RELEASE_ARC.md`'s amendment now
carries it. Cheap in practice: the second run is the one that matters, and on a docs-only
branch the expensive UX tier can be reasoned about separately (this branch's diff contained
zero Python).

**This is the item-52 gate-window class with the polarity flipped.** Item 52 is about
artifacts mutating the tree *after* the gate. This is the tree being *behind* the gate's
own reads — same class ("the tree that lands is never the tree the gate examined"), a
direction the class study does not currently cover.

**Recurrence, honestly labelled:** the identical guard fired for the identical reason on
PR #105 nine days earlier (`docs/dev/blast-radius/chain-gate-integration.md`, run
31114143878) — a chain-close pass creating a `docs/dev/*.md` file without classifying it.
The guard failed closed both times, which is it working. What recurred is the **author-side**
gap: nothing warns at authoring time, so you learn from a red CI job. No fail-closed
mechanism was authored for that here, and the reason is written into
`docs/dev/blast-radius/epic-a-chain-design-corrections.md` rather than left implicit.

---

## 11. NEW — the chain had no authorization envelope, and the governance around it defaults to STOP

Found by the third orchestrating session (2026-08-09), before it ran anything, after the
owner reported that no session had yet run a sprint without stopping. **Owner-approved the
same day**; this section is the sanction, not a proposal.

### 11.1 Observed — why the first two attempts ended

**[VERIFIED]** by reading both session transcripts under
`~/.claude/projects/C--Dev-sartor/`, counting `tool_use` blocks directly:

| | `c42da573` (A1a + A1b start) | `d05ae572` (A1b close) |
|---|---|---|
| Wall clock | 2026-08-08 17:57Z → 08-09 02:02Z (~8h) | 02:04Z → 06:05Z (~4h) |
| Own `Edit`/`Write` | 16 / 8 — **implemented A1a by hand** | 24 / 6 |
| Implementer `Agent` launches | **1** (A1b) | **0** |
| Other agents | 0 | Sonnet refuter, opus fix-applier, **14 wiki scribes/auditors**, gate-fix agent |
| Full gate runs | ≥3 (1 killed) | ≥4 (1 killed) |
| How it ended | **owner interrupt** | **owner interrupt** |

Neither session ran out of context, compacted to death, or crashed. **Both were
interrupted by the owner**, whose final message in each names the symptom verbatim:

> `c42da573`: *"find what you lost and try to get on the right page and then handoff to an
> agent to run the thread"*
>
> `d05ae572`: *"this was supposed to be an epic that hands off to a fresh agent each sprint
> with a single agent orchestrating, but you have yet to run a single sprint without
> stopping. what is wrong?"*

Twelve hours across two sessions produced **1.5 of the chain's 6 branches**.

### 11.2 Falsified — "the orchestrator cannot afford to read four sprint diffs"

This session's own first hypothesis, killed before it was acted on. A1b's diff is 2,126
lines, which looks fatal for a context that must survive four sprints. The split does not
support that reading (`git show --numstat 5474763`):

```
docs 761  |  tests 273  |  production code 392
```

~400 lines of real code per sprint is roughly 10k tokens — an epic-long orchestrator is
comfortably affordable, and W-1's line-level verification duty is **not** the binding
constraint. Recorded here so the next session does not re-derive it.

### 11.3 The mechanism — mandatory stops, with nothing saying which ones are real

An agent running this chain is bound by a dense set of correct, individually-justified
stop conditions: a hook block is *"surface the hook name and its message, and STOP"*
(Binding rule 3); C-9 makes corrupted input a blocked gate; C-12 requires announcing a
gap; `RELEASE_ARC.md`'s own cadence rule says *"discoveries are filed, never chased;
release-blocking discoveries stop the session and surface to the owner"* and *"hook
blocks, gate failures after two honest attempts, or intent ambiguity: stop, write state
durably, surface"*; and the per-sprint close-out is explicitly *"no lightened ceremony"*
with no escape hatch.

Every one of those is right for a single branch. Stacked four sprints deep with **no
statement of what the orchestrator may decide on its own**, they guarantee several
mandatory stops per sprint — which is exactly what the owner observed twice.

The missing vocabulary is not novel: the owner authored it on **2026-08-06** (run vector,
halt points, handbacks, flag stops, resume protocol, *"fail-closed scoping: silence =
stop, not proceed"*). The Epic A design then **explicitly declared it not a precondition**
for this run:

> *"not contingent on the broader 2026-08-06 governance directives (written chain-sanction
> grammar, halt-points / handbacks / flag-stops vocabulary) landing first"*
> — `docs/dev/handoffs/docs-epic-a-wave-orchestration-design.md` §"The design"

**That waiver is the defect.** Per-agent drift is real and additional — A1a was implemented
by hand, the mandated Sonnet reviewer was downgraded once — but drift alone does not
explain two independently-briefed sessions landing in the same place.

### 11.4 The run vector (ordered scope, fail-closed)

```
A2  feat/compose-wait-ux        → item 20  fix/*  → A3  feat/role-summary-drafting
 → A4  feat/prior-apps-pipeline → final Opus xhigh review over the full epic diff
 → epic/a-app-core cut from A4's tip → STOP, hand the PR decision to the owner
```

Anything not on this vector is **out of scope by default**. Silence is a stop, not a
licence: a question the vector does not answer is a flag stop (11.6), never an assumption.

### 11.5 Halt points — unconditional, no judgment involved

The chain stops and waits for the owner at each of these, every time:

1. **Any `git push`, PR creation, or merge.** The epic lands as one owner-gated PR. Nothing
   goes to a public remote without the owner stating what becomes public and approving it.
2. **Any schema, security, or architecture decision not already settled** in the ARC brief,
   the design, or this errata. (Reaffirms `AGENT_FAILURE_PATTERNS.md` 5c.)
3. **Anything that contradicts a recorded owner decision** — the corpus section order, the
   epic close-out shape, the frozen plan file, the model table. Surface the conflict; never
   self-resolve it.
4. **A release-blocking discovery**, per the existing cadence rule.
5. **Branch pruning**, per standing feedback.

### 11.6 Flag stops — conditional; "need a human if I hit this"

1. The gate is red after **two honest attempts** on the same cause.
2. A hook blocks and the block **cannot be cleared by doing the work it asks for** (writing
   the dossier, writing the observation). A hook cleared by doing the work is not a stop —
   it is the hook functioning, and the run continues.
3. An adversarial reviewer returns a **CONFIRMED** correctness/regression finding whose fix
   would **change the sprint's scope** rather than correct its implementation.
4. Evidence required by C-7 **cannot be obtained** — the defect will not reproduce, or the
   instrument would have to be scoped to the hypothesis.
5. A **C-11 recurrence** arises whose fail-closed mechanism would be a new enforcement
   surface (that is itself a scope change, and the owner decides).
6. Context runs thin enough that C-8's handoff trigger fires.

### 11.7 Handbacks — owner executes as a normal sprint

**None for A2, item 20, or A3.** A4 is the owner's option to take as a normal sprint
(the 2026-08-06 directive's own worked example); if not exercised, A4 runs on the vector
like the others.

### 11.8 Inside the envelope — the orchestrator decides alone and keeps moving

Everything the halt points and flag stops do not name. Explicitly including: implementation
approach within a sprint's brief; which findings block a commit versus get filed to
`BOARD.md`; dossier content and structure; test design; how to resolve a gate failure whose
cause is understood; whether a discovery is in-scope-and-small or filed. These get **decided
and recorded**, not surfaced mid-run. The owner reads the record afterward.

### 11.9 The delegation seam — the orchestrator does not touch the working tree

The design delegated the cheap part (≈400 lines of code) and kept the expensive part (two
full gate runs, a 14-subagent wiki loop, a ~480-line handoff, dossiers, BOARD, ledger) in
the one context that must survive longest. `d05ae572` is the proof: a whole session spent
on one sprint's close-out with the code already written by someone else.

**Corrected seam — three fresh agents per sprint:**

1. **Implementer** (model per the design's table) — branch, blast-radius dossier, diagnosis
   dossier if `fix/*`, code, tests, `git add -A`. Reports; commits nothing.
2. **Sonnet refuter** — reads the **staged** diff, instructed to refute, folding in item
   52's structural re-check (doc links, hook modes, `python -m scripts.work_items check`).
3. **Orchestrator** — reads the real code+tests diff, judges the refuter's findings, decides
   block-vs-file. This is the judgment pause the design exists to protect.
4. **Closer** — applies confirmed findings, files deferred ones, regenerates `BOARD.md`,
   commits, runs the gate on the committed tree, runs the wiki-relevance close-out, writes
   the next sprint's handoff and validates it.

The orchestrator's own writes are confined to **this file and the governance amendments it
sanctions** (`RELEASE_ARC.md`'s cadence rule). Every other tracked change on an Epic A
branch — production code, tests, dossiers, `BOARD.md`, handoffs, wiki pages — arrives
through a subagent.

**Unenforced — labelled as C-11 requires.** No gate distinguishes a main-session `Edit`
from a subagent's, so 11.9 is prose discipline, not a mechanism. The falsifiable check the
owner can run cheaply: at each sprint's review point every changed file must be accounted
for by the implementer's own report; a tracked file that no subagent reports having written
means the run has drifted back to hand-implementation. Building a real gate here would be a
new enforcement surface mid-chain — a flag stop under 11.6.5, not something to take
unilaterally.

### 11.10 Resume/pickup protocol

If this session ends before the vector completes, the next one is **not** a fresh
orchestrator improvising: it verifies the pointer, consumes the handoff, reads
`docs/dev/handoffs/docs-epic-a-wave-orchestration-design.md` **in full**, reads this file
in full, and resumes at the vector position the last handoff names. The envelope above
carries forward unchanged — it does not need re-approving.

### 11.11 The wiki freshness ratchet was never zeroed, so it cannot engage

Found 2026-08-09 by the third orchestrator, after the owner asked why incremental wiki
updates were not happening per commit. **They are happening. The checkpoint advance is
not, and that is the whole problem.**

**[VERIFIED] — observed:**

- `docs/wiki/.last_ingest_sha` is `65b0f88f…` — **2026-07-30, 132 commits behind HEAD**.
  Last advanced in `b50abec`; `git show --stat 5474763` confirms A1b did not touch it.
- `python -m scripts.wiki_freshness` reports **36 wiki-relevant files** against the
  75-file block threshold. The 36 span ~10 days and include `db/models.py`,
  `blueprints/corpus/experiences.py`, `corpus_to_json_resume.py` and `db/build_context.py`
  — files A1b's own wiki pass documented.
- A1b did **not** skip the work: `docs/wiki/log.md` records 7 pages written, 3 verified
  no-edit, 4 auditor findings repaired, 2 missed classes disclosed.

**Mechanism — not neglect, a correctly-reasoned refusal.** A1b declined the advance under
C-12 and wrote why: *"This pass inspected one branch's slice; advancing the checkpoint
would assert the whole backlog had been ingested."* That is right. `.last_ingest_sha` is a
single repo-wide "everything up to here is ingested" marker, and a scoped per-branch pass
cannot honestly claim it.

**The fault is structural.** Item 35 (2026-08-04) made small per-branch incremental
updates the norm, but `drift = files changed since .last_ingest_sha` still assumes
periodic full catch-up passes. So correctly-ingested work inflates the counter — A1b said
this in its own log — and every honest agent declines the advance, which grows the backlog,
which makes the next refusal more certain. **A ratchet that was never zeroed cannot
engage.** Left alone the counter reaches 75 mid-chain and reddens a sprint gate with no
code cause: drift is 36 now and the errata's finding 6 estimates Epic A at 40–60
wiki-relevant files.

**Decision, owner-directed 2026-08-09 ("we should be making incremental wiki updates each
commit now").** A2's closer runs the wiki pass **widened to the full `65b0f88`→HEAD
delta** and advances `.last_ingest_sha`. One pass rather than a scoped pass now plus a
catch-up branch later, and it zeroes the ratchet permanently: from A3 onward the checkpoint
sits at the previous sprint's tip, so each sprint's own slice **is** the whole delta and
its closer can advance it honestly and cheaply. That is the per-commit behavior the owner
asked for, and it only becomes available once the backlog is cleared.

**To file as a work item** (the closer owns `BOARD.md`): the counter measures "changed
since checkpoint", not "wiki coverage current", so it will re-diverge from the incremental
workflow the moment a pass is scoped narrower than the checkpoint gap again. Zeroing it
here fixes this instance, **not the class**.

### 11.12 Known limits (C-0)

This section makes the stop conditions **explicit and finite**. It does not make them
correct, and it cannot stop an agent from stopping on something it should have decided, or
deciding something it should have surfaced. It is a written envelope, not a mechanism —
except for 11.5's halt points, which coincide with hooks that already fail closed
(`block-merge-to-main`, `require-feature-branch`).

---

## A1 citation-drift audit — `RELEASE_ARC.md` sprint A1 brief vs. HEAD `d9c9f6f`

**[REPORTED]** throughout. Re-verify any line number before editing against it.

| Cite | Status |
|---|---|
| `templates/index.html:700-845` (corpus section order) | Range exact; **described order wrong** — see below |
| `static/app.js:4392-4439` (education row) | Exact match |
| `static/app.js:254-283` (`.pipeline-row`, also A4's cite) | Exact match |
| `static/app.js:4945-4976` (role-card render order) | Exact match; today's order is summary-field → titles → bullets → intro variants |
| `db/models.py:88-108` (`Experience`) | Claim correct (**no `retired` column**); range should be **`88-124`** |
| `blueprints/corpus/experiences.py:256` (retire handler) | Exact match |
| `corpus_to_json_resume.py:176-181` (unfiltered consumer) | Exact match |

**Citation 1 in detail.** The real DOM order inside `#panelCorpus` is Summary variants →
**Skills → Education** → **Certifications** → roles list. The brief implies
"Summary/Education/Skills", which is wrong on the Skills/Education ordering, and it omits
the **Certifications** section entirely — a fourth section sitting between Education and
the roles list that the A1 reorder does not account for. "Roles render last" is correct.

**Path nit:** alembic revisions live in `db/migrations/**versions**/`, not
`db/migrations/`. The most recent is `0015_application_index_add_is_active.py`.

**Precedent to follow, confirmed present:**
`db/migrations/versions/0011_experience_title_is_active.py` uses a `PRAGMA table_info`
idempotency guard plus a **native `op.add_column`**, deliberately not `batch_alter_table`,
because the table is a parent and a batch recreate would cascade-delete children. The same
rationale applies verbatim to `experience`.

---

## Appendix — recovered `Experience` consumer enumeration

**This is raw material for A1's dossier. It is NOT the dossier.**

It is deliberately not written to `docs/dev/blast-radius/experience-soft-retire.md`.
Placing it there would satisfy `require-consumer-enumeration` before A1 ever looked at it,
turning a gate into a rubber stamp. C-10 is explicit that a hand-maintained consumer list
is **stale until re-derived**, and it rots in both directions — naming sites already fixed
and omitting sites that are not. A1 authors its own dossier and re-derives; this is a
head start and a cross-check, nothing more.

All of it is **[REPORTED]**.

**Canonical facts.** `Experience` at `db/models.py:88`, `__tablename__ = "experience"`;
parent attribute `Candidate.experiences` (`:67`); child back-refs named `experience` on
`ExperienceTitle` (`:154`), `Bullet` (`:193`), `ExperienceSummaryItem` (`:472`); index
`ix_experience_candidate_order` (`:124`). Nearest precedents: `ExperienceTitle.is_active`
(`:144` + migration `0011`), `Bullet.is_active` (`:181`), `Application.is_active` (`:762`
+ `0013`/`0015`).

### The concentration result — the most useful single finding

Filtering at **two** sites — `db/build_context.py:85-91` and
`corpus_to_json_resume.py:176-181` — closes the entire **generation** blast radius
transitively: LLM prompt, synthesized résumé, corpus snapshot, rendered `work[]`,
PDF/DOCX, ATS roundtrip. Everything else is **surface** work.

The riskiest *silent* consumer is `onboarding/corpus_import.py:645-655`, where a résumé
re-import would resurrect a retired role by merging into it with no user-visible signal.

### Required sites, by layer

**DB.** `db/models.py:88-124` (column; consider extending the composite index, per the
`0015` precedent); `db/build_context.py:85-91` (the single query feeding the whole
generation pipeline — highest severity), with `:114-120`/`:332-399`, `:160-163`,
`:180`/`:282-324` covered transitively; a new alembic revision following `0011` exactly.

**Blueprints.** `corpus/experiences.py` `:78-86` (list), `:143-155` (construct live by
default), `:236-263` (**the key site** — today "retire" only sets `is_active=0` on child
bullets and leaves the row visible); `corpus/_shared.py:35-53` and `:74-125` (serializers —
must emit the new flag or the JS toggle has nothing to branch on);
`corpus/curation.py:162-166`, `:250-261`, `:263-280`, `:341-343`, `:699-705`, `:790-796`;
`applications.py:1048-1059`, `:2230-2231`, `:2448-2452`, `:2606`, `:2727`, `:2881-2886`;
`corpus/skills.py:285-290`; `corpus/proposals.py:365-373`.

**Deterministic.** `corpus_to_json_resume.py:176-181` (second-highest severity),
`:186-265+`, and `:183-185` (`work_provenance` is order-aligned with `work[]` — any filter
must apply to both); `onboarding/corpus_import.py:645-655` and `:670-680`;
`onboarding/review_cli.py` (the whole pending-review loop).

**Templates + JS.** `templates/index.html:730` (count must exclude retired);
`static/app.js` — `_corpusExperiences` (`:3635`) is the carrier, plus `:3639`, `:3712-3742`,
`:4870-4890`, `:4928-4930`, `:4967-4968`, `:5281-5290`, `:5474-5496`, `:5499-5510`,
`:5873-5913`, `:5950-5977`, `:2528-2548` (a corpus of only retired roles must read as
empty), `:6047-6059`, `:7366-7384`, `:7674`.

**Scripts + evals.** `evals/seed_import.py:148-160` (needs `exp.get("retired", 0)` for
back-compat with existing fixtures); `scripts/generate_openapi_spec.py` (regenerate).

### Sites needing a decision, not just a filter

`Candidate.experiences` relationship (`db/models.py:67`) — relationship-level `primaryjoin`
vs. filter-at-call-site; repo convention is the latter. `create_experience`'s `.count()`
display-order seed (`:136-142`) — counting retired rows inflates it.
`_load_experience_for_candidate` (`_shared.py:128-142`) — a filter here would silently 404
every mutation on a retired role, **including a restore route**. `get_experience` (404 vs.
render-with-flag), `update_experience` (where restore lands), `merge_experience`.
`save_composition` (400 on a newly-retired role vs. drop the pin). `hardening.py:106`
`CorpusExperience` / `:202` `career_corpus` — adding `retired` to the payload rather than
filtering upstream is a **`context_set` schema change**. `scripts/export_corpus_seed.py:80-83`
— its docstring says the export is a *faithful* snapshot of all rows, so **don't filter**,
but do add `retired` to `_experience_row` and consider bumping `SEED_SCHEMA_VERSION`.
`ui_pages/selectors.py` — a retired-role selector likely needs adding, and that file is
itself a gated C-10 surface.

### Tests

**49 sites construct `Experience(...)`** and need the new column to default correctly;
those asserting on serializer output need updating. Highest-value tests to extend:
`tests/test_corpus_merge_and_retire.py:146-147,184` (the only tests asserting
`include_retired` semantics — the natural home for experience-level coverage);
`tests/ux/regression/test_20260629_corpus_retire_and_busy.py` (pins the owner's hard rule
that retired rows stay hidden until Show retired is ticked);
`tests/test_migrations_data_safety.py:332-354,440-519` (the no-row-loss / downgrade /
fresh-DB / already-at-head pattern a new revision must replicate);
`tests/test_career_corpus_routes.py`, `tests/test_build_context_db.py`,
`tests/test_corpus_to_json_resume.py`, `tests/test_openapi_spec.py`,
`tests/ux/stubs.py:82-91,164-175,203-216`.

**Known false positives** — `"Experience"` as a markdown heading, not the model:
`test_hardening.py` (17 hits), `test_json_resume.py`, `test_render_parity.py`,
`test_ats_roundtrip.py`, `test_parser.py`, `test_normalize_markdown.py`,
`test_pdf_render.py`, `test_docx_to_persona_html.py`, `test_analyzer.py`,
`test_analyze_split.py`, `test_resume_date_formatting.py`.

### Negative results — searched, zero hits

C-10 requires recording these; they are findings, not absences of work.

- `Experience.retired` / `exp.retired` / `"retired"` as an `Experience` field — **no hits.**
  The column genuinely does not exist yet.
- `Experience.is_active` / `exp.is_active` — **no hits.** `Bullet`, `ExperienceTitle` and
  `Application` all carry a soft-retire flag; `Experience` does not.
- **No raw SQL touching the `experience` table** — no `FROM` / `INSERT INTO` / `UPDATE` /
  `JOIN experience` in any `text()` call or `.sql` file. No raw-SQL consumer to patch.
- `db/migrations/versions/0001_initial_schema.py` has **no `op.create_table`** — it is
  `Base.metadata.create_all`, so a fresh clone auto-gets the column and the new revision
  needs the `PRAGMA table_info` guard.
- **No `Experience` coupling in `recall/`**, in `demo_fixtures.py` (its hits are the
  section-label string), or in `generator.py` / `pdf_render.py` /
  `docx_to_persona_html.py` / `parser.py` / `scraper.py`.
- **No secondary templates** — `templates/` holds exactly one HTML file.
- **No `to_dict()` / `__json__` / `serialize` on the model.** Serialization lives entirely
  in `blueprints/corpus/_shared.py`, `corpus_to_json_resume.py`, `db/build_context.py` and
  `scripts/export_corpus_seed.py` — those four are the complete serializer surface.
- **No existing blast-radius dossier covers this change.**
