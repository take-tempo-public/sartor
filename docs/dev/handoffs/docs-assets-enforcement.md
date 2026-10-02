<!-- provenance: schema=1 session=f0c731c3-306e-41e4-bcbe-b96ca895e23a branch=feat/docs-assets-enforcement commit=a377c94 actor=amodal1 agent=anthropic/claude-opus-5-5 generated_at=2026-10-01 -->

# Agent handoff — Epic D sprint D4 close (`feat/docs-assets-enforcement`)

**Branch to create:** `chore/release-v1.1.0` (Epic E, E1), off `main`, once the Epic D PR has merged
**Base branch:** `main`

> **Model for the next session: Opus** (RELEASE_ARC Final March prescription: E1 is Opus,
> "public-cut integrity").
>
> **Epic D is complete on `epic/d-docs-ia`.** D4 was the last sprint. The whole epic lands as
> **one PR** (`epic/d-docs-ia` → `main`), and opening and merging it is **the owner's call**.
> The epic branch is local-only until the owner authorizes a push. If the Epic D PR has not
> merged when you start, that is your first question to the owner. Don't start E1 on a `main`
> without it.
>
> **D4 ran on Opus, not the prescribed Sonnet** (owner decision at D4 kickoff, 2026-10-01).

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
5. `docs/dev/architecture.md` — module map and LLM routing
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

**Stream:** Epic D, `epic/d-docs-ia` (board item 39), documentation and information
architecture, is **complete pending its PR**. Next is Epic E, `epic/e-release` (board item 40).
**Sequencing rule:** strictly sequential, one branch at a time.

- ~~Epics A, B, C~~ ✓ merged to `main`.
- ~~`feat/docs-ia-design` (D1)~~ ✓, ~~`feat/docs-split` (D2)~~ ✓, ~~`feat/user-docs` / `feat/dev-docs` (D3)~~ ✓.
- ~~**`feat/docs-assets-enforcement` (D4)**~~ ✓ ← this branch.
- **Epic D PR** (`epic/d-docs-ia` → `main`): the owner's call, next.
- **`chore/release-v1.1.0` (E1)**, after that.

---

## What just landed on `epic/d-docs-ia`

Commits on `feat/docs-assets-enforcement`, fast-forwarded into `epic/d-docs-ia` with the
owner's confirmation. The C-10 dossier `docs/dev/blast-radius/docs-assets-enforcement.md`
holds every measurement, falsified hypothesis and observation, in a dated addendum per step.

- **`092e544`, kickoff.** The dossier was written before any edit, with the consumed-event
  ledger row. Items 137 (review models and settings for performance and cost) and 138
  (Settings has no help bubble) were filed at the owner's request.
- **`32c2366`, shared doc corpus.** `scripts/doc_corpus.py` makes one shared pass, with
  lexical link resolution. The three doc checkers produce byte-identical output, and an
  18-shape differential test against the old link checker matched exactly. The link check
  went from 6.52 s to 1.98 s (min, interleaved A/B, n=7).
- **`55e13c5`, the §5 lints.** `scripts/doc_lints.py` adds rows 5.3–5.9, gated by
  `tests/test_doc_lints.py`, with a seeded violation for every row including 5.2. The first
  run hit 49 blocks. The lint bugs among them were fixed; the true violations were fixed in
  the docs. The charter gained clause headings and `Sartor` in sentences (an editorial
  change, owner-directed, with a dated note in the charter).
- **`ad8a7ac`, the doc-writing skill.** `skills/doc-writing/` holds the evaluation plan,
  which has not been run.
- **`568e558`, screenshots.** All 10 were regenerated (item 9), and the README hero is
  wired. The capture had failed at Generate because the month-precision gate refused the
  fixture's year-only dates. Two hypotheses were falsified first; see the dossier. At the
  owner's direction, the demo candidate's three year-only duplicate roles were dropped from
  `db/resume.sqlite`, with a backup taken first.
- **`d4b0216`, assistant gating.** `ACCESSIBILITY.md` (user tier) had resolved as `dev`. The
  registry is now the oracle in `tests/test_assistant_path_audience.py`.
- **`038c36c`, "Learn more" links.** Every help bubble, 16 in the wizard and 39 in the
  console, now links to its docs section. Targets are checked by `tests/test_help_learn_more.py`.
- **`084e8b7`, the docs-site build.**
  - **The build had been broken since D2:** all 10 images, because image links were not
    rewritten. Fixed in the projector.
  - **One architecture diagram had been rendering as raw source:** a `;` in a label. Fixed.
  - New `scripts/check_docs_site_mermaid.py`, wired into `docs-deploy.yml` on PRs as well.
    Both halves were proven with seeded failures.
  - The projection stamp, `sourceCommit`, plus `check_docs_projection_fresh.py` (item 126).
  - Items 9 and 126 are closed with `verified_by`.
- **`3798e2d` + `4b32022`, the wiki.** A checkpoint-advancing `/wiki-self-update` covered
  `ca17897..3798e2d`: 3 new pages (the coverage gaps handed on from `user-docs`) and 5
  updated. Author ≠ auditor on all 8: 5 DRIFTED re-anchored, 0 UNSUPPORTED. Structural lint:
  0 ERROR.
- **`a377c94`, sweep.** Items 141 and 142.

**Gate on the final tree:** one `python -m scripts.gate` invocation on `a377c94`, read from its log rather than the task status. The first attempt was stopped by Claude Code for low system memory (non-UX tier at 48%, no failure that wasn't the killed worker). The owner then said "rerun". The complete run reported: "gate: 1.05 GB free (floor 1.00 GB) -- proceeding."; ruff "All checks passed!"; format "381 files already formatted"; mypy "Success: no issues found in 397 source files"; pytest not-ux "3025 passed, 6 skipped"; pytest ux "163 passed, 3031 deselected, 1 xfailed, 1 xpassed"; "work_items: OK (142 files)"; "gate: all steps passed." There were 0 RERUN lines in the log.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

The authoritative home is `docs/dev/work/BOARD.md`, regenerated on this branch. **Header:
"Open 37 / 10 ceiling -- OVER".** The reduction sprint is overdue. It has been flagged at every
Epic D close, and it is flagged again here. When to run it (before E1, or after) is the
owner's call.

`## Open`:
- **50** *(owner)*: C-7/C-10 are enforced by Claude Code hooks only; they don't travel to
  other agents.
- **98**: wiki freshness measures checkpoint staleness, not page staleness. This branch
  advanced the checkpoint to `3798e2d`.
- **99**: install.md documents two never-published distribution paths (open until item 3).
- **105**: corpus import produces no education entries.
- **106**: Compose bullet-text edits don't reach an already-frozen application.
- **107**: first run offers no account-naming step.
- **111**: `check-plan-approved.sh` costs about 2 s per edit on Windows/MSYS.
- **112**: the Dashboard Since filter raises TypeError (naive vs offset-aware dates).
- **115**: the UX-8 test needs a `getComputedStyle` assertion.
- **116**: the "Run this fixture" help bubble was never verified to open in a browser.
- **117**: paid diagnostics runs have no server-side single-flight lock.
- **118**: redaction misses quoted-key header forms and Basic auth.
- **119**: the run lock has no owner; three `acquire()` sites ignore its result.
- **120**: a declined run leaves its button pulsing.
- **121**: `run_detail` reads the whole log per modal open; a non-object line gives a 500.
- **122**: weak C3 test assertions.
- **123**: `verify-binary-on-path` blocks shell brace groups. Hit again in D4.
- **124**: recurrence: agents invoke bare `ruff` and get hook-blocked.
- **125** *(owner)*: merged epics 37/38 still read `blocked`.
- **128** *(owner)*: stray `python3.13` processes from earlier sessions.
- **129** *(owner)*: personal portfolio/interviewer framing in two frozen records.
- **130**: profile edits likely never reach `Candidate`. Code-read only.
- **131**: a retired application can't be found again.
- **132**: "Submit answers and regenerate" may not change a frozen résumé (UNVERIFIED).
- **133** *(owner)*: no way to delete a candidate profile. In D4 the demo candidate's rows
  had to be deleted by hand.
- **136**: `block-merge-to-main` matches merge-to-main text anywhere in a command.
- **137** *(new)*: review the current models and call settings for performance and cost.
- **140** *(new)*: generated text leaks internal bullet ids (`b173`, `b180`), and the cover
  letter invents its date. **Both are visible in two of the new screenshots**
  (`readme_hero_…`, `walkthrough_coverletter_…`). Recapture them after the prompt fix.
- **142** *(new)*: recurrence: backslash escapes in heredoc Python corrupt files. A guard is
  proposed; see below.

Children of epic 39 (open, not in `## Open`):
- **134**: the Tuning vs Quality smoke cost estimates contradict each other. It needs a
  measured run.
- **135** *(owner)*: the template's verbatim close-out step 1 and `charter.md`'s "step 4" lag
  `maintainer-lane.md`. The lint 5.5 module and gate-step checks carry a reviewed exception
  for the template that cites this item.
- **138** *(new, owner)*: the Settings drawer has no help bubble.
- **139** *(new)*: `capture_screenshots.py` leaves its demo user behind (cleanup isn't in a
  `finally`; DB rows persist).
- **141** *(new)*: the `wiki-scribe` agent is told to create pages but has no Write tool.

Plus `## Blocked` (4), `## Deferred` (9, including **113**: 18 console-UX findings awaiting
owner triage), `## Watching` (45) and `## Epics` (6; **39** ready to close when its PR
merges). Full detail: `BOARD.md`.

Declared, not filed (still true):
- **A stale code comment** at `db/build_context.py:92` ("two chokepoints…") predates item
  75's third filter. Fold it into any branch that touches that file.
- **The doc-writing skill's evaluation plan has not been run** (`skills/doc-writing/SKILL.md`
  §"Evaluation plan"). Running it costs agent sessions, so when is the owner's call.
- **32 pre-existing one-way wiki backlinks**, a WARN in this branch's structural lint. None
  are on new pages.

---

## Recurrences observed this session → guardrail authored

1. **A doc restated a count or list that had drifted from the code**: vision's and
   RELEASE_ARC's 7-of-8 deterministic modules, two gate descriptions, and stale
   `tooling.md`-class rosters. This is the D1 audits' class, flagged in both D3 handoffs.
   - **Guardrail authored:** lint 5.5 (`doc_lints.lint_enumeration_drift`,
     `lint_tooling_roster`). It fails the gate on a near-complete list of a code-enumerated
     set, a partial gate-step description, a stale charter range, or a `tooling.md` roster
     that doesn't match the tree in either direction. Each check has a seeded test.
   - Stated limits are in the module docstring. A list missing three or more members isn't
     caught, and the gate-step check needs a "quality gate" marker.
2. **Backslash escapes in heredoc Python corrupted files** (3 times this session; in the
   owner's memory since 2026-08-05).
   - **No mechanism authored.** A new Bash guard is outside a docs sprint's scope.
   - Filed as **item 142** with a fail-closed design: refuse `python -` from a heredoc whose
     body contains a backslash. **Surfaced to the owner.**
3. **Subagent reports carried wrong facts** (the C-12 class; recurrence 2 of the D3
   handoff). Examples this session:
   - a scribe claimed the projector reads the moved-paths map;
   - an auditor "verified" a link that can't resolve;
   - the first explorer's line cite for `_initHelp` was off.

   All were caught by re-reading source before relying on them. **No mechanism authored:**
   no deterministic check can verify a subagent's prose claim. The wiki path's
   author ≠ auditor split caught 5 drifts. **Surfaced to the owner.**
4. **The interrogative-witness pause fired on background task notifications** (about 10
   re-runs this session). Item 87's own record calls this accepted friction. **No mechanism
   authored:** not a defect by the item's terms.

---

## What this branch should build

E1, per `docs/dev/RELEASE_ARC.md` §"Epic E" E1 bullet, quoted verbatim: *"Version 1.0.9 →
1.1.0; CHANGELOG `[Unreleased]` → `[1.1.0]` with the D-7.4 CVE-disclosure line (explicit
"none" if none). Pre-tag gates all green: `python -m scripts.gate`; eval smoke; `/wiki-lint`;
`compliance-witness`; fresh-clone install + run re-verify; the `check_untyped_defs`
type-scan (tag criteria above). Owner `[HUMAN]` steps (item 3) execute during this epic:
repo rename, PyPI Trusted Publisher, GHCR, `enforce_admins`. Tag `v1.1.0` → `release.yml`
publishes (OIDC + Sigstore); verify `pip install sartor` from PyPI; create the GitHub
Release with notes (`release.yml` does not create one). Local-dev install path stays
documented."*

Step-by-step mechanics: `docs/dev/RELEASE_ARC.md` step 17 (`chore/release-v1.1.0`). Scope is
bounded to E1. Do not expand beyond it.

---

## First move

Confirm with the owner that the Epic D PR (`epic/d-docs-ia` → `main`) has merged. Then
create branch `chore/release-v1.1.0` off `main`, write a plan at `~/.claude/plans/<slug>.md`,
and show it to the user before touching any code. **Do not code first.**

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
