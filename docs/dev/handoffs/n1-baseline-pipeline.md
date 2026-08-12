<!-- provenance: schema=1 session=b0e8447e-62c8-4209-baad-a1baa8e19655 branch=feat/n1-baseline-pipeline commit=6ad4bda actor=amodal1 agent=anthropic/claude-fable-5 generated_at=2026-08-11 -->

# Handoff — item 84 built (N=1 baseline pipeline, watching until first run); Epic B is next, owner-gated

> **The single most important thing this handoff carries forward:** the N=1 baseline
> pipeline is **BUILT, NEVER RUN**. Item 84 is `watching`, not closed — an owner
> decision taken on an adversarial reviewer's finding that the structural tests certify
> self-consistency with the design docs, not harness compatibility (the Workflow API the
> script targets has zero committed instances in this repo). **Running the pipeline on a
> real sprint is its own explicit owner opt-in** (§16.5.2.3) — nothing on this branch,
> and nothing in this handoff, authorizes a run. The owner signaled intent this session
> ("run the B epic test with opus"), but the run decision is made at that session's
> start, by the owner, not inherited from here.

**Branch to create:** `epic/b-render-ats` (branch off `main`) — Epic B, board 37,
**owner-gated start**: confirm with the owner both (a) that Epic B starts now and
(b) its execution mode — the normal handoff process, or the first authorized run of
the N=1 pipeline (`docs/dev/n1-baseline-pipeline.md` is the contract if so).
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

**Epic-specific reading, on top of the numbered list above:** `docs/dev/RELEASE_ARC.md`
§"Epic B" (board 37) for the sprint briefs; `docs/dev/n1-baseline-pipeline.md` **only if**
the owner opts into the pipeline run — otherwise it is background, not instruction.

**Stream:** v1.1.0 Final March (`docs/dev/RELEASE_ARC.md:1645`) — five epics, A→E,
strictly sequential.
**Sequencing rule:** strictly sequential — one epic at a time, code first (A–C), docs
after (D), release last (E). The governance-interval branches between Epic A and Epic B
are now complete.
**Blocked until this stream lands:** Epics C, D, E (board 38/39/40) stay behind B.

- ~~Epic A (`epic/a-app-core`, board 36)~~ ✓ — merged `162c1dc` (PR #117).
- ~~`docs/post-epic-a-findings`~~ ✓ — items 77–80 (PR #121).
- ~~`docs/pre-epic-b-review`~~ ✓ — the robustness design pass (PR #122).
- ~~`fix/retired-roles-a3-prompt`~~ ✓ — item 75's fix (PR #123).
- ~~`docs/extraction-governance-drift-reconcile`~~ ✓ — item 86, four stale claims
  reconciled (PR #124).
- ~~**This branch (`feat/n1-baseline-pipeline`)**~~ — item 84's authorized build. Done.
- `epic/b-render-ats` ← next: Epic B, owner-gated start + execution-mode decision.
- Epics C, D, E ← unchanged, sequenced behind B.

**What must NOT be started on the next branch:** *running* the N=1 pipeline without the
owner's explicit in-session opt-in (building was authorized; running was not); widening N
past 1; retiring or merging `AGENT_HANDOFF_TEMPLATE.md`; the §16.5.2.2 ledger event
extension; the §14.7 seam gate (flag stop under §11.6.5); the gate-launcher utility
(item 83, `decision_owner = "user"`); the watching-bucket triage (41 items — still owed,
its own session if the owner schedules it, now flagged by three handoffs running).

---

## What just landed on `main`

**Nothing merged yet from this branch at writing time** — this handoff is written
pre-PR, per the close-out checklist. `main` is at `6ad4bda` (PR #124).

This branch (`feat/n1-baseline-pipeline`, item 84) built the N=1 baseline pipeline the
owner authorized via §16.7 — plan adversarially reviewed before execution (Opus refuter,
20 findings, 19 folded in; the 20th — item 84's closure — went back to the owner and
flipped the disposition to `watching`):

- `.claude/workflows/n1-baseline.mjs` — the pipeline script: two stages via `args.stage`
  (`sprint`: implementer → refuter → judge → closer; `finalize`: commit-only) bracketing
  the **invoking session's** two gate runs; unified escalation primitive where
  `halt_point`/`hook_block` flags short-circuit to the owner with **no reviewer spawned**;
  coherence-drift layer inert at N=1 by construction (`const N = 1`; boundary guard).
  Invoke by `scriptPath`, never by name. Required a `.gitignore` re-include
  (`!.claude/workflows/`) — `.claude/*` is otherwise ignored.
- `agents/n1-refuter.md` (claude-sonnet-5) + `agents/n1-judge.md` (claude-opus-5) —
  read-only role definitions on the compliance-witness pattern; frontmatter is the
  single source of truth for agentType-dispatched models.
- `docs/dev/n1-baseline-pipeline.md` — contract + runbook, led by its C-0 limits
  (harness API unverified until first run). Classified wiki-IRRELEVANT (agent tooling)
  via a C-10 dossier for the gated `scripts/wiki_relevance.py` edit
  (`docs/dev/blast-radius/n1-baseline-pipeline.md`).
- `tests/test_n1_pipeline.py` — 29 structural pins; the JS scanner proved against RED
  fixtures before touching the real file; node syntax check uses the harness-wrap form
  (`node --input-type=module --check` over an async-function wrap — the raw file is
  correctly ESM-illegal on its top-level `return`).
- Small repairs folded in: §16.5.3 → §16.5.2.3 dangling citation
  (`epic-a-chain-design-corrections.md:1624`); RELEASE_ARC §"Session models" gained the
  owner's two re-confirmed clauses (epics on Opus/Sonnet without Fable — Epic B test on
  Opus; Fable = design/planning scope, Opus also an option there; Sonnet-subagent
  delegation with full-diff read); item 84 dated Update + `watching`; BOARD regenerated;
  wiki log verified-no-edit entry for the two wiki-relevant diff paths.

**Gate status at handoff-writing time:** `python -m scripts.gate` was **in progress**
(detached, `> gate1.log 2>&1`, per the §11.9 prose pattern) when this handoff was
drafted. Confirm it finished green before the PR step; if it did not, that is this
branch's next action, not Epic B's.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

`docs/dev/work/BOARD.md` is authoritative (regenerate with `python -m scripts.work_items
board --write`). Reproduced from the board as regenerated at this branch's close (86
files, `check` OK). Item 82's caveat stands: the header's counts mix two populations
(all-items vs top-level) — re-derive, don't trust either number blindly.

**Open (top-level 1; header says 4 incl. epic-nested):** **50** (C-7/C-10 enforced by
Claude Code hooks only — prose binds other agents). Item **84** moved open → watching
this branch (built; awaiting first-run evidence). Epic-nested opens: see board epics
9/19/36 — the two-handoffs-running flag that Epic A's item 36 `status` was never flipped
`closed` **still stands unresolved** (third handoff flagging it).

**Blocked (3):** **3** ([HUMAN] GitHub toggles), **5** (grounding-score persistence
gap), **8** (Compose rewrite latitude, evidence-gated on the PX-39 run).

**Deferred (7):** **4, 7, 24, 25, 41, 42, 43** — unchanged, all owner-gated or
post-1.1.0; see `BOARD.md` for one-line detail.

**Watching (41; was 40 + item 84 joining):** **2, 16, 18, 23, 46, 47, 48, 49, 51, 52,
53, 54, 55, 56, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 76,
77, 78, 79, 80, 81, 82, 83, 84, 85** (top-level; item 57 is epic-nested under 19).

- **The watching bucket grew to 41 this session** (item 84 joined by design — it holds
  the build until run evidence exists). The reduction-sprint flag from the prior three
  handoffs stands and is now stronger: the triage session is owed, not discharged.
- **Nothing else new filed to the ledger this session** — this branch's own follow-on
  (close item 84 after the first authorized run) lives in item 84 itself.

---

## Recurrences observed this session → guardrail authored

**Three recurrences recognized. No new mechanism authored for any — each landed in an
existing fail-closed mechanism that fired correctly, and the reason is stated plainly
per C-11.**

1. **Unclassified new `docs/dev/` doc reddening the classification test post-commit —
   the PR #105 / corrections-doc class, third instance anticipated and PREVENTED.**
   Recognized from the adversarial plan review before any commit; the classification
   entry landed in the same commit that creates the doc, through the existing C-10
   dossier + `tests/test_wiki_relevance_classification.py` mechanism. The existing test
   IS the fail-closed guard; it did its job at plan time rather than in CI.
2. **Stale/absent plan-approval marker blocking the first production edit — the
   documented `reference-flush-stale-plan-stamp-on-branch-not-main` class, with a new
   variant observed:** a MANUAL plan-mode exit (user toggling out, not `ExitPlanMode`)
   creates NO marker, and the first Write blocks with "NO EDIT APPROVAL" (not "PLAN
   RETIRED"). The existing `check-plan-approved.sh` hook is the fail-closed mechanism
   and fired correctly; recovery was one clean ceremony. Memory updated with the
   variant; no new mechanism needed — the hook already fails closed in both variants.
3. **`verify-binary-on-path` false-BLOCK on a shell construct (`{` brace group) — a
   member of item 53's documented false-positive class.** The guard's own C-0-scoped
   block message anticipates exactly this; the command was restructured rather than
   overridden. No new mechanism — the guard's fail-open-by-design posture for unparseable
   constructs is the recorded, deliberate trade (item 53 already tracks the class).

**Carried observation (not a recurrence, inherited from the prior handoff):**
`AGENTS.md:266` cites "charter D5, cite-don't-restate" — a mislabel (charter D-5 is
open-standards mechanics); the prior handoff flagged it and deliberately did not fix it.
This branch did not touch `AGENTS.md` either — the note stands for the next agent who
does.

---

## What this branch should build

<!-- This branch's own work is complete — see "What just landed" above. The NEXT branch: -->

1. **Epic B (`epic/b-render-ats`, board 37)** — per `docs/dev/RELEASE_ARC.md` §Epic B
   (sprints B1 Opus, B2 Sonnet, per §"Session models"). **Owner-gated start**: confirm
   the start and the execution mode with the owner before any code. If — and only if —
   the owner opts into the N=1 pipeline run, `docs/dev/n1-baseline-pipeline.md` §"The
   runbook" is the contract (precondition: a live plan-approval marker; the invoking
   session owns both gate runs; the report's accounting invariant is checked against
   `git status --porcelain`).
2. If the owner declines both, ask what is next instead — do not self-select a branch.

Scope is bounded to Epic B as specified in RELEASE_ARC.md. Do not expand beyond what is
listed there.

---

## First move

1. If this handoff arrived via a pointer, run
   `python scripts/check_handoff_pointer.py "<pointer line>"`, then
   `python scripts/verify_doc_template.py docs/dev/handoffs/n1-baseline-pipeline.md
   docs/dev/AGENT_HANDOFF_TEMPLATE.md --event consumed --agent <your-agent-id>`. A
   `blocked` result is your **first output** — STOP (charter C-9).
2. Ask the owner: does Epic B start now, and in which execution mode (normal handoff
   process, or the first authorized N=1 pipeline run)? Both are owner decisions this
   handoff cannot make.
3. Create branch `epic/b-render-ats` off `main`, write a plan at
   `~/.claude/plans/<slug>.md`, and show it to the user before touching any code. **Do
   not code first.** (Expect the plan-marker ceremony: the merged branch's stamp is
   stale or absent — one blocked edit, then EnterPlanMode → ExitPlanMode; see memory
   `reference-flush-stale-plan-stamp-on-branch-not-main`, including the manual-exit
   variant observed this session.)

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
