<!-- provenance: schema=1 session=06958323-c75b-4863-b27b-cf0d44a07c43 branch=docs/epic-b-briefs commit=31d2574 actor=amodal1 agent=anthropic/claude-fable-5 generated_at=2026-08-11 -->

# Handoff — Epic B briefs authored; the next session is the first authorized N=1 pipeline run (Opus)

> **The single most important thing this handoff carries forward:** the owner
> authorized Epic B as the **first test of the N=1 baseline pipeline** — the whole
> epic, sprint by sprint, with the inter-sprint handoff as an explicit test vector
> and the owner watching the console as live interrupt. The standing context is
> `docs/dev/handoffs/epic-b-design-brief.md`; run 1's sprint brief is
> `docs/dev/handoffs/epic-b-b1a-brief.md`. **The run session still confirms the
> run with the owner at its start** — this handoff records the decision; it does
> not discharge that confirmation. The invoking session runs on **Opus** (RELEASE_ARC
> §"Session models"). Do NOT pre-author the B1b or B2 sprint briefs — each run's
> closer writes the next one; that is the handoff step under test.

**Branch to create:** `epic/b-render-ats` (branch off `main`), then per-sprint
branches per the design brief's mapping table (run 1:
`fix/b1-stale-template-companions` stacked on the epic branch tip).
**Base branch:** `main`.

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
`docs/dev/handoffs/epic-b-design-brief.md` (the epic's standing context — read in
full), `docs/dev/n1-baseline-pipeline.md` (the runbook is the contract for every
run), `docs/dev/handoffs/epic-b-b1a-brief.md` (run 1's sprint brief),
`docs/dev/RELEASE_ARC.md` §"Epic B" (scope of record).

**Stream:** v1.1.0 Final March (`docs/dev/RELEASE_ARC.md:1645`) — five epics, A→E,
strictly sequential.
**Sequencing rule:** strictly sequential — one epic at a time, code first (A–C),
docs after (D), release last (E).
**Blocked until this stream lands:** Epics C, D, E (board 38/39/40) stay behind B.

- ~~Epic A (`epic/a-app-core`, board 36)~~ ✓ — merged `162c1dc` (PR #117).
- ~~Post-Epic-A interval branches~~ ✓ — findings, robustness pass, item 75 fix,
  drift reconcile (PRs #121–#124).
- ~~`feat/n1-baseline-pipeline`~~ ✓ — item 84's authorized build, merged `31d2574`
  (PR #125). BUILT, NEVER RUN.
- ~~**This branch (`docs/epic-b-briefs`)**~~ — Epic B design brief + B1a sprint
  brief authored; Epic B execution mode decided (first pipeline test). Done.
- `epic/b-render-ats` ← next: Epic B, board 37 — the first authorized pipeline
  run (Opus session), three runs per the design brief's mapping table.
- Epics C, D, E ← unchanged, sequenced behind B.

**What must NOT be started on the next branch:** pre-authoring the B1b/B2 sprint
briefs (the closer's job — the test vector); widening N past 1; retiring or
merging `AGENT_HANDOFF_TEMPLATE.md`; the §16.5.2.2 ledger event extension; the
§14.7 seam gate; the gate-launcher utility (item 83, `decision_owner = "user"`);
the watching-bucket triage (41 items — still owed, its own session if the owner
schedules it, flagged by four handoffs running).

---

## What just landed on `main`

**Nothing merged yet from this branch at writing time** — this handoff is written
pre-PR, per the close-out checklist. `main` is at `31d2574` (PR #125).

This branch (`docs/epic-b-briefs`) authored Epic B's planning artifacts — Fable
design/planning scope per RELEASE_ARC §"Session models" — after the owner decided
Epic B's execution mode on screen (2026-08-11, this session):

- `docs/dev/handoffs/epic-b-design-brief.md` — the epic's standing context and
  the file `epicBriefPath` points at: execution mode + authorization record,
  sprint → pipeline-run mapping (3 runs: B1a/B1b Opus, B2 Sonnet), branch
  topology (real `fix/*` branches ff-merged into `epic/b-render-ats` — a stated
  divergence from Epic A so `require-evidence-before-fix` stays live), the
  close-out-interval declaration (light per sprint, full at epic close,
  re-argued not inherited), the coherence-drift declaration (none scheduled,
  justified), acceptance criteria, and what the experiment measures. All
  path:line cites verified against HEAD `31d2574`; two drifted RELEASE_ARC
  anchors re-anchored with a C-0 note (flagged, deliberately not fixed in
  RELEASE_ARC, per the standing flag-don't-fix precedent).
- `docs/dev/handoffs/epic-b-b1a-brief.md` — run 1's sprint brief from
  `EPIC_SPRINT_BRIEF_TEMPLATE.md`, every section present: scope = the
  stale-companion regen guard (`docx_to_persona_html.py:438-444`), first move =
  the C-7 diagnosis dossier, explicit out-of-scope list.
- Both files live in `docs/dev/handoffs/` deliberately — an
  `IRRELEVANT_PREFIXES` entry in `scripts/wiki_relevance.py`, so no C-10 gated
  edit and no wiki drift (the §15.4 placement rationale).
- This session's provenance-ledger file
  (`docs/dev/ledger/06958323-c75b-4863-b27b-cf0d44a07c43.jsonl`) committed here.
- Memory updated: `project-chain-execution-experiment-and-vectoring-directives`
  carries the 08-11 execution-mode decision.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

`docs/dev/work/BOARD.md` is authoritative (regenerate with `python -m
scripts.work_items board --write`). Re-derived from the board at this branch's
close — **unchanged from the previous handoff; nothing filed this session.**
Item 82's caveat stands: the header's counts mix two populations (all-items vs
top-level) — re-derive, don't trust either number blindly.

**Open (top-level 1; header says 4 incl. epic-nested):** **50** (C-7/C-10
enforced by Claude Code hooks only — prose binds other agents). Epic-nested
opens: see board epics 9/19/36 — the flag that Epic A's item 36 `status` was
never flipped `closed` **still stands unresolved** (fourth handoff flagging it).

**Blocked (3):** **3** ([HUMAN] GitHub toggles), **5** (grounding-score
persistence gap), **8** (Compose rewrite latitude, evidence-gated on the PX-39
run).

**Deferred (7):** **4, 7, 24, 25, 41, 42, 43** — unchanged, all owner-gated or
post-1.1.0; see `BOARD.md` for one-line detail.

**Watching (41):** **2, 16, 18, 23, 46, 47, 48, 49, 51, 52, 53, 54, 55, 56, 58,
59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 76, 77, 78, 79,
80, 81, 82, 83, 84, 85** (top-level; item 57 is epic-nested under 19).

- **Item 84 is the one the next session acts on** — `watching`, awaiting
  first-run evidence; the run session's report is that evidence.
- The reduction-sprint flag on the watching bucket stands (fourth handoff
  flagging it): the triage session is owed, not discharged.

---

## Recurrences observed this session → guardrail authored

**Two recurrences recognized. No new mechanism authored for either — each landed
in an existing fail-closed mechanism that fired correctly, and the reason is
stated plainly per C-11.**

1. **Stale plan-approval marker blocking the first Write — the documented
   `reference-flush-stale-plan-stamp-on-branch-not-main` class.** Recognized
   immediately (the prior handoff predicted it). The `check-plan-approved.sh`
   hook blocked with "PLAN RETIRED" for the merged `feat/n1-baseline-pipeline`
   stamp; one blocked edit on the branch flushed it, then a clean
   EnterPlanMode → ExitPlanMode ceremony. The hook IS the fail-closed
   mechanism and worked in this variant too; no new mechanism needed.
2. **RELEASE_ARC cite drift — two §Epic B anchors no longer matched HEAD**
   (`corpus_to_json_resume.py:855-878` → actual `909-932`;
   `experiences.py:118-122,214-220` → actual `119-122,222-227`). Recognized as
   the known cite-rot class (item 65; the A1 citation-drift audit precedent in
   `epic-a-chain-design-corrections.md`). Response: every cite re-verified
   against HEAD before embedding; the design brief carries the corrected
   anchors plus a C-0 drift note; RELEASE_ARC deliberately not edited (the
   flag-don't-fix precedent for inherited drift). No new mechanism — the class
   already has its governance (§17 cite-rot pass) and the countable-claim
   canary covers wiki pages; a RELEASE_ARC-cite checker would be new
   enforcement surface, which is an owner call (§11.6.5), surfaced here.

**Carried observation (inherited, still unfixed):** `AGENTS.md:266` cites
"charter D5, cite-don't-restate" — a mislabel (charter D-5 is open-standards
mechanics); two prior handoffs flagged it; this branch did not touch AGENTS.md
either. The note stands for the next agent who does.

---

## What this branch should build

<!-- This branch's own work is complete — see "What just landed" above. The NEXT session: -->

1. **Run 1 of the Epic B pipeline test** — confirm the run with the owner, then
   follow `docs/dev/n1-baseline-pipeline.md` §"The runbook" exactly: create
   `epic/b-render-ats` off `main`, then `fix/b1-stale-template-companions` on
   its tip; plan ceremony (live plan-approval marker is precondition 0);
   `Workflow({scriptPath: '.claude/workflows/n1-baseline.mjs', args: {stage:
   'sprint', sprintBriefPath: 'docs/dev/handoffs/epic-b-b1a-brief.md',
   epicBriefPath: 'docs/dev/handoffs/epic-b-design-brief.md'}})`; accounting
   check; gate #1; step-6 assertion; finalize stage; gate #2. Record run
   evidence in item 84 in the turn it arrives (C-8). On `escalated_to_owner`:
   surface the verbatim text and stop — that is the pipeline working.
2. If the owner declines the run at session start, ask what is next instead —
   do not self-select an execution mode.

Scope is bounded to §"Epic B — `epic/b-render-ats`" in RELEASE_ARC.md.
Do not expand beyond what is listed there.

---

## First move

1. If this handoff arrived via a pointer, run
   `python scripts/check_handoff_pointer.py "<pointer line>"`, then
   `python scripts/verify_doc_template.py docs/dev/handoffs/epic-b-briefs.md
   docs/dev/AGENT_HANDOFF_TEMPLATE.md --event consumed --agent <your-agent-id>`.
   A `blocked` result is your **first output** — STOP (charter C-9).
2. Confirm with the owner that the first authorized pipeline run starts now
   (the decision recorded in the design brief does not discharge this — the
   run opt-in is made at THIS session's start). Confirm the session is on Opus.
3. Create branch `epic/b-render-ats` off `main`, write a plan at
   `~/.claude/plans/<slug>.md`, and show it to the user before touching any
   code. **Do not code first.** (Expect the plan-marker ceremony: one blocked
   edit on the branch, then EnterPlanMode → ExitPlanMode; see memory
   `reference-flush-stale-plan-stamp-on-branch-not-main`.)

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
