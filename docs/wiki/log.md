# Wiki log

> Append-only record of ingest + lint runs and structural changes to the wiki.
> Newest entry last. See [`SCHEMA.md`](SCHEMA.md) for the source model these record.

## 2026-06-08 — skeleton stood up (`docs/wiki-skeleton`)

Created the committed `docs/wiki/` skeleton (WS-4a step 2):
[`SCHEMA.md`](SCHEMA.md), [`index.md`](index.md), [`overview.md`](overview.md)
(seeded from and deferring to [`../system-model.md`](../system-model.md)), this
`log.md`, `.last_ingest_sha` (sentinel — no ingest yet), and the empty `pages/` home.
Added the root [`llms.txt`](../../llms.txt).

**No code ingest yet.** `pages/` is empty and `.last_ingest_sha` carries no SHA, so the
first `/wiki-ingest` (after the `/wiki-*` skills land in `feat/wiki-skills`, WS-4a step
3) performs a full cold pass. See
[`../dev/RELEASE_ARC.md`](../dev/RELEASE_ARC.md) §Phase 4.5.

## 2026-06-09 — first ingest: the excellence-walk source (`wiki/ingest-excellence-walk`)

**Mode: content-scoped ingest — NOT a code cold pass / diff pass** (WS-4a step 4). The
first real population of `pages/`. Scoped to the preserved excellence-walk source only,
synthesized per [`SCHEMA.md`](SCHEMA.md)'s page conventions + one grounding rule.

**Sources read** (all under [`../dev/excellence-walk/`](../dev/excellence-walk/)):
`excellence-walk.md` (master capture), `q1-overview.md`, `q2-consistency.md`,
`q3-downloads.md`, `README.md`. `walkthrough-sprint-plan.md` was read for provenance only
(its content is already folded into [`../dev/RELEASE_ARC.md`](../dev/RELEASE_ARC.md) §Phase
4.5) and got no page.

**Pages created (8):** `excellence-walk` (provenance hub), `system-model-derivation`,
`project-self-assessment`, `consistency-tracks-enforcement`, `non-dependency-downloads`,
`engineering-workstreams`, `llm-wiki-design`, `governance-extraction`. `index.md` updated;
`[[backlinks]]` reconciled bidirectionally.

**`.last_ingest_sha` deliberately LEFT at the sentinel.** That checkpoint tracks the last
successful **code** ingest (per [`SCHEMA.md`](SCHEMA.md) "Source model"); this was a
*docs* ingest, not a code pass. Advancing it would falsely assert the code was ingested
and would prematurely silence the commit-time freshness reminder before WS-4b ever runs.
It stays the sentinel until `wiki/cold-ingest-code` (WS-4b, after Sprint 6.4). The
excellence-walk pages are grounded in committed docs, so they are not subject to the
`sha → HEAD` code-staleness check.

**The source stays put — it already *is* the raw layer.** `docs/dev/excellence-walk/`
remains a frozen, git-tracked source. Per [`SCHEMA.md`](SCHEMA.md), git already provides
the raw-layer role for tracked material (immutable, diffable, provenanced), so `raw/`
stays at zero and **nothing is copied or relocated into a `raw/` folder** — the wiki pages
synthesize *from* this source and cite it. (Any future `raw/` is the Governance pass's
concern, scoped to genuinely-homeless *prescriptive* material — not a relocation home for
this descriptive capture; see [`pages/governance-extraction.md`](pages/governance-extraction.md).)

**Verification (lint + audit checks, per the `/wiki-lint` + `/wiki-audit` procedures).**
Lint: **PASS** (no ERROR) — all 8 pages present and listed in `index.md`; every
`[[backlink]]` resolves to an existing page slug; every relative link target resolves
(22/22); no orphans; staleness = sentinel (a code cold pass is pending — expected, not an
error); code-module coverage = INFO (WS-4b). Audit (`consistency-tracks-enforcement` +
`governance-extraction`): all load-bearing claims **SUPPORTED** against cited sources; no
UNSUPPORTED. Freshness reminder confirmed **silent** (sentinel carries no 40-char SHA).

## 2026-06-13 — second ingest: the code cold pass (`wiki/cold-ingest-code`)

**Mode: code COLD pass** (WS-4b, item 5) — the first ingest of the *code* architecture,
distinct from the 2026-06-09 content-scoped pass. The repo at HEAD `9816b45` was read,
chunked per the [`../architecture.md`](../architecture.md) module map, and synthesized
into **16 new `pages/`**, every code claim `path:line`-grounded per
[`SCHEMA.md`](SCHEMA.md)'s one grounding rule.

**Sources read** (HEAD `9816b45`): `analyzer.py`, `hardening.py`, `parser.py`,
`generator.py`, `scraper.py`, `json_resume.py`, `corpus_to_json_resume.py`,
`pdf_render.py`, `app.py`, `db/` (`models.py`, `build_context.py`, `persist_run.py`),
`evals/` (`runner.py`, `bootstrap.py`, `rubrics/`), `dashboard/`, `static/app.js`,
`templates/index.html`, plus [`../architecture.md`](../architecture.md) +
`../diagrams/*.mmd` (retired 2026-07-10, `docs/diagrams-a11y`).

**Pages created (16):** `code-module-map` (hub), `deterministic-llm-boundary`,
`prompt-version-discipline`, `context-set-contract`, `iteration-audit-chain`,
`corpus-data-model`, `corpus-to-output-reach`, `application-audit-chain`,
`pipeline-stages`, `llm-call-catalog`, `generation-and-grounding`, `route-surface`,
`frontend-wizard`, `document-rendering`, `eval-harness`, `diagnostics-console`.
[`index.md`](index.md) updated; `[[backlinks]]` reconciled bidirectionally, incl. new
inbound links into `consistency-tracks-enforcement`, `project-self-assessment`,
`engineering-workstreams`, and `non-dependency-downloads`.

**Audience-tag convention authored** ([`SCHEMA.md`](SCHEMA.md) "Audience tag"): a
machine-parseable blockquote line `> **Audience:** ` + a backticked `user`|`dev` token,
plus blanket path→audience rules. All content pages stamped — [`overview.md`](overview.md)
= `user`; the 24 `pages/` = `dev`. `audience: user` education pages are **reserved** for
the Sprint-6.5 sweep (a lint INFO, not an error). This is the boundary the planned
doc-assistant access plane gates on (see
[`../dev/memory-architecture.md`](../dev/memory-architecture.md)).

**`.last_ingest_sha` advanced sentinel → `9816b45851acf5aac3e4249e14bdd8664a8fab29`** —
this *is* the code pass, so the checkpoint now carries a real 40-char SHA and the
commit-time freshness reminder goes live (it was deliberately silent under the sentinel).

**Diagram drifts folded in** (the re-read caught them, as tracked in
[`../dev/RELEASE_CHECKLIST.md`](../dev/RELEASE_CHECKLIST.md)): Step-2 in
`../diagrams/pipeline.mmd` (retired 2026-07-10, `docs/diagrams-a11y` —
content lives solely in `../architecture.md` now) + the embedded copy in
[`../architecture.md`](../architecture.md) "GET INTERVIEW QUESTIONS" → "GET CLARIFYING
QUESTIONS" (the Step-6 iterate flow was already correct);
`../diagrams/data-flow.mmd` (retired 2026-07-10) cover-letter node brought up to
`cover_TS.docx /<br/>.pdf / .md` to match the already-correct `../architecture.md`.

**Authoring method.** A 16-page Workflow — one author agent per page, then a *different*
adversarial grounding auditor per page (the [`/wiki-audit`] discipline). 8 pages passed
clean; 8 had drift the audit caught and the fix pass corrected — e.g. the `app.py` route
count (75 → **92** `@app.route`), `check_refinement_scope` as a 2nd raw LLM call site that
bypasses the `_call_llm` funnel, `_emit_call_log`'s JSON key (`call`, not `call_kind`), and
`CandidateInfo`'s `linkedin_url`/`website_url` (not `links`).

**Verification (lint + audit).** Lint: **PASS** (no ERROR) — all **24** `pages/` ↔
`index.md` agree both ways; every `[[backlink]]` resolves (no dangling); no orphans
(`code-module-map` is the hub); staleness now = a real 40-char SHA (= HEAD, 0 code files
changed since). Audit: the adversarial per-page pass + an independent re-verify of the
highest-impact structural claims (route count, the scope-check call site, the telemetry
key) all SUPPORTED at HEAD; zero UNSUPPORTED remain. Gate: `ruff` ✓ · `mypy` ✓ · `pytest`
**1169/1169** (docs-only — no `.py` touched).

## 2026-06-13 — diff refresh: Chart.js vendoring (`chore/wiki-refresh`)

**Mode: diff** (`9816b45` → `e4e01fd`). Triggered by PX-01 (`fix/vendor-chartjs`,
2026-06 product review), which vendored Chart.js to
[`../../static/vendor/chart.umd.min.js`](../../static/vendor/chart.umd.min.js) and
dropped the `cdn.jsdelivr.net` runtime fetch.

**Scope.** The 78-file diff split: **38** files under `docs/dev/reviews/` were
**excluded** (the review archive forbids wiki ingestion — provenance model); **~28**
`docs/wiki/` files are the artifact, not sources; of the 11 actionable source changes,
`../architecture.md` + `../diagrams/{pipeline,data-flow}.mmd` were WS-4b's own
drift-fixes **already reflected** in the pages it wrote (re-read confirmed, no page
change). A whole-wiki grep confirmed exactly one stale line.

**Page changed (1).** [`pages/diagnostics-console.md`](pages/diagnostics-console.md) —
the shared-drawer note "Chart.js from CDN" → "Chart.js — vendored at
`static/vendor/chart.umd.min.js`, no runtime CDN", with a `path` cite per the grounding
rule. `index.md` unchanged (its one-liner didn't reference the CDN).

**Verification.** Wiki grep for `cdn`/`chart…from…CDN` → only score-over-time chart
hits remain. Gate: `ruff` ✓ · `mypy` ✓ · `pytest` **1169/1169** (docs-only — no `.py`).

## 2026-06-14 — diff refresh: v1.0.6 PX band (`chore/wiki-refresh-px-v106`)

**Mode: diff** (`e4e01fd` → `93a34b9`). The v1.0.6 PX band since the last code-keyed
checkpoint: **PX-02** (profile/website scrape re-wire — the only substantial code change),
PX-08/PX-13 (egress falsifiability test + eval-smoke gate exit-2 guard), PX-03/05/07
(disclosure docs), PX-09/PX-14 (C-0 no-invention reword + GROUNDING_METRIC three-source
union — a [`../dev/GROUNDING_METRIC.md`](../dev/GROUNDING_METRIC.md) *doc* reword, **not** a
code change).

**Scope.** Canonical living docs (`AGENTS.md`, `CONTRIBUTING.md`, `SECURITY.md`,
`vision.md`, [`../system-model.md`](../system-model.md), `../walkthrough.md`, `../dev/*`,
`CHANGELOG.md`, `pyproject.toml`, `llms.txt`, …) are wiki-**referenced**, never duplicated
(design fork D5) — no page restates them. The `docs/wiki/` files in range
([`overview.md`](overview.md), [`pages/diagnostics-console.md`](pages/diagnostics-console.md),
this `log.md`, `.last_ingest_sha`) are the prior `chore/wiki-refresh` pass's own artifacts,
already current at `e4e01fd` (`overview.md`'s PX-09 re-sync to `../system-model.md` was done
there — a re-read confirmed, no page change this round). New test files add no new
wiki-keyed concept. Of the actionable **source** changes, four facts drifted.

**Pages changed (4).**
- [`pages/route-surface.md`](pages/route-surface.md) — `@app.route` count `92` → **93**;
  added the PX-02 [`app.py:fetch_profile`](../../app.py) route
  (`POST /api/users/<u>/profile/fetch`), `_safe_username` + `_within(config_path, CONFIGS_DIR)`-gated,
  running the deterministic `scraper.fetch_profile_content` and caching into
  `Candidate.online_profile_text`.
- [`pages/corpus-data-model.md`](pages/corpus-data-model.md) — alembic head `0009` → **0010**
  ([`0010_online_profile_text.py`](../../db/migrations/versions/0010_online_profile_text.py),
  `down_revision="0009"`): adds `Candidate.online_profile_text`, the PX-02 scrape cache — a
  **DISTINCT** channel from the `profile_text` β.6 positioning summary; native `ADD COLUMN`
  (no batch recreate) because `candidate` is a parent table (cascade-delete safety).
- [`pages/eval-harness.md`](pages/eval-harness.md) — `PROMPT_VERSION` `2026-06-12.2` →
  **`2026-06-13.1`** (PX-02 added the `<candidate_web_presence>` block).
- [`pages/prompt-version-discipline.md`](pages/prompt-version-discipline.md) — the same stale
  `PROMPT_VERSION` literal → **`2026-06-13.1`**.

[`index.md`](index.md) corpus-data-model one-liner `0009` → `0010`. No `[[backlink]]` changes
(no new pages). `assemble_source_union` wording **left as-is** — already the 3-source union;
PX-14 changed `GROUNDING_METRIC.md`, not the function body (verified: the `hardening.py` diff
touches only `CandidateInfo` + `build_context_set`).

**`.last_ingest_sha` advanced `e4e01fd` → `93a34b9738a5272d39539675d3fe56ea91b5fd31`** (HEAD).

**Authoring + verification.** Four direct factual edits (every value pre-verified against
HEAD), then a per-page **adversarial grounding audit** (author≠auditor; one read-only
auditor per page, falsify-against-source). 3 pages PASS clean; the route-surface audit
**caught a real error** — the first draft wrongly called `fetch_profile` `_within`-free, but
it runs `_within(config_path, CONFIGS_DIR)` ([`app.py`](../../app.py):256-258) — corrected +
re-grounded. All changed claims SUPPORTED at HEAD (`grep -c @app.route app.py` = 93; head
`0010`, nothing revises it; `PROMPT_VERSION` = `2026-06-13.1` at `analyzer.py:280`). Lint:
24 `pages/` ↔ `index.md` agree both ways; every `[[backlink]]` resolves; staleness now =
HEAD. Gate: `ruff` ✓ · `mypy` ✓ (159 files) · `pytest` **1191/1191** (docs-only — no `.py`;
the one full-suite failure was the known intermittent UX-tier flake
`test_positioning_pin_preserves_title_pin`, green on isolated re-run).

## 2026-06-14 — content pass: user-facing education guides (`feat/education-tailor-corpus-wizard`)

**Mode: hand-authored content pass — NOT a code ingest / diff pass** (Sprint 6.5, #1 + #18).
The first authoring INTO the wiki's reserved `audience: user` section, mirroring the in-app
education copy this branch ships. Like the 2026-06-09 excellence-walk pass, this is a
*content* pass: it does **not** advance `.last_ingest_sha` (that checkpoint tracks the last
**code** ingest, per [`SCHEMA.md`](SCHEMA.md) "Source model"). The branch *does* change code
(`static/app.js`, `static/style.css`, tests), so the dev-tier
[`pages/frontend-wizard.md`](pages/frontend-wizard.md) may now drift from HEAD — that
code-keyed refresh is deferred to a later `chore/wiki-refresh` / the version-bump branch, and
leaving the checkpoint at `93a34b9` keeps the freshness reminder correctly flagging it.

**Pages created (5, `audience: user`):** `using-sartor` (the first-run hub),
`tailoring-a-resume`, `career-corpus`, `resume-templates`, `candidate-memory`. Each mirrors
the in-app `_HELP_REGISTRY` copy (`static/app.js`) and the wizard surfaces in
`templates/index.html`; plain-language, no technical background assumed.

**Wiki meta updated.** [`index.md`](index.md) gained a "User-facing education" section and
its "Reserved / planned" note flipped from *reserved* to *authored*; [`SCHEMA.md`](SCHEMA.md)
"Audience tag" + "Status" updated (the `user`-tier set is now [`overview.md`](overview.md) +
these five); [`overview.md`](overview.md) gained a one-line "new here?" pointer to
`using-sartor`. `[[backlinks]]` reconciled bidirectionally among the five (hub ↔ guides).

**Verification.** Every `[[backlink]]` resolves to an existing page slug (the five new guides
+ the cross-links among them); the only relative links out are to [`overview.md`](overview.md),
which resolve. Grounding: each user page describes shipped, observable behavior and names the
source surfaces (`templates/index.html` panels + `static/app.js` `_HELP_REGISTRY`); the
no-fabrication promise defers to [`overview.md`](overview.md) (D5 — not restated). The full
quality gate (`ruff` + `mypy` + `pytest` incl. `-m ux` / the axe gate) is run on the branch's
combined code + content before commit; the result is recorded with the branch in
[`../dev/RELEASE_CHECKLIST.md`](../dev/RELEASE_CHECKLIST.md).

## 2026-06-15 — diagnostics-console education landed; dev-tier drift noted (`feat/education-diagnostics-annotate`)

**Mode: note only — NOT an ingest / diff pass** (Sprint 6.5, #15 + #20 + #22). This branch
applied in-app help to the localhost `/_dashboard` console (its own ported help mechanism in
`dashboard/templates/dashboard.html` + lay-language annotate/empty-state copy). The console is
a **dev surface**, so the education is dev content — **no `audience: user` page is authored**;
the in-app copy is the home for it.

**Dev-tier drift.** The dev-tier [`pages/diagnostics-console.md`](pages/diagnostics-console.md)
now drifts from HEAD (the console gained a `#helpModal`, a per-tab `_DASH_HELP` registry, and
rewritten copy). As with the 2026-06-14 frontend changes, `.last_ingest_sha` is **left at**
`93a34b9` (this is not a code ingest), which keeps the commit-time freshness reminder correctly
flagging the dev-tier pages. The consolidated code-keyed refresh (`diagnostics-console.md` +
`frontend-wizard.md`) is deferred to a later `chore/wiki-refresh` / the version-bump branch —
do NOT spin a standalone wiki branch.

**Follow-on (`docs/eval-stack-install-guide`, #17, 2026-06-15).** The user-facing install
docs branch appended **one sentence** to the same `dashboard/templates/dashboard.html`
`dashQuality` help body (an eval-stack install pointer → `CONTRIBUTING.md` / `docs/install.md`).
Same file, same conclusion: the `diagnostics-console.md` drift is already flagged above and
`.last_ingest_sha` stays at `93a34b9` — the deferred consolidated refresh picks this up too. No
new wiki branch.

## 2026-06-15 — diff refresh: Sprint 6.5 education (dev-tier pages) (`chore/version-bump-v1.0.6`)

**Mode: diff** (`93a34b9` → `7d8f427`). The consolidated, code-keyed dev-tier refresh deferred
by the 2026-06-14 (`feat/education-tailor-corpus-wizard`) content pass and the 2026-06-15
(`feat/education-diagnostics-annotate`) note — both left `.last_ingest_sha` parked at `93a34b9`
precisely so this version-bump branch would pick the drift up. The `/wiki-ingest` op is dormant
(not installed), so this pass was done by hand per [`SCHEMA.md`](SCHEMA.md)'s page + grounding
conventions.

**Scope.** The Sprint 6.5 education band since the parked checkpoint. The FRONTEND source changes
in range are [`../../static/app.js`](../../static/app.js) (+336),
[`../../dashboard/templates/dashboard.html`](../../dashboard/templates/dashboard.html) (+285),
[`../../static/style.css`](../../static/style.css) (+57), and
[`../../templates/index.html`](../../templates/index.html) (+19): the reusable in-app help
primitive (`#helpModal` + `openHelpModal` + `_HELP_REGISTRY` + `_initHelp`), per-surface
`(i)`-circle help, the KW3 new-user first-run tour (`_helpTourArmed` / `_maybeFireTourStop` /
`_fireWizardTourStop`), the dashboard's PORT of that primitive (`#helpModal` + `_DASH_HELP` +
`openDashHelp` + `_maybeFireDashHelp`), and the rewritten dashboard annotate / empty-state copy —
plus #17's one-sentence eval-stack pointer in the `dashQuality` help body. The `audience: user`
education guides ([`using-sartor`](pages/using-sartor.md), …) were already authored in the
2026-06-14 content pass and were **not** re-touched (D5 — content pass, not a code key). The
`../../ui_pages/{dashboard_console,selectors}.py` changes in range are Playwright POM / selector
test infrastructure — no wiki page describes that layer, so no page change.

**Pages changed (2, both `audience: dev`).**
- [`pages/diagnostics-console.md`](pages/diagnostics-console.md) — added an "In-app help: a ported
  primitive, not a shared import" section (the `.dash-pane-intro` summary + `(i)` rows;
  [`openDashHelp`](../../dashboard/templates/dashboard.html) +
  [`_DASH_HELP`](../../dashboard/templates/dashboard.html) keyed
  `dashPipeline`/`dashQuality`/`dashGroundedness`/`dashTuning`/`dashAnnotate`; the once-ever
  [`_maybeFireDashHelp`](../../dashboard/templates/dashboard.html); the deliberate-port-not-import
  point — reuses the wizard's `#helpModal` ids + `cb_help_seen:` prefix, never loads `app.js`) +
  the lay-language annotate/empty-state note. Added `dashboard/templates/dashboard.html` to the
  Sources header and a `[[frontend-wizard]]` backlink.
- [`pages/frontend-wizard.md`](pages/frontend-wizard.md) — extended the Concept line; added an
  "In-app help + the KW3 first-run tour" section ([`_HELP_REGISTRY`](../../static/app.js) +
  [`openHelpModal`](../../static/app.js) + [`_initHelp`](../../static/app.js) +
  [`_maybeAutoOpenHelp`](../../static/app.js) / `cb_help_seen:` seam; the shared `#helpModal`
  ([`templates/index.html`](../../templates/index.html)) + `.help-info` CSS
  ([`static/style.css`](../../static/style.css)); the KW3 tour —
  [`_helpTourArmed`](../../static/app.js) / [`_maybeFireTourStop`](../../static/app.js) /
  [`_fireWizardTourStop`](../../static/app.js), armed by `createUser` + an empty-corpus
  `_landingTab`, fired from `_wizardRender` / wizard entry, `offsetParent`-guarded). Added
  `static/style.css` to Sources + a `[[diagnostics-console]]` backlink.

[`index.md`](index.md) unchanged (both one-liners stayed true). No new pages (29 `pages/` total).
The new `[[frontend-wizard]]` ↔ `[[diagnostics-console]]` backlink pair is bidirectional. Neither
page carries a per-page source-SHA marker (`SCHEMA.md` stamps only the audience tag), so only
`.last_ingest_sha` advances.

**`.last_ingest_sha` advanced `93a34b9` → `7d8f427e16be8a9110de202026cb0becb79b6694`** (HEAD).

**Authoring + verification.** Direct factual edits; every cited symbol pre-verified at HEAD
(`openHelpModal`:1644 / `_initHelp`:1689 / `_HELP_REGISTRY`:1484 / `_armHelpTour`:1756 /
`_maybeFireTourStop`:1760 / `_fireWizardTourStop`:1772 in `static/app.js`; `openDashHelp`:893 /
`_DASH_HELP`:811 / `_maybeFireDashHelp`:927 / `#helpModal`:554 / `.dash-pane-intro` in
`dashboard/templates/dashboard.html`; `#helpModal`:872 in `templates/index.html`;
`.help-info`:891 / `.has-help-icon`:884 in `static/style.css`). Gate: `ruff` ✓ · `mypy` ✓ ·
`pytest` **1212/1212** (docs-only — no `.py` touched).

## 2026-06-16 — first self-documenting loop run: v1.0.7 band (`feat/self-documenting-wiki`)

**Mode: diff** (`7d8f427` → `a008f86`) — **the inaugural `/wiki-self-update` run.** This is
the loop ([`../dev/self-documenting-loop-design.md`](../dev/self-documenting-loop-design.md))
executed end-to-end for the first time: orchestrator surfaces cost → Haiku `wiki-scribe`
synthesis → separate Haiku `wiki-grounding-auditor` (author≠auditor) → deterministic
`wiki-lint` → checkpoint advance → this log. (The two model-pinned subagents are not yet
registered in-session — they load on a Claude Code reload — so this run reproduced them as
Haiku-pinned agent invocations against the committed `agents/wiki-scribe.md` /
`agents/wiki-grounding-auditor.md` definitions; the registered path is byte-identical and
verifies on reload.)

**Scope (cost surfaced before spend).** 47 changed sources in window (excl. `docs/wiki/` +
`docs/dev/reviews/`) — the v1.0.7-to-date band: Sprint 7.1 plugin activation, 7.2 governance
extraction, 7.3 design + this branch's loop infra. **Per D5 the wiki references-not-duplicates
the canonical/contract docs** (`AGENTS.md`, `CLAUDE.md`, `vision.md`, `docs/governance/`,
`CONTRIBUTING.md`, `SECURITY.md`, `docs/system-model.md`, …) → almost none map to a page. The
discipline holding is the headline result: **47 changed sources → 1 affected page.** Notably,
the 7.1 commands/agents move (`.claude-plugin/commands/` → `commands/`) drifted only
`docs/system-model.md` (fixed on 7.1) — **no wiki page restated the old location** (the lone
`.claude-plugin` cite, in [`pages/route-surface.md`](pages/route-surface.md), is the unchanged
`route-security-lint.sh` hook).

**Page changed (1).** [`pages/governance-extraction.md`](pages/governance-extraction.md) — it
described the extraction as *"planned… build a separate, later, gated branch"* with **three
open sub-decisions**, but Sprint 7.2 LANDED it. Updated: status → **design settled + build
LANDED at `docs/governance/` (7.2)**; the three sub-decisions → **resolved** (home =
`docs/governance/`; per-doc boundaries codified in `charter.md`'s citation map; `AGENTS.md`
shape = critical-rules-inline-with-pointer, F-gov-05); the governance `RELEASE_ARC §Phase 4.5`
cites **re-anchored → §Phase 4.7** (governance moved there 2026-06-12); added
`charter.md`/`enforcement.md`/`metrics.md` as cited sources. The crux description is preserved.
[`index.md`](index.md) one-liner reconciled ("the planned…" → "LANDED Sprint 7.2"). No
`[[backlink]]` topology change.

**Auditor catch-rate (tuning signal, not a gate).** The independent auditor pass returned
**SUPPORTED 14 / DRIFTED 3 / UNSUPPORTED 0** — it caught **3 fragile bare-line-number cites**
the scribe introduced (`RELEASE_ARC … line 689-690`, `AGENTS.md lines 19-28`, `RELEASE_ARC …
lines 693-694`) and suggested stable section/decision anchors; the orchestrator applied all
three re-anchors (SCHEMA prefers a symbol/anchor over a bare line number). Catch-rate this run
= 3 drift items caught on the 1 audited page; author≠auditor earned its keep on run #1.

**WATCH (surfaced, not auto-edited — human decision).** Two phrasings reference `raw/` as
"introduced by [the] governance-extraction [branch]" ([`pages/llm-wiki-design.md`](pages/llm-wiki-design.md)
line 68 + the `governance-extraction` Related gloss), but 7.2 landed `docs/governance/`
**without** introducing `raw/` (`docs/wiki/raw/` still does not exist; raw/ remains future).
The auditor read these as forward-looking-and-still-true; left as-is for a human call rather
than silently rewritten. Also noted: [`pages/engineering-workstreams.md`](pages/engineering-workstreams.md)
"active — landing across v1.0.6" for WS-4 is now nearly "landed" (minor, pre-existing, §4.5 is
WS-4's correct home). Neither is a release blocker.

**`.last_ingest_sha` advanced `7d8f427` → `a008f86d03e67570272641864378ff846ed6cf46`**
(= HEAD at the loop run; the subsequent wiki-refresh commit touches only `docs/wiki/`, which
the loop excludes, so no drift is introduced).

**Loop invariant held: this run produced a reviewable diff — it did NOT auto-commit.** The
human reviewed the diff and committed it. Lint: PASS (no ERROR) — the changed page's 12
relative links + 5 `[[backlinks]]` all resolve; `index.md` ↔ `pages/` agree; no bare-line
cites remain. Gate: `ruff` ✓ · `mypy` ✓ (162 files) · `pytest` (docs-only — no `.py` touched).

## 2026-06-20 — diff refresh: consolidated v1.0.7 pre-tag (`chore/version-bump-v1.0.7`)

**Mode:** diff (`a008f86…` → `3561657` = the version-bump branch's non-wiki tip). The 52-commit
v1.0.7 feature band (Sprints 7.4–7.8d): the `recall/` Memory substrate, the doc-grounded
assistant / "avatar" (`blueprints/assistant.py`, `static/assistant.js`), the S3 vector tier,
and the citation-format work. **Per D5 the wiki references-not-duplicates** — and the new
subsystems (`recall/`, `blueprints/`, `static/assistant.js`) are cited by **zero** pages, so
they map to no existing page. **Owner-scoped a BOUNDED pre-tag refresh:** the route-surface /
module-map / new-subsystem how-to documentation is deferred to its already-scheduled homes —
**8.6 `/wiki-ingest`** for the post-blueprint-split `app.py` cites + **8.6a
`docs/assistant-wiki-coverage`** for the assistant how-to content — because the 8.3 blueprint
split will move every route and stale any `path:line` cites authored now.

**Pages changed (4)** — all durable, `analyzer.py`/concept-keyed (untouched by the route refactor):
- [`pages/engineering-workstreams.md`](pages/engineering-workstreams.md) +
  [`pages/llm-wiki-design.md`](pages/llm-wiki-design.md) — corrected the now-stale framing of the
  doc-grounded assistant as **"post-v1.1.0"**: it **shipped in v1.0.7** (Sprints 7.5–7.8d;
  `blueprints/assistant.py`, `analyzer.py:avatar_answer_streaming`). The convergence insight is preserved.
- [`pages/llm-call-catalog.md`](pages/llm-call-catalog.md) — added the missing **`avatar_answer`**
  Haiku call kind (the doc-grounded assistant, over a `recall.Context`; `analyzer.py:1611` /
  `:1648-1655`).
- [`pages/prompt-version-discipline.md`](pages/prompt-version-discipline.md) — new section
  documenting **`AVATAR_PROMPT_VERSION`** (`analyzer.py:290`) as the second, separately-bumped
  prompt-version constant.

**Auditor catch-rate (tuning signal, not a gate).** Independent per-page audits (author≠auditor):
3 pages CLEAN (SUPPORTED 3 / 7 / 37); the prompt-version-discipline page returned **needs
attention — 1 UNSUPPORTED**: the scribe claimed the avatar's `avatar_answer` telemetry "carries
`AVATAR_PROMPT_VERSION`", but `effective_prompt_version()` (`analyzer.py:334-346`) stamps
`PROMPT_VERSION` on every funnelled call (`analyzer.py:1072`) with **no** avatar branch. The
orchestrator corrected both that page and the `llm-call-catalog` row to state accurately that
`AVATAR_PROMPT_VERSION` is a **source-level discipline marker, not a telemetry field** (its job
is to record the avatar-prompt revision in source *without* bumping `PROMPT_VERSION`, keeping the
résumé join key stable). Catch-rate this run = **1 UNSUPPORTED caught / 4 audited pages.**

**WATCH (surfaced, not auto-edited — deferred to 8.6 `/wiki-ingest`).** The auditor noted
[`pages/engineering-workstreams.md`](pages/engineering-workstreams.md) line 16 still cites the
pre-PX-10 `6,290-LOC / 75-route` `app.py` size; the current figure is `8,251-LOC / 93-route`
(corrected in CHANGELOG / RELEASE_ARC at v1.0.6). Left as-is: the 8.3 blueprint split changes the
LOC/route counts again, so the durable refresh belongs to the scheduled 8.6 `/wiki-ingest`, not
this bounded pre-tag pass. (The prior run's two WATCH items — the `raw/` phrasing + WS-4
"active→landed" — remain open, same rationale.)

**`.last_ingest_sha` advanced `a008f86d03e67570272641864378ff846ed6cf46` →
`35616579b866568042434f01401d366c477d6fac`** (= the version-bump branch's non-wiki tip — the
ledger/CHANGELOG/version-bump commit plus the flaky-gate-note commit; the subsequent
wiki-refresh commit touches only `docs/wiki/`, which the loop excludes, so `/wiki-lint` stays
clean at the tag).

**`/wiki-lint`: PASS — 0 ERROR, 0 staleness WARN** (`.last_ingest_sha` == non-wiki tip; the 4
changed pages' `[[backlinks]]` + `path:line` cites all resolve; `index.md` ↔ `pages/` agree; the
only `[[backlink]]`/`[[links]]` "dangles" are literal syntax mentions in `SCHEMA.md` / `log.md`).
**Gate:** `ruff` ✓ · `mypy` ✓ (190 files) · `pytest` 1311 passed + the 1 known intermittent
UX-tier flake (`test_positioning_pin_preserves_title_pin`, passes clean isolated — docs-only
branch, not code-caused). **Loop invariant held: reviewable diff, no auto-commit.**

## 2026-06-25 — content pass: assistant how-to coverage (`docs/assistant-wiki-coverage`)

**Mode: hand-authored content pass — NOT a code ingest / diff pass** (Sprint 8.6a). The
second authoring INTO the `audience: user` section (after the 2026-06-14 Sprint-6.5 education
pass), filling the doc-grounded assistant's "woefully uninformed" coverage gap: only the 6
Sprint-6.5 `user`-tier pages existed, and the avatar gates retrieval **strictly by audience**
(`blueprints/assistant.py` `Scope` — a `user`-scoped turn reaches only `audience: user`
pages), so the how-to questions below hit "I don't have that in my docs." Like the 2026-06-09
and 2026-06-14 content passes, this is a *content* pass: it does **not** advance
`.last_ingest_sha` (that checkpoint tracks the last **code** ingest, per [`SCHEMA.md`](SCHEMA.md)
"Source model").

**Pages created (7, `audience: user`):** [`downloading-your-documents`](pages/downloading-your-documents.md),
[`editing-and-refining`](pages/editing-and-refining.md), [`cover-letters`](pages/cover-letters.md),
[`managing-users`](pages/managing-users.md), [`importing-your-experience`](pages/importing-your-experience.md),
[`troubleshooting`](pages/troubleshooting.md), [`using-the-assistant`](pages/using-the-assistant.md)
(the owner-chosen **all-7-topics** scope — dedicated deep-dive pages even for the 3 topics the
wizard/corpus pages already mentioned briefly; those existing pages gained reciprocal
`[[backlinks]]`, not rewrites). Each grounds in the shipped UI (`templates/index.html` ids +
`static/app.js` / `static/assistant.js` functions) and the deterministic/LLM backend
(`blueprints/generation.py`, `blueprints/users.py`, `blueprints/corpus/curation.py`,
`blueprints/assistant.py`, `analyzer.py`, `web_infra/clients.py`, `pdf_render.py`); the
no-fabrication promise defers to [`overview.md`](overview.md) (D5).

**Wiki meta updated.** [`index.md`](index.md) gained the 7 pages under "User-facing education"
(an 8.6a sub-note); `[[backlinks]]` reconciled bidirectionally — the hub
[`using-sartor`](pages/using-sartor.md) "The guides" now lists all 11 guides, and
[`tailoring-a-resume`](pages/tailoring-a-resume.md) Step 6 + [`career-corpus`](pages/career-corpus.md)
"Building it" splice the new how-to backlinks. No `pages/` page carries a per-page source-SHA
marker (`SCHEMA.md` stamps only the audience tag), so only the content changed.

**`.last_ingest_sha` deliberately LEFT at `35616579b866568042434f01401d366c477d6fac`** (the
v1.0.7 pre-tag code checkpoint). The branch changes **no code**, so no dev-tier page drifts;
the consolidated `/wiki-ingest` code-keyed re-anchor (the post-blueprint-split
`app.py`→`blueprints/` route cites) stays the scheduled 8.6 / later pass, not this content
pass.

**Authoring + verification.** Authored with the established pattern (the 2026-06-13 cold
ingest): one author per page, then a **separate** adversarial grounding auditor per page
(author ≠ auditor; the `/wiki-audit` discipline, reproduced as 7 read-only
`wiki-grounding-auditor` agents). **6 pages CLEAN; 1 DRIFTED cite caught + re-anchored** —
[`importing-your-experience`](pages/importing-your-experience.md) cited
`analyzer.extract_experiences`, but the function lives at `onboarding.extract_experiences`
(imported by `blueprints/corpus/curation.py:ingest_resume_to_corpus`); the "deterministic
ingest" wording was also corrected (the ingest delegates a Haiku extraction). The
highest-risk page ([`troubleshooting`](pages/troubleshooting.md)) was bounded to **verified**
failure modes only — Chromium-for-PDF (`pdf_render.py` + [`../install.md`](../install.md)),
the API-key/`.api_key` lookup (`web_infra/clients.py:_get_client`), and the warn-only
date-check note (`blueprints/generation.py:_check_date_grounding`); the unverified
"grounding-abort discards work" idea was **dropped** (the date check is warn-only, never
blocks the generate flow).

**`/wiki-lint`: PASS — 0 ERROR.** 36 `pages/` ↔ `index.md` agree both ways (the 7 new pages
listed); every `[[backlink]]` resolves to an existing slug; no orphans (every new page has an
inbound link from the `using-sartor` hub); `.last_ingest_sha` unchanged (content pass — no
staleness regression). **Gate:** `ruff` ✓ · `mypy` ✓ (228 files); the full UX `pytest` suite
was not re-run for this docs-only branch (owner direction) — no `.py` touched, and
`tests/test_wiki_source.py` is `tmp_path`-only (the real pages don't affect it); the directly
relevant `test_wiki_source` + `test_recall` (28) ran green. Per the
[`../../CHANGELOG.md`](../../CHANGELOG.md) scope rule, this content pass is recorded here (the
wiki's own changelog), not in CHANGELOG.

## 2026-07-10 — diff refresh: the v1.0.9 code-keyed catch-up (`docs/wiki-v109-refresh`)

**Mode: diff** (`3561657` → `e785e53`) — the big deferred **code-keyed** refresh the 2026-06-20
and 2026-06-25 passes parked (both left `.last_ingest_sha` at the v1.0.7 tip precisely so this
branch would pick up the blueprint split). 244 commits / ~341 non-doc source files in window:
the whole **`app.py`→`blueprints/` decomposition** (Sprint 8.3a–h — `app.py` is now a zero-route
factory; the `_safe_username`/`_within` gate + SSE/request helpers moved to the new leaf
[`web_infra/`](../../web_infra/) package; new [`ui_pages/`](../../ui_pages/) POM), the
**compose-frozen-composition** UX re-architecture (deterministic `_frozen_composition` assembly
+ the `draft_*` Compose calls), kit-adoption (mypy `--strict` §6 exit), and packaging.

**Method (parallelized loop).** Six **Sonnet** `wiki-scribe` lanes (worktree-isolated, one per
domain batch), each grounding against source at HEAD `e785e53` — Sonnet, not the default Haiku,
because a 244-commit structural refresh is reasoning-heavy, not a steady-state increment. Per-page
**Haiku** `wiki-grounding-auditor` pass (author≠auditor). **Per D5 the wiki
references-not-duplicates** the canonical/contract docs, so the 341 changed sources map to **29
changed pages** (of 36; `prompt-version-discipline` + 6 others verified CLEAN, no edit). The
dominant re-anchor: every `app.py:<route/helper>` cite → its `blueprints/**` /
`web_infra/security.py` home; route count `93` → **117**.

**Auditor catch-rate (tuning signal, not a gate).** Tooling note: the first audit round used a
`git show`-based prompt the read-only (no-Bash) auditor couldn't run, so it silently read the
**pre-scribe** pages from the main checkout and re-flagged already-fixed drift — invalid. The
pages were integrated onto the review branch and **re-audited against the working tree** (correct
source-of-truth). The valid re-audit over all 29 pages found **5 real drift points**, all
re-anchored centrally: `generator.py:_write_docx` → `_write_docx_from_json_resume`
(document-rendering ×2, code-module-map ×1); `_HELP_SEEN_PREFIX` → `CB_HELP_SEEN_PREFIX`
(frontend-wizard, per `static/help-modal.js`); and a cross-page **"three Compose drafting calls"**
collision (`llm-call-catalog` groups the three `draft_*` calls by explicit Sonnet model;
`generation-and-grounding` means the D5 `prior_clarifications` set — the latter reworded to scope
by that property). The remaining ~24 pages: CLEAN on first synthesis.

**Prior WATCH items closed.** The long-standing `raw/` phrasing (`SCHEMA.md` §"raw/ constitutional
layer" + two pages) is corrected — the Governance-extraction branch **rejected** `raw/` in favor
of `docs/governance/`, so `raw/` stays unbuilt (carried as WATCH since the 2026-06-16 + 2026-06-20
runs). `engineering-workstreams` WS-1 "design-pending" → **SHIPPED**; the stale `6,290-LOC /
75-route` `app.py` figure retired (now the zero-route factory).

**`.last_ingest_sha` advanced `35616579…` → `e785e539df0340f57ba5d5e0d7663b933118b3f1`** (HEAD; the
wiki-refresh commits touch only `docs/wiki/`, which the loop excludes).

**`/wiki-lint`: PASS — 0 ERROR / 0 WARN.** Staleness 0 (checkpoint == code tip); all `[[backlinks]]`
resolve; 36 `pages/` ↔ `index.md` agree both ways; all root-relative `path` cites resolve; no
orphans. **Loop invariant held: reviewable diff, no auto-commit** — the human reviews + commits.
Docs-only branch (no `.py` touched); recorded here (the wiki's changelog), not in CHANGELOG.
## 2026-07-10 — content pass: recruiter Pipeline-tab coverage, closes F-17 (`docs/wiki-content-pass`)

**Mode: hand-authored content pass — NOT a code ingest / diff pass** (v1.0.9 docs epic,
[`../dev/RELEASE_ARC.md`](../dev/RELEASE_ARC.md) §Phase 4.9, branch #3). Closes the
Carry-forward-ledger F-17 gap: `feat/ux-w2-recruiter` (2026-07-07) shipped the recruiter-tier
**Pipeline** tab, but no `audience: user` page described it, so the doc-grounded assistant's
`user`-scoped access plane had nothing to cite and refused Pipeline questions. Like the prior
content passes, `.last_ingest_sha` is **deliberately left unchanged** — no code changed.

**Page created (1, `audience: user`):** [`pages/recruiter-pipeline-tab.md`](pages/recruiter-pipeline-tab.md)
— what the Pipeline board is, who it's for, and how to use it. Grounded against the live app:
`templates/index.html` `#tab-pipeline`/`#pipelineBoard`, `static/app.js`
(`refreshPipeline`/`_renderPipelineBoard`/`_renderPipelineRow`), and the backing
`GET /api/candidates/roster` route (`blueprints/users.py:candidate_roster`). Explicitly
disambiguated from the unrelated `audience: dev` [`pages/pipeline-stages.md`](pages/pipeline-stages.md)
(the internal analyze→clarify→compose→generate→iterate résumé-generation sequence) — a
different "pipeline" entirely; that page was **not** touched.

**Wiki meta updated.** [`index.md`](index.md) gained the new page under a short "Wave 2
recruiter tier" note; `[[backlinks]]` reconciled bidirectionally — [`using-sartor`](pages/using-sartor.md)
"The guides" and [`managing-users`](pages/managing-users.md) "Everyone's data stays separate"
now each link to `recruiter-pipeline-tab`, which links back to both plus
[`tailoring-a-resume`](pages/tailoring-a-resume.md) (which gained a reciprocal pointer too).
[`overview.md`](overview.md) and [`llms.txt`](../../llms.txt) were reviewed and found current —
no edit needed (both describe the system at the wiki/system altitude, not per-feature detail).

**Authoring + verification.** Single-author content pass (no separate grounding-auditor
subagent run this session — every cite was verified directly against the live source files
listed above during authoring, matching the bar the auditor role checks for). `/wiki-lint`-style
manual check: the new page's 3 `[[backlinks]]` all resolve to existing slugs; `index.md` ↔
`pages/` agree; no orphan (inbound link from the `using-sartor` hub). **Gate:** `ruff` ✓ ·
`ruff format --check` ✓ · `mypy` ✓ · `pytest -m "not ux and not slow"` ✓ (docs-only — no `.py`
touched). Per the [`../../CHANGELOG.md`](../../CHANGELOG.md) scope rule this content pass is
recorded here; a CHANGELOG [Unreleased] line was also added (conductor scope directive) since
the branch additionally closes a Carry-forward-ledger row in
[`../dev/RELEASE_CHECKLIST.md`](../dev/RELEASE_CHECKLIST.md).

## 2026-07-10 — diff refresh: v1.0.9 pre-merge bounded catch-up (`chore/wiki-refresh-v109`)

**Mode: BOUNDED diff refresh** (`e785e539` → `c8899fd`) — NOT a full re-ingest. The
pull-in train (docs epic + mypy tooling slice + spectree OpenAPI Layer B) pushed the
`scripts/wiki_freshness.py` drift gate past its threshold; owner directed a genuine
synthesis pass over the new surface, scoped to two items (not the whole 41-file diff,
most of which is canonical living docs the wiki references-not-duplicates per D5, or
the docs/diagrams-a11y + docs-site/Fumadocs work already reconciled by the prior
`docs/wiki-v109-refresh` pass and out of scope here as an L3 projection).

**Scope item 1 — spectree OpenAPI "Layer B."** [`web_infra/openapi.py`](../../web_infra/openapi.py)
(the shared `spec` `SpecTree` instance + `RootModel`/permissive-base response
models, `mode="strict"`), five read-only `GET` routes now carrying
`@spec.validate(resp=..., skip_validation=True)` across
[`blueprints/users.py`](../../blueprints/users.py) (`list_users`, `get_config`),
[`blueprints/corpus/experiences.py`](../../blueprints/corpus/experiences.py)
(`list_experiences`), and [`blueprints/applications.py`](../../blueprints/applications.py)
(`list_applications`, `get_application`); the deterministic generator
[`scripts/generate_openapi_spec.py`](../../scripts/generate_openapi_spec.py); and the
`docs-deploy.yml` CI step wiring it into the Fumadocs build (the Fumadocs render itself,
and everything under `docs-site/`, is an L3 projection — out of wiki scope per
[`SCHEMA.md`](SCHEMA.md)).

**Scope item 2 — mypy `--strict` tooling slice.** `scripts/`, `evals/`, and
`db/migrations/versions/` brought to full `--strict` (72 measured errors fixed,
zero behavior change), narrowing the Decision-7 exempt set to `tests/` only
([`docs/dev/kit-adoption-design.md`](../dev/kit-adoption-design.md) §6 amendment;
[`tests/test_mypy_strict_roster_gate.py`](../../tests/test_mypy_strict_roster_gate.py)
updated in lockstep).

**Pages created (1, `audience: dev`):** [`pages/openapi-api-reference.md`](pages/openapi-api-reference.md)
— no existing page owned this concept (a repo-wide grep for `docs-site|spectree|openapi|fumadocs`
across `docs/wiki/` returned nothing before this pass), so a dedicated page was warranted per
[`SCHEMA.md`](SCHEMA.md)'s "one concept per page" rather than folding a multi-file, CI-spanning
concern into [[route-surface]].

**Pages changed (4, all `audience: dev`).**
- [`pages/route-surface.md`](pages/route-surface.md) — added an "OpenAPI spec emission on
  five GET routes (spectree Layer B)" section naming the five decorated routes and pointing to
  the new page; added a `[[openapi-api-reference]]` backlink.
- [`pages/code-module-map.md`](pages/code-module-map.md) — added `openapi.py` to the
  `web_infra/` leaf-module row + a `[[openapi-api-reference]]` backlink.
- [`pages/engineering-workstreams.md`](pages/engineering-workstreams.md) — WS-2 status:
  the Decision-7 exempt set (previously stated as `tests/`/`evals/`/`scripts/`/
  `db/migrations/versions`) is now **`tests/` only**; recorded the 72-error tooling-slice
  fix and the roster-gate's matching narrowing.
- [`pages/consistency-tracks-enforcement.md`](pages/consistency-tracks-enforcement.md) —
  **Related-section backlink only, no content change** (its content stays pinned to the
  2026-06-07 excellence-walk source per its own grounding note): added
  `[[openapi-api-reference]]` as a reciprocal bidirectional link, since the new page cites
  it as a later instance of the same "consistency tracks enforcement" pattern
  (`mode="strict"` + the 5-path self-check).

**A closer look considered, then declined: `pages/deterministic-llm-boundary.md`.** That
page's scope is explicitly the eight modules AGENTS.md names as the P1 boundary (verified
unchanged by this diff — the only AGENTS.md edit in range retargets a diagram-location
sentence, unrelated). `web_infra/openapi.py` is deterministic by its own docstring but is a
`web_infra/` leaf module, not one of those eight — noted explicitly on the new page instead
of stretching this page's fixed module list `[synthesis]`. The new page links to
`deterministic-llm-boundary` one-way (to state the distinction), deliberately **without** a
reciprocal backlink — adding one there would misrepresent that page's fixed, AGENTS.md-anchored
scope as having grown to include a `web_infra/` module it explicitly does not cover.
The mypy-slice note was also considered for
[`pages/consistency-tracks-enforcement.md`](pages/consistency-tracks-enforcement.md) directly
(beyond the backlink above), but that page's content is pinned to the 2026-06-07
excellence-walk source and its own grounding note says a later audit should re-read that
source, not re-grep live code — WS-2 in `engineering-workstreams.md` (which already tracks
the `--strict` ratchet's live status) is the precise, established home for that fact instead.

**Cite re-anchoring.** None needed on the touched pages: `route-surface.md` and
`code-module-map.md` cite `docs/architecture.md` by section anchor (`§Module map`,
`§"System overview"`), not line number, and those sections were not renumbered;
`engineering-workstreams.md`'s `kit-adoption-design.md` §6 cite is unchanged (the tooling
amendment landed as a new blockquote under the existing §6, not a renumber). No page in
this pass cites `docs/system-model.md`, `docs/dev/memory-architecture.md`, or
`docs/dev/documentation-architecture.md` by line number.

**`.last_ingest_sha` advanced `e785e539df0340f57ba5d5e0d7663b933118b3f1` →
`c8899fdeaf84394cf3b7528b166a58e41731eb9f`** (HEAD at this branch's base — the
spectree-fumadocs-render tip the v1.0.9 pull-in train carries forward).

**Verification.** `python scripts/wiki_freshness.py` → OK (drift now under threshold).
`ruff check .` ✓ · `ruff format --check .` ✓ · `mypy .` ✓ ·
`pytest -m "not ux and not slow"` ✓, including
[`tests/test_wiki_freshness_gate.py`](../../tests/test_wiki_freshness_gate.py) — green now
that the checkpoint is advanced (the one test expected to flip). `index.md` ↔ `pages/`
agree (38 pages); the new page's 4 `[[backlinks]]` and the 3 reciprocal backlinks added on
`route-surface`/`code-module-map`/`consistency-tracks-enforcement` all resolve to existing
slugs; no orphan (inbound links from `route-surface` and `code-module-map`, both
hub-adjacent). Single-author pass, no separate grounding-auditor subagent run this session
— every cite was verified directly against the source files at this branch's HEAD during
authoring; a follow-on grounding audit is expected to run separately per the owner's stated
plan.

---

## 2026-07-13 — `chore/release-governance` — diff pass (`/wiki-self-update`, `--cap 35`)

**Window:** `c8899fd` → `9f3c800` (82 changed sources, excluding `docs/wiki/` and the
review archive). **Mode:** diff.

**Why it was this big.** The freshness gate hit its 75-file block threshold (77) and
failed the `quality` job on PR #20 — a real gate doing its job. The drift was **not**
from the branch that tripped it: the v1.1.0 debt-burn train (7 lanes) merged without a
wiki refresh, so ~10 branches' worth of change accumulated into one pass (`static/app.js`
+419/−145, `static/style.css` +207/−48, `config.py` +98/−29, plus `blueprints/`,
`db/models.py`, `evals/`). The loop is designed to run at **branch close-out**, in small
batches; the lesson recorded here is that skipping the checkpoint, not the cadence, is
what produced a 33-page pass. Owner authorized the spend at `--cap 35`.

**Pages assessed:** 33 (every page citing a changed source, after excluding the
contract/governance docs the wiki references but never duplicates, per D5).
**Pages changed:** 18. **Verified already-current, no edit:** 15 — the scribes were
explicitly permitted to return "no change needed", and did.

**Audit (author ≠ auditor — every changed page audited by a different context):**
18 pages audited, **3 defects caught and fixed by the orchestrator**:
- `frontend-wizard` — **UNSUPPORTED**: claimed the Pipeline tab is opened by its card
  handlers. The cards do the opposite — they switch to **Tailor** on the selected
  candidate's applications (`static/app.js:_renderPipelineRow`). Rewritten.
- `diagnostics-console` — **DRIFTED**: said the run-lock covers "four paid-run buttons";
  `LOCK_BTN_IDS` holds **five** (the collate-fixture button is in the lock too). Corrected.
- `career-corpus` — **DRIFTED**: a bare line-range cite (`static/app.js:3960–3966`) pointed
  at the fetch handler, not the render. Re-anchored to the symbol
  (`_renderDeniedSkillRow`), which is what SCHEMA asks for anyway.

**Auditor catch-rate:** 3 / 18 changed pages (17%). One of the three was a genuine
false claim about behavior, not a stale pointer — the case where author≠auditor pays.

**Deterministic gate:** 0 broken source links, 0 unresolved `[[backlinks]]`, all changed
pages present in `index.md`.

**Checkpoint:** `.last_ingest_sha` advanced `c8899fd` → `9f3c800`.

---

## 2026-07-18 — `refactor/css-cascade-collapse` — diff pass (`/wiki-self-update`, default `--cap 8`)

**Window:** `9f3c800` → `248703b` (76 changed sources, excluding `docs/wiki/` and the
review archive). **Mode:** diff.

**Why it ran, and why the pass was tiny anyway.** The freshness gate hit its 75-file
block threshold (76) and would have blocked this branch's merge. As in the `9f3c800`
pass before it, the drift was **not** from the branch that tripped it — the count went
70 → 76 during the *previous* branch's merge (`542ef02` → `248703b`), before this branch
existed; this branch's own diff is one CSS file. But unlike that pass, the scope
resolved to **one page**, because the file *count* and the wiki *work* turned out to be
almost unrelated here.

**Scope was measured deterministically before spending, not estimated.** A pure
git+regex pass extracted every `path:symbol` / `path:line` cite in the wiki and checked
it against the diff: **316 cites across 38 pages, 86 of them resolving into a changed
file, and all 86 still valid at HEAD** — i.e. **zero cite drift**. The single unit of
real work was a *coverage gap*, not a stale pointer: `hardening.py:write_context_atomic`
and `hardening.py:context_transaction` both existed in code and appeared in **zero**
pages, on a page (`context-set-contract`) whose own subject is that contract.

**Calibration observation (worth carrying).** Of the 76 counted files, the bulk are
handoffs, diagnosis dossiers, and `docs/dev/ledger/*.jsonl` — artifacts D5 says the wiki
must never duplicate, so they are structurally incapable of producing wiki work. The
gate therefore fired on volume while actual staleness was nil. This is a concrete data
point for the already-tracked "wiki gate is mis-tuned (cheap-vague detect, expensive-blind
correct)" concern: a threshold counting files that can never cause drift will keep
firing on process-doc churn. Excluding `docs/dev/handoffs/`, `docs/dev/diagnosis/`, and
`docs/dev/ledger/` from the count would be the obvious first tuning — **not done here**
(changing an enforcement threshold is its own decision, not a side effect of a wiki pass).

**Pages assessed:** 38 scanned by cite-check; 1 affected. **Pages changed:** 1 —
`context-set-contract` (new paragraph in "Persistence and the iteration chain": atomic
writes closing torn reads, and the `context_transaction` read-modify-write closing lost
updates, with the LLM call held outside the lock). `consistency-tracks-enforcement` was
**deliberately not** updated for the new C-7/C-8/C-9 enforcement hooks — it is a thesis
page, and the hook inventory is canonical in `AGENTS.md`/`CLAUDE.md`/`docs/governance/`
(D5, referenced not duplicated); flagged to the owner rather than silently decided.

**Audit (author ≠ auditor):** 1 page audited, 10 claims verified against `hardening.py`
at HEAD. **0 DRIFTED, 0 UNSUPPORTED** — every cite and behavioral claim quote-matched to
source. **1 metadata defect caught and fixed by the orchestrator:** the lone `[synthesis]`
tag sat on a claim that is stated almost verbatim in the `context_transaction` docstring
(`hardening.py:1524-1525`), so the tag was removed — the auditor's finding was itself
re-verified against source before acting, since removing a tag is the riskier direction
of error (it would present an inference as grounded).

**Auditor catch-rate:** **0 / 1** by the logged definition (DRIFTED + UNSUPPORTED per page
audited) — the one catch was a tagging error, which that metric does not count. Recorded
honestly rather than inflated to 1/1: a scribe that grounds every claim correctly and
only over-tags is the *good* failure mode.

**Deterministic gate:** 0 ERRORs — 38/38 pages present in `index.md`, all `[[backlinks]]`
resolve, all relative links resolve, 0 orphans.

**Checkpoint:** `.last_ingest_sha` advanced `9f3c800` → `248703b`.
