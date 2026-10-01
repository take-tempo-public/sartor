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
