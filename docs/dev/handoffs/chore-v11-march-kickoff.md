<!-- provenance: schema=1 session=b6ced217-9fff-4b18-a6d4-82bc2cd54d24 branch=chore/v11-march-kickoff commit=e4902c8 actor=amodal1 agent=anthropic/claude-fable-5 generated_at=2026-08-04 -->

# Agent handoff: after `chore/v11-march-kickoff` (Final March filed; next: epic A, sprint A1)

**Branch to create:** `epic/a-app-core` off `main`, then `fix/experience-soft-retire` off it
(sprint A1's first branch — see "First move")
**Base branch:** `main`

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

**Read for this handoff specifically:** `RELEASE_ARC.md` §"v1.1.0 Final March
(2026-08-04 — owner-approved epic sequence)" — the governing plan for everything from
here to the public v1.1.0 tag. It defines the five epics (A–E, board items 36–40), the
sprint-session cadence (one sprint = one branch = one session, full per-branch
close-out, one PR per epic), the session-model prescriptions, and every sprint brief
with its adversarial-review amendments. `docs/dev/work/BOARD.md` is the live-status
source.

**Stream:** v1.1.0 Final March — epic A (`epic/a-app-core`, board 36).
**Sequencing rule:** strictly sequential — one branch at a time.
**Blocked until this stream tags:** the public v1.1.0 cut (epic E / item 10).

- ~~`fix/wiki-freshness-relevance-classification`~~ ✓ — item 35, gate measurement fixed (PR #97)
- ~~`fix/extract-experiences-telemetry-pollution`~~ ✓ — item 33, telemetry pollution (PR #96)
- ~~`chore/v11-march-kickoff`~~ — this branch (march plan + board filing; PR pending merge at authoring)
- **`fix/experience-soft-retire`** ← next (sprint A1, first branch; Opus session)
- `feat/corpus-polish` ← A1's second branch, its own session after the fix lands
- A2–A4, then epics B–E ← do not start any of these on the A1 branches

Do NOT start A2 (compose UX), A3 (role-summary drafting), or A4 (prior-apps move) on an
A1 branch — each is its own sprint session per the march cadence, and the march briefs
in RELEASE_ARC bound each one. Do not touch epics B–E work at all yet.

---

## What just landed on `main`

**Not yet merged at authoring time** — this branch's PR follows this handoff's commit.
`main` is at `e4902c8` (PR #96, item 33). This branch's own work adds (docs only, no
production code):

- `docs/dev/RELEASE_ARC.md`: new §"v1.1.0 Final March" — five owner-approved epics
  (A–E) with sprint briefs, acceptance criteria, cadence rules, and session-model
  prescriptions; a Phase-5 update note pointing at it.
- Board: epics 36–40 filed (only A open; B–E blocked in sequence); post-1.1 items
  41–43 (domain-vocabulary library, dotx/mht template investigation, approved-fonts
  expansion) deferred; items 9→epic D, 10→epic E, 20→epic A (owner direction captured:
  hard-gate the Step-5 rail on frozen composition; `decision_owner` flipped to agent),
  34→epic A; item 2 gains the wordmark-lint exclusion constraint. `BOARD.md`
  regenerated — Open 3/10.
- Provenance: this session's `consumed` ledger row; the 520b7b1b session's dropped
  third ledger row restored (appended in chronological order).
- `docs/wiki/log.md`: scoped close-out relevance check recorded — `RELEASE_ARC.md`
  classifies wiki-relevant; all 6 citing pages verified no-edit (every cite anchors to
  sections this additive change didn't touch).
- Gate: run on this branch via backgrounded `python -m scripts.gate` — see the PR
  checks for the authoritative result.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

**Adaptation note (same as predecessors):** `docs/dev/work/BOARD.md`'s full still-open
subset is rendered below; `RELEASE_CHECKLIST.md`'s Carry-forward ledger is superseded.

**Open (3 / 10 ceiling):**
1. Epic 36 — Final March epic A (active stream; this handoff's next move).
2. Item 9 — visual-assets refresh (now epic D, sprint D4 — deliberately last-but-one).
3. Item 20 — legacy `generate()` reachable via wizard rail (now epic A, sprint A2;
   owner direction captured: hard-gate on frozen composition).

**Blocked (3 + the sequenced epics):**
4. Item 3 — [HUMAN] GitHub toggles (repo rename, PyPI Trusted Publisher, GHCR,
   `enforce_admins`) — executes during epic E, owner-gated.
5. Item 5 — grounding-score persistence gap.
6. Item 8 — compose-time rewrite dial, pending owner direction.
7. Item 10 — release cut v1.1.0 (epic E terminal step; `depends_on = [3, 6, 7, 9, 19]`).
8. Epics 37–40 — B (render/ATS), C (diagnostics), D (docs IA), E (release) — blocked
   in march sequence A→B→C→D→E.

**Deferred (7):**
9. Item 4 — in-app citation viewer, no friction signal yet.
10. Item 7 — PX-46 memory consolidation, owner sign-off required first.
11. Item 24 — template-preview fidelity spike (related: new item 42).
12. Item 25 — `app.run(threaded=True)` governance decision.
13. Item 41 — domain-vocabulary library for Compose (post-1.1, owner-scheduled).
14. Item 42 — dotx/mht template-format investigation (post-1.1).
15. Item 43 — approved-fonts expansion (post-1.1, per-font verification).

**Watching (5):**
16. Item 2 — wordmark sweep, opportunistic only; the D1/D4 wordmark lint MUST inherit
    its exclusions (`docs/wiki/`, `docs/dev/reviews/`).
17. Item 16 — `evals/runner.py --suite real` non-functional.
18. Item 18 — judge-score run-to-run variance, n=2, uncharacterized.
19. Item 23 — PX-52 analyzer.py split, WATCH disposition.
20. Item 34 — corpus blueprints' `_get_client` unpatched in the UX harness (now epic A —
    an explicit A3 step before any new corpus UX test lands).

Also standing, not a numbered item: the 12 genuinely wiki-relevant files with
accumulated drift since the last real ingest (listed in the item-35 handoff) — picked
up piecemeal by per-branch close-out checks, or all at once if a session deliberately
runs `/wiki-self-update`. Item 19 (UX-flake solution sprint) remains open on the board
inside the release chain via item 10's `depends_on` — schedule it before epic E at the
latest.

Open-only count is 3 — below the ~8–10 reduction-sprint threshold.

---

## What this branch should build

Sprint A1 of the Final March, first branch: `fix/experience-soft-retire`.

1. Reproduce the defect first (C-7): soft-retiring a 0-bullet experience role
   silently no-ops — `Experience` has no retired column (`db/models.py:88-108`);
   `DELETE /api/experiences/<id>` only cascades `is_active=0` to bullets
   (`blueprints/corpus/experiences.py:236-263`, the update at `:256` matches 0 rows,
   returns 200, toasts "Retired 0 bullet(s)"). Write the dossier at
   `docs/dev/diagnosis/experience-soft-retire.md` before any production edit.
2. Fix: experience-level retired flag + Alembic migration — native `ADD COLUMN` per
   the `db/migrations/versions/0011_experience_title_is_active.py` precedent, never
   `batch_alter_table` on this parent (FK-cascade trap). Route + list filtering +
   an unretire affordance in the corpus UI (`deleteExperience`,
   `static/app.js:5499-5511`; `_renderCorpusDetail` `static/app.js:4945-4976`).
3. Blast-radius filtering (adversarial-review amendment — this is most of the work):
   audit every unfiltered `session.query(Experience)` consumer; at minimum
   `corpus_to_json_resume.py:176-181` (a retired empty role otherwise still renders
   into REAL generated output) and the curation suggestion queries
   (`blueprints/corpus/curation.py:162,341,417`); decide-and-document each site
   (filter vs deliberately include).
4. Tests: the 0-bullet retire path end-to-end (retires visibly, excluded from
   generated output, unretire restores), migration up/down on a copy.

Scope is bounded to sprint A1's `fix/experience-soft-retire` bullet in
`RELEASE_ARC.md` §"v1.1.0 Final March" (Epic A). Do not expand beyond what is listed
there — the corpus layout work (section order, education rows, skills compaction,
role-card order) is `feat/corpus-polish`, the NEXT session's branch.

---

## First move

**Owner, at launch: set `/model opus`** (march prescription for sprint A1) and approve
the session plan when asked — one click, per the sprint-session cadence.

Agent: FIRST action is `python scripts/check_handoff_pointer.py "<the pointer line you
were given>"`; once it passes, consume this file
(`python scripts/verify_doc_template.py docs/dev/handoffs/chore-v11-march-kickoff.md
docs/dev/AGENT_HANDOFF_TEMPLATE.md --event consumed --agent <agent>`). Then read
`RELEASE_ARC.md` §"v1.1.0 Final March" + `docs/dev/work/BOARD.md`. Then create
`epic/a-app-core` off `main`, create `fix/experience-soft-retire` off it, write a plan
at `~/.claude/plans/<slug>.md`, and show it to the user before touching any code.
**Do not code first.** Close-out reminder for that session: the sprint branch merges
into `epic/a-app-core` as the session's FINAL act (after the full close-out checklist);
never edit production code on the epic branch itself.

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
   the user the URL) → **wait for all required checks to go green** →
   `gh pr merge <n> --merge` (never `--squash` / `--rebase`) →
   `git checkout main && git pull --ff-only`. Use `--ff-only` so an unexpected
   divergence fails loudly instead of silently manufacturing a merge commit.
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
