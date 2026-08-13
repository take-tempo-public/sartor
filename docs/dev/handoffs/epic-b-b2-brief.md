# Epic B sprint brief — B2: ATS conformance (`feat/ats-conformance`)

> Written from [`EPIC_SPRINT_BRIEF_TEMPLATE.md`](EPIC_SPRINT_BRIEF_TEMPLATE.md) — the
> declared intra-epic cadence artifact (`epic-b-design-brief.md` §"Close-out intervals").
> Authored 2026-08-13 by `fix/b1-education-render`'s closer (the derived intra-epic path —
> `epicSprintIndex: 2 < epicSprintCount: 3`), from `epic-b-design-brief.md` row 3,
> `RELEASE_ARC.md` §Epic B (B2), and this sprint's own judge-confirmed refuter findings.

---

## Sprint identity

- **Sprint:** B2 — Epic B run 3 of 3 (the epic's **terminal** sprint — its own closer
  runs the full `AGENT_HANDOFF_TEMPLATE.md` ceremony, not another sprint brief; the
  pipeline derives this from `epicSprintIndex(3) == epicSprintCount(3)`, not from a
  caller-chosen `closeoutKind`)
- **Branch to create:** `feat/ats-conformance` (name fixed in `epic-b-design-brief.md`
  row 3 — do not rename)
- **Stacked on:** `epic/b-render-ats` @ the tip **after** `fix/b1-education-render`'s
  ff-merge — resolve with `git rev-parse epic/b-render-ats` at cut time. Do **not** cut
  from this branch's pre-merge tip; verify `git log -1 epic/b-render-ats` shows this
  sprint's commit (the F1/F2/F3 corrections below, still uncommitted as this brief is
  written) before cutting.
- **Implementer model + effort:** Sonnet (`epic-b-design-brief.md` row 3 /
  `RELEASE_ARC.md` session-models table, B2). The **invoking session's** model is the
  owner's choice of Fable or Opus, stated at invocation.

## Standing context — read, do not expect it restated here

| What | Where |
|---|---|
| Design of record | `docs/dev/handoffs/epic-b-design-brief.md` — read in full; skipping this is the most expensive mistake this chain has made |
| Authorization envelope (run vector, halt points, flag stops, epic-remainder authorization) | `epic-b-design-brief.md` §"Execution mode + authorization record" + `docs/dev/n1-baseline-pipeline.md` §"Escalation" |
| Close-out cadence for this epic | `epic-b-design-brief.md` §"Close-out intervals" (light per sprint; **full ceremony now, at this sprint's own close, because B2 is the epic's last sprint** — board regen per-sprint, gate-bound) |
| Sprint scope | `docs/dev/RELEASE_ARC.md` §"Epic B — `epic/b-render-ats`" (B2) as re-anchored by `epic-b-design-brief.md` row 3 |
| The invoker's own loop | `docs/dev/n1-baseline-pipeline.md` §"The runbook" — step 0a (preflight batch + scope reconciliation) through step 9 (the epic loop) |

## What just landed

- **B1a** (`d8f0a8f`, already on `epic/b-render-ats`): stale imported-template
  companions fixed on a skeleton-version stamp; refuter F1 applied, F2 deferred as item
  88, item 89 filed.
- **B1b** (`fix/b1-education-render`, **staged, not yet committed** as this brief is
  written — the invoking session's gate + commit + ff-merge are still owed): the
  implementer rendered `studyType` across the education surfaces that were dropping it
  (Classic, Spacious, the `.docx` writer, the markdown round-trip — Modern and Tech
  already rendered it) via one canonical joiner
  (`json_resume.education_position_text` / `split_education_position` /
  `EDUCATION_FIELD_SEPARATOR`), and closed the docx template font-name capture gap
  (`generator.py:_capture_proto`/`_apply_run_proto`/`_add_inline_runs_with_proto` now
  carry `run_font_name`). The refuter raised one finding (F1: an institution-less
  education entry's `studyType` gets re-keyed into `institution` on the markdown
  round-trip via `_split_h3_header`'s pre-existing `" — "` fallback) plus two doc-accuracy
  findings (F2: several docstrings/titles claimed "three of the four [render surfaces]"
  dropped `studyType" — the actual counts are either "2 of 4 personas" or "4 of 6
  surfaces total" depending on context, never "3 of 4"; F3: two stale `path:line`
  anchors in the diagnosis dossier's "The fix" section). The judge confirmed all three
  as real but **narrow** — F1 is investigated-and-proven-NOT-a-regression (executed
  both the pre-fix and post-fix code on the institution-less path: pre-fix drops
  `studyType` before parsing ever runs, `{institution: <area>}`; post-fix is a strict
  superset, `{institution: <area>, area: <studyType>}` — NOT byte-identical, strictly
  more data), so the fix ordered was a docstring/test correction, not a change to
  `_split_h3_header`. This closer applied all three: `json_resume.py`'s
  `EDUCATION_FIELD_SEPARATOR` docstring now states the true, narrower guarantee (no
  collision only when an institution is present) and names the institution-less
  collision explicitly; a new test
  (`test_institution_less_entry_re_keys_studytype_into_area_on_emit`) pins that exact
  behavior and its second-cycle stability; the count corrections landed in
  `corpus_to_json_resume.py`, `json_resume.py`, `tests/test_render_parity.py`, the
  diagnosis dossier (title + "The fix" §0), and the blast-radius dossier (:18, :95-96);
  the two stale anchors were re-derived post-edit (`generator.py:911`,
  `json_resume.py:751`) and cross-checked against the live tree by grep, not
  hand-counted. 186 scoped tests pass
  (`test_json_resume.py`/`test_render_parity.py`/`test_pdf_render.py`/`test_corpus_to_json_resume.py`);
  `ruff check` / `ruff format --check` / `mypy .` scoped-and-whole-repo all clean. **The
  invoking session's own gate has not run yet** — that and the commit are this sprint's
  own next steps, owed before `feat/ats-conformance` is cut.

## What this sprint builds

From `RELEASE_ARC.md` §Epic B (B2) via `epic-b-design-brief.md` row 3:

1. **Dates to `MM/YYYY`**, en-dash range separator retained, via the single canonical
   helper — re-verified at HEAD, now `json_resume.py:588-622`
   (`format_month_year`/`format_date_range`; the design brief's own citation,
   `582-616`, drifted by B1b's line insertions upstream in the same file — re-anchor
   again before trusting either number, the file may move further before B2 starts).
   Currently emits `MM-YYYY`.
2. **Month hard block at generate time** for included experience roles with year-only
   dates (**education exempt — owner decision**). Current validation
   (`blueprints/corpus/experiences.py` create ~`:115-123`, edit ~`:218-227` — both
   re-verified present at HEAD, accepting `\d{4}(-\d{2})?`, i.e. year-only still
   passes today) has no month-required path yet; this sprint adds one.
3. **"Month needed" corpus badge** + month-required create/edit validation (same file,
   same sites).
4. **Import-path surfacing**: year-only roles currently enter with no warning
   (`onboarding/extract_experiences.py:85` — re-verified, "year-only is fine" is still
   the literal extraction-prompt language; `onboarding/corpus_import.py:670-677`). The
   import summary must report "N roles need month precision and will block
   generation" — **verified this string does not exist yet** (grepped, zero hits).
5. **Approved fonts** `[Arial, Calibri, Georgia]` — no existing enforcement found by
   this closer; treat as net-new, not a re-verify.
6. **Structural tests**: single column, no tables/text boxes/headers/footers, standard
   headings only.

> **A named fix site in this section is a HYPOTHESIS, not a spec (C-0).** Verify each
> mechanism is reachable on the failing path before implementing — the education-only
> exemption in item 2 in particular should be confirmed against the corpus UI before
> the month-block logic is written, not assumed from this brief.

**Explicitly OUT of scope:** anything in B1a/B1b (already landed or landing this
sprint's predecessor); widening N past 1 (owner-reserved); the watching-bucket triage;
any refactor beyond the six items above; touching `_split_h3_header`'s `" — "`
fallback or the general institution-less/name-less emitter ambiguity across
`work`/`education`/`projects` that B1b's refuter surfaced and the judge explicitly
declined to fix (Consumer #11 in `docs/dev/blast-radius/b1-education-render.md`) —
that is a separate, unfiled work item, not this sprint's to pick up.

## First move

For the **invoking session**: runbook step 0 + 0a — preconditions, the batched
preflight (including the live dispatch probe and the scope reconciliation against the
authorization record), then:

```
Workflow({scriptPath: '.claude/workflows/n1-baseline.mjs', args: {
  stage: 'sprint',
  sprintBriefPath: 'docs/dev/handoffs/epic-b-b2-brief.md',
  epicBriefPath: 'docs/dev/handoffs/epic-b-design-brief.md',
  epicSprintIndex: 3,
  epicSprintCount: 3,
}})
```

No `nextSprintBriefPath` — `epicSprintIndex(3) == epicSprintCount(3)` derives
`closeoutKind: 'terminal'` (`.claude/workflows/n1-baseline.mjs:325`, re-verified at
HEAD). The pipeline's guard only throws the other direction — `nextSprintBriefPath`
missing when `closeoutKind` is `'intra_epic'` (`:326-327`) — so omitting it here is
correct, not merely harmless; verify this against the script before invoking in case
its shape has changed since this brief was written.

For the **implementer**: this is a `feat/*` branch — no `require-evidence-before-fix`
gate (that hook keys on `fix/*`; see `epic-b-design-brief.md` §"Branch topology" for
why this is deliberate, not a gap). Start from the design brief row 3's six items above,
each re-verified live before being implemented.

## Decisions taken alone last sprint that this one inherits

- **F1 (institution-less education collision) investigated and left unfixed,
  deliberately** — the judge's verdict was CONFIRMED-but-narrow: real, but not a
  regression (executed both pre-fix and post-fix: pre-fix drops `studyType` entirely,
  post-fix is a strict superset that recovers it re-keyed into `area` — not
  byte-identical, strictly better post-fix), not reachable from the product's own
  corpus forms today
  (`blueprints/corpus/career_assets.py` blocks empty `institution` at both create and
  edit), and its fix would touch `_split_h3_header`'s shared fallback — a scope change
  explicitly declined this sprint. Do not reopen `_split_h3_header` in B2 on the
  strength of this note; if B2's date-parsing work touches the same function for an
  unrelated reason, treat that as a **new** finding needing its own verdict, not a
  license to also fix F1.
- **The doc-count corrections (F2) are cosmetic, not behavioral** — nothing about
  which surfaces render `studyType` changed; only the prose describing the count was
  wrong and is now fixed in five places. No code implication for B2.
- **No new work items were filed by this sprint's closer** — the deferred-findings
  list handed to the closer was empty; all three refuter findings were fixed in-branch
  rather than deferred. If a future session wants the general institution-less/
  name-less emitter ambiguity tracked on `BOARD.md`, that is still open to file.

## Open risks handed forward

- **B1b's own gate has not run as this brief is written** — **reported, not
  verified**: 186 scoped tests pass and the three static checks (ruff/ruff
  format/mypy) are clean, but `python -m scripts.gate` (the full suite, including the
  UX tier) has not been run by anyone this sprint. That is the invoking session's next
  step, before `feat/ats-conformance` is cut.
- **The `format_month_year`/`format_date_range` citation drifts every time
  `json_resume.py` gains lines above it** (it has now drifted twice across two
  sprints: design-brief's `582-616` → this brief's re-verified `588-622`). Re-verify
  at HEAD before B2's implementer trusts either number.
- **Month-required validation and the import-summary string are both confirmed
  ABSENT at HEAD** (verified, not assumed) — B2 is building net-new logic, not
  extending an existing partial implementation, for items 2-4 of "What this sprint
  builds."
- **Approved-fonts enforcement (`[Arial, Calibri, Georgia]`)**: this closer found no
  existing check and did not search exhaustively (font names appear all over
  `generator.py`/`docx_to_persona_html.py` for capture/re-apply, which is a different
  concern from an *allow-list*) — B2's implementer should still enumerate before
  assuming there is nothing to extend.
- **Item-87 witness pause mid-run:** task notifications can re-arm the
  interrogative-witness, and its refusal landing on a subagent's first edit becomes a
  `hook_block` short-circuit stop (run-3 preflight, `acdb737`). The invoker consumes
  the pause deliberately before the first Workflow call (runbook step 0a); a mid-run
  re-arm that stops the run is the owner's call, not a thing to route around.

## Flag-stop state

None waiting. No halt point is pending; the epic PR (halt point 1) is owed at the epic
close, after B2 — which this sprint IS, so it arrives at the end of B2's own run, not
handed forward past it.

## Gate + verification state

- Last gate run: **none this sprint.** This closer ran only scoped verification —
  186 tests across the four affected test files, `ruff check` / `ruff format --check`
  scoped to the six touched Python files, and `mypy .` (whole repo, clean, 370 source
  files). **`python -m scripts.gate` was not run** — it belongs to the invoking
  session (§11.9), and B1b's own commit has not happened yet either.
- Rerun sweep: not applicable yet — no gate run to sweep.
- Wiki drift at handoff: **17 of 75** (`python -m scripts.wiki_freshness`, measured
  pre-commit against `HEAD=0838558`; will rise slightly once this sprint's 5
  wiki-relevant files are committed, still well under the epic's 40-file deferral
  margin). Scoped relevance check run and recorded this sprint
  (`docs/wiki/log.md`, 2026-08-13 entry): 5 relevant paths, 0 pages needed an edit.
  Each run's monitor re-runs the drift check at the sprint gate.

---

## Close-out obligations this sprint still owes

- **Owed now (per-sprint floor, `epic-b-design-brief.md` §"Close-out intervals"):**
  C-7/C-10 dossiers where triggered (hook-gated — B2 is `feat/*`, so C-7's
  `require-evidence-before-fix` does not fire; C-10 fires only if a gated surface is
  touched, unlikely for this scope but re-check); a substantive commit message
  (composed by the invoking session for the finalize stage); work items filed for
  anything discovered-and-not-chased; board regeneration (gate-bound); the invoking
  session's two gate runs with the log swept for `RERUN`; the refuter pass; the
  scoped wiki-relevance check on B2's own diff.
- **Deferred to epic close (this sprint IS the epic close):** the wiki pass +
  `.last_ingest_sha` advance (widened to the full backlog per
  `epic-a-chain-design-corrections.md` §11.11's zeroing precedent, since Epic B
  inherited a non-zero starting drift too), full grounding audits, the full
  `AGENT_HANDOFF_TEMPLATE.md` ceremony with `verify_doc_template.py` validation, the
  epic-level adversarial review, experiment outcomes recorded
  (`epic-b-design-brief.md` §"What the experiment measures"), the epic PR
  (owner-gated halt point 1). **B2's own closer owes all of these** — this is the
  terminal sprint; there is no B3 to defer further to.
