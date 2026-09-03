<!-- provenance: schema=1 session=9f7ad6ac-dee6-431c-8d5a-5326eccab176 branch=docs/first-run-account-naming-finding commit=6979ec8 actor=amodal1 agent=anthropic/claude-opus-5 generated_at=2026-09-02 -->

# Agent handoff: `docs/first-run-account-naming-finding`

**Branch to create:** none directed by this session. The open backlog is at
`docs/dev/work/BOARD.md`; see "What this branch should build" for the one thing
this session recommends raising first.
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

**Stream:** v1.1.0 final march. Epic A and Epic B are both merged (Epic B landed
as PR #128, `86dee5c`); C/D/E are factory cards rather than branch sessions
(`docs/dev/work/items/0097-external-orchestration-hypothesis.md`).
**Sequencing rule:** strictly sequential — one branch at a time.

This branch is **not** part of the arc sequence. It is a work-item filing branch
opened to record findings from a live install session; it ships no code and
touches no product surface.

- ~~`epic/b-render-ats`~~ ✓ — rendering + ATS correctness, merged
- ~~`docs/container-persistence-guidance`~~ ✓ — items 99–106, merged as PR #131
- **`docs/first-run-account-naming-finding`** ← this branch (item 107 only)
- next ← the user's call; this session recommends a backlog reduction sprint

**Do not start** any of items 99–107 on this branch. Each is a filed, unstarted
finding; several are docs-only and several need instrumentation first. They were
filed to be worked deliberately, not swept.

---

## What just landed on `main`

Commit `318156d` (PR #131), merged by a **concurrent session** working in the
same clone. It carries two sessions' work: this session's `4c27edf` (items
99–105, install-DX findings from a live macOS walkthrough) and that session's
own item 106 plus its close-out. Docs only — no code, no routes, no schema.

This branch adds `6979ec8`: item 107 and the regenerated `BOARD.md`. Also docs
only.

Gate: `ruff check .` + `ruff format --check .` + `mypy .` + `pytest` +
`work_items check` (107 files) — run on this branch before the handoff commit.

**Context for the findings.** A non-maintainer attempted a first install on a
macOS 12.7.4 (Monterey) machine. **Neither documented install path worked.** The
container path is blocked by an undocumented macOS 13+ floor, and — found while
diagnosing that — **neither distribution artifact has ever been published**:
`git ls-remote --tags origin` returns nothing, both `release.yml` and
`docker.yml` trigger on a tag push that has never happened, and
`gh release list` is empty. The ten local tags `v0.2.0`–`v1.0.9` exist only in
this clone. A source clone plus `pip install --user -e .` was the only path that
worked. Item 3 has been updated with this, and its "blocked on the repo rename"
framing is now stale — the rename is done.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

The one authoritative home is `docs/dev/work/BOARD.md` (charter W-1.4; the
work-item schema replaced `RELEASE_CHECKLIST.md`'s live Carry-forward ledger per
`docs/dev/work/SCHEMA.md` §7). Full still-open subset — 16 open against a ceiling
of 10, **over, and the board says so**:

- **19** — (epic) UX-suite flakiness solution sprint — mode-C residual + newly observed instances
- **36** — (epic) Final March epic A — main-app function + UX
- **50** — C-7 and C-10 are enforced by Claude Code hooks only; the clauses do not travel to other agents (`user`)
- **94** — The item-87 interrogative-witness pause kills N=1 pipeline runs (`user`)
- **96** — Sprint briefs prescribe an implementer model in prose while their First-move block omits the arg (`agent`)
- **98** — Wiki freshness measures checkpoint-staleness, not page-staleness (`agent`)
- **99** — install.md documents two distribution paths that have never been published (`agent`) [depends on 3]
- **100** — Install docs state no OS or runtime version floors and offer no preflight check (`agent`)
- **101** — Container quickstart defaults to a throwaway container and hides a bind-mount trap (`agent`)
- **102** — `sartor --setup`'s failure summary names both features whenever either step fails (`agent`)
- **103** — PDF output is offered in the UI even when the Chromium binary is absent (`agent`)
- **104** — Every documented API-key entry method writes the key into shell history (`agent`)
- **105** — Corpus import produced bullets and skills but no education entries (`agent`)
- **106** — Compose bullet-text edits don't reach an already-frozen application's preview, generate, or download (`agent`)
- **107** — First run offers no account-naming step; the account is named after the email address (`agent`)

(One open item is an epic child and renders under `## Epics` rather than
`## Open`; `BOARD.md` is the authoritative render, not this list.)

**At 16/10 this is well past the ~8–10 reduction-sprint threshold.** Nine of the
sixteen were filed today. Flagged to the user; not acted on.

**Not carried into the ledger, because they are not repo work:**

- The Anthropic API key used for the install test is on a machine the owner does
  not control, at `~/Desktop/sartor/.api_key` (mode 600). Shell history on that
  box was scrubbed and verified clean (`grep -c` returned 0). **Rotation is
  owed** when the machine is handed back. Held in the memory
  `project-dx-install-test-macos12`.
- The DX test was still in progress when this session closed — the app was
  running on that Mac and the owner was working through import and compose.
  Expect further findings.

---

## Recurrences observed this session → guardrail authored

**1. Two agent sessions in one working tree.** Recognized as a recurrence, not a
first sighting: the memory `feedback-concurrent-agents-worktree` already records
a 2026-06-12 instance with three collision modes. This session hit a **fourth,
new** mode — sequential ID allocation. I read the highest work-item id (`0098`),
filed `0099`–`0105`; the concurrent session filed `0106`; my next file claimed
`0106` as well.

- **Mechanism that held:** `python -m scripts.work_items check` fails closed on a
  duplicate id and caught it ("id 106 used by multiple files"). That gate already
  existed and did its job. Nothing new was authored because nothing new was
  needed for this half.
- **Mechanism that does NOT exist, and I did not author one:** `board --write`
  renders from the **working tree**, so regenerating picks up another session's
  *uncommitted* item file. Committing that board without their file is green
  locally and broken in CI — the board would reference an item that does not
  exist at HEAD. Nothing detects this. I avoided it by hand, by parking my file
  outside the repo until the other session landed. **That is discipline, not a
  mechanism, and C-11 is explicit that discipline is not a compliant answer on
  its own.** Declaring the gap rather than implying coverage. Surfaced to the
  user in session, who directed the wait-and-land sequence.

**2. Treating a question as a work order.** Recognized as a recurrence — a
documented class with its own dossier (`feedback-interrogative-is-not-a-work-order`,
recorded in `CLAUDE.local.md` as of 2026-08-12) and its own live hooks from item
87. The user asked for step-by-step install instructions "here, in this
terminal"; I began authoring a published artifact instead and had to be stopped:
*"i did not ask for instructions as a deliverable... stop trying to do anything
else other than supporting this single install."*

- **The item-87 witness fired and did not prevent it.** The pause is one-shot per
  prompt and self-clears on re-run; the prompt genuinely was a directive (it
  asked for instructions), so re-running was correct. What was wrong was the
  *form* of the deliverable, which no heuristic over the prompt text can classify.
- **No mechanism authored.** I do not believe one is available here: the failure
  is output-format selection, not prompt classification, and C-0 forbids claiming
  a deterministic gate over a judgment call. Saying that plainly is what C-11
  requires when no mechanism is possible. The existing witness remains the only
  control, and it is a witness, not a gate.

**3. Asserting from stale memory instead of verifying.** Twice I stated things a
16-day-old memory said that the repo contradicted: that the repo rename was still
blocking publication (it is done), and that `SARTOR_HOME` was planned rather than
shipped (it is implemented — `config._default_base_dir()`). Both were corrected
in-session by reading the repo, and both corrections are now durable — in item
3's update and in item 101 respectively. Recognized as a member of the class
`feedback-verify-against-durable-docs` already names. **No new mechanism
authored;** the existing rule is prose and stayed prose. Declared, not implied.

---

## What this branch should build

Nothing further. This branch closes with item 107 filed and the board
regenerated.

The one thing this session recommends the next agent raise with the user
**before** picking up any individual item:

1. **A backlog reduction pass.** 16 open against a ceiling of 10, nine of them
   filed in a single day. Items 99–104 are one coherent cluster — the
   install/onboarding documentation and preflight story — and would be better
   worked as a single branch than as six. Items 105, 106 and 107 are product
   defects found in the same session, and each needs instrumentation before a
   fix: do not treat any of their "candidate mechanism" paragraphs as a
   diagnosis. Every one is labelled a hypothesis for a reason (C-7).

Scope is bounded to what is filed in `docs/dev/work/items/`. Do not expand beyond
it, and do not start an item without the user naming it.

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
