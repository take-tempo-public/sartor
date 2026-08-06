<!-- provenance: schema=1 session=c8caf603-88cf-46b6-b2aa-77d41a898d3c branch=fix/chain-gate-integration commit=f568ca3 actor=amodal1 agent=anthropic/claude-sonnet-5 generated_at=2026-08-06 -->

# Agent handoff: after `fix/chain-gate-integration` (the two named-test fixes the chain declared but did not implement — chain now closed)

**Branch to create:** none — this is the chain's own close-out fix, and the chain is now complete. The next step is the orchestrator's own chain close (adversarial full-diff review, then the push/PR/merge flow), not a new case branch.
**Base branch:** `fix/plan-approval-marker-pr-merge` (tip `bc224bc`)

**This is not `main`.** Same stacked-chain posture as every case before it:
nothing in this chain has been pushed, PR'd, or merged as of this writing.
This branch's own close-out checklist step 4 ("Land it through the PR
channel") is reproduced verbatim below per template but was **not executed
this session** — landing the whole chain is the orchestrator's own next
step, not this branch's.

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
- ~~`fix/plan-approval-marker-pr-merge`~~ ✓ — item 45 dossier written, root cause
  proven, neither candidate fix shape implemented (item stays open by design);
  declared (not fixed there) the two pre-existing gate failures this branch
  closes
- **`fix/chain-gate-integration`** ← this branch — the two named-test fixes
  the prior handoff declared as a chain-level blocker, now resolved
- **Next: the orchestrator's own chain close-out** — adversarial full-diff
  review across every case branch, then the owner's morning flow: push, one
  PR, `python -m scripts.ci_wait`, merge, then dependabot upgrades
  (#63 ruff, #50, #84) with owner confirm. **No further case branches follow
  this one — the chain is complete.**

**The march is still deliberately paused. Do not touch epics B–E.**

**Item 10's release chain is still gated on epic 19** — untouched this
session.

**The chain-level blocker `fix/plan-approval-marker-pr-merge` declared —
`feat/verify-dont-assume-guard`'s own tip failing 2 pre-existing gate
checks — is RESOLVED by this branch.** See "What just landed" below. The
full gate (`ruff` / `ruff format --check` / `mypy` / `pytest -m "not ux"`)
is now green at this branch's tip with no reruns; the two named tests that
were failing at `bc224bc` now pass. The chain is clear to push.

---

## What just landed on `fix/plan-approval-marker-pr-merge`

Commit `f568ca3` on this branch. Two named-test fixes, both root-caused by
the prior branch's own C-7 dossier work (`docs/dev/diagnosis/plan-approval-marker-pr-merge.md`
and its handoff — this branch did not re-diagnose, it implemented what was
already proven):

- **F1 — `hooks/bash-dispatcher.sh` committed at git index mode `100644`.**
  Fixed via `git update-index --chmod=+x hooks/bash-dispatcher.sh` (Windows
  has no filesystem x-bit; the index is where this lives — CI checks out the
  index mode). Verified before commit with `git ls-files -s hooks/` (the same
  method `test_every_hook_script_is_executable_in_the_index` uses): all 8
  `hooks/*.sh` now read `100755`.
- **F2 — a doc-link false positive from an embedded regex literal.**
  `docs/dev/handoffs/feat-verify-dont-assume-guard.md:178` quoted the
  `_MSYS_ABS_PATH_RE` regex literal (as defined in
  `scripts/enforcement/guards/verify_binary_on_path.py`) inside backticks
  that did not immediately wrap the whole `[text](path)` shape (the
  checker's own literal-backtick exemption requires the backtick to sit
  flush against the link's own opening and closing characters; here a
  two-character prefix sat between the backtick and the link-shaped
  content), so `check_doc_links.py`'s link-parser misread the pattern's
  character-class-then-group shape as a markdown link with a target that
  does not exist. Fixed per charter D5 (cite-don't-restate): the
  parenthetical now names `_MSYS_ABS_PATH_RE`'s home instead of restating
  the pattern.
  - **Discovered beyond what the inherited handoff named** (surfaced here,
    not silently absorbed — C-12): the RED-first run showed
    `test_no_broken_cross_document_links_or_cites` reporting **two** broken
    links, not the one the inherited handoff's own diagnosis described.
    `docs/dev/handoffs/fix-plan-approval-marker-pr-merge.md:120` — while
    *describing* this exact bug — itself quotes the identical regex literal
    and trips the identical false positive. Fixed with the same
    cite-don't-restate treatment (same file, same session, same root cause);
    both files' fingerprints were re-`generated` in the ledger after their
    edits (`feat-verify-dont-assume-guard.md` → `6ceeca43ae2d`,
    `fix-plan-approval-marker-pr-merge.md` → `18b73b8aff5f`). This second
    file was already `consumed` earlier this session under its OLD
    fingerprint (`95ec1b686939`, before this branch's edit) — that
    `consumed` event stays valid (it correctly validated the doc as it stood
    at the moment it was read); the fresh `generated` event is a later,
    additional fact for whoever reads the ledger next, not a contradiction
    of the earlier one.

**Both fixes share one cause, stated in the commit message:** post-gate
artifacts committed by an earlier branch were never re-gated against the
FINAL committed tree before that branch's own close-out — exactly the
procedural gap `fix/plan-approval-marker-pr-merge`'s own handoff named and
asked the chain close-out to consider (see "Recurrences" below).

**GREEN, re-verified after both fixes (no reruns):**
`tests/test_doc_links.py::test_no_broken_cross_document_links_or_cites` +
`tests/test_evidence_gate.py::TestEnforcementIsWired::test_every_hook_script_is_executable_in_the_index`
→ `2 passed`.

**Full gate at this branch's tip (foreground, timestamped):**
- `ruff check .` → all checks passed
- `ruff format --check .` → 342 files already formatted
- `mypy .` → Success: no issues found in 357 source files
- `pytest -m "not ux" -n auto` → **2357 passed, 1 skipped** (was 2355
  passed / 2 failed at `bc224bc`; the delta is exactly the two named tests
  flipping to green — no other test's outcome changed), no rerun markers in
  the output
- `pytest -m ux` (single background run, sanctioned — exceeds the 600s local
  cap; complete read-back below, not a skipped step) → **138 passed, 2358
  deselected, 2 xpassed in 724.69s (0:12:04)**, `EXIT: 0`. Full-log grep for
  `rerun`/`RERUN` matches only the plugin banner
  (`rerunfailures-16.4`) — no test needed a retry. The 2 `xpassed` are both
  in `tests\ux\regression\test_20260708_busy_states_and_chip.py`, pre-existing
  `xfail`-marked cases unrelated to either of this branch's two fixes (that
  file is untouched by this branch's diff) — an `xfail` marker that no
  longer reproduces, not a new failure; `EXIT: 0` confirms nothing failed.
  Noted here per C-12 rather than silently passed over; not investigated or
  fixed — out of this branch's two-named-test scope.
- `python -m scripts.work_items check` → `work_items: OK (51 files)`

**Wiki-relevance check (pre-close sweep item 0), performed explicitly, not
skipped:** `scripts.wiki_relevance.is_wiki_relevant()` checked against every
path this branch's own diff touches (`hooks/bash-dispatcher.sh`,
`docs/dev/handoffs/feat-verify-dont-assume-guard.md`,
`docs/dev/handoffs/fix-plan-approval-marker-pr-merge.md`) — **all three
returned `False`.** Verified no-edit; no `/wiki-self-update` run this
session, per the same convention `docs/wiki/log.md` already uses for a
checked-and-skipped path.

**No dev server or long-lived background process left running.** The one
background process this session started (`pytest -m ux`, PID `93068`)
terminated on its own with `EXIT: 0`; `tasklist` after completion shows no
python process belonging to this session (the remaining `python*.exe`
entries — PIDs `23528`, `64048`, `54328` — resolve to Claude-Code hook
infrastructure and a pre-existing `C:\Dev\spolia` orphan, confirmed via
`wmic process ... get CommandLine`, neither started by this branch).

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

Reproduced from `fix/plan-approval-marker-pr-merge`'s own handoff, updated
**only** where this branch changed reality — items 4 and 5 below are now
**RESOLVED**, not open. No other item was re-touched or re-derived this
session.

**Open (3 — was 5 last handoff; 0 new, 2 resolved this session):**

1. **Item 19 — UX-suite flake epic, still open (reopened 2026-08-05).** Not
   touched this session.
2. **Item 45 — plan-approval marker survives a PR-channel merge.** Not this
   branch's subject (that was `fix/plan-approval-marker-pr-merge`). Root
   cause proven there; both fix shapes characterized; neither implemented —
   the narrower `SessionStart` branch-existence design is a staged,
   not-yet-built proposal awaiting an owner decision. Item stays open. Not
   touched this session.
3. **Item 50 — C-7/C-10 are Claude-Code-only; the extraction gap.** Not
   touched this session.

**RESOLVED this session (2):**

4. ~~**`feat/verify-dont-assume-guard`'s own tip failed 2 pre-existing gate
   checks.**~~ **RESOLVED by this branch (commit `f568ca3`).** Both
   root-caused by the prior branch, fixed here: the doc-link regex-escape
   false positive (F2, two files) and `hooks/bash-dispatcher.sh` committed
   non-executable (F1). The full gate is green at this branch's tip with no
   reruns — see "What just landed" above. **This was the chain's own
   declared push-blocker; it no longer blocks.**
5. ~~**`hooks/bash-dispatcher.sh`'s non-executable commit — recognized
   recurrence of commit `dfe1767`'s failure class.**~~ **RESOLVED by this
   branch's F1.** The recurrence-class question itself (should a new
   mechanism be authored, or does the existing test already cover it) is
   addressed fresh in "Recurrences" below — this branch's own C-11 answer
   differs from the inherited handoff's, because this branch is a *third*
   sighting of the class, not a second, and that changes the answer.

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
  post-merge-morning check — both carried from several handoffs back, still
  not checked or built; not this branch's scope.

**Blocked (3 + the sequenced epics, unchanged):** item 3 ([HUMAN] GitHub
toggles), item 5, item 8, epics 37–40.

**Deferred (7, unchanged):** items 4, 7, 24, 25, 41, 42, 43.

Open-only count is now **3**, comfortably under the reduction-sprint
threshold — the two items that pushed it to 5 last handoff were this
session's own fix targets, not new backlog growth. `docs/dev/work/BOARD.md`
was not regenerated this session (`python -m scripts.work_items check`
passed against the committed items; none of this branch's two fixes are
tracked work items — they were named directly by the inherited handoff,
not filed as `docs/dev/work/items/*.md` entries — so no board regeneration
was needed or performed).

---

## Recurrences observed this session → guardrail authored

**Two recognized recurrences this session. One gets the same disclosed,
no-new-mechanism answer every predecessor handoff in this chain already
gave; the other gets a different C-11 answer than the inherited handoff
gave for the same underlying class — stated plainly, because the reasoning
that justified "no new mechanism" last time no longer holds.**

1. **Two mid-session `compacted` ledger events — the fifth consecutive
   session disclosing this class** (`docs/dev/ledger/c8caf603-88cf-46b6-b2aa-77d41a898d3c.jsonl`,
   two new rows this session, both `branch=fix/chain-gate-integration,
   session=unknown, trigger=unknown`, timestamps `2026-08-06T13:50:07Z` and
   `2026-08-06T13:55:46Z`, matching the same shape every predecessor
   handoff in this chain has already disclosed). **No new guardrail
   authored**, for the same reason stated in every prior disclosure: the
   existing mechanism (the PreCompact hook writing a `compacted` receipt)
   is precisely what this class needs — a disclosure trigger, not a
   prevention mechanism, since a repo-side hook cannot prevent compaction
   itself. Per C-8's own instruction to reconcile against the repo and git
   after a compaction rather than trust a summary: every fact this handoff
   states was re-verified directly against live tool output at the point of
   use this session (git ls-files, pytest output, ruff/mypy exit codes, the
   ledger diff itself) — nothing here was carried forward from an
   unverified prior-turn summary.
2. **`hooks/bash-dispatcher.sh` committed non-executable.** The inherited
   handoff recognized this as the *second* sighting of the class first seen
   at commit `dfe1767` ("the three new hook scripts were not executable")
   and declined to author a new mechanism, reasoning that the existing test
   (`test_every_hook_script_is_executable_in_the_index`) already covers the
   class and "fired correctly the moment this session ran the full gate" —
   framing the gap as **procedural** (a branch's close-out not re-running
   the full gate against its own final committed tree), not a missing
   check.

   **This session is a fix, not a diagnosis — the fact pattern is now a
   *third* instance of the same class** (`dfe1767`, then the mode-bit miss
   `fix/plan-approval-marker-pr-merge` found and declared, now this
   branch's own F1 fixing it). Three instances of "the existing test would
   have caught this at commit time, but didn't run until later" is no
   longer a one-off procedural lapse to note and move past — it is a
   pattern in how commits get made on this repo (an agent-authored file
   arrives via `Write`, which does not set the x-bit on Windows, and the
   gate that would catch it does not run until close-out, by which point
   several commits may have already landed the miss).

   **No new mechanism authored on this branch either — but for a different,
   narrower reason than the inherited handoff's, and stated explicitly per
   C-11's "if no mechanism is possible, say so explicitly, with the
   reason" clause:** the fix belongs at the point where a new hook script
   file is *written*, not at close-out (a pre-commit or PostToolUse hook on
   `Write`/`Edit` to `hooks/*.sh` that immediately calls
   `git update-index --chmod=+x` would close this at the source, before a
   single commit lands the miss) — but authoring that hook is itself a
   change to `.claude/settings.json`'s hook wiring, which this branch's own
   scope (two named test fixes, nothing else) does not authorize, and
   which — per this same repo's own governance history — is exactly the
   kind of addition that should not be improvised mid-fix by the agent that
   happens to be looking at the third occurrence. **Surfaced explicitly to
   the orchestrator/owner as a candidate new gate** (a `hooks/*.sh`-path
   PostToolUse `Write`/`Edit` chmod-stamper), narrower and more specific
   than the inherited handoff's own "should the close-out checklist gain a
   final re-gate step" suggestion — that suggestion would still only catch
   the miss at close-out, i.e. after N more commits already carry it. Not
   built here.

**Everything else this session** (running the full `pytest -m "not ux"`
suite twice while confirming no rerun markers, once for the gate itself and
once for a redundant confirmatory grep — a self-caught inefficiency, not a
correctness issue, corrected within the same turn by not repeating it for
the `-m ux` run) **was a first-sighting self-correction, not a recognized
recurrence left ungoverned.**

---

## What this branch should build

**Nothing further — this branch's two named fixes are its complete
deliverable, and this is the chain's last case.**

1. **F1 and F2, as declared by `fix/plan-approval-marker-pr-merge`'s own
   handoff**, are implemented and committed (`f568ca3`): `hooks/bash-dispatcher.sh`
   re-gated to `100755` in the index; the doc-link regex-literal false
   positive fixed per cite-don't-restate, in both the one file the inherited
   handoff named and the one additional file this session's RED-first run
   found containing the identical defect.
2. **The full gate is green** (`ruff` / `ruff format --check` / `mypy` /
   `pytest -m "not ux"` at 2357 passed / 1 skipped, `pytest -m ux` — see
   below) with **no reruns** — the chain-level push-blocker the prior
   handoff declared is resolved.

**THIS CHAIN IS COMPLETE.** The next step is the orchestrator's own chain
close-out: an adversarial full-diff review across every case branch in this
stacked chain, then the owner's morning flow — push, open one PR, wait with
`python -m scripts.ci_wait`, merge, then the queued dependabot upgrades
(#63 ruff, #50, #84) with owner confirm. **No further case branches follow
this handoff.** Scope was bounded to exactly the two named tests this
handoff's own predecessor declared as a chain-level blocker; nothing beyond
those two (plus the one additional occurrence of F2's own defect class
this session's RED-first run surfaced, needed to make the SAME named test
pass) was implemented. Do not expand beyond what is listed here.

---

## First move

There is no "first move" for a new case branch — this chain is closed. The
orchestrator's first move is its own chain close-out (see above), starting
with the adversarial full-diff review across every case branch this chain
produced.

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
