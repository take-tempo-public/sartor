<!-- provenance: schema=1 session=24889186-748a-46ce-936c-8fcdf3e7fea6 branch=feat/prior-apps-pipeline commit=f42b2ea actor=amodal1 agent=anthropic/claude-opus-5 generated_at=2026-08-10 -->

# Handoff — Epic A close-out: `epic/a-app-core` (board item 36) is complete and PR-ready, NOT pushed

**Branch to create:** `epic/a-app-core`, cut from this branch's tip — **only on explicit
owner authorization.** Cutting the epic branch and opening its PR is **halt point 1**
(`docs/dev/epic-a-chain-design-corrections.md` §11.5 / §15.1) — outward-facing on a public
repo, and the one step in Epic A's "no owner intervention" target that stays the owner's by
design. No agent cuts this branch or pushes on its own initiative.
**Base branch:** `feat/prior-apps-pipeline` (the tip of the Epic A stacked chain) — **NOT
`main`.** Nothing in this chain has merged to `main` yet.

> **This is the epic-close handoff, not a sprint-to-sprint brief.** Per
> `docs/dev/epic-a-chain-design-corrections.md` §15.1 decision 3, the epic-close ceremony —
> this template, its verbatim blocks, `verify_doc_template.py` — was deliberately deferred
> from every sprint boundary to exactly this moment. It documents an epic that is **done**,
> not a sprint that is about to start. There is no "next sprint" inside Epic A; the only
> next step is the owner's PR decision.

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

**Epic-A-specific reading, on top of the numbered list above:**
`docs/dev/epic-a-chain-design-corrections.md` in full — it is the authorization envelope
(§11), the post-Epic-A review register (§12), and the owner-scoped plan for the epic's
second half (§15). §15.6/§15.7 name what must be true before Epic B starts; this handoff
exists to record that those conditions are checked, not silently assumed.

**Stream:** v1.1.0 Final March — **Epic A (`epic/a-app-core`, board item 36)**: main-app
function + UX. Four sprints, A1–A4, run as a **stacked chain** with no intermediate merges —
six sprint branches on one physical chain, because item 20 took its own `fix/*`.
**Sequencing rule:** strictly sequential — one sprint, one branch, one session, each branching
off the previous sprint's tip. **Now closed out as a chain; the epic branch has not been cut.**
**Blocked until this stream lands on `main`:** epics B (render/ATS), C (diagnostics), D (docs
IA), E (release) — board items 37/38/39/40, all `blocked`. **Do not start any of them without
explicit owner direction**, even though Epic A itself is finished.

- ~~`feat/corpus-polish` (A1a)~~ ✓ — corpus panel reordered to Summary → Work Experience →
  Education → Skills; rows compacted; role-card order fixed. Commit `7c15c2e`.
- ~~`fix/experience-soft-retire` (A1b)~~ ✓ — retire now happens at the *role* level, not only
  its bullets; migration `0016` (`db/migrations/versions/0016_experience_is_active.py`) adds
  `Experience.is_active`, plus the unfiltered-consumer sweep. Commits `b8381f5` (reproduction),
  `5474763` (fix).
- ~~`feat/compose-wait-ux` (A2)~~ ✓ — the "Composing…" arrival wait gate, the labelled
  background-reload chip, word-button skills pin/drop, in-place Edit on every compose bullet.
  Commit `2a0b37a`.
- ~~`fix/wizard-rail-frozen-composition-gate` (item 20)~~ ✓ — the Step-5 rail is a hard gate on
  one predicate (`hardening.frozen_composition_doc`), shared by client and server. Commit
  `3e2b8a5`.
- ~~`feat/role-summary-drafting` (A3)~~ ✓ — `draft_experience_summaries`, a net-new batched
  Sonnet call end-to-end (prompt, grounding widening, `PROMPT_VERSION` bump, telemetry,
  pricing, UI, eval fixture). Commit `7d3ff33`. Unplanned mid-sprint addition:
  `BOARD_DEFERRAL.md` (commit `543917c`) — scoped `BOARD.md`-staleness exemption for the
  remainder of the epic, itself refuted and strengthened before landing.
- ~~`feat/prior-apps-pipeline` (A4)~~ ✓ ← **this branch; this handoff's branch; HEAD.** Removed
  the Tailor applications panel; `_renderPipelineRow`'s `activate()` now opens the shared
  detail modal in place instead of tab-switching to Tailor first. Commit `3cfb98d`.
- **This session (epic close-out)** — advanced `.last_ingest_sha` to this commit, retired
  `BOARD_DEFERRAL.md` and regenerated `BOARD.md` for real, and wrote this handoff. No
  production code touched.
- **Next: `epic/a-app-core` cut from this tip, final Opus `xhigh` review over the full epic
  diff, PR opened** — **owner's call, halt point 1.** Not started by this session.
- **Not started, not authorized here:** Epic B / C / D / E (board items 37–40). They stay
  `blocked` until Epic A actually lands on `main`.

---

## What just landed on `feat/prior-apps-pipeline`

**This is this branch's own tip — not `main`. Nothing in Epic A has reached `main` yet.** This section describes the state of this
branch's HEAD, which is 29 commits ahead of `main` (`52c821e`) and has no upstream — `git
ls-remote --heads origin feat/prior-apps-pipeline` and `...epic/a-app-core` both return
nothing. Read every claim below as "true on this branch," not "true on `main`."

**A4 itself** (commit `3cfb98d`): removed the Tailor applications panel
(`templates/index.html`, `static/app.js`), rewired `_renderPipelineRow`'s `activate()` to open
the shared detail modal in place, and updated `ui_pages/` + the pinned regression test that
asserted the old tab-switch behavior. `ui_pages/selectors.py` is a C-10 gated surface this
sprint touched; its blast-radius dossier is `docs/dev/blast-radius/prior-apps-pipeline.md`.

**This session's own four close-out tasks, all committed-pending (staged, not yet committed —
the orchestrator commits):**
1. `docs/wiki/.last_ingest_sha` advanced `3e2b8a5` → `f42b2ea` (this commit). The epic-close
   wiki pass covering the full `3e2b8a5..HEAD` delta (18 wiki-relevant files → 9 pages edited,
   11 verified-no-edit) was done and independently audited in an earlier session; this session
   only advanced the checkpoint to make that already-true fact honestly assertable.
2. `docs/dev/work/BOARD_DEFERRAL.md` deleted (`git rm`), then `python -m scripts.work_items
   board --write` regenerated `docs/dev/work/BOARD.md` for real, then `python -m
   scripts.work_items check` passed strictly: `work_items: OK (76 files)` — no DEFERRED
   notice, no staleness error.
3. This handoff file, stamped and validated (see the close-out checklist below for the exact
   command and result).

### Hypothesis outcomes (§15.6) — record this, it is the deliverable, not just the finished epic

| # | Hypothesis | Outcome |
|---|---|---|
| **H-6** | Deferring close-out ceremony to the epic boundary cuts per-sprint cost toward 10–20% without increasing escaped defects. | **Not confirmed — a cost datum only, explicitly disclaimed in the source.** A3's delegated work totalled ≈1.495 M subagent tokens, of which ≈432,808 was the unplanned `BOARD_DEFERRAL.md` work, leaving ≈1.062 M for the sprint proper against A2's ≈1.64 M and item 20's ≈1.23 M. §12.7 states directly: **"Do not read this as H-6 confirmed"** — A2's total included ≈868 k of wiki pass + grounding audits that §15.2 deferred, so the comparison is confounded in H-6's favour by construction. No A4-specific figure is recorded in `epic-a-chain-design-corrections.md` as of this commit. |
| **H-7** | A fresh agent can execute a sprint from the §15.4 sprint brief + pointers, without the full handoff ceremony. | **No outcome recorded in `epic-a-chain-design-corrections.md` as of this commit.** I looked for an explicit verdict and did not find one — flagged here as a genuine gap rather than inferred. If the next reader has evidence either way, it belongs in §15.6 of that document, not reconstructed from memory. |
| **H-8** | The countable-claim canary (§15.5) catches page-quality problems at a fraction of full-audit cost. | **No outcome recorded in `epic-a-chain-design-corrections.md` as of this commit.** Same gap as H-7 — not found, not inferred, stated as missing. |
| **H-9** | A chain can reach PR-ready with no owner input. | **FALSIFIED at A3** (§12.7, stop 4). Five owner interactions occurred; the falsifier fires on interaction #1 alone (an unauthorized "proceed now?" question before A3 started — A3 was already the next item on the vector). Two more (#4, #5 — "is A4 running?", "why did you stop?") were forced by an unannounced stall at the A3/A4 sprint boundary: A3 closed cleanly, gate green, zero RERUN, and the session then posted a terminal summary and did nothing further — no halt point or flag stop was in play, so under §11.8 the orchestrator owed a decision, not a pause. One interaction (#2, the `BOARD.md`-staleness-vs-§15.2 conflict) **was** properly authorized under §11.5.3/§11.6.5. §12.7 also flags an open tension: as long as §11.6.5 stands, ANY run that meets a new-or-modified enforcement surface mid-flight must stop, so H-9 as literally written may be unsatisfiable by construction — not resolved in the source document. |

**F12/F13 — new friction findings from A4, worth carrying into any Epic B design:**
- **F12** — a **subagent** that calls `run_in_background` deadlocks permanently: the
  completion notification routes only to the orchestrator, never back into the subagent's own
  context. A4's implementer lost ~47 minutes and 373k tokens waiting on a signal that
  structurally could not arrive, while its actual working tree was complete and correct — one
  recovery round-trip away from the sprint's entire narrative being redone from scratch.
  Mitigation applied from A4's recovery onward (prose in every subagent brief: never
  `run_in_background`, never wait on a task notification) is **explicitly labelled unenforced**
  in the source (C-11) — nothing fails closed if a future brief omits it. **This session's own
  task brief carried that exact prohibition, and it was followed — no recurrence this
  session.**
- **F13** — the harness's own `run_in_background: true` is **not** equivalent to `nohup … &`;
  a background-launched gate can be killed wholesale by the harness even with a correct
  `> file 2>&1` redirect. A4's gate died mid-`pytest` this way (ruff/mypy had already passed).
  Correction recorded in §11.9: launch the gate with `nohup … &` from a foreground call, never
  via the harness's own backgrounding.

### Two real defects caught by adversarial review, not by tests — the honest state of the epic

1. **Item 20's contentless-freeze rail gap** (fixed on the item-20 branch itself, before this
   handoff's branch existed) — the obvious fix (gate on the client's `_compositionFrozen`
   flag) was written and then refuted: a contentless freeze still opened the Step-5 rail.
   Resolved as one predicate, one implementation (`hardening.frozen_composition_doc`), shared
   by all three seams.
2. **A3's cross-application pending-variant leak** — a foreign application's PENDING intro
   variant could reach the *rendered résumé*, not just the drafting prompt. Confirmed and
   blocked pre-merge by A3's adversarial refuter. The narrower sibling gap
   (`_active_intros_by_experience` feeding a foreign PENDING intro into the draft prompt as
   "existing intros" — prompt-context bias only, no rendered-résumé leak) is filed as item 69,
   `watching`, lower severity than what A3 actually fixed.

Eight work items were filed across A3/A4/this close-out: **69–76.**

### Item 75 — retired roles still reach the A3 drafting prompt (filed this close-out)

`blueprints/applications.py:_build_experience_summary_targets` (~line 2725) reads the
**frozen** analyze-time `career_corpus` snapshot and never intersects it against live
`Experience.is_active`. A role soft-retired by A1b can still reach the
`draft_experience_summaries` Sonnet prompt. The sibling gap-fill lane
(`draft_application_gap_fill`) was hardened at exactly this seam with a live-DB
`is_active=1` filter; A3's lane did not get the same treatment.

**Blast radius traced and bounded** (why the item is `watching`, not urgent): the retired
role never renders a card (`get_application_composition` filters `is_active=1`), cannot be
kept (`experience_summary_decide` 400s on it), and never reaches the grounding union
(`assemble_source_union` reads only the already-filtered `experiences` list). Actual cost is
wasted Sonnet tokens and an inert in-memory entry — no user-visible defect.

**The docstring at `applications.py:2711` claims the effective-bullet rule "mirrors
`corpus_to_json_resume.build_json_resume_from_corpus` exactly" — it does not**, because that
function reads the live DB (`is_active=1`) and this one reads the frozen snapshot. **Per the
item's own explicit instruction: the docstring must NOT be corrected on its own.** The
docstring describes the correct intent; the code is what's wrong. Fixing the prose alone
would enshrine the defect — both must change together, by making the code intersect the
frozen snapshot against live `is_active` (mirroring the `cand_exp_ids` pattern already proven
in the gap-fill lane), the docstring updated in the same commit as the code.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

`docs/dev/work/BOARD.md` is the authoritative live-item source (regenerate with `python -m
scripts.work_items board --write`; never hand-edited — `RELEASE_CHECKLIST.md`'s own former
prose ledger was formally superseded by it on 2026-07-28). Reproduced from the board **as
regenerated at this branch's tip, this session, after `BOARD_DEFERRAL.md`'s removal** — these
are frontmatter `status` counts computed across all **76** item files (item + epic kind
together), not the board's own flat-section counts, which exclude items rendered nested under
an epic heading. **55 items are still open in some status (open/blocked/deferred/watching); 6
of those are epics.**

**Open (4):** items **9** (release/visual-assets refresh — stale screenshots, under epic 39),
**19** (UX-suite flakiness umbrella epic, children 27–31, 57), **36** (Epic A — this epic,
child **20 now closed**, child **34** still open below), **50** (C-7/C-10 are enforced by
Claude Code hooks only — do not travel to other agents or an extracted governance package).

**Blocked (8):** items **3** ([HUMAN] GitHub toggles — repo rename, PyPI Trusted Publisher,
GHCR visibility, `enforce_admins`), **5** (grounding-score persistence gap blocks calibrated
L1/L2 metric layers), **8** (Compose-time rewrite latitude — the "generate but don't invent"
dial, design landed, nothing built), **10** (the v1.1.0 release cut itself, under epic 40,
depends on 3/6/7/9/19), and the four blocked epics **37 / 38 / 39 / 40** (Epics B/C/D/E —
render+ATS, diagnostics console, docs+IA, the public cut).

**Deferred (7):** items **4** (in-app rendered citation viewer), **7** (PX-46 selective memory
consolidation, owner sign-off required), **24** (template-preview fidelity spike, needs
product-priority decision), **25** (`app.run(threaded=True)` governance decision, C-1-sensitive
owner call), **41** (domain-vocabulary library for Compose drafting, post-1.1.0), **42**
(template-format investigation — dotx/mht import, post-1.1.0), **43** (approved-fonts list
expansion, post-1.1.0). All owner-gated or explicitly post-1.1.0.

**Watching (36 — 8 new this epic close):** items **2, 16, 18, 23, 30, 34, 46, 47, 48, 49, 51,
52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68**, and **69, 70, 71, 72, 73,
74, 75, 76 (new — filed across A3/A4/this close-out)**.

- **Items 69–76 are new**, filed across A3, A4, and this close-out session. **69** — a
  narrower sibling of A3's fixed pending-variant leak (prompt-context bias only). **70** — the
  UX-stub-coverage AST walker only matches one import form, minor/not exploitable today. **71**
  — data gathered toward a future managed/orchestrated-epic-execution design pass (not a
  proposal). **72** — Pipeline rows lost the removed panel's pending-proposals indicator. **73**
  — `PriorAppsPage.open_detail()` shifted from click-driven to direct-JS-invocation coverage in
  four test files, zero diff but a real coverage-mode change. **74** — `refreshPipeline()`
  refetches the whole cross-candidate roster on 7 sites instead of one candidate; disclosed
  trade, no N+1. **75** — retired roles reach the A3 drafting prompt (see above; docstring at
  `applications.py:2711` must be fixed WITH the code). **76** — `BOARD_DEFERRAL.md`'s
  `declared` field has no expiry bound (the marker this session just retired — filed so the
  *mechanism gap*, not just this instance, is on record for any future deferral marker).
- **Item 34 is still open and parented to Epic A (child of 36).** The corpus blueprints'
  `_get_client` is never patched in the UX test harness — a real billed-API risk, not just a
  stub-tidiness issue. It was folded into the A3 brief but is not confirmed closed here; verify
  before treating Epic A as fully clean.
- **Item 58 carries a C-11 clock.** A handoff amended after its `generated` stamp blocks the
  next session with no warning at authoring time. It was filed as a first instance. **A second
  instance owes a fail-closed mechanism, not another item update** — do not edit this file
  after it is committed.
- **Item 65 is the wiki-counter class** (the counter measures "changed since checkpoint," not
  "coverage current"). Zeroing it each sprint fixes the instance; the class stays open. This
  session's advance to `f42b2ea` is another honest instance-fix, not a class-fix.
- **Item 52 is the gate-window-gap class** — the tree that lands is never quite the tree the
  gate examined. Six instances documented; still open.

**Epics (6):** **19** (UX-flake umbrella, open, children 27–31 + 57), **36** (Epic A, open,
child 20 closed / child 34 open), **37 / 38 / 39 / 40** (Epics B/C/D/E, all blocked, no
children filed yet except 9 under 39 and 10 under 40).

**Open-only count is 4 against the 10 ceiling — under the reduction-sprint threshold**, same
as every prior handoff in this chain reported. **The `watching` bucket is the one that should
draw the owner's attention.** Its growth across the epic: 16 → 22 → 25 → 28 → **36** — this
session's own close-out alone added 8. It has never been reduced, only added to, across all
four sprints of Epic A. This is not itself the 8–10-ceiling trigger (that ceiling is defined
against `open`), but a bucket that only grows for an entire epic and is never triaged is
exactly the shape charter W-1 exists to catch. Flagging it explicitly rather than letting the
number simply grow into the next handoff.

---

## Recurrences observed this session → guardrail authored

**None observed in this closing session's own actions.** This session ran four scheduled,
narrowly-scoped administrative tasks (advance the wiki checkpoint, retire
`BOARD_DEFERRAL.md` + regenerate `BOARD.md`, write and validate this handoff) and hit no
repeat failure mode of its own — in particular, the F12 subagent-backgrounding deadlock that
cost A4's implementer ~47 minutes did **not** recur here: this session's own brief prohibited
`run_in_background` and waiting on a task notification, and no tool call in this session used
either.

**The epic-wide recurrences are not restated here.** F11 (a detached gate emits no completion
signal), F12 (a subagent that backgrounds a task deadlocks permanently), and F13 (the
harness's `run_in_background` is not `nohup … &`) were each identified, and their
mitigations/corrections already recorded, in `docs/dev/epic-a-chain-design-corrections.md`
§12.2 and §11.9 (committed at `0189b08`, `0415de3`, `c6a472e` respectively) — each is
**explicitly labelled unenforced (C-11)** in that source: prose in a subagent brief and in
the authorization envelope, not a gate. Restating them here as if newly discovered by this
session would misattribute them; the source document is the citable record.

---

## What this branch should build

**Nothing.** This is an epic-close handoff, not a sprint-start brief — there is no next sprint
inside Epic A to scope. The only authorized next action is described in "First move" below,
and it is owner-gated. Do not treat any open or watching board item above as authorized work
for this branch; none of them is in scope here.

---

## First move

1. Verify the pointer that brought you here with
   `python scripts/check_handoff_pointer.py "<pointer line>"`, then
   `python scripts/verify_doc_template.py docs/dev/handoffs/prior-apps-pipeline.md
   docs/dev/AGENT_HANDOFF_TEMPLATE.md --event consumed --agent <your-agent-id>`. A failure at
   either step is your **first output** and you **STOP** (charter C-9).
2. Read `docs/dev/epic-a-chain-design-corrections.md` §15.7 ("What must be true before Epic B
   starts") and confirm each of its four conditions against this document and the repo — do
   not assume they are already satisfied because this handoff exists.
3. **Ask the owner whether to cut `epic/a-app-core` from this tip and open the PR.** This is
   halt point 1 (§11.5) — do not push, do not create the epic branch, do not open a PR without
   that explicit go-ahead. If the owner has already given that direction before you read this,
   the PR-channel steps in the close-out checklist below are the path (push → PR → `ci_wait` →
   `gh pr merge --merge`, never a local merge).
4. **Do not start Epic B, C, D, or E** (board items 37–40) on this branch or any new branch
   until the owner has explicitly directed it. They remain `blocked` in `BOARD.md` for a
   reason — Epic A landing on `main` is a precondition, not a formality.

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
