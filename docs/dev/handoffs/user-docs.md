<!-- provenance: schema=1 session=d3d2e857-5e71-497d-8e08-a2079eee5c9c branch=feat/user-docs commit=a47ea16 actor=amodal1 agent=anthropic/claude-opus-5-5 generated_at=2026-09-29 -->

# Agent handoff — Epic D sprint D3 user half close (`feat/user-docs`)

**Branch to create:** `feat/dev-docs` (branch off `epic/d-docs-ia`)
**Base branch:** `epic/d-docs-ia`

> **Model for the next session: Opus** (RELEASE_ARC Final March prescription: Opus for D1/D3,
> Sonnet for D2/D4).
>
> **Epic cadence (owner decision, 2026-09-27):** Epic D runs on the integration branch
> `epic/d-docs-ia`. Each sprint branch merges into it as that session's final act (D2 fast-forwarded
> it), and the whole epic lands as **one PR after D4**. The epic branch is
> **local-only until the owner authorizes a push**.

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
**Sequencing rule:** strictly sequential, one branch at a time. The D3 dev half works inside
the structure D2 built and next to the user tier this branch wrote.
**Blocked until this stream tags:** Epic E (`chore/release-v1.1.0`). Epic D lands as one PR,
not a tag.

- ~~Epic C~~ ✓: merged to `main` as PR #148 (`f3dd472`).
- ~~`feat/docs-ia-design` (D1)~~ ✓: audits, research and the design doc.
- ~~`feat/docs-split` (D2)~~ ✓: the mechanical split and the publication registry.
- ~~**`feat/user-docs` (D3, user half)**~~ ✓ ← this branch: the user tier's content.
- **`feat/dev-docs` (D3, dev half)** ← next.
- `feat/docs-assets-enforcement` (D4) ← don't start on the dev half: screenshots, diagrams,
  bubble "Learn more" links and the §5 lints are D4's.

---

## What just landed on `epic/d-docs-ia`

Commits on `feat/user-docs` (fast-forwarded into `epic/d-docs-ia` as this session's final act,
with the owner's confirmation):

- **`52711af`: dossier + ledger.**
  - The C-10 dossier `docs/dev/blast-radius/user-docs.md`, written before any edit. It carries
    the owner's kickoff decisions and 29 consumer rows, plus Deferred.
  - The consumed-event ledger row (session `d3d2e857`).
- **`ef28837`: items 130–133 filed.**
  - 130: profile edits probably never reach `Candidate` (code-read, not observed).
  - 131: retired application unrecoverable.
  - 132: follow-up regenerate after freeze (UNVERIFIED).
  - 133: no profile delete (owner).
- **`d2affdf`: walkthrough and install.**
  - The walkthrough's eight "Under the hood" blocks were cut. The missing facts went to
    `architecture.md`.
  - Drift fixed: TW-F2, the Tailor tab, surgical Refine, and resume via Pipeline.
  - The install maintainer runbook moved to `docs/dev/releasing.md`.
  - Cost has one measured home: `install.md` "What an application costs" ($0.25 p50, n=13).
  - The circular anchor and the SECURITY budget-guard pointer (TW-F1) are fixed.
- **`b4c8dc7`: the new rungs.**
  - `docs/user/iterating.md` (U3) and `docs/user/coaching.md` (U4a).
  - `templates.md` split: the user half stays, and `docs/dev/bundled-templates.md` holds the
    rest.
  - The item-20 correction: Step 5 opens only after Compose is saved (`static/app.js:7051-7081`).
  - All five docs registered; `wiki_relevance` entries added.
- **`596230f`: O-1 in the UI.**
  - `Sartor` in sentences in `index.html`, `app.js` `_HELP_REGISTRY`, the two assistant strings
    in `dashboard.html`, and `AVATAR_SYSTEM_PROMPT` (`AVATAR_PROMPT_VERSION` →
    `2026-09-29.1`; `PROMPT_VERSION` untouched).
  - New `panelPipeline` help entry; `panelOutput` explains Refine; the Pipeline hint is no
    longer "Read-only".
- **`ca17897`: close-out.**
  - CHANGELOG.
  - Scoped wiki pass: `prompt-version-discipline` updated; auditor 13/0/0.
- **`a47ea16`: checkpoint-advancing wiki pass** (owner-authorized, cap raised to 11).
  - The first full gate at close-out **failed** on `tests/test_wiki_freshness_gate.py`: 78
    wiki-relevant files had changed since `f42b2ea`, against a block threshold of 75.
  - 11 pages corrected; `.last_ingest_sha` advanced to `ca17897`; 84 SUPPORTED / 0 UNSUPPORTED.
    Full detail is in `docs/wiki/log.md`.
  - Coverage gaps handed to D4 (not false claims): keyless-client refusal, education
    degree+field rendering, and the docs IA split.

**Gate on the final tree** (`a47ea16`, the log read directly, not the task status):
- "gate: 1.65 GB free (floor 1.00 GB) -- proceeding.";
- ruff "All checks passed!"; format "373 files already formatted";
- mypy "Success: no issues found in 389 source files";
- pytest not-ux "2885 passed, 6 skipped"; pytest ux "161 passed, 2891 deselected, 2 xpassed";
- "work_items: OK (133 files)"; "gate: all steps passed." exit 0; 0 RERUN.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

Authoritative home: `docs/dev/work/BOARD.md` (regenerated this session). **Header: "Open 31 /
10 ceiling -- OVER".** The reduction sprint is overdue and is flagged again at this close. It
is the owner's call when to run it (after Epic D, or sooner).

`## Open`:
- **50**: C-7/C-10 hooks don't travel to non-Claude-Code agents.
- **98**: Wiki freshness measures checkpoint-staleness, not page-staleness. **It blocked this
  branch's first close-out gate** (78 ≥ 75). It was cleared by a checkpoint-advancing pass
  (`a47ea16`), and the mechanism is unchanged.
- **99**: install.md documents two never-published distribution paths. The doc half has been
  done since 2026-09-03. It stays open until publication (item 3). Re-verified 2026-09-29:
  nothing is published.
- **105**: Corpus import produces no education entries.
- **106**: Compose bullet-text edits don't reach an already-frozen application.
- **107**: First run offers no account-naming step.
- **111**: `check-plan-approved.sh` takes ~2 s per edit and 8–21 s per retire on Windows/MSYS.
- **112**: Dashboard Since filter raises TypeError (naive vs offset-aware dates).
- **115**: UX-8 test needs a `getComputedStyle` assertion.
- **116**: "Run this fixture" help bubble never verified to open in a browser.
- **117**: No server-side single-flight lock for paid diagnostics runs.
- **118**: Redaction misses quoted-key header forms and Basic auth.
- **119**: Run lock has no owner; three `acquire()` sites ignore its result.
- **120**: A declined run leaves its button pulsing.
- **121**: `run_detail` reads the whole log per modal open; a non-object line gives a 500.
- **122**: Weak C3 test assertions.
- **123**: `verify-binary-on-path` blocks shell brace groups.
- **124**: Recurrence: agents invoke bare `ruff` and get hook-blocked.
- **125** *(owner)*: merged epics 37/38 still read `blocked`.
- **126**: A stale local docs-site projection reads as authoritative (candidate mechanism in D4).
- **128** *(owner)*: stray `python3.13` processes from earlier sessions.
- **129** *(owner)*: personal portfolio/interviewer framing in two frozen records.
- **130** *(new)*: profile edits (Notes, identity) likely never reach `Candidate` after
  creation. Code-read only. **It holds the Notes documentation** that RELEASE_ARC's D3 bullet
  asks for.
- **131** *(new)*: a retired application can't be found again (the dialog cites a missing
  "Show retired" toggle). `docs/user/iterating.md` states the caveat.
- **132** *(new, UNVERIFIED)*: "Submit answers and regenerate" may not change a frozen résumé.
- **133** *(new, owner)*: no way to delete a candidate profile.

Epic 39's own child **127** (CONTRIBUTING / `agents/git-flow.md` `--no-ff`, "latent" CI, the
four-step gate description) is **the dev half's own work**. Plus `## Blocked` (4), `## Deferred`
(9, including **113**, 18 console-UX findings awaiting owner triage), `## Watching` (45) and
`## Epics` (6; **39** open). Full detail: `BOARD.md`.

Declared, not filed (from this branch's dossier `## Deferred`, carried here so it isn't lost):
- **Stale code comment** `db/build_context.py:92` ("two chokepoints that close the whole
  generation blast radius") predates item 75's third filter. It was noted by the wiki
  auditor and not fixed here (product code, not docs). Fold it into any branch that touches
  that file.
- **Settings has no help bubble.** `_initHelp` attaches only to `.cb-panel`
  (`static/app.js:2371`), and Settings is a drawer. It needs new mechanism code, which is
  product scope, not docs. It's a gap against RELEASE_ARC's "bubbles" line; the owner decides
  whether it's wanted.

---

## Recurrences observed this session → guardrail authored

1. **Docs asserting a state the code no longer has.** Recognized as a recurrence of TW-F2 / the
   D1 audits' drift class. `walkthrough.md` was wrong in six places. `architecture.md` and the
   Step-5 help copy still promised the pre-item-20 "Generate without Compose" AI path.
   `templates.md` and `build_bundled_templates.py` listed Helvetica. **No fail-closed mechanism
   authored on this branch.** The designed one is D4's enumeration-drift lint (docs-ia-design
   §5.5), and label/behavior claims in prose aren't mechanically checkable in general. Surfaced
   to the owner at close; memory `reference-user-docs-verify-against-live-labels` records the
   method.
2. **A subagent's report carried a stale fact** (C-12 class): the product-facts explorer
   didn't know item 20 had gated Step 5. It was caught by reading `_wizardReachable` directly
   before commit. **No mechanism authored.** C-12's existing controls cover citations, not
   subagent completeness. Surfaced to the owner.
3. **The freshness gate blocked a close-out because scoped passes never advance the
   checkpoint.** Recognized as item 98's documented mechanism, now observed as a hard block
   rather than a drift figure. **No mechanism authored.** Item 98 already names the build (a
   coverage ledger plus a generated figure). The workaround used here was an owner-authorized
   checkpoint-advancing pass. Surfaced to the owner at the block.
4. **The handoff narrowed ratified scope.** The D2 handoff's list omitted two items in
   RELEASE_ARC's D3 bullet (Notes, bubbles). Same class as memory
   `feedback-scope-is-quoted-never-derived`. Caught by reading RELEASE_ARC directly; the owner
   decided at kickoff. **No mechanism authored**: `verify_doc_template.py` checks structure,
   not scope fidelity. Surfaced to the owner. This handoff quotes RELEASE_ARC's dev-path line
   verbatim below to avoid repeating it.

---

## What this branch should build

D3, dev half, per `docs/dev/RELEASE_ARC.md` §"Epic D" D3 bullet, quoted verbatim: *"Dev path:
builds on the user path; per-tab diagnostics documentation with Mermaid flow diagrams + tables
matching C3's on-screen copy; module-map refresh; the new governance hooks/skills documented."*
Plus the dev-side rows of `docs/dev/docs-ia-design.md` §2.1 and §4 (dev ladder), and O-2:

1. **`docs/dev/README.md`**: the dev ladder D0–D5 and the routed index (reference · runbooks ·
   designs · templates · records), design §4. Link the two new dev docs from this branch,
   `releasing.md` and `bundled-templates.md`.
2. **O-2, split `AGENTS.md`** (owner decision 2026-09-28): the code rules stay in AGENTS.md
   (non-Claude agents read it raw, so it must not become an import shell). The owner's session
   protocol (handoffs, ledger, plan markers, pointer checks) moves to an owner-lane doc that
   AGENTS.md links. This is a C-10 surface: hooks, templates and tests quote AGENTS.md
   sections, so enumerate first.
3. **Item 127:** `CONTRIBUTING.md:57` and `agents/git-flow.md:19` (local `git merge --no-ff`
   vs AGENTS step 4's PR flow), CONTRIBUTING's "latent" CI, and the gate described as four
   steps while `scripts/gate.py` runs six. Cite `scripts/gate.py` rather than restating it
   (design §4 D1).
4. **Diagnostics documentation per tab:** Mermaid flow diagrams and tables matching C3's
   on-screen copy (`dashboard/templates/dashboard.html` `_DASH_HELP`). The dashboard's own
   in-sentence `sartor` (O-1, ~69 hits) is deferred here from this branch.
5. **Module-map refresh** in `docs/dev/architecture.md`. This includes the item-20 stale
   labels this branch left in its diagrams (`:98-100` Mermaid comment, `:208` sequence `else`,
   `:816` flowchart edge — "known live gap" is no longer true; `static/app.js:7051-7081`).
6. **Governance hooks and skills documented** (the ones added since the last catalog pass;
   derive the list from `.claude/settings.json` + `hooks/` + `skills/`, never from memory).
7. Design §2.1 dev-side rows:
   - `vision.md` "C-0…C-6" → cite the charter's range (TW-F3);
   - the `README.md:235-276` dev sections shrink to links;
   - `system-model.md` tier conflict with its wiki twin;
   - `PRODUCT_SHAPE.md` historical sections → `archive/`;
   - `documentation-architecture.md` body rewrite;
   - `ACCESSIBILITY.md` audience token.

Read `docs/dev/doc-style-guide.md` first. Use `scripts/docs_move.py` only for whole-file
moves; section moves are by hand (it has no section support). Run `check_doc_links.py`
**after `git add`**.

Scope is bounded to Epic D, D3 (dev half) in `docs/dev/RELEASE_ARC.md` and the D1 design's §2.1
and §4. Do not expand beyond what is listed there. Screenshots, diagram regeneration, bubble
"Learn more" links and the §5 lints are D4's.

---

## First move

Create branch `feat/dev-docs` off `epic/d-docs-ia`, write a plan
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
