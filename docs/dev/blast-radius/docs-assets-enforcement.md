# Blast radius — docs-assets-enforcement

> **Branch:** `feat/docs-assets-enforcement`
> **Status:** enumeration complete for the planned changes. Written before the first content
> edit, 2026-10-01, on `feat/docs-assets-enforcement` at `4ff22b4`. Plan: the owner-approved
> D4 plan; the owner's decisions are quoted in [Surface](#surface). Later steps get a dated
> addendum here before their first edit.

---

## Surface

Epic D sprint D4 (`docs/dev/RELEASE_ARC.md:2019-2023`; `docs/dev/docs-ia-design.md` §5,
done criterion `:458-460`). Owner decisions at kickoff, 2026-10-01:
- D4 runs on Opus in this session (the arc names Sonnet; the deviation goes in the handoff).
- "Learn more" links target the public docs site, `https://sartor-docs.taketempo.com/docs/<slug>/`.
- No Settings help bubble in D4: filed as a work item.
- Mermaid is checked by a fail-closed Playwright step in docs-deploy CI.
- A short work item for reviewing current models and settings for performance and cost
  (outside D4's build).

What changes:

1. **`scripts/doc_corpus.py` (new).** One `git ls-files '*.md'`, each file read once, header
   fields, unfenced lines, tracked-path set, lexical link-target resolution.
2. **`scripts/check_doc_links.py`, `scripts/check_doc_frontmatter.py`,
   `scripts/check_doc_single_home.py`.** Re-based onto the corpus. Their CLI contract (args,
   exit codes, message text) does not change; `PUBLISHED_DOC_FILES` stays exported from
   `check_doc_frontmatter`.
3. **New lints (§5.3–§5.9)** in a new test module plus the corpus. Fixes to the true
   violations each one finds land in the same commit as that lint.
4. **`scripts/project_docs_to_mdx.py`: `build_frontmatter`** gains a source-commit stamp
   (item 126).
5. **`static/help-modal.js`: `cbOpenHelpModal`** renders an optional "Learn more" link and
   widens its focus trap from `button` to `button, a[href]`.
6. **`_HELP_REGISTRY` (`static/app.js`) and `_DASH_HELP` (`dashboard/templates/dashboard.html`)**
   gain an optional `learnMore` slug on entries that have a doc page.
7. **The two `#helpModal` containers** (`templates/index.html:1122-1132`,
   `dashboard/templates/dashboard.html:893-898`) gain an empty, hidden link slot.
8. **`docs/wiki/SCHEMA.md:104-107`** (gated): the stale "five Sprint-6.5 education guides"
   sentence is corrected to the current user-tier set.
9. **`ui_pages/selectors.py`** (gated): one new selector, `Help.MODAL_LEARN_MORE`, for the UX
   test.

Not changed: `docs/dev/AGENT_HANDOFF_TEMPLATE.md` (item 135 is the owner's decision),
`scripts/wiki_relevance.py` (a new `scripts/*.py` defaults to irrelevant under
`MIXED_PREFIXES`, `:106`, which is correct for lint tooling).

---

## Enumeration

Run on `4ff22b4`, 2026-10-01. Whole tree, `git grep`.

```
git grep -l <name> | wc -l
  check_doc_links         28    check_doc_frontmatter   20    check_doc_single_home 14
  PUBLISHED_DOC_FILES     16    project_docs_to_mdx     29    build_frontmatter      2
  help-modal              19    cbOpenHelpModal          6    _HELP_REGISTRY        23
  _DASH_HELP              22    doc_registry            18
```

Code-level (imports / invocations), the only sites whose behavior can break:

```
git grep -nE "(import|from) .*(check_doc_links|check_doc_frontmatter|check_doc_single_home|doc_registry|project_docs_to_mdx)" -- '*.py' '*.yml' '*.mjs' '*.ts' '*.tsx'
  scripts/check_doc_frontmatter.py:40   from doc_registry import PUBLISHED, PUBLISHED_PATHS, Entry, is_record
  scripts/check_doc_links.py:91         from check_doc_frontmatter import PUBLISHED_DOC_FILES
  scripts/check_doc_links.py:92         from doc_registry import is_record
  scripts/check_doc_single_home.py:56   from check_doc_frontmatter import PUBLISHED_DOC_FILES
  scripts/docs_move.py:50               from doc_registry import is_record
  scripts/project_docs_to_mdx.py:87     from doc_registry import PUBLISHED, Entry
  tests/test_doc_registry.py:18-19      doc_registry, project_docs_to_mdx
  tests/test_doc_single_home_gate.py:25 check_doc_single_home
  tests/test_docs_move.py:23            check_doc_links
  tests/test_docs_projection.py:24-25   project_docs_to_mdx, doc_registry
.github/workflows/docs-deploy.yml:70    python scripts/project_docs_to_mdx.py

git grep -n "help-modal\|cbOpenHelpModal" -- static templates dashboard ui_pages tests scripts
  dashboard/templates/dashboard.html:18,1757   load + call
  templates/index.html:1437                    load
  static/app.js:2374                           call
  static/assistant.js:12                       comment only (precedent note)
  tests/ux/a11y/test_axe_smoke.py:155,182,339  axe on the open modal
  tests/ux/regression/test_20260923_dashboard_polish_ux.py:115  body text check
  ui_pages/dashboard_console.py:61, ui_pages/selectors.py:77-81,85,132  locators
```

Negative results: `learnMore|learn more|docsUrl|helpUrl` in `static/ templates/ dashboard/` = 0;
no docs-site URL anywhere in app code (`sartor-docs|taketempo` in `static/ templates/
dashboard/ blueprints/ app.py` = 0).

The remaining text hits (CHANGELOG, handoffs, reviews, blast-radius dossiers, RELEASE_*,
design docs) are records or prose that name the scripts. Records are frozen. Live prose is
re-checked per step below.

---

## Consumers

| # | Site (`path:line`) | Decision | Rationale |
|---|---|---|---|
| 1 | `scripts/check_doc_links.py` (whole) | update | Re-based on `doc_corpus`; lexical link resolution. CLI + messages unchanged. |
| 2 | `scripts/check_doc_frontmatter.py:40-44` | update | Reads headers from the corpus; keeps exporting `PUBLISHED_DOC_FILES` for #1, #3. |
| 3 | `scripts/check_doc_single_home.py:56,140` | update | Reads bodies from the corpus instead of its own `read_text`. |
| 4 | `scripts/docs_move.py:50` | no change | Imports only `doc_registry.is_record`, which is untouched. |
| 5 | `tests/test_doc_links.py`, `tests/test_doc_frontmatter_gate.py`, `tests/test_doc_single_home_gate.py`, `tests/test_docs_move.py:23` | no change (must stay green) | They are the behavior-preservation oracle for #1–#3. `test_docs_move` calls `cdl` functions directly, so any helper it uses keeps its signature. |
| 6 | `scripts/project_docs_to_mdx.py:455-465` (`build_frontmatter`) | update | Adds the source-commit stamp (item 126). |
| 7 | `tests/test_docs_projection.py` (`build_frontmatter` asserts) | update | Asserts the stamp is present and well-formed. |
| 8 | `.github/workflows/docs-deploy.yml:70` | update | Adds the Mermaid fallback check after `npm run build`. The projector call stays as it is. |
| 9 | `static/help-modal.js:45-86` (`cbOpenHelpModal`) | update | Optional link + focus trap includes `a[href]`. An entry without `learnMore` must behave exactly as today (link slot stays hidden). |
| 10 | `static/app.js:2184-2360` (`_HELP_REGISTRY`), `:2374` | update | `learnMore` slug on entries with a user-doc page. The caller at `:2374` is unchanged. |
| 11 | `dashboard/templates/dashboard.html:1280-1730` (`_DASH_HELP`), `:1757` | update | `learnMore` slug → `dev-diagnostics` sections. The caller at `:1757` is unchanged. |
| 12 | `templates/index.html:1122-1132`, `dashboard/templates/dashboard.html:893-898` | update | Hidden link slot inside each `#helpModal`. |
| 13 | `tests/ux/a11y/test_axe_smoke.py:155,182,339` | no change (must stay green) | axe runs on the open modal; a visible link must pass contrast + name rules. |
| 14 | `tests/ux/regression/test_20260923_dashboard_polish_ux.py:115` | no change | Checks body text only. |
| 15 | `tests/test_dashboard_copy.py:219-310` | review at edit time | Checks `_DASH_HELP` entries; if it asserts an exact key set per entry, it is updated to allow `learnMore`. |
| 16 | `ui_pages/selectors.py:77-81` (`Help`) | update | Adds `MODAL_LEARN_MORE`. Existing selectors untouched. |
| 17 | `ui_pages/dashboard_console.py:61` | no change | Returns the modal locator only. |
| 18 | `scripts/capture_screenshots.py` (`_HELP_REGISTRY` mention) | no change | Suppresses the tour; does not read entries. |
| 19 | `docs/wiki/SCHEMA.md:104-107` | update | Stale user-tier sentence. |
| 20 | `docs/wiki/pages/frontend-wizard.md`, `using-sartor.md`, `diagnostics-console.md` | update if cited lines move | Wiki pages cite `_HELP_REGISTRY`/`_DASH_HELP`; the step-8 wiki pass re-anchors them. |

---

## Deferred

- **The handoff template's verbatim close-out step 1** (item 135) — owner's decision, not
  touched here. Lint 5.5's gate-step pair will **exclude** `docs/dev/AGENT_HANDOFF_TEMPLATE.md`
  and `docs/dev/handoffs/**` (records / a gated template), and say so at the exclusion site.
- **Settings drawer help bubble** — owner decision 2026-10-01: filed as a work item, not built.

---

## Verification

- #1–#3: the existing doc-gate tests pass unchanged, and a before/after diff of each
  checker's stdout on the real tree is empty.
- #9–#12: a UX test opens a bubble with `learnMore` and one without; asserts link visibility,
  `href`, and Tab reaching the link. axe smoke stays green.
- A gate test asserts every `learnMore` slug maps to a `doc_registry` entry's projected route,
  so a missed or renamed page fails closed.

---

## Addendum — step 1 baseline (2026-10-01, `092e544`)

Measured before any checker edit. Script: five subprocess runs per checker, wall time,
`time.perf_counter()` (session scratch `time_checkers.py`).

```
check_doc_links:       min 5.40s median 6.07s (n=5, exit 0)  578 tracked markdown files
check_doc_frontmatter: min 0.32s median 0.42s (n=5, exit 0)  39 published docs
check_doc_single_home: min 0.71s median 0.85s (n=5, exit 0)  39 published docs
sum of medians: 7.35s
```

`python -m cProfile -s cumtime scripts/check_doc_links.py` (8.51 s under the profiler):
`check_links` 7.90 s cumulative; `Path.resolve` 2,718 calls, 3.35 s (`nt._getfinalpathname`
2.78 s); `Path.exists` 5,675 calls, 2.32 s (`nt.stat` 2.11 s); `read_text` 648 calls, 0.67 s;
`_iter_unfenced_lines` 0.56 s. So about 5.7 of 8.5 s is per-link filesystem resolution, the
cost §5's lexical resolution removes.

The D1 baseline (`docs-ia-design.md:63-69`) was 3.51 s total. Today's figure is higher on a
larger tree (578 files) and a loaded machine; the before/after comparison uses only today's
numbers, same machine, same session.

## Addendum — step 1 after (2026-10-01): corpus refactor measured

**Behavior preserved.**
- `check_doc_links`, `check_doc_frontmatter` and `check_doc_single_home` print byte-identical
  output before and after on the real tree (`diff` of saved stdout, all three exit 0).
- Differential run on a throwaway worktree: the `092e544` link checker and the new one gave
  **identical output** on a seeded doc with 18 link shapes. Shapes: missing file, existing
  file, good and bad target anchor, good and bad same-file anchor, a dir with and without a
  slash, a missing dir, an untracked-but-present file, a gitignored target, a
  deleted-but-indexed file, a case mismatch, a path escaping the repo, a non-md fragment, an
  anchor on a dir, `./`, a backslash path. Both exited 1 with the same 7 violations.
- `tests/test_doc_links.py` + `tests/test_docs_move.py`: 11 passed.

**Timing, interleaved A/B** (old = `092e544` version, new = this branch, alternating runs,
same tree, same moment). The machine was under heavy load (one old run took 39.85 s), so min
is the fairest figure:

```
old: min 6.52s median 9.08s max 39.85s (n=7)
new: min 1.98s median 3.29s max 16.96s (n=7)
```

New profile (3.18 s under cProfile): the two `git` calls take 0.83 s, of which `git ls-files
--deleted` is about 0.32 s. It stats every index entry, and it is the price of keeping
deleted-but-indexed targets failing. Reading and fence-splitting 618 files takes 1.09 s.
`Path.resolve` / `Path.exists` no longer appear.

**One deliberate departure from the §5 text.** §5 says a lexical miss falls back to `git
check-ignore`. This branch first checks the filesystem on a miss, then `git check-ignore`. A
link to a new file that hasn't been `git add`-ed yet therefore stays valid, as it always
was. Pure lexical-then-check-ignore would have turned it into a false failure.

## Addendum — step 2 owner decision (2026-10-01)

**Charter edits are editorial (owner: "Editorial: do both, note it").** Lint 5.4's fix
changes lowercase `sartor.` to `Sartor` in `docs/governance/charter.md` (6 lines) and
`docs/governance/metrics.md` (3 lines). Lint 5.8 gives each C-clause its own `###` heading.
Neither changes a clause's meaning. They land on this branch with one dated
`[src: editorial, owner-directed]` note in the charter and a CHANGELOG line. The owner signs
off at the epic PR. Added consumer rows:

| # | Site | Decision | Rationale |
|---|---|---|---|
| 21 | `docs/governance/charter.md:64-288` (13 clause openers) | update | `**C-n — Title.** text` becomes `### C-n — Title` plus the text. Inbound `charter.md#…` anchors are re-checked by `check_doc_links` in the same commit. |
| 22 | `docs/governance/charter.md`, `metrics.md` wordmark lines | update | `sartor.` → `Sartor` in sentences (style guide; O-1). |

## Addendum — step 2: the §5 lints (2026-10-01)

`scripts/doc_lints.py` + `tests/test_doc_lints.py` (27 tests: each gated lint on the real
tree, plus one seeded violation per row 5.2–5.9).

**Day-one findings on the real tree, before any doc fix** (first full run): 49 blocks.
Three classes turned out to be lint bugs, found by reading each hit, and were fixed in the lint:
- an acronym expansion wrapped onto the next line wasn't counted (vision, walkthrough-example);
- inline code spanning a line break wasn't seen as code (`RELEASE_CHECKLIST.md:4380`);
- double-backtick spans were mis-paired (`docs-ia-design.md:328`);
- `<!-- -->` inside inline code was read as a comment.

Two over-reaches were narrowed:
- 5.5 compared against prose with inline code stripped, so it never saw backticked module
  names. It now reads raw unfenced text.
- 5.5's gate-step check matched gate-run *logs* in long DONE items. It now needs a
  gate-description marker (`quality gate`, `scripts.gate`, `gate.py`, `the gate runs/is`)
  and counts per list item, table row or paragraph.

YAML frontmatter is skipped (an agent's `description:` isn't rendered prose).

True violations fixed, by row:
- **5.3:** `**Type:**` added to 6 user docs, using the D1 design's types.
- **5.4:** `sartor.` → `Sartor` in 17 sentences across charter, metrics, EXTRACTION,
  RELEASE_CHECKLIST, documentation-architecture, PERFORMANCE_HISTORY, screenshot-capture and
  vision.
- **5.5:** `vision.md` and `RELEASE_ARC.md` listed 7 of 8 deterministic modules;
  `architecture.md` and `RELEASE_ARC.md` restated 4 and 3 of the gate's 5 tools. Each now
  lists all of them or cites `scripts/gate.py`.
- **5.6:** "sanity check" in walkthrough-example.
- **5.7:** 9 acronym first uses expanded (README, install, iterating, vision); 5 tracker IDs
  removed from rendered user text (README governance line, coaching, iterating).
- **5.8:** 13 charter clause headings (owner decision above); 2 memory `[[…]]` refs in
  RELEASE_CHECKLIST.

**Reviewed exceptions** (`doc_lints._REVIEWED_ENUMERATIONS`, each with its reason in code;
`test_reviewed_exceptions_still_match_something` fails if one goes stale):
- the handoff template's module list and its gate line (item 135, owner);
- epic-a design's consumer list;
- two historical gate-run logs;
- two historical `C-0…C-6` ranges;
- the quoted old UI string in docs-ia-design.

**Perf.** The first version ran 9.46 s under cProfile: 5.3 s in 190k per-member regex
searches. One precompiled alternation per set, plus cheap prefilters, brought the lint to
1.96 s in-test, and the whole module from 20.4 s to 10.8 s on the same loaded machine.

**Stated limits (C-0):**
- 5.5 catches a list missing at most two members; a shorter list reads as prose about a
  subset and is not checked.
- The gate-step check needs the description marker.
- 5.6's `just` + imperative uses a closed verb list.
- 5.3 checks that the type is present, not that it is right.
- 5.9 is report-only.

## Addendum — step 7: assistant audience gating (2026-10-01, before the edit)

**Observed.** Each `doc_registry.PUBLISHED` entry was checked against
`blueprints.assistant._path_audience` (a one-off script, output:
`MISMATCH ACCESSIBILITY.md user Audience.DEV`). That was the only mismatch among 39 entries.
`ACCESSIBILITY.md` is user-tier in the registry, but the assistant classes it `dev`, so a
user-mode turn can never cite the accessibility page. The direction is safe (it under-
rather than over-discloses), but it is drift.

| # | Site | Decision | Rationale |
|---|---|---|---|
| 23 | `blueprints/assistant.py:101` (`_USER_DOC_NAMES`) | update | Add `ACCESSIBILITY.md`. Consumers: `GitGrepSource` (`:200`) and `VectorSource` (`:211`) take the resolver as a function, so neither signature changes. |
| 24 | `tests/test_assistant_path_audience.py` | update | Registry as oracle: every `PUBLISHED` entry resolves to its tier (fails closed on the next drift). Edge cases: `docs/user/README.md`, `docs/dev/README.md`, `docs/work/`, `docs/ux/`, backslash paths. |
| 25 | `docs/wiki/SCHEMA.md:100-107` (gated) | update | The user-tier row gains `ACCESSIBILITY.md`, and the stale "five Sprint-6.5 education guides" sentence is corrected (row 19). |

Left as is, documented: a user-tagged wiki page reached through git-grep or the vector
index resolves `dev` (path rule), while `WikiSource` serves it as `user`. This is
conservative. The wiki tier is the canonical way user turns reach those pages.

## Addendum — step 4: screenshot capture, run 1 failed (2026-10-01)

**Observed.** `python -m scripts.capture_screenshots --headless` (owner-approved) captured 8
of 10 shots, then failed at step 9:

```
playwright._impl._errors.TimeoutError: Page.wait_for_selector: Timeout 120000ms exceeded.
  - waiting for locator("#outputPreviewBlock") to be visible
    223 × locator resolved to hidden <div id="outputPreviewBlock" class="live-preview-block hidden">
```

The app log shows `2026-10-01 14:35:19,030 [werkzeug] INFO:  * Restarting with stat`, which
lines up with this session's edit to `blueprints/assistant.py` (step 7). The debug reloader
restarted the server during the in-flight Generate call. **The cause was the session's own
concurrent edit, not a product defect.** Run 2 started with no `.py` edits allowed until it
finished.

Side finding: the script's `cleanup()` runs only on success (it is not in a `finally`), so the
failed run left `configs/demo.config`, `resumes/demo/` and `output/demo/` behind. Run 2
reuses them.

**Correction (run 2, same day): the reloader explanation above was a hypothesis, and it is
falsified.** Run 2 had no `.py` edits and failed the same way:

```
- waiting for locator("#outputPreviewBlock") to be visible
  222 × locator resolved to hidden <div id="outputPreviewBlock" class="live-preview-block hidden">
```

`logs/llm_calls.jsonl` shows that in **neither** run was a generation call ever made. The
last logged call in each run is Step 4's (run 1 `2026-10-01T21:33:28Z`, run 2 `21:47:32Z`).
In run 1 the reload came at 21:35:19, almost two minutes into the 120 s wait. So the Generate
click never started a generation request. What stops it is **not yet observed**.

**Run 3 (instrumented, owner-approved; scratch wrapper around `run_step5_and_6`, capture script
unchanged).** Events recorded at the Generate click:

```
state-before-generate  lastContextPath=C:\Dev\sartor\output\demo\context_20261001_151538.json  btnDisabled=false
request   POST http://localhost:5000/api/generate/stream
response  422  http://localhost:5000/api/generate/stream
console   error "Failed to load resource: the server responded with a status of 422 (UNPROCESSABLE ENTITY)"
```

- **Falsified:** "`lastContextPath` is empty and the alert guard fires". It was set, and the
  request went out.
- **Observed:** the server refuses the generate request with a 422.
- **Not yet observed:** why the server refuses it (the response body).

**Root cause, observed** (run 3's failure screenshot, the app's own Error-detail dialog):

```
Stage:   Generate
User:    demo
When:    2026-10-01T22:16:23.982Z
Message: 3 role(s) need month precision before generating: Helix L…
```

That text comes from `blueprints/generation.py:_month_block_response`, the month-precision
hard block on both generate routes. The capture script's synthetic Priya résumé
(`scripts/capture_screenshots.py`, built at `:105-180`) gives year-only dates, so Generate
is refused before any LLM call. Steps 1–4 have no such gate. `capture-smoke.yml` runs only
to Step 1 (`--smoke`), so CI could not have caught it: it is the "zero automated coverage"
class the script's docstring already records.

**Fix, owner-directed (2026-10-01).**
- **Fixture.** The capture script's synthetic Priya résumé gets month dates ("Jan 2023 –
  Present", "Jan 2019 – Jan 2023", "Jan 2017 – Jan 2019"). The owner confirmed month dates
  are the enforced rule.
- **Demo data.** The demo candidate (id 5) held 6 roles: 17–19 with months (`2023-01`…)
  and 26–28 as year-only duplicates (`2023`…) from a later import. Owner: "if they are
  dupes then keep the ones with months and drop the ones without". `db/resume.sqlite` was
  backed up first (SQLite online backup, to session scratch). Rows 26–28 were deleted with
  `PRAGMA foreign_keys=ON` (cascade: 22 bullets, 3 titles). Verified afterwards: no
  `application_bullet` referenced them (0 rows), 0 orphan bullets, `foreign_key_check`
  clean. The demo now has exactly rows 17–19. The fixture's "Jan" months match them, so
  the next import merges instead of duplicating.

| # | Site | Decision | Rationale |
|---|---|---|---|
| 26 | `scripts/capture_screenshots.py` (synthetic docx dates) | update | Consumers: the script itself and `.github/workflows/capture-smoke.yml` (Step 1 only, no Generate, so it is unaffected). |

## Addendum — step 5: Mermaid render check + projection stamp (before the edits)

| # | Site | Decision | Rationale |
|---|---|---|---|
| 27 | `docs-site/src/components/mermaid.tsx` | update | Adds `data-mermaid="pending|ok|failed"` on the wrapper. Today the loading and failed states render the same `<pre>`, so a browser check can't tell them apart. The rendered output is otherwise unchanged. Its only consumer is `src/components/mdx.tsx` (registration). |
| 28 | `docs-site/source.config.ts` (`projectedPageSchema`) | update | Adds optional `sourceCommit`. Optional, so a projection without it still validates. The stale "four architecture diagrams" comment is fixed here too. |
| 29 | `scripts/project_docs_to_mdx.py` (`_GENERATED_BANNER`, `build_frontmatter`, `main`) | update | Stamps the source commit (plus "+ uncommitted changes" when registered sources are dirty) into the banner and the frontmatter. `build_frontmatter` gains an optional keyword, so existing callers and tests are unaffected. One `git rev-parse` per run, not per page. |
| 30 | `.github/workflows/docs-deploy.yml` | update | After "Verify static export", installs Chromium and runs the new Mermaid check on both triggers (push and PR). |
| 31 | `scripts/check_docs_site_mermaid.py`, `scripts/check_docs_projection_fresh.py` (new) | add | The new checks. They are test-covered for their pure parts. |

**Observed (step 5, local build of the docs site, 2026-10-01).** The CI sequence was run
locally (`generate_openapi_spec.py`, `project_docs_to_mdx.py`, `npm run gen:api-docs`,
`npm run build`, with existing `node_modules`):

```
Error: Turbopack build failed with 10 errors:
Module not found: Can't resolve '../screenshots/install_setup_user-picker.png'
… (8 more '../screenshots/walkthrough_*.png')
Module not found: Can't resolve './docs/screenshots/readme_hero_wizard-step1-filled.png'
```

Nine of the ten are image links this branch did not touch. The projector copies each local
image to `content/docs/screenshots/`, but it leaves the image link as the source wrote it,
so `../screenshots/x.png` resolves from `content/docs/` to a directory that doesn't exist.
**Not yet observed:** which commit broke it. Plausibly D2's move of the guides into
`docs/user/` (written there as `../screenshots/`), but that is unverified. Either way, the
epic's docs-deploy check would fail as it stands.

| # | Site | Decision | Rationale |
|---|---|---|---|
| 32 | `scripts/project_docs_to_mdx.py` (image references) | update | Rewrite each local image's link to `./screenshots/<name>`, the place `copy_local_images` puts the file. The basename-collision guard already makes that name unique. Tested in `tests/test_docs_projection.py`. |

**Observed: diagrams, rendered in headless Chromium with the site's own mermaid**
(`docs-site/node_modules/mermaid`; scratch probe that renders each fence and records
`mermaid.render`'s error). 10 of 11 render, including the five in `docs/dev/diagnostics.md`
that D3 could not verify. One fails:

```
FAIL docs/dev/architecture.md:84 Parse error on line 99:
... Step 5 until frozen, item 67)        A
-----------------------^
Expecting '()', 'SOLID_OPEN_ARROW', … 
```

The fence at `architecture.md:84` is the pipeline sequence diagram. Its line 99 carries the
item-67 relabel D3 wrote (`4fac13a`, "the legacy Generate branch is reachable only by a
direct POST"). On the published site that diagram shows as raw source. The build stayed
green, which is exactly the blind spot this check closes. The built site
(`check_docs_site_mermaid.py`) reported the same: `/docs/dev-architecture/: 3 of 4
diagram(s) rendered (1 failed, 0 still pending)`.

The same run reported all 10 local images as "did not load". **Not yet verified as real:**
Next renders them `loading="lazy"`, so an off-screen image hasn't loaded when the page is
inspected. The check is being changed to test each image URL's HTTP status instead.

**Fixed and verified (step 5).**
- **The broken diagram.** `architecture.md:209`'s `;` became `,`. Mermaid ends a statement
  at `;`, so the label stopped mid-parenthesis. The probe then rendered **11 of 11**.
- **The image check.** It now fetches each same-origin image URL and requires HTTP 200,
  instead of reading load state (the images are lazy-loaded).
- **Re-projected and rebuilt:** `build exit 0`. Then
  `check_docs_site_mermaid: OK — 39 pages, 11 diagram(s) rendered, every local image
  returned 200.`
- **Seeded violations**, so neither half passes vacuously:
  - the unfixed diagram gave `/docs/dev-architecture/: 3 of 4 diagram(s) rendered (1
    failed…)`;
  - moving the hero PNG out of `out/` gave `/docs/: image
    /_next/static/media/readme_hero_wizard-step1-filled.….png -> HTTP 404`, exit 1. The
    PNG was restored afterwards.
- **The projection stamp.** `check_docs_projection_fresh` read the July-era local copy as
  `STALE — 36 page(s) carry no sourceCommit`. After re-projection it reads
  `OK — projected from HEAD`. A frontmatter longer than the first read window was found
  and fixed along the way (the stamp is now read from the whole frontmatter block).

**Observed (step 5 test run, `pytest -n 4`):** `tests/test_doc_lints.py::test_5_8_wikilink_seeded`
failed with `assert [] == [('x.md', 4)]`, after passing in the step-2 runs.
**Inferred, not observed:** `doc_lints.prose()` cached by `(id(corpus), path)` in a
module-level dict. Once a test's in-memory corpus is garbage-collected, CPython can reuse its
id, so a later corpus with the same `x.md` path got the earlier test's cached text. The
cache now lives on the corpus object, so it can't outlive it. After the change, three runs of
the module under `-n 4` passed (27/27 each). An intermittent failure makes that weak
evidence, and it is recorded as such.
