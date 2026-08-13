<!-- provenance: schema=1 session=b0769daa-4696-48ed-90e8-76f1659c3244 branch=epic/b-render-ats commit=75b57a4 actor=amodal1 agent=anthropic/claude-fable-5 generated_at=2026-08-13 -->

# Handoff — B1b landed and the method largely held; the invoker's own context is the measured bottleneck. Review this run's experience, propose SMALL mitigations, then run again.

> **The owner's directive for the next session (2026-08-13, on screen, closing
> run 5):** review this session's experience so that you can **evaluate the
> method**, and from that evaluation **seek small redesigns to mitigate this
> properly** — "this" being the invoker-context degradation that forced run 5's
> boundary stop — **and try another run.** The next run's target is unchanged:
> the Epic B remainder (now just B2 + the epic close to PR-ready) per the
> owner-ratified scope sentence, single-sourced in `epic-b-design-brief.md`
> §"Execution mode + authorization record" — cite it, never restate it.
>
> **This is a review-and-design session first, an executor second.** Do not
> invoke the pipeline before the review is done, the redesigns are
> owner-approved, and the owner has opted into the run. Do not resurrect any
> control the 2026-08-13 adversarial review killed
> (`docs/dev/diagnosis/n1-pipeline-hardening-review.md` §"Adversarial review"
> — killed for cited reasons). "Small" is the owner's word: mitigations, not
> architecture.

**Branch to create:** `fix/n1-invoker-context-budget` (create only when moving
from review to implementation of owner-approved survivors; the reading/review
phase needs no branch)
**Base branch:** `epic/b-render-ats` @ `75b57a4` (verify with
`git log -1 epic/b-render-ats` before cutting)

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

**Epic-specific reading, on top of the numbered list above:**
`docs/dev/handoffs/epic-b-design-brief.md` (standing context; the ratified
scope sentence's single source), `docs/dev/n1-baseline-pipeline.md` (contract
+ runbook), `docs/dev/diagnosis/n1-pipeline-hardening-review.md` (the 0-for-4
record, the adversarial verdicts, AND run 5's S5 harness measurements),
`docs/dev/work/items/0084-build-n1-baseline-pipeline.md` (the complete run
evidence trail — run 5's two entries are the newest),
`docs/dev/handoffs/epic-b-b2-brief.md` (the NEXT run's sprint brief — already
written, already amended, stays valid).

**Stream:** v1.1.0 Final March (`docs/dev/RELEASE_ARC.md` §"v1.1.0 Final
March") — five epics, A→E, strictly sequential.
**Sequencing rule:** one epic at a time; Epics C, D, E (board 38/39/40) stay
behind B.

- ~~Epic A (`epic/a-app-core`, board 36)~~ ✓ — merged `162c1dc` (PR #117).
- ~~`feat/n1-baseline-pipeline`~~ ✓ — item 84's authorized build (PR #125).
- ~~`fix/b1-stale-template-companions`~~ ✓ — sprint B1a (run 3); ff-merged
  at `d8f0a8f`.
- ~~`fix/n1-invoker-loop`~~ ✓ — run-3 polish (epic loop, item 89).
- ~~`fix/n1-scope-dedup`~~ ✓ — the hardening review (S1–S5); `9d3bec5`.
- ~~`fix/b1-education-render`~~ ✓ — **sprint B1b, run 5, THIS session:
  complete through both gates, ff-merged, branch pruned** (see "What just
  landed").
- **`fix/n1-invoker-context-budget`** ← **next: yours — the owner-directed
  method review + small mitigations (see "What this branch should build").**
- `feat/ats-conformance` ← B2, run 6, AFTER your review lands and the owner
  opts into the run — via `epic-b-b2-brief.md`'s First-move block (terminal
  sprint: `epicSprintIndex: 3, epicSprintCount: 3`, no `nextSprintBriefPath`).
- Epic close-out to PR-ready → owner-gated epic PR (halt point 1) → then
  Epics C, D, E.

**What must NOT be started by this session:** the B2 sprint itself (only
after review + owner run opt-in); widening N past 1 (owner-reserved, §16.7);
any killed control from the adversarial review (Workflow-matcher gate,
blocking Stop hook, epic-plan JSON, in-pipeline probes, gate receipts);
large redesigns of any kind — the owner asked for SMALL; the watching-bucket
reduction sprint (flagged, but its own decision).

---

## What just landed on `epic/b-render-ats`

Four commits this session (`0838558` → `75b57a4`), all on the epic branch or
ff-merged into it:

- `0838558` — run-5 invocation record + **S5 harness measurements** (PreToolUse
  fires for Workflow with structured `tool_input`; workflow-internal spawns
  invisible to it; Stop fires at turn end) + session ledger shard. Probe hooks
  deleted from machine-local settings after recording.
- `f47b1ed` — **sprint B1b**, the pipeline's work: `studyType` rendered across
  every education surface via one canonical joiner
  (`json_resume.education_position_text`/`split_education_position`/
  `EDUCATION_FIELD_SEPARATOR`); docx font-name capture closed including the
  emphasis-branch widening the brief missed. Refuter findings F1/F2/F3 all
  judge-confirmed as narrow, fixed by the closer, recheck-cleared.
  **The escalation primitive fired live for the first time**: refuter
  `flag_stop` (§11.6.3) → one Opus reviewer → `targeted_fix`, verbatim
  rationale carried end-to-end; the reviewer reproduced and REATTRIBUTED the
  finding (pre-existing emitter ambiguity, not a regression) and the run
  correctly continued. 10 files, 969 insertions at stage time; both gates
  green with **0 RERUN lines each**.
- `f74c94d` — second hook-appended `compacted` receipt (the boundary-stop
  trigger, see below).
- `75b57a4` — run evidence in item 84 + the b2 brief's false "no items filed"
  claim amended (dated, attributed).

Items **90/91/92** filed by the invoker (closer divergence — see Recurrences).
Wiki drift 17/75 at the sprint gate (under the epic's 40 margin); the sprint's
scoped wiki-relevance check ran in-pipeline (5 relevant paths, 0 page edits,
`docs/wiki/log.md`). Working tree clean; sprint branch pruned.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

`docs/dev/work/BOARD.md` is authoritative; re-derived at this close
(regenerated at the sprint gate, `work_items check` OK, 92 files).

**Open — 1 top-level + 2 open epics:** **50** (C-7/C-10 enforced by Claude
Code hooks only — prose binds other agents). Epics **19** and **36** open —
**Epic A's item 36 status never flipped `closed` — at least the ELEVENTH
handoff flagging it.** (Epic-nested open: 20, 34 under epic 36; 27–31, 57
under epic 19.)

**Blocked — 3 top-level:** **3** ([HUMAN] GitHub toggles), **5** (grounding-
score persistence gap), **8** (Compose rewrite latitude), plus epics **37,
38, 39, 40**; **9**, **10** epic-nested.

**Deferred (7):** **4, 7, 24, 25, 41, 42, 43** — see `BOARD.md`.

**Watching — 45 top-level (42 + this session's 90, 91, 92):** 2, 16, 18, 23,
46, 47, 48, 49, 51, 52, 53, 54, 55, 56, 58, 59, 60, 61, 62, 63, 64, 65, 66,
67, 68, 69, 70, 71, 72, 73, 74, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 88,
90, 91, 92. **The reduction-sprint flag stands and the bucket GREW — at
least the ELEVENTH handoff flagging it.**

- **Item 84** — run 5 added the strongest evidence yet (first live escalation
  firing, full B1b completion, S5 measurements) but `halt_point`/`hook_block`
  short-circuit routing and `harness_throw` remain unexercised live. Stays
  watching.
- **Item 58** (post-stamp handoff amendment) — this session amended the
  UNSTAMPED b2 brief (safe), but the class stands.
- From the hardening review's residue, still standing for the owner:
  `bypassPermissions` in machine-local settings undermines every hatch-based
  control repo-wide; the governance-hooks gate needs restructuring before any
  hook-based pipeline enforcement. (The third residue item — record S5 +
  delete probe hooks — was DISCHARGED this session.)

---

## Recurrences observed this session → guardrail authored

1. **Hook-written CRLF in the session ledger shard — recognized as the
   working-tree CR-byte class, its FOURTH+ instance** (S3's dossier records it
   was "live in a ledger shard this very day" on 2026-08-13's review session;
   this session it recurred TWICE — the shard came back CRLF after the
   `consumed` event and after each `compacted` append). Mechanism authored on
   this branch: **none** — stated plainly. S3's CR-byte test covers
   `.claude/workflows/*.mjs` only; the ledger-shard writer
   (`scripts/enforcement/adapters/claude_context_hook.py` and
   `scripts/verify_doc_template.py`) still emits platform line endings. A
   fail-closed mechanism IS possible and small (write `b"\n"` explicitly at
   the writers, plus extending the working-tree byte check to
   `docs/dev/ledger/*.jsonl`) — deliberately not authored mid-close because
   the owner directed "stop now"; it is FIRST on the candidate list in "What
   this branch should build," and this line is the C-11 declaration
   surfacing the gap to the owner rather than counting silence as protection.
2. **Item-87 witness re-arming on task notifications — known counted class**
   (run-3 preflight first observed it). Twice this session; both landed on
   the INVOKER's own main-loop write (benign, one re-run each), never on a
   subagent. No new mechanism (standing owner decision: a mid-run re-arm
   stopping a run is the owner's call, not a thing to route around); counts
   recorded in item 84.
3. **A closer skipping judge-ordered work-item filing — FIRST instance of
   this specific class** (recorded, not yet a recurrence): `itemsFiled: []`
   despite the judge's F1 verdict ordering a filing and the implementer
   handing two more findings over. The invoker filed items 90/91/92 and
   amended the b2 brief's resulting false claim. Recorded in item 84 and in
   each item's Update section; a closer-prompt fix is on the candidate list
   below. If the NEXT run's closer does it again, that is a recurrence and
   C-11 demands a mechanism on that branch.
4. **The scope-restatement class did NOT recur** — worth recording as the
   S1/S2 fixes' first live validation: preflight reconciliation was genuinely
   clean (byte-identical sentence), zero owner questions were asked, and the
   ceremony derived itself from position args.

---

## What this branch should build

**The owner's mandate (see the block quote at the top): review run 5's
experience → evaluate the method → propose SMALL redesigns → owner approval →
implement survivors → then the owner decides the next run.** Numbered:

1. **Read the experience record in full.** The inputs, in order:
   item 84's two run-5 entries (`docs/dev/work/items/0084-*.md`); the S5
   measurements section in
   `docs/dev/diagnosis/n1-pipeline-hardening-review.md`; this handoff top to
   bottom; the session ledger shard
   (`docs/dev/ledger/b0769daa-4696-48ed-90e8-76f1659c3244.jsonl`); the run
   transcript if needed (session `b0769daa`, recoverable per
   `~/.claude/projects/C--Dev-sartor/` — the workflow journals for
   `wf_23457bb9-ae5`, `wf_008f60f1-129`, `wf_b6c11f29-255` live under its
   subagents dir).

2. **Evaluate the method against what run 5 actually showed.** What HELD
   (evidence cited in item 84): the escalation primitive end-to-end; the
   derived ceremony (S2); zero-question preflight (S1); exact accounting;
   the kill-proof gate shape twice; the S4 banner derivation; refuter →
   judge → recheck catching and scoping real findings. What COST the run
   (the invoker's own observed frictions, each with its durable record):
   - **The central finding — the invoker is not context-free.** The C+drift
     design's monitor was specified as "a deterministic Workflow-script
     monitor with no LLM context of its own"
     (`epic-a-chain-design-corrections.md` §16); the de-facto invoker is a
     full LLM session that accumulates ~12.3k lines of mandatory kickoff
     reading (measured: the 11-doc list), every verbose run report (the
     sprint-stage result alone was ~24k chars), every gate wait, and every
     notification. Two `compacted` receipts fired DURING gate waits
     (22:51:12Z, 23:08:27Z — ledger shard) in sprint 1 of an intended
     3-sprint continuous window. The §16 empirical driver — "accumulation
     ACROSS sprints in one continuous window" (11x/14x compaction) — has now
     reproduced at the INVOKER level. What internal capability was actually
     lost is NOT measurable from inside (C-0/C-8: the receipts are the only
     evidence; do not narrate degradation beyond them).
   - The closer divergence (Recurrences #3).
   - The CRLF ledger class (Recurrences #1).
   - The evidence hook blocking the invoker's own machine-local
     `.claude/settings.local.json` edit on the `fix/*` sprint branch
     (path-level bluntness, discharged from the epic branch; recorded in
     item 84's kickoff entry).
   - The plan-stamp late-bind: the runbook predicts "one marker re-approval
     per sprint boundary"; in practice the stamp transferred
     `fix/n1-scope-dedup` → `fix/b1-education-render` → `epic/b-render-ats`
     without ever retiring (merged-to-epic ≠ merged-to-main). Benign this
     session, but the runbook's prediction is wrong and should be corrected
     or the behavior confirmed as intended.
   - Item-87 re-arms on notifications (Recurrences #2).

3. **Propose SMALL redesigns, evidence-first, owner-approved before any
   implementation.** Candidates run 5's experience suggests (candidates, not
   conclusions — refute freely): (a) LF-explicit writes in
   `claude_context_hook.py`/`verify_doc_template.py` + widening the CR-byte
   working-tree check to ledger shards (Recurrences #1 — smallest, most
   deterministic); (b) a closer-prompt line in `n1-baseline.mjs` making
   judge-ordered filings an explicit named obligation with the report
   schema requiring `itemsFiled` to reconcile against judge verdicts;
   (c) invoker context-budget mitigations — e.g. trimming the run report's
   chat-surface size (full detail already lands in `journal.jsonl`),
   moving the mandatory-reading list toward targeted sections, or
   declaring one-sprint-per-session WITH a mandatory boundary handoff as
   the recorded norm (this last one CHANGES the ratified scope sentence —
   it is the owner's sentence, so it is the owner's call alone; surface
   the trade, do not pre-decide it); (d) the runbook's plan-stamp
   prediction corrected to the observed late-bind behavior. Weigh each
   against the adversarial review's kill-reasons before proposing —
   anything that rhymes with a killed control needs to say why it is not
   that control.

4. **Implement only owner-approved survivors** on
   `fix/n1-invoker-context-budget` (evidence dossier first — the compaction
   receipts and this handoff ARE the `## Observed` material), gate green,
   ff-merge to the epic branch per this epic's topology.

5. **Then stop and hand the owner the run decision.** The next run is B2 +
   epic close via `epic-b-b2-brief.md` (already written, already amended,
   still valid — do NOT rewrite it as part of the review). The run opt-in is
   per-session and the owner's alone; nothing in this handoff grants it.

Scope is bounded to the owner's review-and-small-redesigns directive above
plus §"Epic B — `epic/b-render-ats`" in `RELEASE_ARC.md` for the eventual
run. Do not expand beyond what is listed there.

---

## First move

Verify this handoff's pointer (`python scripts/check_handoff_pointer.py
"<pointer line>"`) and stamp it consumed (`python
scripts/verify_doc_template.py docs/dev/handoffs/fix-b1-education-render.md
docs/dev/AGENT_HANDOFF_TEMPLATE.md --event consumed --agent <agent>`), then
read the documents above — the run-5 experience record included — then write
the review as a plan at `~/.claude/plans/<slug>.md` and show it to the owner
before touching any code. **Do not code first; do not invoke the pipeline at
all this session without the owner's explicit run opt-in.**

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
