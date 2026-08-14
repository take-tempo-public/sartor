# Blast radius — ats-conformance

> **Branch:** `feat/ats-conformance` (Epic B, sprint B2 — run 3 of 3)
> **Status:** complete — enumeration finished before the first production edit.

Scope of record: `docs/dev/RELEASE_ARC.md` §"Epic B — `epic/b-render-ats`" (B2),
re-anchored by `docs/dev/handoffs/epic-b-design-brief.md` row 3 and
`docs/dev/handoffs/epic-b-b2-brief.md` §"What this sprint builds".

**Why this dossier exists even though no `require-consumer-enumeration` surface is
touched.** `scripts/enforcement/blast_radius.py`'s `GATED` table does not list
`json_resume.py`, `blueprints/corpus/_shared.py` or `onboarding/corpus_import.py`, so
the hook will not fire on this branch. C-10 is a charter clause about *shared
contracts and widely-consumed helpers*, not about the hook's path list, and three of
this sprint's surfaces qualify on the clause's own terms — `format_date_range` is the
single presentation-boundary date helper for **six** renderers, `_experience_summary_dict`
is a wire payload with a Pydantic mirror, and `ImportReport` is consumed by a route, a
CLI printer and the frontend. The gate's own known limit ("path-level… curation-only for
JS/Jinja/CSS") is exactly the blind spot this change sits in: four Jinja personas and
`static/app.js` consume these contracts and no gate can see them.

---

## Surface

Seven surfaces change. Named precisely, with the symbol inside each:

| Surface | Symbol / section that changes |
|---|---|
| `json_resume.py` | `format_month_year` (separator `-` → `/`); **new** `is_month_precise`, `APPROVED_FONTS`, `map_to_approved_font`, `_ISO_YEAR_MONTH_RE`-adjacent comment block |
| `blueprints/generation.py` | **new** `_month_imprecise_roles` + its call in `run_generation` and `run_generation_stream` |
| `blueprints/corpus/_shared.py` | `_experience_summary_dict` — **new** `needs_month` key |
| `blueprints/corpus/experiences.py` | four `re.fullmatch(r"\d{4}(-\d{2})?")` date validators (create ×2, edit ×2) → month-required |
| `web_infra/openapi.py` | `ExperienceSummaryItem` — **new** `needs_month` field |
| `onboarding/corpus_import.py` | `ImportReport` — **new** `experiences_needing_month` / `month_needed_experiences`; `merge()`; `_ingest_one_experience`; `format_report` |
| `docx_to_persona_html.py` / `generator.py` / `scripts/build_bundled_templates.py` | off-list font mapping + explicit docx `Normal`-style font |

Plus presentation-only consumers: `static/app.js`, `static/style.css`, four
`personas/bundled/*.css`, `blueprints/corpus/curation.py`,
`onboarding/extract_experiences.py` (prompt text + comment), `analyzer.py`
(`PROMPT_VERSION` bump, required by AGENTS.md §"LLM prompts").

---

## Enumeration

Every command below was run from the repo root at HEAD `37915ca`, **before** the first
production edit. `git grep` (not plain `grep`) so the search is the whole tracked tree,
not a subdirectory.

```
$ git grep -n "format_month_year" | wc -l
16
$ git grep -ln "format_month_year"
CHANGELOG.md
docs/dev/handoffs/epic-b-b2-brief.md
docs/dev/handoffs/epic-b-design-brief.md
json_resume.py
tests/test_json_resume.py
```

The narrow symbol name hides the real fan-in: the helper reaches renderers through
`format_date_range` and through the `date_range` Jinja global, so the second search is
the load-bearing one.

```
$ git grep -ln "format_date_range\|date_range"
CHANGELOG.md                                     docx_to_persona_html.py
corpus_to_json_resume.py                         generator.py
db/build_context.py                              json_resume.py
docs/dev/RELEASE_ARC.md                          onboarding/review_cli.py
docs/dev/blast-radius/b1-stale-template-companions.md   pdf_render.py
docs/dev/diagnosis/b1-education-render.md        personas/bundled/classic.html
docs/dev/diagnosis/b1-stale-template-companions.md      personas/bundled/modern.html
docs/dev/handoffs/epic-b-b1a-brief.md            personas/bundled/spacious.html
docs/dev/handoffs/epic-b-b2-brief.md             personas/bundled/tech.html
docs/dev/handoffs/epic-b-design-brief.md         tests/test_docx_to_persona_html.py
                                                 tests/test_json_resume.py
                                                 tests/test_pdf_render.py
                                                 tests/test_resume_date_formatting.py
```

**The two `date_range` hits that are NOT this helper** — found by reading each, not by
assuming the name meant one thing:

```
$ git grep -n "date_range = f" -- db/ onboarding/
db/build_context.py:457:        date_range = f"{exp.start_date} — {exp.end_date or 'Present'}"
onboarding/review_cli.py:151:        date_range = f"{exp.start_date} → {exp.end_date or 'present'}"
```

Both are **local variables that shadow the name** and interpolate raw ISO storage. Neither
imports `json_resume`. They are prompt-payload / CLI text, not the presentation boundary.
Recorded so a later reader does not "fix" them into the helper — see `## Deferred`.

Literal `MM-YYYY` assertions that must move in lockstep with the separator:

```
$ git grep -n "0[0-9]-20[0-9][0-9]" -- tests/ personas/ | grep -v "555-\|010-2200\|claude-haiku"
tests/test_docx_to_persona_html.py:364,376
tests/test_json_resume.py:381,398,587,605,610,611,620
tests/test_pdf_render.py:123
tests/test_resume_date_formatting.py:62,63,64,65,74,75,92,93,102
```

19 assertion sites across 4 files. `test_render_parity.py` returns **zero** hits — a
negative result that contradicts RELEASE_ARC:1930, which names it as needing an update.
Verified by reading: it asserts structural parity across renderers, never a literal date.

Payload / report contracts:

```
$ git grep -n "_experience_summary_dict"
blueprints/corpus/_shared.py:35        (definition)
blueprints/corpus/experiences.py:23   (import)
blueprints/corpus/experiences.py:87   (the one call site)
web_infra/openapi.py:129              (docstring: "Mirrors _experience_summary_dict")
docs/wiki/pages/openapi-api-reference.md:88, docs/wiki/pages/route-surface.md:170
docs/dev/blast-radius/experience-soft-retire.md:139,166  (the prior enumeration of this
                                                          same pair — it found the
                                                          openapi mirror the same way)

$ git grep -ln "ImportReport"
CHANGELOG.md  blueprints/corpus/curation.py  docs/dev/RELEASE_CHECKLIST.md
docs/dev/kit-adoption-design.md  onboarding/corpus_import.py  tests/test_corpus_import.py
```

The `experiences_dropped` / `dropped_experiences` pair is the **exact precedent** this
change copies (a counter + a detail list, surfaced in four places). Tracing it gives the
complete surfacing path for free:

```
$ git grep -n "dropped_experiences\|experiences_dropped" -- '*.py' '*.js'
onboarding/corpus_import.py:100,101,120,121,622,623,984,991   (field, merge, record, CLI text)
blueprints/corpus/curation.py:498,506,509,519,520              (logger.warning + JSON payload)
static/app.js:809,810                                          (the user-visible note)
tests/test_corpus_ingest_route.py:163-165, tests/test_corpus_import.py:641,642
```

Negative results (each one a finding — nothing to extend, so this is net-new build):

```
$ git grep -n "needs_month\|month_needed\|needs month"        -> 0 hits
$ git grep -n "APPROVED_FONT\|approved_font"                  -> 0 hits
$ git grep -n "month precision"  -> 3 hits, ALL in docs (RELEASE_ARC:1938,
                                    epic-b-b2-brief.md:99, epic-b-design-brief.md:95)
$ python -c "...'month' occurrences in blueprints/generation.py" -> 0
```

Corpus date validators, counted rather than eyeballed:

```
$ python -c "re.findall(r're\.fullmatch\((r\"[^\"]+\")', <experiences.py>)"
['r"\\d{4}(-\\d{2})?"', 'r"\\d{4}(-\\d{2})?"', 'r"\\d{4}(-\\d{2})?"', 'r"\\d{4}(-\\d{2})?"']
```

Four, not the two the brief's `~:115-123, ~:218-227` anchors imply — create validates
`start_date` **and** `end_date`, and so does edit. Both briefs cite only the start-date
pair. **A change that fixed only the two cited lines would leave year-only end dates
passing.**

Font surfaces:

```
$ git grep -n "Arial\|Calibri\|Georgia\|font_name\|font-family" -- personas/ generator.py \
      pdf_render.py docx_to_persona_html.py json_resume.py scripts/build_bundled_templates.py
personas/bundled/{classic,modern,spacious,tech}.css   (4 base font-family rules)
personas/cover_letter.html:42                          ({{ font_family }} — injected)
docx_to_persona_html.py:85-93   (_css_font_stack — the imported-docx font path)
generator.py:323-339            (_cover_letter_font_name)
generator.py:502,521,607,608,626 (run_font_name capture/apply — landed in B1b)
generator.py:735                (Normal.font.name = "Calibri", NO-TEMPLATE branch only)
pdf_render.py:52,56,214-241     (persona_font_family)
scripts/build_bundled_templates.py:69,114,130,146,168 (TypographyPreset.font_family)
```

---

## Consumers

One row per site. Every row decided **before** the first edit.

### A. The date separator (`MM-YYYY` → `MM/YYYY`)

| # | Site (`path:line`) | Decision | Rationale |
|---|---|---|---|
| 1 | `json_resume.py:588-605` (`format_month_year`) | **update** | The single mutation. `f"{month}-{year}"` → `f"{month}/{year}"`. Docstring's stated format changes with it. |
| 2 | `json_resume.py:607-622` (`format_date_range`) | **no change (code)** | Delegates to #1; the ` – ` en-dash separator and the `Present` sentinel are explicitly retained by the acceptance criterion. Docstring text updated only. |
| 3 | `json_resume.py:78-82` (format comment block) | **update** | States "owner-decided: numeric MM-YYYY". Leaving it is drift on the line that explains the decision. |
| 4 | `json_resume.py:721,753` (`json_resume_to_markdown` work/education) | **no change** | Calls #2. Behavior follows automatically — that is the point of the single helper. |
| 5 | `generator.py:670-678` (`_date_range`) | **docstring only** | Thin wrapper; its docstring names the old format. |
| 6 | `pdf_render.py:71-87` (`_register_date_range_global`) | **docstring only** | Registers #2 as the Jinja `date_range` global; docstring names the old format. |
| 7 | `personas/bundled/{classic,modern,spacious,tech}.html` (7 `date_range(...)` calls) | **no change** | They call the global registered at #6. The four templates are the reason the helper exists; touching them would fork it. |
| 8 | `corpus_to_json_resume.py:912` (comment) | **no change** | Prose reference to "the boundary", format-agnostic. Re-read to confirm. |
| 9 | `tests/test_json_resume.py:381,398,587,605,610,611,620` | **update** | 7 literal assertions. `:381/:398` are the markdown **round-trip** pair — the highest-value ones, because they prove `09/2010` survives `_split_h3_header` and re-emits identically. |
| 10 | `tests/test_resume_date_formatting.py:62-102` | **update** | 9 literals. This file is the declared cross-renderer regression guard; its module docstring names the format and changes too. |
| 11 | `tests/test_pdf_render.py:121-123` | **update** | 1 literal + its comment. Named explicitly in RELEASE_ARC:1930. |
| 12 | `tests/test_docx_to_persona_html.py:364,376` | **update** | 2 literals. B1a's acceptance bar (`04-2023 – Present`); it renders through the same global, so it moves or B1a's own guard goes red. |
| 13 | `tests/test_render_parity.py` | **no change** | **Negative result, contradicting RELEASE_ARC:1930** which names it. `git grep "0[0-9]-20[0-9][0-9]"` = 0 hits; read in full — it asserts structural parity, never a date literal. Recorded rather than silently skipped. |
| 14 | `db/build_context.py:457` | **no change** | Local variable that *shadows* the name. Raw ISO into the LLM prompt payload. Storage stays ISO by design (`json_resume.py:79`); reformatting the prompt would change what the model sees for zero user-visible gain. |
| 15 | `onboarding/review_cli.py:151-152` | **no change** | Same shadowing; a dev CLI with a `→` separator that was never the product's presentation format. |
| 16 | `CHANGELOG.md:3609-3615` | **no change** | Historical entry describing the 2026-05 decision as it was then. Amending history is worse than superseding it; the new entry supersedes. |

### B. Month precision — predicate, generate-time block, corpus badge, validation

| # | Site (`path:line`) | Decision | Rationale |
|---|---|---|---|
| 17 | `json_resume.py` (**new** `is_month_precise`) | **add** | One canonical predicate for "this stored ISO date carries a month". `json_resume.py` already owns `_ISO_YEAR_MONTH_RE` / `_ISO_YEAR_ONLY_RE`, is on the deterministic-boundary list (C-6 safe), and is importable from `blueprints/`, `db/` and `onboarding/` without a cycle (`hardening.py:26` imports `json_resume`, never the reverse). Defining it in `hardening.py` would drag telemetry+threading into the importer for a regex. |
| 18 | `blueprints/generation.py` (**new** `_month_imprecise_roles`) | **add** | Reads the *included* roles from whichever path is live: `frozen_doc["work"]` when a composition is frozen, else `context_set["career_corpus"]`. **Education is never read** — the owner's exemption is enforced by which key the function looks at, not by a filter that could be edited away. |
| 19 | `blueprints/generation.py:869` (`run_generation`) | **update** | Insert the block after `_is_pre_corpus_context` and before the first LLM call, so a blocked run costs zero tokens. |
| 20 | `blueprints/generation.py:1161` (`run_generation_stream`) | **update** | **The site the briefs do not name.** Same request shape, same payload, its own copy of the preamble. Blocking only `/api/generate` would leave the SSE path wide open — the shipped-green-with-the-defect-intact failure this sprint was warned about. Found by `git grep -n "_is_pre_corpus_context"`, not by the brief. |
| 21 | `blueprints/corpus/_shared.py:35-59` (`_experience_summary_dict`) | **update** | Add `needs_month`. Computed server-side so the badge and the block agree by construction — a JS-side re-derivation is a second implementation of the rule, the exact disagreement item 20 records for `frozen_composition_doc`. |
| 22 | `web_infra/openapi.py:128-145` (`ExperienceSummaryItem`) | **update** | Its docstring says it "Mirrors `_experience_summary_dict`". `experience-soft-retire.md:166` is the precedent: adding a key there without this is drift. |
| 23 | `blueprints/corpus/experiences.py` create — `start_date` + `end_date` validators | **update** | Month-required. |
| 24 | `blueprints/corpus/experiences.py` edit — `start_date` + `end_date` validators | **update** | Same. Rows 23+24 are **four** validators; both briefs cite two. |
| 25 | `static/app.js:4960` (corpus card header) | **update** | Render a `MONTH NEEDED` flag next to the existing `RETIRED` one — same `corpus-row-flag` idiom, same header row. |
| 26 | `static/app.js:5057-5058` (`start_date`/`end_date` field spec) | **update** | Client `pattern` is already `\d{4}-\d{2}`, but the labels say "(YYYY-MM)" while the server used to accept `YYYY`. Now the server agrees; the placeholder/hint says month is required so the rejection is predictable rather than surprising. |
| 27 | `static/style.css` (`.corpus-row-flag`) | **update** | Add the `.needs-month` colour variant beside `.retired`. |
| 28 | `static/app.js:4453,5456,5581,5996,6178,8867` (other date renderers) | **no change** | Corpus-editor surfaces that print raw ISO storage. They are *editing* views of stored values, not the résumé presentation boundary; showing `09/2022` in a field whose validator wants `2022-09` would be actively misleading. |
| 29 | `db/models.py` (`Experience.start_date`) | **no change** | **Deliberate, and the reason matters:** month-precision is a *policy*, not a schema constraint. Existing rows are year-only; a NOT-NULL-style tightening would break load for corpora already on disk. This also keeps the branch off `GATED["db/models.py"]`. |

### C. Import-path surfacing

| # | Site (`path:line`) | Decision | Rationale |
|---|---|---|---|
| 30 | `onboarding/corpus_import.py:68-101` (`ImportReport`) | **update** | Add `experiences_needing_month: int` + `month_needed_experiences: list[dict]`, mirroring `experiences_dropped` / `dropped_experiences` exactly. |
| 31 | `onboarding/corpus_import.py:104-123` (`merge`) | **update** | Sub-reports are merged per file. A counter added without a `merge()` line silently reports only the last file's total — the failure the existing pairs already avoid. |
| 32 | `onboarding/corpus_import.py:614-621` (`_ingest_one_experience`) | **update** | Record the finding **before** the create/merge branch, so both paths count. The dedup key is `(company, start_date)`, so a year-only role that merges into an existing year-only row still needs surfacing. |
| 33 | `onboarding/corpus_import.py:984-995` (`format_report`) | **update** | The CLI text summary — carries the required sentence "N role(s) need month precision and will block generation". |
| 34 | `blueprints/corpus/curation.py:498-521` (ingest route) | **update** | `logger.warning` + the two new JSON payload keys, mirroring the dropped-role block immediately above it. |
| 35 | `static/app.js:809-819` (ingest result copy) | **update** | The user-visible half. Without it the report exists and nobody reads it. |
| 36 | `onboarding/extract_experiences.py:85` (extraction prompt) | **update** | The literal "(year-only is fine — many résumés list years only)" now contradicts a product that hard-blocks on year-only. Ask for month precision *when the résumé shows it*; keep year-only accepted so roles still land. |
| 37 | `analyzer.py:495` (`PROMPT_VERSION`) | **update** | AGENTS.md §"LLM prompts" is unconditional: any prompt-template change bumps it in the same commit. #36 is a prompt-template change. `call_kind="extract_experiences"` is stamped with it. |
| 38 | `onboarding/extract_experiences.py:194-197` (`_DATE_RE`) | **no change (comment only)** | **Tightening this would be a regression.** A year-only date failing `_DATE_RE` drops `start_date`, which sends the whole role down the `experiences_dropped` path at `corpus_import.py:616` — the role vanishes instead of arriving flagged. Its comment is updated to say why it stays permissive. |
| 39 | `tests/test_corpus_import.py:430` (`"start_date": "2020"`) | **no change** | An existing year-only fixture. It must keep passing: it is the proof that #38 held and year-only still *enters* the corpus. New assertions ride on the same fixture. |

### D. Approved fonts + structure

| # | Site (`path:line`) | Decision | Rationale |
|---|---|---|---|
| 40 | `json_resume.py` (**new** `APPROVED_FONTS`, `map_to_approved_font`) | **add** | One canonical allow-list. Sits beside `_ATS_UNSAFE_CHARS` / `scrub_ats_unsafe` — `json_resume.py` is already the ATS **output-policy** home (`hardening.check_ats_format` is the different job of warning about *parsed input*). |
| 41 | `docx_to_persona_html.py:85-93` (`_css_font_stack`) | **update** | The imported-docx font path. `_css_font_stack("Papyrus")` currently emits `"Papyrus", …` as the CSS primary — observed. Map to the nearest approved family and keep the original only as a downstream fallback. |
| 42 | `docx_to_persona_html.py` (companion writer) | **update** | Emit the substitution notice — "visible notice" is in the acceptance criterion, and a silent swap is worse than the off-list font. |
| 43 | `generator.py:_write_docx_from_json_resume` (template branch, `:725-730`) | **update** | **The observed gap.** All four bundled templates return `Normal.font.name is None` after generation (probe R2). RELEASE_ARC:1938 names it: "set the docx Normal-style font explicitly". A run with no captured proto currently inherits Word's `docDefaults`, which is not ours to control. |
| 44 | `generator.py:735` (no-template branch) | **no change** | Already `Calibri`, already approved. Re-verified rather than assumed. |
| 45 | `generator.py:521,607-608,626` (`run_font_name` capture/apply) | **update (map on apply)** | B1b started carrying the template's real font name into output. That is the path an off-list imported font now reaches the generated `.docx` by — B1b closed a data-loss hole and opened this one. Map at the apply boundary. |
| 46 | `generator.py:323-339` (`_cover_letter_font_name`) | **update** | Takes the CSS stack's *primary*, which for `classic.css` is `Helvetica Neue` — off-list, and it becomes a real `.docx` font name. |
| 47 | `personas/bundled/classic.css:42`, `modern.css:45` | **update** | Primaries `"Helvetica Neue"` and `Roboto` — both off-list (probe R6). Approved family first, old stack retained behind it so nothing regresses where the font exists. |
| 48 | `personas/bundled/spacious.css:33`, `tech.css:44` | **no change** | Both already lead with `Georgia`. Verified, not assumed. |
| 49 | `scripts/build_bundled_templates.py:114,130,146,168` (`font_family`) | **no change (assert instead)** | Already `Arial`/`Calibri`/`Arial`/`Georgia` — all approved (probe, `.docx` runs). Nothing to change; what is missing is anything *stopping* a future preset from going off-list. A test asserts the presets against `APPROVED_FONTS`. |
| 50 | `personas/cover_letter.html:42` (`{{ font_family }}`) | **no change** | Renders whatever #46 hands it; fixing the source is the correct single point. |
| 51 | `tests/test_ats_structure.py` (**new**) | **add** | Item 6. Single column, no tables, no text boxes, no header/footer text, standard headings only, approved fonts — asserted on the **generated output** `.docx` (RELEASE_ARC:1940 says "output docx"), not only on the bundled inputs. |
| 52 | `tests/test_ats_roundtrip.py` | **no change** | Parses generated `.docx` back for bullet/section recovery — a different axis. Must stay green as a regression witness on #43/#45. |

---

## Deferred

1. **`db/build_context.py:457` and `onboarding/review_cli.py:151`** — the two
   `date_range` local variables that shadow the helper's name. Left as raw ISO
   interpolation. `build_context`'s string is prompt payload: the model reads ISO today,
   and changing what it reads is a prompt change with eval-attribution cost for no
   user-visible benefit. `review_cli`'s is dev-tool output that never used the product
   format. Recorded because the shared *name* makes them look like consumers, and a later
   reader deserves the reason rather than having to re-derive it.

2. **A UX (Playwright) test for the `MONTH NEEDED` badge.** Would require adding a
   selector to `ui_pages/selectors.py`, which **is** `GATED` ("the one selector registry;
   14 non-test importers, consumed by the whole `pytest -m ux` tier AND
   `scripts/capture_screenshots.py`"). Editing it would pull a genuine gated contract into
   a sprint whose scope does not include it. Covered instead at the seam that carries the
   decision — `needs_month` on the route payload, asserted server-side — so the badge
   renders from data that is tested even though the rendering itself is not. **This is a
   real gap, stated not papered over:** a JS typo in the badge would not be caught. It is
   the smaller of the two risks.

3. **The `_split_h3_header` `" — "` fallback / institution-less emitter ambiguity.**
   Out of scope by name (`epic-b-b2-brief.md` §"Explicitly OUT of scope"; filed as item
   90). This branch touches `json_resume.py` and the markdown round-trip, so the boundary
   is worth restating: the separator change is inside `format_month_year` only, and
   `_split_h3_header` is not edited. Verified after the fact by `git diff`.

4. **Retro-fixing existing year-only rows.** No migration, no backfill. The corpus is the
   user's data; guessing a month is invention (C-3). The badge plus the block plus the
   import summary tell them which rows to fix, and the edit form now requires a month when
   they do.

---

## Verification

How a **missed consumer** surfaces — not how the change works:

1. **The separator.** 19 literal assertions across 4 files fail loudly on any renderer
   whose path was missed, because every one asserts a full date string. The markdown
   round-trip pair (`test_json_resume.py:381/398`) is the strongest: it emits *and*
   re-parses, so a separator the parser cannot read back fails there rather than silently
   producing a lossy second cycle. Run: `pytest tests/test_json_resume.py
   tests/test_resume_date_formatting.py tests/test_pdf_render.py
   tests/test_docx_to_persona_html.py tests/test_render_parity.py`.

2. **The generate-time block.** Tested on **both** entry points. `run_generation_stream`
   is the site neither brief names; a test that only drove `/api/generate` would pass
   with the SSE path unguarded, so the SSE test is the one that proves the enumeration
   found row 20.

3. **The payload contract.** `ExperienceSummaryItem` is validated by spectree against the
   live response, so a `needs_month` added to `_experience_summary_dict` and forgotten in
   `web_infra/openapi.py` (or vice versa) surfaces as a schema failure rather than as
   silence.

4. **Fonts.** `tests/test_ats_structure.py` asserts an **exact set** — every font name in
   every generated `.docx` must be a member of `APPROVED_FONTS` — rather than checking a
   list of known-bad names. A new persona preset, a new emitter, or a new capture path that
   introduces an off-list font fails without anyone remembering to add it to a deny-list.
   Same shape for the presets in `scripts/build_bundled_templates.py`.

5. **Import surfacing.** `tests/test_corpus_import.py:430`'s pre-existing year-only fixture
   must still produce a created (not dropped) role — that is the assertion that catches a
   too-eager tightening of `_DATE_RE` (row 38), which is the one change in this area that
   would look correct and silently delete user data.
