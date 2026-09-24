# Epic C sprint brief — C2: `feat/run-detail-modal` (run 3 of 4)

> **Position superseded 2026-09-24:** C1c was inserted ahead of this sprint (see the
> run record at the bottom). C2 is now **run 4 of 5**. Its re-run invocation comes from
> `docs/dev/handoffs/epic-c-c2-rerun-brief.md` (written by C1c's closer). This file stays
> C2's scope of record.

> Written by C1b's closer (`feat/dashboard-polish`), 2026-09-23, from
> `docs/dev/handoffs/EPIC_SPRINT_BRIEF_TEMPLATE.md`, per the epic's declared intra-epic
> sprint-transition cadence (item 89; `epic-b-design-brief.md` §"Close-out intervals",
> restated for Epic C in `epic-c-design-brief.md` §"Close-out intervals").

## Sprint identity

- **Sprint:** C2, run 3 of 4 (`epicSprintIndex: 3`, `epicSprintCount: 4`)
- **Branch to create:** `feat/run-detail-modal`
- **Stacked on:** `feat/dashboard-polish` — **staged (`git add -A`) but not committed by
  this closer.** Per the corrected close ordering
  (`docs/dev/epic-a-chain-design-corrections.md` §11.9.4 / §2), the commit and the full
  gate belong to the invoking session, which runs after this brief is written. The
  invoking session must record the actual commit sha here (or verify it directly) before
  starting C2 — **do not start C2 against an uncommitted tip.** For reference, C1a
  (`fix/dashboard-run-lock-gaps`) is already committed as `150bfb9` and ff-merged into
  `epic/c-diagnostics` (tip `3e29527` + the docs commit `dd803e3` recording that sha into
  this branch's own C1b brief) — C1b's own tip, once committed, stacks on `dd803e3`.
  **Recorded by the C2 invoker (session preflight, 2026-09-24):** C1b committed as
  `27a1fdc`, plus the hook-written ledger commit `e7005b2`. Both are ff-merged, so
  `epic/c-diagnostics` == `feat/dashboard-polish` == `e7005b2`. C1b's gate #1 and gate #2 logs
  both end `gate: all steps passed.` with 0 `RERUN`. `feat/run-detail-modal` is cut from `e7005b2`.
- **Implementer model + effort:** `sonnet`, per `epic-c-design-brief.md` §"Sprint →
  pipeline-run mapping" (RELEASE_ARC §"Session models": C2 = Sonnet).

## Standing context — read, do not expect it restated here

| What | Where |
|---|---|
| Design of record | `docs/dev/handoffs/epic-c-design-brief.md`. **Read in full**, including the ratified scope sentence and the no-prune rule in §"Branch topology". |
| Authorization envelope (run vector, halt points, flag stops, seam) | `epic-c-design-brief.md` §"Execution mode + authorization record" and §"Escalation + envelope"; `docs/dev/epic-a-chain-design-corrections.md` §11.4-§11.9 (the envelope this closer itself ran under). |
| Close-out cadence for this epic | `epic-c-design-brief.md` §"Close-out intervals" |
| Sprint scope | `docs/dev/RELEASE_ARC.md` §"Epic C", C2 rows; row 3 of `epic-c-design-brief.md` §"Sprint → pipeline-run mapping" (`:107`) |
| Pre-verified UX checklist | `docs/dev/reviews/epic-c-console-ux-audit.md`, **UX-7 and UX-8** |

## What just landed

C1b (`feat/dashboard-polish`), staged but **not yet committed** by this closer:

- Sticky `.dash-tabs` (UX-2) via a `body:has(#runLockBanner:not([hidden])) .dash-tabs`
  rule that shifts the tab bar's `top` to clear the sticky run-lock banner instead of
  overlapping it.
- Corrected the false "Read-only observability" header (UX-3) and the false
  "only write surface" claims (UX-24) — the header paragraph
  (`dashboard/templates/dashboard.html:253-258`) now groups **Quality** with Tuning and
  Annotate on the read-write/spend side (it has its own "Run eval" control,
  `#evalRunBtn`, that spends paid Sonnet/Haiku calls and writes eval-result files) rather
  than with the pure-read Pipeline/Groundedness tabs, and names Quality's own controls in
  the trailing "use the … controls below" clause. The Annotate intro and the CSS comment
  at `:190-191` already said this correctly; only the top header sentence was wrong.
- **This closer's own fix, applied per this sprint's judge verdict (F1, "fix" — CONFIRMED
  from the staged diff):** the above header correction, plus tightening
  `tests/ux/regression/test_20260923_dashboard_polish_ux.py`'s UX-3/UX-24 test — the
  original assertion (`expect(meta).to_contain_text("Tuning and Annotate are
  read-write")`) was a substring of the *correct* sentence too, so it would have passed
  even with Quality wrongly omitted. It now asserts the full "Quality, Tuning and
  Annotate are read-write" grouping is present, the stale "Pipeline, Quality and
  Groundedness read" grouping is absent, and the trailing clause names Quality's own
  controls.
- Opaque + pulsing run-in-progress banner (UX-4) — `#runLockBanner`'s background is now
  fully opaque (was 14%-alpha) and carries a `cb-status-pulse-strong` animation, silenced
  under `prefers-reduced-motion: reduce` by `static/style.css`'s existing global override.
- `.btn-pending` / `cb-status-pulse-strong` ported to every wait state (UX-5) — the four
  streamed runs, Save, Collate, Export seed, and fixture Load all get the shared
  disabled+pulsing state for the whole request via `window.sartorEval.setBtnPending()` /
  `clearBtnPending()`.
- The terminal Cancel state (UX-6) — the progress line used to stay on "Cancelling…"
  forever; the abort branch now reaches "Cancelled — no further paid calls were started."
  once the abort actually lands, and clears the Run button's pending/pulsing state.
  Covered by updates to the existing `test_20260720_diagnostics_run_cancel.py` rather than
  a new test, since that file already drives the exact code path.
- **Filing obligations this sprint:** none. The judge payload's single verdict (F1) was a
  "fix," not a "defer," and its own rationale says "Fix, not escalate" explicitly — no
  work item ordered. The deferred-verdicts list was empty; no implementer report handed
  this closer anything to file. `BOARD.md` was regenerated
  (`python -m scripts.work_items board --write`) and produced **no diff** — consistent
  with zero filings.
- **Not verified by this closer:** the full gate (`pytest`, the UX suite included) has
  **not** been run on this branch by this closer — that is the invoking session's job
  (§11.9.4). This closer ran only the three static gate steps on the current tree:
  `python -m ruff check .` ("All checks passed!"), `python -m ruff format --check .`
  ("363 files already formatted"), `python -m mypy .` ("Success: no issues found in 379
  source files"). The invoking session still owes gate #1 (pre-refuter) and #2 (post-fix)
  for C1b with the `RERUN` sweep.
- **Wiki:** scoped no-edit check recorded at `docs/wiki/log.md`'s 2026-09-23 C1b entry.
  Drift at C1b's tip: **40 of 75** (up one from C1a's 39), well under the epic's 60
  backstop — the full wiki pass stays deferred to the epic close.

## What this sprint builds

**In scope (RELEASE_ARC C2, `feat/run-detail-modal`; UX-7, UX-8):**
- `GET /_dashboard/api/run/<run_id>` on the same `dashboard_bp` blueprint (inherits
  `_localhost_guard`; a non-localhost request gets 403) — one bounded JSONL pass reusing
  `_run_trace`, `_reliability`, `_cost_by_call_kind` (all in `dashboard/routes.py`).
- Every run id shown in the console (trace tile, calls table, "Recent runs" fold,
  recent-evals table — currently four inert `<code>` spots, per UX-7) becomes a button
  that opens a composite modal backed by the new endpoint, showing that run's spans,
  latency, cost and errors. Today only the *latest* run's waterfall is viewable; the other
  9 rows in "Recent runs" (`routes.py` `runs_sorted[:10]`) have no drill-down.
- Clickable error-rate rows (UX-8) — today the error-rate detail gives counts per call
  kind and the calls table just says `error`, with no message shown anywhere. Clicking an
  error-rate row lists that call kind's recent error records with their actual messages.

**Out of scope, deliberately:**
- C3 (`feat/dashboard-copy-discovery`) — the next (terminal) run.
- UX-22..UX-41 — excluded from Epic C per the kickoff-session decisions (items 112, 113).
  If the implementer thinks a UX-3x finding is the same defect as UX-7/UX-8, that is a
  flag for the owner, not a fold-in.
- Any change to `LOCK_BTN_IDS` / `acquireRunLock()` / the run-lock mechanics, or to the
  C1b wait-state/animation work (`.btn-pending`, the run-lock banner, sticky tabs) — C2 is
  a new read endpoint + modal UI, not a revisit of C1a/C1b's surfaces. If C2's implementer
  finds the modal needs a lock-state affordance, that is a flag stop (scope question the
  vector does not answer — §11.6, "silence is a stop, not a licence").

> **A named fix site in this section is a HYPOTHESIS, not a spec (C-0).** The implementer
> verifies each named line/selector is still accurate — C1a's and C1b's edits have both
> moved line numbers in `dashboard/templates/dashboard.html` since
> `epic-c-design-brief.md`'s C2 row (`dashboard.html:291`, `:765`, `:809`, `:914`, `:794`,
> `:783-785`, `:767`) was written — re-derive, do not assume the cite is still exact.

## First move

C2 is a `feat/*` branch, not `fix/*` — `require-evidence-before-fix` does not gate it.
`dashboard/routes.py` and `dashboard/templates/dashboard.html` do not currently appear in
`scripts/enforcement/blast_radius.py`'s gated-surface registry (verified: neither
`dashboard/routes.py` nor `dashboard/templates/dashboard.html` appears there as of C1b's
tip), so `require-consumer-enumeration` does not gate it either — **but the implementer
must re-check this against the actual branch tip before assuming it still holds**, since a
new route on an existing blueprint is exactly the kind of change that could justify adding
one of these paths to the registry; if the guard fires, that is the guard functioning, not
a stop.

For the **implementer**: re-derive every cited line number against the actual branch tip
first (C1a's and C1b's edits already moved several of them). Confirm UX-7 and UX-8's
described gaps are still present by driving the running dashboard (the `run` skill /
`docs/dev/reference-sandbox-ux-walkthrough-method` pattern from memory — drive the real
app, sandboxed, rather than trust the audit alone) before writing the route or the modal.
Then implement, and add or extend a UX regression test per defect where the existing suite
doesn't already cover it (UX-7/UX-8's acceptance criteria above are the test targets).

For the **invoking session**: runbook step 0 + 0a first (preconditions, batched preflight,
scope reconciliation, witness-pause consumption), **then verify C1b's commit landed and
record its sha above** before this:

```
Workflow({scriptPath: '.claude/workflows/n1-baseline.mjs', args: {
  stage: 'sprint',
  sprintBriefPath: 'docs/dev/handoffs/epic-c-c2-brief.md',
  epicBriefPath: 'docs/dev/handoffs/epic-c-design-brief.md',
  epicSprintIndex: 3,
  epicSprintCount: 4,
  nextSprintBriefPath: 'docs/dev/handoffs/epic-c-c3-brief.md',
  implementerModel: 'sonnet',
}})
```

## Decisions taken alone last sprint that this one inherits

From C1b, under §11.8 (decided and recorded, not surfaced mid-run):
- The judge's F1 fix was applied as a direct edit to the header sentence and the UX-3/UX-24
  test, not filed as a work item — the rationale explicitly said "Fix, not escalate," and
  the fix stayed inside the in-scope UX-3 header sentence with no `LOCK_BTN_IDS`/
  `acquireRunLock()` change (the brief's own out-of-scope fence).
- C2's modal work will surface run ids and error rows that already exist in the DOM
  (UX-7/UX-8 are additive — new buttons/click handlers on existing elements, plus one new
  read-only endpoint); nothing about C1b's header-copy fix or wait-state polish (UX-2,
  UX-4, UX-5, UX-6) changes that shape.
- Inherited from C1a (still applicable, unchanged by C1b): the tuning/bootstrap/
  grounding-score inline `acquire()` call sites were left without return-value hardening;
  C2 does not touch these buttons' lock logic either.

## Open risks handed forward

- **C1b's gate has not run yet, reported by this closer, not verified end-to-end:** only
  the three static steps (ruff check/format, mypy) were run by this closer. The invoking
  session's gate #1/#2 and `RERUN` sweep are still owed and could surface an issue in
  C1b's `pytest -m ux` coverage (both the new UX-2/3/4/5/24 test file and the updated
  UX-6 cancel test) that this brief cannot see.
- **Line-number drift:** every cite above from `epic-c-design-brief.md`'s C2 row predates
  BOTH C1a's and C1b's edits to `dashboard.html`. Re-derive before relying on any of them
  (matches the design brief's own "Cite-drift note").
- **UX suite flake history** (memory / carry-forward ledger): the rerun sweep is
  mandatory; a green-after-retries result is a stop-and-look per C-7, not a pass.
- **Blast-radius registry drift:** `dashboard/routes.py` / `dashboard/templates/
  dashboard.html` are not gated today, but C2 is the first sprint to add a genuinely new
  route (`GET /_dashboard/api/run/<run_id>`) rather than edit template copy/CSS — worth a
  second look at whether this crosses into "shared contract" territory before assuming the
  guard's silence still applies.

## Flag-stop state

None. C1b hit no halt point and no flag stop; its only correction (the F1 header/test fix)
was an in-envelope §11.8 decision, not a stop.

## Gate + verification state

- Last gate run: **not run by this closer.** The invoking session owes gate #1 (pre-
  refuter) and gate #2 (post-fix, pre-commit) for C1b; report the verbatim terminal
  summary line here once run.
- This closer's own static checks (2026-09-23, on the staged C1b tree):
  `python -m ruff check .` → "All checks passed!"; `python -m ruff format --check .` →
  "363 files already formatted"; `python -m mypy .` → "Success: no issues found in 379
  source files".
- Rerun sweep: not yet applicable — no full gate run has happened on this branch yet.
- Wiki drift at handoff: **40 of 75** (`python -m scripts.wiki_freshness`, 2026-09-23, up
  one from C1a's 39). The epic's backstop is 60; C2 should re-check this at its own close,
  since it may touch `dashboard/routes.py` (a new file relative to C1a/C1b's
  template-only diffs) in addition to the template.

---

## Close-out obligations this sprint still owes

- **Owed now:** a substantive commit message, the **C3 brief** at
  `docs/dev/handoffs/epic-c-c3-brief.md` (the closer, from the template, whose First move
  must pass `implementerModel: 'opus'` and `epicSprintIndex: 4` — C3 is the terminal run,
  so its own First move passes no `nextSprintBriefPath`), work items for anything
  discovered and not chased, `BOARD.md` regeneration, the invoker's two gate runs with a
  `RERUN` sweep, and the refuter pass. No C-7/C-10 dossier is expected unless the
  implementer's diff turns out to touch a gated surface or needs a `fix/*` branch after
  all (see "Open risks" above on the blast-radius registry) — the dossier becomes owed at
  that point, not skipped.
- **Deferred to epic close:** the wiki pass (unless drift reaches 60), full grounding
  audits, the full `AGENT_HANDOFF_TEMPLATE.md` ceremony, and the epic-level adversarial
  review.

## Invoker run record (C2)

- 2026-09-24, invoker session `93ed5108` (Opus 5.5). Probe `wf_7f6d3065-0c7` returned `ok_to_run`.
- Sprint stage `wf_697596d4-c2f` returned **`escalated_to_owner`** (a `flag_stop` §11.6 raised
  by the implementer, then `escalate` from both Opus reviewers). UX-8 says "with their
  messages", but `analyzer.py`'s `_emit_call_log` never records exception text. The
  implementer built a version that shows only metadata (call kind, timestamp, model,
  stop_reason, latency) and labels it "no message logged". Owner choice: (a) scope exception
  capture separately, with a C-10 dossier, or (b) accept metadata-only and amend UX-8. The
  closer did not run. The implementer's 7 files are staged and **not gated**. Journal:
  `~/.claude/projects/C--Dev-sartor/93ed5108-6347-4192-a19a-2ec4c9f7a4b8/subagents/workflows/wf_697596d4-c2f/journal.jsonl`.
- **Owner decision, 2026-09-24 (typed "a"):** option (a). Exception-text capture into
  `llm_calls.jsonl` is a **separately scoped change** with its own C-10 consumer dossier and a
  redaction/size policy. It is **not** folded into C2. The sequencing against C2 was still being
  confirmed when this was written.
