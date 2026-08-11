<!-- provenance: schema=1 session=92c2e82d-a080-4ba0-8c3f-5f56be9863a3 branch=docs/extraction-governance-drift-reconcile commit=3fa20a3 actor=amodal1 agent=anthropic/claude-sonnet-5 generated_at=2026-08-11 -->

# Handoff — four stale extraction/governance claims reconciled; item 84 (N=1 baseline) is still next

> **The single most important thing this handoff carries forward:** this branch was an
> **interposed docs-only detour**, not the branch the prior handoff
> ([`retired-roles-a3-prompt.md`](retired-roles-a3-prompt.md)) named as next. That prior
> handoff's authorization stands **unchanged**: the owner's §16.7 answer authorized
> **item 84 — the N=1 baseline pipeline build** — as the next branch,
> `feat/n1-baseline-pipeline`, off `main`. This branch does not touch that authorization,
> does not touch code, and does not advance Epic B in any way.

**Branch to create:** `feat/n1-baseline-pipeline` (branch off `main`) — item 84, the
authorized N=1 build. Building the pipeline is authorized; **running** it on a real
sprint is its own later, explicitly opted-into step (§16.5.2.3).
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
`docs/dev/epic-a-chain-design-corrections.md` §16 in full (the C+drift design the next
branch builds the N=1 baseline of — §16.4 structure, §16.5 staged rollout + audit trail,
§16.7 with the owner's decision recorded in item 84), plus item 84's own file
(`docs/dev/work/items/0084-build-n1-baseline-pipeline.md`).

**Stream:** v1.1.0 Final March (`docs/dev/RELEASE_ARC.md:1645`) — five epics, A→E,
strictly sequential.
**Sequencing rule:** strictly sequential — one epic at a time, code first (A–C), docs
after (D), release last (E). This branch (docs drift reconcile) and the next (item 84's
build) are **not march epics** — governance-interval / infrastructure work between Epic A
and Epic B.
**Blocked until this stream lands:** Epics C, D, E (board 38/39/40) stay behind B. Epic
B's first code sprint remains un-started; its execution mode is downstream of the N=1
baseline evidence, per the owner's §16.7 answer — do not resume any chain under the old
§11 envelope.

- ~~Epic A (`epic/a-app-core`, board 36)~~ ✓ — merged `162c1dc` (PR #117).
- ~~`docs/post-epic-a-findings`~~ ✓ — items 77–80 (PR #121).
- ~~`docs/pre-epic-b-review`~~ ✓ — the robustness design pass (PR #122, `7a6d8e7`).
- ~~`fix/retired-roles-a3-prompt`~~ ✓ — item 75's fix (PR #123, `3fa20a3`).
- ~~**This branch (`docs/extraction-governance-drift-reconcile`)**~~ — item 86, four stale
  extraction/governance claims reconciled. Interposed docs-only detour; does not change
  the arc position below. Done.
- `feat/n1-baseline-pipeline` ← next: item 84, the authorized N=1 build.
- Epic B (`epic/b-render-ats`, board 37) ← after that, owner-gated start.
- Epics C, D, E ← unchanged, sequenced behind B.

**What must NOT be started on the next branch:** any Epic B code; *running* the built
pipeline on a real sprint (build-only is what §16.7's answer authorized); widening N past
1; editing `AGENT_HANDOFF_TEMPLATE.md` (§16.5.1 — its own later, owner-gated decision,
made only once N=1 evidence exists); the watching-bucket triage (recommended, but its own
session if the owner schedules it).

---

## What just landed on `main`

**Nothing merged yet from this branch at writing time** — this handoff is written pre-PR,
per the close-out checklist. `main` itself is at `3fa20a3` (PR #123, item 75's fix).

This branch (`docs/extraction-governance-drift-reconcile`, item 86) reconciled **four**
stale claims an external read-only survey flagged in sartor's extraction/governance docs
— **each verified independently against HEAD before any edit** (C-7), not trusted on the
survey's word:

1. `docs/dev/EXTRACTION.md` — `recall/`'s "design-only, not committed" → committed +
   boundary-lint green (`tests/test_recall_boundary.py`, 5/5 verified this session);
   second-consumer gate left explicitly open (only in-repo importer found:
   `blueprints/assistant.py`).
2. `docs/dev/EXTRACTION.md` — "the compliance agent does not exist yet" → points at
   `agents/compliance-witness.md` + `commands/compliance-witness.md` (shipped `4e8b1df`,
   Sprint 7.7, 2026-06-16).
3. `docs/dev/governance-extraction-design.md` §5 — portable-enforcement-core framed as a
   pending decision → a status note added, past tense, pointing at
   `docs/governance/enforcement.md` as canonical (single-home; the migration landed
   2026-07-08 on `feat/portable-enforcement-core`).
4. `docs/governance/enforcement.md` — "CI latent until the git remote activates" →
   corrected **in place** (this is the canonical home) — live branch protection verified
   via `gh api repos/take-tempo-public/sartor/branches/main/protection`: 6 required
   contexts, `strict: true`. AGENTS.md's live-CI description was already correct and
   needed no edit.

Two bonus same-class findings surfaced during verification and were folded in:
`enforcement.md`'s stale "4 required checks" → 6 (re-derived from the live protection);
`kit-adoption-design.md`'s header blockquote contradicting its own `DOC-STATUS` banner,
plus a matching "no remote" claim in its temporal map, both reconciled to defer to the
`DOC-STATUS`/`enforcement.md` rather than re-asserting. Also retired a
Callback→Sartor rename survivor found in the same file
(`EXTRACTION.md:114`, product sense — "a callback Operation surface" → "a Sartor
Operation surface", per `docs/dev/doc-style-guide.md` §1; the only `callback` hit across
all four touched docs).

**Files:** `docs/dev/EXTRACTION.md`, `docs/dev/governance-extraction-design.md`,
`docs/governance/enforcement.md`, `docs/dev/kit-adoption-design.md` (prose only — no
code, no prompt constants, no charter clause text, per the scope guard). Work item 86
filed and closed same-session (`closure_exception`, not `verified_by` — prose
reconciliation has no automated correctness gate; the four verification commands are
recorded in the item file). `docs/wiki/log.md` gained a verified-no-edit entry (all four
paths are wiki-relevant per `is_wiki_relevant()`; checked every page citing them —
[[consistency-tracks-enforcement]], [[engineering-workstreams]],
[[governance-extraction]] — none restates the specific corrected prose). No CHANGELOG
entry (dev-internal docs only, per `governance-extraction-design.md` §6's own precedent —
the last purely-docs commit, `7a6d8e7`, also didn't touch CHANGELOG.md).

**Gate status at handoff-writing time:** `ruff check .` ✓, `ruff format --check .` ✓,
`mypy .` ✓ (365 source files), `python -m scripts.work_items check` ✓ (86 files).
`pytest -m "not ux"` was **in progress** when this handoff was drafted (docs-only change,
so this is a regression check, not proof of the edit) — confirm it finished green before
step 1 of the close-out checklist below; if it did not, that is this branch's next
action, not `feat/n1-baseline-pipeline`'s.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

`docs/dev/work/BOARD.md` is authoritative (regenerate with `python -m scripts.work_items
board --write`). Reproduced from the board as regenerated at this branch's close (86
files, `check` OK). Item 82's caveat stands: the header's counts mix two populations
(all-items vs top-level) — re-derive, don't trust either number blindly.

**Open (top-level 2; header says 5 incl. epic-nested 9/19/36):** **50** (C-7/C-10
enforced by Claude Code hooks only — prose binds other agents), **84** (**the N=1
baseline build — open, owner-authorized; the next branch**). Epic-nested: **9**
(visual-assets refresh, under epic 39), **19** (UX-flake epic close-out), **36** (Epic A —
merged; its item `status` still not flipped `closed`, worth the follow-up check two
handoffs running have now flagged).

**Blocked (3):** **3** ([HUMAN] GitHub toggles), **5** (grounding-score persistence gap),
**8** (Compose rewrite latitude, evidence-gated on the PX-39 run).

**Deferred (7):** **4, 7, 24, 25, 41, 42, 43** — unchanged, all owner-gated or
post-1.1.0; see `BOARD.md` for one-line detail.

**Watching (40, unchanged — this branch closed item 86 same-session, so it never entered
the open/watching ledger at all):** **2, 16, 18, 23, 46, 47, 48, 49, 51, 52, 53, 54, 55,
56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 76, 77, 78,
79, 80, 81, 82, 83, 85** (41 listed — the top-level/nested population caveat above
applies; item 57 is epic-nested).

- **The watching bucket did not move this session** — this branch's own work (item 86)
  was filed and closed same-session, so it never passed through `open`/`watching`. The
  reduction-sprint flag from the prior two handoffs stands: the bucket has been at 40–41
  for two branches running; the triage session is still owed, not discharged by this
  branch.
- **Nothing new filed to the open/watching ledger this session.** Item 86 is a closed
  item from filing to close; it adds a `closed`-count entry, not an open one.

---

## Recurrences observed this session → guardrail authored

**One recurrence recognized. No new mechanism authored — it landed in the existing
tracking, and the reason is stated plainly per C-11.**

1. **The stale-plan-stamp flush firing on branch creation — a RECURRENCE of the
   documented class** (memory `reference-flush-stale-plan-stamp-on-branch-not-main`): the
   first `Edit` call on this branch was blocked with "PLAN RETIRED: branch
   'fix/retired-roles-a3-prompt' has already merged... its approval was archived, not
   deleted," exactly the flush-on-first-production-edit pattern that memory documents.
   **No new mechanism authored:** the existing `check-plan-approved.sh` hook + the
   `EnterPlanMode`/`ExitPlanMode` ceremony **is** the fail-closed mechanism, and it fired
   correctly — this is confirmation the guard works as designed on a genuinely new
   branch, not a gap. Recognized immediately from the memory rather than treated as a
   surprise; no time lost investigating it.

**A second observation, not a recurrence but worth recording plainly:** the incoming
prompt (from an external read-only survey) cited "charter D-5" as the authority for the
single-home / cite-don't-restate discipline it invoked. **Verified and found
inaccurate** — charter `D-5` is "Open-standards + auditable-iterations mechanics"
(JSON Resume / auditable-iterations), unrelated. The actual single-home discipline this
branch applied is `governance-extraction-design.md`'s own §2 ("cite, don't re-fix").
Separately, `AGENTS.md:266` itself cites **"charter D5, cite-don't-restate"** for an
unrelated frontend-config rule — the same mislabel, pre-existing, not introduced this
session. **Not fixed here** (out of this branch's four-finding scope; fixing it would be
scope creep into a fifth, unrequested correction) — flagged here so it isn't lost. Not
added to the Carried-forward ledger above because it is prose-citation drift, not a
tracked defect class with its own item; the next agent touching either file should note
it in passing.

---

## What this branch should build

<!-- This branch's own work is complete — see "What just landed" above. The NEXT branch builds: -->

1. **Item 84 — the N=1 baseline pipeline** (`feat/n1-baseline-pipeline`): implementer →
   Sonnet refuter → judge → closer for ONE ordinary sprint, as a Workflow script, per
   `docs/dev/epic-a-chain-design-corrections.md` §16.4 (structure) and §16.5 (staged
   rollout; the Workflow-native capability argument in §16.5.2.3 — `journal.jsonl` +
   `resumeFromRunId` — bears on HOW to build, and does not authorize running). Authorized
   by the owner's §16.7 decision, recorded in item 84's Updates (2026-08-11).
2. Scope boundary: build + its own tests/verification only. The provenance-ledger event
   extension (§16.5.2.2) is explicitly NOT authorized. Running the pipeline on a real
   sprint is a separate owner opt-in.

Scope is bounded to item 84 and §16.4–§16.5 of the corrections doc. Do not expand beyond
what is listed there.

---

## First move

1. If this handoff arrived via a pointer, run
   `python scripts/check_handoff_pointer.py "<pointer line>"`, then
   `python scripts/verify_doc_template.py
   docs/dev/handoffs/extraction-governance-drift-reconcile.md
   docs/dev/AGENT_HANDOFF_TEMPLATE.md --event consumed --agent <your-agent-id>`. A
   `blocked` result is your **first output** — STOP (charter C-9).
2. Read `docs/dev/epic-a-chain-design-corrections.md` §16 in full and item 84's file —
   the owner's authorization and its exact scope live there, not in this summary.
3. Create branch `feat/n1-baseline-pipeline` off `main`, write a plan at
   `~/.claude/plans/<slug>.md`, and show it to the user before touching any code. **Do
   not code first.** (Expect the stale-plan-stamp flush: one blocked edit on the branch,
   then the EnterPlanMode → ExitPlanMode ceremony — see memory
   `reference-flush-stale-plan-stamp-on-branch-not-main`; it fired for this branch too,
   confirmed working as designed — see "Recurrences observed" above.)

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
