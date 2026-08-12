<!-- provenance: schema=1 session=e3099fd0-3033-413b-9d69-21027d396509 branch=feat/interrogative-prompt-witness commit=1f882b0 actor=amodal1 agent=anthropic/claude-fable-5 generated_at=2026-08-12 -->

# Handoff — interrogative-prompt witness BUILT, LIVE-FIRED, and CLOSED (item 87); Epic B run 1 (attempt 3) is yours

> **The single most important thing this handoff carries forward:** the
> pre-run branch the owner sequenced ahead of Epic B run 3 is DONE — both
> witness hooks are live, and they fired IN THEIR OWN BUILDING SESSION (the
> harness hot-loads settings.json hook edits mid-session). Your session is
> the first Epic B run these witnesses protect. Expect, by design: a
> one-line "the deliverable is the ANSWER" context reminder whenever a
> prompt classifies as a question, and ONE self-clearing PAUSE refusal on
> the first Edit/Write after every prompt/notification turn — a clean
> re-run of the identical call proceeds. **That is the mechanism working,
> not an obstacle; never treat the pause as a hook to route around.**
> Epic B is 0/2 — both losses were before any agent spawned. The B1a
> sprint brief is unused and still valid. Runbook **step 0a** (ONE batched
> preflight question set, then an uninterrupted window) is binding.

**Branch to create:** `fix/b1-stale-template-companions` (branch off `epic/b-render-ats`; sprint B1a, Epic B run 1 attempt 3)
**Base branch:** `main` (Epic B reaches `main` as ONE epic PR at the epic close — not now)

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
`docs/dev/handoffs/epic-b-design-brief.md` (standing context — read in full),
`docs/dev/n1-baseline-pipeline.md` (pipeline contract + runbook — **step 0a
is binding**), `docs/dev/handoffs/epic-b-b1a-brief.md` (run 1's sprint
brief, unused and still valid, carrying the "Kickoff preflight" section),
`docs/dev/work/items/0084-build-n1-baseline-pipeline.md` (all first-run
evidence), and `docs/dev/work/items/0087-interrogative-prompt-witness-hook.md`
(the witness protecting YOUR session — closed, live-fire evidence inside).

**Stream:** v1.1.0 Final March (`docs/dev/RELEASE_ARC.md:1645`) — five epics,
A→E, strictly sequential.
**Sequencing rule:** strictly sequential — one epic at a time, code first
(A–C), docs after (D), release last (E).
**Blocked until this stream lands:** Epics C, D, E (board 38/39/40) stay behind B.

- ~~Epic A (`epic/a-app-core`, board 36)~~ ✓ — merged `162c1dc` (PR #117).
- ~~`feat/n1-baseline-pipeline`~~ ✓ — item 84's authorized build, merged
  `31d2574` (PR #125). BUILT, NEVER RUN.
- ~~`docs/epic-b-briefs`~~ ✓ — Epic B design brief + B1a sprint brief, merged
  `5b8bafc` (PR #126).
- ~~`fix/n1-args-guard-hardening`~~ ✓ — refuter fixes mutant-verified, C-11
  CRLF gate, runbook step 0a. ff-merged into the epic branch, pruned.
- ~~`feat/interrogative-prompt-witness`~~ ✓ — this session: item 87's two
  witness hooks built, live-fired, item closed. ff-merged into the epic
  branch, pruned.
- **`epic/b-render-ats`** ← the epic umbrella, UNMERGED and staying that way
  until the epic close. Carries invocability fixes, the hardening, AND the
  witnesses.
- **`fix/b1-stale-template-companions`** ← **next: yours.** Cut it fresh off
  the epic tip, record the real base sha in the brief, run sprint B1a
  through the pipeline.
- B1a → B1b → B2 ← the three Epic B pipeline runs, none started.
- Epics C, D, E ← unchanged, sequenced behind B.

**What must NOT be started on this branch:** the B1b/B2 sprint briefs (each
run's closer writes the next — the test vector); widening N past 1 (owner
decision, §16.7); retiring or merging `AGENT_HANDOFF_TEMPLATE.md`; the
§16.5.2.2 ledger event extension; the §14.7 seam gate; the gate-launcher
utility (item 83, `decision_owner = "user"`); the watching-bucket triage
(41 items — its own session, flagged by seven handoffs now); fixing the
`BLOCKER_RULE_NAMES` C-10 undercount (a separate deliberate
governance-count correction, declared in
`tests/test_governance_hooks_gate.py`'s docstring).

---

## What just landed on `epic/b-render-ats`

`main` is untouched at `5b8bafc` (PR #126); nothing was pushed. On the epic
branch, this session's `feat/interrogative-prompt-witness` landed (ff-merged
after a green gate), containing work item 87:

- **`scripts/enforcement/guards/interrogative_witness.py`** (NEW) — the
  classifier (trailing `?` / interrogative lead word, the item's verbatim
  set), per-session state under the OS temp dir (`SARTOR_WITNESS_STATE_DIR`
  override), and the one-shot pause: first Edit/Write per recorded prompt
  refused once, state marked BEFORE refusing so the identical retry
  proceeds. Fail-open on every error path.
- **`scripts/enforcement/adapters/prompt_witness_hook.py`** (NEW) +
  **`hooks/interrogative-prompt-witness.sh`** (NEW) + a `UserPromptSubmit`
  entry in `.claude/settings.json` — the prompt-receipt half; always exit
  0; reminder injected via plain stdout on a question match.
- **Registry wiring** — `interrogative-witness` appended to
  `claude_dispatcher._GUARD_ORDER` (seven Edit|Write guards now) and
  `claude_hook._GUARD_NAMES`/`dispatch()`.
- **Gates amended deliberately** — `tests/test_governance_hooks_gate.py`
  (TENTH blocker rule — the pause reaches exit 2 and that file's taxonomy
  is mechanical; plus a FOURTH hook category `PROMPT_WITNESS_HOOKS` for the
  always-exit-0 UserPromptSubmit half, with wiring + never-gates tests);
  `tests/test_enforcement_core.py` (dispatcher exact set);
  `tests/test_enforcement_coverage.py` (+`docs/governance/enforcement.md`)
  — reach declared **Claude-only by NATURE, not by gap** (git hooks have no
  user prompt; the governance extraction can skip it without losing
  coverage).
- **`tests/test_interrogative_witness.py`** (NEW, 34 tests) — classifier
  spec cases, pause-once lifecycle, every fail-open path, adapter exit-0 —
  plus an autouse witness-state isolation fixture in `tests/conftest.py`
  (the item-33 temp-state-leak shape).
- **C-10 enumeration first:** `docs/dev/blast-radius/interrogative-prompt-witness.md`
  written before the first code edit (the registry is pin-tested even
  though not in the GATED table). Wiki: scoped self-update via
  scribe+auditor pairs on `governance-extraction` +
  `consistency-tracks-enforcement` (26 SUPPORTED / 1 pre-existing DRIFT
  re-anchored / 0 UNSUPPORTED); checkpoint deliberately not advanced
  (item 65); `docs/wiki/log.md` entry appended.
- **LIVE FIRE, same session:** the harness hot-loaded the new hooks
  mid-session; a task-notification turn armed the state (correctly silent —
  not a question) and the next Edit was refused once with the spec PAUSE
  message, proceeding on the identical retry. Item 87 closed on that
  sighting (its stated close condition), `verified_by` in the item file.

**Gate:** green on this tree — watched to `gate.log`'s own terminal line,
`RERUN`-swept (zero). Full disclosure of the run history (C-12): run 1
failed at `ruff format --check` (the new guard module — one-command fix);
run 2 failed at `pytest -m ux` on
`test_restore_scroll_y_loses_to_post_restore_growth`'s own control arm
("experiment invalid, not a defect finding", `filler_present=False`) — a
second member of item 46's control-arm-timing class, 5/5 isolated re-runs
pass on the same tree, filed in item 46 with the C-11 no-mechanism
declaration; run 3 green end-to-end. The exact counts are in the closing
commit message; confirm against `git log` rather than trusting prose
(C-12).

**Still true: no agent has ever been spawned by this pipeline.** agentType
bare-name dispatch, `phase()` grouping, escalation routing, `journal.jsonl`,
and the §11.9 accounting check remain UNVERIFIED. Your run is the first real
test of everything downstream of invocation.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

`docs/dev/work/BOARD.md` is authoritative (regenerate with `python -m
scripts.work_items board --write`). **Re-derived from the regenerated board
at this branch's close** (`python -m scripts.work_items check` reporting
OK), not copied from the previous handoff.

**Open — 1 top-level item + 2 open epics:** **50** (C-7/C-10 enforced by
Claude Code hooks only — prose binds other agents) is the only top-level
*item*; epics **19** and **36** are open. **Epic A's item 36 `status` was
never flipped `closed` — SEVENTH handoff flagging it, still unresolved.**

**Blocked — 3 top-level:** **3** ([HUMAN] GitHub toggles), **5**
(grounding-score persistence gap), **8** (Compose rewrite latitude,
evidence-gated on the PX-39 run), plus the Epic B–E epics **37, 38, 39,
40**; **9**, **10** are epic-nested.

**Deferred (7):** **4, 7, 24, 25, 41, 42, 43** — unchanged.

**Watching — 41 top-level:** 2, 16, 18, 23, 46, 47, 48, 49, 51, 52, 53, 54,
55, 56, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74,
76, 77, 78, 79, 80, 81, 82, 83, 84, 85. The reduction-sprint flag stands;
**seventh handoff flagging it.** (Item 87 entered and LEFT this bucket in
one session — closed on live-fire evidence, not left to watch.)

- **Item 84 is where all first-run evidence lives** and stays `watching` — a
  run that never reached its first agent is not first-run evidence.

**Nothing new was left unfiled by this session.** (The two facts this
session surfaced — settings.json hooks hot-load mid-session, and task
notifications count as prompt-receipt events for the witness — are filed in
item 87's closing update, which is their durable home.)

---

## Recurrences observed this session → guardrail authored

1. **The question-treated-as-work-order class itself (third recorded
   instance, recognized from the owner's 2026-08-12 dossier — this branch
   IS its C-11 response).** Mechanism authored, on this branch: the two
   witness hooks described above. The pause half fails CLOSED at the moment
   of momentum (one reachable exit-2 refusal per prompt, counted honestly
   as the tenth blocker rule); the classification half is a fail-open
   witness and is **labeled unenforced as a classifier** (C-0: intent
   classification is not deterministic — the mechanism forces the
   consideration; it cannot prove intent). Live-fire verified in this very
   session.
2. **Generated-artifact staleness caught by its own gate (BOARD.md stale
   after an item-status edit — recognized as the standing class the
   `work_items check` gate exists for).** No new mechanism authored and
   none needed: the existing gate fired, failed closed, and the regenerate
   command it names fixed it. Recorded here as the mechanism *working*,
   not as a gap.
3. **Formatting drift in a new module caught by the gate's `ruff format
   --check` step (recognized as the standing tool-induced-churn class,
   AGENT_FAILURE_PATTERNS §5d).** No new mechanism authored and none
   needed: the gate's existing format step is the fail-closed mechanism;
   it caught the drift on the first run and the fix was one command.
4. **A control-arm assertion failing as its own timing race under
   full-suite load (recognized as item 46's class — "the control assertion
   is itself a timing race" — second member observed:
   `test_restore_scroll_y_loses_to_post_restore_growth`, gate run 2, 5/5
   isolated passes on the same tree).** No mechanism authored on this
   branch, declared plainly (C-11): the right fix — skip-vs-fail semantics
   for an invalid experiment arm, or a load-tolerant trigger wait — is a
   design decision for the UX-flake cluster (items 46/47/62), not a
   drive-by edit from a hooks branch; an always-skipping experiment
   silently rots, which is presumably why its author made
   invalid-experiment a FAILURE. Filed in item 46's 2026-08-12 update;
   surfaced to the owner in this session's close-out summary.

---

## What this branch should build

**Epic B run 1, attempt 3 — the sprint itself, through the pipeline. Your
session is protected by the item-87 witnesses; expect their one-shot pause
and clean-retry rhythm as normal operation.**

1. **Kickoff preflight (runbook step 0a — do this FIRST, in one message):**
   read the standing context in full; run
   `python -m pytest tests/test_n1_pipeline.py tests/test_gitattributes_coverage.py -q`;
   confirm the per-session run opt-in with the owner **plus every other
   decision your reading surfaces, in ONE batch**; state the expected
   uninterrupted window. The opt-in is NOT discharged by this handoff.
2. **Cut `fix/b1-stale-template-companions` fresh off the epic tip** and
   record the real base sha in `docs/dev/handoffs/epic-b-b1a-brief.md`
   (replacing `<filled by the invoking session>`).
3. **Run sprint B1a** per the brief and
   `docs/dev/n1-baseline-pipeline.md` §"The runbook": the stale
   imported-template companion defect (`docx_to_persona_html.py:438-444`
   regen guard; skeleton-version stamp fix). The pipeline's first artifact
   is the diagnosis dossier at
   `docs/dev/diagnosis/b1-stale-template-companions.md` — hook-gated, never
   the fix first.
4. **Treat every escalation flag as the pipeline working** — surface its
   verbatim text to the owner and stop. A load/dispatch failure at the
   first agent spawn is an **experiment result** (C-0 limit 2 finally
   getting tested), not a sprint failure — record it in item 84 in the turn
   you see it.
5. **Close per the epic's cadence:** gate #1 → step-6 assertion → finalize
   stage → gate #2 → ff-merge into `epic/b-render-ats` → the B1b sprint
   brief written by this run's closer (the inter-sprint handoff under test).

Scope is bounded to §"Epic B — `epic/b-render-ats`" (B1,
`RELEASE_ARC.md:1899`) in RELEASE_ARC.md plus the pipeline work item 84. Do
not expand beyond what is listed there.

---

## First move

Verify this handoff's pointer (`python scripts/check_handoff_pointer.py`) and
stamp it consumed, then execute runbook step 0a — the preflight decision
batch — **before creating any branch or touching any code.** The branch cut
(`fix/b1-stale-template-companions` off `epic/b-render-ats`) happens after
the owner's batched go-ahead, and the plan-marker ceremony may precede your
first edit (one blocked edit flushes a stale stamp — see memory
`reference-flush-stale-plan-stamp-on-branch-not-main`; **never hand-create
the marker**). Your first Edit/Write of each turn may ALSO draw the
item-87 PAUSE — re-run the identical call; that is its designed rhythm,
distinct from any hook block that names a different guard.

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
