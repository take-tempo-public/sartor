# Blast radius — user-docs

> **Branch:** `feat/user-docs`
> **Status:** enumeration complete for the planned changes (written before the first content
> edit, 2026-09-29). Plan: owner-approved D3 (user half) plan; owner decisions are quoted in
> [Surface](#surface).

---

## Surface

Epic D sprint D3, the user half (`docs/dev/RELEASE_ARC.md` §"Epic D" D3 bullet;
`docs/dev/docs-ia-design.md` §4). Owner decisions made at kickoff, 2026-09-29:
- the help-bubble copy is in scope;
- the Notes field is held, pending a board item;
- the "Under the hood" blocks are cut and folded into `architecture.md`;
- the assistant rename covers the UI strings **and** `AVATAR_SYSTEM_PROMPT`;
- defects are filed as items, and the docs state today's behavior.

What changes:

1. **`scripts/wiki_relevance.py`** (gated): `KNOWN_RELEVANT_TOP_LEVEL` gains the two new
   `docs/dev/` root files, `releasing.md` and `bundled-templates.md`.
   `tests/test_wiki_relevance_classification.py:66` fails on any unclassified top-level entry.
2. **`scripts/doc_registry.py`** `PUBLISHED`: add `docs/user/iterating.md`,
   `docs/user/coaching.md`, `docs/user/templates.md` (user tier), and `docs/dev/releasing.md`,
   `docs/dev/bundled-templates.md` (dev tier).
3. **Section moves by hand** (`scripts/docs_move.py` is whole-file only, `:76-86`, `:246-263`):
   - `docs/user/install.md` §"Maintainer: publishing" (`:305-335`) → `docs/dev/releasing.md`
   - `docs/user/templates.md` maintainer half ("Role-paragraph order", the bundled-template
     regeneration, "How to add a new bundled template", `:27-84`) → `docs/dev/bundled-templates.md`
   - the eight `docs/user/walkthrough.md` "Under the hood" paragraphs (`:163, 206, 253, 317, 357,
     393, 441, 475`) are cut. Any fact `docs/dev/architecture.md` lacks is added there.
4. **O-1 wordmark in UI copy.** In-sentence `sartor`/`sartor.` → `Sartor` in:
   - `templates/index.html`
   - `static/app.js`
   - the two assistant strings in `dashboard/templates/dashboard.html`
   - `analyzer.py` `AVATAR_SYSTEM_PROMPT` (`:801` onward), with an `AVATAR_PROMPT_VERSION` bump
     (`:504-507`) in the same commit

   The test pin in `tests/test_avatar_streaming.py:340,346` is rewritten to the new invariant.
5. **New `_HELP_REGISTRY` entries** in `static/app.js` (`:2184-2348`): Pipeline, document
   refinement, and Settings → Profile. Plus the Pipeline panel hint copy in
   `templates/index.html`.

---

## Enumeration

Commands run 2026-09-29 on `feat/user-docs` at `c52fc06`. The exclusions are the record classes
in `scripts/doc_registry.py:31-44`, which are frozen and never rewritten.

```
$ git grep -n "maintainer-publishing\|Maintainer: publishing"
  -> 4 hits: docs/user/install.md:305 (the section itself) + 3 in docs/dev/reviews/** (records)
  -> 0 inbound anchor links
$ git grep -n "install.md" .github/
  -> .github/workflows/release.yml:5  (comment: PyPI setup steps "in docs/user/install.md")
$ git grep -n "install.md#" -- (live, excluding records)
  -> README.md:184 (#local-development-headless--container--ci-runs-f-18)
  -> docs/user/walkthrough.md:504 (#troubleshooting)
  -> tests/test_docs_move.py:38-159 (synthetic fixtures, not this file)
$ git grep -n "walkthrough.md#"            -> 0 live hits
$ git grep -n -c "Under the hood"
  -> docs/user/walkthrough.md:8; others are records/CHANGELOG-archive, plus
     docs/dev/docs-ia-design.md:1 and docs/dev/handoffs/docs-split.md:1 (a record)
$ git grep -n "templates\.md\|template_authoring" -- (live)
  -> docs/bundled_templates_LICENSE.md:63, scripts/build_bundled_templates.py:10 (both cite
     the ATS RULE SET), docs/user/README.md:20, docs/dev/docs-ia-design.md:58,127,173,273,
     scripts/docs_move.py:80 (D2's MOVES entry), docs/wiki/index.md:98 +
     docs/wiki/log.md:1894 (these name pages/resume-templates.md, a different file)
$ git grep -n -i "sartor" -- templates/index.html      -> 11 hits
$ git grep -n -i "sartor" -- static/app.js | grep -v take-tempo  -> 22 hits
$ git grep -n "how sartor\|sartor\. assistant" -- dashboard/ templates/ static/ analyzer.py tests/
  -> analyzer.py:801, dashboard/templates/dashboard.html:919,939,
     templates/index.html:1148,1169, tests/test_avatar_streaming.py:340
$ git grep -n -i "sartor\. assistant\|how sartor\. works\|Ask how" -- docs/wiki llms.txt README.md docs/user ACCESSIBILITY.md
  -> 0 hits
$ git grep -n "AVATAR_PROMPT_VERSION" -- '*.py' '*.md'
  -> analyzer.py (definition + telemetry use); CHANGELOG.md history only
$ git grep -n "user-walkthrough\|user-install" tests/
  -> tests/test_docs_projection.py:82 (slug), :221 (ladder order vision < user-install < user-walkthrough)
```

---

## Consumers

| # | Site (`path:line`) | Decision | Rationale |
|---|---|---|---|
| 1 | `scripts/wiki_relevance.py` `KNOWN_RELEVANT_TOP_LEVEL` (`:125-206`) | update | Add `docs/dev/releasing.md` and `docs/dev/bundled-templates.md`; otherwise `tests/test_wiki_relevance_classification.py:66` fails |
| 2 | `scripts/doc_registry.py` `PUBLISHED` (`:75-109`) | update | Register the 5 docs. User entries go after `walkthrough-example.md`, keeping the ladder order `tests/test_docs_projection.py:221` pins |
| 3 | `tests/test_doc_registry.py:22-50` | no change | Invariants (exists, unique, tiers ordered, no records) hold for the new entries |
| 4 | `tests/test_docs_projection.py:175-176,221` | no change | `:175` derives from `PUBLISHED`; `:221` order is preserved |
| 5 | `scripts/check_doc_frontmatter.py:47-96` | no change | New docs carry the P/A/A header with a leading audience token |
| 6 | `scripts/check_doc_links.py:102` (cite check = `PUBLISHED_DOC_FILES`) | no change | Registering widens the cite check. Expect stale `path:line` cites to surface (D2 recurrence 1); fix them in the doc |
| 7 | `scripts/check_doc_single_home.py` | no change | Moved text is **moved**, not copied. No paragraph may exist in two registered docs |
| 8 | `.github/workflows/release.yml:5` | update | Repoint the comment to `docs/dev/releasing.md` |
| 9 | `README.md:160` (cost guidance → install.md) | no change *(revised in execution)* | README already sends readers to install.md for cost guidance, and install.md now actually carries it (§"What an application costs"), so the loop is broken on the install.md side alone |
| 10 | `README.md:184` → `install.md#local-development-headless--container--ci-runs-f-18` | no change | Heading kept; the anchor must survive (link gate checks anchors) |
| 11 | `docs/user/walkthrough.md:504` → `install.md#troubleshooting` | no change | Heading kept |
| 12 | `docs/bundled_templates_LICENSE.md:63`, `scripts/build_bundled_templates.py:10` | no change to the pointer; docstring font list updated *(execution)* | Both cite the ATS **rule set**, which stays in `docs/user/templates.md`. The script's docstring restated the stale "Arial, Calibri, Helvetica" font list, now corrected to `json_resume.APPROVED_FONTS` (`json_resume.py:965`) |
| 13 | `docs/user/README.md:18-20` | update | Fill rungs 4 and 5 with the new docs |
| 14 | `docs/dev/docs-ia-design.md:58,127,170,173,273` | no change | Design record of the plan; its path mentions stay accurate (`templates.md` keeps its path) |
| 15 | `templates/index.html:1148,1169` | update | O-1: "how Sartor works" |
| 16 | `templates/index.html:6` (`<title>`), `:33`, `:1418` (comments), `:39` (`aria-label="sartor, home"`) | no change / update `:39` | `<title>` and the top bar are the wordmark standing alone (style guide §1). Comments aren't copy. `:39` is a spoken label, so `Sartor, home` |
| 17 | `templates/index.html:477,485,601,607` (`sartor --setup`) | no change | Command, a code identifier (style guide §1 table) |
| 18 | `static/app.js:2187-2343` (`_HELP_REGISTRY` copy, 17 in-sentence hits) and `:8961` | update | O-1: `Sartor` in sentences |
| 19 | `static/app.js:61,3543,3561` | no change | Code comments |
| 20 | `dashboard/templates/dashboard.html:919,939` | update | Same assistant strings as index.html; kept in parity |
| 21 | `analyzer.py:801-815` `AVATAR_SYSTEM_PROMPT` + `AVATAR_PROMPT_VERSION` (`:504-507`) | update | Owner decision. In-sentence `sartor.`/`sartor` → `Sartor`; version bumped in the same commit (`analyzer.py:496-502` rule). Not an eval target, so `PROMPT_VERSION` is untouched |
| 22 | `tests/test_avatar_streaming.py:340,346` | update | `:340` pins the old string. `:346` asserts `"Sartor" not in html` (the old identity rule). Rewritten to the O-1 invariant: no in-sentence `sartor.` in the assistant copy |
| 23 | `tests/ux/regression/test_20260616_assistant_panel.py:24,29`, `test_20260619_assistant_no_user.py:27` | no change | Stubbed LLM answer text, not app copy |
| 24 | `docs/dev/archive/avatar-voice-tone-guidance.md:942` (frozen lowercase identity) | no change | Record (archive). Superseded by O-1, recorded in `docs-ia-design.md` "Open decisions" |
| 25 | `static/app.js` `_HELP_REGISTRY` (new keys for Pipeline, refinement, Settings profile) | update | RELEASE_ARC D3 "progressive-discovery copy for main-app bubbles"; the registration mechanism (`:2368-2414`) is reused unchanged |
| 26 | `blueprints/assistant.py:125-136` (audience by path) | no change | `docs/user/**` is user-tier automatically; the new `docs/dev/**` files are dev-tier |

---

## Deferred

- **The rest of `dashboard/templates/dashboard.html`'s in-sentence `sartor`** (69 case-insensitive
  hits in the file). The diagnostics console is dev-tier copy, and its C3 lay copy is D3's
  **dev** half (`feat/dev-docs`). Only the two assistant strings change here, for parity with
  the main app.
- **The Notes field in user docs.** Held by owner decision: `Candidate.notes` is written only on
  creation or when empty (`onboarding/corpus_import.py:183,193-196`), and analyze reads the DB
  (`db/build_context.py:214`). Filed as a board item; documented once it's verified or fixed.
- **`docs/dev/architecture.md`'s item-20 claim in its diagrams** (`:98-100` Mermaid comment,
  `:208` sequence-diagram `else` label, `:816` flowchart edge). They still call the no-freeze
  Generate path "a known live gap", but item 20 gated the Step-5 rail on a frozen composition
  (`static/app.js:7051-7081`). The prose (System overview, step 4) was corrected on this
  branch. The diagrams are D4's "diagram refresh" and the dev half's module-map refresh, so
  they're left for `feat/dev-docs` and named in its handoff.
- **`docs/wiki/**` in-sentence wordmarks.** Item 2's exclusion, and the D4 lint's scope.

---

## Verification

- `tests/test_wiki_relevance_classification.py` fails on a missed `docs/dev/` root file.
- `tests/test_doc_registry.py` + `tests/test_docs_projection.py` fail on a bad registry entry or
  a broken ladder order.
- `scripts/check_doc_links.py` (anchors included, run **after `git add`**) fails on any link to a
  removed heading.
- `scripts/check_doc_single_home.py` fails if moved text was copied instead.
- Wordmark residue: re-run
  `git grep -n -i "sartor" -- templates/index.html static/app.js analyzer.py`. Every remaining hit
  must be a row above marked "no change".
