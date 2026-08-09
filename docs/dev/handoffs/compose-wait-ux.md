<!-- provenance: schema=1 session=aaa7857e-4732-4daf-90f7-97315fac91f9 branch=feat/compose-wait-ux commit=2a0b37a actor=amodal1 agent=anthropic/claude-opus-5 generated_at=2026-08-09 -->

# Handoff — Epic A sprint A3 of the stacked chain: the item-20 Step-5 rail gate

**Branch to create:** `fix/step5-rail-frozen-gate` (branch off `feat/compose-wait-ux`)
**Base branch:** `feat/compose-wait-ux` — the A2 tip. **NOT `main`.**

> **Read this before anything else.** The Epic A chain stacks: each sprint branch
> starts from the prior sprint's own tip and there are **no intermediate merges**.
> The whole epic lands as **ONE owner-gated PR after A4**. Close-out steps 4 and 5
> in the verbatim checklist at the bottom of this file (push, PR, `ci_wait`, merge,
> prune) **do not apply at a sprint boundary** — you do steps 0–3 and stop. This is
> not your discretion; it is the owner-approved amendment recorded in
> `docs/dev/RELEASE_ARC.md` §"Cadence + process" (2026-08-08) and the authorization
> envelope named below.
>
> **The chain's authorization envelope is `docs/dev/epic-a-chain-design-corrections.md`
> §11, and it carries forward unchanged.** Run vector, halt points, flag stops, the
> delegation seam (the orchestrator never touches the working tree; three fresh agents
> per sprint — implementer, adversarial refuter, closer), and the resume protocol all
> live there. **Read §11 in full; it is not restated here** and nothing in this handoff
> overrides it.
>
> **The design of record is `docs/dev/handoffs/docs-epic-a-wave-orchestration-design.md`
> — read it IN FULL, not the errata alone.** Two sessions got their own role wrong by
> skipping it and reading only the corrections doc. Budget the read.
>
> **No new plan ceremony.** One `ExitPlanMode` approval, taken once at the start of the
> chain, covers every sprint. The approved plan file is **FROZEN** — do not rewrite it,
> do not re-enter plan mode, do not ask for a fresh approval click. The "First move"
> section below is adapted accordingly and deliberately departs from the template's
> default wording.

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

**Stream:** v1.1.0 Final March — **Epic A (`epic/a-app-core`, board item 36)**: main-app
function + UX. Four sprints, A1–A4, run as a **stacked chain** with no intermediate
merges.
**Sequencing rule:** strictly sequential — one sprint, one branch, one session, each
branching off the previous sprint's tip.
**Blocked until this stream lands:** epics B (render/ATS), C (diagnostics), D (docs IA),
E (release) — board items 37/38/39/40, all `blocked`.

- ~~`feat/corpus-polish` (A1a)~~ ✓ — corpus panel reordered to Summary → Work Experience
  → Education → Skills; rows compacted; role-card order fixed. Commit `7c15c2e`.
- ~~`fix/experience-soft-retire` (A1b)~~ ✓ — retire now happens at the *role* level, not
  only its bullets, so a 0-bullet role stops silently no-op'ing; migration `0016` +
  `Experience.is_active` + the unfiltered-consumer sweep. Commit `5474763`.
- ~~`feat/compose-wait-ux` (A2)~~ ✓ ← **just closed; this handoff's branch.** The
  "Composing…" arrival wait gate, the labelled bg chip, word-button skills pin/drop,
  in-place Edit on every compose bullet. Commit `2a0b37a`.
- **`fix/step5-rail-frozen-gate`** ← **next: this is what you build.** Item 20, the
  Step-5 wizard-rail hard gate. **Its own `fix/*` branch — see below for why.**
- `feat/role-summary-drafting` (A3) ← after that. Do **not** start it here.
- `feat/prior-apps-pipeline` (A4) ← last sprint of the epic. Do **not** start it here.

**Why item 20 gets its own `fix/*` branch instead of riding on a `feat/*` one.** The
`require-evidence-before-fix` guard (charter C-7) fires **only on `fix/*` branches**.
Folding an evidence-owing fix onto a `feat/*` branch does not merely skip a ceremony —
it **silently disables the guard**. That makes Epic A **six branches, not five**, and it
is deliberate: `docs/dev/epic-a-chain-design-corrections.md` finding 5, echoed in
`docs/dev/RELEASE_ARC.md` and in A2's own `docs/dev/blast-radius/compose-wait-ux.md`
`## Deferred` note 6. Do not "simplify" it back onto a feature branch.

**Do NOT start on this branch:** anything in A3 (the `draft_experience_summaries` call,
the per-role summary card, the eval fixture) or A4 (removing the Tailor applications
panel, rewriting `_renderPipelineRow`'s `activate()`). Each is its own sprint with its
own brief in `RELEASE_ARC.md` §"Epic A". Item 20 is a bounded flow fix; keep it bounded.

---

## What just landed on `feat/compose-wait-ux`

Commit **`2a0b37a`** (`feat(compose): hold a visible wait state across the Compose
arrival volley`), plus **`2a174bb`** (the chain's authorization envelope, written before
any A2 code) and this close-out commit.

Files: `static/app.js` (+308/−…), `ui_pages/selectors.py` (C-10 gated, +31),
`templates/index.html`, `tests/ux/regression/test_20260809_compose_wait_ux.py` (new, 290
lines), `tests/ux/regression/test_20260708_busy_states_and_chip.py` (2 tests tightened to
the new invariant), `docs/dev/blast-radius/compose-wait-ux.md` (new, 55 consumer rows in
three groups + 6 `## Deferred` entries, written **before** the first edit),
`docs/dev/RELEASE_ARC.md`, `docs/dev/epic-a-chain-design-corrections.md`.

What it does: the Compose panel used to become visible the instant `wizardGoTo(3)` ran —
which is when the background volley *starts*, not when it finishes — so the step read as
done while cards were still being rebuilt underneath. A2 adds `_holdComposingBusy` /
`_flushComposeSettleWaiters`, reusing the two existing idioms (`_setBusy` for the
app-wide banner, the analyze/generate streaming-panel block for the in-panel one) rather
than inventing a third. **The settle contract itself is unchanged**: `Compose.READY` and
`Compose.SETTLED` keep their exact values; the product reads the same two in-app signals
the selectors encode. The one guarantee added is **ordering** — the release runs
synchronously immediately before whichever DOM mutation makes `SETTLED` observable, so a
reader that sees `SETTLED` can never also see the overlay still up. Widening `SETTLED` to
mention the banner was considered and **rejected in writing** (it inverts the contract and
breaks `test_20260722_compose_bare_reload_settle.py`, which deliberately observes an
unsettled state).

Also: `_markComposeBgReload` gains an **optional** label so `#composeBgChip` names the leg
in flight (counter arithmetic, the `Math.max(0, …)` floor and the never-`="0"` invariant
are behaviourally byte-identical); skills pin/drop move to the word-button idiom keeping
the `.skill-pin` / `.skill-drop` classes; in-place Edit extends to every compose bullet
and survives approval.

**Honestly, what is NOT settled about it.** The adversarial review found 6 findings and 4
were fixed. **Finding 1's fix is defensive with unproven reachability**: the
`_composeApplicationId == null` branch of `loadComposition` is the only exit with no
`await` before it, so a hold raised after it would have nothing left to flush it — that
*mechanism* is confirmed by reading, but **no live path was found** where
`lastContextPath` is truthy while `_composeApplicationId` is null at that line. It is
guarded, and filed as an open question (**board item 64**), not claimed as an observed
failure. Separately, the **20 s cap** (`_COMPOSE_SETTLE_CAP_MS`) releases the wait state
whether or not the volley finished — a real, declared hole (`## Deferred` note 4), not an
absence of one.

Correction carried in the same commit: the ARC brief said 9 `_markComposeBgReload` call
sites. There are **12**; 9 was the count `fix/compose-unawaited-reloads` *fixed*,
preserved in `static/app.js`'s own comment and copied into the brief as though it were a
live total. `RELEASE_ARC.md` is corrected with the reason so it is not silently re-broken.

**Wiki: the ratchet is now ZEROED.** This close-out ran the wiki pass **widened to the
full `65b0f88`→HEAD delta** — 36 wiki-relevant paths, each either written into a page or
given a verified-no-edit line in `docs/wiki/log.md` — and advanced
`docs/wiki/.last_ingest_sha` to **`2a0b37a`**. Drift is **0**. Nine edited pages were then
grounding-audited by independent read-only auditors (author ≠ auditor preserved): 6
DRIFTED, 0 UNSUPPORTED, all six re-anchored on this branch, preferring symbol/function
cites over line numbers.

**From here this is a standing expectation, not a catch-up task:** the checkpoint sits at
the previous sprint's tip, so **each sprint's own slice IS the whole delta**, and *every*
sprint's closer runs its scoped pass and advances `.last_ingest_sha` to its own tip.
Cheap, honest, per-branch. If you skip it, you re-open the backlog that made the counter
useless in the first place (**board item 65**).

Quality gate: run **once, on the committed tree**, per the 2026-08-09 RELEASE_ARC
amendment. Its verbatim summary lines are in this session's closing report.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

`docs/dev/work/BOARD.md` is the authoritative live-item source (regenerate with
`python -m scripts.work_items board --write`; never hand-edited). Reproduced from the
board **as regenerated at this branch's tip** — not re-derived from memory.

**Open (1 in the flat section; 5 by frontmatter, the other 4 being epics and epic
children):**
1. **50** — C-7 and C-10 are enforced by Claude Code hooks only; the clauses do not
   travel to other agents or an extracted governance package.
- Also `status = "open"` but rendered under Epics: **9** (visual assets refresh),
  **19** (UX-flake umbrella epic), **36** (Epic A), and **20** — *the item this next
  branch closes*.

**Blocked (3):** items **3** ([HUMAN] GitHub toggles), **5** (grounding-score
persistence gap), **8** (Compose-time rewrite latitude dial).

**Deferred (7):** items **4, 7, 24, 25, 41, 42, 43** — all owner-gated or post-1.1.0.

**Watching (22 — three NEW this session):** items **2, 16, 18, 23, 46, 47, 48, 49, 51,
52, 53, 54, 55, 56, 58, 59, 60, 61, 62**, and **63, 64, 65 (new)**.
- **Item 63 is new** — `body.cb-busy` has **no CSS rule**, so `_setBusy` blocks no input
  anywhere in the app despite its "don't navigate away" copy. Confirmed twice
  (implementer and reviewer). `decision_owner = "user"`: blocking-vs-advisory is a
  product call, and the change touches every busy operation in the app.
- **Item 64 is new** — the `_holdComposingBusy` reachability question described above.
  Filed as a **question**, not a bug claim.
- **Item 65 is new** — the wiki freshness counter measures "files changed since
  checkpoint", not "coverage current", so a scoped pass can never honestly advance it and
  the backlog self-perpetuates. Zeroing it this sprint fixed **the instance, not the
  class**. Full analysis: `docs/dev/epic-a-chain-design-corrections.md` §11.11.
- **Item 62 is directly relevant to your gate run** —
  `tests/ux/regression/test_20260708_busy_states_and_chip.py` carries a **non-strict xfail
  pair** that legitimately flips between `1 xfailed, 1 xpassed` and `2 xfailed` across
  runs. **Either split is legal; do not chase it.**
- **Item 52 stays load-bearing** — the single gate run on the *committed* tree is what
  closes its window. Not optional.
- **Item 58 carries a C-11 clock** — a handoff amended after its `generated` stamp blocks
  the next session. It was filed as a *first* instance, so a note was compliant once. **A
  second instance owes a fail-closed mechanism, not another item update.** Concretely:
  once you commit this file's successor, do not edit it.

**Epics (6):** **19** (UX-flake umbrella, children 27–31, 57), **36** (Epic A, children
**20**, 34), **37/38/39/40** (epics B/C/D/E, blocked). Item **9** and **10** also render
with children.

Open-only count is **5** against the 10 ceiling — under the reduction-sprint threshold,
but the **watching** column has grown from 16 to 22 across three sprints. Worth the
owner's attention at the epic boundary, not a closer's unilateral call.

---

## Recurrences observed this session → guardrail authored

**1. The Epic A chain failed twice for the same reason: no authorization envelope.**
Recognized as a recurrence, not a first sighting — the second attempt reproduced the
first's failure shape exactly: a *compliant* agent stopping several times per sprint to
ask permission the plan had already granted, because nothing wrote down what the chain
authorized it to do without asking.
**Mechanism authored:** the authorization envelope at
`docs/dev/epic-a-chain-design-corrections.md` §11 — run vector, halt points, enumerated
flag stops, the delegation seam, the resume protocol — committed in **`2a174bb`**,
*before* any A2 code was written.
**Stated honestly:** §11.9 (the orchestrator never touches the working tree) is
**labelled unenforced** in the doc itself. No gate distinguishes a main-session edit from
a subagent's, so that clause is prose discipline, not a mechanism. §11.12 says so in the
document's own words rather than letting a reader count it as protection.

**2. Bare `path:line` cites rotted on two unrelated wiki pages in a single pass.**
Recognized as a recurrence and as a member of a **known class**: `docs/wiki/SCHEMA.md`
already *prefers* symbol cites precisely because line numbers rot, and this pass's
grounding audit returned 6 DRIFTED / 0 UNSUPPORTED — every one of them an anchor problem,
not a claim problem. `diagnostics-console` alone had three cite groups off by ~+48/+58
lines while the code they described was correct.
**No mechanism was authored, and this is surfaced rather than implied.** A lint that
rejects bare `path:line` cites in `docs/wiki/` in favour of symbol cites is the obvious
fail-closed gate — but it is a **new enforcement surface arriving at close-out**, which
the authorization envelope makes an explicit **flag stop** (§11.6.5) for the owner to
decide, not a closer's unilateral addition. It is stated plainly here and in
`docs/wiki/log.md`. **This is the open C-11 debt of this session**: a second pass finding
the same class again should not produce a third note.

**3. The wiki freshness counter measures the wrong thing for an incremental workflow.**
Recognized as a recurrence in the same sense as (2) — a first instance recognized as a
member of a known class of "the metric and the workflow disagree, and the honest agent
loses". A1b did the work correctly and *still* grew the counter, then correctly declined
the advance under C-12.
**No mechanism was authored.** What landed is an *instance* fix: the pass was widened to
the whole backlog and the checkpoint advanced, taking drift 36 → 0. Changing what the
gate **measures** is a redesign of an existing enforcement surface — the same §11.6.5
flag stop as (2). Filed as **board item 65** with `decision_owner = "user"`, and named
here so it is not mistaken for solved. **Filing it is not the mechanism, and this section
does not pretend otherwise.**

---

## What this branch should build

**Item 20 — hard-gate the Step-5 wizard rail on a frozen composition.** Board item 20
(`docs/dev/work/items/0020-legacy-generate-reachable-without-freeze.md`), authorized by
`docs/dev/RELEASE_ARC.md` §"Epic A", sprint A2's brief ("Item 20 (owner direction
captured at march sign-off): hard-gate the Step-5 wizard rail on frozen composition").

The shape of the defect, as **filed** (this is the item's claim, not yet your evidence):
`_wizardReachable` in `static/app.js` gates Step 5 on having a context path and nothing
more, so a user who analyzes and then jumps straight to Step 5 via the rail has no
`approved_composition`; `_frozen_composition` in `blueprints/generation.py` returns `None`
and the **legacy full-LLM Sonnet `generate()` path fires** — the path the
frozen-composition re-architecture was meant to retire for corpus-mode users.
`_renderGenerateStepCopy` already swaps Step 5's copy between "legacy" and "frozen"
variants *because both paths are live today*.

1. **FIRST COMMIT: the diagnosis dossier, not the fix.** Write
   `docs/dev/diagnosis/step5-rail-frozen-gate.md` from
   `docs/dev/diagnosis/TEMPLATE.md`, with a **filled-in `## Observed`** section carrying a
   real citation — a driven run, a `path:line` you verified at this tip, a probe output, or
   a test that fails without the change. The `require-evidence-before-fix` hook **will
   block every production edit** until it is there, and `scripts/enforcement/evidence.py`
   additionally rejects an `## Observed` bullet with no run id / `path:line` / quoted
   command / fenced artifact. **The line numbers in item 20's `refs` are from 2026-07-28
   and A2 moved ~308 lines of `static/app.js` — treat them as stale and re-derive.**
   Reproduce the skip-Compose path yourself; do not inherit the mechanism from the item.
2. **Then decide the flow, and write the decision down before coding it.** The owner's
   direction is captured (hard-gate, corpus-mode users go through Compose), but *hard-gate*
   still admits several shapes: rail step disabled with a reason, rail click intercepted
   with a redirect to Compose, or the server refusing and the client explaining. Item 20's
   own body records the alternatives that were considered. Pick one, say why, and note what
   happens to a **legacy (non-corpus) user** who has no Compose step at all — that case is
   not covered by "everyone goes through Compose" and is the obvious way to break existing
   users.
3. **`static/app.js`** — `_wizardReachable` and `_renderGenerateStepCopy`. Once Step 5 is
   unreachable without a frozen composition, the "legacy" copy variant may be dead; if you
   remove it, remove it deliberately and say so, and check the UX tier for tests that
   assert the legacy copy.
4. **`blueprints/generation.py`** — `_frozen_composition` and its caller. Decide whether
   the server-side fallback to `generate()` stays as defence-in-depth or becomes an error.
   If any route changes, `_safe_username()` / `_within()` / `secure_filename()` still apply
   and `route-security-lint` enforces it.
5. **C-10 check before the first edit.** If your change touches `ui_pages/selectors.py` or
   any other gated surface in `scripts/enforcement/blast_radius.py`, you owe
   `docs/dev/blast-radius/step5-rail-frozen-gate.md` with a `## Consumers` section naming
   that surface **first**. A2's dossier (`docs/dev/blast-radius/compose-wait-ux.md`) is a
   good worked example of the expected depth.
6. **Tests.** A UX-tier regression that drives analyze → rail-jump to Step 5 and asserts
   the gate holds, plus whatever server-side test pins the `generate()` path not firing.
   A1b's lesson applies: **a targeted green says nothing about the files it did not
   execute** — run the compose + generate UX modules as a group.
7. **Close-out (steps 0–3 only).** Pre-close sweep, the **scoped** wiki pass for this
   branch's own diff with `.last_ingest_sha` advanced to your tip, work-item 20 moved to
   `closed` **with a `verified_by` artifact** (the C-11 closure bar; `board --write`
   afterwards), the handoff, the commit, then **one** `python -m scripts.gate` run on the
   **committed** tree. **Then STOP.** No push, no PR, no merge, no prune.

Scope is bounded to **item 20 / the A2 brief's final line in `RELEASE_ARC.md` §"Epic A"**.
Do not expand beyond what is listed there.

---

## First move

**This chain does not re-run the plan ceremony.** One `ExitPlanMode` approval covers all
of Epic A's sprints and the approved plan file is **FROZEN** — do not rewrite it, do not
re-enter plan mode, do not ask for a new approval click. This section deliberately departs
from the template's default "write a plan and show it to the user" wording, on the owner's
2026-08-08 amendment.

Instead, in order:

1. Verify the pointer that brought you here with
   `python scripts/check_handoff_pointer.py "<pointer line>"`, then
   `python scripts/verify_doc_template.py docs/dev/handoffs/compose-wait-ux.md
   docs/dev/AGENT_HANDOFF_TEMPLATE.md --event consumed --agent <your-agent-id>`. A
   failure at either step is your **first output** and you **STOP** (charter C-9).
2. Read `docs/dev/handoffs/docs-epic-a-wave-orchestration-design.md` **in full**, then
   `docs/dev/epic-a-chain-design-corrections.md` §11.
3. `git checkout feat/compose-wait-ux && git checkout -b fix/step5-rail-frozen-gate` —
   off the A2 tip, **not** `main`.
4. Write `docs/dev/diagnosis/step5-rail-frozen-gate.md` with a filled-in `## Observed`
   **before any production edit**. **Do not code first.**

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
