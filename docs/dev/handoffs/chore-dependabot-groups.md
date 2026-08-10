<!-- provenance: schema=1 session=c8caf603-88cf-46b6-b2aa-77d41a898d3c branch=chore/dependabot-groups commit=55f7c1e actor=amodal1 agent=anthropic/claude-sonnet-5 generated_at=2026-08-06 -->

# Agent handoff: after `chore/dependabot-groups` (dependabot PR collapse landed as config; next is the verify-don't-assume Bash guard)

**Branch to create:** `feat/verify-dont-assume-guard` (branch off `chore/dependabot-groups`)
**Base branch:** `chore/dependabot-groups`

**This is not `main`.** This handoff's branch is one case in an owner-sanctioned,
serialized experiment chain running tonight — cases stack tip-to-tip on each
other's local, unmerged branch tips, not off `main`. Nothing in this chain has
been pushed, PR'd, or merged as of this writing; that is deliberate (see
"What just landed" below), and the close-out checklist's own step 4 ("Land it
through the PR channel") is reproduced verbatim below per template but was
**not executed this session** — the chain's own close-out (adversarial
full-diff review + staged state for morning) is a separate, later step, not
this branch's job.

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
  (pip / github-actions / npm-docs-site), this handoff's branch
- **`feat/verify-dont-assume-guard`** ← next (owner-directed: PreToolUse Bash
  guard for binaries not on PATH, plus folding the Bash-matcher hooks into one
  dispatcher mirroring `hooks/edit-write-dispatcher.sh`)
- Still queued: dependency upgrades (#63 ruff, then #50, #84) → items 45 →
  sprint A1
- `fix/experience-soft-retire` ← sprint A1, only after the above **and** a
  check-in

**The march is still deliberately paused. Do not touch epics B–E.**

**Item 10's release chain is still gated on epic 19** — untouched this
session; do not route around it.

---

## What just landed on `main`

**Nothing yet — not merged, not pushed, no PR.** This is deliberate for this
session: this branch is one case in a serialized experiment chain running
locally, tip-to-tip, with a separate later chain-close step (adversarial
full-diff review + staged state left for morning) that decides what — if
anything — goes through the PR channel. The "Land it through the PR channel"
step in the Close-out checklist below is reproduced verbatim per the
template's own requirement, but was **explicitly not executed** — no `git
push`, no `gh pr create`, no merge. Say this plainly rather than letting the
verbatim checklist text imply otherwise.

**On `chore/dependabot-groups` (branched off `main` @ `55f7c1e`), staged for
this session's close-out commit:**

- **`.github/dependabot.yml`** — added a `groups:` key to each of the three
  `update:` blocks (`pip`, `github-actions`, `npm` in `/docs-site`), grouping
  `minor` + `patch` `update-types` per ecosystem. `major` is deliberately left
  out of every group so a breaking bump still opens its own
  individually-reviewable PR. Schema matches GitHub's documented `groups`
  reference; validated locally by round-tripping the file through
  `yaml.safe_load` (there is no server-side dependabot dry-run available —
  the config is latent until pushed, same "committed but dormant" framing the
  file's own header already used for the rest of it).
- **`CHANGELOG.md`** — one `[Unreleased]` entry added at the top of the
  section (newest-first, matching the file's existing convention), naming the
  change, the `major`-excluded design choice, and the explicit
  out-of-scope-tonight caveat below.
- **`docs/dev/ledger/c8caf603-88cf-46b6-b2aa-77d41a898d3c.jsonl`** — this
  session's own provenance-ledger shard (two `consumed` rows for the incoming
  handoff, one from the orchestrating session and one from this agent, plus a
  `compacted` row — see below), landing per `docs/dev/prov/SPEC.md` §5 step 3.

**Explicitly out of scope for this commit, stated rather than silently
omitted (per this branch's own brief):** verifying that dependabot's next
scheduled run actually opens grouped PRs from this config. Dependabot only
re-evaluates `.github/dependabot.yml` on its own schedule / next push, so
there is nothing to observe yet tonight — this is real, deferred, **post-merge
morning work**, not a check that could have been run now. See "Carried-forward
observations" below.

**Local gate green**, run as individual steps per this branch's own brief
(foreground, explicit timeouts, `; echo "EXIT: $?"` on each): `ruff check .` ✓
· `ruff format --check .` ✓ · `mypy .` ✓ **355 files** · `pytest -m "not ux"
-n auto` **2325 passed / 1 skipped** (491.46s) · `pytest -m ux` **138 passed /
1 xfailed / 1 xpassed, zero reruns** (716.11s — exceeded the Bash tool's
600 000 ms single-command cap and was moved to background by the tool itself
rather than killed; see the deviation note below) · `work_items check` ✓ **51
files**. `python -m scripts.gate` was **not** re-run as one wrapper command
after the individually-verified steps all passed — this branch's own brief
listed the six steps individually and did not additionally ask for the
wrapper, so this is not a deviation the way it was framed on the prior branch,
just stating it for the record.

**Deviation from the literal chunking instruction, stated plainly rather than
glossed over:** the brief's contingency for `pytest -m ux` exceeding the cap
was "three chunks — a11y+flows, regression first half, regression second
half." That chunk split was **not executed**. Instead, the Bash tool's own
graceful degradation (move-to-background on timeout rather than kill) let the
single unsplit run complete to a clean, coherent result, which was then read
back from its output file. The effect is equivalent — one full, uninterrupted
suite run, not three partial ones stitched together — but the literal
documented procedure was not the one followed, and that gap is named here
rather than left implicit. Worth a look for whoever next touches this
close-out contract: the ux tier's wall-clock (~716–818s across the last two
sessions) reliably exceeds the tool's 600s single-command ceiling, so the
"if over-cap" branch is not a rare contingency, it is the normal case —
proactively backgrounding or chunking `pytest -m ux` from the start (rather
than reactively, after hitting the cap) would remove this recurring
ambiguity. Filed here as a discovery, not built.

**A `compacted` ledger event appeared mid-session** (`docs/dev/ledger/c8caf603
-….jsonl`, `session=unknown`, `trigger=unknown`, timestamped between the two
long-running gate commands). Disclosed per C-8/C-12 rather than worked around
quietly: this agent's own reasoning trace shows no discontinuity or dropped
context at any point in this session, and every fact this handoff cites was
re-verified directly against live `git`/tool output at the point of use, not
recalled from a prior summary — so nothing is known to have been lost on this
agent's side. The event's own `session=unknown` field means it cannot be
attributed with certainty to *this* agent's context versus a concurrently
running process sharing the same ledger path; that uncertainty is stated
rather than resolved by assumption. This is the **second consecutive session**
in which a mid-session `compacted` event was disclosed this way (the
immediately-prior handoff, `feat/flake-rate-measurement`, reported the same
class of event). See "Recurrences observed this session" below for why no new
mechanism was authored for it.

**Unrelated discovery, not touched:** a stray `python.exe` process (PID
64048, `C:\Dev\spolia\.venv\Scripts\python.exe -m http.server 8971`) was
observed running on this machine, created 2026-08-01 — five days before this
session started, from an entirely different project. Not started by this
session, not cleaned up by this session (out of scope for a `sartor.`
close-out sweep, which covers processes *this* session started). Named here
per C-12 rather than silently left unmentioned, since it is exactly the class
of orphaned-process risk the carry-forward ledger's item 20 already
documents.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

**Open (2 / 10 ceiling, unchanged this session):**
1. **Item 19 — UX-suite flake epic, still open (reopened 2026-08-05).** Not
   touched this session. The flake CLASS itself remains unguarded.
2. Item 45 — plan-approval marker survives a PR-channel merge. Not touched
   this session; still worth a fresh `EnterPlanMode` → plan → `ExitPlanMode`
   rather than trusting a pre-existing marker.

**Watching (10, +1 new this session):**
- Item 30 — REOPENED, three dated CI occurrences, still not root-caused.
  **Do not fix from the rate alone.** Untouched this session.
- Item 46 — independently reproduced by `flake_rates.py`; still n=1,
  escalation signal not fired. Untouched this session.
- Item 47 — audit sibling scroll-spy tests for item 44's settle-gate hole;
  still not done. **This session incidentally observed one relevant data
  point while running the unrelated UX gate step** — a live flip from the
  prior session's "2 xfailed" baseline to "1 xfailed / 1 xpassed" on
  `tests/ux/regression/test_20260708_busy_states_and_chip.py::
  test_wizard_render_smooth_scroll_creeps_explicit_baseline`. That test's own
  docstring frames an occasional xpass as expected instrument behavior
  (`strict=False`, explicitly not a gate signal for anything but mode C), so
  this is **not** treated as a new defect and **item 47's line is otherwise
  left unchanged** — no audit was performed, only incidentally observed.
  Filed as a data point for whoever next opens item 47, not chased.
- Item 48 — pytest-step duration anomaly, still uncharacterized (n=1).
  Untouched this session.
- Item 51 — `report --check` against a committed budget; deliberately
  unbuilt, not enough history yet. Untouched this session.
- Item 2 (wordmark sweep) · Item 16 (`--suite real` non-functional) · Item 18
  (judge variance, n=2) · Item 23 (PX-52 analyzer split) — untouched this
  session.
- **NEW, unfiled — verify the dependabot `groups:` PRs actually land grouped.**
  This branch added `groups:` to `.github/dependabot.yml`; dependabot only
  re-evaluates config on its own schedule / next push, so there is nothing to
  check yet tonight. **Explicitly post-merge, morning work** per this
  branch's own brief. Capture in whichever branch is open when the chain's
  staged state is reviewed and (if approved) pushed — do not open a
  standalone branch just for this check.

**Blocked (3 + the sequenced epics, unchanged this session):** item 3
([HUMAN] GitHub toggles), item 5, item 8, epics 37–40 — untouched this
session.

**Deferred (7, unchanged this session):** items 4, 7, 24, 25, 41, 42, 43 — see
`BOARD.md`, untouched.

Open-only count is 2, under the reduction-sprint threshold — unchanged. The
honest signal, same as last handoff: nothing landed this session fixes a
flake or resolves a board item. This branch changed one piece of dependabot
config and added one deferred, unfiled follow-up check; nothing here should
read as progress against the open ledger itself.

---

## Recurrences observed this session → guardrail authored

**One recognized recurrence, deliberately given no new mechanism (the
existing one already covers it); nothing else recognized as a class member
this session.**

1. **A mid-session `compacted` ledger event, the same class disclosed by the
   immediately-prior handoff (`feat/flake-rate-measurement`) — now observed
   in two consecutive sessions.** → **No new guardrail authored.** The
   existing mechanism — the PreCompact hook writing a `compacted` receipt into
   the session's own ledger shard, which is what made this event visible at
   all rather than silent — is precisely what this class of event needs: a
   disclosure trigger, not a prevention mechanism (compaction itself is not
   something a repo-side hook can prevent). Authoring a third redundant
   mechanism for an already-covered gap would be exactly the failure C-11's
   own text warns against ("filing a third redundant mechanism for the same
   already-covered gap"). Stated explicitly per that same reasoning rather
   than silently repeating it.

**Everything else surfaced this session** (the `pytest -m ux` over-cap
deviation, the item-47 xpass/xfail data point, the unrelated `spolia` orphan
process) **was a first sighting or an explicitly-anticipated contingency from
this branch's own brief, not a recognized recurrence of a prior failure
mode.** Each is filed above under "What just landed" / "Carried-forward
observations" rather than claimed here as a C-11 recurrence it is not. Read
that distinction twice before trusting it: the over-cap wall-clock in
particular *could* be argued as a recurrence (the same tier exceeded the same
cap on the prior branch too, per that handoff's own "818s local wall-clock"
figure) — it is named as a discovery rather than a C-11 recurrence because
this branch's own brief already anticipated and pre-authorized a specific
mitigation for it (the three-way chunk split), which makes it a contingency
this session executed a *different-but-equivalent* path through, not a gap
this session newly recognized and had to decide how to guard.

---

## What this branch should build

**OWNER-DIRECTED, not a proposal to re-confirm:** per the chain's own
sequencing (this handoff's own case list, and the
`project-verify-dont-assume-guard` memory), the next case is a PreToolUse
Bash guard for binaries not on `PATH`, plus folding the existing Bash-matcher
hooks into one dispatcher mirroring `hooks/edit-write-dispatcher.sh` (which
already does this for `Edit`/`Write`).

1. **A PreToolUse hook for the `Bash` tool matcher** that checks the first
   token of the command against `PATH` (and any project convention for
   locating interpreters/binaries — check `hooks/` for how the existing
   dispatcher resolves tool names) and blocks with a clear message rather than
   letting the shell fail with a bare "command not found" deep inside a
   multi-step command.
2. **Fold the current per-hook Bash matchers into one dispatcher script**
   mirroring `hooks/edit-write-dispatcher.sh`'s pattern — read that file first
   to understand the dispatch shape it already uses for `Edit`/`Write`
   (single entry point in `.claude/settings.json`, sub-hooks invoked from
   inside the dispatcher) before writing a new one for `Bash`. Enumerate the
   current Bash-matched hooks in `.claude/settings.json` before touching
   anything — this is itself a "how many things does this touch" question in
   the same spirit as C-10, even though `.claude/settings.json` is not on the
   formal `blast_radius.py` registry.
3. Per the memory `project-verify-dont-assume-guard`: this is **owner-
   directed**, not owner-*confirmed-per-branch* the way `flake-rate-
   measurement` was — **confirm scope with the owner at session start** rather
   than assuming this full memory-note scope is exactly and only what's
   wanted tonight, the same caveat the incoming handoff applied to this
   branch's own dependabot scope.

**Scope is bounded to the PreToolUse Bash guard + the dispatcher fold
described above and in the `project-verify-dont-assume-guard` memory.** Do
not also pick up the ruff/codeql/fumadocs dependency bumps, item 45, sprint
A1, or any flake fix — those are separately sequenced, and this chain's own
next-next case (`fix/plan-approval-marker-pr-merge` — item 45) is already
slotted after this one.

---

## First move

**This branch bases off `chore/dependabot-groups`, not `main`** — this
chain's cases stack tip-to-tip. Do not `git checkout main` first.

Agent: FIRST action is `python scripts/check_handoff_pointer.py "<the pointer
line you were given>"`; once it passes, consume this file
(`python scripts/verify_doc_template.py
docs/dev/handoffs/chore-dependabot-groups.md
docs/dev/AGENT_HANDOFF_TEMPLATE.md --event consumed --agent <agent>`).

Then create `feat/verify-dont-assume-guard` off `chore/dependabot-groups`
(**not** `main`), write a plan at `~/.claude/plans/<slug>.md`, and show it
before touching code. **Do not code first.**

**Do not trust a pre-existing plan-approval marker** (item 45). Earn a fresh
one via `EnterPlanMode` → plan → `ExitPlanMode`.

**This chain has not been pushed anywhere.** There is no PR to wait on yet
for this case or the one before it — `scripts/ci_wait.py` only becomes
relevant once/if the chain's own close-out decides to push and open PRs.

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
