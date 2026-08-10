# A4 sprint brief — `feat/prior-apps-pipeline`

> Written per `docs/dev/handoffs/EPIC_SPRINT_BRIEF_TEMPLATE.md` (§15.4 of
> `docs/dev/epic-a-chain-design-corrections.md`). This is the intra-chain sprint
> transition artifact, **not** a session-to-session handoff — it points at standing
> context rather than restating it.

## Sprint identity

- **Sprint:** A4 (Epic A, `epic/a-app-core`)
- **Branch to create:** `feat/prior-apps-pipeline`
- **Stacked on:** `feat/role-summary-drafting @ fab794d` — A3's tip, **never `main`**
- **Implementer model + effort:** Sonnet, per `docs/dev/RELEASE_ARC.md`'s Session
  models table (`A4 | Sonnet | mechanical move + handler/test rewrite`). The
  design-corrections doc's own caution (§"4. HIGH — A2 and A4 hit an unanticipated
  C-10 block on `ui_pages/selectors.py`", `docs/dev/epic-a-chain-design-corrections.md`)
  says this plainly and it is repeated here rather than assumed known: *"A4 is the
  Sonnet sprint — the least-equipped implementer meeting a no-escape-hatch gate with
  no brief coverage."* That finding's own correction is what this brief exists to
  supply — see "What this sprint builds" below.

## Standing context — read, do not expect it restated here

| What | Where |
|---|---|
| Design of record | `docs/dev/epic-a-chain-design-corrections.md` — read in full; skipping this is the most expensive mistake this chain has made |
| Authorization envelope (run vector, halt points, flag stops, seam) | `docs/dev/epic-a-chain-design-corrections.md` §11 |
| Close-out cadence for this epic | `docs/dev/epic-a-chain-design-corrections.md` §15 |
| Sprint scope | `docs/dev/RELEASE_ARC.md` — Epic A section, "A4 — prior applications → Pipeline" |

## What just landed (A3, `feat/role-summary-drafting`)

Two commits, `7d3ff33` (implementation) and `fab794d` (post-gate compaction-disclosure
ledger row). Honest summary, not a gloss:

- New net-new LLM call, `analyzer.draft_experience_summaries` — one batched Sonnet
  call covering every included role (never per-role), grounded via
  `hardening.assemble_source_union` widened to a fifth source
  (`experience_summary_items`); `PROMPT_VERSION` bumped
  `2026-07-08.4` → `2026-08-09.1`.
- Compose UI parity: per-role summary card, edit in place, keep/reject, save-to-corpus
  as a pending intro variant, via two new routes.
- New-call-kind checklist closed (`EXPECTED_CALL_KINDS`, never-logged-kind probe,
  UX stub, pricing keys verified-by-construction). Item 34 closed and **widened**:
  enumerating `_get_client` consumers fresh found two more unpatched corpus
  blueprints beyond item 34's own list (`curation.py`, `blueprints/assistant.py`);
  fixed all four and added `tests/test_ux_stub_coverage.py`, an AST-walk gate, since
  this was the third instance of the same class (items 21, 22, 34) — a C-11
  recurrence.
- **Adversarial review (Sonnet refuter) confirmed and this sprint fixed one real
  defect before commit**: a kept-but-unreviewed `ExperienceSummaryItem` drafted for
  one application could leak — via the composition picker, save validation, AND the
  rendered/downloaded résumé — into a *different* application for the same
  candidate. Fixed with a mirrored per-application acceptance ledger
  (`accepted_experience_summary_ids`), guarded at all four read sites. **This is the
  precedent A4 inherits — see below.**
- Eval: a targeted synthetic corpus-mode fixture + `evals/corpus_drafting_probe.py`,
  $0.025 real spend across two runs, logged in `evals/TUNING_LOG.md`. The
  union-widening's live metric effect was **not** demonstrated by the eval runs
  (stated as a negative finding) — proven instead by a deterministic unit test.
- **Compaction disclosure (`fab794d`, unverified-until-read, said plainly):** the
  full gate that ran on the committed tree did **not** examine `fab794d` itself
  (data-only ledger append, per item 52's class — routine and expected). Separately,
  and worth more attention: this sprint's own ledger shard recorded **five**
  compacted subagent events (three pre-commit, two around the gate run) — the
  standing, unresolved F6/§12.6 risk that a compacted subagent can return a degraded
  result with no signal to the orchestrator. A3's mitigation was independent
  re-verification rather than trusting subagent self-reports: the orchestrator
  re-read the core diff directly, re-ran mypy/pytest itself rather than citing
  agent-reported numbers, and checked three separate concurrent-edit-stale Pyright
  alarms against ground truth (all three were noise, confirmed by direct grep/read).
  **Not a fix — compaction telemetry remains unbuilt.** I have not independently
  re-verified any of this beyond reading the two commits; it is reported here as A3
  recorded it, not re-confirmed by this brief.
- **One deferred-not-fixed gap, disclosed in the A3 commit and now filed as work
  items** (see "Open risks handed forward").

## What this sprint builds

Per `docs/dev/RELEASE_ARC.md`'s Epic A section, "A4 — prior applications → Pipeline"
(`feat/prior-apps-pipeline`):

- **Remove the Tailor applications panel** — `templates/index.html:172-208`,
  `static/app.js:6147-6264` (verify these ranges against HEAD before editing; the
  design-corrections doc's own A1-citation-drift audit found line-number drift is a
  recurring failure mode in this chain — re-derive, don't trust the cite).
- **Rewrite `_renderPipelineRow`'s `activate()`** (`static/app.js:263-277` as of
  `fab794d` — verified directly for this brief) to open the shared detail modal **in
  place**. Today it tab-switches to Tailor first
  (`document.getElementById('topTabTailor')` → `switchTopTab('tailor', tailorBtn)`)
  and *then* calls `_showApplicationDetail(a.id)`.
  `tests/ux/regression/test_20260707_recruiter_roster_pipeline.py:135-146` pins the
  current tab-switch-then-modal behavior and **must be rewritten with it**, not left
  passing on the old assumption.
- **Update `ui_pages/` and any copy referencing the panel.**

**The C-10 blast-radius requirement, stated explicitly because the design-corrections
doc found this exact gap for this exact sprint.** `ui_pages/selectors.py` is a
**gated** C-10 surface (`scripts/enforcement/blast_radius.py`), and this sprint's
`PriorApps` class (`ui_pages/selectors.py:287-297`) — `PANEL`, `LIST`, `MODAL`,
`RESUME_BUTTON`, `TITLE_INPUT`, `COMPANY_INPUT` and more — is exactly what removing
the panel touches. `require-consumer-enumeration` **will** block the first edit to
this file until `docs/dev/blast-radius/prior-apps-pipeline.md` exists with a
`## Consumers` section that **literally names** `ui_pages/selectors.py`. Write that
dossier **before** the first edit to `ui_pages/selectors.py` or `static/app.js`'s
`activate()` — not after, and not as a rubber stamp. Enumerate every consumer of
`PriorApps.*` (grep-complete: the class attributes themselves, `tests/ux/**`,
`scripts/capture_screenshots.py`, any other selector-registry consumer) before
deciding what changes and what is deferred.

**What is explicitly OUT of scope:** anything not in the three bullets above. The
nursery item G7 ("prior-application compact cards", `docs/dev/RELEASE_ARC.md`
line ~1433) is a *different*, deferred idea about a denser card — it is not this
sprint's scope and should not be folded in.

## First move

Create the branch off `fab794d`, take the mechanical precondition edit needed if the
approved-plan stamp requires a flush (per `RELEASE_ARC.md`'s "Mechanical precondition
for the single approval" — check whether this chain's existing single `ExitPlanMode`
approval still covers A4 before assuming a fresh ceremony is needed), then **write
`docs/dev/blast-radius/prior-apps-pipeline.md` before touching `ui_pages/selectors.py`
or `static/app.js`'s `activate()`.** This is a `feat/*` branch, not `fix/*`, so the
C-7 evidence-dossier gate does not fire — the blast-radius dossier is the gate that
does.

## Decisions taken alone last sprint that this one inherits

- **The per-application-acceptance-ledger shape is now a live precedent.**
  `accepted_experience_summary_ids` (mirroring `accepted_generated_bullet_ids`) is
  the pattern A3 used to close a cross-application leak: a server-owned ledger,
  carried forward from the fresh in-lock context read (not the stale outer
  snapshot) on every composition save, checked at every read site that could
  surface the data. If A4 encounters any structurally similar
  cross-application-visibility question while touching the Prior Applications →
  Pipeline surface, this is the established shape to reach for rather than
  inventing a new one — though whether it actually applies is A4's own judgment,
  not assumed here.
- **The single-gate-run-after-commit sequence is Epic-A-scoped and still in force**
  (`docs/dev/RELEASE_ARC.md`'s 2026-08-09 amendment): implement → stage → adversarial
  review of the staged diff → fix confirmed findings → stage → file deferred findings
  → stage → **commit** → `python -m scripts.gate` on the committed tree → if red, fix,
  commit again, re-gate.
- **Light §15.2 close-out stays in force for A4 too** — wiki pass and `BOARD.md`
  regen deferred to epic close, contingent on `python -m scripts.wiki_freshness`
  staying under the 40-drift threshold at A4's own gate (it was 16/75 at this
  sprint's close; re-check, don't assume it's still there).

## Open risks handed forward

- **[reported, filed]** Work item 69: `_active_intros_by_experience`
  (`blueprints/applications.py:2828-2854`) has the same `is_active`-only filter the
  A3 pending-leak fix closed elsewhere — a foreign pending intro can bias a *new*
  draft's wording via prompt context. Lower severity than what A3 fixed (does not
  reach a rendered résumé), deliberately left out of A3's scope, now tracked.
  Not in A4's scope unless A4 independently decides it overlaps its own work.
- **[reported, filed]** Work item 70: `tests/test_ux_stub_coverage.py`'s AST walker
  only matches `from web_infra import _get_client` (`ast.ImportFrom`); a
  hypothetical `import web_infra` + attribute-access blueprint would evade it in
  either direction. Not exploitable today (verified — every current blueprint uses
  the matched form). Docstring now discloses the limit. Minor, no action needed
  from A4.
- **[reported, from A3's own disclosure]** The F6/§12.6 compaction risk: a
  compacted subagent can return a degraded result with no signal to the
  orchestrator. Unmitigated by tooling — the only defense is the orchestrator's own
  independent re-verification of subagent claims (re-read diffs, re-run
  mypy/pytest directly, check flagged alarms against ground truth) rather than
  trusting self-reports. A4's orchestrator should expect to do the same, especially
  since A4 is explicitly the "least-equipped implementer" sprint per the
  design-corrections doc's own finding.
- **[verified, this brief]** `ui_pages/selectors.py`'s `PriorApps` class exists at
  `:287-297` and is exactly what this sprint's panel removal touches — confirmed by
  direct read for this brief, not inferred from the design-corrections doc's report
  of it.

## Flag-stop state

None waiting on the owner as of this brief. If A4's blast-radius enumeration finds
that removing the Tailor panel requires a schema, security, or architecture decision
not already settled in the ARC brief or the design-corrections doc, that is Halt
point 2 (§11.5) — stop and surface, do not self-resolve.

## Gate + verification state

- Last gate run: `fab794d` — "gate: all steps passed." (per the `fab794d` commit
  message; not independently re-run by this closer, per the closer's own §15.2
  scope, which does not include re-running the gate).
- Rerun sweep: 0 `RERUN` (per the `7d3ff33` commit message: "2437 passed, 1 skipped,
  0 failed, non-UX").
- Wiki drift at handoff: 16 of 75 — under the 40-drift epic deferral threshold
  (correctly deferred per §15.2; this closer did not re-run
  `python -m scripts.wiki_freshness` — the 16/75 figure is carried forward from the
  task brief this closer was given, not independently re-measured. **Reported, not
  verified — A4 should re-check at its own gate rather than trust this number
  stale.**).

---

## Close-out obligations this sprint still owes

- **Owed now (per sprint, no escape hatch):** C-10 blast-radius dossier for
  `ui_pages/selectors.py` (see "What this sprint builds"); substantive commit
  message; this sprint's own §15.4 brief for A4's successor; work items for
  anything discovered-and-not-chased; `python -m scripts.gate` on the committed
  tree with the rerun sweep; one adversarial refuter on the staged diff; the §15.5
  countable-claim canary on any touched wiki page (none expected this sprint, since
  the wiki pass itself is deferred — but any *incidental* wiki edit still owes the
  canary).
- **Deferred to epic close:** the wiki pass and `.last_ingest_sha` advance; full
  grounding audits of wiki pages; the full `AGENT_HANDOFF_TEMPLATE.md` ceremony;
  `BOARD.md` regeneration.
