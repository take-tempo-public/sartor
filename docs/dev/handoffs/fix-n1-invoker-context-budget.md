<!-- provenance: schema=1 session=c931e519-38cc-4315-a98d-d01af66853b6 branch=fix/n1-invoker-context-budget commit=f465de2 actor=amodal1 agent=anthropic/claude-fable-5 generated_at=2026-08-14 -->

# Handoff — the run-5 method review landed its owner-approved mitigations; next is the owner-gated B2 run (terminal sprint), then the epic close

> **Where this sits (2026-08-14):** the owner directed a method review of run 5's
> invoker-context degradation; the review's conclusions were approved on screen
> ("this sounds like exactly what i had in mind. approved and continue") and its
> mitigations are landed on this branch. The next session is the **B2 pipeline
> run** — the Epic B terminal sprint — via
> `docs/dev/handoffs/epic-b-b2-brief.md`, **only on the owner's per-session run
> opt-in** (nothing in this handoff grants it). The scope source stays the
> owner-ratified sentence, single-homed in `epic-b-design-brief.md` §"Execution
> mode + authorization record" — cite it, never restate it.

**Branch to create:** `feat/ats-conformance` (the B2 sprint branch — cut by the
pipeline invoker per the B2 brief's First-move block, only after the owner's run
opt-in)
**Base branch:** `epic/b-render-ats` (this review branch ff-merges into it as its
last act; verify the tip with `git log -1 epic/b-render-ats` before cutting)

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

**Note for the pipeline invoker (this review's runbook change):** runbook step
0a now scopes the INVOKER role's mandatory kickoff reading to the runbook, the
sprint brief, the epic design brief (ratified sentence verbatim from its single
home), and `AGENT_FAILURE_PATTERNS.md` §5f — the full list above binds ordinary
branch sessions. Trim the list, never delegate the reading.

**Stream:** v1.1.0 Final March (`docs/dev/RELEASE_ARC.md` §"v1.1.0 Final
March") — five epics, A→E, strictly sequential.
**Sequencing rule:** one epic at a time; Epics C, D, E (board 38/39/40) stay
behind B.

- ~~Epic A (`epic/a-app-core`, board 36)~~ ✓ — merged `162c1dc` (PR #117).
- ~~`feat/n1-baseline-pipeline`~~ ✓ — item 84's authorized build (PR #125).
- ~~`fix/b1-stale-template-companions`~~ ✓ — sprint B1a (run 3).
- ~~`fix/n1-invoker-loop`~~ ✓ — run-3 polish (epic loop, item 89).
- ~~`fix/n1-scope-dedup`~~ ✓ — the hardening review (S1–S5).
- ~~`fix/b1-education-render`~~ ✓ — sprint B1b (run 5, first live escalation
  firing, clean boundary stop).
- ~~`fix/n1-invoker-context-budget`~~ ✓ — **THIS session: the run-5 method
  review's mitigations (see "What just landed").**
- **`feat/ats-conformance`** ← **next: B2, run 6, owner-gated — via
  `epic-b-b2-brief.md`'s First-move block (terminal sprint:
  `epicSprintIndex: 3, epicSprintCount: 3`, no `nextSprintBriefPath`).**
- Epic close-out to PR-ready → owner-gated epic PR (halt point 1) → then
  Epics C, D, E.

**What must NOT be started by the next session:** Epics C/D/E; any killed
control from the 2026-08-13 adversarial review
(`docs/dev/diagnosis/n1-pipeline-hardening-review.md` §"Adversarial review");
widening N past 1 (owner-reserved, §16.7); the item-93 session-shape decision
(that is the OWNER's, at Epic C planning — B2 runs under the standing ratified
sentence); rewriting `epic-b-b2-brief.md` (already written, already amended,
still valid); the watching-bucket reduction sprint.

---

## What just landed on `epic/b-render-ats`

One commit on `fix/n1-invoker-context-budget` (ff-merged to the epic tip), the
run-5 method review's owner-approved mitigations. Evidence dossier:
`docs/dev/diagnosis/n1-invoker-context-budget.md` (O1–O5, red-first record).

- **LF-explicit ledger writes + fail-closed CR sweep** — the C-11 mechanism the
  run-5 handoff declared owed: `newline="\n"` at both shard writers
  (`claude_context_hook.py`, `verify_doc_template.py`); red-first byte tests;
  `tests/test_verify_doc_template.py::TestLedgerWorkingTreeBytes` sweeps
  `docs/dev/ledger/*.jsonl` working-tree bytes; **81 stale-CRLF shards
  renormalized with zero content delta** (79 were pre-pin materializations —
  `git ls-files --eol` diagnosis in the dossier). The fixed writer's first
  organic append (a mid-gate `compacted` receipt) was byte-checked: 0 CR.
- **Run-report digests** (`n1-baseline.mjs`): `report.agents.<role>` entries
  are now bounded digests — full returns stay in the harness `journal.jsonl`
  (`report.journalRef`); escalation `verbatim` text and
  `accounting.claimedFilesWritten` stay complete (accumulated via `claimedRaw`).
  The invoker-context reducer for run 5's measured ~24k-char report.
- **Closer filing reconciliation**: the closer prompt enumerates all THREE
  obligation sources; `CLOSER_SCHEMA` requires `filingsOrdered`; a
  deterministic `report.filingDivergence` surfaces unfiled obligations
  (machine-readable subset only — stated C-0 limit). Run-5 divergence #1's
  answer.
- **Runbook**: invoker-scoped step-0a reading list (labeled unenforced);
  step-8 digest/journal wording; step-9 plan-stamp prediction corrected to the
  observed late-bind behavior.
- **Item 93 filed** (blocked, `decision_owner = "user"`): the Epic-C invoker
  session-shape decision — per-sprint fresh sessions vs continuous window +
  tripwire. Board regenerated (93 files, `work_items check` OK). CHANGELOG
  entry added. Gate green, **0 RERUN lines**; structural suite 46 passed.
  Wiki-relevance check: **0 relevant paths in this diff** (explicit no-edit
  finding, not a silent skip).

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

`docs/dev/work/BOARD.md` is authoritative; re-derived at this close (board
regenerated this session, `work_items check` OK, 93 files).

**Open — 1 top-level + 2 open epics:** **50** (C-7/C-10 enforced by Claude
Code hooks only — prose binds other agents). Epics **19** and **36** open —
**Epic A's item 36 status never flipped `closed` — at least the TWELFTH
handoff flagging it.** (Epic-nested open: 20, 34 under epic 36; 27–31, 57
under epic 19.)

**Blocked — 4 top-level:** **3** ([HUMAN] GitHub toggles), **5** (grounding-
score persistence gap), **8** (Compose rewrite latitude), **93** (Epic-C
invoker session-shape decision — NEW this session, owner's at Epic C
planning), plus epics **37, 38, 39, 40**; **9**, **10** epic-nested.

**Deferred (7):** **4, 7, 24, 25, 41, 42, 43** — see `BOARD.md`.

**Watching — 45 top-level:** 2, 16, 18, 23, 46, 47, 48, 49, 51, 52, 53, 54,
55, 56, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74,
76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 88, 90, 91, 92. **The
reduction-sprint flag stands — at least the TWELFTH handoff flagging it.**

- **Item 84** — this branch changed the run-report SHAPE (digests +
  `filingsOrdered`/`filingDivergence`); those paths' first LIVE exercise is
  the B2 run. `halt_point`/`hook_block` short-circuit routing and
  `harness_throw` remain unexercised live. Stays watching.
- From the hardening review's residue, still standing for the owner:
  `bypassPermissions` in machine-local settings undermines every hatch-based
  control repo-wide; the governance-hooks gate needs restructuring before any
  hook-based pipeline enforcement.

---

## Recurrences observed this session → guardrail authored

1. **Hook-written CRLF in ledger shards — the working-tree CR-byte class,
   4th+ instance, reproduced live in THIS session** (this session's own
   `--event consumed` append carried 1 CR byte, byte-counted before the fix).
   **Mechanism authored on this branch, fails closed:** `newline="\n"` at both
   writers (`scripts/enforcement/adapters/claude_context_hook.py`,
   `scripts/verify_doc_template.py`) + the working-tree sweep
   `tests/test_verify_doc_template.py::TestLedgerWorkingTreeBytes` (with the
   checker self-test), which fails the gate's pytest step on any CR byte in
   `docs/dev/ledger/*.jsonl`. This discharges the C-11 gap the run-5 handoff
   declared.
2. **Item-87 witness re-arming on a task notification — known counted class**
   (run-3 preflight first observed it; run 5 counted two). Once this session,
   on the invoker's own dossier edit after the gate's task notification;
   consumed with one re-run. No new mechanism — standing owner decision (a
   mid-run re-arm stopping a run is the owner's call), surfaced here per that
   decision.
3. **Invoker-session compaction — the §16.1.B accumulation class at the
   invoker level, second session running** (one `compacted` receipt,
   00:49:01Z, during this session's own gate run; run 5 had two). Partial
   mechanisms landed on this branch (the report-digest and reading-list
   reducers shrink the accumulation rate); **the full mechanism — bounding
   context age by construction via per-sprint sessions — is a scope-sentence
   change that is the owner's alone**, stated plainly: item 93 records the
   decision for Epic C planning (the filing is the surfacing, not the
   mechanism), and this session announced its own receipt per C-12 rather
   than working around it.

---

## What this branch should build

The next session is **run 6: the B2 sprint + the epic close**, owner-gated.
Numbered:

1. **Owner run opt-in first.** The opt-in is per-session and the owner's
   alone. If granted, proceed under the ratified scope sentence
   (`epic-b-design-brief.md` §"Execution mode + authorization record" — quote
   it, never restate it).
2. **Runbook step 0/0a** (`docs/dev/n1-baseline-pipeline.md`): preconditions,
   the invoker-scoped reading list (this review's change), the structural
   gate + live dispatch probe, scope reconciliation, ONE batched question set
   (expected: zero questions — the record settles them), deliberate item-87
   consumption, window statement.
3. **Invoke the sprint stage per `epic-b-b2-brief.md`'s First-move block**
   (`fix/ats-conformance` is NOT the branch name — the brief names
   `feat/ats-conformance`; `epicSprintIndex: 3, epicSprintCount: 3`, no
   `nextSprintBriefPath` — the terminal ceremony derives itself). **Expect the
   NEW report shape:** `agents` entries are digests (full returns in
   `journal.jsonl`), and a `filingDivergence` field, if present, means unfiled
   closer obligations — reconcile before finalize.
4. **Gates + finalize per runbook steps 2–8** (accounting check against
   `accounting.claimedFilesWritten`; gate #1; step-6 assertion — a mid-gate
   `compacted` ledger row is the documented benign drift; finalize; gate #2).
5. **The epic close-out to PR-ready** (terminal ceremony ran in-sprint; the
   epic-level obligations — wiki pass, grounding audits, epic-level
   adversarial review, experiment outcomes in item 84 — run ONCE here, per
   the epic brief), then **stop at halt point 1**: the epic PR is
   owner-gated (`python -m scripts.ci_wait <n>`; exit 3 = stop and look).

Scope is bounded to the owner-ratified sentence in `epic-b-design-brief.md`
§"Execution mode + authorization record" plus §"Epic B — `epic/b-render-ats`"
in `RELEASE_ARC.md`. Do not expand beyond what is listed there.

---

## First move

Verify this handoff's pointer (`python scripts/check_handoff_pointer.py
"<pointer line>"`) and stamp it consumed (`python
scripts/verify_doc_template.py docs/dev/handoffs/fix-n1-invoker-context-budget.md
docs/dev/AGENT_HANDOFF_TEMPLATE.md --event consumed --agent <agent>`), then
follow runbook step 0 — the B2 brief and the ratified scope sentence are the
operative instructions. **Do not invoke the pipeline without the owner's
explicit per-session run opt-in.**

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
