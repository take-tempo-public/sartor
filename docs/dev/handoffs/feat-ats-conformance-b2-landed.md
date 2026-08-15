<!-- provenance: schema=1 session=22f86995-65eb-4a32-8132-f774048534f7 branch=feat/ats-conformance commit=f81b553 actor=amodal1 agent=anthropic/claude-fable-5 generated_at=2026-08-14 -->

# Handoff — B2 landed conventionally; Epic B code-complete awaiting the owner-gated epic PR; next session is the item-97 design sprint

> **Where this sits (2026-08-14):** the owner redirected after run 6 (see the
> consumed predecessor handoff `feat-ats-conformance.md`), chose the external
> GitHub-native factory direction (item 97: `anthropics/claude-code-action` in
> automation mode on a self-hosted runner) with **the repo board itself as the
> dispatch queue** (forge-issue sync is simply out of scope — a posture, not a
> recorded prohibition; see `board-forge-sync-review.md` §3), and had B2 landed
> **conventionally** in the same session — all six scope items plus the four
> brief corrections, on this branch. **Epic B is code-complete**; the epic PR
> (halt point 1) is the owner's gate. The next working session is the
> **design sprint** for the factory move. A `compacted` ledger receipt exists
> for this session (C-12 disclosure); all work was reconciled from durable
> state (git, dossier, board), never from summary memory.

**Branch to create:** owner names it at the design-sprint sync (suggestion:
`feat/dark-factory-design`) — it is design/docs work, not a build.
**Base branch:** `main` if the owner has merged the epic PR by then, else
`epic/b-render-ats` (verify with `git log -1` before cutting; do not base
design work on `feat/ats-conformance`, which is fully ff-merged into the epic).

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
March") — five epics A→E — **plus the item-97 factory stream opening beside it.**
**Sequencing rule:** one epic at a time; C, D, E (board 38/39/40) stay behind
Epic B's PR. The design sprint is not an epic and may run before the epic PR
if the owner chooses.

- ~~Epic A (`epic/a-app-core`, board 36)~~ ✓ — merged `162c1dc` (PR #117).
- ~~`feat/n1-baseline-pipeline`~~ ✓ — item 84's authorized build (PR #125).
- ~~`fix/b1-stale-template-companions`~~ ✓ — sprint B1a (run 3).
- ~~`fix/n1-invoker-loop`~~ ✓ / ~~`fix/n1-scope-dedup`~~ ✓ /
  ~~`fix/b1-education-render`~~ ✓ (B1b, run 5) /
  ~~`fix/n1-invoker-context-budget`~~ ✓ — the pipeline-era polish branches.
- ~~**`feat/ats-conformance`**~~ ✓ — **B2 LANDED (this branch, this handoff):**
  run 6 stopped with zero code; the owner then directed a conventional landing,
  done same-day. Epic B is code-complete at the epic tip.
- **Owner-gated next: the Epic B PR** (halt point 1) — merge-commit only, via
  `scripts.ci_wait`. Note the wiki-freshness gate will surface the 64-commit
  un-ingested window (pre-existing; see Carried-forward) — a catch-up
  `/wiki-ingest` pass may be owed at that point.
- **Next working session: the item-97 design sprint** (this handoff's "What
  this branch should build").
- Epics C, D, E — do NOT start; behind the Epic B PR, and their execution
  vehicle is exactly what the design sprint decides.

**What must NOT be started by the next session:** implementing the factory
(workflow YAML, picker, schema changes) before the design sprint's decisions
are recorded and the C-10 dossier for `docs/dev/work/SCHEMA.md` exists; Epics
C/D/E; any `.claude/workflows/n1-baseline.mjs` invocation (retired as vehicle;
owner opt-in never inherited).

---

## What just landed on `epic/b-render-ats`

`feat/ats-conformance` ff-merges to the epic tip with its commits above
`b0aaed3` (`8a01052`..HEAD):

- `8a01052` — **B2 item 1:** dates render `MM/YYYY` via the single canonical
  helper (`json_resume.format_month_year`); 19 literal assertions moved in 4
  test files; `test_render_parity.py` needed none (dossier row 13 held);
  `hardening.compute_date_grounding` verified format-agnostic. Session ledger
  shard folded in.
- `3f6c5c1` — **items 2–3:** month hard block at BOTH generate entry points
  (`/api/generate` + SSE — the site neither brief named), shared 422 builder;
  `is_month_precise`/`needs_month_precision` predicate pair; `needs_month`
  payload key + `ExperienceSummaryItem` mirror + MONTH NEEDED badge; all FOUR
  date validators month-required; education exempt by construction.
- `b3cd3a6` — **item 4:** import-path surfacing — year-only roles land
  flagged, never dropped (`experiences_needing_month`/`month_needed_experiences`
  through report/merge/CLI/route/UI); `_DATE_RE` verified permissive-by-design;
  extraction-prompt wording change → `PROMPT_VERSION = 2026-08-14.1`.
- `d22feb2` — **items 5–6:** `APPROVED_FONTS` (Arial/Calibri/Georgia) +
  `map_to_approved_font` enforced at every output write boundary; NEW
  `tests/test_ats_structure.py` (29 tests: structure + allow-list-exact fonts
  on generated `.docx`, incl. a synthetic off-list template).
- `5658163` — CHANGELOG, dossier verification notes (incl. the grounding-check
  negative finding), item-43 dependency-satisfied update, and
  `docs/dev/board-forge-sync-review.md` (the design-sprint board analysis).
- `f81b553` — scoped `/wiki-self-update`: 7 pages, author≠auditor audits,
  catch-rate 2/7 (both pre-existing), checkpoint deliberately NOT advanced;
  `board-forge-sync-review.md` classified deliberately wiki-irrelevant after
  the classification gate caught it unclassified.

Gate: `python -m scripts.gate` run at close over the final tree (result
recorded in the close-out chat; the ruff/mypy/pytest steps also ran green
per-section during the build). Consumer dossier:
`docs/dev/blast-radius/ats-conformance.md` (52 rows + implementation-time
verification notes).

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

`docs/dev/work/BOARD.md` is authoritative (regenerated + `work_items check` OK
this session, 97 files). Top-level subsets:

**Open — 3:** **50** (C-7/C-10 enforced by Claude Code hooks only — prose
binds other agents; carries INTO the factory design as a stated limit);
**94** (witness kills pipeline runs — dissolves structurally under the
factory's fresh-process-per-task shape; the owner retires it when recording
item 97); **96** (brief model args silently default — transforms into
"model is a required task-schema field, dispatcher fails loudly without it").
Epics **19** and **36** remain open — **Epic A's item 36 status still never
flipped `closed`, at least the FOURTEENTH handoff flagging it.**

**Blocked — 6:** **3** ([HUMAN] GitHub toggles), **5** (grounding-score
persistence gap), **8** (Compose rewrite latitude), **93** (Epic-C invoker
session shape — mooted by the factory direction; owner retires with 97),
**95** (resume pre-authorization names a broken remedy — owner amendment/
retirement owed with 97), **97** (external orchestration — direction GIVEN
in-session: claude-code-action factory + NO Issues projection; the FORMAL
decision record is the design sprint's first deliverable). Plus epics
**37, 38, 39, 40**.

**Deferred (7):** 4, 7, 24, 25, 41, 42, **43** (approved-fonts expansion —
its B2 dependency is NOW SATISFIED; expansion stays deferred, owner-gated).

**Watching — 45 top-level** (see BOARD.md). **The reduction-sprint flag
stands — at least the FOURTEENTH handoff flagging it.** Item **84** stays
watching: the pipeline is retired as the vehicle; its escalation taxonomy is
design input.

**New durable captures this session (each already filed, listed here per W-1):**
- `docs/wiki/log.md` (2026-08-14 entry): route-surface.md:235-236 carries a
  pre-existing UNSUPPORTED claim ("`proposals.py` … the only corpus submodule
  on the egress allowlist" — `skills.py` is also on it); left flagged, owner
  decision + suggested fix recorded there.
- Same entry: the wiki checkpoint is 64 commits behind the epic base —
  catch-up ingest owed at epic close; `scripts/wiki_freshness.py` is the
  deterministic backstop.
- `docs/dev/board-forge-sync-review.md` §5–6: the factory smoke tests owed
  before trust (repo hooks in a headless run; the runner must not carry
  `bypassPermissions`) and the failed-run-state open question.
- Standing from the hardening review, still the owner's: `bypassPermissions`
  in machine-local settings undermines hatch-based controls repo-wide.

---

## Recurrences observed this session → guardrail authored

1. **A new top-level `docs/dev/` file landed unclassified for wiki-relevance**
   (`board-forge-sync-review.md`) — recognized as the classification-drift
   class `docs/dev/diagnosis/wiki-freshness-relevance-classification.md`
   documents. **The already-authored mechanism fired and held:**
   `tests/test_wiki_relevance_classification.py` failed the gate closed until
   the file was classified on purpose (deliberately IRRELEVANT, with rationale,
   in `scripts/wiki_relevance.py`). No new mechanism owed — this is the
   existing gate doing exactly its job; recorded so the catch is attributed to
   the gate, not to vigilance.
2. **CRLF written into tracked text files by a `pathlib.write_text` without a
   pinned newline** (two files, this session's own tooling) — recognized as a
   member of the CR-byte class (five prior ledger-shard instances; the sixth
   sighting shape). **No new mechanism authored, and here is the reason:** for
   *tracked text files* git's eol normalization already fails safe — the
   committed bytes were LF-clean (git said so at commit), which is the
   protection the ledger shards lacked and `TestLedgerWritersPinLf` now gives
   them. The residual exposure (working-tree CRLF churn) is cosmetic; a
   repo-wide writer-side newline gate is listed as a design-sprint candidate
   rather than built mid-close-out. Surfaced to the owner in the close-out
   message.
3. **The item-87 witness pause fired three times** — twice on user-prompt
   turns and once RE-ARMED BY A BACKGROUND TASK-NOTIFICATION, which is
   precisely the non-user-event arming item 94 documents. All three consumed
   by the documented identical-re-run convention; the one-shot witness design
   is the existing mechanism and behaved as specified. Under the factory's
   fresh-process-per-task shape the fatal mid-run re-arm case (item 94) stops
   existing; the notification re-arm observed here is fresh live evidence for
   that item's mechanism section.

---

## What this branch should build

**The next session is a SYNC + DESIGN session, not a build.** The owner's
stated flow: get synced, plan a design sprint that sets goals, makes
decisions, and finds out what we need to know before designing — then
externalize. Deliverables, in order:

1. **The item-97 formal decision record** — the direction (GitHub-native
   factory: `anthropics/claude-code-action` automation mode, self-hosted
   runner, serial `concurrency` group; Kestra uncoupled, homelab-only),
   **quoted from its recorded home**
   (`docs/dev/work/items/0097-external-orchestration-hypothesis.md`
   owner-verbatim block) per the scope-is-quoted rule, with the board-as-queue
   scope stated per `docs/dev/board-forge-sync-review.md` §3 (forge-issue
   sync is out of scope — record it as scope, NOT as a "never Issues" rule;
   the owner explicitly declined a standing prohibition). Update item 97;
   retire item 93 (moot), retire/amend item 95's pre-authorization (owner's
   own words needed), transform item 96 into the factory task-schema rule,
   note item 94's structural dissolution.
2. **Owner work-package 1 — affected-resources sweep:** review ALL repo code
   + documentation for areas touched by the in-repo orchestration system
   (n1 pipeline + runbook + briefs, governance hooks it trips, board, handoff/
   ledger ceremony) → a durable list, **adversarially reviewed** (reviewer
   instructed to REFUTE), logged to a durable document.
3. **Owner work-package 2 — touched-areas design review:** what the external
   design must address per area; adversarially verified.
4. **Owner work-package 3 — build-certainties vs. open questions:** start
   from `docs/dev/board-forge-sync-review.md` §5 (needed changes: schema
   `priority` + `work_items next` + dispatch-payload convention + factory
   workflow + runner hygiene) and §6 (open questions incl. failed-run state,
   priority scale, multi-project namespacing, budgets, what survives of the
   pipeline's taxonomy). These are INPUT for the design agent, who probes
   further as requirements are set.
5. **Owner work-package 4 — the BOARD design pass** (owner-flagged
   2026-08-14: the board as it stands is NOT ready to support factory
   dispatch): readiness semantics designed and gate-enforced, the priority
   model, the dispatch-payload convention, execution-state fields incl. the
   fail-closed failed-run home, the item-82 header/population debt, epic
   nesting vs. dispatch, and the 97-file triage — as ONE schema change-set
   behind ONE C-10 dossier. Full brief:
   `docs/dev/board-forge-sync-review.md` §7.
6. **The two smoke tests** (may land as evidence during design): repo hooks
   firing in a headless `claude -p` run (expect exactly one self-clearing
   item-87 pause), and the runner-settings `bypassPermissions` check.
7. The full research record for the design agent: the **Dark Factory
   Dispatch artifact** — https://claude.ai/code/artifact/479ee279-abc8-413e-83ec-3256dd0c9672
   — §03 comparison (Sortie/Beads as fallbacks), §05 item-97 answers, §09
   agenda; plus memory `reference-dark-factory-research`.

Constraint carried from the board analysis: `docs/dev/work/SCHEMA.md` is a
GATED surface — the `priority` schema change owes a C-10 consumer dossier
BEFORE its first edit.

Scope is bounded to item 97 (`docs/dev/work/items/0097-external-orchestration-hypothesis.md`)
plus the owner's in-session direction as recorded in
`docs/dev/board-forge-sync-review.md` §3 and §7. Do not expand beyond what is
listed there.

---

## First move

Verify this handoff's pointer (`python scripts/check_handoff_pointer.py
"<pointer line>"`) and stamp it consumed (`python
scripts/verify_doc_template.py docs/dev/handoffs/feat-ats-conformance-b2-landed.md
docs/dev/AGENT_HANDOFF_TEMPLATE.md --event consumed --agent <agent>`). Then
**sync with the owner** to set the design sprint's goals and decisions —
that conversation, not this file, authorizes the branch. **Do not code
first; do not touch the factory build before the design decisions are
recorded.**

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
