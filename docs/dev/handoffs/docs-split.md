<!-- provenance: schema=1 session=dde107cd-c785-4c2e-a194-c5589bf31851 branch=feat/docs-split commit=406858d actor=amodal1 agent=anthropic/claude-opus-5-5 generated_at=2026-09-28 -->

# Agent handoff — Epic D sprint D2 close (`feat/docs-split`)

**Branch to create:** `feat/user-docs` (branch off `epic/d-docs-ia`)
**Base branch:** `epic/d-docs-ia`

> **Model for the next session: Opus** (RELEASE_ARC Final March prescription: Opus for D1/D3,
> Sonnet for D2/D4).
>
> **Epic cadence (owner decision, 2026-09-27):** Epic D runs on the integration branch
> `epic/d-docs-ia`. Each sprint branch merges into it as that session's final act, and the whole
> epic lands as **one PR after D4**. The epic branch is **local-only until the owner authorizes
> a push**.

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
**Sequencing rule:** strictly sequential, one branch at a time. D3 works inside the structure
D2 built.
**Blocked until this stream tags:** Epic E (`chore/release-v1.1.0`). Epic D lands as one PR,
not a tag.

- ~~Epic C~~ ✓: merged to `main` as PR #148 (`f3dd472`).
- ~~`feat/docs-ia-design` (D1)~~ ✓: audits, research and the design doc.
- ~~**`feat/docs-split` (D2)**~~ ✓ ← this branch: the mechanical split and the publication
  registry.
- **`feat/user-docs` (D3, user half)** ← next. Then `feat/dev-docs` (D3, dev half), as its own
  session.
- `feat/docs-assets-enforcement` (D4) ← don't start on D3.

---

## What just landed on `epic/d-docs-ia`

Commits on `feat/docs-split` (merged into `epic/d-docs-ia` as this session's final act, with the
owner's confirmation):
- `bb6401b`: consumed the D1 handoff (ledger row, session `dde107cd`). Owner decisions O-1…O-5,
  O-3a and slugs are recorded in `docs/dev/docs-ia-design.md` §"Open decisions for the owner".
  C-10 dossier: `docs/dev/blast-radius/docs-split.md`.
- `1d0f92b`: **publication registry.** `scripts/doc_registry.py` is now the single definition
  of published docs (with tier and nav order) and of the record-path classes. The projector
  publishes only registry entries, and `meta.json` gets "Using Sartor" / "Building on Sartor"
  separators. `check_doc_frontmatter.py` requires a leading `` `user` ``/`` `dev` `` Audience
  token that matches the registry tier.
- `ce069e5`: `scripts/docs_move.py` (scripted move plus live-link rewrite) and the
  `docs/dev/moved-paths.json` lookup for record-origin links in `check_doc_links.py`.
- `43ca17d`: **the move.**
  - `docs/user/`: `install.md`, `walkthrough.md`, `walkthrough-example.md`, `templates.md`,
    plus a `README.md` stub
  - `docs/dev/`: `architecture.md`, `system-model.md`, `PRODUCT_SHAPE.md`,
    `screenshot-capture.md`, plus a `README.md` stub
  - 16 designs moved to `docs/dev/archive/`

  468 live-doc rewrites.
- `406858d`: close-out. Items 125–129 filed, a scoped wiki pass on `code-module-map`, and the
  CHANGELOG entry.

Gate: `python -m scripts.gate` on the close-out tree. The result is recorded in the handoff
commit's message.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

Authoritative home: `docs/dev/work/BOARD.md` (regenerated this session). **Header: "Open 27 /
10 ceiling -- OVER".** The reduction sprint is overdue and was flagged again at this close. It
is the owner's call when to run it (after Epic D, or sooner).

`## Open`:
- **50**: C-7/C-10 hooks don't travel to non-Claude-Code agents.
- **98**: Wiki freshness measures checkpoint-staleness, not page-staleness.
- **99**: install.md documents two never-published distribution paths. **D3 touches this doc**
  (now `docs/user/install.md`).
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
- **125** *(new, owner)*: merged epics 37/38 still read `blocked`; closing needs the owner to
  say what counts as `verified_by`.
- **126** *(new)*: a stale local docs-site projection reads as authoritative. Candidate
  mechanism: the projector stamps the source commit (D4).
- **127** *(new, epic 39: **D3's own work**)*: `CONTRIBUTING.md:57` and
  `agents/git-flow.md:19` instruct a local `git merge --no-ff`; CONTRIBUTING calls CI "latent";
  the gate is described as four steps but `scripts/gate.py:72-82` runs six.
- **128** *(new, owner)*: stray `python3.13` processes from earlier sessions.
- **129** *(new, owner)*: personal portfolio/interviewer framing survives in two frozen records
  (`docs/dev/archive/app-blueprints-design.md`, `docs/dev/perf/R1_PHASE2_RESULTS.md`).

Plus `## Blocked` (4), `## Deferred` (9, including **113**: 18 console-UX findings awaiting
owner triage), `## Watching` (45) and `## Epics` (6; **39** open). Full detail: `BOARD.md`.

---

## Recurrences observed this session → guardrail authored

1. **A widened scope surfaced latent defects the narrower scope had hidden.** Registering more
   docs widened `check_doc_links`'s cite check, which reuses `PUBLISHED_DOC_FILES` by design,
   and three stale `path:line` cites appeared at once. **Mechanism already exists and failed
   closed:** the link gate blocked, and the cites were fixed on this branch. D3 adds docs to
   the registry, so expect the same.
2. **An untracked file escaped a gate this session.** `check_doc_links.py` enumerates with
   `git ls-files`, so the new dossier passed the pre-commit check while it was untracked, then
   failed once tracked. It was fixed immediately. **No mechanism authored:** the gate is
   correct for committed state, and the pytest run catches it before merge. Noted so the next
   agent runs the link check *after* `git add`.

---

## What this branch should build

D3, user half: the content of the user tier, per `docs/dev/RELEASE_ARC.md` §"Epic D" (D3
bullet) and `docs/dev/docs-ia-design.md` §4 (user ladder):

1. **Rung U3** (`docs/user/iterating.md`, new): second application, refining, Prior
   Applications, Candidate Memory. Then register it in `scripts/doc_registry.py`
   (`` `user` `` token).
2. **Rung U4a** (`docs/user/coaching.md`, new): using Sartor for several candidates.
3. **`docs/user/templates.md`:** split into a user half and a maintainer half (the maintainer
   half goes to `docs/dev/`). Add the P/A/A header and register it.
4. **`docs/user/install.md`:** move the maintainer runbook to `docs/dev/`, and fix the
   circular cost anchor (design §4 U1). Item 99 bears on the two unpublished distribution
   paths.
5. **`docs/user/walkthrough.md`:** move the "Under the hood" blocks to dev docs, and fix TW-F2
   (Generate calls Sonnet only when Compose wasn't frozen).
6. **O-1 (owner):** `Sartor` in sentences, including UI copy. The shipped assistant string
   (`templates/index.html`, "Ask how sartor. works") changes here; check `PROMPT_VERSION`
   rules if a prompt string is touched.
7. Fill `docs/user/README.md` rungs 4 and 5 once those docs exist.

RELEASE_ARC's user-path rule applies: assume no technical knowledge, and every user choice
answers what it does, why you'd use it, how, and what to expect. Read
`docs/dev/doc-style-guide.md` first. Use `scripts/docs_move.py` (add to `MOVES`) for any file
move. Never hand-edit link rewrites.

Scope is bounded to Epic D, D3 (user half) in `docs/dev/RELEASE_ARC.md` and the D1 design's
§4. Do not expand beyond what is listed there. The dev half (`feat/dev-docs`, including item
127 and the AGENTS.md split, O-2) is the next session's.

---

## First move

Create branch `feat/user-docs` off `epic/d-docs-ia`, write a plan
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
