# Epic C sprint brief — C3: `feat/dashboard-copy-discovery` (run 5 of 5, terminal)

> Written by the C2-rerun closer (`feat/run-detail-modal`), 2026-09-24, from
> `docs/dev/handoffs/EPIC_SPRINT_BRIEF_TEMPLATE.md`, per the epic's declared intra-epic
> sprint-transition cadence (item 89; `epic-b-design-brief.md` §"Close-out intervals",
> restated for Epic C in `epic-c-design-brief.md` §"Close-out intervals") and per this
> sprint's own brief's instruction for the closer
> (`docs/dev/handoffs/epic-c-c2-rerun-brief.md` — carrying `epic-c-c2-brief.md`'s own
> "First move" forward, and per the corrected close ordering,
> `docs/dev/epic-a-chain-design-corrections.md` §11.9.4 / §2).

**This closer applied three confirmed judge-verdict fixes on top of the restored C2
implementation (F1, F2, F3 — see "What just landed" below) rather than building anything
new.** C3's own scope of record stays `docs/dev/RELEASE_ARC.md` §"Epic C" (the C3 row) and
`epic-c-design-brief.md`'s sprint table — read both in full. This brief states C3's scope
(largely unchanged, restated here since no prior C3-specific brief existed) plus what
changed on C2's tip that C3 inherits.

## Sprint identity

- **Sprint:** C3, run 5 of 5 (terminal) (`epicSprintIndex: 5`, `epicSprintCount: 5`).
- **Branch to create:** `feat/dashboard-copy-discovery`.
- **Stacked on:** `feat/run-detail-modal` — **staged (`git add -A` by this closer, not
  committed).** Per the corrected close ordering
  (`docs/dev/epic-a-chain-design-corrections.md` §11.9.4 / §2), the commit and the full
  gate belong to the invoking session, which runs after this brief is written. HEAD at the
  time of writing is `d3859b0` (the C2-rerun invoker's preflight-record commit); this
  closer's own staged work (the three F1/F2/F3 fixes to `dashboard/templates/
  dashboard.html` and `docs/dev/blast-radius/run-detail-modal.md`, work item 115,
  `BOARD.md`, this brief, and the `docs/wiki/log.md` entry) sits on top of it, uncommitted,
  alongside the C2 implementation itself (also still staged — see "What just landed").
  **The invoking session must record the actual `feat/run-detail-modal` commit sha here
  (or verify it directly) before starting C3 — do not start C3 against an uncommitted
  tip.**
- **Implementer model + effort:** `opus`, per `epic-c-design-brief.md` §"Sprint →
  pipeline-run mapping" (RELEASE_ARC §"Session models": C3 = Opus).

## Standing context — read, do not expect it restated here

| What | Where |
|---|---|
| Design of record | `docs/dev/handoffs/epic-c-design-brief.md` — **read in full**, including the ratified scope sentence and its 2026-09-24 amendment record (the C1c insertion, which renumbered C3 from run 4 of 4 to run 5 of 5). |
| Authorization envelope | `epic-c-design-brief.md` §"Execution mode + authorization record", §"Escalation + envelope"; `docs/dev/epic-a-chain-design-corrections.md` §11.4-§11.9. |
| Close-out cadence | `epic-c-design-brief.md` §"Close-out intervals" — **C3 is the terminal sprint, so the epic-close obligations (deferred by every prior sprint) land here**: the full wiki pass, full grounding audits, the `AGENT_HANDOFF_TEMPLATE.md` ceremony with `verify_doc_template.py`, and the epic-level adversarial review. |
| Sprint scope | `docs/dev/RELEASE_ARC.md` §"Epic C", the **C3** bullet (`:1962` at last verification, re-derive before relying on it — line numbers move). |
| Pre-epic UX audit (C3's concrete checklist) | `docs/dev/reviews/epic-c-console-ux-audit.md` — UX-9, UX-10, UX-11, UX-13, UX-14..UX-20, UX-18, UX-21, UX-42 (see `epic-c-design-brief.md`'s sprint table for the one-line gloss on each). |

## What just landed

- **C1a** `150bfb9`, **C1b** `27a1fdc` + ledger `e7005b2`, and **C1c** `0d480c2` + ledger
  commits `90e91b0`/`71d0d17`, are committed on this branch's history (`epic/c-diagnostics`
  lineage). The C2-rerun invoker's preflight record `d3859b0` is HEAD at the time of
  writing.
- **C2's implementation (UX-7 + UX-8) is staged, not yet committed.** It was restored from
  `wip/c2-run-detail-modal @ 12acfc5` onto `feat/run-detail-modal` (fast-forwarded from
  C1c's tip), per `epic-c-c2-rerun-brief.md`'s instructions, and finished against C1c's new
  `error_type`/`error_message` telemetry fields. **I have not re-verified the restoration
  itself** (the invoking session's or C2 implementer's job, per that brief) — I received
  the tree already staged and worked from there.
- **This closer's three judge-ordered fixes, applied against the staged tree (all
  `[VERIFIED]` by direct read, not reused from the judge payload's own citations):**
  1. **F1 (esc() attribute-escaping gap).** `dashboard/templates/dashboard.html`'s `esc()`
     helper did a `textContent`→`innerHTML` round-trip, which escapes `& < >` (and U+00A0)
     but not quote characters — a gap when the same helper builds an attribute value (the
     waterfall row's `title="..."`). No live injection path exists today (`call_kind` is
     an internal literal, `model` is `effective_model`), but the helper is reused for
     genuinely external text (`error_message`, a redacted API exception string) elsewhere
     in the same block, so the gap matters going forward. Fixed with a one-line
     `.replace(/"/g,'&quot;').replace(/'/g,'&#39;')` appended to the returned string —
     the renderer itself is untouched.
  2. **F2 (dossier accuracy).** `docs/dev/blast-radius/run-detail-modal.md` rows 1–2 named
     an `error_rate_row` static method and an `open_run_modal(run_id)` page-object method
     that were never added — the actual members (`RUN_MODAL`, `RUN_MODAL_OPEN`,
     `RUN_MODAL_TITLE`, `RUN_MODAL_BODY`, `RUN_MODAL_CLOSE`, `RUN_LINK`, `ERR_LINK`,
     `run_link()`/`err_link()` on the selectors side; `run_link`, `open_run_detail`,
     `err_link`, `open_errors_for_kind`, `run_modal`, `run_modal_open`, `run_modal_body`,
     `close_run_modal` on the page-object side) were confirmed by reading both files
     directly. The C-10 mechanism itself held (both sites were correctly identified and
     decided `update`); this was a docs-accuracy defect in the dossier's own cell text,
     now corrected in place with a dated note.
  3. **F3 (CSS-cascade regression).** The new `.cb-dash button.err-link { color:
     var(--info); ... }` rule (specificity 0,3,1) outranked the inherited
     `.fail { color: var(--danger) }` on a failing call kind's `<td>`, silently dropping
     the red "this is failing" cue for every `.err-link` button (100% of the cases it
     existed for — the button only renders inside `{% if k.error_count %}`, exactly when
     `.fail` applies). Fixed with a `.cb-dash td.fail button.err-link` rule
     (specificity 0,3,2) plus a matching `:hover` rule (0,3,3) so the pre-existing hover
     affordance isn't shadowed by the fix. **Verified against source, not measured live**
     — see the filed follow-up below.
- **Filed, not applied — work item 115.** The judge's F3 rationale explicitly separated
  the required fix (above) from a non-blocking suggestion: add a `getComputedStyle`
  assertion to the UX-8 test so the color fix is actually measured in a live browser
  rather than re-confirmed by reading the same CSS rules. Filed as
  `docs/dev/work/items/0115-run-detail-err-link-computed-style-assertion.md` rather than
  applied, per the judge's own "not a blocker" framing.
- **Wiki relevance check done, no edit.** `docs/wiki/log.md`'s 2026-09-24 C2-rerun entry —
  `dashboard/routes.py` and `dashboard/templates/dashboard.html` are wiki-relevant in this
  diff; `docs/wiki/pages/diagnostics-console.md` has zero hits on any run-detail-modal or
  `esc()`/cascade-related term, so nothing to correct. Drift stays **40 of 75** (this
  sprint's files are staged, not committed, so the counter hasn't moved).

## What this sprint builds

**Per `epic-c-design-brief.md`'s sprint table (C3 row) and `docs/dev/RELEASE_ARC.md`
§"Epic C"** — restated here since no C3-specific brief existed before this one:

- A lay one-line summary plus a `_DASH_HELP` bubble for every module on every tab
  (UX-9; registry around `dashboard/templates/dashboard.html:1003-1152` at last
  verification — **re-derive the line numbers before relying on them**, C1a/C1b/C2 have
  all since edited this file).
- Quality-tab lay rewrite (UX-11).
- p50/p95/median/mean explainers (UX-10).
- Filter-scoping explainer (UX-13).
- The full Annotate instruction set per RELEASE_ARC (UX-14..UX-20).
- Fix the wrong Score-grounding help copy (UX-18).
- Groundedness + Tuning module copy (UX-21, UX-42).
- **Doc-page links wait for D4** — explicitly out of scope for C3, per the design brief's
  sprint table.

> **A named fix site above is a HYPOTHESIS, not a spec (C-0).** The implementer verifies
> each named location is still current (this file has moved under every prior sprint) by
> reading it directly before writing copy against it — the epic-a corrections doc's own
> worked example (B1a's unreachable-guard brief) is the cautionary case for treating a
> brief's line numbers as ground truth.

**New since the original C3 scope was drafted:** this sprint's own error-rate rows and the
run-detail modal (UX-7/UX-8, landed this sprint) are themselves tiles/controls a lay reader
will meet — if UX-9's `_DASH_HELP` registry is meant to cover every module, the C3
implementer should decide (and record, not surface) whether the new `.run-link`/`.err-link`
buttons and the run-detail modal need their own help entry, since they postdate the
original UX audit. This is exactly the kind of in-envelope call §11.8 assigns to the
implementer, not a flag stop.

## First move

1. Verify `feat/run-detail-modal`'s actual committed tip (recorded by the invoking session
   per "Sprint identity" above) before branching.
2. Read `docs/dev/reviews/epic-c-console-ux-audit.md`'s UX-9/10/11/13/14-20/18/21/42
   entries in full — they are the concrete checklist, not this brief's paraphrase.
3. Re-derive every line-number citation in this brief and in the audit against the current
   tip before writing copy against it (three sprints have edited `dashboard.html` since
   the audit was written).
4. Decide, and record, whether the new run-detail-modal controls need a `_DASH_HELP` entry
   (see "What this sprint builds" above).

For the **invoking session**, the copy-paste invocation MUST carry every arg the prose
prescribes, including `implementerModel` from **Sprint identity** above (item 96 — never
defaulted):

```
Workflow({scriptPath: '.claude/workflows/n1-baseline.mjs', args: {
  stage: 'sprint',
  sprintBriefPath: 'docs/dev/handoffs/epic-c-c3-brief.md',
  epicBriefPath: 'docs/dev/handoffs/epic-c-design-brief.md',
  epicSprintIndex: 5,
  epicSprintCount: 5,
  implementerModel: 'opus',
}})
```

`nextSprintBriefPath` is omitted: C3 is terminal (5 of 5). The run proceeds from C3's gate
straight to the epic close-out (owner-gated PR), per the ratified scope sentence in
`epic-c-design-brief.md`.

## Decisions taken alone last sprint that this one inherits

- **The redaction/size policy** (C1c, unchanged): `error_message` is never raw `str(exc)` —
  whitespace-collapsed, API-key/header-masked, 500-char truncated with `…[truncated]`. C3's
  copy work should describe this behavior accurately if it writes any help text touching
  the error display, rather than re-deriving or contradicting it.
- **The stash-guard decision** (C1c, owner-directed, unchanged): no pipeline agent may run
  any state-changing `git stash` command (`88add1f`, Bash dispatcher). Still binding.
- **This closer's F1/F2/F3 fixes** (this sprint) are load-bearing for C3: the `esc()`
  helper C3's own copy work may reuse for any new dynamic text is now attribute-safe; the
  `.err-link` failing-state color is now correct in the rendered page C3 will screenshot or
  describe; the C-10 dossier's member names are now accurate should C3 need to cite them.

## Open risks handed forward

- **[REPORTED, not independently re-verified by this closer]** The C2-rerun invoker's
  claim that `wip/c2-run-detail-modal @ 12acfc5`'s restoration onto `feat/run-detail-modal`
  is complete and correct (7 files, 728+/6−). I worked from the already-staged tree and did
  not re-diff it against the wip branch or the stash.
- **[VERIFIED by this closer]** The F1/F2/F3 fixes themselves — re-read against source
  after editing, not just against the judge's own citations.
- **[UNVERIFIED]** Work item 115's suggested `getComputedStyle` test addition — filed, not
  built, and not confirmed to close the gap it describes (that confirmation is exactly what
  the item asks a future agent to add).
- **UX-suite flake history:** unchanged from prior sprints — the rerun sweep is mandatory,
  and a green-after-retries result means stop and look (C-7).

## Flag-stop state

None. Nothing from this sprint's F1/F2/F3 fixes or the wiki check is waiting on the owner.

## Gate + verification state

- Last gate: C1b gate #2 at `e7005b2` — `gate: all steps passed.`, 0 `RERUN`. Neither
  C1c's nor this sprint's (C2 rerun's) gate has run yet — both belong to the invoking
  session, per the corrected close ordering, and run against the committed tree after this
  closer's staged work (including this brief) is committed.
- This closer ran the **static** subset only, per this sprint's own explicit instruction
  (never the full gate from a subagent): `ruff check` and `ruff format --check` on every
  file touched (`dashboard/templates/dashboard.html`,
  `docs/dev/blast-radius/run-detail-modal.md`, `docs/wiki/log.md`,
  `docs/dev/work/items/0115-run-detail-err-link-computed-style-assertion.md`,
  `docs/dev/handoffs/epic-c-c3-brief.md`) and `python -m mypy .` (whole repo) — see this
  session's own report for the exact result.
- Wiki drift: **40 of 75** (`python -m scripts.wiki_freshness`, run by this closer,
  2026-09-24) — unchanged, since this sprint's files are staged but not committed. Well
  under the 60 backstop; **C3 is the terminal sprint, so the full epic-close wiki pass is
  now owed at C3's own close-out**, not deferred further.

---

## Close-out obligations this sprint still owes

- **Owed now (per the epic's per-sprint floor):**
  - a substantive commit message (invoking session, after this closer's staged work);
  - work items for anything C3 discovers and doesn't chase;
  - the invoking session's two gate runs with the `RERUN` sweep;
  - the refuter pass;
  - `BOARD.md` regeneration (already current as of this closer's write).
- **Owed at THIS sprint's close (C3 is terminal — nothing further defers):**
  - the full wiki pass (currently 40 of 75; re-check at C3's own close-out — if still under
    60 the pass still runs here, since there is no later sprint to defer to);
  - full grounding audits;
  - the complete `AGENT_HANDOFF_TEMPLATE.md` ceremony, validated with
    `scripts/verify_doc_template.py`;
  - the epic-level adversarial review over the full epic diff;
  - recording the experiment outcomes from `epic-c-design-brief.md` §"What the experiment
    measures";
  - preparing the one epic PR to `main` for the owner's gate (halt point 1) — creation and
    push stay owner-gated, never taken unilaterally.
