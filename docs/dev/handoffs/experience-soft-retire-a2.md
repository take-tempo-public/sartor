<!-- provenance: schema=1 session=d05ae572-3c7d-4de9-88f9-acdf997626a1 branch=fix/experience-soft-retire commit=5474763 actor=amodal1 agent=anthropic/claude-opus-5 generated_at=2026-08-08 -->

# Agent handoff: sprint A1b is CLOSED and committed — start A2 (`feat/compose-wait-ux`)

> **Read this box first.** Unlike the handoff this session received, nothing is
> left staged or unreviewed. Sprint A1b is committed at `5474763`, the
> adversarial review ran, its findings are resolved, and the wiki pass is done.
> **One thing is genuinely unfinished and is the first thing you must do:** the
> committed-tree gate run. See "First move".

**Branch to create:** `feat/compose-wait-ux` (branch off `fix/experience-soft-retire`)
**Base branch:** `fix/experience-soft-retire` @ `5474763` — the A1b tip. This chain
stacks **tip-to-tip** and never branches off `main`.

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

**Before anything in the list above — the two documents this chain runs on:**

- **`docs/dev/handoffs/docs-epic-a-wave-orchestration-design.md`** — the chain's
  statement of intent. **Read it in full.** Two sessions ago an agent skipped it,
  worked from the errata alone, and got its own role wrong for a whole sprint.
  §"The design" holds the orchestrator role, the `Agent`-not-`Workflow` mechanism,
  the model table, and the one-approval property. **The model table is load-bearing
  and easy to guess wrong:** A1 and A2 implementers are **Opus**, not Sonnet. This
  session checked rather than assumed, and would have guessed wrong.
- **`docs/dev/epic-a-chain-design-corrections.md`** — the errata that supersedes it
  where they disagree. Read its "Verification status" legend first: **[REPORTED] is
  a lead, not evidence.** A1b re-derived its own enumeration and found the
  `[REPORTED]` appendix wrong or incomplete in four places.

**Stream:** v1.1.0 Final March — Epic A, an owner-sanctioned stacked-branch chain
(`RELEASE_ARC.md:1675-1686`, the 2026-08-08 amendment).
**Sequencing rule:** strictly sequential, stacked tip-to-tip, no intermediate
merges, one PR per epic at the very end.
**Blocked until this stream tags:** the public v1.1.0 cut (epic E / item 10).

- ~~`docs/epic-a-wave-orchestration-design`~~ ✓ — the chain design (PR #114)
- ~~`docs/epic-a-chain-design-corrections`~~ ✓ — 10 errata + the ARC amendment (PR #115)
- ~~`feat/corpus-polish`~~ ✓ — **sprint A1a**, corpus panel reorder + row density, `7c15c2e`
- ~~`fix/experience-soft-retire`~~ ✓ — **sprint A1b**, role-level soft-retire, `5474763`
- **`feat/compose-wait-ux`** ← next (A2), stacked on this tip
- `fix/<item-20>` → `feat/role-summary-drafting` (A3) → `feat/prior-apps-pipeline` (A4)
- `epic/a-app-core` cut from A4's tip → one PR to `main`

**Do not merge anything mid-chain.** Close-out steps 4 and 5 (push / PR / merge /
prune) do **not** apply at a sprint boundary — Epic A lands as ONE PR from
`epic/a-app-core` after A4. Apply steps 0–3 at each sprint boundary; 4–5 once, at
the end.

**Owner decisions already taken — do not re-litigate:**
- Corpus section order: Summary → Work Experience → Education → Certifications → Skills.
- Epic close-out shape: the epic CHANGELOG entry, final handoff and ledger row are
  committed **on A4**; `epic/a-app-core` is cut from A4's tip.
- **One `ExitPlanMode` approval covers all four sprints** — a verified property of
  `hooks/check-plan-approved.sh`, proven against `tests/test_plan_approval_scoping.py`.
  The approved plan file `~/.claude/plans/drifting-skipping-hummingbird.md` is
  **FROZEN**: any write to it blocks every later production edit until a fresh
  ceremony. **Do not re-open this with the owner** — two sessions have now lost a
  turn to it.

---

## What just landed on `fix/experience-soft-retire`

Commit `5474763` (sprint A1b) — the 0-bullet-role retire no-op, fixed at the row
level. `Experience` gains `is_active` (alembic `0016`, native `ADD COLUMN` behind a
`PRAGMA` guard — never `batch_alter_table`, since `experience` is the cascade parent
of `experience_title`, `bullet` AND `experience_summary_item`). **No backfill**, and
that is a decision with a written reason, not an omission.

Generation is closed at the two chokepoints that cover it transitively —
`db/build_context.py` and `corpus_to_json_resume.py`, the latter filtered at the
shared query so `work[]` and its order-aligned `work_provenance` cannot drift apart.
Retired roles also drop out of the review queue, merge suggestions, skill proposals,
compositions and role-intro staging, and no longer act as a silent merge target for a
résumé re-import. Restore is `PUT {"is_active": true}`. `context_set` is
**unchanged** — filtering upstream means a retired role never reaches the payload.

37 files. Evidence: `docs/dev/diagnosis/experience-soft-retire.md` (four-layer
reproduction, passing control arm). Enumeration:
`docs/dev/blast-radius/experience-soft-retire.md`.

**Gate status — green on the committed tree, with the caveats stated.** Run on
`5474763` itself, not the staged tree:

```
=== gate: ruff check . ===  === gate: ruff format --check . ===  === gate: mypy . ===
================= 2387 passed, 1 skipped in 446.59s (0:07:26) =================
========= 138 passed, 2388 deselected, 2 xfailed in 463.57s (0:07:43) =========
=== gate: work_items check ===   work_items: OK
gate: all steps passed.
```

**Zero reruns** — verified by sweeping the full log, not by reading a bare `PASSED`
(C-7 rule 3). The only `rerun` hits are test *names* in `tests/test_ci_wait.py`, and
neither summary line carries a rerun count.

Two things about this that you should know rather than inherit as clean:
- **An earlier committed-tree attempt was killed** mid-`pytest` with no terminal
  line and free RAM at 2.39 GB. Cause **not** established (see Recurrences #2).
- **One earlier run was piped through `tail`,** which discarded the log and made its
  reruns uncheckable. That run's green is *not* evidence; the run quoted above is.
  Do not pipe the gate through `tail` — `tee` the full log and sweep it.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

`docs/dev/work/BOARD.md` is the authoritative live source (regenerate with
`python -m scripts.work_items board --write`; never hand-edited). Reproduced from the
board at this branch's tip.

**Open (1):**
1. **50** — C-7 and C-10 are enforced by Claude Code hooks only; the clauses do not
   travel to other agents or an extracted governance package.

**Blocked (3):** items 3 ([HUMAN] GitHub toggles), 5 (grounding-score persistence
gap), 8 (Compose-time rewrite latitude dial).

**Deferred (7):** items 4, 7, 24, 25, 41, 42, 43 — all owner-gated or post-1.1.0.

**Watching (19 — three NEW this session):** items 2, 16, 18, 23, 46, 47, 48, 49, 51,
52, 53, 54, 55, 56, 58, 59, and **60, 61, 62 (new)**.
- **Item 60 is new** — with every role retired and "Show retired" ticked, the corpus
  count reads "0 experiences" while retired cards render. The count is live-only by
  design; the empty-state hint branches on total rows. Cosmetic, filed not fixed.
- **Item 61 is new, and it is the one worth your attention.** Revision `0001` is
  `Base.metadata.create_all` against the **live** models, so stopping the alembic
  chain at N-1 still yields today's full schema — every
  `test_upgrade_..._adds_column_...` test skips the `op.add_column` it is named for.
  Verified directly, twice. Affects `0011`/`0013`/`0015`/`0016` alike.
- **Item 62 is new** — a scroll-creep `xfail` in
  `tests/ux/regression/test_20260708_busy_states_and_chip.py` flipped between
  `1 xfailed, 1 xpassed` and `2 xfailed` across this session's two gate runs, over
  code neither run changed. Invisible today because the marker is non-strict; it
  would fail intermittently if anyone hardened it to `strict=True`. Not
  branch-caused, not investigated.
- **Item 52 stays directly load-bearing** — and this close-out sits inside its
  window: the committed-tree gate ran green at `5474763`, then this handoff, item
  62 and the regenerated `BOARD.md` landed **after** it in a docs-only commit. No
  Python changed, and `work_items check` was re-run standalone against the final
  tree, but the full gate did not see that tree. Stated, not hidden.
- **Item 58 carries a C-11 clock** — filed as a first instance, so a note was
  compliant once. A second instance owes a fail-closed mechanism.

Open-only count stays **1**, well under the reduction-sprint threshold. **Watching is
now 18 and growing every sprint** — worth a reduction pass before it stops being read.

---

## Recurrences observed this session → guardrail authored

**Three recognized recurrences. One mechanism held; two have none, and that is
stated plainly rather than papered over.**

1. **A consumer enumeration that was grep-complete and still missed a live
   consumer — the same seam, in the opposite direction, inside the same document.**
   The dossier caught site 32 (a raw INSERT omitting a column the schema now
   requires) and, four rows later, dismissed all 50 `Experience(...)` constructions
   under `tests/` because "`default=1` applies on every ORM construction" — which is
   precisely the mechanism that breaks them: `default=1` makes the ORM *always emit*
   the column, so any test pinning the DB to a revision older than `0016` and seeding
   through the ORM fails. Two tests did exactly that.
   **Mechanism: already existed and FIRED — `python -m scripts.gate`.** The
   mandatory full-suite run before commit is the fail-closed guard, and it caught
   this when four targeted `pytest` runs (one adversarial reviewer, two implementers,
   one orchestrator) had all been green without ever touching the file. Dossier site
   50 is marked **falsified** in place rather than silently corrected, and
   `## Verification` finding 6 records the mechanism and the fix. **The transferable
   lesson: a targeted green is not evidence about a file it does not execute.**

2. **A gate run that did not complete.** Sprint A1a had one (`[gw1] node down`, free
   RAM 2.5 GB). This session's committed-tree run was killed with free RAM 2.39 GB of
   15.73. **I did NOT establish that these share a cause** — A1a's had an explicit
   node-down marker; this one's log simply stops after the `pytest` header with no
   kill message. Calling it a confirmed second instance would be an unsourced
   narrowing (C-12), so it is recorded as *a killed run, cause unestablished*.
   **Mechanism authored: none.** The prior session's reasoning still stands and this
   session agrees with it: the kill is environmental, `scripts/gate.py` takes no flags
   **by design** (single definition of "gate green"), and lowering parallelism so
   one's own run passes is the wrong move. **Surfaced to the owner in-session.**
   What *is* actionable and was measured: 13 `claude` processes held 2.49 GB, so a
   large subagent fan-out contributes to — but does not dominate — the pressure.

3. **A false-green channel: the background runner reported `exit code 0` for a gate
   run whose own output said `gate: FAILED at pytest (exit 1)`.** Recognized as a
   recurrence because it is already a known class in durable memory
   (`reference-background-bash-kill-ceiling` / `background-task-exit-code-unreliable`).
   **Mechanism authored: none — and under C-11 that is NOT compliant on its own, so
   it was surfaced to the owner as an explicit decision rather than filed and
   forgotten.** The mechanism that would fail closed is small and concrete: a checker
   that reads a gate log and exits nonzero unless it contains the exact terminal line
   `gate: all steps passed.` **and** no rerun markers — so "green" is never inferred
   from an exit code or from the absence of the word FAILED. It was not built here
   because it is a new enforcement surface arriving at close-out on an
   already-committed branch, which would need its own gate cycle; the owner was asked
   to decide rather than have it added unilaterally. **If you hit this again, that is
   a third instance and it owes the mechanism, not another paragraph.**

---

## What this branch should build

**Sprint A2 — `feat/compose-wait-ux`.** Scope is defined by `RELEASE_ARC.md`'s Epic A
section and the chain design; read both before scoping, and do not expand beyond what
they authorize.

**A1b is closed — you inherit no unfinished obligation from it.** Its committed-tree
gate is green with zero reruns (quoted above). The only tree the full gate did not
see is the docs-only close-out commit stacked on it (this handoff, item 62, and the
regenerated `BOARD.md`); no Python changed there, and `work_items check` was re-run
standalone against that final tree.

**A2 proper.** Per the design's model table, A2's implementer is **Opus** (the
Compose settle-contract carries real regression risk). Drive it with the **`Agent`
tool — never `Workflow`** — one implementer launch, read the result, judge it,
proceed. **If you find yourself writing sprint code with your own hands, you are in
the wrong role.** The mandatory **Sonnet adversarial review of the diff** runs every
sprint; instruct it to **refute**, not confirm, and fold item 52's structural
re-check (doc links, hook modes, `python -m scripts.work_items check`) into the same
pass. Confirmed correctness/regression findings **block the commit**; lower-severity
findings get filed to `BOARD.md`.

**Inherited open risk on A1b — not fact, not verified:**
- **No UX test covers role-level retire.** The retired-card class, RETIRED flag,
  Restore button, live-only count and the toggle's list reload are covered only by
  Python tests and by reading. The 12 existing corpus UX tests pass, but they were
  written for *row-level* retire.
- `ui_pages/selectors.py` deliberately untouched (C-10 gated; adding a selector no
  test consumes would be a gated edit on speculation). The one-liner is spelled out
  in the dossier's `## Deferred` for whoever adds coverage.
- The nine JS readers of `_corpusExperiences` and the by-id ownership hops are
  decided "no change" **by reading only**, and the JS ones sit in C-10's own declared
  blind spot (first-party Python import fan-in only).
- **Pyright/IDE diagnostics** (`reportOptionalMemberAccess`) appear on
  `tests/test_corpus_merge_and_retire.py` and `tests/test_proposal_review_bridge.py`
  from the repo-wide `.first().attr` idiom. Pyright is **not** in the gate; `mypy` is
  and is clean. Treat as review input, not gate failure.

Scope is bounded to Epic A sprint A2 in `RELEASE_ARC.md`. Do not expand beyond what
is listed there.

---

## First move

**Read `docs/dev/handoffs/docs-epic-a-wave-orchestration-design.md` in full before
any tool call**, then create `feat/compose-wait-ux` off this tip. A1b is closed and
gated; there is nothing to finish first. The design doc is named first deliberately —
skipping it is the single most expensive mistake this chain has made, twice.

**No new plan ceremony is needed or wanted.** One `ExitPlanMode` approval already
covers all four sprints, and the approved plan file is FROZEN — writing to it blocks
every later production edit. Progress goes in the ledger, `BOARD.md`, and commit
messages.

**Model and role:** you are the **orchestrator** — Opus at effort `high` (`xhigh` is
reserved for the single final full-epic review at A4). One implementer `Agent` launch
per sprint, plus the Sonnet refuter.

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
