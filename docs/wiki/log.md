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
[`../diagrams/`](../diagrams/) `*.mmd`.

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
[`../diagrams/pipeline.mmd`](../diagrams/pipeline.mmd) + the embedded copy in
[`../architecture.md`](../architecture.md) "GET INTERVIEW QUESTIONS" → "GET CLARIFYING
QUESTIONS" (the Step-6 iterate flow was already correct);
[`../diagrams/data-flow.mmd`](../diagrams/data-flow.mmd) cover-letter node brought up to
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

**Pages created (5, `audience: user`):** `using-callback` (the first-run hub),
`tailoring-a-resume`, `career-corpus`, `resume-templates`, `candidate-memory`. Each mirrors
the in-app `_HELP_REGISTRY` copy (`static/app.js`) and the wizard surfaces in
`templates/index.html`; plain-language, no technical background assumed.

**Wiki meta updated.** [`index.md`](index.md) gained a "User-facing education" section and
its "Reserved / planned" note flipped from *reserved* to *authored*; [`SCHEMA.md`](SCHEMA.md)
"Audience tag" + "Status" updated (the `user`-tier set is now [`overview.md`](overview.md) +
these five); [`overview.md`](overview.md) gained a one-line "new here?" pointer to
`using-callback`. `[[backlinks]]` reconciled bidirectionally among the five (hub ↔ guides).

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
education guides ([`using-callback`](pages/using-callback.md), …) were already authored in the
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
