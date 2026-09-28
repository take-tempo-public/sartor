# Technical-writer audit — documentation corpus, against the house style guide

> **Purpose:** the opening documentation audit for Epic D / D1 (information-architecture design sprint): content-type and audience mixing, style-guide violations with counts, duplication, structure, and freshness, each finding cited and ranked.
> **Audience:** `dev` — Epic D D1 input
> **Authoritative for:** nothing normative. This is an evidence record at HEAD `88c0011` (branch `feat/docs-ia-design`, 2026-09-27); the style guide ([`../../doc-style-guide.md`](../../doc-style-guide.md)) and the charter govern. Counts are from the quoted commands and go stale as the tree moves.

---

## Method and limits

- Read in full: `docs/dev/doc-style-guide.md` (the yardstick), `README.md`. Read in part (headers, headings, targeted sections): every other in-scope root and `docs/*.md` file, `docs/governance/charter.md`, `docs/wiki/SCHEMA.md`, `docs/wiki/overview.md`, 6 wiki pages, `docs/dev/documentation-architecture.md` (first 110 lines), and the three `scripts/check_doc_*.py` gates plus `scripts/project_docs_to_mdx.py` (audience classifier).
- `docs/dev/*.md` loose files: headers and sizes only (skimmed, not read).
- `docs-site/content/docs/*.mdx` is **generated and untracked** (`git ls-files docs-site/content` returns only `.gitkeep`), so the sampled `.mdx` files are a local build, not committed state.
- The grep commands below use line-based regexes. They undercount phrases wrapped across lines, and they cannot tell a sentence from a heading unless stated. Every count carries that limit.
- Ran (read-only): `python scripts/check_doc_single_home.py` → `OK — 16 published doc(s)`; `python scripts/check_doc_links.py` → `OK — 540 tracked markdown files, no broken links or cites`.

Rank key: **HIGH** = misleads a reader about behavior, cost, or rules, or blocks the D1 lints; **MED** = structural or audience defect that the IA must absorb; **LOW** = polish.

---

## 1. Content-type mixing (Diátaxis)

| Doc | Primary type | Also carries | Mix verdict |
|---|---|---|---|
| `README.md` | explanation (positioning) | how-to (install, `README.md:121-184`), reference (model routing `:188-197`, plugin catalog `:265-270`, dev loop `:272-276`), status report (`:287-296`) | **Mixed — HIGH.** A front door carrying four types; the install how-to duplicates `docs/install.md` (see §4). |
| `docs/install.md` | how-to | reference (version floors `:47`, downloads `:339`), maintainer runbook (`:305-337`, "Maintainer: publishing (one-time `[HUMAN]` setup)") | **Mixed — HIGH.** A maintainer release runbook sits inside the first-install guide. |
| `docs/walkthrough.md` | tutorial / how-to | reference ("Under the hood" ×8: routes, function names, `context_set`, metrics — e.g. `:393-412`) | **Mixed — MED.** The header itself claims route + LLM-call mapping (`:12-14`). |
| `docs/walkthrough_example.md` | tutorial (worked example) | cost reference (`:315`) | Clean enough — LOW. |
| `vision.md` | explanation | reference (per-file module list `:155-160`), agent instructions (`:324-340`) | **Mixed — MED.** |
| `docs/PRODUCT_SHAPE.md` | explanation (design rationale) | roadmap, bug log (`:484`, "§9 Bug found during exploration"), deferral ledger (`:497-692`), conversation transcript framing (`:18-22`) | **Mixed — HIGH.** Reads as a planning notebook, filed as L1 canonical. |
| `docs/system-model.md` | explanation | open author questions (`:156-173`, "Open revision points … not yet resolved") | **Mixed — MED.** Draft questions from 2026-06-07 still ship. |
| `docs/architecture.md` | reference | explanation | Acceptable — LOW. 932 lines, 11 headings (84 lines/heading). |
| `docs/template_authoring.md` | reference (rules) | how-to (`:73`, `:85`) | Acceptable, but no P/A/A header at all (§2). |
| `CONTRIBUTING.md` | how-to | reference (GPU scorer install `:126-199`), future design (`:247-256`, "Future: multi-agent identity") | **Mixed — MED.** |
| `SECURITY.md` | reference | how-to (reporting `:173`), explanation | Conventional for a SECURITY file — LOW. |
| `ACCESSIBILITY.md` | reference (status) | — | Clean. Worked example the style guide cites (`doc-style-guide.md:116`). |
| `AGENTS.md` | reference (contract) | how-to (close-out checklist), explanation ("Why this clause exists") | Mixed by design (operational mirror, `AGENTS.md:17-25`) — LOW. |
| `docs/governance/charter.md` | reference (rules) | explanation (worked costs per clause) | Acceptable; see §5 on anchors. |
| `docs/governance/enforcement.md`, `metrics.md` | reference | — | Clean. |
| `CHANGELOG.md` | reference (log) | — | Clean; 8,513 lines. |
| `docs/wiki/pages/tailoring-a-resume.md` (user) | how-to | `[synthesis]` audit tags and a JS-symbol `Grounding:` header shown to users (`:6-12`, `:25`) | **Mixed — MED** (scaffolding leaks into user copy). |
| `docs/wiki/pages/pipeline-stages.md` (dev) | reference | — | Clean. |

## 2. Audience mixing — declared vs actual

The machine audience is **not** what the header says for most docs. `scripts/project_docs_to_mdx.py:208-218` reads only a backtick token (`` `user` `` / `` `dev` ``), falls back to a path list (`:132-134`: `README.md`, `docs/install.md`, `vision.md`, `docs/walkthrough*`), and otherwise defaults to `dev`. Of the 16 L1 docs, only `README.md:4` uses the token.

| Doc | Declared `Audience:` (verbatim start) | Machine tier | Actual content | Rank |
|---|---|---|---|---|
| `README.md:4` | `` `user` `` — all three audiences | user | user + dev reference (`:235-276`, plugin tables, `PX-19`, `Sprint 8.3a`, `F-arch-01`) | **HIGH** |
| `docs/install.md:6` | humans installing Sartor for the first time | user (path) | user + maintainer runbook (`:305-337`) + "F-18" in a heading (`:255`) | **HIGH** |
| `docs/walkthrough.md:10` | humans using the app for the first time | user (path) | user + 25 code refs (`grep -cE "/api/\|\.py\b\|analyzer\.\|hardening\.\|\(\)" docs/walkthrough.md` → 25) | MED |
| `vision.md:17` | humans evaluating whether to use or contribute; LLM agents | user (path) | explanation for both; agent section `:324` | MED |
| `ACCESSIBILITY.md:6` | anyone … who relies on assistive technology | **dev** (default) | user-facing status page | **HIGH** — a user page is filed under dev on the site |
| `SECURITY.md:7` | humans deploying in a non-default tenancy; contributors | dev (default) | mixed; the "what stays on your machine" part is user-relevant | MED |
| `docs/system-model.md:8` | humans meeting the project … "a well-informed layman" | dev (default) | explanation; its wiki twin `docs/wiki/overview.md:8` is tagged `` `user` `` | **HIGH** — same content, two tiers |
| `docs/architecture.md:7` | humans contributing PRs; LLM agents | dev | dev | OK |
| `docs/PRODUCT_SHAPE.md:7` | humans and LLMs planning features | dev | dev | OK |
| `docs/walkthrough_example.md:7` | humans reading the walkthrough; future contributors | user (path) | user | OK |
| `CONTRIBUTING.md:6` | external contributors (humans) | dev | dev | OK |
| `AGENTS.md:8` | AI coding agents AND humans | dev | dev | OK |
| `docs/template_authoring.md` | **none** (no header) | not projected | user (uploaders) + dev (bundled templates) | MED |
| `docs/bundled_templates_LICENSE.md`, `CODE_OF_CONDUCT.md`, `CHANGELOG.md` | none | not projected | legal / log | LOW |
| `docs/governance/*.md` | contributors and agents (`charter.md:7`, `enforcement.md:9`, `metrics.md:8`) | dev | dev | OK |
| `docs/dev/*.md` | 10 of 42 loose files have **no** `Audience:` line (`AGENT_FAILURE_PATTERNS`, `AGENT_HANDOFF_TEMPLATE`, `app-blueprints-design`, `avatar-voice-tone-guidance`, `board-forge-sync-review`, `gate-window-class-study`, `generation-experience-rearchitecture`, `GROUNDING_METRIC`, `ORCHESTRATION_PLAYBOOK`, `RELEASE_ARC`); the rest use free prose ("whoever executes …") | dev (path) | dev | LOW (path rule covers them) |
| `docs/wiki/pages/*.md` | 39 pages, all tokenized: 26 `` `dev` ``, 13 `` `user` `` | as tagged | user pages carry `[synthesis]` tags and JS-symbol grounding headers | MED |

Two structural facts behind the table:

- **The audience gate checks presence, not value.** `scripts/check_doc_frontmatter.py:28-34` says so in its own docstring ("does not verify the audience value is a known token"). The "leak check" the IA design promises (`documentation-architecture.md:75`) has no implementation that reads the token.
- **The published nav ignores the tier.** `docs-site/content/docs/meta.json` is one flat list of 37 slugs; `agents`, `claude`, `contributing` sit between `system-model` and `security`, with no user/dev separator. `documentation-architecture.md:79` says `meta.json` "encodes the ICP + pillar ordering"; the file does not. (`meta.json` is generated; this reflects the local build — unverified against CI output.)

## 3. Voice and style-guide violations

### 3a. Wordmark rule (`doc-style-guide.md:37-58`)

Pattern: `(^|[^\`/.-])sartor\.([[:space:]]|$|[,;:)])`, heading lines (`:#`) separated out.

| Bucket | In-prose hits | Command scope |
|---|---|---|
| The 12-file swept surface (`doc-style-guide.md:53-55`) | **1** — `vision.md:68` ("…before any human sees them. sartor. / ships templates") | `README.md vision.md docs/install.md docs/walkthrough.md docs/architecture.md docs/system-model.md docs/PRODUCT_SHAPE.md CONTRIBUTING.md SECURITY.md ACCESSIBILITY.md AGENTS.md CLAUDE.md` |
| `docs/governance/*.md` (not in the swept list) | **7** (e.g. `charter.md:21`, `:74`, `:103`, `:126`, `:443`; `metrics.md:28`) | `:(glob)docs/governance/*.md` |
| Other top-level `docs/*.md` | 3 (`walkthrough_example.md:92`; `bundled_templates_LICENSE.md:8,10` — legal copyright line, arguably exempt) | `:(glob)docs/*.md` |
| `docs/dev/**` excluding `reviews/` | **49** (38 in `avatar-voice-tone-guidance.md`) | |
| `docs/ux/**` | 12 (`onboarding_audit_2026-05-25.md`) | |
| `agents/`, `commands/`, sub-READMEs | 7 | |
| **Excluded per work item 0002** — `docs/wiki/**` / `docs/dev/reviews/**` | 7 / 68 | `docs/dev/work/items/0002-wordmark-sweep.md` |
| Possessive / hyphen form `sartor.'s`, `sartor.-` (not caught above) | 30 outside the exclusions | `git grep -nE "sartor\.['’-]" -- '*.md' ':!docs/wiki/**' ':!docs/dev/reviews/**'` |

Headings: 28 H1/H2 lines carry the wordmark outside the exclusions. Most are the allowed `# Vision — sartor.` form. Three read as phrases and so violate `doc-style-guide.md:50-51`: `docs/install.md:1` ("# Installing sartor."), `docs/walkthrough.md:1` ("# Using sartor. — screen-by-screen walkthrough"), `CONTRIBUTING.md:1` ("# Contributing to sartor."). Also `documentation-architecture.md:1` ("how sartor.'s docs are organized").

Three findings the rule does not yet cover:

- **HIGH — a rule conflict, not a violation.** `doc-style-guide.md:9-10` scopes the rule to "user-facing UI copy". `docs/dev/avatar-voice-tone-guidance.md:942` freezes the assistant's identity as "lowercase 'sartor.' with the trailing period", and shipped UI follows it: `templates/index.html:1148` ("Ask how sartor. works or how to use it"). The two docs give opposite instructions for the same string. D1 must pick one before a lint can exist.
- **MED — a third form.** The 13 user-tier wiki pages write bare lowercase `sartor` in prose **67** times and `Sartor` 2 times (e.g. `docs/wiki/pages/tailoring-a-resume.md:21`, "sartor reads the posting"). The style guide names only `sartor.` and `Sartor`. A lint that only hunts `sartor.` passes these.
- **Evidence for line-aware linting:** `vision.md:68` was written 2026-07-02 (`git blame`), before the 2026-07-13 sweep, and survived it. The wordmark sits at end-of-line with the sentence continuing on `:69`. A line-local check reads it as a sentence ending.

### 3b. Jargon before definition (`doc-style-guide.md:104-105`)

| Doc | Term | First use | Expansion | Rank |
|---|---|---|---|---|
| `README.md` | LLM | `:11` | none (`grep -c "large language model" README.md` → 0; 6 uses) | **HIGH** — front door |
| `README.md` | JD | `:110` | none as "(JD)"; "job description" appears at `:9` unlinked to the acronym | MED |
| `README.md` | C-0, PX-19, PX-20, Sprint 8.3a, F-arch-01 | `:254`, `:292` | none; internal tracker IDs on the user tier | **HIGH** |
| `docs/walkthrough.md` | LLM | `:13` (first body line) | `:30-32` — after first use | LOW |
| `docs/install.md` | LLM, JD | `:570`, `:586` | none in file | MED |
| `docs/install.md` | F-18 (heading) | `:255` | none | MED |

This recurs: `docs/ux/onboarding_audit_2026-05-25.md:68` flagged "README never defines [LLM]" four months ago, and it still holds. Under charter C-11 a second instance calls for a gate, not another note.

### 3c. Hedging, marketing, and reader-blaming words

The guide bans "simply", "just", "easy", "obviously", hype ("powerful", "seamless", "revolutionary"), and figurative phrasing ("choke on", "cripple", "sanity check", "blind to") (`doc-style-guide.md:102-109`). Counts by surface. **User core** is README, vision, install, walkthrough, walkthrough_example, ACCESSIBILITY, SECURITY, and the 13 `` `user` `` wiki pages. **Dev** is `docs/dev/**` minus reviews, AGENTS, CLAUDE, and governance. Case-insensitive, whole-word.

| Word | User core | Dev | Real violations seen in user core | Candidate for ban list? |
|---|---|---|---|---|
| `simply` | 1 | 55 | `docs/wiki/pages/recruiter-pipeline-tab.md:49` | **Yes** — low false-positive rate |
| `just` | 18 | 574 | 0 reader-blaming imperatives. All sampled are "only" or "merely" (`docs/install.md:345`, `docs/walkthrough.md:179`) | **Only as `just + imperative verb`** (repo-wide pattern hit 1 doc instance: `commands/prompt-tune.md:48`) |
| `easy` / `easily` | 0 / 0 | 16 / 7 | — | Yes (user tier) |
| `obviously` / `clearly` | 0 / 1 | 12 / 12 | `docs/walkthrough_example.md:215` ("clearly-irrelevant") | `obviously` yes; `clearly` warn only |
| `sanity check` / `sanity-check` | 1 / 1 | 13 / 5 | `docs/walkthrough_example.md:258`; `CONTRIBUTING.md:33` | **Yes** (named in the guide) |
| `powerful`, `seamless`, `revolutionary`, `cripple`, `choke`, `blind to` | 0 each | 1, 2, 1, 1, 4, 3 | — | Yes (cheap, guide-named, currently clean on user tier) |
| `genuinely` | 2 | 173 | `docs/install.md:148` | Warn (intensifier; heavy dev use) |
| `actually` | 10 | 314 | intensifier use common | Warn only |
| `honest` / `honestly` | 13 / 1 | 127 / 45 | `README.md:211` ("*The honest catch:*"), `:231`, `vision.md:3` ("answers one question, honestly") | **Warn on the user tier** — asserting honesty is a claim, and the guide prefers showing the mechanism |
| `first-class` | 5 | 16 | `docs/system-model.md:60,90`; `docs/walkthrough.md:174` | Warn (jargon for a lay reader) |
| `load-bearing`, `under the hood` | 6, 8 | — | jargon or figurative for lay readers | Warn on the user tier |
| `robust`, `leverage` | 0 | 17, 22 | — | Dev-tier warn at most |
| Exclamation marks in prose | 0 | — | — | Yes (currently clean) |

Commands: `git grep -iwE "<word>" -- <surface>`. The `just` imperative pattern: `git grep -niE "\bjust (click|run|paste|type|open|set|use|add|delete|edit|re-?run|restart|install|pick)"`.

### 3d. Characterizations of other products (`doc-style-guide.md:60-80`)

- User tier: **none found.** `vision.md:39-41` and `:315` ("not … a generic résumé template generator") describe Sartor's own scope, which the rule permits. AFFIRM.
- LOW: `docs/dev/avatar-voice-tone-guidance.md:366` recommends assistant copy "sartor. can't guarantee any resume passes ATS — **no tool can**". That is a category claim. It is not in `analyzer.py`, `static/*.js`, or `templates/*.html` (grep → 0).
- LOW: `docs/bundled_templates_LICENSE.md:62` names "Jobscan's ATS template guidance". This is attribution, not characterization; allowlist it.

Command: `git grep -niE "generic (ai|tool|résumé|resume)|other (tools|products)|unlike (most|other|typical)|competitor|chatgpt|jobscan|\bteal\b|rezi|kickresume|no tool can" -- <scope>`.

## 4. Duplication — one fact, several homes

`scripts/check_doc_single_home.py` passes (16 docs). By its own docstring (`:21-35`) it checks only **byte-identical normalized paragraphs ≥240 chars** across the 16-file `PUBLISHED_DOC_FILES` registry (`check_doc_frontmatter.py:73-75`). It misses:

1. **HIGH — the deterministic-module list: 4 variants in live docs, 105 frozen copies.** The code truth is 8 modules (`tests/test_construction_boundary.py:27-36`, including `docx_to_persona_html.py`). `AGENTS.md:51` has 8. `README.md:263`, `vision.md:158-160`, and `docs/dev/AGENT_HANDOFF_TEMPLATE.md:276-277` have 7. `docs/system-model.md:79` has 5. The template section is `<!-- verbatim -->`, so `git grep -l 'No LLM calls in \`hardening.py\`' -- 'docs/dev/handoffs/*'` → **105** handoffs carry the stale 7. The gate misses this because the lists are list items or short lines, not ≥240-char paragraphs, and because handoffs are outside the registry.
2. **MED — README restates install.** Demo mode (`README.md:165-178` vs `docs/install.md:275-303`; "demo still wins: nothing spends" appears in both, `README.md:178` / `install.md:301`), container named-volume guidance (`README.md:156-159` vs `install.md:158-176`), and headless flags (`README.md:180-184` vs `install.md:255-273`). The README header claims "Everything else is **cited**" (`README.md:5`). These are paraphrases, which the gate cannot see.
3. **MED — `system-model.md` ↔ `docs/wiki/overview.md`.** The "Open revision points" list is near-verbatim (`system-model.md:166-167` vs `overview.md:88-89`, identical except line wrapping), and "an AI coding agent treated as a first-class inhabitant" appears at `system-model.md:60` and `overview.md:48`. The gate excludes `docs/wiki/**`.
4. **MED — overlapping "Authoritative for" claims.** `AGENTS.md:11-14` and `CONTRIBUTING.md:7-9` both claim "the ruff + mypy + pytest minimum-bar" and `PROMPT_VERSION` discipline. `AGENTS.md:47` then names `scripts/gate.py` as "the single definition". Three homes claim one fact. Nothing checks that `Authoritative for` claims are disjoint.
5. **LOW — eval-smoke cost** (`~$0.35-0.40`): `AGENTS.md:288`, `README.md:275`, `evals/README.md:43,981`. The values agree today.
6. **AFFIRM — the six wizard step names** match across `README.md:108-113`, `docs/walkthrough.md:195-421`, `docs/wiki/pages/tailoring-a-resume.md:19-70`, and `static/app.js:7026` (`_WIZARD_STEP_LABELS`).

What the gate structurally misses: paraphrase; lists and short lines; anything outside the 16-file registry (wiki, `docs/dev/**`, handoffs, `agents/`, `commands/`); and code-vs-doc duplication (a doc restating a constant that lives in code).

## 5. Headings, structure, scannability

- **MED — charter clauses cannot be linked to.** `docs/governance/charter.md` has 481 lines and 6 headings. C-0 through C-12 are bold paragraphs (`:64-288`), not headings, so no `#c-7` anchor exists. Every "charter C-7" citation across the repo points at the whole file.
- **MED — header placement is inconsistent.** The P/A/A block starts at line 3 in 13 of 16 L1 docs, at `vision.md:13` (after an opening quote and acronym list), and at `docs/walkthrough.md:5` (after a lead sentence). `docs/template_authoring.md` has none. The projector keys on the first `> **Purpose:**` (`project_docs_to_mdx.py:120`), so this works, but a reader meets two opening styles.
- **MED — ledgers too large to scan.** `docs/dev/RELEASE_CHECKLIST.md`: 4,424 lines, 22 headings (201 lines/heading). `docs/architecture.md`: 84 lines/heading. `CHANGELOG.md`: 8,513 lines.
- **LOW — README density.** 9 lines exceed 400 characters (`awk 'length>400' README.md | wc -l`), and there are 5 emoji status lines (`README.md:291-295`) whose meaning is carried only by the glyph and the bold label.
- **LOW — dated artifacts at the `docs/dev/` root.** `window-8.5-*`, `V1_0_5_VERIFICATION.md`, and `dependency-triage-pre-v1.1.0.md` sit beside live design docs. Their frozen status is not signalled by location.
- **AFFIRM** — `docs/walkthrough.md` uses a repeating "What you see / What you do / Under the hood / Verify" frame per step, which scans well. The "Under the hood" slot is where the dev content lives, so D1 can split along that seam.

## 6. Freshness — claims that contradict code or each other

| # | Rank | Claim | Contradicted by |
|---|---|---|---|
| F1 | **HIGH** | `docs/install.md:24-26`: "See `[Cost guidance](../README.md#install)` for the per-application breakdown; budget guards are documented in SECURITY.md" | `README.md:121-184` has no cost breakdown and points back to install (`:160`). `grep -ci budget SECURITY.md` → 0. `README.md:162-163`: "Sartor has no built-in budget guard." A circular pointer ends at a claim of something that does not exist. The link checker passes because the anchor resolves. |
| F2 | **HIGH** | `docs/walkthrough.md:393-401`: Generate "calls `generate()`… Model: Sonnet 5 … Cost ~$0.05–$0.15 … ~30–60s" | `docs/architecture.md` LLM-routing block (after `:536`): "generate's route is CONDITIONAL: it only fires when Compose was not frozen — the common path assembles the résumé body deterministically with zero LLM calls." The user doc overstates cost and wait on the common path. |
| F3 | **HIGH** | `README.md:292`, `vision.md:94`, `AGENTS.md:20`: charter "C-0…C-6" / "C-1…C-6 clauses" | `docs/governance/charter.md:146-288` defines C-7 through C-12. |
| F4 | **HIGH** | 7-module deterministic list (`README.md:263`, `vision.md:158`, `AGENT_HANDOFF_TEMPLATE.md:276`); 5-module list (`system-model.md:79`) | `tests/test_construction_boundary.py:27-36` (8 modules, including `docx_to_persona_html.py`). `README.md:263` also says the boundary is "enforced by tests + a route-security hook". The route-security hook enforces `_safe_username`/`_within`, not the LLM boundary (`CLAUDE.md` hook list). |
| F5 | MED | `AGENTS.md:55`: "all eight LLM call kinds" | `grep -oE 'call_kind="[a-z_]+"' analyzer.py \| sort -u \| wc -l` → 20. `architecture.md`'s `accDescr` lists 21 call sites. `AGENTS.md:48`'s Sonnet list also omits the four `draft_*` calls the diagram shows. |
| F6 | MED | `CLAUDE.md` subagent catalog lists 9; "the other six subagents use the undated alias `claude-sonnet-5`" (same list at `README.md:269`) | `ls agents/` → 11 (`n1-judge.md`, `n1-refuter.md` missing). `grep "^model:" agents/*.md` → 7 × `claude-sonnet-5`, 1 × `claude-opus-5` (`n1-judge`), 3 × Haiku. |
| F7 | MED | `docs/PRODUCT_SHAPE.md:26-43` "The asymmetry matrix (where we are today)": summaries have no own table, no variants, and are not scored against the JD; `Bullet` is cited at `db/models.py:134` | `db/models.py:357` `class SummaryItem`, `:445` `class ExperienceSummaryItem`; `:134` sits just above `class ExperienceTitle` (`:136`); `Bullet` is at `:179`. `:435` still says "v1.0 (next branch after `feat/release-visual-ia`)" while `pyproject.toml:7` is `1.0.9`. |
| F8 | MED | `docs/wiki/SCHEMA.md:105`: overview "plus the five Sprint-6.5 education guides … are the `user`-tier pages" | `grep -l 'Audience:\*\* \`user\`' docs/wiki/pages/*.md` → 13 pages. |
| F9 | MED | `docs/walkthrough.md`: 8 route links target `../app.py` (e.g. `:393`, "`[/api/generate](../app.py)`") | `blueprints/generation.py:919` (`@generation_bp.route("/api/generate"…)`). The link resolves, so `check_doc_links.py` passes, but it points at the wrong file. |
| F10 | LOW | `README.md:274`: dev loop "`ruff check . && mypy . && pytest` … CI runs the same" | `scripts/gate.py:11-15`: also `ruff format --check .`, and pytest split into `-m "not ux" -n auto` + `-m ux`. `CONTRIBUTING.md:33-35` has the correct list. |
| F11 | LOW | `docs/dev/AGENT_HANDOFF_TEMPLATE.md:274-275`: `route-security-lint` "enforces this on `app.py` edits" | `AGENTS.md` "Key patterns": enforced "on `app.py` + `blueprints/**.py`" (PX-21 widen). Propagates to handoffs through the verbatim section. |
| F12 | LOW | `SECURITY.md:11-12`: sibling "[`CLAUDE.md`] (contract)" | `CLAUDE.md` header: the universal contract is `AGENTS.md`. |

AFFIRM checks: README's "4 ATS-safe templates" (`README.md:111`) matches `personas/bundled/` (classic, modern, spacious, tech). Model IDs in `AGENTS.md:48` match `analyzer.py:848-849`.

---

## Implications for the D1 IA + governance design

1. **Make the audience token mandatory and valued, then derive nav from it.** Extend `check_doc_frontmatter.py` so `**Audience:**` must start with `` `user` `` or `` `dev` `` on every projected doc. Generate `meta.json` with user/dev separators from the token. *False-positive risk:* low. The real risk is **mis-tagging**: `ACCESSIBILITY.md` and `system-model.md` default to `dev` today (§2), so the first run forces ~14 human tier decisions, not a mechanical fill.
2. **`docs/user/` is a subset, not a rename.** README, install, and walkthrough each carry dev sections (`README.md:235-276`, `install.md:305-337`, walkthrough "Under the hood" ×8). Split them along those seams: the maintainer runbook goes to `docs/dev/`, and "Under the hood" moves to a linked dev page. Otherwise `docs/user/` inherits the mixing.
3. **Settle the wordmark conflict before writing the lint** (`doc-style-guide.md:9-10` vs `avatar-voice-tone-guidance.md:942` / `templates/index.html:1148`). Also rule on bare `sartor` (67 wiki hits). The owner decides this, not the lint author.
4. **Wordmark lint spec:** flag `sartor.` followed by whitespace+lowercase, `'s`, `-`, or a line break whose next line starts lowercase. Allow `# … — sartor.` title form. Exclude fenced code, backtick spans, paths (`sartor.py`), `docs/wiki/**`, `docs/dev/reviews/**` (item 0002), and legal lines (`bundled_templates_LICENSE.md:8,10`). *False-positive risk:* medium. A sentence that legitimately ends on the standalone wordmark ("through sartor.") is ambiguous, so route it to a warning. Frozen handoffs and `CHANGELOG.md` history need an exclusion or they go red on history.
5. **Banned-words lint, tiered.** **Block** on the user tier: `simply`, `easy`, `easily`, `obviously`, `powerful`, `seamless(ly)`, `revolutionary`, `sanity[- ]check`, `choke`, `cripple`, `blind to`, and `just` + imperative verb. **Warn** on the user tier: `honest(ly)`, `genuinely`, `actually`, `clearly`, `first-class`, `load-bearing`, `under the hood`. **Do not** ban bare `just`: 18 user-core hits, 0 reader-blaming ones found. *False-positive risk:* low for the block list (nearly all at zero on the user tier today); high for bare `just`/`actually`. Quoted "Don't" examples in the style guide itself (`:72`, `:102-109`) need a `<!-- lint-allow -->` region.
6. **Jargon-first-use lint (user tier only):** for a closed acronym list (LLM, JD, ATS, SSE, API), the first occurrence must be in or after an expansion within the same doc. Block internal tracker IDs (`PX-\d+`, `F-[a-z]+-\d+`, `Sprint \d`, `C-\d+`, `item \d+`) on user-tier pages. *False-positive risk:* medium. A header acronym block (`vision.md:8-11`) must count as the definition, and `C-1`-style strings can collide with ordinary text.
7. **Code-truth anchors for enumerations.** The module list (F4), call-kind count (F5), and subagent roster (F6) drifted because docs restate what code enumerates. Replace each with a pointer, or add a test that parses the doc list and compares it to `DETERMINISTIC_MODULES` / `agents/*.md` / `call_kind` literals. *False-positive risk:* low; it breaks whenever someone rephrases the list, and that is the purpose.
8. **Widen single-home, but as a report first.** Add (a) `docs/wiki/**` against L1, (b) a sentence-level or shingled near-match (≥ ~25 tokens) in place of the ≥240-char byte-identical rule, and (c) a disjointness check on normalized `Authoritative for` phrases. *False-positive risk:* high for (b), since the wiki is designed to synthesize L1. Ship it as a non-blocking report with a reviewed-pairs allowlist.
9. **Dead links: the gate is sound; add semantic and scope checks.** `check_doc_links.py` already resolves files and anchors repo-wide (540 files). Add: `[[wikilinks]]` outside `docs/wiki/`; link-to-code targets that must contain the named symbol (F9: `/api/generate` → `app.py`); and a projection-time check on the rewritten `.mdx` links. *False-positive risk:* symbol checks break on renames, which is intended.
10. **Anchor the charter.** Give C-0 through C-12 their own `###` headings so citations can deep-link and a lint can verify `C-\d+` references against defined clauses. That check alone would have caught F3. *False-positive risk:* low.
11. **Stale-snapshot flags.** L1 docs that say "where we are today", "next branch", or "not yet resolved" (`PRODUCT_SHAPE.md:26,435`, `system-model.md:156`) should carry a `DOC-STATUS` with a date or move to `docs/dev/`. A lint could require a `DOC-STATUS` on any L1 doc matching those phrases. *False-positive risk:* medium (phrases recur in legitimate prose).
12. **The doc-writing skill should run the lints, not restate them.** Keep the rules in `doc-style-guide.md` and the lint registry. The skill's job is the ordering: choose tier and Diátaxis type first, write the P/A/A header, cite instead of restating, then run the lints. That keeps the single-home rule from drifting between skill and guide.
