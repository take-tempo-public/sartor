<!-- provenance: schema=1 session=7225a213-c3ac-4820-aa36-61fcb2332248 branch=fix/n1-scope-dedup commit=43dd351 actor=amodal1 agent=anthropic/claude-fable-5 generated_at=2026-08-13 -->

# Handoff — hardening review closed: the scope sentence is owner-ratified and single-sourced; the next session executes the ENTIRE remainder of Epic B

> **The single most important thing this handoff carries forward — the
> owner-ratified scope sentence, quoted verbatim from its single source
> (`epic-b-design-brief.md` §"Execution mode + authorization record"; cite it,
> never restate it):**
>
> > The pipeline test is the ENTIRE remaining Epic B — B1b, then B2, then the
> > epic close-out to PR-ready — run continuously by one invoking session that
> > manages the flow at every boundary. Stopping before PR-ready is a failure
> > unless an escalation is awaiting the owner or the owner has said stop;
> > partial completion is not success.
>
> **Stopping after one sprint is not partial success — it is the recurring
> failure mode this handoff exists to prevent** (it has already cost the owner
> a lost day once, and near-missed twice more; item 84, tenth and eleventh
> failures). If you cannot complete the full remainder, you FAIL GRACEFULLY
> AND LOUDLY: state exactly where you stopped, why, and the resume state —
> never stop silently, never perform a quiet close-out mid-epic, and never
> respond to your own failure with unrequested fix proposals (that reaction
> class is documented: `docs/dev/diagnosis/n1-pipeline-hardening-review.md`
> D0a/D4b).

**Branch to create:** `fix/b1-education-render` (sprint B1b — name fixed in
`epic-b-design-brief.md` row 2, do not rename; subsequent sprint branches per
the same table)
**Base branch:** `epic/b-render-ats` — cut each sprint branch fresh off the
epic tip, only after verifying this branch's ff-merge landed
(`git log -1 epic/b-render-ats` must show this branch's commits).

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
restated here):** `docs/dev/handoffs/epic-b-design-brief.md` (standing context
— read in full; carries the owner-ratified scope sentence and the epic
authorization record), `docs/dev/n1-baseline-pipeline.md` (contract + runbook
— steps 0/0a and 9 are the ones whose absence or corruption killed prior
runs; **the sprint-stage args contract changed on this branch — see "What
just landed"**), `docs/dev/handoffs/epic-b-b1b-brief.md` (run 2's
sprintBriefPath — carries the exact, updated Workflow invocation block),
`docs/dev/diagnosis/n1-pipeline-hardening-review.md` (the 0-for-4
investigation, root causes, and the adversarial-review verdicts — read before
proposing ANY pipeline change; the killed proposals are killed for cited
reasons, do not resurrect them), and `docs/dev/diagnosis/n1-scope-dedup.md`
(this branch's dossier).

**Stream:** v1.1.0 Final March (`docs/dev/RELEASE_ARC.md` §"v1.1.0 Final
March") — five epics, A→E, strictly sequential.
**Sequencing rule:** one epic at a time; Epics C, D, E (board 38/39/40) stay
behind B.

- ~~Epic A (`epic/a-app-core`, board 36)~~ ✓ — merged `162c1dc` (PR #117).
- ~~`feat/n1-baseline-pipeline`~~ ✓ — item 84's authorized build (PR #125).
- ~~`fix/b1-stale-template-companions`~~ ✓ — sprint B1a, Epic B run 1 of 3;
  the pipeline's first end-to-end completion; ff-merged at `d8f0a8f`.
- ~~`fix/n1-invoker-loop`~~ ✓ — the run-3 polish round (epic loop, item 89,
  harness_throw); ff-merged at `dc2f0cf`.
- ~~aborted run 4 + `docs/n1-0for4-analysis`~~ ✓ — the false "clean" record,
  corrected at `43dd351`; branch folded and pruned.
- ~~`fix/n1-scope-dedup`~~ ✓ — **this branch, the owner-directed hardening
  review** (see "What just landed"). ff-merged onto the epic tip.
- **`fix/b1-education-render`** ← **next: yours. Sprint B1b, then WITHOUT
  ENDING THE SESSION: B2 (`feat/ats-conformance`), then the epic close-out to
  PR-ready — the ENTIRE remainder, per the ratified sentence above.**

**What must NOT be started or done by the executor session:** widening N past
1 (owner-reserved, §16.7); hand-authoring `epic-b-b2-brief.md` (B1b's closer
writes it — the inter-sprint handoff under test); the epic PR merge itself
(halt point 1 — PR-READY is the target; push/PR/merge need the owner);
resurrecting any control the adversarial review killed (Workflow-matcher
gate, blocking Stop hook, epic-plan JSON, in-pipeline probes, gate receipts —
reasons cited in `n1-pipeline-hardening-review.md`); ANY pipeline or
governance redesign, especially as a reaction to a failure mid-run.

---

## What just landed on `epic/b-render-ats`

This branch (base `43dd351`; the cleanup commit corrected run 4's false
"scope reconciliation clean" record and landed the 0-for-4 analysis with a
verification addendum). The owner-approved survivors of a three-reviewer
adversarial pass — full verdicts in
`docs/dev/diagnosis/n1-pipeline-hardening-review.md`:

- **S1 — the scope sentence is single-sourced and owner-ratified.** The
  poisoned "(default: one sprint per session)" parenthetical in
  `epic-b-design-brief.md` is DELETED (it was an agent codification of an
  ambiguous owner utterance and directly caused run 4's guess); the ratified
  sentence quoted at the top of this handoff replaced it. The stale
  one-sprint arm in `fix-n1-invoker-loop.md` carries a superseded banner
  (re-stamped; ledger row `39f84e140005`).
- **S2 — `closeoutKind` is no longer a caller decision.**
  `.claude/workflows/n1-baseline.mjs` sprint stage now REQUIRES
  `epicSprintIndex`/`epicSprintCount` (1-based) and DERIVES the ceremony
  (index < count → intra_epic + `nextSprintBriefPath` required; index ==
  count → terminal). A caller-supplied `closeoutKind` is rejected by name.
  Consumers updated (runbook step 1 + args table + step 9; the b1b brief's
  First-move block now passes `epicSprintIndex: 2, epicSprintCount: 3`).
  Red-first: the derivation arm failed on the pre-fix script, then 43/43
  structural green. Enumeration: `docs/dev/blast-radius/n1-scope-dedup.md`.
- **S3 — CR-byte working-tree gate** (`TestWorkflowWorkingTreeBytes` in
  `tests/test_n1_pipeline.py`): no CR bytes in `.claude/workflows/*.mjs`
  working-tree copies, probe included — the class that rejected run 1's
  invocation twice, and it was live again in a ledger shard this very day.
- **S4 — the epic-state banner.** `scripts/enforcement/adapters/
  claude_context_hook.py` now injects Epic B's remainder into EVERY fresh
  session's context at SessionStart, derived from committed briefs at the
  epic tip (brief-existence — survives the runbook's own branch pruning). A
  silently stopped epic can no longer hide from the next session. Context,
  not a gate; it retires itself when the epic lands on main.
- **S5 — log-only harness-measurement hooks** staged in
  `.claude/settings.local.json` (machine-local): PreToolUse(Workflow) and
  Stop payloads append to `~/.claude/sartor-probe-*.log`, always exit 0.
  **The executor session's step-0a probe call produces the first
  measurements passively — recording them is one of your kickoff duties
  (below).**

**Gate (this branch, full `python -m scripts.gate`, 2026-08-13):** terminal
line verbatim — `gate: all steps passed.` Rerun sweep: **0 `RERUN` lines** —
a clean pass, not a retried one. (First gate attempt was collateral-killed by
the harness stopping its background waiter — the gate log froze mid-ux-tier;
diagnosed, orphans killed, full re-run green. The kill-proof shape: launch
`nohup python -m scripts.gate > gateN.log 2>&1 &` from a Bash call that exits
immediately, then watch the log with a Monitor until-grep on the terminal
line. Never leave a long-lived background waiter holding the gate.)

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

`docs/dev/work/BOARD.md` is authoritative (`python -m scripts.work_items
board --write`); re-derived at this close — the gate's `work_items check`
passed with the board fresh; no items were filed or closed this session.

**Open — 1 top-level item + 2 open epics (unchanged):** **50** (C-7/C-10
enforced by Claude Code hooks only — prose binds other agents; note the
non-Claude-agent asymmetry also applies to this branch's S4 banner and S5
probes, Claude-harness-only by construction, declared per C-11). Epics **19**
and **36** open — **Epic A's item 36 status never flipped `closed` — at
least the TENTH handoff flagging it.**

**Blocked — 3 top-level (unchanged):** **3** ([HUMAN] GitHub toggles), **5**
(grounding-score persistence gap), **8** (Compose rewrite latitude), plus
epics **37, 38, 39, 40**; **9**, **10** epic-nested.

**Deferred (7, unchanged):** **4, 7, 24, 25, 41, 42, 43** — see `BOARD.md`.

**Watching — 42 top-level (unchanged):** 2, 16, 18, 23, 46, 47, 48, 49, 51,
52, 53, 54, 55, 56, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71,
72, 73, 74, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 88. **The
reduction-sprint flag stands — at least a TENTH handoff flagging it.**

- **Item 84 stays `watching`** — this branch added hardening, not run
  evidence; escalation routing has STILL never fired live.
- **Item 58** (post-stamp handoff amendment) — exercised deliberately this
  session (superseded banner + re-stamp on `fix-n1-invoker-loop.md`); still
  no mechanism, still watching.
- New this session, durable homes in `n1-pipeline-hardening-review.md`
  §residue (not board-filed — the watching bucket is already flagged for
  reduction): `bypassPermissions` in machine-local settings undermines every
  hatch-based control repo-wide (owner attention); the governance-hooks gate
  needs deliberate restructuring BEFORE any hook-based pipeline enforcement
  is ever attempted; S5 measurement results must be recorded in the review
  doc and the probe hooks then deleted.

---

## Recurrences observed this session → guardrail authored

1. **The scope-restatement class — fourth-plus instance, recognized from the
   record itself** (runs 3/4, the polish inversion, the prompt rewrite; this
   session's own kickoff prompt carried the corrupted one-sprint form).
   Mechanisms authored on this branch: the ceremony half now **fails
   closed** — `n1-baseline.mjs` rejects a caller `closeoutKind` by name and
   derives it from required position args, pinned red-first in
   `tests/test_n1_pipeline.py`. The sentence half is prose by adversarial
   verdict (every blocking variant was killed for cited reasons):
   single-sourced + owner-ratified + contradictions deleted, and **plainly
   labeled unenforced** — surfaced to the owner in the approval and here.
2. **The CRLF/working-tree byte class — third instance, recognized live**
   (CR bytes in a ledger shard while `git check-attr` reported `eol: lf`).
   Mechanism: `TestWorkflowWorkingTreeBytes` (fails closed on any CR byte in
   a working-tree workflow script; checker self-test proves teeth).
3. **The silent-stop class** (run 3's lost day). Mechanism: the S4
   epic-state banner — deterministic context injection at every session
   start; NOT fail-closed (a banner cannot force behavior), stated plainly:
   the blocking variants were adversarially killed, visibility is what
   survived, and the residual (a sincerely-wrong stop) is declared in the
   review doc and to the owner.
4. **Untrustworthy background-task status — recognized as run-3 retro #9's
   class, hit live this session** (the harness killed the gate's background
   waiter and took the gate's process tree with it; the frozen log was the
   only tell). No NEW mechanism authored: the runbook already prescribes
   waiting on the gate's own terminal line, and the kill-proof launcher
   shape is now recorded in "What just landed" — surfaced here and to the
   owner rather than silently absorbed.

---

## What this branch should build

**This branch's own work is complete — see "What just landed". The NEXT
session is the executor: the ENTIRE remainder of Epic B through the
pipeline, per the ratified sentence quoted at the top of this handoff.**

1. **Kickoff (runbook steps 0 + 0a, once per sprint):** preconditions (plan
   ceremony — expect a stale-stamp flush; never hand-create the marker);
   the ONE preflight batch — structural gate (`python -m pytest
   tests/test_n1_pipeline.py tests/test_gitattributes_coverage.py -q`), the
   live dispatch probe (`.claude/workflows/n1-agent-probe.mjs`, STOP unless
   `ok_to_run`), scope check against the ratified sentence (any conflict
   between records is surfaced VERBATIM and stops the session — never
   resolved by guess), the item-87 pause consumption. **Plus, first sprint
   only: record the S5 measurements** — after the probe call, read
   `~/.claude/sartor-probe-pretooluse-workflow.log` and
   `~/.claude/sartor-probe-stop.log`, record what fired and what the
   payloads carry in `docs/dev/diagnosis/n1-pipeline-hardening-review.md`
   (a "nothing fired" result is a finding too), then delete the S5 entries
   from `.claude/settings.local.json`.
2. **Run B1b** with the exact First-move block in `epic-b-b1b-brief.md`
   (`epicSprintIndex: 2, epicSprintCount: 3, nextSprintBriefPath:
   'docs/dev/handoffs/epic-b-b2-brief.md'`). Invoker steps 2–8: accounting
   check, gate #1 (kill-proof shape above, wait on the gate's own terminal
   line), step-6 assertion (ledger-receipt handling per runbook step 4),
   finalize, gate #2, rerun sweep.
3. **Step 9 at the B1b boundary:** ff-merge, verify `epic-b-b2-brief.md`
   exists (missing = pipeline defect: surface it, never improvise a brief),
   **report the boundary to the owner immediately** — then CONTINUE into B2
   (`feat/ats-conformance`, `epicSprintIndex: 3, epicSprintCount: 3` —
   terminal derives itself). Continuing is the default the ratified sentence
   grants; a context-degradation signal (external: compaction receipts, the
   threshold banner) means stop CLEANLY with the exact resume state named —
   that is the ONLY self-judged early stop the records permit.
4. **After B2 + its gates:** the epic close-out per the epic brief's
   deferred list (wiki pass + `.last_ingest_sha`, grounding audits, the full
   `AGENT_HANDOFF_TEMPLATE.md` ceremony, the epic-level adversarial review,
   experiment outcomes recorded in item 84) to **PR-READY** — then stop and
   hand the owner the PR decision (halt point 1; push/PR/merge are
   owner-only, always).
5. **Stop-and-surface conditions (each one verbatim, then STOP):**
   `status: 'escalated_to_owner'` (surface the flag's verbatim text — that
   is the pipeline WORKING); any hook block (name + message); a red gate
   (`gate: FAILED` + the failing tail); any records conflict found at
   preflight; any harness throw or contract violation; the external
   context-degradation signal (stop cleanly, resume state named); an owner
   stop. **Proceed autonomously on everything else the records already
   grant** — the sprint sequence, the continue-at-boundary default, the
   intra-epic ff-merges, the invoker model the owner set at launch;
   re-asking a recorded grant is itself a preflight defect.
6. **If you cannot complete the full remainder:** fail gracefully and
   loudly. One message: where you stopped, why (the verbatim evidence), what
   ran and what did not, the exact resume state (epic tip sha, next brief
   path, the runbook). Do NOT perform a quiet terminal close-out mid-epic,
   do NOT paper over the gap, do NOT propose fixes or redesigns — the owner
   decides what happens next.

Scope is bounded to §"Epic B — `epic/b-render-ats`" (B1 second bullet + B2)
in `RELEASE_ARC.md` as mapped by `epic-b-design-brief.md` rows 2–3.
Do not expand beyond what is listed there.

---

## First move

Verify this handoff's pointer (`python scripts/check_handoff_pointer.py
"<pointer line>"`) and stamp it consumed (`python
scripts/verify_doc_template.py docs/dev/handoffs/fix-n1-scope-dedup.md
docs/dev/AGENT_HANDOFF_TEMPLATE.md --event consumed --agent <agent>`), then
read the documents above — the epic-specific list included — then execute
deliverable 1 (kickoff + S5 measurement recording) **before creating any
branch or touching any code.** The invoking model is whatever the owner set
at launch — Fable and Opus are both authorized (RELEASE_ARC §"Session
models"); proceeding on either requires no question. The owner's message
delivering this pointer is the run opt-in for the entire remainder; the only
questions you may ask at kickoff are ones the records genuinely do not
settle, batched in ONE message.

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
