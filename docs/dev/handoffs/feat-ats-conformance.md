<!-- provenance: schema=1 session=49c375cd-a989-45bc-b359-48b1a72ec731 branch=feat/ats-conformance commit=f8785e9 actor=amodal1 agent=anthropic/claude-fable-5 generated_at=2026-08-14 -->

# Handoff — Epic B run 6 stopped at `escalated_to_owner` with B2 unimplemented; the owner has redirected toward EXTERNAL orchestration

> **Where this sits (2026-08-14):** the B2 sprint was invoked and **died before
> writing a single line of production code** — the item-87 witness pause landed
> on the implementer's first edit, which is a `hook_block` and therefore a
> no-reviewer short-circuit to the owner. What survived is genuinely valuable:
> a grep-complete 52-row consumer dossier and all six B2 defects reproduced.
> **The owner then redirected**: iterative development "may not be solvable at
> this point" in-project, and chain orchestration may belong OUTSIDE sartor
> entirely (item 97). **Epic B is NOT complete and B2 is NOT built.** Do not
> start any pipeline run without the owner's explicit per-session opt-in.

**Branch to create:** depends on the owner's direction — see "What this branch
should build". If the owner picks up item 94, it is a `fix/*` branch and **the
first commit must be the instrument, not the fix**.
**Base branch:** `epic/b-render-ats` (verify the tip with `git log -1
epic/b-render-ats` before cutting; `feat/ats-conformance` ff-merges into it)

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

**Stream:** v1.1.0 Final March (`docs/dev/RELEASE_ARC.md` §"v1.1.0 Final
March") — five epics, A→E, strictly sequential.
**Sequencing rule:** one epic at a time; Epics C, D, E (board 38/39/40) stay
behind B.

- ~~Epic A (`epic/a-app-core`, board 36)~~ ✓ — merged `162c1dc` (PR #117).
- ~~`feat/n1-baseline-pipeline`~~ ✓ — item 84's authorized build (PR #125).
- ~~`fix/b1-stale-template-companions`~~ ✓ — sprint B1a (run 3).
- ~~`fix/n1-invoker-loop`~~ ✓ — run-3 polish (epic loop, item 89).
- ~~`fix/n1-scope-dedup`~~ ✓ — the hardening review (S1–S5).
- ~~`fix/b1-education-render`~~ ✓ — sprint B1b (run 5).
- ~~`fix/n1-invoker-context-budget`~~ ✓ — the run-5 method review.
- **`feat/ats-conformance`** ← **THIS branch. B2 was invoked (run 6) and
  STOPPED with zero production code. The branch carries the implementer's
  dossier + this session's findings, NOT the B2 implementation.**
- Still owed: **B2 itself**, then the epic close-out to PR-ready → owner-gated
  epic PR (halt point 1) → then Epics C, D, E.

**What must NOT be started by the next session:** Epics C/D/E; widening N past
1 (owner-reserved, §16.7); rewriting `epic-b-b2-brief.md` (still valid — but
see the four corrections below, which the brief does not yet carry); the
item-93 and item-97 decisions (both the OWNER's); implementing item 94's fix
**before** its instrument proves the discriminator exists.

---

## What just landed on `epic/b-render-ats`

Nothing yet — `feat/ats-conformance` has **not** been merged into the epic
branch. Four commits sit on this branch above epic tip `dc60ba9`:

- `d25d3d4` — run-6 invocation record + preflight (item 84), ledger shard folded in.
- `e6e1402` — **LF pinned at the third ledger writer** (`hooks/lib/retire-approved-plan.sh`)
  + `tests/test_verify_doc_template.py::TestLedgerWritersPinLf`, the writer-side
  gate the CR-byte class was missing. Fifth instance, caught at preflight.
- `37915ca` — dispatch-probe verdict `ok_to_run` + pre-gate process hygiene.
- `f8785e9` — run-6 stop record + the implementer's blast-radius dossier
  (`docs/dev/blast-radius/ats-conformance.md`, 321 lines, 52 decided consumer rows).

Plus, uncommitted at this writing and folded into the close commit: items
94–97, the regenerated board, the runbook prune-ordering correction, and the
CHANGELOG entry.

**Gate status: see the close commit's message** — the gate was run once over the
final tree rather than before the doc edits, so the tree that was gated is the
tree that commits.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

`docs/dev/work/BOARD.md` is authoritative; regenerated this session
(`work_items check` OK, **97 files**). Header reads **Open 6 / 10 ceiling |
Blocked 6 | Deferred 7 | Watching 45 | Epics 6 | Closed 25** — note item **82**
records that this header mixes populations (the open count includes
epic-nested items; the others are top-level only), so the lists below are the
top-level subsets.

**Open — 3 top-level:** **50** (C-7/C-10 enforced by Claude Code hooks only —
prose binds other agents); **94** (NEW — the item-87 witness kills pipeline
runs; C-11 gap DECLARED, see Recurrences); **96** (NEW — sprint briefs
prescribe a model in prose while their First-move block omits the arg).
Epics **19** and **36** remain open — **Epic A's item 36 status still never
flipped `closed`, at least the THIRTEENTH handoff flagging it.**

**Blocked — 6 top-level:** **3** ([HUMAN] GitHub toggles), **5** (grounding-
score persistence gap), **8** (Compose rewrite latitude), **93** (Epic-C
invoker session shape — owner's, at Epic C planning), **95** (NEW — the
mid-run-pause pre-authorization names a broken remedy), **97** (NEW — the
owner's external-orchestration redirect). Plus epics **37, 38, 39, 40**.

**Deferred (7):** **4, 7, 24, 25, 41, 42, 43** — see `BOARD.md`. Note **43**
(approved-fonts expansion) explicitly depends on B2 shipping the
Arial/Calibri/Georgia list, which it has not.

**Watching — 45 top-level:** 2, 16, 18, 23, 46, 47, 48, 49, 51, 52, 53, 54,
55, 56, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74,
76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 88, 90, 91, 92. **The
reduction-sprint flag stands — at least the THIRTEENTH handoff flagging it.**

- **Item 84** — run 6 recorded in full. The digest report shape and
  `filingDivergence` had their first live exercise and worked; `halt_point`
  routing and `harness_throw` remain unexercised live. `hook_block` routing is
  now **exercised and correct**. Stays watching.
- Still standing for the owner from the hardening review's residue:
  `bypassPermissions` in machine-local settings undermines every hatch-based
  control repo-wide; the governance-hooks gate needs restructuring before any
  hook-based pipeline enforcement.

---

## Recurrences observed this session → guardrail authored

1. **Working-tree CR bytes in a ledger shard — FIFTH instance, and the first
   from a third writer.** Recognized as a recurrence immediately: the previous
   branch fixed exactly this class in two Python writers and shipped a sweep for
   it. **Mechanism authored on this branch, fails closed:** `newline="\n"` at
   `hooks/lib/retire-approved-plan.sh:153` (the `plan-archived` receipt, written
   from an embedded-Python heredoc the earlier fix never looked at), **plus**
   `tests/test_verify_doc_template.py::TestLedgerWritersPinLf` — a curated-list +
   discovery-scan dual check that fails the gate when a **new** ledger writer
   ships without the flag. The old sweep catches a dirty shard; this catches the
   writer. Both arms carry non-vacuity self-tests. Caught at preflight; gate #1
   would otherwise have failed ~90 minutes into the run.
2. **The item-87 witness pause stopping pipeline work — THIRD counted
   encounter, first fatal one.** Recognized as a recurrence because run-3
   preflight observed it and run 5 counted two re-arms. **NO MECHANISM WAS
   AUTHORED, and that is stated plainly rather than dressed up.** Filing item 94
   is *not* a mechanism; neither is the runbook note. The reason no guard was
   written: the only available fix needs an `agent_id`/`agent_type` discriminator
   whose presence in a **PreToolUse** payload is asserted from a doc reference in
   a code comment and **never observed here** — the one covering test feeds a
   synthetic payload, and 83 real `compacted` ledger rows carry zero `agent_id`.
   Writing a guard on that premise is the C-7 trap this repo has paid for
   repeatedly. **The instrument comes first** (see item 94). This gap was
   surfaced to the owner in-session, along with the full blast radius, and the
   owner's response was the strategic redirect in item 97.
3. **A plan-approval marker retiring at a moment that cost a ceremony —
   recognized as a member of the known plan-stamp class** (memory:
   `reference-flush-stale-plan-stamp-on-branch-not-main`), though this specific
   trigger was new. Pruning an already-ff-merged branch that the marker named
   retired it instantly, mid-preflight. **Mechanism: documentation only, and
   therefore NOT a C-11-compliant guard** — the runbook's epic-loop step now
   carries an explicit "prune AFTER the sprint stage, never before it" rule with
   the corrected trigger. Stated honestly: no gate enforces the ordering. A real
   mechanism would be a preflight assertion that the marker is live before the
   first `Workflow` call; not authored here because the session's remaining scope
   was the owner-directed documentation pass.

---

## What this branch should build

**Read this first: the next move is the OWNER's, not yours.** Item 97 records a
strategic redirect that may change how all remaining work is driven. Do not
assume the pipeline is the vehicle.

If the owner directs **B2 via the pipeline again** (run 7):

1. **Owner run opt-in first** — per-session, never inherited from this handoff.
2. **Consume the item-87 pause deliberately with your own `Edit`/`Write`
   immediately before the `Workflow` call**, and understand it can re-arm from
   any prompt-like event mid-run (item 94). A fresh invocation is required —
   **do NOT use `resumeFromRunId` on `wf_44350cb5-6b2`**: it would replay the
   blocked implementer's block-description as success and march the pipeline
   over an unimplemented sprint (item 95, runbook stated limit 4).
3. **Hand the implementer the four brief corrections below** — the B2 brief does
   not carry them, and three are verified:
   - **VERIFIED:** a second, unnamed generate entry point exists —
     `run_generation_stream` at `blueprints/generation.py:1162`, with its own
     duplicated `_is_pre_corpus_context` (`:1206`) and `_frozen_composition`
     (`:1226`). Implementing the month block only at `/api/generate` ships green
     with the defect fully reachable over SSE.
   - **VERIFIED:** `blueprints/corpus/experiences.py` has **four** date
     validators (`:119`, `:122`, `:222`, `:227`) — start *and* end, at create
     *and* edit — not the pair both briefs cite.
   - **REFUTED — do not inherit this claim:** the implementer asserted
     `tests/test_render_parity.py` "contains zero date literals" and concluded
     `RELEASE_ARC.md:1930` was "a false claim in the scope of record." Line 178
     carries `"### Acme, Staff Engineer\t2022-01 – present\n"` in the `UNSAFE_MD`
     fixture. The narrow point survives (that test asserts scrub/parity, not the
     date string), but the conclusion does not rest on a false categorical.
   - **UNVERIFIED (implementer's own, not re-checked here):** `_DATE_RE` in
     `onboarding/extract_experiences.py:197` must stay permissive or a failing
     `start_date` sends the whole role down the `experiences_dropped` path.
4. The dossier `docs/dev/blast-radius/ats-conformance.md` is committed —
   rows 1–52 are the ordered work list; rows 20, 23–24, 38, 43 are the ones that
   differ from the brief.

If the owner directs **item 94** instead: it is a `fix/*` branch, and **the
first commit is the instrument** — spawn one trivial subagent that attempts a
single `Edit` and log the raw PreToolUse payload. The full pre-implementation
blast radius is already enumerated in item 94; do not re-derive it, but **do**
re-verify it, since it was written before any code changed.

If the owner directs **item 97**: it is design work, not a build. Start from the
four open questions in the item; the load-bearing one is which system is
authoritative for task state.

Scope is bounded to the owner-ratified sentence in `epic-b-design-brief.md`
§"Execution mode + authorization record" plus §"Epic B — `epic/b-render-ats`"
in `RELEASE_ARC.md`. Do not expand beyond what is listed there.

---

## First move

Verify this handoff's pointer (`python scripts/check_handoff_pointer.py
"<pointer line>"`) and stamp it consumed (`python
scripts/verify_doc_template.py docs/dev/handoffs/feat-ats-conformance.md
docs/dev/AGENT_HANDOFF_TEMPLATE.md --event consumed --agent <agent>`). Then
**ask the owner which of the three directions above to take** — that choice is
not derivable from this file, and items 94/95/97 are all `decision_owner =
"user"`. **Do not invoke the pipeline without the owner's explicit per-session
run opt-in.**

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
