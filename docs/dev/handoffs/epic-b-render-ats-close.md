<!-- provenance: schema=1 session=e72ae348-3926-48f2-817f-19fbbe362662 branch=epic/b-render-ats commit=a85a559 actor=amodal1 agent=anthropic/claude-fable-5 generated_at=2026-08-15 -->

# Handoff — Epic B closes; sartor's next work is a small housekeeping branch, then the epics migrate to the factory

> **Where this sits (2026-08-15):** Epic B (`epic/b-render-ats`, board 37) is
> **code-complete and landing through its PR at this close-out** — B1a, B1b, and
> B2 all on this branch, gate green. The owner held the item-97 design sprint in
> this session (in the sartor CLI, editing nothing in sartor except item 98 and
> the board): the direction is an **external, container-run agent factory** whose
> durable design record now lives at `C:\Dev\the-factory\docs\design\00-sync-record-2026-08-14.md`
> (sister directory, working label, not yet a git repo). **Epics C, D, E do NOT
> run as sartor branch sessions** — they migrate into the factory's card system as
> its first test, after the factory design is finished. A `compacted` receipt
> exists in this session's ledger shard (C-12); all state below was reconciled
> from git, the board, and files — never from summary.

**Branch to create:** `docs/item-97-decision-record` (branch off `main`)
**Base branch:** `main` (after this PR merges — verify with `git log -1 main`)

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
March") — five epics A→E — **with execution of C/D/E moving to the external
factory (item 97).**
**Sequencing rule:** one epic at a time. The factory design (in `the-factory`)
precedes any further epic; sartor's remaining epics are the factory's first test.
**Blocked until this stream tags:** the 1.1.x series (`RELEASE_ARC.md` §"Post-public").

- ~~Epic A (`epic/a-app-core`, board 36)~~ ✓ — merged `162c1dc` (PR #117).
- ~~`feat/n1-baseline-pipeline`~~ ✓ — item 84's build (PR #125); the pipeline is
  **retired as a vehicle** after run 6; its escalation taxonomy is factory design input.
- ~~**Epic B (`epic/b-render-ats`, board 37)**~~ ✓ — **this branch, this handoff:**
  B1a (stale template companions), B1b (education render), B2 (ATS conformance —
  MM/YYYY dates, month hard block, import-path month surfacing, approved fonts +
  structural output gate). Landing via PR at this close.
- **`docs/item-97-decision-record`** ← next sartor branch (small, docs-only; see
  "What this branch should build").
- Epics C (`epic/c-diagnostics`, 38), D (`epic/d-docs-ia`, 39), E (`epic/e-release`,
  40) ← **do NOT start as branch sessions.** They migrate into the factory's cards
  once the factory design is finished (owner ruling 2026-08-15, recorded in the
  factory sync record §7b.2 / §10).

**What must NOT be started by the next session:** any epic branch; any
`.claude/workflows/n1-baseline.mjs` invocation (retired; owner opt-in never
inherited); implementing item 98 (the wiki coverage ledger) or item 97's factory
— both are cards for the factory's first test run, not branch-session work;
editing `docs/dev/work/SCHEMA.md` (gated surface; the board redesign happens in
the factory, and sartor adopts it back by vendoring later).

---

## What just landed on `main`

The Epic B PR — `epic/b-render-ats` at its tip, 39 commits above `5b8bafc`
(`34ad528`..HEAD), merge-commit only. Contents, verified via `git log main..epic`:

- **B1a** `6cbac2f` — refresh stale imported-template companions on a
  skeleton-version stamp. **B1b** `f47b1ed` — `studyType` rendered across every
  education surface via one canonical joiner.
- **B2** `8a01052` / `3f6c5c1` / `b3cd3a6` / `d22feb2` — dates render `MM/YYYY`
  via `json_resume.format_month_year`; month hard block at BOTH generate entry
  points + `MONTH NEEDED` badge; import-path month surfacing (year-only roles land
  flagged, never dropped; `PROMPT_VERSION = 2026-08-14.1`); `APPROVED_FONTS`
  allow-list enforced at every output write + new `tests/test_ats_structure.py`
  (29 tests). CHANGELOG + dossier notes in `5658163`; scoped wiki self-update
  (7 pages) in `f81b553`. Consumer dossier: `docs/dev/blast-radius/ats-conformance.md`.
- **Pipeline-era polish** on the same branch: item 87 (interrogative witness,
  built + live-verified), item 84 run records 2–6, `fix(n1)` hardening (namespaced
  `agentType`, invoker epic loop, context reducers, LF ledger writers + gate).
- **This session** (design sprint, sartor side only): work item **98** filed
  (wiki checkpoint coverage ledger — owner-selected build), `BOARD.md`
  regenerated (Open 7/10), this session's ledger shard, this handoff.

Gate: `python -m scripts.gate` on the tip at close — result recorded in the
close-out chat (see the commit that lands this handoff). `wiki_freshness.py`:
**OK, 33 relevant files (< 75)** — measured with the tool, not counted in commits
(the prior handoff's "64-commit window" prediction that the gate would fire was
wrong; item 98 is that defect).

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

`docs/dev/work/BOARD.md` is authoritative (regenerated + `work_items check` OK
this session, 98 files). Top-level subsets:

**Open — 4:** **50** (C-7/C-10 enforced by Claude Code hooks only — carries into
the factory design as a stated limit); **94** (witness kills pipeline runs —
dissolves structurally under the factory's fresh-process-per-task; owner retires
with 97); **96** (brief model args silently default — transforms into "model is a
required task field" in the factory schema); **98** (NEW — wiki checkpoint
coverage ledger + generated drift figure; owner: "test with it and some open
ledger items before running the epics"). Epics **19** and **36** remain open —
**Epic A's item 36 still never flipped `closed`, at least the FIFTEENTH handoff
flagging it**; Epic B's item **37** should close with this PR — the next branch
does it.

**Blocked — 6:** **3** ([HUMAN] GitHub toggles), **5** (grounding-score
persistence gap), **8** (Compose rewrite latitude), **93** (Epic-C invoker session
shape — mooted by the factory; retire with 97), **95** (resume pre-authorization
names a broken remedy — owner amendment owed with 97), **97** (external
orchestration — direction GIVEN and now DESIGNED in `the-factory`; the sartor-side
formal decision record is the next branch's deliverable). Plus epics 37, 38, 39, 40.

**Deferred (7):** 4, 7, 24, 25, 41, 42, 43.

**Watching — 45 top-level** (see BOARD.md). **The reduction-sprint flag stands —
at least the FIFTEENTH handoff flagging it.** Item 84 stays watching (pipeline
retired; taxonomy = design input).

**New durable captures this session (each already filed, listed per W-1):**
- Work item 98 (measured diagnosis; owner-selected build 1+3).
- Sartor doc defect: `AGENTS.md` claims the 10-Principles backbone is frozen in
  `docs/governance/charter.md`; it lives in `vision.md` §"Principles backbone"
  (found by isidium's harvest `docs/harvest/ten-principles-framework.md` §5).
  **Unfiled as a work item — capture in your branch** (one-line pointer fix +
  item; memory `project-sartor-10p-backbone-pointer-stale`).
- The factory sync record (`the-factory/docs/design/00-sync-record-2026-08-14.md`)
  carries every design decision with provenance marks; the sartor-side item-97
  record must QUOTE from it and from item 97's owner-verbatim block, never restate.
- Session memory: `project-item97-design-sprint-decisions` (pointer),
  `reference-spolia-board-comparison`, `reference-isidium-tracking-part-bdd-fit`,
  `reference-substrate-projection-layering`, `reference-wiki-checkpoint-ratchet-defect`,
  `feedback-design-sprint-interactive-elicitation`,
  `feedback-dont-overcommit-to-time-based-decisions`.

---

## Recurrences observed this session → guardrail authored

1. **Agents reporting a wiki drift figure that is not the gate's measure**
   (raw commit counts — "64-commit window" in the consumed handoff, "73 commits
   behind" by this session — instead of `python scripts/wiki_freshness.py`'s
   relevant-file count). Recognized as a recurrence: `docs/wiki/log.md`
   2026-08-08 already records "predicting a drift count instead of running the
   classifier". **No mechanism authored on this branch, and here is why:** the
   owner directed the fix to land as **work item 98** — a generated-only figure
   (`wiki_freshness.py --json` → handoff line, `verify_doc_template.py` refusing
   a hand-typed number) plus the coverage ledger — to be run as one of the
   factory's first test cards, not built mid-close-out on the epic branch.
   Surfaced to the owner in the close-out chat; the owner chose the venue.
   Stated plainly: until item 98 lands this is **unenforced**.
2. **Summary-cap violations while filing item 98** — three consecutive
   `work_items check` failures (149/133/128 chars) from *guessing* the length
   instead of measuring it; recognized live as the same class as the drift-count
   error (asserting a number the tool computes). **The existing mechanism held:**
   `scripts/work_items.py`'s 120-char cap failed closed each time until the
   summary was measured with `len()` and cut to 118. No new mechanism owed — the
   gate did exactly its job; recorded so the catch is attributed to it.
3. **The item-87 witness pause fired on every Edit/Write turn and once RE-ARMED
   BY A BACKGROUND TASK-NOTIFICATION** (the spolia sweep's completion) — the
   item-94 shape again. All consumed by the documented identical-re-run
   convention. Existing mechanism, behaving as specified; the notification
   re-arm is one more live datum for item 94, which the factory's
   fresh-process shape dissolves.

---

## What this branch should build

**A small, docs-only branch. No code. No epic.**

1. **The item-97 formal decision record** — update
   `docs/dev/work/items/0097-external-orchestration-hypothesis.md` (`## Updates`
   block; frontmatter status per the owner): quote the owner-verbatim direction
   already in the file; record the decided direction by QUOTING
   `C:\Dev\the-factory\docs\design\00-sync-record-2026-08-14.md` §0–§5 (external
   container-run factory; cards are the substrate, board and queue are
   projections; owner gate at card ratification; per-epic batch merges) — never
   restated; note the scope-vocabulary sharpening the owner ratified ("cards are
   the substrate; board and queue are projections" supersedes "the board is both
   canonical record and dispatch queue" in `docs/dev/board-forge-sync-review.md`
   §3, which stays as record).
2. **Board housekeeping the owner directed** (each an `## Updates` entry + status
   change, `decision_owner = user` items only with the owner's own words):
   retire **93** (moot under fresh-process-per-task); amend/retire **95** (owner
   wording required); transform **96** into "model + effort are required task
   fields, dispatcher fails loudly without them" — a factory-schema note, then
   close or defer; note **94**'s structural dissolution; **close 37** (Epic B) with
   `verified_by` = the Epic B PR number + `tests/test_ats_structure.py`; and
   finally flip **36** (Epic A) `closed` — merged at `162c1dc`, PR #117 — fifteen
   handoffs is enough.
3. **File the `AGENTS.md` backbone-pointer defect as a work item and land the
   one-line fix** (`AGENTS.md` "Read these first" → `vision.md` §"Principles
   backbone"), citing isidium's `docs/harvest/ten-principles-framework.md` §5.
4. Regenerate `BOARD.md` (`python -m scripts.work_items board --write`); gate;
   handoff; PR.

Reuse: `python -m scripts.work_items check|board --write`
(`scripts/work_items.py`); item file shape per `docs/dev/work/SCHEMA.md` §2–3
(append-only `## Updates`). Authorization: owner direction 2026-08-15 (this
handoff's "Where this sits" + the factory sync record §7 item 8) and item 97's
own "Open questions" block.

Scope is bounded to the item-97 decision record + the board housekeeping listed
above (`RELEASE_ARC.md` §"v1.1.0 Final March" governs the epic sequence; nothing
here changes it). Do not expand beyond what is listed there.

---

## First move

Verify this handoff's pointer (`python scripts/check_handoff_pointer.py
"<pointer line>"`) and stamp it consumed (`python scripts/verify_doc_template.py
docs/dev/handoffs/epic-b-render-ats-close.md docs/dev/AGENT_HANDOFF_TEMPLATE.md
--event consumed --agent <agent>`). Then create branch
`docs/item-97-decision-record` off `main`, write a plan at
`~/.claude/plans/<slug>.md`, and show it to the user before touching any file.
**Do not code first.** If the owner's session instead opens in `the-factory`,
this sartor branch simply waits — it is not a prerequisite for the factory design.

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
