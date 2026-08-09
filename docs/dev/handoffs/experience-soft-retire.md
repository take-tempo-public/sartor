<!-- provenance: schema=1 session=c42da573-16a2-49f3-a422-1cbdae638308 branch=fix/experience-soft-retire commit=b8381f5 actor=amodal1 agent=anthropic/claude-opus-5 generated_at=2026-08-09 -->

# Agent handoff: resume the Epic A chain mid-sprint-A1b — an UNCOMMITTED staged diff awaits its adversarial review

> **READ THIS BOX FIRST. This is not a normal branch-close handoff.**
> Sprint A1b's fix is **implemented, staged, and deliberately NOT committed.**
> It is waiting on the chain's mandatory **Sonnet adversarial review of the
> staged diff**, which has **not run**. Do not commit before that review. Do
> not `git stash`, `git checkout .`, or `git reset` — the staged diff is the
> sprint's work product and exists only in the working tree.
> Verify on arrival: `git status --short --branch` should show
> `## fix/experience-soft-retire` with ~22 staged entries, and
> `git diff --quiet` should exit 0 (worktree == index).

**Branch to create:** none — **continue on the existing `fix/experience-soft-retire`**
(HEAD `b8381f5`). The next branch you create is A2's `feat/compose-wait-ux`, stacked on
this branch's tip, and only after A1b closes.
**Base branch:** `feat/corpus-polish` @ `7c15c2e` (the A1a tip — this chain stacks
tip-to-tip and never branches off `main`).

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

**Before anything in the list above — the two documents this chain actually runs on:**

- **`docs/dev/handoffs/docs-epic-a-wave-orchestration-design.md`** — the chain's
  statement of intent. **Read it in full.** The session that wrote this handoff
  skipped it, worked from the errata alone, and got its own role wrong for an entire
  sprint. §"The design" is where the orchestrator role, the `Agent`-not-`Workflow`
  mechanism, the model table and the one-approval property live.
- **`docs/dev/epic-a-chain-design-corrections.md`** — the errata that supersedes it
  where they disagree. Read its "Verification status" legend first: **[REPORTED] is a
  lead, not evidence.**


**Stream:** v1.1.0 Final March — Epic A, running as an owner-sanctioned stacked-branch
chain (`RELEASE_ARC.md:1675-1686`, the 2026-08-08 amendment).
**Sequencing rule:** strictly sequential, stacked **tip-to-tip**, no intermediate
merges, one PR per epic at the very end.
**Blocked until this stream tags:** the public v1.1.0 cut (epic E / item 10).

- ~~`docs/epic-a-wave-orchestration-design`~~ ✓ — captured the chain design (PR #114)
- ~~`docs/epic-a-chain-design-corrections`~~ ✓ — 10 errata + the ARC amendment (PR #115)
- ~~`feat/corpus-polish`~~ ✓ — **sprint A1a**, corpus panel reorder + row density,
  `7c15c2e`, gate green on the committed tree
- **`fix/experience-soft-retire`** ← this branch — **sprint A1b, IN PROGRESS**,
  reproduction committed, fix staged and unreviewed
- `feat/compose-wait-ux` ← next (A2), stacked on this tip
- `fix/<item-20>` → `feat/role-summary-drafting` (A3) → `feat/prior-apps-pipeline` (A4)
- `epic/a-app-core` cut from A4's tip → one PR to `main`

**Do not start A2 on this branch.** Six branches, five handoffs — the chain's shape is
in `RELEASE_ARC.md`'s amendment and the design handoff, not improvised.

**Owner decisions already taken — do not re-litigate:**
- Corpus section order: Summary → Work Experience → Education → Certifications → Skills.
- Epic close-out shape: the epic CHANGELOG entry, final handoff and ledger row are
  committed **on A4**, and `epic/a-app-core` is cut from A4's tip. No fast-forward
  re-points.

---

## What just landed on `feat/corpus-polish`

Commit `7c15c2e` (sprint A1a) — presentational only, no schema, no routes, no Python.
`templates/index.html` panel reorder (verified a pure move: identical 34-ID set before
and after); `static/style.css` compacts skill rows onto `.pipeline-row`'s density idiom
and puts education reorder arrows parallel with Edit/Retire; `static/app.js` renders the
role card titles → summary → bullets. Gate green **on the committed tree**:
ruff ✓ · ruff-format ✓ · mypy ✓ 357 files · `pytest -m "not ux"` 2376 passed/1 skipped ·
`pytest -m ux` 138 passed/0 failed · work_items OK · **zero RERUN markers**.

**On this branch, `b8381f5`** — the C-7 reproduction commit (instrument before fix):
`tests/test_experience_soft_retire.py` + `docs/dev/diagnosis/experience-soft-retire.md`
+ ledger rows. On `7c15c2e` it fails **3 failed, 1 passed**; the control arm (retiring a
*bulleted* role) passes, which is what localizes the defect to the missing row-level flag
rather than a broken cascade.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

`docs/dev/work/BOARD.md` is the authoritative live-item source (regenerate with
`python -m scripts.work_items board --write`; never hand-edited). Reproduced from the
board at this branch's tip.

**Open (1):**
1. **50** — C-7 and C-10 are enforced by Claude Code hooks only; the clauses do not
   travel to other agents or an extracted governance package.

**Blocked (3):** items 3 ([HUMAN] GitHub toggles), 5 (grounding-score persistence gap),
8 (Compose-time rewrite latitude dial).

**Deferred (7):** items 4, 7, 24, 25, 41, 42, 43 — all owner-gated or post-1.1.0.

**Watching (16 — two NEW this session):** items 2, 16, 18, 23, 46, 47, 48, 49, 51, 52,
53, 54, 55, 56, and **58, 59 (new)**.
- **Item 58 is new** — a handoff amended after its `generated` stamp blocks the next
  session; the in-doc stamp drifts silently too. **It carries a C-11 clock:** filed as a
  *first* instance, so a note was compliant once. A second instance owes a fail-closed
  mechanism, not another item update.
- **Item 59 is new** — a corpus role card offers two summary editors (the legacy
  `Experience.summary` cache and the canonical variants section) with nothing saying
  which wins. Filed as an observation, explicitly not a diagnosis.
- **Item 52 stays directly load-bearing** — the per-sprint commit sequence's second gate
  run on the *committed* tree is what closes its window. Not optional.

**Epics (6):** 19 (UX-flake umbrella, children 27–31, 57), 36 (Epic A, children 20, 34),
37/38/39/40 (epics B/C/D/E, blocked).

Open-only count stays **1**, well under the reduction-sprint threshold.

---

## Recurrences observed this session → guardrail authored

**Three recognized recurrences.**

1. **An agent losing the chain design and rebuilding it from the errata — a fresh
   instance of the "reconstruct instead of read" class.** This session read
   `epic-a-chain-design-corrections.md` and never opened
   `docs-epic-a-wave-orchestration-design.md`, then acted for a whole sprint on a model
   of its own role assembled from the errata. Consequences: it implemented A1a **by
   hand** instead of launching the implementer agent the design requires; it downgraded
   the mandated **Sonnet** adversarial reviewer to an inline self-review; and it stalled
   the chain asking the owner to resolve a branch-per-session question the design had
   already settled and proven against `tests/test_plan_approval_scoping.py`.
   **Mechanism authored: a durable memory, and that is explicitly NOT a fail-closed
   gate — stated plainly per C-11.** New memory
   `reference-epic-a-chain-orchestration-design` records the orchestrator role, the
   `Agent`-not-`Workflow` mechanism, the Sonnet refuter, the model table and the
   one-approval property; the stale
   `project-chain-execution-experiment-and-vectoring-directives` (whose closing line
   "until then, one branch, one session, normal mode" is what actually caused the drift)
   is marked superseded for Epic A. A real gate would have to detect "you are acting on
   a doc whose superseding parent you never opened," which nothing here can do today.
   **Surfaced to the owner in-session**, who identified the loss before this session did.

2. **Compaction as an unannounced data-loss event — and this time the announcement
   itself was skipped.** `docs/dev/ledger/c42da573-….jsonl` records **three** `compacted`
   receipts (`2026-08-09T00:44:54Z`, `01:00:47Z`, `01:06:02Z`). The orchestrating session
   announced **none** of them at the time; the first mention came from the A1b subagent's
   own C-12 disclosure, reading the ledger this session had written and not read.
   C-12 exists exactly for this and the clause was violated. **Mechanism: already exists
   and worked** — `claude_context_hook.py`'s PreCompact receipt is why the evidence
   survived to be caught at all. What failed is the disclosure *by the model*, which the
   receipt cannot force. **This handoff is the compliant response to the trigger:** C-8
   names "a compaction having occurred" as an external, mechanical handoff trigger, and
   three had.

3. **A gate run killed mid-flight under memory pressure — the known shared-machine
   class.** Gate run 2 on A1a's committed tree died at 98% with
   `[gw1] node down: Not properly terminated`; run 3 passed clean in 279s vs 496s.
   Free RAM 2.5 GB of 15.7. **Mechanism authored: none, deliberately.** The kill is
   environmental, not a repo defect; `scripts/gate.py` takes no flags *by design*
   (single definition of "gate green"), and editing it to lower parallelism so one's own
   run passes is the wrong move. **Both results recorded, not just the green one**
   (C-7 rule 3). If it recurs, that is a second instance and owes a real response.

---

## What this branch should build

**Nothing new. Finish A1b in the order below.** The implementation is done and staged;
what remains is the review, the gate, and the close-out.

**1. Verify the inherited state before trusting any of it.**
```
git status --short --branch     # expect: fix/experience-soft-retire, ~22 staged
git diff --quiet && echo clean  # expect: clean (worktree == index)
git log --oneline -3            # expect: b8381f5 reproduction on top of 7c15c2e
```

**2. Read the full staged diff yourself.** `git diff --cached`. This is not optional
politeness — charter **W-1** requires the owning session to read the full diff of every
subagent contribution **before committing**, by direct line-level verification. The
session that wrote this handoff did **not** do so (it was three compactions deep and
correctly refused to). **That obligation is now yours and it is unmet.**

**3. Launch the Sonnet adversarial reviewer on the STAGED diff.** Design-mandated,
owner's explicit call, every sprint. Instruct it to **refute**, not confirm, against
sprint A1b's brief, and to fold in item 52's cheap structural re-check (doc links, hook
modes, `python -m scripts.work_items check`) in the same pass. Confirmed
correctness/regression findings **block the commit** and get fixed + re-reviewed;
lower-severity findings get filed to `BOARD.md` rather than chased mid-sprint.

**4. Then, and only then**, the per-sprint sequence (`RELEASE_ARC.md:1696-1712`):
fix findings → `git add -A` → file deferred findings →
`python -m scripts.work_items board --write` → `git add -A` → `python -m scripts.gate`
→ assert `git diff --quiet` and no unstaged/untracked entries → commit → **run the gate
a SECOND time on the committed tree** (a staged tree passes HEAD-reading checks
vacuously — finding 10 cost PR #115 three red jobs).

**5. Close-out obligations already known to be owed:**
- **Wiki:** this branch's diff **is** wiki-relevant (`db/models.py`,
  `db/migrations/**`, `static/style.css` all classify `True`). A scoped
  `/wiki-self-update` is owed, committed before the PR. A1a's own check was a
  **verified no-edit**, already logged in `docs/wiki/log.md`; drift is **22/75**.
- **This handoff's own ledger shard** is already folded into `b8381f5`.

**What the A1b implementer reported, carried forward verbatim in substance — the
blast-radius re-derivation contradicted the `[REPORTED]` appendix in four places:**
1. The appendix claims *"No raw SQL touching the `experience` table."* **False, and it
   breaks:** `tests/test_experience_summary_item_routes.py:220-230` does a raw
   `INSERT INTO experience (...)` with an explicit column list, and the new
   `NOT NULL` column has no SQL-side default (Python-side `default=1`, matching all
   three siblings). Probed to an `IntegrityError` before editing, then fixed at the
   insert rather than by deviating from the model convention.
2. `db/persist_run.py` is **absent from the appendix entirely** — three
   `query(Experience)` sites (`:194`, `:288`, `:373`), all decided "no change" with a
   reason (by-id ownership; filtering would silently drop audit rows if a role retires
   mid-run).
3. **Nine further blueprint sites** the appendix omits.
4. `web_infra/openapi.py:128-141` omitted — the appendix's "complete serializer surface"
   names four; there are five.

**Explicitly unverified — inherited as open risk, not as fact:**
- **No UX test covers the new role-level behavior.** The retired-card class, RETIRED
  flag, Restore button, live-only count and the toggle's list reload are covered only by
  Python tests and by reading. The 12 existing corpus UX tests pass, but they were
  written for *row-level* retire.
- `ui_pages/selectors.py` deliberately untouched (C-10 gated; adding a selector no test
  consumes would be a gated edit taken on speculation). Deferred with reason in the
  dossier.
- The nine JS readers of `_corpusExperiences` and the by-id ownership hops are decided
  "no change" **by reading only** — and the JS ones sit in C-10's own declared blind
  spot (first-party Python import fan-in only).
- The appendix says 49 `Experience(...)` construction sites; the implementer's grep says
  **57** (50 under `tests/`). Not reconciled site-by-site.
- **Pyright/IDE diagnostics appeared** on `tests/test_experience_soft_retire.py:120` and
  `db/build_context.py:283` (`reportTypedDictNotRequiredAccess`) plus unused-binding
  warnings. `mypy` — which is what the gate runs — was reported clean at 359 files.
  Pyright is **not** in the gate; treat these as review input, not as a gate failure,
  and check whether the `build_context.py` ones predate this branch.

**Decision already taken, with its reason, on `hardening.py`:** the flag was **not**
added to `CorpusExperience` / `career_corpus`; `context_set` is unchanged. It is a
persisted contract frozen into `application_run.corpus_snapshot_json`, so a new key
would need an absence-tolerant branch in every reader forever, and filtering at
`db/build_context.py` means a retired role never reaches the payload. Stated
consequence: a snapshot frozen before retirement still contains the role on re-render —
intended freeze semantics, same as a retired bullet.

---

## First move

**Verify the inherited state (step 1 above) before anything else.** Then read the full
staged diff, then launch the Sonnet refuter. Do not commit before the review.

**Model and role — get this right, because the last session did not:** you are the
**orchestrator**. Confirm with the owner that this session is **Opus at effort `high`**
(`xhigh` is reserved for the single final full-epic review, at A4). You drive each
sprint via the **`Agent` tool — never `Workflow`** — one implementer launch per sprint:
read the result, judge it, proceed. **If you find yourself writing sprint code with your
own hands, you are in the wrong role.**

**No new plan ceremony is needed or wanted.** One `ExitPlanMode` approval already covers
all four sprints — a verified property of `hooks/check-plan-approved.sh`, not an
assumption. The approved plan file `~/.claude/plans/drifting-skipping-hummingbird.md` is
**FROZEN**: any write to it blocks every later production edit until a fresh ceremony.
Progress goes in the ledger, `BOARD.md`, and commit messages.

**Two chain-scoped readings of the verbatim blocks below.** They are reproduced
byte-for-byte because the template requires it, and two of their clauses assume a
normal single-branch branch-and-merge session. Neither is waived — both are scoped:

1. **"One branch per session"** (Hard constraints). Epic A is an owner-sanctioned
   stacked chain (`RELEASE_ARC.md:1675-1686`): branches stack tip-to-tip and **nothing
   merges until the epic's single PR**, so "close, merge, hand off before starting the
   next" has no merge to attach to mid-chain. Creating the next sprint's branch on this
   tip is the designed behavior, not a violation. The single `ExitPlanMode` approval
   covering all four sprints is **verified**, proven against
   `tests/test_plan_approval_scoping.py`. **Do not re-open this with the owner** — the
   session that wrote this handoff did, and lost a turn to it.
2. **Close-out steps 4 and 5** (push / PR / merge / prune) **do not apply mid-chain.**
   Nothing on this branch is pushed, PR'd, merged or pruned; Epic A lands as **one PR
   from `epic/a-app-core`** after A4. Apply steps 0–3 at each sprint boundary, and
   steps 4–5 once, at the end of the epic.

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
