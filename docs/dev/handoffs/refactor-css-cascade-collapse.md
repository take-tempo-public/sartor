<!-- provenance: schema=1 session=88ee0376-1e46-4f1f-b1a3-d7cca4290ceb branch=refactor/css-cascade-collapse commit=248703b actor=amodal1 agent=anthropic/claude-opus-4-8 generated_at=2026-07-18 -->

# Agent handoff: `refactor/css-cascade-collapse`

**Branch to create:** `chore/config-drift-batch` (branch off `main`) — step 5 of the
numbered sequence in `RELEASE_ARC.md`. Confirm with the owner before starting, per this
repo's one-branch-per-session convention.
**Base branch:** `main`

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

**Stream:** step 4 of `RELEASE_ARC.md`'s "v1.1.0 close-out — reconciliation" numbered
sequence — the first branch in a while that IS in that sequence (the previous four were
out-of-sequence ad-hoc fixes).
**Sequencing rule:** strictly sequential — one branch at a time (Key decision 10: no
conductor/waves until further notice).
**Blocked until this stream tags:** nothing downstream was gated on this step.

- ~~`docs/v110-plan-reconciliation`~~ ✓ — step 1
- ~~`fix/plan-approval-hook-scope`~~ ✓ — step 2
- ~~`fix/handoff-pointer-verification`~~ ✓ — out-of-sequence
- ~~`fix/compose-unawaited-reloads`~~ ✓ — step 3
- ~~`docs/handoff-template-relative-link`~~ ✓ — out-of-sequence
- ~~`fix/capture-screenshots-welcome-modal`~~ ✓ — out-of-sequence, unblocked PX-51's
  screenshot gate
- **`refactor/css-cascade-collapse`** ← this branch, step 4 (PX-51)
- `chore/config-drift-batch` (PX-47) ← step 5, the next numbered step
- `chore/hook-dispatcher` (PX-37 + kit-adoption commitment 3) ← step 6; touches the
  enforcement surface directly — do not start it on this branch

Do not treat this handoff as authorizing anything beyond `chore/config-drift-batch`, and
confirm even that with the owner first.

---

## What just landed on `main`

Nothing yet — `main` is still at `248703b` (merge of `fix/capture-screenshots-welcome-modal`).
This branch has not merged; that is pending the owner's merge confirmation.

**What this branch did (PX-51 — `static/style.css` duplicate-cascade collapse).**
`static/style.css` **4386 → 4258 lines (−128)**. Sixteen duplicate selector-group pairs
collapsed to exactly one definition each, across **three** separate source regions (not
one contiguous block, as both prior estimates assumed):

1. **Compose cluster** — `.compose-row.pinned` / `::before` / `.excluded` (early copies
   at ~1283-1302 deleted; kept copies at ~2640-2654).
2. **Phase D.2 tabs** — `.top-tabs`, `.top-tab-btn`, `:hover`, `.active` (early copies at
   ~1379-1409 deleted; kept copies in the restyle section).
3. **Primary layout/panels/forms/buttons** — `.cb-main`, `.cb-panel`, `.panel-header`,
   `.panel-header::after`, `.panel-body`, `.cb-btn` (+3 pseudo-states),
   `input,select,textarea`, `input:focus` (early copies at ~167-336 deleted).

**The method, and why it matters for anyone touching this file again.** In every pair the
**later ("restyle") copy was kept** — its values are what actually render for every
contested property — and any property the later copy never redeclares was **carried
forward** into the kept rule before the earlier copy was deleted. That carry-forward set
is the whole risk surface; the highest-stakes members were `.panel-header::after`'s
`content: '▾'` (a pseudo-element generates no box at all without `content`, so a naive
deletion silently removes the panel-collapse chevron) and `input,select,textarea`'s
`flex: 1; min-width: 0` (the app-wide `.form-row` layout rule).

**Verification was empirical, not argued.** A live `getComputedStyle` oracle was captured
against a running dev server **before** any edit and again after, covering every flagged
property across all 16 selectors — **byte-identical both times**, plus a manual
click-through (tabs, hover, panel collapse/expand, form modal) that was visually
indistinguishable. Two findings from that oracle are worth keeping:
- `.compose-row.pinned`'s `box-shadow: var(--edge-top)` survives on **specificity**, not
  source order (a 2-class selector beats the later 1-class base rule regardless of file
  position). Confirmed by rendered alpha `0.043` matching `--edge-top` (`0.045`, after
  float→byte rounding) rather than the base rule's `--edge-soft` (`0.025`). A
  source-order-only reasoner would have wrongly deleted it as dead.
- The `.top-tab-btn` `border-radius` / `:hover` `background` pair — the exact properties a
  prior session wrongly called dead — were re-confirmed live.

**Two pre-existing, unrelated bugs found during the census and deliberately NOT fixed**
(both behave identically before and after the collapse; fixing either would have turned a
provably behavior-preserving refactor into a behavior change, defeating the oracle):
`.cb-panel`'s collapse-animation easing appears already fully overridden, and a mobile
`@media (max-width:768px)` `.panel-body` padding override appears already shadowed. Both
are filed as ledger items 16 and 17.

**Wiki refresh rode along (owner-authorized).** The `wiki_freshness` gate was **already
failing at the branch point** (76 files ≥ 75 threshold; it crossed 70 → 76 during the
*previous* branch's merge). Ran `/wiki-self-update`: a deterministic cite-scan found
**316 cites across 38 pages, 86 into changed files, all 86 still valid — zero drift**, so
the pass was one page (`context-set-contract`, gaining `write_context_atomic` +
`context_transaction` coverage). Auditor: 10/10 SUPPORTED, 0 DRIFTED, 0 UNSUPPORTED, one
misplaced `[synthesis]` tag caught and removed. `.last_ingest_sha` advanced
`9f3c800` → `248703b`; gate now green.

**Gate:** `ruff check .` ✓ · `ruff format --check .` ✓ (313 files) · `mypy .` ✓ (328 files,
0 issues) · `pytest -m "not ux"` **2027 passed, 1 skipped** · `pytest -m ux` **120 passed**.
The only failure across the whole run was `test_restore_scroll_y_stale_invocation_overwrites_later_scroll`
— **investigated, not waved off**: it failed with *two different* assertion messages on
consecutive runs, and one of them ("page too short to scroll") was exactly what editing
`.cb-main`'s `min-height` could plausibly cause. Settled by a controlled baseline A/B
(backup → `git checkout HEAD -- static/style.css` → re-run 3× → **1 failed / 2 passed on
unmodified baseline** → restore, md5-verified). Not attributable to this branch; filed as
a data point on the existing scroll-flake ledger item.

**Note on `agent=` in this file's stamp:** the CSS work and verification were executed
under `anthropic/claude-sonnet-5`; the owner switched the session to
`anthropic/claude-opus-4-8` during close-out, which is what authored this handoff. Stated
rather than inferred, per `prov/SPEC.md` §1.

---

## Carried-forward observations (cumulative open ledger — render the full still-open subset)

Full detail for every item lives in `docs/dev/RELEASE_CHECKLIST.md`'s Carry-forward ledger
(`#### Open`); this is the required one-line-each mirror. **18 open** (verified by direct
`grep -c '^- \[ \]'` over that subsection) — this branch resolved none and added three
(16, 17 — pre-existing CSS bugs surfaced by its own census; 18 — a merge-guard defect
surfaced by its own close-out).

1. `--reruns 2` on the `ux` CI tier is a masking policy — it hid a chronically broken test
   (64% fail rate) for 11 CI runs. Underlying bug fixed; the retry-policy question is
   deliberately left open pending a real post-fix CI sample.
2. The quality gate is unrunnable by an agent in one shot — a governance hole, worked
   around by hand again this branch (see the note below this list).
3. **[HUMAN/OWNER]** wire CodeQL as a *required* status check on `main` — admin-only
   Settings toggle, not automatable.
4. `test_corpus_reload_preserves_scroll_position` (and siblings) — modes B/D root-caused
   and FIXED (Chip 3); mode C (~17% under saturation) is a separate, unfixed hazard. **New
   data this branch:** a controlled baseline A/B cleared the CSS refactor of a related
   failure, and surfaced a `before == 0` signature not in the A/B/C/D taxonomy for that
   test, appearing *without* deliberate CPU saturation.
5. `chore/scrub-local-eval-paths` parked branch — 2 commits, unmerged, gate
   re-verification incomplete (not failed); owner decision: leave parked.
6. Wordmark sweep owed on `docs/wiki/` + `docs/dev/reviews/` (~107 files) — deliberately
   deferred, opportunistic only, do not schedule.
7. 3 `loadComposition()` sites excluded from the `compose-unawaited-reloads` fix
   (`static/app.js`) — materially different call-path shapes; needs its own scoped design
   pass, not a mechanical `await`.
8. PyPI wheel packaging — RESOLVED-PENDING-PUBLISH; open only for the still-blocked
   `[HUMAN]` Trusted Publisher / GHCR prerequisite.
9. In-app rendered citation viewer — deliberately deferred; build only if real friction
   shows up.
10. Grounding/hallucination metric calibrated layers (L1/L2) — labels + scorer persistence
    fixed; the calibration itself is still owner-gated.
11. Agent-coding-practices kit-adoption staged commitments — mypy `--strict` ratchet,
    gate-hardness ratchet-then-block, skills/hooks packaging coherence.
12. 2026-07 efficiency review PX-37..PX-56 aggregate — **PX-51 landed this branch (8 of 13
    now land); 5 remain:** PX-37, PX-39, PX-44 (refactor half), PX-46, PX-47.
13. UX round-2 remediation — Wave A landed; the design-heavy remainder is registered as the
    UX Cohesion Epic, unscheduled.
14. `docs/governance/enforcement.md` (and several memory files) cite "charter W-1" as an
    existing clause — it still does not exist, only an intro-line mention. Needs an
    owner-directed amendment ceremony.
15. `scripts/capture_screenshots.py` has zero automated/periodic coverage, which let three
    independent staleness bugs accumulate silently over ~7 weeks. Needs an owner decision
    on cadence vs LLM spend.
16. **NEW** — `.cb-panel`'s collapse animation likely already snaps instead of easing: its
    `transition` is fully contested and the restyle copy's value already wins, replacing
    the `grid-template-rows 0.35s ease`. Independent of the PX-51 collapse. Owner decision:
    restore the easing or accept the snap.
17. **NEW** — a mobile `@media (max-width:768px)` `.panel-body` padding override is already
    shadowed/dead (same-specificity, earlier in source than an unconditional rule; media
    conditions don't affect source-order tie-breaking). Needs verification on a real narrow
    viewport, then an owner decision.
18. **NEW, AND IT WILL BLOCK YOU TOO** — `block-merge-to-main`'s wiki arm evaluates the
    **pre-merge** worktree, so a branch that refreshes the wiki cannot be locally merged:
    standing on `main`, the guard reads main's still-stale `.last_ingest_sha` and blocks,
    even though completing that merge is what makes the wiki fresh. No escape hatch by
    design (`CLAUDE_CONFIRM_MERGE=1` explicitly does not cover it). Never hit before
    because the only prior checkpoint advance reached `main` on its first-parent line (a
    GitHub PR merge), so this local guard never fired — verified, not assumed. **If you
    run a wiki pass, expect this wall at close-out and read the ledger item first.**

**Reduction sprint is overdue and getting worse** — the ~8–10 ceiling has been exceeded
across multiple handoffs and this branch pushed it 15 → 18. Items 5, 6, 9 and possibly 3
look cheap to clear in one pass. Strongly consider scheduling the sprint before the
v1.1.0 tag rather than after another feature branch.

**New evidence on ledger item 2 (worth reading before you run the gate).** Background
commands were killed repeatedly this session at wildly inconsistent points — 58% through
pytest once, then *instantly* on an identical retry, then at 9%. A long-running Flask dev
server that had been stable for a long time was killed at the same moment as a
freshly-started gate run, which points at an **environment-wide event** (session/shell
recycle?) rather than the per-command wall-clock ceiling the ledger previously inferred.
**Practical advice:** don't retry the full gate hoping it survives; chunk from the start
(`split -n l/8` over `tests/test_*.py`, ~15 files per chunk, plus `tests/ux/` by
subdirectory) — and note that **foreground** Bash calls survived reliably when identical
backgrounded ones were killed.

---

## What this branch should build

This handoff records `refactor/css-cascade-collapse`'s close-out. The next numbered step:

**`chore/config-drift-batch` (PX-47)** — purely mechanical config-drift cleanup, per
`RELEASE_ARC.md` step 5 and the PX-47 row in
`docs/dev/reviews/2026-07-efficiency/prescriptions.md`. Per the 2026-07-07 staleness
re-verify (`px-staleness-reverify-2026-07-07.md`), the prescription is **PARTIALLY_STALE**
— re-derive before acting rather than trusting the original four legs:
1. `.claude-plugin/plugin.json` version bump — it read `"version": "1.0.6"` against the
   project's actual `1.0.9` as of the last audit; **verify at HEAD first**.
2. `CLAUDE.local.md` refresh.
3. The model-pin convention across the 9 subagents in `agents/` — **re-scoped to an
   explicit owner decision** by that re-verify (no dated Sonnet-5 snapshot exists on the
   API), so surface it, don't decide it.
4. The `settings.local.json` prune leg is **already DONE** — drop that sub-item.

Scope is bounded to PX-47 as prescribed in `docs/dev/reviews/2026-07-efficiency/` and
re-verified in `RELEASE_ARC.md`. Do not expand beyond what is listed there, and do not
treat this handoff as authorizing it without the owner's go-ahead.

---

## First move

Create branch `chore/config-drift-batch` off `main`, write a plan
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
   observations` section above**; branches to prune identified. "Done" is the output
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
4. Ask user to confirm merge to `main`; execute merge after confirmation
5. Prune merged branch(es) with the user's OK. Generate the one-line
   pointer with `python scripts/print_handoff_pointer.py
   docs/dev/handoffs/<branch-slug>.md` — never hand-type the branch or
   commit hash — then immediately verify that exact output with
   `python scripts/check_handoff_pointer.py "<output>"` before pasting
   anything (enforce the method, then check the result: a hand-typed hash
   was proven fabricated once — see
   `docs/dev/diagnosis/handoff-pointer-verification.md`).
   Give the user the checked line **as copyable chat text**, as the
   **last act** before closing the window. Never paste the handoff file's
   content into chat; that reintroduces the corruption channel this
   pipeline exists to remove.
