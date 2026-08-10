<!-- provenance: schema=1 session=c764076e-42dc-466a-ba56-55bc3604f59e branch=docs/epic-a-wave-orchestration-design commit=cd83a2b actor=amodal1 agent=anthropic/claude-sonnet-5 generated_at=2026-08-07 -->

# Agent handoff: begin Final March Epic A as a stacked-branch, Opus-orchestrated chain

**Branch to create:** `epic/a-app-core` sprint branches per the design below — start with
`feat/corpus-polish` + `fix/experience-soft-retire` (sprint A1). See "First move."
**Base branch:** `main` (this handoff's own base; `main` was at `cd83a2b` — PR #112 —
when this branch started).

**This branch captures a design, it does not execute it.** The prior session worked out
a specific method for running Epic A (sprints A1–A4) as an Opus-orchestrated,
stacked-branch chain of full-ceremony sessions, across a long conversation — and never
wrote it to a durable doc before closing out. A prior handoff correctly flagged that
risk; the owner tried it anyway, and the next session lost the design, confirming the
gap. This branch is the fix: the full design, captured here, inline, so the next session
can actually begin.

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

**Stream:** v1.1.0 Final March — CI-infrastructure pass complete; epic A not yet started.
**Sequencing rule:** strictly sequential — one branch at a time (within Epic A's own
chain, "sequential" means tip-to-tip stacking, not each off `main` — see "The design").
**Blocked until this stream tags:** the public v1.1.0 cut (epic E / item 10).

- ~~`fix/plan-approval-marker-pr-merge`~~ ✓ — item 45 closed (D3(c))
- ~~`fix/plan-approval-branch-switch-gap`~~ ✓ — item 45 reopened + reclosed same day;
  the reconciliation ordering fix this whole design's plan-approval mechanics depend on
- **`docs/epic-a-wave-orchestration-design`** ← this branch — captures the design,
  executes nothing
- **Next: sprint A1** (`feat/corpus-polish` + `fix/experience-soft-retire`), the first
  case in the stacked chain. See "First move" and "The design" below.

**The march is still deliberately paused before epics B–E.**

**Item 10's release chain is still gated on epic 19** — untouched this session.

---

## What just landed on `main`

`main` was at `cd83a2b` (PR #112) when this branch started. This branch adds one file
(itself) — no production code, no `RELEASE_ARC.md` edit (deliberately simplified per
owner direction mid-session: one handoff, not a separate design doc + pointer edit).

---

## The design — Epic A as a stacked-branch, Opus-orchestrated chain

**Origin.** The owner asked to reuse the 2026-08-06 pre-march chain experiment's method
(PR #105: 4 serialized fresh-context Sonnet-xhigh cases, Fable orchestrating, stacked
branches, full ceremony per case, handoff-file-only inter-case channel) for Epic A
specifically — with Opus orchestrating instead of Fable, and several deliberate changes
adapted from a "traditional wave test" method the owner used successfully on the
`spolia` project, chosen to be **more conservative** here since this project has more
moving parts.

**What this is, and what it explicitly is not.** Sequential, stacked, full-ceremony
sessions — closest in shape to the 08-06 chain. **Not** parallel subagent lanes
reporting completion on each other's behalf, which is the 2026-07-11 debt-burn train
shape (`docs/dev/ORCHESTRATION_PLAYBOOK.md`, a genuinely different, older mechanism):
several lane deliverables in that train were reported complete when they were only
partially done, and that failure is exactly what motivated the charter's standing
**W-1 "no waves" posture** ("no multi-agent conductor, no parallel lanes, no wave
assembly... until Claude Code's reliability is trusted again," Key Decision 10,
2026-07-16). This design does not do that. It is scoped by the owner to Epic A only, as
a bounded experiment — **not** a standing reversal of W-1, and not contingent on the
broader 2026-08-06 governance directives (written chain-sanction grammar, halt-points /
handbacks / flag-stops vocabulary) landing first; those remain the eventual, larger goal
but are explicitly not a precondition for this run, per the owner's direction.

**Track record, stated honestly, not oversold.** The 08-06 chain genuinely caught a real
defect (`fix/chain-gate-integration`'s own Case 4 caught Case 2's gate-window gap)
*because of* its serialized, full-ceremony structure — not despite it. The owner paused
the *next* chain the following morning because Fable's usage window ran out mid-run, not
because the method failed; that distinction was confirmed explicitly this session.

**Roles and models:**
- **Orchestrator: Opus.** Effort `high` as the sustained default for ongoing judgment
  calls (reading each sprint's diff, deciding whether to proceed); `xhigh` reserved for
  the single highest-stakes call — the final full-epic review, below. Mechanically:
  the orchestrating session drives each sprint directly via the `Agent` tool (**not**
  the `Workflow` tool) — one implementer-agent launch per sprint, read the result, judge,
  proceed. A pre-authored deterministic `Workflow` script doesn't naturally give the
  judgment pause this design wants between every stage (the per-sprint adversarial
  review, below, depends on that pause existing).
- **Sprint executors — right-sized per `RELEASE_ARC.md`'s own existing A1–A4 table**
  (independently re-derived this session from each sprint's own risk profile, landing
  on the same assignment — not just copied):
  - **A1 (`feat/corpus-polish` + `fix/experience-soft-retire`) — Opus.** Schema
    migration (`Experience`-level `retired` flag) + blast-radius audit across every
    unfiltered `Experience` consumer — a cascading-filter correctness tail, and
    `db/models.py` / `db/migrations/**` are C-10 gated surfaces (`docs/dev/blast-radius/
    experience-soft-retire.md` required before the first schema edit, per the
    owner-directed `feat/consumer-enumeration-gate` insert ahead of A1).
  - **A2 (`feat/compose-wait-ux` + item-20 fix) — Opus.** Compose settle-contract risk
    across 9 `_markComposeBgReload` call sites, with a live, named UX flake epic (19)
    directly behind it.
  - **A3 (`feat/role-summary-drafting`) — Opus.** A net-new LLM call end-to-end (prompt
    design, eval fixture, telemetry, pricing keys) — design work, not a bounded scope.
  - **A4 (`feat/prior-apps-pipeline`) — Sonnet, effort `xhigh`.** A well-specified
    mechanical move (remove the Tailor applications panel, rewrite one `activate()`) +
    one pinned-test rewrite.
- **Per-sprint adversarial reviewers: Sonnet, regardless of which sprint** — the owner's
  explicit call, not Opus. A deliberate, cheaper, independent-model check layered on top
  of the Opus implementation for A1–A3.

**Mechanics — stacked branches.** Each sprint's branch stacks on the **prior** sprint's
own tip, never off `main`. Nothing is pushed, PR'd, or merged until the epic's own
end — **one PR per epic to `main`**, matching `RELEASE_ARC.md`'s existing Final March
cadence rule verbatim ("One PR per epic to main; the owner reviews and merges").

**Per-sprint adversarial review, before that sprint's own commit.** After a sprint's own
gate is green, stage (don't commit) the diff; a Sonnet reviewer, instructed to *refute*
(not confirm) against the sprint's own brief, reads it. **Folds in item 52's** (the
gate-window class study, `docs/dev/gate-window-class-study.md`) cheap (~40s) structural
re-check — doc-links, hook modes, `python -m scripts.work_items check` — in the *same*
pass: item 52's whole failure mode is "nothing re-examines the final tree between gate
and commit," and this review already is that moment, for free. Confirmed
correctness/regression findings block the commit and get fixed + re-reviewed before it
lands; lower-severity findings get filed to the carry-forward ledger (`BOARD.md`) rather
than chased mid-sprint, matching the existing march cadence rule.

**Final review: Opus, effort `xhigh`, over the full epic diff, before the one PR.**
Formalizes — with an explicit effort tier — the cadence rule `RELEASE_ARC.md` already
states: "before each epic's PR: an adversarial diff review over the epic's full diff."

**The plan-approval gate — verified mechanics, not assumed.** This was resolved not via
any hand-touching of marker files (never legitimate without an explicit owner
escape-hatch direction — see the Binding rules below) but via a genuinely **verified**
property of `hooks/check-plan-approved.sh`, fixed on this session's own prior branch
(`fix/plan-approval-branch-switch-gap`, merged as PR #112, `cd83a2b`):

> **One legitimate `ExitPlanMode` approval, done once at the very start, covers editing
> across all four stacked sprint branches — as long as no intermediate branch is merged
> into `main` before the epic's own single final PR.** This holds by construction, since
> stacking exists precisely to defer that merge to the end. Proven this session via two
> isolated throwaway repros plus the real committed pytest suite
> (`tests/test_plan_approval_scoping.py`), not inferred from reading the hook's source
> alone — see `docs/dev/diagnosis/plan-approval-branch-switch-gap.md` for the evidence.

**Practical instruction for whoever runs this:** do the `EnterPlanMode` → write a plan
that explicitly names all four sprints plus the review/gate structure above (so the
approved plan's own scope legitimately covers all of it) → `ExitPlanMode` ceremony
**once**, at the start of sprint A1. Do not expect or need a fresh approval click
between A1→A2→A3→A4. If any intermediate branch is merged early for any reason, the
*next* edit attempt will correctly re-block (fail-closed, by design — this is the fix
working, not a bug); handle it via the normal ceremony, never by hand-touching a marker
file.

**Governance write-up — last, contingent, narrowly scoped.** If the run succeeds, write
up *this specific technique* (stacked-branch + per-sprint adversarial gate + final epic
review + right-sized models) as an optional execution method in governance —
**explicitly not** a general subagent-wave endorsement, and **explicitly not** the
broader "roll subagent methodology into waves" direction the owner has separately
flagged as a future interest. This is the last leg of the chain, contingent on the run
actually going well — not a precondition for starting it.

**How "Opus orchestrates" works mechanically — resolved, not open.** The owner flips the
orchestrating session to Opus via `/model`, and that session drives each stage directly
with the `Agent` tool (one implementer launch per sprint, read the result, judge, proceed)
— option (a) of the two the design session put to the owner, the other being a
pre-authored `Workflow` script, rejected because it doesn't give the judgment pause the
per-sprint adversarial review depends on. The owner confirmed this explicitly
("1, 2, 4, 5 confirmed"), together with the effort levels: **`high` sustained** across the
run, **`xhigh`** reserved for the single final full-epic review.

*Recovery note (session `551b775e`, 2026-08-08): the first draft of this handoff carried
the above as an unresolved open question. That was wrong — it had been settled in the
source conversation, and the record was lost when that session hung mid-close-out. Restored
from the transcript and re-confirmed with the owner. The owner also confirmed that the
per-sprint review is the **orchestrator's** adversarial review, not an owner approval
ceremony — so the single `ExitPlanMode` approval described above is correct as written —
and directed that all model assignments stand as designed (the owner fixed only
Opus-as-orchestrator and Sonnet-as-adversarial; the rest was the design's own call, and it
matches `docs/dev/RELEASE_ARC.md:1707-1710`'s committed A1–A4 table).*

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

`docs/dev/work/BOARD.md` is the authoritative live-item source (regenerate with
`python -m scripts.work_items board --write`; not hand-edited). Reproduced verbatim
from the board at this branch's tip, not re-derived.

**Open (1, unchanged this session):**
1. **50** — C-7 and C-10 are enforced by Claude Code hooks only — the clauses do not
   travel to other agents or an extracted governance package. Guards are not routed
   by `git_hook.py`, so only Claude Code enforces them; prose binds other agents.

**Blocked (3):** item 3 ([HUMAN] GitHub toggles), item 5 (grounding-score persistence
gap), item 8 (Compose-time rewrite latitude dial).

**Deferred (7):** items 4, 7, 24, 25, 41, 42, 43 — all owner-gated or explicitly
post-1.1.0-scheduled; see `BOARD.md` for each.

**Watching (13):** items 2, 16, 18, 23, 46, 47, 48, 49, 51, 52, 53, 54, 55; see
`BOARD.md` for each. **Item 52 is directly load-bearing for this design** — see "The
design" above, folded into the per-sprint adversarial review rather than left as a
separately-scheduled fix.

**Epics (6):** 19 (UX-suite flakiness umbrella, children 27–31), 36 (Final March epic A,
children 20, 34 — open; A1/A2 fold items 20/34 in per `RELEASE_ARC.md`), 37/38/39/40
(Final March epics B/C/D/E — blocked, sequenced after A). Epic 39 carries item 9 (stale
screenshots); epic 40 carries item 10 (the v1.1.0 tag itself, `depends on: 3, 6, 7, 9, 19`).

**Closed (20, unchanged):** see `BOARD.md` for the full list.

Open-only count stays **1**, well under the reduction-sprint threshold.

---

## Recurrences observed this session → guardrail authored

**One recognized recurrence this session.**

1. **A design worked out entirely in chat, never written durably, then lost when a
   different session inherited the handoff pointer — the exact failure the prior
   handoff's own "First move" section predicted for itself.** Recognized as a direct
   instance of charter C-8 ("durable before deep") the moment the owner reported the
   next agent had lost the design. **Mechanism authored:** this handoff itself — the
   full design is now a committed, pointer-verifiable file
   (`docs/dev/handoffs/docs-epic-a-wave-orchestration-design.md`), not a summary someone
   has to reconstruct from memory or ask the owner to repeat. There is no *gate* that
   prevents a future design conversation from staying chat-only until close-out (that
   would need a much broader mechanism than one branch can build), so the honest
   guardrail here is narrower: this specific design is now safe, and the pattern —
   "if a design conversation runs long and produces real decisions, write it down before
   the branch that discussed it closes, not after" — is worth carrying into the eventual
   governance write-up this design's own "last leg" step describes.

---

## What this branch should build

**Nothing further — this branch's scope is capturing the design, and it is done.**

Do not expand into actually running Epic A on this branch. Sprint A1 is explicitly the
next session's own scoped branch.

---

## First move

**Start sprint A1 directly — this is not an open owner decision the way the prior
handoff's "First move" was; the design above already resolves it.**

1. Read the **W-1 "Working model" posture paragraph** in `docs/governance/charter.md`
   before starting — "The design" above explains how this bounded, Epic-A-only run
   relates to it. Confirm with the owner that this session is on **Opus** (`/model`) at
   effort **`high`**; the mechanics are settled (see "The design"), but the model and
   effort are the owner's own switches to throw, not yours.
2. `EnterPlanMode` → write a plan explicitly naming all four sprints (A1–A4) plus the
   per-sprint adversarial-review / final-epic-review / stacked-branch structure from
   "The design" above, so the resulting approval's scope legitimately covers the whole
   chain → `ExitPlanMode` **once**.
3. Branch `feat/corpus-polish` (+ `fix/experience-soft-retire` per `RELEASE_ARC.md`'s
   A1 brief) off `main`, and begin sprint A1 per the roles/models table above.

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
