<!-- provenance: schema=1 session=e9e3e26d-6a92-45a0-b258-2053289bf4ab branch=feat/dev-docs commit=6eacaf5 actor=amodal1 agent=anthropic/claude-opus-5-5 generated_at=2026-09-30 -->

# Agent handoff — Epic D sprint D3 dev half close (`feat/dev-docs`)

**Branch to create:** `feat/docs-assets-enforcement` (branch off `epic/d-docs-ia`)
**Base branch:** `epic/d-docs-ia`

> **Model for the next session: Sonnet** (RELEASE_ARC Final March prescription: Opus for D1/D3,
> Sonnet for D2/D4).
>
> **Epic cadence (owner decision, 2026-09-27):** Epic D runs on the integration branch
> `epic/d-docs-ia`. Each sprint branch merges into it as that session's final act, and the
> whole epic lands as **one PR after D4**. The epic branch is **local-only until the owner
> authorizes a push**.
>
> **The close-out protocol moved on this branch.** The branch close-out checklist and the
> handoff-intake steps now live in `docs/dev/maintainer-lane.md`, which `CLAUDE.md` imports;
> `AGENTS.md` keeps a pointer section. The template's verbatim close-out block below is
> unchanged (item 135 records that its step 1 lags `python -m scripts.gate`).

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

**Stream:** Epic D, `epic/d-docs-ia` (board item 39): documentation and information
architecture.
**Sequencing rule:** strictly sequential — one branch at a time.
**Blocked until this stream tags:** Epic E (`chore/release-v1.1.0`). Epic D lands as one PR,
not a tag.

- ~~Epic C~~ ✓ — merged to `main` as PR #148 (`f3dd472`).
- ~~`feat/docs-ia-design` (D1)~~ ✓ — audits, research and the design doc.
- ~~`feat/docs-split` (D2)~~ ✓ — the mechanical split and the publication registry.
- ~~`feat/user-docs` (D3, user half)~~ ✓ — the user tier's content.
- ~~**`feat/dev-docs` (D3, dev half)**~~ ✓ ← this branch: the dev tier, O-2, item 127.
- **`feat/docs-assets-enforcement` (D4)** ← next, and the last sprint before the epic PR.

After D4, the epic PR (`epic/d-docs-ia` → `main`) is the owner's call. Don't open it on the
D4 branch unless the owner says to.

---

## What just landed on `epic/d-docs-ia`

Commits on `feat/dev-docs`, fast-forwarded into `epic/d-docs-ia` with the owner's confirmation:

- **`2b03cdc`: dossier + ledger.** The C-10 dossier `docs/dev/blast-radius/dev-docs.md`,
  written before any edit. It carries the owner's kickoff decisions, 25 consumer rows,
  Deferred, and a dated addendum per commit group. Plus the consumed-event ledger row
  (session `e9e3e26d`).
- **`35192ee`: item 127 closed.**
  - CONTRIBUTING and `agents/git-flow.md` now say PR-only landing (no local `--no-ff` merge).
  - The "latent" CI wording is gone from six files.
  - AGENTS, CONTRIBUTING and `ci.yml` cite `scripts/gate.py` instead of "four steps".
  - A scan found 9 contradiction hits at `f0e1b5f` and 0 after.
- **`9e41c70`: O-2, AGENTS.md split.**
  - The owner's session protocol moved to `docs/dev/maintainer-lane.md`, text intact.
  - `CLAUDE.md` gained `@docs/dev/maintainer-lane.md`.
  - AGENTS.md keeps the code rules plus a "Branch close-out checklist" pointer section:
    31,961 → 23,220 bytes.
  - No charter amendment was needed: every citer of that heading still resolves.
- **`797d8dc`: `docs/dev/diagnostics.md`.** For each of the five console tabs, a Mermaid
  flow plus a control table: route `path:line`, paid?, run lock?, and the `_DASH_HELP` key.
  `dashboard/README.md` now says five tabs and the inline detail panel. Item 134 filed.
- **`4fac13a`: module map refresh.**
  - `architecture.md` now covers every root module and package, with the stale names fixed
    and the route counts replaced by the command that recounts them.
  - The item-20 labels now say the legacy Generate branch is reachable only by a direct POST
    (item 67).
- **`eba60cb`: `docs/dev/tooling.md`.**
  - The roster: 9 hooks, 11 guards, 12 commands, 11 subagents, 1 skill; 44 of 44 names are
    present.
  - CLAUDE.md's catalog is fixed: plan-gate + require-feature-branch bullets, `n1-*`, the
    model-pin count.
  - `enforcement.md` gains a dated "all shipped" status note.
- **`582c06b`, `1b8e0fe`, `2761a8d`: the §2.1 dev rows.**
  - The README dev sections are now links.
  - `vision.md` and the AGENTS header no longer restate "C-0…C-6".
  - `system-model.md` names its user-tier wiki twin.
  - PRODUCT_SHAPE §1/§7/§9/§10 moved to `docs/dev/archive/PRODUCT_SHAPE-history.md`
    (owner decision). The live §10 cites were repointed: calibration "B" → item 5, and
    RELEASE_CHECKLIST's process step → `work/BOARD.md`.
  - `documentation-architecture.md`'s body was rewritten to the shipped model.
  - ACCESSIBILITY was verified as a no-op.
- **`ba67e2d`: `docs/dev/README.md`.** The dev ladder D0–D5 as a table, a
  "where to make a change" index, and every live `docs/dev` doc routed by kind. Verified: no
  loose doc unindexed.
- **`1d1ef15`, `e836886`: close-out.** CHANGELOG; items 135 and 136. Item 136 is marked as a
  recurrence, with no mechanism authored; see below.
- **`6eacaf5`: scoped `/wiki-self-update`** (owner-authorized, checkpoint *not* advanced).
  Pages: `code-module-map`, `diagnostics-console`, `governance-extraction`. Author ≠ auditor:
  0 DRIFTED / 0 UNSUPPORTED. The other 16 wiki-relevant sources were verified no-edit
  (`docs/wiki/log.md`).

**Gate on the final tree:** split across two runs, read from the logs, not the task status. Run 1 (`python -m scripts.gate` on `6eacaf5`): "gate: 1.34 GB free (floor 1.00 GB) -- proceeding."; ruff "All checks passed!"; format "373 files already formatted"; mypy "Success: no issues found in 389 source files"; pytest not-ux "2885 passed, 6 skipped", 0 RERUN. The harness then killed run 1 for low system memory about 14% into the UX tier, with no failures to that point. Run 2 (owner-directed: rerun only the unfinished steps, same tree, at 1.12 GB free): pytest ux "161 passed, 2891 deselected, 2 xpassed", 0 RERUN; "work_items: OK (136 files)". So every gate step passed, but **not as one `python -m scripts.gate` invocation**.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

The authoritative home is `docs/dev/work/BOARD.md`, regenerated on this branch. **Header:
"Open 33 / 10 ceiling -- OVER".** The reduction sprint is overdue and is flagged again here.
When to run it is the owner's call (after Epic D, or sooner).

`## Open`:
- **50** *(owner)*: C-7/C-10 are enforced by Claude Code hooks only; they don't travel to
  other agents.
- **98**: wiki freshness measures checkpoint staleness, not page staleness. This branch's
  scoped pass left the checkpoint at `ca17897`, so the count keeps growing: 19 wiki-relevant
  files as of this close.
- **99**: install.md documents two never-published distribution paths (open until item 3
  publishes).
- **105**: corpus import produces no education entries.
- **106**: Compose bullet-text edits don't reach an already-frozen application.
- **107**: first run offers no account-naming step.
- **111**: `check-plan-approved.sh` costs about 2 s per edit, and 8–21 s per retire, on
  Windows/MSYS.
- **112**: the Dashboard Since filter raises TypeError (naive vs offset-aware dates).
- **115**: the UX-8 test needs a `getComputedStyle` assertion.
- **116**: the "Run this fixture" help bubble was never verified to open in a browser.
- **117**: paid diagnostics runs have no server-side single-flight lock.
- **118**: redaction misses quoted-key header forms and Basic auth.
- **119**: the run lock has no owner; three `acquire()` sites ignore its result. This is now
  documented in `docs/dev/diagnostics.md`.
- **120**: a declined run leaves its button pulsing.
- **121**: `run_detail` reads the whole log per modal open; a non-object line gives a 500.
- **122**: weak C3 test assertions.
- **123**: `verify-binary-on-path` blocks shell brace groups.
- **124**: recurrence: agents invoke bare `ruff` and get hook-blocked.
- **125** *(owner)*: merged epics 37/38 still read `blocked`.
- **126**: a stale local docs-site projection reads as authoritative. D4 has a candidate
  mechanism.
- **128** *(owner)*: stray `python3.13` processes from earlier sessions. Still present at
  this close: hook-parsing `python3 -c` stubs dated 2026-09-18..30, all ~0 MB.
- **129** *(owner)*: personal portfolio/interviewer framing in two frozen records.
- **130**: profile edits (Notes, identity) likely never reach `Candidate`. Code-read only.
  It still holds the Notes documentation.
- **131**: a retired application can't be found again.
- **132**: "Submit answers and regenerate" may not change a frozen résumé (UNVERIFIED).
- **133** *(owner)*: no way to delete a candidate profile.
- **136** *(new)*: `block-merge-to-main` matches merge-to-main text anywhere on one line of
  the raw command (grep patterns, heredoc bodies). A recurrence; see below.

Children of epic 39 (open, not in `## Open`):
- **134** *(new)*: the Tuning smoke cost estimate (≈$0.20 for two runs) contradicts Quality
  smoke (≈$0.35–0.40 for one). Needs a measured run, not a doc edit.
- **135** *(new, owner)*: two copies of the close-out protocol have drifted from
  `maintainer-lane.md`:
  - the template's verbatim step 1 (ruff+mypy+pytest; the gate runs 6 steps);
  - `charter.md:206`'s "step 4" (it's step 5).

  The template is a gated surface and the charter is ceremony, so both are the owner's
  decision.

Plus `## Blocked` (4), `## Deferred` (9, including **113**: 18 console-UX findings awaiting
owner triage), `## Watching` (45) and `## Epics` (6; **39** open). Full detail: `BOARD.md`.

Declared, not filed (carried from `user-docs` and still true):
- **Stale code comment** at `db/build_context.py:92` ("two chokepoints…") predates item
  75's third filter. Fold it into any branch that touches that file.
- **Settings has no help bubble.** `_initHelp` attaches only to `.cb-panel`
  (`static/app.js:2371`), and Settings is a drawer. It's product code; the owner decides
  whether it's wanted. It overlaps D4's "Learn more" wiring, so decide it there.

---

## Recurrences observed this session → guardrail authored

1. **`block-merge-to-main` blocked a command that only *contained* merge-to-main text** (a
   heredoc line saying "git merge/push targeting main").
   - **Recognized as a recurrence:** the owner's session memory recorded "`block_merge_to_main`
     matches command TEXT" as a live trap on 2026-08-04.
   - **No mechanism authored.** The fix changes a safety guard's matching, which is outside a
     docs sprint's scope. The current failure direction is also safe: it over-blocks.
   - Filed as item 136, with the mechanism and a workaround (put scripts in a file). **Surfaced
     to the owner at close.**
2. **A subagent's report carried wrong facts** (C-12 class; recurrence of the `user-docs`
   handoff's recurrence 2). Three this session:
   - the diagnostics explorer put `_safe_username`/`_within` in `web_infra/request_gates.py`
     (they're in `security.py`);
   - it overstated the cost contradiction (the full-subset figures are consistent);
   - it counted ~69 wordmark hits in `dashboard.html` (there are 0).

   All three were caught by re-reading source before writing. **No mechanism authored.** C-12's
   controls cover citations, not subagent correctness, and no deterministic check can verify
   a subagent's prose claim. Surfaced to the owner.
3. **The interrogative-witness PAUSE fired on background task notifications** (5 re-runs).
   Item 87's own record calls this accepted, by-design friction ("task notifications count as
   prompt-receipt events"). **No mechanism authored:** not a defect by the item's own terms.
   Noted for the owner.
4. **A doc restated a count that had rotted.** Examples:
   - CONTRIBUTING's "six of the ten" hooks;
   - CLAUDE.md's "other six" Sonnet subagents;
   - AGENTS' "four steps";
   - architecture.md's "93 routes".

   This is the D1 audits' drift class and the `user-docs` handoff's recurrence 1. **No
   fail-closed mechanism authored on this branch.** The designed one is D4's enumeration-drift
   lint (docs-ia-design §5.5). This branch replaced each count with a citation or a
   re-derivation command, and `docs/dev/tooling.md` says plainly that no test checks it yet.

---

## What this branch should build

D4, per `docs/dev/RELEASE_ARC.md` §"Epic D" D4 bullet, quoted verbatim: *"Full screenshot
regeneration (item 9) + README hero wiring; diagram refresh; wire C3's bubble "Learn more"
links to their doc pages; in-app ↔ docs-site link integrity; implement the D1 lints/hooks +
doc-writing skill; wiki self-update + wiki-lint green; assistant audience gating re-verified
against the new tree."* The lint and skill designs are `docs/dev/docs-ia-design.md` §5
(§5.1–§5.2 already shipped in D2; §5.10 is the doc-writing skill).

1. **Screenshots (item 9) + README hero.** Regenerate with `scripts/capture_screenshots.py`
   (page objects in `ui_pages/`); runbook `docs/dev/screenshot-capture.md`.
2. **Diagram refresh.** Render-check every Mermaid block. This branch could **not** parse
   Mermaid locally: `docs-site/node_modules/mermaid` needs a DOM, and the known-good
   `architecture.md` diagrams fail the same way as the control arm (dossier C3 addendum).
   So the five new diagrams in `docs/dev/diagnostics.md` are unverified. The docs-site
   build is the place to prove them.
3. **"Learn more" links** from C3's help bubbles (`_DASH_HELP` in `dashboard.html`,
   `_HELP_REGISTRY` in `static/app.js`) to their doc pages: `docs/dev/diagnostics.md` for
   the console, the user guides for the wizard. The Settings help-bubble question (above)
   belongs here.
4. **In-app ↔ docs-site link integrity.**
5. **The §5 lints.** The first is the enumeration-drift lint (§5.5). This branch left it a
   ready target: `docs/dev/tooling.md` lists every hook, guard, command, subagent and skill
   derived from the tree. The completeness check used in the dossier's C5 addendum (44 of 44
   names) is the lint's core. Also the wordmark lint (§5.4) and the shared doc-corpus pass
   (`scripts/doc_corpus.py`, §5 intro).
6. **Wiki:**
   - a checkpoint-advancing `/wiki-self-update` (the checkpoint is at `ca17897`);
   - `/wiki-lint` green;
   - the coverage gaps handed on from `user-docs` (keyless-client refusal, education
     degree+field rendering, the docs IA split).
7. **Assistant audience gating**, re-verified against the new tree (`docs/user/**` = user;
   `docs/dev/**` = dev; `blueprints/assistant.py` path→audience rules).

Scope is bounded to Epic D, D4 in `docs/dev/RELEASE_ARC.md` and the D1 design's §5.
Do not expand beyond what is listed there.

---

## First move

Create branch `feat/docs-assets-enforcement` off `epic/d-docs-ia`, write a plan
at `~/.claude/plans/<slug>.md`, and show it to the user before touching any
code. **Do not code first.**

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