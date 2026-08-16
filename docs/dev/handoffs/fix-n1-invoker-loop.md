<!-- provenance: schema=1 session=1abaec04-51fd-4de4-b64c-8af5ab48055c branch=fix/n1-invoker-loop commit=d8f0a8f actor=amodal1 agent=anthropic/claude-fable-5 generated_at=2026-08-12 -->

# Handoff — run-3 polish round closed: the invoker epic loop exists, item 89 fixed, invoker model is the owner's choice; Epic B run 2 (B1b) is next

> **The single most important thing this handoff carries forward:** the next session is
> the **invoking (monitor) session for Epic B run 2 — sprint B1b through the N=1
> pipeline** — and every defect that made runs 1–3 fail at a process boundary has a fix
> committed on this branch. The epic's remainder (B1b → B2 → epic close + PR) is
> **pre-authorized, one sprint per run** (`epic-b-design-brief.md` §"Execution mode +
> authorization record", owner decision 2026-08-12). The invoker model is **whatever the
> owner set at launch — Fable and Opus are both authorized** (`RELEASE_ARC.md` §"Session
> models", dated amendment). Do not halt to re-ask either of those; re-asking a recorded
> authorization is the exact failure this branch closes (item 84, tenth failure).

**Branch to create:** `fix/b1-education-render` (branch off `epic/b-render-ats`;
sprint B1b — name and scope fixed in `docs/dev/handoffs/epic-b-design-brief.md` row 2,
do not rename)
**Base branch:** `epic/b-render-ats` — cut fresh off the epic tip **after** verifying
this branch's ff-merge landed (`git log -1 epic/b-render-ats` must show the polish-round
commit; do not cut from `d8f0a8f`, the pre-polish tip).

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

**Epic-specific reading, on top of the numbered list above (do not expect it
restated here):** `docs/dev/handoffs/epic-b-design-brief.md` (standing context —
read in full; its §"Execution mode + authorization record" now carries the
2026-08-12 owner authorization this handoff summarizes),
`docs/dev/n1-baseline-pipeline.md` (pipeline contract + runbook — **step 0a and
the new step 9, the epic loop, are the two steps whose absence killed run 3's
epic**), `docs/dev/handoffs/epic-b-b1b-brief.md` (**run 2's sprintBriefPath —
carries the exact Workflow invocation block**), and
`docs/dev/diagnosis/n1-invoker-loop.md` (this branch's evidence dossier: what
run 3 actually did, quoted from the committed record).

**Stream:** v1.1.0 Final March (`docs/dev/RELEASE_ARC.md` §"v1.1.0 Final
March") — five epics, A→E, strictly sequential.
**Sequencing rule:** strictly sequential — one epic at a time, code first
(A–C), docs after (D), release last (E).
**Blocked until this stream lands:** Epics C, D, E (board 38/39/40) stay behind B.

- ~~Epic A (`epic/a-app-core`, board 36)~~ ✓ — merged `162c1dc` (PR #117).
- ~~`feat/n1-baseline-pipeline`~~ ✓ — item 84's authorized build, merged
  `31d2574` (PR #125).
- ~~`docs/epic-b-briefs`~~ ✓ — Epic B design brief + B1a sprint brief, merged
  `5b8bafc` (PR #126).
- ~~`fix/n1-args-guard-hardening`~~ ✓ — args guard + CRLF gate + runbook step
  0a; ff-merged into the epic branch, pruned.
- ~~`feat/interrogative-prompt-witness`~~ ✓ — item 87's witness hooks;
  ff-merged into the epic branch, pruned.
- ~~`fix/b1-stale-template-companions`~~ ✓ — **sprint B1a, Epic B run 1 of
  3** — ff-merged at `d8f0a8f`. The pipeline's first end-to-end completion.
- ~~`fix/n1-invoker-loop`~~ ✓ — **this branch, the run-3 polish round**
  (see "What just landed"). ff-merged onto the epic tip.
- **`fix/b1-education-render`** ← **next: yours. Sprint B1b, Epic B run 2 of
  3, THROUGH the pipeline** — the invoking session drives; the pipeline's
  agents implement.
- `feat/ats-conformance` ← B2, Epic B run 3 of 3, after B1b. Sonnet
  implementer per the model table; its brief (`epic-b-b2-brief.md`) is
  written by **B1b's closer**, not by hand.
- Epic close: full ceremony + the one epic PR to `main` (owner-gated), after
  B2.
- Epics C, D, E ← unchanged, sequenced behind B.

**What must NOT be started on this branch:** B2's scope or its brief
(hand-authoring `epic-b-b2-brief.md` deletes the intra-epic closer artifact
under test — the pipeline writes it); widening N past 1 (owner decision,
§16.7); the epic PR before B2 lands; editing the consumed
`fix-b1-stale-template-companions.md` handoff (item 58 — a post-stamp
amendment C-9-blocks nothing now, but drifts its fingerprint against the
ledger); the watching-bucket triage (42 top-level items — at least the NINTH
handoff flagging it).

---

## What just landed on `epic/b-render-ats`

This branch's single commit (it carries this handoff), ff-merged onto
`d8f0a8f`. The owner-directed polish round between Epic B runs 1 and 2, fixing
every invoker-side defect run 3 exposed:

- **`.claude/workflows/n1-baseline.mjs`** — (1) both stage bodies wrapped in an
  error boundary: a harness throw (the class that killed three runs) now
  returns `status: 'escalated_to_owner'` with a `kind: 'harness_throw'`
  escalation carrying the error verbatim, instead of dying with
  `escalations: []`; caller-error guards deliberately stay outside it. (2)
  Item 89 fixed: `closeoutKind` (`'terminal'` default | `'intra_epic'`) +
  `nextSprintBriefPath` args, guards rejecting bad values by name, and the
  closer prompt branching between the full `AGENT_HANDOFF_TEMPLATE.md`
  ceremony and the light `EPIC_SPRINT_BRIEF_TEMPLATE.md` next-sprint brief.
  (3) The closer now runs the gate's static steps (`ruff check`,
  `ruff format --check`, `mypy`) on its own work before reporting (run 3's
  gate #1 red was a mypy error in closer-authored test code). (4) Agents
  report repo-relative forward-slash paths; the accounting union normalizes
  separators. (5) The implementer is told the brief's named fix site is a
  C-0 hypothesis to verify against the live repro (run 3's brief named an
  unreachable guard).
- **`docs/dev/n1-baseline-pipeline.md`** — **step 9, the epic loop** (merge →
  verify the closer-written next brief → **report the boundary to the owner
  immediately** → context check on external signals → continue or stop
  cleanly with the named resume state; full ceremony ONCE at the epic close);
  step 0a now opens with the scope reconciliation (epic authorization vs
  sprint brief — surface conflicts verbatim, never re-ask what the record
  grants); the stale "BUILT, NEVER RUN" header replaced with real run
  history; C-0 limit 1 updated (what run 3 attested vs what remains untested
  — **escalation routing has still never fired live**).
- **`docs/dev/RELEASE_ARC.md` §"Session models"** — dated owner amendment:
  invoking-session model for pipeline runs = **owner's choice of Fable or
  Opus, stated at invocation**; sprint-internal casting unchanged.
- **`docs/dev/handoffs/epic-b-design-brief.md`** — the same model amendment;
  the 2026-08-12 authorization record (epic remainder pre-authorized, invoker
  manages the flow); the item-89 wiring note; the BOARD-regen deferral
  corrected (the gate's `work_items check` binds it per-sprint —
  `scripts/gate.py:63`).
- **`docs/dev/handoffs/epic-b-b1b-brief.md`** — run 1's owed artifact,
  authored in the declared template format, carrying run 2's exact Workflow
  invocation block. **`EPIC_SPRINT_BRIEF_TEMPLATE.md`** gained the
  fix-site-is-a-hypothesis note.
- **`tests/test_n1_pipeline.py`** — new pins, red-first at `d8f0a8f` then
  green (`docs/dev/diagnosis/n1-invoker-loop.md` records the run):
  closer-ceremony branch, harness-throw capture, two new node-executed
  args-region arms (unknown `closeoutKind` rejected by name; `intra_epic`
  without `nextSprintBriefPath` rejected by name), the run-history header
  pin, the epic-loop step pin. 41 passed, zero reruns.
- **Work items** — 84 updated (the tenth failure named + fixes + amendments;
  stays `watching` — escalation routing untested, `decision_owner = "user"`);
  **89 CLOSED** (`verified_by` = the new closer-ceremony structural pin);
  board regenerated (`work_items check` → OK, 89 files). Session ledger shard
  committed. Wiki-relevance check run: 1 relevant path (`RELEASE_ARC.md`),
  verified no-edit, logged in `docs/wiki/log.md` (drift 17/75 — under the
  epic's 40-file margin).

**Gate (this branch, full `python -m scripts.gate` before commit,
2026-08-12):** terminal line verbatim — `gate: all steps passed.` Tier
summaries: `2571 passed, 2 skipped in 645.95s` (non-ux) and `146 passed, 2573
deselected, 1 xfailed, 1 xpassed in 585.67s` (ux — the `1 xpassed` is item
62's known nondeterministic non-strict xfail flip, already on the board, not a
new observation). Rerun sweep: **0 `RERUN` lines in the whole gate log** — a
clean pass, not a retried one.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

`docs/dev/work/BOARD.md` is authoritative (regenerate with `python -m
scripts.work_items board --write`). Re-derived from the board as regenerated at
this branch's close (`python -m scripts.work_items check` → OK, 89 files), not
copied from the previous handoff.

**Open — 1 top-level item + 2 open epics (unchanged):** **50** (C-7/C-10
enforced by Claude Code hooks only — prose binds other agents). Epics **19**
and **36** open — **Epic A's item 36 `status` was never flipped `closed` —
at least the NINTH handoff flagging it** (not this branch's scope; it needs
one session to verify Epic A's closure evidence and flip it).

**Blocked — 3 top-level (unchanged):** **3** ([HUMAN] GitHub toggles), **5**
(grounding-score persistence gap), **8** (Compose rewrite latitude,
evidence-gated on the PX-39 run), plus the Epic B–E epics **37, 38, 39, 40**;
**9**, **10** are epic-nested.

**Deferred (7, unchanged):** **4, 7, 24, 25, 41, 42, 43** — see `BOARD.md`
for one-line detail.

**Watching — 42 top-level (was 43; 89 closed this session, nothing new
filed):** 2, 16, 18, 23, 46, 47, 48, 49, 51, 52, 53, 54, 55, 56, 58, 59, 60,
61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 76, 77, 78, 79, 80,
81, 82, 83, 84, 85, 88. **The reduction-sprint flag stands — at least a NINTH
handoff flagging it, still not scheduled.**

- **Item 84 stays `watching`** — the pipeline has now completed end-to-end
  (run 3) and the invoker loop exists (this branch), but escalation routing
  — reviewers, halt points, and the new `harness_throw` boundary — has never
  fired live. The close call is the owner's.
- **Item 58** (post-stamp handoff amendment blocks the next session) —
  deliberately NOT given its mechanism on this branch (retro #6; a new
  enforcement surface, out of the polish round's scope; reason recorded in
  item 84's update). Still watching.

---

## Recurrences observed this session → guardrail authored

**Three recurrences recognized. Two got fail-closed mechanisms on this branch;
one got none, stated plainly.**

1. **Doc/mechanism drift (the class already on this board as items 54, 65,
   81, 82) — three instances this session:** the epic's declared cadence
   never wired into the closer prompt (item 89), the runbook header still
   claiming "BUILT, NEVER RUN" three runs after first execution, and the
   invoker's epic-flow role existing in the owner's authorization but no
   committed doc. **Mechanisms authored, all in `tests/test_n1_pipeline.py`,
   all red-first:** `test_closer_ceremony_branches_on_closeout_kind`,
   `test_harness_throw_is_captured_as_escalation`,
   `test_states_run_history_and_per_session_opt_in`,
   `test_epic_loop_step_present`. **Known limit (C-0):** these fail closed on
   the TEXT being deleted or reverted, not on a future agent declining to
   follow it — the runbook's step 9 behavior itself is pinned prose, labeled
   unenforced in that sense.
2. **The scoping conflict (item 84's tenth failure) — recognized as a member
   of the same drift class from the authorization side:** an epic-level owner
   authorization and a sprint-scoped handoff, never reconciled. **Mechanism:**
   the step-0a scope-reconciliation requirement (pinned by the existing
   `test_preflight_decision_batch_step_present` over the section) plus the
   authorization record itself now living in `epic-b-design-brief.md` where
   step 0a's mandatory reading finds it. Same C-0 limit as above — a pin on
   the text, not on compliance; stated, not papered over.
3. **The plan-marker wipe → repeat approval ceremony (run-3 retro #8's known
   per-run tax) — hit live this session:** the first Write after a fresh plan
   approval was blocked by `PLAN RETIRED` because the previous branch's stamp
   reconciled (merged + pruned) and archived the new approval with it. **No
   mechanism authored, and none is proposed:** the reconciler is itself a
   mechanism working as designed (stale approvals must not survive their
   branch); the cost is priced in retro #8 and the runbook's step 9 now tells
   every invoker to EXPECT one re-approval per sprint boundary. Surfaced to
   the owner here, per C-11's explicit allowance.

---

## What this branch should build

> **Superseded (2026-08-13, `fix/n1-scope-dedup`):** item 4's
> stop-after-one-sprint default below was one of the contradictory scope
> encodings that caused run 4's guess (item 84, eleventh failure). The single
> source for session scope is now the owner-ratified sentence in
> `epic-b-design-brief.md` §"Execution mode + authorization record" — read it
> there. This section is preserved unedited as the historical record.

**This branch's own work is complete — see "What just landed". The NEXT
session is Epic B run 2: sprint B1b through the pipeline.**

1. **Execute runbook step 0 + 0a** (`docs/dev/n1-baseline-pipeline.md`):
   preconditions (plan marker via the ceremony — expect a stale-stamp flush
   first; branch `fix/b1-education-render` cut off the verified epic tip),
   then the ONE preflight batch — structural gate
   (`python -m pytest tests/test_n1_pipeline.py tests/test_gitattributes_coverage.py -q`),
   the live dispatch probe
   (`.claude/workflows/n1-agent-probe.mjs`, STOP unless `ok_to_run`), the
   scope reconciliation, the run opt-in, the stated uninterrupted-window
   contract.
2. **Invoke the pipeline** with the exact args block in
   `docs/dev/handoffs/epic-b-b1b-brief.md` §"First move"
   (`closeoutKind: 'intra_epic'`, `nextSprintBriefPath:
   'docs/dev/handoffs/epic-b-b2-brief.md'`). The implementer verifies the
   education repro live FIRST (`generator.py:883-896` is an UNVERIFIED
   citation — the brief says so).
3. **Run the invoker's own steps 2–8**: accounting check, gate #1 (literal
   invocation, wait on the gate's own terminal line), step-6 assertion
   (ledger-receipt handling documented in step 4), finalize, gate #2.
4. **Run step 9, the epic loop**: ff-merge into `epic/b-render-ats`, verify
   `epic-b-b2-brief.md` exists (the intra-epic closer wrote it — if not,
   that is a pipeline defect to surface), **report the boundary to the owner
   immediately**, context check → continue into B2 only if the owner's
   invocation scoped this session to more than one sprint; otherwise close
   THIS session properly: the full close-out ceremony for
   `fix/b1-education-render`'s session happens per the checklist below, and
   the next handoff scopes run 3 (B2, `closeoutKind: 'terminal'` — the
   epic's last sprint).

Scope is bounded to §"Epic B — `epic/b-render-ats`" (B1, second bullet) in
`RELEASE_ARC.md` plus `docs/dev/handoffs/epic-b-b1b-brief.md`. Do not expand
beyond what is listed there.

---

## First move

Verify this handoff's pointer (`python scripts/check_handoff_pointer.py`) and
stamp it consumed (`python scripts/verify_doc_template.py … --event consumed`),
then read the documents above — the epic-specific list included — then execute
runbook step 0a as deliverable 1 describes, **before creating any branch or
touching any code**. The invoking model is whatever the owner set at launch:
**Fable and Opus are both authorized for this role** (RELEASE_ARC §"Session
models", 2026-08-12 amendment) — proceeding on either requires no question.
The plan-marker ceremony precedes your first edit (one blocked edit flushes
the stale stamp — never hand-create the marker); the item-87 witness pause
takes one deliberate Edit/Write to consume before the first Workflow call
(runbook step 0a names why). The branch cut happens only after the preflight
batch's go-ahead **and** after `git log -1 epic/b-render-ats` shows this
branch's polish-round commit.

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
