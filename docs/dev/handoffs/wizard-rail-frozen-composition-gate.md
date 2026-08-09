<!-- provenance: schema=1 session=aaa7857e-4732-4daf-90f7-97315fac91f9 branch=fix/wizard-rail-frozen-composition-gate commit=3e2b8a5 actor=amodal1 agent=anthropic/claude-opus-5 generated_at=2026-08-09 -->

# Handoff — Epic A sprint A3: `feat/role-summary-drafting`, the largest sprint in the epic

**Branch to create:** `feat/role-summary-drafting` (branch off `fix/wizard-rail-frozen-composition-gate`)
**Base branch:** `fix/wizard-rail-frozen-composition-gate` — the item-20 tip. **NOT `main`.**

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
> delegation seam (the orchestrator never touches the working tree; fresh agents per
> sprint — implementer, adversarial refuter, closer), and the resume protocol all live
> there. **Read §11 in full; it is not restated here** and nothing in this handoff
> overrides it.
>
> **§11.9's gate rules are not optional and cost this chain a sprint's tail already.**
> The quality gate is **step 5 and belongs to the ORCHESTRATOR**. A subagent must
> **never** run `python -m scripts.gate` — a closer's gate died with the agent on A2.
> Launch it **detached with a direct redirect (`> file 2>&1`)**, never `| tee`: `tee`
> dying with the Bash wrapper while the gate ran on headless produced two false
> mechanisms in a row on A2, one command short of killing a live run. And `kill -0
> <pid>` is **invalid here** — Git Bash tracks MSYS pids, not Windows pids, so a waiter
> built on it returns instantly and lies; poll with `tasklist` / `Get-CimInstance`.
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
merges — **six branches**, because item 20 took its own `fix/*`.
**Sequencing rule:** strictly sequential — one sprint, one branch, one session, each
branching off the previous sprint's tip.
**Blocked until this stream lands:** epics B (render/ATS), C (diagnostics), D (docs IA),
E (release) — board items 37/38/39/40, all `blocked`.

- ~~`feat/corpus-polish` (A1a)~~ ✓ — corpus panel reordered to Summary → Work Experience
  → Education → Skills; rows compacted; role-card order fixed. Commit `7c15c2e`.
- ~~`fix/experience-soft-retire` (A1b)~~ ✓ — retire now happens at the *role* level, not
  only its bullets, so a 0-bullet role stops silently no-op'ing; migration `0016` +
  `Experience.is_active` + the unfiltered-consumer sweep. Commit `5474763`.
- ~~`feat/compose-wait-ux` (A2)~~ ✓ — the "Composing…" arrival wait gate, the labelled bg
  chip, word-button skills pin/drop, in-place Edit on every compose bullet. Commit
  `2a0b37a`.
- ~~`fix/wizard-rail-frozen-composition-gate` (item 20)~~ ✓ ← **just closed; this
  handoff's branch.** The Step-5 rail is a hard gate, on one predicate shared by client
  and server. Commit `3e2b8a5`.
- **`feat/role-summary-drafting` (A3)** ← **next: this is what you build.** The
  `draft_experience_summaries` call, end to end.
- `feat/prior-apps-pipeline` (A4) ← last sprint of the epic. Do **not** start it here.

**Note the branch name.** The A2 handoff predicted `fix/step5-rail-frozen-gate`; the
branch that exists is **`fix/wizard-rail-frozen-composition-gate`**, and its dossier and
blast-radius files carry that slug. Branch off the name that exists, not the predicted one.

**A3 is the largest sprint in Epic A. Say it to yourself before you scope your day.** It
is a **net-new LLM call end-to-end** — prompt, grounding widening, `PROMPT_VERSION` bump,
telemetry, pricing, stubs, UI surface, and an eval fixture — where A1/A2/item-20 were each
a bounded change to existing machinery. `RELEASE_ARC.md`'s own session-model table pins A3
to **Opus** for exactly this reason ("new LLM call end-to-end: prompt, eval, telemetry").
If a sprint in this chain is going to need a mid-sprint handoff, it is this one; plan for
the durable-writes discipline (C-8) accordingly rather than discovering it at 80%.

**Do NOT start on this branch:** anything in A4 (removing the Tailor applications panel,
rewriting `_renderPipelineRow`'s `activate()`), and none of the three items this branch
filed (66, 67, 68) — each is `watching`, two are `decision_owner = "user"`, and none is
authorized work.

---

## What just landed on `fix/wizard-rail-frozen-composition-gate`

Commit **`3e2b8a5`** (`fix(wizard): hard-gate the Step-5 rail on a composition the server
will assemble`) plus this close-out commit. Gate: **run once on the committed tree** per
the 2026-08-09 RELEASE_ARC amendment — `gate: all steps passed.`, 2393 non-UX + 146 UX
passed, **0 rerun markers**.

Files: `hardening.py` (new public `frozen_composition_doc`), `blueprints/generation.py`,
`blueprints/applications.py`, `static/app.js`, `tests/ux/regression/test_20260809_wizard_rail_frozen_gate.py`
(new), `tests/ux/regression/test_20260707_generate_surface_download.py`,
`tests/test_application_routes.py`, `tests/test_composition_summary.py`, `ui_pages/base.py`,
`docs/dev/diagnosis/wizard-rail-frozen-composition-gate.md`.

**What it actually does, and it is not the obvious thing.** The rail was gated on nothing
but a context path, so a click that skipped Compose reached Generate and the retired
full-LLM `generate()` fired. The obvious fix — gate on the client's `_compositionFrozen` —
was **written and then refuted** by the adversarial reviewer: the client asked only "is
`approved_composition` a dict?" while `/api/generate` also requires corpus-mode and a
document with content, so a **contentless freeze** still opened the rail under Step-5 copy
promising "no AI variation" over a run the server then handed to the LLM. Resolved as **one
predicate with one implementation**: `hardening.frozen_composition_doc` (the former
`_frozen_composition` body, moved verbatim), called from all three seams — the generate
gate, `_pre_generate_hydration`'s new `has_frozen_composition`, and the `/composition`
freeze response's `frozen` field (which was returning a bare `bool(freeze)` and by itself
still opened the rail). It lives in `hardening.py` because `applications.py` cannot import
`generation.py` (cycle via `templates.py`), because that module owns the `ContextSet`
contract, and because it is pure dict reads — **no LLM call added, C-6 intact**.

**The gate is deliberately TIGHTER than "Compose was completed."** A candidate whose
analyze-time `career_corpus` snapshot is empty is locked out of Step 5, because that run
*would* reach the LLM path and the determinism claim behind the rail would be false. The
implementer had originally chosen the weaker predicate on purpose to protect that
candidate; the reversal is recorded in the dossier rather than silently overwritten. They
are not walled in — steps 1–4 stay reachable off `lastContextPath`, asserted in the new UX
test rather than assumed.

**Honestly, what is NOT closed.** Three surfaces were **filed, not fixed**, and reading
item 20 as "the legacy path is gone" would be wrong:

- **Item 66 — the sticky-stale frozen flag.** Freeze → back to Compose → edit; the
  debounced autosave omits `freeze`, so `_compositionFrozen` stays `true` over a stale
  snapshot. **Generation is unaffected** — the server re-reads `approved_composition` from
  disk and never consults the client flag — so this is a UX-honesty gap, not a correctness
  one. Pre-existing; item 20 made the flag load-bearing where it previously only chose copy.
- **Item 67 — `/api/generate` still reaches legacy `generate()` by direct POST**, outside
  the rail. Deliberate: the rail is the gate, the server fallback is the floor, and two
  committed tests pin the fallback (a zero-active-role candidate legitimately needs it).
- **Item 68 — the Step-5 lock reason names Compose only.** Right for a contentless frozen
  document; wrong for an empty analyze-time `career_corpus`, where recovery is outside the
  rail entirely. Distinguishing them needs the client to learn *why* the server refused — a
  payload-shape change, not a copy edit.

**Also worth a reviewer's eye, carried forward from the commit message:** three test
fixtures gained a corpus snapshot rather than only new assertions — they lacked
`career_corpus` and would have gone silently false under the tightened predicate. Each
carries a comment saying why it is load-bearing. A fixture edited to keep a test green is
exactly the move that can hide a regression.

**Wiki: the checkpoint is live and each sprint now advances it.** This close-out ran the
scoped pass mechanically — `git diff --name-only 2a0b37a HEAD` (29 files) filtered through
`scripts/wiki_relevance.py:is_wiki_relevant`, leaving **4**: `hardening.py`,
`blueprints/applications.py`, `blueprints/generation.py`, `static/app.js`. Four pages
edited (`corpus-to-output-reach`, `frontend-wizard`, `context-set-contract`,
`route-surface`), four given explicit **verified-no-edit** lines in `docs/wiki/log.md`
(`pipeline-stages`, `document-rendering`, `deterministic-llm-boundary`, plus the
`approved_composition`-as-data group). `docs/wiki/.last_ingest_sha` advanced `2a0b37a` →
**`3e2b8a5`**; **drift 4 → 0**. Every cite added is a **symbol** cite, never a bare
`path:line`. The pages were written by the closing context and have **no independent
auditor** — the orchestrator runs the grounding audits; that list of four is the audit list.

**From here this is a standing expectation, not a catch-up task:** the checkpoint sits at
the previous sprint's tip, so **your sprint's own slice IS the whole delta**. Run the
scoped pass and advance `.last_ingest_sha` to your tip. If you skip it, you re-open the
backlog that made the counter useless in the first place (**board item 65**).

**Pyright diagnostics in this harness are stale against the working tree — do not spend
verification effort on them.** Three were surfaced and each verified **spurious** this
session: `_BUSY_COMPOSING`, an `Output` import, and `frozen_assemblable`. **mypy is the
gate, and it is clean.** If the editor flags something in a file this chain has touched,
check `mypy` before treating it as real.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

`docs/dev/work/BOARD.md` is the authoritative live-item source (regenerate with
`python -m scripts.work_items board --write`; never hand-edited). Reproduced from the
board **as regenerated at this branch's tip**, and the counts below are the **frontmatter**
counts computed over all 68 item files — not the board's flat-section counts, which exclude
items rendered under an epic. **47 items are still open in some status; 6 of those are
epics.**

**Open (4):** items **9** (visual-assets refresh, under epic 39), **19** (UX-flake umbrella
epic), **36** (Epic A), **50** (C-7/C-10 are enforced by Claude Code hooks only; the clauses
do not travel to other agents or an extracted governance package).

**Blocked (8):** items **3** ([HUMAN] GitHub toggles), **5** (grounding-score persistence
gap), **8** (Compose-time rewrite latitude dial), **10** (the v1.1.0 release cut, under epic
40), and the four blocked epics **37 / 38 / 39 / 40**.

**Deferred (7):** items **4, 7, 24, 25, 41, 42, 43** — all owner-gated or post-1.1.0.

**Watching (28 — three NEW this session):** items **2, 16, 18, 23, 30, 34, 46, 47, 48, 49,
51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65**, and **66, 67, 68 (new)**.

- **Items 66, 67, 68 are new** — the three item-20 deferrals described above. 66 is
  `decision_owner = "agent"`; 67 and 68 are `"user"`, because each turns on a product call
  (what a post-freeze edit *means*; whether the server floor should ever become a `409`;
  whether the honest-but-noisy lock message beats a structured reason code).
- **Item 34 is YOURS this sprint** — the corpus blueprints' `_get_client` is never patched
  in the UX harness, a real billed-API risk. `RELEASE_ARC.md`'s A3 brief folds it in
  explicitly ("extend the UX-harness `_get_client` autouse patch to the corpus blueprints").
  It is `watching` and parented to epic 36; close it with a `verified_by` artifact when you
  land the patch.
- **Item 62 is directly relevant to your gate run** —
  `tests/ux/regression/test_20260708_busy_states_and_chip.py` carries a **non-strict xfail
  pair** that legitimately flips between `1 xfailed, 1 xpassed` and `2 xfailed` across runs.
  **Either split is legal; do not chase it.**
- **Item 52 stays load-bearing** — the single gate run on the *committed* tree is what
  closes its window. Not optional.
- **Item 58 carries a C-11 clock** — a handoff amended after its `generated` stamp blocks
  the next session. It was filed as a *first* instance, so a note was compliant once. **A
  second instance owes a fail-closed mechanism, not another item update.** Concretely: once
  you commit this file's successor, do not edit it.
- **Item 65 is the wiki-counter class** — zeroing it on A2 fixed the instance, not the
  class. Your sprint's honest advance is what keeps the instance fixed.
- **Item 16 will bite the eval half of your sprint** — `--suite real` is non-functional (no
  fixtures exist). A3's brief calls for a **targeted corpus-mode fixture** precisely because
  `--suite synthetic` does not cover corpus-mode drafting; do not assume a real-suite
  baseline exists to compare against.

**Epics (6):** **19** (UX-flake umbrella, children 27–31, 57), **36** (Epic A, children
**20 — now closed** and **34**), **37 / 38 / 39 / 40** (epics B/C/D/E, blocked).

Open-only count is **4** against the 10 ceiling — under the reduction-sprint threshold. The
**watching** column, however, has grown 16 → 22 → 25 → **28** across four sprints, and
three of this session's own additions are in it. That trend is worth the owner's attention
at the epic boundary; it is not a closer's unilateral call, and no closer in this chain has
had standing to act on it.

---

## Recurrences observed this session → guardrail authored

**1. Bare `path:line` cites rotted on two unrelated wiki pages in a single A2 audit pass.**
Recognized as a recurrence and as a member of a **known class**: `docs/wiki/SCHEMA.md`
already *prefers* symbol cites precisely because line numbers rot, and A2's audit returned
6 DRIFTED / 0 UNSUPPORTED — every one an anchor problem, not a claim problem, on two
unrelated pages in one pass. Re-anchoring to today's line numbers just resets the clock.
**No mechanism was authored, and this is surfaced rather than implied.** A lint rejecting
bare `path:line` cites in `docs/wiki/` is the obvious fail-closed gate, but it is a **new
enforcement surface**, which §11.6.5 of the authorization envelope makes an explicit **flag
stop** for the owner — not a closer's addition. What this session did instead is
**mitigation, not a mechanism**: every cite added in its wiki pass is a symbol cite, and
`docs/wiki/log.md` says so. **This is now the second consecutive session to file this same
debt with no gate. A third should not produce a third note.**

**2. The wiki counter measures "changed since checkpoint", not "coverage current."**
Recognized as a recurrence in the same sense — the metric and the workflow disagree, and
the honest agent loses. **A2 zeroed the instance; the class is open.** **No mechanism was
authored.** Changing what the gate measures is a redesign of an existing enforcement
surface — the same §11.6.5 flag stop. Tracked as **board item 65**, `decision_owner =
"user"`. **Filing it is not the mechanism, and this section does not pretend otherwise.**

**3. A subagent's gate run died with the agent, and `| tee` truncated two more.**
Recognized as a recurrence within a single sprint — A2 hit it **twice**, and the second
occurrence produced a *false mechanism* ("memory pressure is killing the gate") that came
one command short of killing a live run while reclaiming what were believed to be orphaned
workers. **Mechanism authored:** `docs/dev/epic-a-chain-design-corrections.md` §11.9 now
states that the gate is the **orchestrator's**, is launched **detached with `> file 2>&1`**
and never `| tee`, is never run by a subagent, and that **`kill -0` is invalid on Windows
pids**. **Labelled unenforced, as C-11 requires:** that is prose in the authorization
envelope, not a gate. No mechanism distinguishes a main-session command from a subagent's,
so nothing fails closed if a future agent runs the gate itself; §11.9 says so in the
document's own words rather than letting a reader count it as protection.

---

## What this branch should build

**A3 — role-summary JD-fitting**, authorized by `docs/dev/RELEASE_ARC.md` §"Epic A", the
A3 brief. **Read that brief directly**; the list below sequences it and flags the traps,
it does not replace it.

1. **The new call: `draft_experience_summaries` in `analyzer.py`.** **Batched — ONE call
   for all included roles, never one call per role.** That is the brief's wording and it is
   the load-bearing constraint (`analyzer.py` is the only home for LLM calls; the
   deterministic modules are off-limits). `recommend_experience_summaries` stays the
   *selector* and is not what you are building.
2. **Grounding.** Widen `hardening.assemble_source_union` to match, the way the other three
   Compose drafting calls (`draft_positioning_summary`, `draft_gap_fill_bullets`,
   `suggest_skills`) already are — prompt-side source block AND the deterministic metric,
   or the grounding metric will flag legitimate material. `hardening.py` is a **C-10 gated
   surface** and this branch will also touch it: you owe
   `docs/dev/blast-radius/role-summary-drafting.md` with a `## Consumers` section **naming
   that path**, written **before the first edit**. Item 20's own dossier is a recent worked
   example.
3. **`PROMPT_VERSION` bump in the SAME commit as the prompt.** Hard constraint below; eval
   telemetry mis-attributes without it.
4. **The new-call-kind checklist — all four legs, none optional.** `EXPECTED_CALL_KINDS` in
   `tests/test_call_kind_telemetry.py`; a never-logged-kind probe; a `tests/ux/stubs.py`
   stub; pricing keys. Board items 21 and 22 are the history of what each missing leg costs
   — a call invisible to telemetry, and four call kinds that were never logged because no
   test ever exercised them.
5. **Item 34, folded in by the brief:** extend the UX-harness `_get_client` autouse patch
   to the **corpus** blueprints. `install_llm_stubs` patches four blueprints and not those,
   which is a real billed-API risk, not a stub-tidiness issue. Close board item 34 with a
   `verified_by` artifact when it lands.
6. **UI parity in Compose:** a per-role summary card — edit in place, keep/reject,
   save-to-corpus as a pending intro variant. Note **board item 59**: a role card already
   shows *two* different summary editors (the legacy denormalized `Experience.summary` and
   the canonical variants section). Do not add a third surface without deciding, in
   writing, how it relates to those two.
7. **Eval.** Corpus-mode drafting is **not** covered by `--suite synthetic` — add a
   targeted fixture, baseline before, run after, and log it in `evals/TUNING_LOG.md`. Real
   Anthropic spend: surface the estimate to the user before running. See item 16 above.
8. **Close-out (steps 0–3 only).** Pre-close sweep; the **scoped** wiki pass for this
   branch's own diff with `.last_ingest_sha` advanced to your tip; board items 34 (and any
   others you close) moved with a `verified_by` artifact and `board --write` afterwards; the
   handoff for A4; the commit. The gate is the **orchestrator's**, run detached on the
   committed tree — **you do not run it**. **Then STOP.** No push, no PR, no merge, no prune.

Scope is bounded to **`RELEASE_ARC.md` §"Epic A" sprint A3**. Do not expand beyond what is
listed there.

---

## First move

**This chain does not re-run the plan ceremony.** One `ExitPlanMode` approval covers all of
Epic A's sprints and the approved plan file is **FROZEN** — do not rewrite it, do not
re-enter plan mode, do not ask for a new approval click. This section deliberately departs
from the template's default "write a plan and show it to the user" wording, on the owner's
2026-08-08 amendment.

Instead, in order:

1. Verify the pointer that brought you here with
   `python scripts/check_handoff_pointer.py "<pointer line>"`, then
   `python scripts/verify_doc_template.py docs/dev/handoffs/wizard-rail-frozen-composition-gate.md
   docs/dev/AGENT_HANDOFF_TEMPLATE.md --event consumed --agent <your-agent-id>`. A failure
   at either step is your **first output** and you **STOP** (charter C-9).
2. Read `docs/dev/handoffs/docs-epic-a-wave-orchestration-design.md` **in full**, then
   `docs/dev/epic-a-chain-design-corrections.md` §11 — **§11.9 in particular**, before you
   plan any gate run.
3. `git checkout fix/wizard-rail-frozen-composition-gate && git checkout -b feat/role-summary-drafting`
   — off the item-20 tip, **not** `main`.
4. Write `docs/dev/blast-radius/role-summary-drafting.md` with a `## Consumers` section
   naming `hardening.py` **before any edit to it**. **Do not code first.**

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
