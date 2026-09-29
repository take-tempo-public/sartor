# Blast radius — docs-split

> **Branch:** `feat/docs-split`
> **Status:** enumeration complete for the planned moves (written before the first code edit,
> 2026-09-28). The scripted rewrite's own dry-run list is appended under
> [Verification](#verification) when it exists; that list is the per-link receipt.

---

## Surface

Epic D sprint D2, the mechanical split (`docs/dev/docs-ia-design.md` §2, §3, §5.1, §5.2, §6;
owner decisions recorded in that doc's "Open decisions for the owner", 2026-09-28). What changes:

1. **24 doc paths move** (`git mv`, content unchanged except where noted):
   - §2.1, 8 live moves:

     | Old | New |
     |---|---|
     | `docs/install.md` | `docs/user/install.md` |
     | `docs/walkthrough.md` | `docs/user/walkthrough.md` |
     | `docs/walkthrough_example.md` | `docs/user/walkthrough-example.md` |
     | `docs/template_authoring.md` | `docs/user/templates.md` |
     | `docs/architecture.md` | `docs/dev/architecture.md` |
     | `docs/system-model.md` | `docs/dev/system-model.md` |
     | `docs/PRODUCT_SHAPE.md` | `docs/dev/PRODUCT_SHAPE.md` |
     | `docs/ux/screenshot_capture.md` | `docs/dev/screenshot-capture.md` |

   - §2.2, 16 archive moves `docs/dev/<name>.md` → `docs/dev/archive/<name>.md`. The only
     edit is a one-time banner. The files are `COMPOSE_REWRITE_DIAL`, `app-blueprints-design`,
     `avatar-voice-tone-guidance`, `avatar-citation-format-guidance`, `board-forge-sync-review`,
     `gate-window-class-study`, `governance-extraction-design`, `kit-adoption-design`,
     `pagedjs-preview-spike`, `self-documenting-loop-design`,
     `generation-experience-rearchitecture`, `dependency-triage-pre-v1.1.0`,
     `ORCHESTRATION_PLAYBOOK`, `V1_0_5_VERIFICATION`, `window-8.5-findings` and
     `window-8.5-walkthrough`.
   - Two of the design's 18 archive candidates **stay live** (owner, O-3a):
     `epic-a-chain-design-corrections.md` (the operating envelope
     `.claude/workflows/n1-baseline.mjs:41-43` embeds in every pipeline prompt;
     `agents/n1-judge.md:14` and `agents/n1-refuter.md:14` cite it as their role spec) and
     `handoff-integrity-design.md` (cited by `docs/governance/charter.md:204,210`, AGENTS.md
     step 5, and the verbatim Binding-rules text at `docs/dev/AGENT_HANDOFF_TEMPLATE.md:246`).
2. **New `scripts/doc_registry.py`**: the publication registry (O-4) plus `RECORD_PREFIXES`.
   It replaces:
   - the projector's header-scan selection and its audience fallback table
     (`scripts/project_docs_to_mdx.py:130-135`, `classify_audience` `:208-218`)
   - the hand-listed `PUBLISHED_DOC_FILES` (`scripts/check_doc_frontmatter.py:48-73`)
3. **`scripts/check_doc_links.py`**: record-origin links resolve through
   `docs/dev/moved-paths.json` (design §3.3).
4. **`scripts/wiki_relevance.py`**: `KNOWN_RELEVANT_TOP_LEVEL` and `IRRELEVANT_PREFIXES`
   entries for moved and new paths (gated surface, `blast_radius.py:160`).
5. **`docs/wiki/SCHEMA.md:103`**: the blanket path→audience rule names `docs/install.md` and
   `docs/walkthrough*.md`, which becomes `docs/user/**` (gated surface, `blast_radius.py:110`).

---

## Enumeration

Per moved basename, whole tree. "Live" excludes record classes
(`docs/dev/{handoffs,ledger,diagnosis,blast-radius,reviews,perf,excellence-walk,flake-rates,work}`,
`docs/ux/onboarding_audit_*`, `docs/wiki/log.md`, `CHANGELOG*.md`):

```
for n in <24 basenames>; do
  git grep -l -F "$n" | wc -l                                  # all
  git grep -l -F "$n" -- <record excludes> | wc -l             # live
  git grep -l -F "$n" -- '*.md' <record excludes> | wc -l      # live markdown
  git grep -l -F "$n" -- <record excludes> ':!*.md'            # live non-markdown files
done
```

| Basename | All files | Live | Live `.md` |
|---|---|---|---|
| `architecture.md` * | 207 | 71 | 43 |
| `install.md` | 58 | 22 | 13 |
| `walkthrough.md` | 27 | 16 | 12 |
| `walkthrough_example.md` | 13 | 8 | 4 |
| `template_authoring.md` | 9 | 4 | 2 |
| `system-model.md` | 38 | 20 | 17 |
| `PRODUCT_SHAPE.md` | 52 | 32 | 21 |
| `screenshot_capture.md` | 4 | 3 | 2 |
| `COMPOSE_REWRITE_DIAL.md` | 24 | 3 | 2 |
| `app-blueprints-design.md` | 10 | 4 | 3 |
| `avatar-voice-tone-guidance.md` | 10 | 7 | 5 |
| `avatar-citation-format-guidance.md` | 6 | 5 | 4 |
| `board-forge-sync-review.md` | 6 | 2 | 1 |
| `gate-window-class-study.md` | 11 | 3 | 2 |
| `governance-extraction-design.md` | 17 | 11 | 9 |
| `kit-adoption-design.md` | 31 | 15 | 11 |
| `pagedjs-preview-spike.md` | 5 | 3 | 2 |
| `self-documenting-loop-design.md` | 10 | 8 | 7 |
| `generation-experience-rearchitecture.md` | 14 | 9 | 7 |
| `dependency-triage-pre-v1.1.0.md` | 4 | 2 | 1 |
| `ORCHESTRATION_PLAYBOOK.md` | 11 | 6 | 4 |
| `V1_0_5_VERIFICATION.md` | 9 | 4 | 3 |
| `window-8.5-findings.md` | 8 | 6 | 5 |
| `window-8.5-walkthrough.md` | 7 | 5 | 4 |

\* The basename `architecture.md` also matches `memory-architecture.md` and
`documentation-architecture.md`. That is why `recall/**` shows up in the unfiltered
non-markdown list. The path-precise grep below is the authoritative one for non-markdown:

```
git grep -n -E "(docs/|\.\./|[^-a-z])architecture\.md" -- ':!*.md' | grep -v "memory-architecture\|documentation-architecture"
git grep -n -E "docs/(install|walkthrough|walkthrough_example|template_authoring|system-model|PRODUCT_SHAPE)\.md|screenshot_capture\.md|ORCHESTRATION_PLAYBOOK" -- ':!*.md' ':!docs/dev/ledger'
git grep -n -E "avatar-voice-tone-guidance|kit-adoption-design|generation-experience-rearchitecture|governance-extraction-design" -- ':!*.md'
```

**Live markdown** (the "Live `.md`" column) is handled by `scripts/docs_move.py`. It makes
one pass over `git ls-files '*.md'` and rewrites (a) relative markdown link targets and
(b) exact repo-relative path strings (for example `` `docs/install.md` `` →
`` `docs/user/install.md` ``) in live docs only. Bare basenames in prose (`install.md`) are
ambiguous, so they are left alone. The dry-run list is the receipt; see Verification.

**Checked and found nothing (negative results):**
- no `.sh` hook references any moved path
- no `package.json` / `.toml` other than `pyproject.toml` comments
- no link anywhere in the repo to a docs-site route, other than `tests/test_docs_projection.py:275,282`
- no in-app template links to a site slug

---

## Consumers

Non-markdown sites plus the gated markdown surfaces. Every site is decided below.

| # | Site (`path:line`) | Decision | Rationale |
|---|---|---|---|
| 1 | `scripts/project_docs_to_mdx.py:130-135,208-218,511-562,607-624,696-704` | update | Registry replaces the header-scan, fallback table and README doc-map ordering (O-4). Docstring `:42,74-75` path mentions updated |
| 2 | `scripts/check_doc_frontmatter.py:31,48-73` | update | `PUBLISHED_DOC_FILES` derived from the registry, keeping the name because `check_doc_links.py:89` and `check_doc_single_home.py:56` import it. Adds the §5.2 audience-token check |
| 3 | `scripts/check_doc_links.py:124-144` | update | `_TEMPLATE_QUOTE_LINKS` keys name `docs/dev/governance-extraction-design.md` as the *source* file, so they follow it to `archive/`. `:128` comment updated. Adds the §3.3 map lookup near `:318` |
| 4 | `scripts/wiki_relevance.py:184-190,195-223` (+ `IRRELEVANT_FILES`/prefixes) | update | Stale entries are dropped and `docs/user` is classified; `docs/dev/archive/` goes into `IRRELEVANT_PREFIXES` (records). Enforced by `tests/test_wiki_relevance_classification.py:66,99` |
| 5 | `docs/wiki/SCHEMA.md:103` | update | Blanket rule becomes `docs/user/**` → `user` |
| 6 | `blueprints/assistant.py:130-131` (`_path_audience`) | update | Prefix `("docs/install", "docs/walkthrough")` → `("docs/user/",)`. Otherwise a moved user doc falls through to `dev`. That wouldn't over-disclose, but user-mode answers would lose those docs |
| 7 | `llms.txt:22-24` | update | Hand-maintained; points at `docs/system-model.md`, `docs/architecture.md` and `docs/PRODUCT_SHAPE.md` |
| 8 | `app.py:309` | update | Comment path |
| 9 | `dashboard/templates/dashboard.html:1303` | update | User-visible string naming `docs/install.md` |
| 10 | `.github/workflows/release.yml:5` | update | Comment path |
| 11 | `scripts/capture_screenshots.py:4,6,106,546` | update | Docstring and print paths |
| 12 | `scripts/build_bundled_templates.py:10` | update | Docstring path |
| 13 | `db/models.py:346`, `json_resume.py:3`, `pdf_render.py:3` | update | Comment/docstring only. No behaviour change, so the deterministic boundary is untouched |
| 14 | `docs-site/source.config.ts:34` | update | Comment path |
| 15 | `.claude/workflows/n1-baseline.mjs:37` | update | Comment cites `docs/dev/ORCHESTRATION_PLAYBOOK.md` as precedent, so it becomes `archive/` |
| 16 | `pyproject.toml:381,394,400,432` | update | `docs/dev/kit-adoption-design.md` → `archive/` (only `:381` carries the directory; the rest are bare basenames, left) |
| 17 | `tests/test_docs_projection.py:81-83,96-121,237-238,255-295` | update | Fallback-table tests are replaced by registry tests. Slug/link tests move to the new paths |
| 18 | `tests/test_pdf_capability_ui.py:5`, `tests/test_preflight.py:15` | update | Docstring paths |
| 19 | `tests/test_docstring_coverage_gate.py:11`, `tests/test_mypy_strict_roster_gate.py:5` | update | Docstring paths to `kit-adoption-design.md` (the directory-qualified ones only) |
| 20 | `tests/test_avatar_streaming.py:151`, `tests/test_regenerate_gap_fill.py:4` | update | Comment paths to archived docs |
| 21 | `docs/dev/AGENT_HANDOFF_TEMPLATE.md:77` (gated) | update, scripted | The dry run found one hit: item 5 of the **verbatim** "Documents to read" list names `docs/architecture.md`. It becomes `docs/dev/architecture.md`, which changes the canonical verbatim text. That's correct, because the old path would be a dead instruction in every future handoff. Handoffs already consumed are unaffected; the next one (this branch's) is generated from the new text |
| 22 | live `*.md` (the "Live `.md`" column above) | update, scripted | `docs_move.py`; no hand-edited link rewrites (design §3.2) |
| 23 | the 24 moved files' **own outbound** relative links | 8 live moves: rewritten by the script. 16 archived: **not rewritten** | Archived files are records. `check_doc_links.py` resolves a moved record's links against its *old* directory, then through the map, so the bytes stay frozen |


### Found while landing the registry (step 2), and decided

- **The widened published set widens two gates that reuse `PUBLISHED_DOC_FILES`:**
  `check_doc_links.py:98` (`CITE_CHECK_FILES`) and `check_doc_single_home.py:56`. That reuse is
  intentional (the comment at `check_doc_links.py:93-97` says so). The first run surfaced three
  real stale cites in newly published docs:
  - `docs/dev/RELEASE_CHECKLIST.md:3457-3458` cited the retired `docs/diagrams/*.mmd` as
    `path:line`. Reworded to "line N (since retired)".
  - `docs/dev/epic-a-chain-design-corrections.md:1114` had a placeholder `path.md:12`.
    Rewritten as `<path>.md:<line>`.

  The single-home gate stayed green.
- **§5.2 audience tokens:** 24 registered docs gained a leading tier token on their
  `**Audience:**` line (a header-only edit). The tier is the owner-approved registry tier.
  `ACCESSIBILITY.md` gets `` `user` · `dev` ``.
- **`docs/dev/perf/PERFORMANCE_HISTORY.md`** is kept and published as project history.
  Registry `LIVE_EXCEPTIONS` records the owner's reason. On owner direction (2026-09-28) its
  personal "portfolio / reviewers, interviewers / presentation" framing was removed (header
  plus `:300` and `:381`). The same framing survives in two frozen records,
  `docs/dev/app-blueprints-design.md` (archived by this branch) and
  `docs/dev/perf/R1_PHASE2_RESULTS.md`. It is left there as records, and surfaced to the owner.

---

## Deferred

- **`db/migrations/versions/0004_summary_item.py:8`, `0008_experience_summary_item.py:8`,
  `0009_skill_corpus_item.py:8`**: docstrings citing `docs/PRODUCT_SHAPE.md`. Migrations are
  frozen history and a gated prefix (`blast_radius.py:174-182`), and the citation was true when
  written. Left, like records.
- **`analyzer.py:808`** (`AVATAR_SYSTEM_PROMPT`): its NOT-OK example, a markdown link to `docs/architecture.md`,
  is an illustrative NOT-OK example of a forbidden markdown link, not a pointer to the doc.
  Editing it is a prompt change (a `PROMPT_VERSION` bump, eval attribution) for zero behaviour
  change.
- **Record classes and `CHANGELOG*.md`**: never rewritten (design §3.1). Their links resolve
  through `docs/dev/moved-paths.json`.
- **Bare-basename prose mentions** (`install.md` without a directory) in live docs: ambiguous
  to rewrite mechanically. They aren't links, so no gate sees them. D3 rewrites the prose.
- **Site URLs**: slugs follow paths (owner, 2026-09-28), so about 7 hosted-site URLs change
  once, before v1.1.0. Nothing in the repo links to them.

---

## Verification

- `tests/test_wiki_relevance_classification.py` fails on any unclassified or vanished
  top-level entry. It reads HEAD, so it has to run after the commit.
- `python scripts/check_doc_links.py`: every live link to an old path fails (the map is
  consulted only for record-origin links), so a missed live-doc rewrite surfaces as a violation.
- `git grep` for each old path after the move: remaining hits must be records, CHANGELOG,
  `moved-paths.json`, or the Deferred sites above. The result is appended here.
- New tests: `tests/test_doc_registry.py` (no record path registered, every entry exists,
  valid tier, unique slugs); `tests/test_docs_move.py` (tmp git repo); seeded link-map cases.

### Dry-run receipt (`python scripts/docs_move.py`, before `--apply`)

```
docs_move: 24 moves
docs_move: 468 rewrite(s) in 54 live markdown file(s)
docs_move: 65 old-path mention(s) in non-markdown files (not rewritten)
```

The 54 files are all live. No record path appears in the list (`is_record` is judged on the
post-move path, so the 16 archived files are excluded), and neither does `CHANGELOG*`. The
gated markdown hits are `docs/dev/AGENT_HANDOFF_TEMPLATE.md:77` (row 21) and
`docs/wiki/SCHEMA.md:56,103,163`. For `:103` the script rewrites the exact
`docs/install.md` but not the `docs/walkthrough*.md` glob, so that line is finished by hand to
`docs/user/**` (row 5). The 65 non-markdown mentions are exactly the rows above plus the
Deferred sites, and the registry/`wiki_relevance.py` entries edited in the move commit.

Control arm for the map lookup: with `check_doc_links.load_moved_paths` stubbed to `{}`,
`tests/test_docs_move.py::test_record_links_resolve_through_the_map` fails with
`docs/dev/archive/old-design.md:8 -> ../install.md  (target does not exist)`. The lookup is
what makes it pass.
