<!-- provenance: schema=1 session=c8caf603-88cf-46b6-b2aa-77d41a898d3c branch=fix/plan-approval-marker-pr-merge commit=867cb04 actor=amodal1 agent=anthropic/claude-sonnet-5 generated_at=2026-08-06 -->

# Agent handoff: after `fix/plan-approval-marker-pr-merge` (item 45 dossier written, both fix shapes characterized, neither implemented — chain's last case)

**Branch to create:** none — this handoff's own subject branch (`fix/plan-approval-marker-pr-merge`) is the chain's **last case**. The next step is the orchestrator's own chain close-out, not a new case branch.
**Base branch:** `feat/verify-dont-assume-guard`

**This is not `main`.** Same stacked-chain posture as every predecessor in this
series: nothing in this chain has been pushed, PR'd, or merged as of this
writing. This branch's own close-out checklist step 4 ("Land it through the PR
channel") is reproduced verbatim below per template but was **not executed
this session** — landing the whole chain is the orchestrator's own next step,
not this branch's.

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

**Stream:** v1.1.0 Final March — CI-infrastructure pass, ahead of epic A.
**Sequencing rule:** strictly sequential — one branch at a time (within this
chain, "sequential" means tip-to-tip stacking, not each off `main`).
**Blocked until this stream tags:** the public v1.1.0 cut (epic E / item 10).

- ~~`chore/v11-march-kickoff`~~ ✓ · ~~`feat/consumer-enumeration-gate`~~ ✓ (C-10)
- ~~`fix/ux-scroll-spy-overlapping-refresh`~~ ✓ — item 44
- ~~`feat/ci-wait-wrapper`~~ ✓ — `scripts/ci_wait.py` (PR #102)
- ~~`feat/enforcement-first-governance`~~ ✓ — C-11 + C-12 (PR #103)
- ~~`feat/flake-rate-measurement`~~ ✓ — `scripts/flake_rates.py` + `docs/dev/flake-rates/`
- ~~`chore/dependabot-groups`~~ ✓ — `groups:` key added to `.github/dependabot.yml`
- ~~`feat/verify-dont-assume-guard`~~ ✓ — `verify-binary-on-path` PreToolUse guard +
  Bash-matcher hooks folded into one dispatcher
- **`fix/plan-approval-marker-pr-merge`** ← this branch (item 45 — dossier
  written, decision made: neither fix shape implemented, see below)
- **Next: the orchestrator's own chain close-out** — adversarial full-diff
  review across every case branch, then the owner's morning flow: push, one
  PR, `python -m scripts.ci_wait`, merge, then dependabot upgrades
  (#63 ruff, #50, #84) with owner confirm. **No further case branches follow
  this one.**

**The march is still deliberately paused. Do not touch epics B–E.**

**Item 10's release chain is still gated on epic 19** — untouched this
session.

**A NEW, urgent, chain-level blocker was found this session** (not part of
item 45, not fixed here — see "Carried-forward observations" and "What just
landed" below): the gate is **not** green at this branch's own base
(`feat/verify-dont-assume-guard`, `867cb04`), for two reasons entirely
predating this branch's own diff. **The orchestrator's chain close-out should
resolve this before pushing** — pushing now would fail CI on both.

---

## What just landed on `feat/verify-dont-assume-guard`

**Nothing pushed, PR'd, or merged.** This branch added no production code —
item 45's own dossier work concluded that neither candidate fix shape clears
the bar for implementation this session (see "What this branch should build"
below for the full reasoning). What actually changed:

- **New:** `docs/dev/diagnosis/plan-approval-marker-pr-merge.md` — the C-7
  dossier. Root cause of item 45 is **PROVEN** (re-verified live, plus a new
  isolated reproduction that holds "HEAD is a genuine merge commit" constant
  and true across both a PR-channel-shaped run and a local-`--no-ff`-shaped
  run, varying only the Bash command text/output — proving the mechanism is
  exactly "command-text shape", not "whether a merge structurally occurred").
  Both candidate fix shapes are characterized in depth; **neither is
  implemented**. Passes `scripts.enforcement.evidence.has_observed_evidence`
  and `has_observed_citation` (checked directly, not assumed).
- **Updated:** `docs/dev/work/items/0045-plan-approval-marker-survives-pr-merge.md`
  — a dated `## Updates` entry recording the re-verification, the new
  reproduction, and the decision. **Item 45 stays `open`** — no `verified_by`
  is claimed, because no fix landed (C-11: a closure needs a falsifiable
  artifact; there isn't one to point to here).
- **Committed:** this session's own provenance-ledger file
  (`docs/dev/ledger/c8caf603-88cf-46b6-b2aa-77d41a898d3c.jsonl`) — the
  `consumed` event for the prior handoff plus several `compacted` events
  (see "Recurrences" below).

**A NEW discovery, unrelated to item 45, found while running this branch's own
close-out gate — declared, not fixed, per this branch's own scope boundary:**
`feat/verify-dont-assume-guard`'s own tip (`867cb04`, this branch's base) does
**not** pass `pytest -m "not ux"` cleanly, despite that branch's own commit
message (`ee2ee0f`) claiming "2357 passed, 1 skipped... zero reruns". Two
failures, both root-caused (via `git stash` + isolated re-run against the
clean tip — the failures reproduce identically with none of this branch's own
changes present, proving they predate and are independent of this branch's
diff):

1. `tests/test_doc_links.py::test_no_broken_cross_document_links_or_cites` —
   `docs/dev/handoffs/feat-verify-dont-assume-guard.md:178` contains the
   `_MSYS_ABS_PATH_RE` regex literal (as defined in
   `scripts/enforcement/guards/verify_binary_on_path.py`) inside backticks;
   `check_doc_links.py` misparses the pattern's character-class-then-group
   shape as a link target that does not exist.
2. `tests/test_evidence_gate.py::TestEnforcementIsWired::test_every_hook_script_is_executable_in_the_index`
   — `hooks/bash-dispatcher.sh` is committed at git mode `100644` (not
   executable), confirmed via `git ls-tree ee2ee0f -- hooks/bash-dispatcher.sh`
   showing `100644` **at the commit that created the file** — unlike every
   sibling hook script (`git ls-tree` on `hooks/restore-evidence.sh` /
   `hooks/edit-write-dispatcher.sh` shows `100755`). **This is a recognized
   recurrence**, not a first sighting: commit `dfe1767` ("the three new hook
   scripts were not executable") is the exact same failure class, already
   once fixed reactively in this repo's history.

Both are **entirely outside item 45's scope** (a doc-link regex escape and a
git file-mode bit in a different branch's own deliverable) and this branch's
own C-7 dossier does not cover either — fixing them here would blur which
case fixed what, the same reasoning item 45's own file already gives for not
folding its fix into a governance branch. **Declared here per C-11/C-12
instead: this needs to be resolved before the chain pushes**, since it is
baked into the tip every case in this chain branches from and will fail CI
identically for whichever branch's PR opens first.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

**Open (5 — was 3 last handoff; +2 new this session, both declared above, 0
resolved):**

1. **Item 19 — UX-suite flake epic, still open (reopened 2026-08-05).** Not
   touched this session.
2. **Item 45 — plan-approval marker survives a PR-channel merge.** **This
   branch's own subject.** Root cause proven; both fix shapes characterized;
   **neither implemented** — the narrower `SessionStart` branch-existence
   design characterized in the dossier's "Decision" section is a staged,
   not-yet-built proposal for the owner to approve or reject. Item stays
   open.
3. **Item 50 — C-7/C-10 are Claude-Code-only; the extraction gap.** Not
   touched this session.
4. **NEW — `feat/verify-dont-assume-guard`'s own tip fails 2 pre-existing
   gate checks**, contradicting that branch's own commit-message claim of a
   clean gate run. Both root-caused this session (see "What just landed"
   above): a doc-link regex-escape false-positive in
   `docs/dev/handoffs/feat-verify-dont-assume-guard.md:178`, and
   `hooks/bash-dispatcher.sh` committed non-executable
   (`git ls-tree ee2ee0f -- hooks/bash-dispatcher.sh` → `100644`). **Resolve
   before the chain pushes** — CI will fail on both otherwise. Not fixed
   here (out of item 45's scope; would blur which case owns the fix).
5. **NEW — `hooks/bash-dispatcher.sh`'s non-executable commit is a
   recognized recurrence of a known failure class** (commit `dfe1767`,
   "the three new hook scripts were not executable", already fixed once
   reactively). The MECHANISM that catches this (`test_every_hook_script_is_
   executable_in_the_index`) already exists and fired correctly this time —
   the gap is procedural (the prior branch's own close-out did not re-run the
   full gate as the literal last step before its final commit), not a
   missing test. Worth the chain close-out asking: should the close-out
   checklist itself gain a "re-run gate against the FINAL committed tree,
   not a pre-handoff working copy" step? Named, not built — a process
   change to the checklist itself is bigger than this branch's own scope.

**Watching (10, unchanged this session — not re-touched, not re-derived
beyond confirming none of this session's own work affects them):**
- Item 30 — REOPENED, three dated CI occurrences, still not root-caused.
- Item 46 — independently reproduced by `flake_rates.py`; still n=1.
- Item 47 — audit sibling scroll-spy tests for item 44's settle-gate hole.
- Item 48 — pytest-step duration anomaly, still uncharacterized (n=1).
- Item 49 — test suite leaves `tmp*.html` litter in tracked `personas/bundled/`.
- Item 51 — `report --check` against a committed budget; deliberately unbuilt.
- Item 2 (wordmark sweep) · Item 16 (`--suite real` non-functional) · Item 18
  (judge variance, n=2) · Item 23 (PX-52 analyzer split).
- The Git-Bash/MSYS-path resolution class + the dependabot-groups
  post-merge-morning check — both carried from the immediately-prior handoff,
  still not checked or built; not this branch's scope.

**Blocked (3 + the sequenced epics, unchanged):** item 3 ([HUMAN] GitHub
toggles), item 5, item 8, epics 37–40.

**Deferred (7, unchanged):** items 4, 7, 24, 25, 41, 42, 43.

Open-only count is now **5**, still under the reduction-sprint threshold, but
worth flagging: 2 of the 5 are new-this-session discoveries about a SIBLING
branch's own gate state, not new item-45 work — the chain close-out should
treat resolving them as a precondition for pushing, not as backlog.

---

## Recurrences observed this session → guardrail authored

**Two recognized recurrences this session. Neither got a NEW mechanism —
one because the existing mechanism already covers it and fired correctly,
one because this dossier's own conclusion is that authoring a NEW
approval-adjacent mechanism needs an owner decision first, and building one
anyway under a decision-not-yet-made would be exactly the failure C-11 exists
to prevent, not a compliant response to it.**

1. **A mid-session `compacted` ledger event — the fourth consecutive session
   disclosing this class** (`docs/dev/ledger/c8caf603-88cf-46b6-b2aa-77d41a898d3c.jsonl`,
   one new row this session: `branch=fix/plan-approval-marker-pr-merge,
   ts=2026-08-06T13:16:05Z`, `session=unknown`, `trigger=unknown`, matching
   the same shape every predecessor handoff has already disclosed). **No new
   guardrail authored**, for the same reason stated in every prior
   disclosure: the existing mechanism (the PreCompact hook writing a
   `compacted` receipt) is precisely what this class needs — a disclosure
   trigger, not a prevention mechanism, since a repo-side hook cannot prevent
   compaction itself. This agent's own reasoning trace shows no discontinuity
   at any point in this session; every fact cited above was verified directly
   against live tool output at the point of use, not recalled from a prior
   summary.
2. **`hooks/bash-dispatcher.sh` committed non-executable — recognized as the
   same class as commit `dfe1767`** ("the three new hook scripts were not
   executable"), not a first sighting. **No new mechanism authored on THIS
   branch**, for a specific reason: the mechanism that catches this class
   ALREADY EXISTS (`test_every_hook_script_is_executable_in_the_index`) and
   it fired correctly the moment this session ran the full gate — it is not
   a missing check, it is a **procedural** gap (the branch that introduced
   the regression did not re-run the full gate as the literal last step
   before its own final commit). Authoring a second mechanism for a gap the
   first mechanism already closes would be exactly the "third redundant
   mechanism" C-11's own text names as the failure. **Surfaced explicitly to
   the user/orchestrator instead** (per C-11's own "if no mechanism is
   possible, say so explicitly, with the reason" clause) as a candidate
   process change to the close-out checklist itself (see "Carried-forward
   observations" item 5) — not built here, because a checklist-process
   change is bigger than this branch's own scope and needs the same kind of
   owner sign-off as item 45's own fix shape.

**Everything else this session** (the isolated D2 reproduction's own
self-caught instrumentation bug — an early `-q` flag on the setup `git merge`
suppressed git's own `Merge made by...` output, producing a false negative
about the test's OWN correctness, not the hook's; caught and fixed within the
same turn, never landed as a claim) **was a first-sighting-with-its-own-fix,
not a recognized recurrence left ungoverned.**

---

## What this branch should build

**Nothing further on this branch — item 45's dossier work is this branch's
complete deliverable, and the decision it reached is "neither implemented."**
Per `docs/dev/work/items/0045-plan-approval-marker-survives-pr-merge.md` and
this branch's own brief:

1. **Root cause of item 45 is PROVEN**, not inferred — see
   `docs/dev/diagnosis/plan-approval-marker-pr-merge.md`'s `## Observed`
   section (re-verified live at this branch's own HEAD, plus a new isolated
   reproduction).
2. **Both candidate fix shapes were characterized, neither implemented:**
   - (a) a `PostToolUse` matcher on `gh pr merge`'s command shape is
     demonstrably insufficient — it structurally cannot see dependabot's
     server-side auto-merge (enabled in this repo since 2026-08-04),
     GitHub-UI merges, or merges from another terminal/session, which are
     the dominant real merge channel here, not an edge case.
   - (b) naive `SessionStart` reconciliation ("has `main` moved since
     approval?") fails the mandated compaction-mid-session test: an
     unrelated auto-merge landing on `main` while an unrelated plan is still
     legitimately active would disarm a legitimately-armed marker. A
     narrower design ("has *this approved branch* been merged?", via a new,
     additive stamp file + branch-existence/ancestor-of-`main` check) is
     channel-independent and, hand-traced against the compaction scenario,
     does not misfire — but it is a first-of-its-kind mechanism that can
     autonomously delete approval state, and the dossier's own "Decision"
     section judges that deserves an explicit owner call before being
     written, not only before being merged.
3. **Item 45 stays open.** The dossier's "Decision" section carries the
   staged, not-yet-built proposal (the narrower branch-existence design) for
   the owner to approve, reject, or amend on a future branch.

**Scope was bounded to item 45** as filed in
`docs/dev/work/items/0045-plan-approval-marker-survives-pr-merge.md`. The two
NEW discoveries about `feat/verify-dont-assume-guard`'s own gate state
(above) were deliberately **not** picked up as fixes, for the same reason —
they are a different case's own defects, and fixing them here would blur
which branch owns which fix.

**This is the chain's last case.** The next step is the orchestrator's own
chain close-out: an adversarial full-diff review across every case branch in
this stacked chain, then the owner's morning flow — push, open one PR, wait
with `python -m scripts.ci_wait`, merge, then the queued dependabot upgrades
(#63 ruff, #50, #84) with owner confirm. **No further case branches follow
this handoff.** The two pre-existing gate failures named above should be
resolved as part of that close-out, before the push — see "Carried-forward
observations" items 4–5.

---

## First move

There is no "first move" for a new branch — this handoff's own subject
branch already exists and this session's work on it is complete. The
orchestrator's first move is its own chain close-out (see above), starting
with the two pre-existing gate failures this handoff declares.

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
