<!-- provenance: schema=1 session=09c6abaa-ef5e-4dcb-bd9f-0dfafbe4d430 branch=feat/install-onboarding-preflight commit=89008b0 actor=amodal1 agent=anthropic/claude-opus-5 generated_at=2026-09-04 -->

# Agent handoff: `feat/install-onboarding-preflight`

**Branch to create:** none directed by this session. The open backlog is at
`docs/dev/work/BOARD.md`; see "What this branch should build" for this
session's recommendation.
**Base branch:** `main` (once this branch has merged)

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

**Stream:** v1.1.0 final march. Epic A and Epic B are both merged; C/D/E are
factory cards rather than branch sessions
(`docs/dev/work/items/0097-external-orchestration-hypothesis.md`).
**Sequencing rule:** strictly sequential — one branch at a time.

This branch is **not** part of the arc sequence. It is a backlog-reduction
branch: the six install/onboarding findings (items 99–104) filed from one live
non-maintainer install, worked as a single cluster at the owner's direction.

- ~~`epic/b-render-ats`~~ ✓ — rendering + ATS correctness, merged
- ~~`docs/container-persistence-guidance`~~ ✓ — items 99–106 filed, merged as PR #131
- ~~`docs/first-run-account-naming-finding`~~ ✓ — items 107–108 filed, merged as PR #133
- ~~`feat/gate-memory-preflight`~~ ✓ — item 108, the gate memory floor, merged as PR #134
- **`feat/install-onboarding-preflight`** ← this branch (items 99–104)
- next ← the user's call; see "What this branch should build"

**Do not start** items 105, 106 or 107 on a whim — each is a product defect
whose write-up is a *candidate mechanism*, not a diagnosis. Each needs its own
instrument first (C-7), and each deserves its own branch.

---

## What just landed on `main`

Commit `3956340` (PR #134) — item 108's fail-closed memory preflight for
`scripts/gate.py`, merged before this branch started. `scripts/gate.py` reads
free physical memory before any of the six gate steps and refuses below a
measured 1.0 GB floor. Regression suite `tests/test_gate_memory_preflight.py`.

**Gate status on that merge — CI green**, per that branch's own `ci_wait`
record. This session did not re-verify it independently; this branch's own full
local gate run (below) is the stronger, more recent signal on the code it
builds on.

---

## What this branch built

**Items 100, 101, 102, 103, 104 — closed. Item 99 — documentation half done,
deliberately kept OPEN.** Open count 16 → 11 (ceiling is 10, so **still over by
one** — say that plainly rather than reporting a clean reduction).

Four of the six were symptoms of one absence: nothing could answer *"what can
this machine actually do?"*, so every capability gap surfaced as a runtime
failure after the user had already committed to a path.

- **New `preflight.py`** — tri-state capability probes (`True` / `False` /
  `None` for "could not determine"), stdlib-only, no new dependency, no browser
  launch, no network. Unknown is resolved at the *call site*, not in the probe.
- **`sartor --doctor`** (item 100) — prints the whole capability set before
  anything downloads; exits non-zero only when Python itself is below the floor.
- **`sartor --setup` key prompt** (item 104) — `getpass`, then
  `os.open(..., 0o600)` so the file is never briefly world-readable. Never
  prompts when a key resolves, never on a non-interactive stdin, never echoes.
- **PDF gated on capability** (item 103) — both PDF buttons render disabled with
  a visible reason when Chromium is absent.
- **Per-step `--setup` summary** (item 102) — names only what actually failed.
- **`docs/install.md` + `README.md`** (items 99/100/101) — version floors,
  pre-release markers on the two unpublished distribution paths, and a container
  section that no longer defaults to data loss.

**Two refutations, from instrumenting item 103 before fixing it** — the item
asked for that explicitly and it paid for itself twice
(`docs/dev/diagnosis/install-onboarding-preflight.md`, O-1…O-7, two arms):

1. **`render_pdf` does NOT raise `RuntimeError`.** `playwright.sync_api.Error`'s
   MRO is `(Error, Exception, BaseException, object)`. Both `pdf_render.py`
   docstrings claimed RuntimeError, and item 103 had inherited the claim *from
   one of those docstrings*. Corrected and pinned by a test.
2. **`chromium.executable_path` is the wrong artifact to stat.**
   `launch(headless=True)` — `render_pdf`'s effective default — needs
   `chromium_headless_shell-<rev>`. The probe design this branch's own plan had
   already written down would have called a partial install "available". A
   deliberately-wider-than-the-hypothesis instrument is the only reason that
   surfaced.
3. **Cost, measured:** the Playwright API path costs 2912 ms (it spawns a Node
   driver); `browsers.json` + two stats costs 8.4 ms and checks strictly more.

**Gate status: NOT YET RUN AT TIME OF WRITING.** The full
`python -m scripts.gate` runs as the last step before the PR. Targeted runs are
green: 59 preflight tests, 26 setup/key tests, 9 PDF-UI tests, 4 pdf_render
exception tests, plus the doc-link and work-item gates. **If you are reading
this, check the PR's CI result rather than trusting this paragraph** — it was
written before the gate finished.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

The one authoritative home is `docs/dev/work/BOARD.md` (charter W-1.4). Full
still-open subset — **11 open against a ceiling of 10, still over**:

- **50** — C-7 and C-10 are enforced by Claude Code hooks only; the clauses do not travel to other agents (`user`)
- **94** — The item-87 interrogative-witness pause kills N=1 pipeline runs (`user`)
- **96** — Sprint briefs prescribe an implementer model in prose while their First-move block omits the arg (`agent`)
- **98** — Wiki freshness measures checkpoint-staleness, not page-staleness (`agent`)
- **99** — install.md documents two distribution paths that have never been published (`agent`) [depends on 3] — **docs half landed this branch; kept open by owner decision until a tag ships and both publish workflows are green**
- **105** — Corpus import produced bullets and skills but no education entries (`agent`)
- **106** — Compose bullet-text edits don't reach an already-frozen application's preview, generate, or download (`agent`)
- **107** — First run offers no account-naming step; the account is named after the email address (`agent`)

Plus three open **epics** (19, 36, and the third the board renders) — `BOARD.md`
is the authoritative render, not this list.

**New this session, filed durably:**

- **`preflight.py` is deterministic but is NOT on `AGENTS.md`'s enumerated C-6
  boundary list** (which names eight modules). The wiki now says so explicitly
  in two places rather than letting a table heading imply membership. **Whether
  the C-6 list should grow to include it is an owner-gated governance question
  this session did not answer** — flagged, not decided.
- **Two container claims remain unverified** and are marked as such in
  `docs/install.md` rather than asserted or dropped: rootless-Podman bind-mount
  writability for uid 10001, and whether a fresh `/app/db` mount shadows the
  baked recall index (the latter was previously stated as *fact* at
  install.md:69 and has been removed as unverified in either direction). Both
  need a container run on supported hardware, which item 99 blocks.
- **`.last_ingest_sha` is 213 files stale** (`f42b2ea`). This branch's wiki pass
  was branch-scoped and deliberately did **not** advance it — see item 98.

**Not repo work, unchanged:** the borrowed macOS machine's API key rotation is
still owed on handback (memory `project-dx-install-test-macos12`).

---

## Recurrences observed this session → guardrail authored

**1. Heredoc-delivered content is mangled — 4th instance, new character class.**
Recognized as a recurrence, not a first sighting: memory
`reference-heredoc-escaping-and-first-match-anchors` already documents three
instances (`\n` collapsing, first-match anchors). This session hit it with a
**literal backslash** — a `replace()` whose target contained a shell
line-continuation `\` matched 0 times against a file that plainly contained it.

- **Mechanism authored: the memory was widened**, not just re-noted — a new
  "Trap 1b" section generalizes the rule from "escape sequences break" to **any
  backslash in heredoc-delivered content is unreliable**, and names the two
  workarounds that actually worked here (write the script to a file with `Write`
  and run it; or splice by index on backslash-free anchors).
- **No repo-level fail-closed gate is possible, and that is stated rather than
  implied (C-11):** this is Bash-tool/harness command parsing, not project code.
  There is no project surface to gate. Surfaced to the user in-session.

**2. A test that patched the wrong target passed slowly for the wrong reason.**
Recognized as a member of the known "the fake is not being used" class.
`tests/test_pdf_render_missing_chromium.py`'s first draft patched
`pdf_render.sync_playwright`, but `render_pdf` does `from playwright.sync_api
import sync_playwright` **inside the function**, so the name is rebound per call
and the patch was a no-op — the test **launched a real browser and rendered an
actual PDF**, taking 38 s before failing on `DID NOT RAISE`.

- **Mechanism authored:** new memory
  `reference-function-local-import-defeats-module-patch`, plus an in-file
  comment at the patch site naming the trap and why the source module is the
  correct target — so the next person editing that test cannot silently revert
  it. **The durable tell is recorded too:** unexplained multi-second runtime in
  a test that should be pure is evidence the fake is not being used.
- Honest limit: this is a memory + an in-file comment, **not a CI gate.** No
  deterministic check can tell a correct patch target from an incorrect one.

**3. A doc claim contradicted the code it described.** `pdf_render.py`'s
docstrings said `RuntimeError`; the code raises `playwright.sync_api.Error`.
Recognized as the compliance-witness class (a docstring contradicting its code).

- **Mechanism authored:** `tests/test_pdf_render_missing_chromium.py` asserts
  the documented class is the raised class, with a failure message naming both
  the docstring and the diagnosis to revisit. **This one does fail closed** — if
  Playwright ever makes `Error` a `RuntimeError` subclass, or the docstring
  drifts back, the suite goes red.

---

## What this branch should build

Nothing further — this branch closes with items 100–104 built and closed, and
item 99's documentation half landed.

Recommendations for the next session, in priority order:

1. **The backlog is still over ceiling: 11 open vs 10.** One more reduction
   closes it. The cheapest honest candidate is **item 96** (sprint briefs
   prescribe a model in prose while the copy-paste block omits the arg) — small,
   self-contained, and it removes a live footgun.
2. **Items 105, 106, 107 each need an instrument before a fix.** Item 106 has the
   most groundwork (memory `reference-compose-bullet-edit-not-refrozen` names a
   *candidate* mechanism, explicitly not a diagnosis). Whichever is picked, the
   first commit on that branch is the instrument, not the fix.
3. **Raise the C-6 question with the owner:** should `preflight.py` join
   `AGENTS.md`'s enumerated deterministic-boundary list? This session declined to
   decide it unilaterally — it is a governance edit.
4. **Item 98 / the wiki checkpoint** is now 213 files stale and every scoped
   close-out makes it worse. It is the documented ratchet defect and it needs the
   coverage-ledger redesign, not another scoped pass.

Scope is bounded to what is filed in `docs/dev/work/items/`. Do not expand
beyond it, and do not start an item without the user naming it.

---

## First move

Create the branch the user names, off `main`, write a plan at
`~/.claude/plans/<slug>.md`, and show it to the user before touching any code.
**Do not code first.**

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
