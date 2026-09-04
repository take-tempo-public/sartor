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

## 2026-07-20 — `feat/diagnostics-run-cancel` — diff pass (`/wiki-self-update`, default `--cap 8`)

**Mode: diff pass**, `248703b` → `b87ab19` — 77 files changed, spanning several merged
branches accumulated since the last ingest (`chore/scrub-local-eval-paths`,
`chore/config-drift-batch`, `chore/hook-dispatcher`, `fix/context-write-lost-update-gap`,
and this branch's own run-cancel work), not just this branch. Triggered by the CI
`test_this_repos_wiki_is_fresh_enough_to_merge` gate crossing the 75-file block
threshold on PR #35.

**Scope triage (before spending):** a naive file-level scan (any page citing any changed
file) surfaced ~20 candidate pages — well over the default cap. A precision pass (reading
each candidate page's actual claim against the real diff content, not just filename
overlap) narrowed this to **4 genuinely affected pages**, well under cap; no `--cap` raise
needed. 16 candidates were checked and ruled out — files that changed for reasons
unrelated to what the citing page actually claims (e.g. `db/models.py`'s only change was
removing a stray absolute local-machine path from a comment; `static/style.css`'s 128-line
net deletion was PX-51's duplicate-selector cascade collapse, zero hits on the specific
classes `frontend-wizard` cites; `route-surface.md` was already current on the
hook-dispatcher migration).

**Pages changed (4):**
- `diagnostics-console` — new "Run cancellation (disconnect-as-cancel)" subsection: the
  `_HEARTBEAT_INTERVAL_S` timeout-poll + `GeneratorExit` mechanism across all 4 SSE
  routes, the per-request `cancel_check` threading, and why it's disconnect-based rather
  than a literal second route (single-threaded `app.run()`). The page previously covered
  these same 4 routes and the run-lock in detail but said nothing about cancellation — a
  real coverage gap, not just drift.
- `iteration-audit-chain` — corrected a now-false claim: `save_edits` no longer "rewrites
  that same file in place," it applies a delta via `context_transaction` (the
  `fix/context-write-lost-update-gap` rewrite, landed before this branch).
- `eval-harness` — documented the new `cancel_check` param on `run_suite` and
  `run_pipeline_over_jd_texts`, parallel to the existing `progress` param coverage.
- `context-set-contract` — `context_transaction`'s site count widened from 12 to 17 (5
  more sites converted); cited both diagnosis dossiers as evidence.

**16-page citation-drift check (explicitly requested):** re-verified whether any of the
16 ruled-out pages' citations had merely drifted in line number even though content was
unaffected. First pass over-reported drift (~30 apparent hits) — a grep bug misread its
own `-n` line-number prefix as a cited target line. Re-run with a pattern matching only
genuine `path:N` citations in the source text found exactly 2 real numeric citations in
the whole 16-page set (`pyproject.toml:81`, `:92` in `non-dependency-downloads.md`), both
confirmed still accurate (the `pyproject.toml` edit was a same-line comment fix, no
line-count shift). Every other citation across these 16 pages links at file/symbol
granularity, which cannot drift from an unrelated line moving. **Net: zero drift, zero
edits needed** on the 16 — confirmed, not assumed.

**Audit (author ≠ auditor):** all 4 changed pages reviewed by a second pass against
source at HEAD before being accepted; no fabrication beyond the named source files found.

**Deterministic gate:** 0 ERRORs — 38/38 pages present in `index.md`, all `[[backlinks]]`
resolve, all 85 unique cited repo paths exist, 0 orphans.

**Checkpoint:** `.last_ingest_sha` advanced `248703b` → `b87ab19`.

## 2026-07-24 — diff pass, `feat/context-structure-review-skill` (clears the 75-file
staleness threshold)

**Mode: diff pass**, `b87ab19` → `c79b916` (78 files changed — the gate's block
threshold is 75; this branch's own commit was what tipped the count over). Scoped down
from an initially-requested full cold pass after flagging the cost/scope tradeoff: with
38 existing pages already covering most of the codebase, a true whole-repo re-verify
was materially more expensive than what clearing the threshold required.

**File-list triage:** of the 78 changed files, the large majority were non-wiki
artifacts — 17 `docs/dev/ledger/*.jsonl` provenance records, ~17 `docs/dev/handoffs/*.md`
session handoffs, CI/workflow + dependency-bump config, and dev-process docs
(`RELEASE_ARC.md`, `RELEASE_CHECKLIST.md`, `kit-adoption-design.md`, `COMPOSE_REWRITE_DIAL.md`)
that the wiki doesn't track as concept pages. Four pages (`context-set-contract.md`,
`diagnostics-console.md`, `eval-harness.md`, `iteration-audit-chain.md`) were already
hand-updated in-diff by the branches that touched their underlying code (the
"`.last_ingest_sha` unchanged" convention this log already documents elsewhere) — trusted
as current, not re-verified from scratch.

**Real candidates checked, diffed against current wiki content:**
- `blueprints/diagnostics.py` (6-line diff, `%s`→`%r` log format only) — no drift, no
  edit.
- `static/app.js` / `static/style.css` (comment additions explaining already-documented
  race-free/cascade behavior, plus a CSS specificity fix) — matches existing
  understanding, no drift, no edit.
- `scripts/capture_screenshots.py` (new `--smoke` flag, 60-line diff) — dev-tooling, no
  existing or warranted dedicated page under this wiki's scope conventions.
- `docs/governance/charter.md` (98-line addition) + `docs/governance/enforcement.md`
  (small diff) — **real gap found**: the charter grew C-7…C-9, the full "Working model
  (W-1/W-2)" section, and a formal Amendment ceremony since the last ingest, none of
  which [[governance-extraction]] reflected.

**Page updated:**
- `governance-extraction` — added a "Working model (W-1/W-2) + amendment ceremony"
  section summarizing the landing (referencing `charter.md`, not restating its clauses,
  per this page's own D5 grounding rule) and the F-gov-03 citation-gap resolution
  `enforcement.md` records. Backlink to [[engineering-workstreams]] already existed
  bidirectionally — no new backlink wiring needed.

**No pages added** — this pass found one real content gap on an existing page, not new
concept territory.

**Checkpoint:** `.last_ingest_sha` advanced `b87ab19` → `c79b916`.

## 2026-07-24 — `/wiki-lint` (pre-merge gate, `feat/context-structure-review-skill`)

**Staleness:** 0 files changed since `.last_ingest_sha` — no ingest debt.

**Structural integrity:** 38/38 pages present in `index.md` (0 missing either
direction) · 0 dangling `[[backlinks]]` · 0 orphan pages (every page has at least one
inbound link) · 324 `path:line`/`path:SYMBOL` cites checked across 43 unique cited
paths, 0 broken (all resolve once checked against their actual subdirectory —
`static/`, `dashboard/templates/`, etc. — rather than assumed repo-root).

**Coverage gaps:** none newly identified this pass; scope was the diff-pass ingest
above, not a fresh full-repo coverage sweep.

**ERROR count: 0. WARN count: 0. Gate verdict: PASS.**

## 2026-07-27 — `/wiki-self-update` (diff pass, `test/fixture-scoping-rollout`)

**Mode: diff**, `c79b916` → `00c109a`. Triggered by the repo's own wiki-freshness
merge gate: this branch's 46-file PX-44 test-fixture-scoping rollout pushed the
cumulative changed-file count from 38 (on `main`, passing) to 83, past the 75-file
block threshold — not itself a content-drift finding, but the trigger for this pass.

**Sources read** (`git diff --name-status c79b916 HEAD`, excluding `docs/wiki/` and
`docs/dev/reviews/`): 83 files. The overwhelming majority (46 `tests/*.py` +
`tests/conftest.py`) are this branch's own DX-only test-fixture-mechanism changes,
covered by no wiki page and introducing no user-facing or architectural concept —
correctly out of scope per the wiki's own D5 rule (canonical/internal-mechanism docs
are referenced, not restated). Of the remainder, real product-code changes worth
checking against existing citations: `blueprints/corpus/curation.py` (merge-suggestions
pagination, ledger item 11), `onboarding/experience_match.py` (company-gate
short-circuit perf fix, ledger item 10), `static/app.js`/`static/style.css` (the same
merge-suggestions render-cap UI + a scroll-anchoring CSS fix, ledger item 2 round 7),
`scripts/bench_corpus_scale.py` (new dev-only benchmark script), `docs-site/source.config.ts`
(badge-fetch build-flake fix, ledger item 8).

**Affected-page determination:** checked each candidate against the pages that cite
its file (`career-corpus`, `corpus-data-model`, `importing-your-experience`,
`frontend-wizard`). None cite the SPECIFIC changed lines/functions at `path:line`
granularity — `importing-your-experience.md`'s merge-suggestions description is
prose-level UX behavior ("shows you a Possible duplicate roles section"), unaffected
by the added pagination params (an internal >1000-match scale fix, not a UX change);
the other three pages cite the changed files generically for unrelated sections.
`onboarding/experience_match.py` has zero existing wiki citations — an internal
scoring-algorithm optimization, not a new page-worthy concept.

**0 affected pages — no scribe/auditor spend.** Confirmed via `/wiki-lint`
(re-run this pass, see next entry) that this conclusion doesn't mask an existing
drift: 0 dangling backlinks, 0 broken `path:line` cites, 0 orphans, index/pages
agree exactly (38/38).

**No pages added or changed.**

**Checkpoint:** `.last_ingest_sha` advanced `c79b916` → `00c109a`.

## 2026-07-27 — `/wiki-lint` (pre-merge gate, `test/fixture-scoping-rollout`)

**Staleness:** 0 files changed since `.last_ingest_sha` (post-advance, this pass).

**Structural integrity:** 38/38 pages present in `index.md` (0 missing either
direction) · 0 dangling `[[backlinks]]` · 0 orphan pages (every page has at least one
inbound link) · all `path:line` cites (numeric-suffixed citations only, script-checked)
resolve to existing files.

**Coverage gaps:** none newly identified this pass; scope was the diff-pass ingest
above, not a fresh full-repo coverage sweep.

**ERROR count: 0. WARN count: 0. Gate verdict: PASS.**

---

## 2026-07-30 — /wiki-self-update (diff pass, `00c109a7…` → `65b0f88`)

**Branch:** `fix/ux-restore-scroll-y-resource-contention` (close-out checkpoint trigger — the
75-file freshness gate blocked the merge). **Window:** 75 changed source files across 5 merged
branches + this branch; owner authorized a one-run cap raise to 18 (affected-page union 15).

**Sources driving page work:** `static/app.js` (`_navGen` navigation guard, `switchTopTab`
smooth-scroll cancel, `wizardInit`/`_wizardRender` opts — item 29), `scripts/gate.py`
(`-n auto` non-UX tier, `work_items check` step), `dashboard/routes.py` (`judge_error`
exclusion), `blueprints/diagnostics.py` (run-cancel heartbeat), NEW `scripts/work_items.py`.

**Pages changed (3):** `frontend-wizard` (stale-landing guard + scroll-cancel subsection,
`{scroll:false}` opts; cites re-anchored), `code-module-map` (`gate.py` step list updated;
new `scripts/work_items.py` entry citing `docs/dev/work/SCHEMA.md` per D5),
`diagnostics-console` (SSE cancel line re-anchors; `judge_error` exclusion detail).
**Pages verified no-edit (12):** `using-sartor`, `route-surface`, `pipeline-stages`,
`tailoring-a-resume`, `career-corpus`, `managing-users`, `troubleshooting`, `cover-letters`,
`downloading-your-documents`, `editing-and-refining`, `importing-your-experience`,
`recruiter-pipeline-tab` — symbol-anchored cites or out-of-scope claims. No new page for the
work-item system (SCHEMA.md is authoritative; cite-don't-restate).

**Auditor catch-rate:** 1 catch / 3 pages audited (a `work_items.py:board` anchor naming a
subcommand, not a symbol — re-anchored to `render_board`). Orchestrator lint additionally
caught 6 cite-form errors (line numbers in link targets) in `frontend-wizard`, fixed
mechanically.

**/wiki-lint: ERROR 0 / WARN 0. Gate verdict: PASS.** Checkpoint advanced to `65b0f88`.

---

## 2026-08-04 — scoped close-out relevance check (`chore/v11-march-kickoff`)

**Branch:** `chore/v11-march-kickoff` (per-branch close-out check, AGENTS.md wiki-relevance
step). **Branch diff:** 17 files; one classifies wiki-relevant (`docs/dev/RELEASE_ARC.md` —
additive: new §"v1.1.0 Final March" + a Phase-5 update note; no existing section edited).

**Pages verified no-edit (6):** `engineering-workstreams`, `excellence-walk`,
`governance-extraction`, plus `index.md`/`log.md`/`SCHEMA.md` pointers — every RELEASE_ARC
cite anchors to §Phase 4.5/4.7/4.8/4.9 or the post-public 1.1.x section, none of which this
branch's additive edit touched. No page edit needed; checked, not skipped.

---

## 2026-08-04 — scoped close-out relevance check (`feat/consumer-enumeration-gate`)

**Trigger:** branch close-out, scoped to this branch's own diff (not a full ingest).

**Wiki-relevant paths in this diff** (per `scripts/wiki_relevance.py`): `AGENTS.md`,
`CLAUDE.md`, `docs/governance/charter.md`, `docs/governance/enforcement.md`,
`docs/dev/AGENT_HANDOFF_TEMPLATE.md`. Everything else this branch touches classifies
irrelevant — `scripts/` (mixed, none of the new files are in `RELEVANT_OVERRIDES`),
`tests/`, `hooks/`, `docs/dev/work/`, `CHANGELOG.md`, and the new
`docs/dev/blast-radius/` prefix this branch adds to `IRRELEVANT_PREFIXES`.

**Page edited (1):** `governance-extraction` — its §"Working model (W-1/W-2) + amendment
ceremony" named the charter's clause tail as **C-7…C-9**, which this branch's C-10
amendment drifts. Updated to C-7…C-10 with the new clause's one-line gloss. The page's
own grounding rule (clauses are not restated here; `charter.md` is the durable home) is
preserved — the edit is to the enumeration, not to the clause text.

**Pages verified no-edit:** the remaining 18 pages matching `AGENTS.md`/`CLAUDE.md`/
governance cites reference them for the deterministic-LLM boundary, PROMPT_VERSION
discipline, route surface, and module map — none of which this branch touches. C-10 adds
a clause and a guard; it changes no product behavior, no route, no prompt, and no module
boundary. Checked, not skipped.

---

## 2026-08-04 — scoped close-out relevance check (`fix/ux-scroll-spy-overlapping-refresh`)

**Trigger:** branch close-out, scoped to this branch's own diff (not a full ingest).

**Wiki-relevant paths in this diff (per `scripts/wiki_relevance.py`): none.** Every path
this branch touches classifies irrelevant — `tests/` (the only code change; the fix is in
the UX regression harness), `docs/dev/diagnosis/`, `docs/dev/work/`, `docs/dev/ledger/`,
and `CHANGELOG.md`. Classifier run over the full committed + working diff, not eyeballed.

**Pages edited (0). Pages verified no-edit:** no page needed inspection, because the
classifier surfaced no relevant source. The branch changes no product behavior, no route,
no prompt, no module boundary, and no governance clause — `static/app.js` is untouched and
the defect was in the test harness, not the app. Checked, not skipped.

---

## 2026-08-05 — scoped close-out relevance check (`feat/ci-wait-wrapper`)

**Trigger:** branch close-out, scoped to this branch's own diff (not a full ingest).

**Wiki-relevant paths in this diff (per `scripts/wiki_relevance.py`): 2** —
[`../../AGENTS.md`](../../AGENTS.md) and
[`../dev/AGENT_HANDOFF_TEMPLATE.md`](../dev/AGENT_HANDOFF_TEMPLATE.md). Classifier run over
the branch's committed diff, not eyeballed. (`scripts/ci_wait.py`, `tests/test_ci_wait.py`,
`CHANGELOG.md`, `docs/dev/blast-radius/`, and `docs/dev/ledger/` all classify irrelevant.)

**Pages edited (1):** [`pages/code-module-map.md`](pages/code-module-map.md) — added
`scripts/ci_wait.py` to the "Build and tooling infrastructure" table. It is a genuine
sibling of the `scripts/gate.py` row already there: gate.py is the single definition of
"gate green", ci_wait.py the single definition of "the PR is green", and the map would
have been silently incomplete without it. The trailing `[synthesis]` sentence gained a
clause distinguishing it from the CI-invoked scripts — it *reads* CI rather than running
inside it.

**Pages verified no-edit (2):**
[`pages/llm-wiki-design.md`](pages/llm-wiki-design.md) mentions branch close-out only as
the wiki loop's own trigger, which is unchanged; the wiki [`SCHEMA.md`](SCHEMA.md) match
is its own schema prose, not a claim about close-out. Both inspected, not assumed.

**Not a governance change.** Charter clauses are untouched — C-7 rule 3 is *applied* by
the new wrapper, not amended, so no `[[charter]]`-bearing page needed a revision.

---

## 2026-08-05 — scoped close-out relevance check (`feat/enforcement-first-governance`)

**Trigger:** branch close-out, scoped to this branch's own diff (not a full ingest).

**Wiki-relevant paths in this diff (per `scripts/wiki_relevance.py`): 4** —
[`../../AGENTS.md`](../../AGENTS.md), [`../governance/charter.md`](../governance/charter.md),
[`../dev/AGENT_HANDOFF_TEMPLATE.md`](../dev/AGENT_HANDOFF_TEMPLATE.md), and
[`../dev/work/SCHEMA.md`](../dev/work/SCHEMA.md). Classifier run over the branch's committed
diff (16 files), not eyeballed.

**Pages edited (2), both because this branch FALSIFIED a claim they carried:**

1. [`pages/governance-extraction.md`](pages/governance-extraction.md) — said the charter
   "now carries **C-7…C-10**". It carries C-7…C-12 as of this branch. Corrected, and the two
   new clause names added to the parenthetical. The page's own grounding rule (do not restate
   clauses here; the charter is the durable home) is respected — only the range and the names
   changed.
2. [`pages/code-module-map.md`](pages/code-module-map.md) — the `scripts/work_items.py` row
   described a validator and board generator. It now also carries the **C-11 closure bar**,
   which is a materially different role: it is the one C-11/C-12 mechanism that binds *every*
   agent, because it runs in `gate.py` and CI rather than as a Claude Code hook. Anchor
   updated to `_CLOSURE_BAR_GRANDFATHERED` so the cite points at the new behaviour.

**Pages verified no-edit:** [`pages/llm-wiki-design.md`](pages/llm-wiki-design.md) (its
close-out mention is about the wiki loop's own trigger, unchanged);
[`pages/deterministic-llm-boundary.md`](pages/deterministic-llm-boundary.md) and
[`pages/prompt-version-discipline.md`](pages/prompt-version-discipline.md) (cite C-6 and the
`PROMPT_VERSION` rule respectively — neither touched). Inspected, not assumed.

**This IS a governance change**, unlike the previous two close-out checks — which is exactly
why two pages needed correcting rather than none.

---

## 2026-08-07 — scoped `/wiki-self-update --since 55f7c1e` (`docs/wiki-enforcement-catchup`)

**Trigger:** the chain's own handoff (`docs/dev/handoffs/fix-chain-gate-integration.md`
"Post-chain addendum") directed a scoped run against the chain's own diff, not the full
`.last_ingest_sha`→HEAD window — the chain PR (#105) merged as `c15d080`, a merge commit
whose **first** parent (`55f7c1e`, PR #104) is the true pre-chain `main` tip; its second
parent (`f67943c`) is the chain branch's own tip, easily mistaken for the base in the
opposite order. `--since 55f7c1e` isolates exactly the chain's landed diff.

**Wiki-relevant paths in this diff (per `scripts/wiki_relevance.py`): 2** —
[`../../CLAUDE.md`](../../CLAUDE.md) and
[`../governance/enforcement.md`](../governance/enforcement.md). Classifier run over the
full `55f7c1e..HEAD` diff (32 changed paths); the guard/dispatcher source itself
(`hooks/bash-dispatcher.sh`, `scripts/enforcement/guards/verify_binary_on_path.py`,
`scripts/enforcement/adapters/bash_dispatcher.py`) classifies irrelevant — `hooks/` and
most of `scripts/` are wholesale agent-tooling, not product surface — confirming rather
than contradicting the handoff's own claim, which named the *concepts* (the
`verify-binary-on-path` guard, the Bash-dispatcher fold, the `enforcement.md` reach
declaration) rather than the source files carrying them.

**Pages edited (0). Pages verified no-edit:** grepped every `docs/wiki/pages/*.md` for
`verify-binary-on-path` / `verify_binary_on_path` / `bash-dispatcher` / `bash_dispatcher` /
`claude_hook` / `PreToolUse` / `adapters/` — no page cites any of it, so nothing to
re-anchor. Per D5, changes to `CLAUDE.md` / `docs/governance/` usually map to no page; this
diff is Claude-Code-hook-wiring detail (agent tooling), the same category
`scripts/wiki_relevance.py` already excludes `hooks/` and `scripts/enforcement/` from
wholesale — not a new product concept the wiki curates (contrast
[[route-surface]], which cites `edit-write-dispatcher.sh` because that fold is load-bearing
for *why the security gate is uniform*, a product-security claim, not a hooks-mechanics
one). No scribe/auditor spend — $0.

**`.last_ingest_sha` deliberately NOT advanced** (stays `65b0f88f5c2469484a3ed2ad8edbe28991f56df1`,
2026-07-30) — declared, not silently left, per C-12. This run only diffed
`55f7c1e..HEAD` (the chain's own slice); the checkpoint already lagged 93 commits behind
`55f7c1e` before this branch started, covered piecemeal by several branches' own
lightweight "scoped close-out relevance check" log entries above (which inspect a
branch's own diff and log the verdict but do not move the formal checkpoint — a second,
lighter mechanism alongside this full loop). Advancing the checkpoint to HEAD here would
misrepresent that gap as checked when only its final 2-file slice was. Current drift,
verified: `python -m scripts.wiki_freshness` → **20 file(s) changed since the last ingest
(< 75-file block threshold)** — matches the handoff's own "20/75 at chain close" figure
exactly (this branch's own commits added no further wiki-relevant paths). Safe to leave
for the next bounded catch-up pass; not a merge blocker for this branch.

## 2026-08-08 — scoped close-out relevance check (`docs/epic-a-chain-design-corrections`)

**Wiki-relevant paths in this diff (per `scripts/wiki_relevance.py`): 1** —
[`../dev/RELEASE_ARC.md`](../dev/RELEASE_ARC.md).

**Corrected mid-branch twice (originally recorded as 2 paths / drift 22, then 1 / 21).**
Both figures were *reasoned*, not measured; the measured value is **drift 20/75,
unchanged by this branch**, because `docs/dev/RELEASE_ARC.md` was **already** in the
drift set from earlier branches (verified: `git diff --name-only 65b0f88 HEAD` piped
through `is_wiki_relevant()` → 20 paths, RELEASE_ARC.md among them). This branch
therefore adds **zero** new wiki-relevant paths. Recording the arithmetic slip rather
than just the right number: predicting a drift count instead of running the classifier
is the same C-12 failure mode as any other unsourced assertion.

The first version of this
entry counted the new `docs/dev/epic-a-chain-design-corrections.md` as relevant. It is
not: `tests/test_wiki_relevance_classification.py::test_every_top_level_entry_is_classified`
failed closed on CI (PR #115, run 31267919219, all three quality jobs) because that file
was a **new, unclassified** `docs/dev/` top-level entry. It has now been classified into
`IRRELEVANT_FILES` — a dev-process errata record, the same character as the
already-listed `docs/dev/gate-window-class-study.md` and the wholesale-excluded
`docs/dev/diagnosis/`. Consumer enumeration for that gated edit:
[`../dev/blast-radius/epic-a-chain-design-corrections.md`](../dev/blast-radius/epic-a-chain-design-corrections.md).
The superseded figures are left visible here rather than silently overwritten.

The other changed paths classify irrelevant and are accounted for, not overlooked:
`docs/dev/work/items/0056-*.md` / `0057-*.md` and `docs/dev/work/BOARD.md` (per-item
filings + the file generated from them), `docs/dev/ledger/*.jsonl` (provenance record),
`docs/dev/blast-radius/` and the handoff (process records).

**Pages edited (0). Pages verified no-edit:** grepped every `docs/wiki/pages/*.md` for
`Epic A` / `one sprint` / `stacked` / `plan-approval` / `integration branch`. Exactly one
hit — [`pages/governance-extraction.md`](pages/governance-extraction.md) line 107 — and it
cites **`charter.md`'s W-1**, not the `RELEASE_ARC.md` cadence bullet this branch amended.
That distinction is load-bearing rather than convenient: the amendment is explicitly scoped
to Epic A as a bounded experiment and explicitly **not** a reversal of W-1's serial-default
posture, so the claim that page makes ("the operative default is still serial") remains
true at HEAD and needs no re-anchoring. The new corrections doc is errata for a specific
epic's execution method — the same process-record category `wiki_relevance.py` already
excludes wholesale for `docs/dev/diagnosis/` and `docs/dev/handoffs/`; it defaults relevant
only because it sits at `docs/dev/*.md` top level. No scribe/auditor spend — $0.

**`.last_ingest_sha` deliberately NOT advanced** — declared, not silently left, per C-12.
The checkpoint remains `65b0f88f5c2469484a3ed2ad8edbe28991f56df1` (2026-07-30) and still
lags the same 93+ commits the entry above documents; this branch inspected only its own
two-path slice and advancing the checkpoint would misrepresent that backlog as checked.
Drift after this branch: **20 wiki-relevant files against the 75-file block threshold** —
unchanged from the entry above, per the measurement in this entry's own correction note.
Not a merge blocker; the backlog stays queued for the next bounded catch-up pass.

## 2026-08-08 — scoped close-out relevance check (`feat/corpus-polish`)

Epic A sprint A1a — a presentational reorder of the Career corpus panel plus two row-density
changes. Three of this branch's changed paths classify **wiki-relevant** via
`scripts/wiki_relevance.py`: `templates/index.html`, `static/app.js`, `static/style.css`.
The rest classify irrelevant and are accounted for, not overlooked:
`docs/dev/work/items/0058-*.md` / `0059-*.md` and `docs/dev/work/BOARD.md` (per-item filings
plus the file generated from them), and `docs/dev/ledger/*.jsonl` (provenance records).

**Pages edited (0). Pages verified no-edit:** grepped every `docs/wiki/pages/*.md` for
`panelCorpus` / `corpus panel` / `section order` / `skillsEditorSection` / `Summary variants`.
Two hits, both in a **Grounding:** header rather than in body prose —
[`pages/career-corpus.md`](pages/career-corpus.md) line 6 and
[`pages/importing-your-experience.md`](pages/importing-your-experience.md) line 7. Both cite
by **ID selector** (`#panelCorpus`, `#educationEditorSection`, `#certificationsEditorSection`,
`#corpusIngestFile`), not by line number, and every one of those IDs still exists, unrenamed,
in the reordered markup — verified by an ID-set diff across the whole panel, which came back
identical at 34 IDs before and after.

The distinction that makes this a no-edit rather than a convenient skip: **neither page
documents the section *order*.** They describe what the corpus is and how it fills up. A
reader following either page finds every element it names, in a panel whose sequence it never
asserted. Had either page said "Skills sits above Education," this would have been a required
edit. No scribe/auditor spend — $0.

**`.last_ingest_sha` deliberately NOT advanced** — declared, not silently left, per C-12. The
checkpoint remains `65b0f88f5c2469484a3ed2ad8edbe28991f56df1` (2026-07-30) and still lags the
backlog the entries above document; this branch inspected only its own three-path slice.
Drift after this branch: **22 wiki-relevant files against the 75-file block threshold**, up 2
from the 20 above. Measured, not reasoned: of this branch's three relevant paths,
`static/app.js` was **already** in the drift set from earlier branches, while
`templates/index.html` and `static/style.css` are new to it. Not a merge blocker; the backlog
stays queued for the next bounded catch-up pass.

---

## 2026-08-08 — `fix/experience-soft-retire` (Epic A, sprint A1b) — scoped diff pass

**Mode:** diff, window `7c15c2e` → working tree (this branch's own slice only, per the
close-out per-branch rule). **Not** the `.last_ingest_sha` window.

**Sources read:** the branch's 17 wiki-relevant paths — the `Experience.is_active`
soft-retire column (`db/models.py`, `db/migrations/versions/0016_experience_is_active.py`),
its consumer filters (`db/build_context.py`, `corpus_to_json_resume.py`,
`blueprints/corpus/{experiences,_shared,curation,skills}.py`, `blueprints/applications.py`,
`onboarding/{corpus_import,review_cli}.py`, `evals/seed_import.py`,
`scripts/export_corpus_seed.py`, `web_infra/openapi.py`) and the UI
(`static/app.js`, `static/style.css`).

**Pages changed (7, none created):** `corpus-data-model` (the load-bearing one — a fourth
carrier of the `is_active` pattern, chain head `0015`→`0016`), `corpus-to-output-reach`
(the two generation chokepoints), `route-surface` (three changed route contracts),
`career-corpus`, `frontend-wizard`, `importing-your-experience`, `openapi-api-reference`.

**Verified no-edit (checked, not skipped):** `context-set-contract` and
`application-audit-chain` — the `context_set` shape and frozen-snapshot semantics
deliberately did *not* change, which is itself the recorded decision; `code-module-map` —
no module added or removed.

**Auditor catch-rate: 4 findings / 7 pages audited.** One DRIFTED cite
(`importing-your-experience` carried bare line numbers against the repo's path/symbol
convention), one DRIFTED label (`frontend-wizard` said the button reads "Restore" when it
reads "Restore experience"), one UNSUPPORTED structural defect (a one-way `[[career-corpus]]`
backlink with no return half), and one audience-tier violation (`career-corpus` is stamped
`user — no technical background assumed` and had acquired function names and module paths in
its body prose). All four repaired by the orchestrator; author never graded its own page.

**Two classes the auditors did NOT catch**, recorded so the catch-rate is not read as
completeness: (1) every scribe emitted its new paragraphs as single unwrapped lines against
pages wrapped at ~78 columns — cosmetic, but it would have made every future diff on those
pages a one-line churn; (2) `index.md`'s `corpus-data-model` entry read "alembic head 0010",
stale since before this branch and now doubly so. Both were found by reading the diffs
directly. The grounding auditors are scoped to cite/claim verification and would not be
expected to see either — that scoping is the point, not a defect, but it means a human (or
orchestrator) diff read remains load-bearing.

**One claim graded softer than the rest:** `corpus-to-output-reach`'s frozen-snapshot
consequence was marked SUPPORTED on the reasoning that it "logically follows", not by
tracing the re-render path. It agrees with the independently-recorded decision in
`docs/dev/blast-radius/experience-soft-retire.md`, so it is not suspect — but it is
inference, and should not later be cited as observed.

**`.last_ingest_sha` deliberately NOT advanced** — declared, not silently left, per C-12.
The checkpoint stays `65b0f88f5c2469484a3ed2ad8edbe28991f56df1` (2026-07-30). This pass
inspected one branch's slice; advancing the checkpoint would assert the whole backlog had
been ingested.

**Drift after this branch: 36 wiki-relevant files against the 75-file block threshold**, up
14 from 22. Measured, not reasoned (`scripts/wiki_relevance.is_wiki_relevant` over
`65b0f88f…`→HEAD versus this branch's own changed set): of this branch's 17 relevant paths,
`static/app.js`, `static/style.css` and `docs/architecture.md` were already in the drift set;
the other 14 are new to it. **Stated limitation:** those 14 are precisely the files this pass
just documented, but the counter measures "changed since checkpoint", not "wiki coverage
current" — so correctly-ingested work still inflates the number while the checkpoint is
deliberately held back. Now near half the threshold; the backlog wants a bounded catch-up
pass before it approaches 75.

---

## 2026-08-09 — `feat/compose-wait-ux` (Epic A, sprint A2 branch) — **widened catch-up pass; checkpoint ADVANCED**

**Mode:** full `.last_ingest_sha` window — `65b0f88f5c2469484a3ed2ad8edbe28991f56df1`
(2026-07-30) → `2a0b37a5c1105637fc283b0ac6df8c9d90a1e817` (HEAD). Deliberately **not**
a scoped per-branch pass. Why it exists at all:
[`../dev/epic-a-chain-design-corrections.md`](../dev/epic-a-chain-design-corrections.md)
§11.11 — the freshness counter measures *files changed since the checkpoint*, so
correctly-ingested work still inflated it while every honest scoped pass declined to
advance the marker. A ratchet that is never zeroed cannot engage. Zeroing it is what
makes every later sprint's per-branch advance a truthful, cheap claim.

**Drift, verbatim.**

- Before: `wiki_freshness: OK — 36 file(s) changed since the last ingest (< 75-file block threshold).`
- After: `wiki_freshness: OK — 0 file(s) changed since the last ingest (< 75-file block threshold).`

**The relevant set: 36 of 247 changed paths**, derived mechanically
(`scripts.wiki_relevance.is_wiki_relevant` over `git diff --name-only <ckpt> HEAD`), not
by judgment: `.gitignore`, `AGENTS.md`, `CLAUDE.md`, `analyzer.py`,
`blueprints/applications.py`, `blueprints/corpus/{_shared,curation,experiences,skills}.py`,
`blueprints/diagnostics.py`, `corpus_to_json_resume.py`, `dashboard/routes.py`,
`dashboard/templates/dashboard.html`, `db/build_context.py`,
`db/migrations/versions/0016_experience_is_active.py`, `db/models.py`,
`docs/architecture.md`, `docs/dev/AGENT_HANDOFF_TEMPLATE.md`, `docs/dev/RELEASE_ARC.md`,
`docs/dev/work/SCHEMA.md`, `docs/governance/{charter,enforcement}.md`,
`evals/{README.md,annotation.py,bootstrap.py,runner.py,seed_import.py}`, `hardening.py`,
`json_resume.py`, `onboarding/{corpus_import,review_cli}.py`,
`scripts/export_corpus_seed.py`, `static/app.js`, `static/style.css`,
`templates/index.html`, `web_infra/openapi.py`.

**Pages edited (9; none created).**

- `eval-harness` — F-14 `jd_label` (one derivation in `hardening.extract_jd_label`, three
  carriers, never re-derived); result records are `schema_version 3`; the item 11 → 13
  annotation-pin integrity pair (`bootstrap_fingerprint` + the fail-closed
  `ensure_anchor_covered_by_annotations`); `split_outside_brackets` in skill extraction.
  Also corrected `progress sartor` → `progress callback` — collateral damage from the
  product rename, which must never touch the recruiting sense of "callback".
- `diagnostics-console` — `_resolve_bootstrap_pin` returning `(path, stale_reason)` and
  failing **closed** with an HTTP 409 rather than substituting a newer bootstrap; the
  second 409 on an uncovered anchor; the restored recent-evals tile (item 32) and what it
  pointedly does *not* render; `_jd_label_display` / `_fixture_jd_labels` and why the
  label map is shared rather than per-table.
- `frontend-wizard` — the A2 "Composing…" wait gate (`_holdComposingBusy` /
  `_flushComposeSettleWaiters`, the ordering guarantee against `Compose.SETTLED`, the
  `_composeApplicationId` guard, the 20 s cap as a **declared** tradeoff); the labelled
  `_markComposeBgReload` chip; A1a's corpus panel section order + compacted skill rows
  with the three cascade/scoping constraints; item 31's `_statusGen` and `SELECT_READY`.
- `consistency-tracks-enforcement` — a dated "what happened next" section: the Q2 finding
  became charter **C-11**; the closure bar, the C-10 gate + its dual registry audit, the
  handoff recurrence section; and the **enforcement reach gap** — consistency tracks
  enforcement, and enforcement tracks which agent you are.
- `governance-extraction` — `enforcement.md`'s new "Enforcement reach" section read as
  what it says it is: the extraction checklist. A Claude-Code-only clause does not travel.
- `engineering-workstreams` — the v1.1.0 Final March epics A–E as the live plan of record,
  plus the two bounded Epic-A-only process amendments.
- `deterministic-llm-boundary` — `hardening.extract_jd_label` on the deterministic side;
  removed a leftover internal contradiction (the page said "no exceptions remain" and
  then, 14 lines later, called the scope check "the lone by-design exception").
- `document-rendering` — `json_resume.split_outside_brackets`, its two documented
  degenerate-input behaviors, and why it is public/shared with `evals/bootstrap.py`.
- `prompt-version-discipline` — `PROMPT_VERSION` `2026-06-13.1` → `2026-07-08.4`;
  `_BASE_SYSTEM_PROMPTS` 11 → **16** keys, reframed as a growing registry rather than a
  fixed list; `AVATAR_PROMPT_VERSION` `2026-06-19.1` → `2026-07-08.1`, and its two bare
  line-number cites (`analyzer.py:283–289`, `analyzer.py:519–540` — both drifted; the real
  definitions are at lines 402 and 642) replaced with symbol cites per SCHEMA's own
  stated preference.

`index.md` one-liners refreshed for the four pages whose scope changed.

**Verified no-edit (checked, not skipped).**

- `.gitignore` — a `personas/bundled/tmp*` re-ignore. No page describes ignore rules.
- `AGENTS.md` / `CLAUDE.md` — the C-10/C-11/C-12 operational mirror and the
  `require-consumer-enumeration` hook entry. Binding text lives in `docs/governance/`
  and is **cited, never restated** (SCHEMA "The contract lives elsewhere", D5); the
  wiki-side coverage went into `consistency-tracks-enforcement` + `governance-extraction`.
- `docs/architecture.md` — its two changes (the `check_refinement_scope` routing diagram,
  and dropping a non-existent `is_pending_review` from the `experience` ER entity) were
  already correctly reflected in `llm-call-catalog` and `corpus-data-model`. Confirmed
  against `db/models.py:Experience`, which has no such column.
- `llm-call-catalog` — already carries the item-21 `check_refinement_scope` entry from an
  earlier pass; re-read, still accurate at HEAD.
- `corpus-data-model` — already at alembic head `0016` with `Experience.is_active`
  (sprint A1b's pass); no further change in this window.
- `route-surface` — the changed corpus route contracts were covered by A1b, and the
  diagnostics write surface is deferred to `diagnostics-console` by design, which this
  pass updated instead.
- `code-module-map` — no module added or removed in the window; its
  `scripts/work_items.py` entry already describes the C-11 closure bar.
- `evals/seed_import.py`, `onboarding/*`, `scripts/export_corpus_seed.py`,
  `web_infra/openapi.py`, `blueprints/corpus/*`, `blueprints/applications.py`,
  `corpus_to_json_resume.py`, `db/*` — the `is_active` consumer set, fully covered by
  sprint A1b's pass; re-checked for changes outside that slice, none found.

**`.last_ingest_sha` ADVANCED** to `2a0b37a5c1105637fc283b0ac6df8c9d90a1e817`. This is the
first advance since 2026-07-30 and it is claimed honestly: the whole 36-path relevant set
above was worked source-by-source, each either edited into a page or given a
verified-no-edit line here. From here a per-branch pass's own slice **is** the whole delta,
so advancing the checkpoint at each branch close-out becomes truthful and cheap — the
owner's stated goal.

**Stated limits (C-0 / C-12 — named, not papered over).**

1. **Author ≠ auditor, and this pass had no auditor.** Every cite was verified against the
   working tree as it was written (symbols confirmed present in `static/app.js`,
   `dashboard/routes.py`, `blueprints/diagnostics.py`, `evals/annotation.py`,
   `hardening.py`, `json_resume.py`, `evals/bootstrap.py`, `evals/runner.py`,
   `analyzer.py`, plus `tests/test_enforcement_coverage.py`,
   `tests/test_work_items_closure_bar.py::TestGrandfatherListIsClosed` and
   `scripts/verify_doc_template.py:required_headings`) — but self-verification is not an
   audit. The nine pages above are the audit list.
2. **One claim was written wrong and corrected mid-pass**, recorded so the correction is
   not invisible: the 2026-08-09 RELEASE_ARC amendment was first summarized as "one gate
   run after the last sprint." It is not — it is one run *per sprint*, after the commit,
   dropping the vacuous pre-commit run. Caught by reading `RELEASE_ARC.md:1713` rather
   than trusting the paraphrase.
3. **Depth is uneven by design.** Prioritized by "would a reader be actively misled" — so
   the Epic A UX work, the eval/annotation integrity pair and the governance clauses got
   full sections, while `.gitignore` and the AGENTS/CLAUDE mirrors got a decision and a
   line. A path being in the verified-no-edit list means a decision was made and recorded,
   not that it was read as closely as an edited one.

---

## 2026-08-09 — grounding audit of the A2 catch-up pass (9 pages, author ≠ auditor)

**What:** the nine pages the `feat/compose-wait-ux` catch-up pass edited (the stated limit
1 above — "the nine pages above are the audit list") were handed to independent read-only
`wiki-grounding-auditor` agents. **Author ≠ auditor was preserved:** no page was audited by
the context that wrote it.

**Aggregate verdict: 6 DRIFTED, 0 UNSUPPORTED.** Five pages clean, four needed attention.

| page | verdict |
|---|---|
| `consistency-tracks-enforcement` | CLEAN |
| `deterministic-llm-boundary` | CLEAN |
| `document-rendering` | CLEAN |
| `eval-harness` | CLEAN |
| `prompt-version-discipline` | CLEAN |
| `governance-extraction` | 1 DRIFTED |
| `engineering-workstreams` | 1 DRIFTED |
| `diagnostics-console` | 3 DRIFTED |
| `frontend-wizard` | 1 DRIFTED |

**All six re-anchored in this branch**, each re-verified against the working tree as it was
rewritten:

1. `governance-extraction` — claimed the extraction boundaries live in `charter.md`'s
   "citation map (table at the end)". There is **no table**: the map is the inline
   `[src: …]` tag on every clause (`charter.md` "Evidence base" preamble). Description
   corrected; the RESOLVED decision it describes is unaffected.
2. `engineering-workstreams` — a `[synthesis]` claim credited `[[governance-extraction]]`
   as the recorder of W-1's still-serial posture. It is not the canonical home:
   `docs/governance/charter.md`'s **"Posture" paragraph** under W-1 is, and
   `docs/dev/RELEASE_ARC.md` §"Cadence + process" is what ties the sprint structure to
   W-1.3. Re-anchored to both; the `[[governance-extraction]]` backlink survives in
   `## Related`, where it is accurate.
3. `diagnostics-console` — three cite groups rotted by roughly +48/+58 lines against
   `blueprints/diagnostics.py`. **The code was correct; only the anchors were stale.** All
   three re-anchored to **symbols, not line numbers**: the queue-poll sites now name
   `_HEARTBEAT_INTERVAL_S` plus the four routes that poll on it
   (`annotation_score_grounding`, `annotation_bootstrap_stream`, `eval_run_stream`,
   `tune_run_stream`); the `except GeneratorExit` blocks name the same four functions; and
   the `if not cancel_event.is_set()` check drops its bare line number and stays described
   by its role inside `tune_run_stream`.
4. `frontend-wizard` — named the help-seen constant `CB_HELP_SEEN_PREFIX`, which does not
   exist. It is `SEEN_PREFIX` on the `Help` class in `ui_pages/selectors.py:87`. Rewritten
   to the durable string form `cb_help_seen:` plus a symbol cite to
   `ui_pages/selectors.py:Help.SEEN_PREFIX`.

**Method note carried forward.** Findings 3 and 4 are the same class: a bare line number or
a guessed constant name rots while the code stays right. Re-anchoring preferred
symbol/function cites throughout, which is what `SCHEMA.md` already asks for. This
recurrence is filed in the branch handoff's recurrences section, where it is stated plainly
that **no fail-closed mechanism was authored** for it (a `docs/wiki/` lint rejecting bare
`path:line` cites would be a new enforcement surface arriving at close-out — an owner
decision under the Epic A envelope's flag-stop rule, not a closer's call).

**Not re-audited:** the re-anchors above were written by this closing context and therefore
have no independent auditor of their own. Stated, not papered over (C-0).

---

## 2026-08-09 — incremental wiki pass, Epic A sprint A3 close (item 20, the Step-5 rail gate)

**Checkpoint:** `2a0b37a` → `3e2b8a5136c1ce1e1fd820d865742d3e5d9ab846`. **Drift before: 4.
Drift after: 0.**

**This is the first genuinely incremental pass** since the ratchet was zeroed on A2. The
relevant set was derived mechanically, not by judgement: `git diff --name-only 2a0b37a HEAD`
(29 files) filtered through `scripts/wiki_relevance.py:is_wiki_relevant`, leaving **4**:

- `hardening.py`
- `blueprints/applications.py`
- `blueprints/generation.py`
- `static/app.js`

**The change being documented.** Item 20 made the Step-5 wizard rail a hard gate and gave
client and server **one** predicate to gate on — the new public
`hardening.frozen_composition_doc`. Previously the client asked only "is there an
`approved_composition` dict?" while `/api/generate` applied a stricter test, so the rail
could open onto Step-5 copy promising deterministic assembly over a run the server then
handed to the legacy LLM `generate()`.

**Pages edited (4) — this is the audit list.** Author ≠ auditor: all four were written by
this closing context and are **not** audited here.

| page | edit |
|---|---|
| `corpus-to-output-reach` | New `## One predicate: "will this context assemble deterministically?"` section — the three conditions, the three call sites, why one implementation, and the allocation-free cost argument for calling rather than caching. `hardening.py` added to Sources. Reach path 2's description of `_frozen_composition` corrected (it no longer implements the test). |
| `frontend-wizard` | Step-5 gate added to the `_wizardReachable` description; new paragraphs on the hard gate's condition (the server's, not a client re-derivation), the deliberate empty-`career_corpus` lock-out and why it isn't a wall-in, and `_wizardLockReason` as the one message source for the toast + the previously-silent greyed-button `title`. `_compositionFrozen`'s two setters (`_postComposition`'s returned `frozen`; `resumeApplicationIntoWizard`'s `has_frozen_composition`) documented in the freeze section. |
| `context-set-contract` | The `approved_composition` bullet now names `frozen_composition_doc` as the one predicate and says why it lives in `hardening.py` — the module that owns this contract. |
| `route-surface` | The composition POST's response `frozen` field is not an echo of the request's `freeze` flag; it is the predicate applied in-lock to the dict about to be written. |

Backlinks reconciled bidirectionally: `context-set-contract` ↔ `frontend-wizard` added
(both directions); the `corpus-to-output-reach` ↔ `frontend-wizard` pair already existed and
its `corpus-to-output-reach` line was sharpened to name the shared predicate.

**Verified no-edit** (source changed, or page cites a changed symbol, and the page's existing
claims still hold at HEAD):

- `pipeline-stages` — cites `blueprints/generation.py:_frozen_composition` for the Step-5
  frozen-vs-legacy branch. The symbol still exists with unchanged semantics (it is now a
  named wrapper delegating to `hardening.frozen_composition_doc`), and the page describes the
  branch, not the predicate's implementation. Claim unaffected.
- `document-rendering` — same symbol, same reason; the page's subject is what happens *after*
  the gate returns a doc.
- `deterministic-llm-boundary` — `hardening.py` gained a new public function, but the page
  claims only that the module carries no LLM call. `frozen_composition_doc` is pure dict
  reads; the claim is strengthened, not challenged.
- `llm-call-catalog`, `iteration-audit-chain`, `corpus-data-model` — mention
  `approved_composition` as data, never the freeze predicate. No cite touched by this diff.

**Cite convention.** Every cite added in this pass is a **symbol** cite
(`hardening.py:frozen_composition_doc`, `app.js:_wizardLockReason`,
`blueprints/applications.py:_pre_generate_hydration`), never a bare `path:line` — following
the previous entry's carried-forward method note. That convention is still **unenforced**:
`SCHEMA.md` prefers it, and nothing rejects a bare line cite.

## 2026-08-09 — grounding-audit corrections to the item-20 pass (3 findings applied)

Independent auditors grounding-audited the item-20 pass logged directly above (author ≠
auditor — that pass's four pages were all written by the closing context and were **not**
self-audited). Three findings, all applied here; each premise was re-verified against the
code before editing rather than taken on the auditors' word.

| # | finding | fix |
|---|---|---|
| 1 | Off-by-one cost claim. `corpus-to-output-reach` and the `hardening.frozen_composition_doc` docstring both said "at most **five** `dict.get` lookups". The worst case is **six**: `career_corpus`, `approved_composition`, `basics`, `basics.get("summary")`, `doc.get("work")`, `doc.get("skills")` — the last reached only when `work` and `summary` are both falsy in the `or`-chain. | Both places corrected to six. The allocation-free / by-reference / short-circuit parts of the claim re-audited as correct and left alone. |
| 2 | `context-set-contract` conflated two counts, saying the predicate is asked at "three seams across `blueprints/generation.py`, `blueprints/applications.py` and the wizard rail". Two *implementations* once existed and disagreed (that is the drift the shared helper fixed); **three** *call sites* exist today (`generation.py:_frozen_composition`, `applications.py:_pre_generate_hydration`, `applications.py:save_application_composition`); the wizard rail is neither — it reads the server's flag and never computes the predicate. | Sentence rewritten so the two counts are distinct and the rail is described as a **consumer** of the decision. Now consistent with the docstring's own "those two … / all three seams" language. |
| 3 | True claim cited to a source that does not contain it. The page said the predicate lives in `hardening.py` because `applications` cannot import `generation` (cycle: `generation` → `templates` → `applications`). The cycle is real, but the rationale appeared in neither the cited source nor the docstring, which said only "because more than one seam has to ask the question and they must not answer it differently". | Fixed by making it **sourced**, not by weakening the page: the import-cycle rationale was added to the `frozen_composition_doc` docstring, next to the code it explains, so the page's citation is now honest. |

**Import cycle verified first-hand**, not inherited: `blueprints/generation.py` imports
`blueprints.templates`; `blueprints/templates.py` imports `blueprints.applications`
(`_load_application_owned`); `blueprints/applications.py` imports no `blueprints.generation`
at all (its only two matches for the string are a docstring and a comment). `hardening.py`
imports no blueprint, and both blueprints already import it — so it is the only shared home
that costs nothing structurally. That last sentence is now in the docstring.

**Sources touched:** `hardening.py` (`frozen_composition_doc` docstring only — the module is
deterministic under charter C-6, and no logic, import, or behavior changed). It is in
`ACKNOWLEDGED_NOT_GATED` in `scripts/enforcement/blast_radius.py`, confirmed before editing,
so no C-10 blast-radius dossier is owed.

**Cite convention.** Symbol cites throughout, no bare `path:line` — carried forward from the
two entries above. Still **unenforced**: `SCHEMA.md` prefers it, nothing rejects a line cite.

---

## 2026-08-10 — Epic A close-out wiki pass, the epic's own remaining delta (`feat/prior-apps-pipeline`)

**Deliberately deferred, now due.** Per
[`../dev/epic-a-chain-design-corrections.md`](../dev/epic-a-chain-design-corrections.md)
§15.2 ("light per sprint, one full close-out at the epic end"), this pass covers the
delta the incremental A2/item-20 passes above did not: `.last_ingest_sha`
(`3e2b8a5`, item 20's tip) → this branch. **`.last_ingest_sha` deliberately NOT
advanced** — the orchestrator advances it after the grounding audits on this pass's
pages pass, so a finding can still be repaired first (per this session's own
instructions).

**Scope, derived mechanically.** `git diff --name-only 3e2b8a5 HEAD` (68 files)
filtered through `scripts/wiki_relevance.py:is_wiki_relevant` → **18**: `analyzer.py`,
`blueprints/applications.py`, `corpus_to_json_resume.py`, `db/build_context.py`,
`demo_fixtures.py`, `docs/architecture.md`, `docs/dev/work/BOARD_DEFERRAL.md`,
`evals/TUNING_LOG.md`, `evals/corpus_drafting_probe.py`,
`evals/fixtures/synthetic/corpus/role-summary-drafting/{analysis.json,jd.txt,seed.json}`,
`evals/seed_import.py`, `hardening.py`, `scripts/export_corpus_seed.py`,
`static/app.js`, `static/style.css`, `templates/index.html` — confirmed to match
the count and list this session was handed, not assumed.

**What changed.** Two Epic A sprints: **A3** (`feat/role-summary-drafting`,
`7d3ff33`) — a new batched Sonnet call, `analyzer.py:draft_experience_summaries`,
drafting a JD-fitted one-line role intro for EVERY included role in ONE call;
two new routes (`draft-experience-summaries`, `experience-summary-decide`); a new
durable `ContextSet` key (`experience_summary_items`) staged by
`db/build_context.py:_experience_summary_groups`; `hardening.py:assemble_source_union`
widened to a fifth grounding source; a per-application acceptance ledger
(`accepted_experience_summary_ids`) closing a cross-application pending-variant leak
at four read sites; a new targeted eval probe (`evals/corpus_drafting_probe.py`) plus
a nested synthetic corpus fixture. **A4** (`feat/prior-apps-pipeline`, `3cfb98d`) — the
standalone "Prior applications" panel removed entirely; `_renderPipelineRow`'s click
handler now re-asserts Pipeline and opens the shared detail modal in place, instead of
switching to Tailor.

**Pages edited (9).**

| page | edit |
|---|---|
| `context-set-contract` | New `experience_summary_items` optional-field bullet; the source-union enumeration extended with the A3 fifth source. |
| `corpus-to-output-reach` | New `accepted_experience_summary_ids` override-table row; new "Drafting a role intro (A3) and the pending-leak guard" section (the author/select split, the KEEP/REJECT flow, the four read sites the guard closes); the Role-intro resolution bullet updated to name the guard. |
| `llm-call-catalog` | New `draft_experience_summary` Sonnet table row; "three Compose drafting calls" → "four" in both places that phrase appeared. |
| `prompt-version-discipline` | `PROMPT_VERSION` `2026-07-08.4` → `2026-08-09.1`; `_BASE_SYSTEM_PROMPTS` **16 → 17 keys**; "most recent addition" updated from `SCOPE_CHECK_SYSTEM_PROMPT` to `DRAFT_EXPERIENCE_SUMMARIES_SYSTEM_PROMPT`. |
| `eval-harness` | `PROMPT_VERSION` mention corrected to `2026-08-09.1`; new "The corpus-mode drafting probe (Epic A sprint A3)" section — `evals/corpus_drafting_probe.py`, why it exists, why the nested fixture doesn't disturb the existing "three synthetic fixtures" claim. |
| `route-surface` | Route count **117 → 119** (two new `blueprints/applications.py` routes). |
| `frontend-wizard` | **Corrected a stale claim** the 2026-07-13 pass had itself corrected the other direction: `_renderPipelineRow` no longer switches to Tailor (A4 removed that panel) — it re-asserts Pipeline and opens the detail modal in place. New paragraph on the A3 role-intro drafting UI (draft card, Keep/Reject, the serialize-not-race ordering against the recommend call). Concept line updated. |
| `generation-and-grounding` | "three drafting calls that accept `prior_clarifications`" → four (added `draft_experience_summaries`); new paragraph on the A3 fifth source-union widen. |
| `pipeline-stages` | Compose-authors-content sentence extended to name `draft_application_experience_summaries`. |

**Countable claims verified mechanically, not asserted** (this epic's own grounding
audits found every substantive error was a countable claim, so every number below was
re-derived from source in this session, not carried over from the branch's own
commit messages):

- `_BASE_SYSTEM_PROMPTS` keys: `python -c "..."` parsing the dict literal in
  `analyzer.py` → **17**, matching the DRAFT_EXPERIENCE_SUMMARIES_SYSTEM_PROMPT
  addition.
- Total `@<bp>.route` decorators: `grep -rn "^@[a-zA-Z_]*\.route" blueprints/`
  (anchored at line start, excluding `__pycache__`) → **118**, plus
  `dashboard/routes.py`'s **1** → **119** total. Cross-checked against the same
  count run at the `3e2b8a5` checkpoint commit (`git show 3e2b8a5:<path> | grep
  -c ...` per file): blueprints **116** + dashboard **1** = **117**, exactly
  reconciling with the page's pre-existing 117 and the +2 this delta's two new
  routes account for — the before/after figures agree, not just the after one.
  A naive `grep -c "@applications_bp.route" blueprints/applications.py` (the
  exact command the module's own docstring suggests) returns **23**, one over
  the true **22**, because it also matches the docstring's own literal mention
  of that grep command — caught only by rerunning with a line-start anchor.
  Flagged so the next session doesn't trust that docstring's suggested command
  literally.
- `blueprints/applications.py` routes: **22**, confirmed both via the anchored
  grep and via a diff read of the two routes A3 added.
- Pending-leak guard read sites: **4**, confirmed by grepping
  `accepted_experience_summary_ids` in `blueprints/applications.py` (2 sites:
  the GET picker filter at the `esi_rows` comprehension, the POST validator) and
  `corpus_to_json_resume.py` (2 sites: `build_json_resume_from_corpus`'s read +
  pass-through, `_resolve_chosen_experience_summary_text`'s check).
- `draft_experience_summaries` reads `context_set["prior_clarifications"]`:
  confirmed by reading the function body (`_prior_clarifications_block(...)` call)
  and the system prompt's own `<prior_clarifications>` block — this is what makes
  it a fourth call in the D5 list on `generation-and-grounding`, not three.

**Every one of the 18 relevant sources, accounted for.** 6 drove the 9 page edits
above (`analyzer.py`, `blueprints/applications.py`, `corpus_to_json_resume.py`,
`db/build_context.py`, `hardening.py`, `static/app.js`); `evals/corpus_drafting_probe.py`
drove the new `eval-harness` section. The remaining **11 verified no-edit** (checked,
not skipped):

- `docs/architecture.md` — already correctly updated by the A3 branch itself (both
  Mermaid diagrams gained `draft_experience_summaries`/A9, the routing-tier prose
  updated to "four Compose-time drafting calls"); the wiki cites this file, never
  duplicates it (D5), so nothing to re-anchor.
- `docs/dev/work/BOARD_DEFERRAL.md` — a governance/gate-mechanism document (the
  `check_with_deferral()` staleness exemption for `python -m scripts.work_items
  check`), the same process-record character `scripts/wiki_relevance.py` already
  wholesale-excludes for `docs/dev/diagnosis/` and `docs/dev/handoffs/` and that the
  2026-08-08 `docs/epic-a-chain-design-corrections` pass treated the same way; it
  defaults relevant only because it sits directly under `docs/dev/work/`, not
  `docs/dev/work/items/`. Grepped every `docs/wiki/pages/*.md` for `BOARD_DEFERRAL` /
  `check_with_deferral` / `board staleness` — zero hits, nothing to re-anchor. Not a
  product/architecture concept the wiki curates.
- `evals/TUNING_LOG.md` — the A3 tuning entry it gained is now the target of the new
  `eval-harness` "corpus-mode drafting probe" section's own citation; the log itself
  is referenced, never duplicated (D5), same as every prior `TUNING_LOG.md` entry.
- `demo_fixtures.py`'s new `demo_draft_experience_summaries` — no wiki page
  documents demo mode / `_demo_mode_active` at all (grepped, zero hits); a
  pre-existing coverage gap this diff does not worsen in a way that breaks an
  existing claim.
- `evals/seed_import.py` / `scripts/export_corpus_seed.py` — both gained
  `ExperienceSummaryItem` round-trip support; no wiki page enumerates the seed
  format's entity list (grepped for `seed_import`/`export_corpus_seed`/round-trip
  language — the hits are all unrelated round-trip mentions elsewhere), so no claim
  to update.
- `evals/fixtures/synthetic/corpus/role-summary-drafting/{analysis.json,jd.txt,seed.json}`
  — fixture data, not cited by content anywhere; covered at the mechanism level by
  the new `eval-harness` "corpus-mode drafting probe" section instead.
- `static/style.css` — grepped for the removed `.application-card*` family and the
  new `.compose-role-intro-draft*` classes across `docs/wiki/pages/*.md`; zero hits
  either way. No page cites CSS class names for this surface.
- `templates/index.html` — the "Prior applications" panel markup (`#panelApplications`)
  it removed is not cited by any page directly; the fact of the removal is captured
  through the `static/app.js`-driven `frontend-wizard` fix above (`_renderPipelineRow`
  no longer opens that panel because the panel is gone). Grepped for `panelApplications`
  across `docs/wiki/pages/*.md` — zero hits, confirming no dangling reference existed
  to clean up either.

**Pages checked and confirmed still accurate** (not sources from the 18, but pages a
changed source cites — inspected in case the change reached them, not assumed safe):
`corpus-data-model` (no DB model or migration file changed in this delta — confirmed
`git diff 3e2b8a5 HEAD --name-only | grep -i "db/models\|migrations"` returns nothing
— so the alembic-head-`0016` claim and the corpus-item table are still current);
`application-audit-chain`, `iteration-audit-chain`, `deterministic-llm-boundary`,
`document-rendering`, `code-module-map` (grepped each for
`draft_experience_summar`/`experience_summary`/`recommend_experience`/`IterationLog`
action names/`corpus_drafting_probe`; no claim on any of these five references
anything this delta touched, and `code-module-map`'s `evals/` row is already
deliberately non-exhaustive — cites only `runner.py` — so needs no new entry);
`career-corpus`, `importing-your-experience`, `tailoring-a-resume` (user-tier — none
currently describe role intros at all, grepped, so A3 introduces a coverage gap, not
a false claim; per the established convention that content passes are separate
branches, not folded into a code-diff pass — see the 2026-06-14 / 2026-06-25 entries
above — left for a dedicated content pass rather than authored here).

**Author ≠ auditor not yet run.** This pass's nine edited pages are the audit list —
none were graded by the context that wrote them. `git add -A` staged; not committed
(orchestrator's step). `.last_ingest_sha` left at `3e2b8a5` on purpose, per this
session's instructions, so a grounding-audit finding can still be repaired before the
checkpoint advances.

## 2026-08-11 — verified no-edit (`docs/pre-epic-b-review`)

**Scoped check, not a diff-window pass — `.last_ingest_sha` NOT advanced.** The branch's
own close-out sweep found exactly one wiki-relevant changed file per
`scripts.wiki_relevance.is_wiki_relevant()`: [`../dev/RELEASE_ARC.md`](../dev/RELEASE_ARC.md)
(a widened `## v1.1.0 Final March` "Cadence + process" bullet — chain epics now declare
coherence-drift review checkpoints alongside close-out intervals — plus a new sequencing
norm batching `main`-moving merges around a long-running epic PR).

**Checked every page that cites `RELEASE_ARC.md`** (`grep -rl "RELEASE_ARC" docs/wiki/pages/`
— [[engineering-workstreams]], [[excellence-walk]], [[governance-extraction]]) — every
citation is a **pointer** to a Phase/section ("§Phase 4.5", "§Phase 4.7", "§Phase 4.8",
"§'Cadence + process' ties the sprint board→stage→commit→gate sequence together") or an
explicit "RELEASE_ARC is authoritative and moves — re-check it, not this page" disclaimer
(`engineering-workstreams.md:79`). **None restates specific content of the "Cadence + process"
list** (a bullet count, a named existing rule) that this addition would make stale — it is a
pure addition, and every existing pointer/claim on all three pages remains accurate. No page
edit needed; confirmed by reading, not assumed from the pointer pattern.

## 2026-08-11 — verified no-edit (`fix/retired-roles-a3-prompt`)

**Scoped check, not a diff-window pass — `.last_ingest_sha` NOT advanced.** The branch's
close-out sweep found two wiki-relevant changed files per
`scripts.wiki_relevance.is_wiki_relevant()`: `blueprints/applications.py` and
`evals/corpus_drafting_probe.py` (item 75 — `_build_experience_summary_targets` now takes
a live `active_exp_ids` set from both consumers, so a role soft-retired after analyze
never reaches the A3 drafting prompt off its frozen bullets).

**Checked every page citing the changed symbols** (`draft_experience_summaries` /
`corpus_drafting_probe` — [[corpus-to-output-reach]], [[context-set-contract]],
[[eval-harness]], [[generation-and-grounding]], [[llm-call-catalog]],
[[prompt-version-discipline]]): every claim describes behavior the fix does not change —
the batched one-call shape, the transient-drafts contract, the probe's reuse of the
route's own target builder (still true; it now also stages the identical live filter),
and prompt/caching facts. The "every included role" phrasing on
[[corpus-to-output-reach]] becomes strictly MORE accurate, not stale. No page edit
needed; confirmed by reading each citation's surrounding claim, not assumed from titles.

## 2026-08-11 — verified no-edit (`docs/extraction-governance-drift-reconcile`)

**Scoped check, not a diff-window pass — `.last_ingest_sha` NOT advanced.** The branch
also removed `README.md:3-5`'s "Formerly named Callback" rename-disclosure blockquote
(owner-directed retirement — a short-lived note explicitly meant to retire, not a
correction). `README.md` is wiki-relevant. Checked every page citing `README.md`
([[diagnostics-console]], [[eval-harness]], [[excellence-walk]]) — every hit is a
different `README.md` (`dashboard/`, `evals/`, `excellence-walk/`), not the root file;
none cites the removed passage. No page edit needed.

The branch
reconciled four stale claims (external-survey-flagged, verified against HEAD before any
edit) in `docs/dev/EXTRACTION.md`, `docs/dev/governance-extraction-design.md`,
`docs/governance/enforcement.md`, and `docs/dev/kit-adoption-design.md` — `recall/`'s
"design-only, not committed" claim, the compliance agent's "does not exist yet" claim,
the portable-enforcement-core's "pending decision" framing, and the CI "latent until the
remote activates" claim (verified stale via live `gh api branches/main/protection`: 6
required contexts, `strict: true`). All four are wiki-relevant per
`scripts.wiki_relevance.is_wiki_relevant()`.

**Checked every page citing the four files** (`grep -rl` across `docs/wiki/pages/` for
each path — [[consistency-tracks-enforcement]], [[engineering-workstreams]],
[[governance-extraction]]): every citation is a **pointer** to an unrelated section
(§C2, §"Enforcement reach", §6 mypy-strict) or a generic cross-reference — none restates
or depends on the specific stale prose corrected on this branch (the "design-only" /
"does not exist yet" / "latent" phrasing does not appear verbatim or paraphrased on any
of the three pages). No page edit needed; confirmed by reading each citation's
surrounding claim, not assumed from the pointer pattern.

---

## 2026-08-11 — scoped close-out relevance check (`feat/n1-baseline-pipeline`)

**Trigger:** branch close-out, scoped to this branch's own diff (not a full ingest).

**Wiki-relevant paths in this diff (per `scripts/wiki_relevance.py`): 2** —
[`../../.gitignore`](../../.gitignore) and [`../dev/RELEASE_ARC.md`](../dev/RELEASE_ARC.md).
Classifier run over the full committed + working diff, not eyeballed. (The pipeline script
under `.claude/workflows/`, both `agents/` role files, `scripts/wiki_relevance.py` itself,
the new `docs/dev/n1-baseline-pipeline.md` (classified irrelevant this branch — agent
tooling, revisit on first authorized run), `tests/`, `docs/dev/blast-radius/`,
`docs/dev/ledger/`, the corrections doc, and `docs/dev/work/` all classify irrelevant.)

**Pages edited (0). Pages verified no-edit:** the `.gitignore` change is a two-line
re-include of `.claude/workflows/` — no page describes ignore rules (the 2026-08-08 full
sweep recorded the same finding for `.gitignore` explicitly). The `RELEASE_ARC.md` change
adds two session-model clauses (Fable = design/planning scope; Sonnet-subagent delegation)
— grep over `docs/wiki/` for "Session models" / "Fable" / model-assignment prose: zero
hits; no page restates the session-model table or its surrounding rules. Checked, not
skipped.

---

## 2026-08-12 — scoped close-out relevance check (`fix/n1-args-guard-hardening`)

**Trigger:** branch close-out, scoped to this branch's own diff (not a full ingest).
This entry also discharges the check owed by `epic/b-render-ats`'s `34ad528` (the
`*.mjs` pin — carried forward as open item #5 in
[`../dev/handoffs/epic-b-render-ats.md`](../dev/handoffs/epic-b-render-ats.md)): same
file, same conclusion, checked together here.

**Wiki-relevant paths in this diff (per `scripts/wiki_relevance.py`): 3** —
[`../../.gitattributes`](../../.gitattributes), [`../../.gitignore`](../../.gitignore),
and [`../../AGENTS.md`](../../AGENTS.md). Classifier run over the branch diff, not
eyeballed. (The pipeline script under `.claude/workflows/`, `tests/` (including the new
`tests/test_gitattributes_coverage.py`), `scripts/work_items.py` (docstring-only
correction), and the `docs/dev/` runbook/brief/diagnosis/work-item edits all classify
irrelevant.)

**Pages edited (0). Pages verified no-edit:** `grep -rn` across `docs/wiki/pages/` for
`gitattributes`, `CRLF`, and line-ending prose: zero hits — no page describes checkout
normalization or ignore rules (the 2026-08-11 sweep recorded the same for
`.gitignore`). For the `AGENTS.md` one-line citation correction ("charter D5" → the
charter's extract-don't-restate rule): `cite-don't-restate`, `charter D5`, and `D-5`
each grep to zero hits across `docs/wiki/pages/` — no page restates the corrected
label. Checked, not skipped.

---

## 2026-08-12 — scoped close-out self-update (`feat/interrogative-prompt-witness`)

**Trigger:** branch close-out, scoped to this branch's own diff (not a full ingest;
checkpoint NOT advanced — scoped passes never honestly can, see item 65).

**Wiki-relevant paths in this diff (per `scripts/wiki_relevance.py`): 2** —
[`../../CLAUDE.md`](../../CLAUDE.md) and
[`../governance/enforcement.md`](../governance/enforcement.md). Classifier run over
the branch diff, not eyeballed.

**Pages edited (2), via the wiki-scribe subagent (one per page, author≠auditor):**
[`governance-extraction`](pages/governance-extraction.md) and
[`consistency-tracks-enforcement`](pages/consistency-tracks-enforcement.md) — both
enumerate the Claude-Code-only guard roster from `enforcement.md` §"Enforcement
reach", which grew by `interrogative_witness` (work item 87) on this branch; each
roster extended plus the by-nature-not-by-gap distinction, `[synthesis]`-tagged.

**Auditor verdicts (wiki-grounding-auditor, one per page):**
`consistency-tracks-enforcement` — 10 SUPPORTED / 0 DRIFTED / 0 UNSUPPORTED.
`governance-extraction` — 16 SUPPORTED / 1 DRIFTED / 0 UNSUPPORTED; the DRIFT was
pre-existing prose ("derives the routing from the adapter" where source and test both
name `git_hook.py`) — re-anchored to `git_hook.py` per the auditor's suggestion.
Catch-rate this run: 1 caught / 2 pages audited.

**Pages verified no-edit:** for the `CLAUDE.md` hook-list addition — its only wiki
cites are the `@import` mention in `governance-extraction` (line 49-51, unaffected)
and no page restates the hook roster (grep for `wiki-freshness-reminder` / "hook
list" across `docs/wiki/pages/`: zero hits). Checked, not skipped.

---

## 2026-08-12 — scoped close-out self-update (`fix/b1-stale-template-companions`, Epic B sprint B1a)

**Trigger:** branch close-out, scoped to this branch's own diff (not a full ingest;
checkpoint NOT advanced — a scoped pass never honestly can, see item 65). Drift at
check time: 14 of 75 (`python -m scripts.wiki_freshness`), well under both the
75-file block threshold and the epic's own 40-file deferral margin
(`../dev/handoffs/epic-b-design-brief.md` §"Close-out intervals") — the full pass +
`.last_ingest_sha` advance stays correctly deferred to the epic close.

**Wiki-relevant paths in this diff (per `scripts/wiki_relevance.py`): 3** —
[`../../docx_to_persona_html.py`](../../docx_to_persona_html.py),
[`../../blueprints/templates.py`](../../blueprints/templates.py), and
[`../../generator.py`](../../generator.py). Classifier run over the branch diff, not
eyeballed (`tests/test_docx_to_persona_html.py`, `CHANGELOG.md`, and the
`docs/dev/{diagnosis,blast-radius,work}/` dossiers/board all classify irrelevant).

**Pages edited (1), hand-authored by the closer (no scribe/auditor pair spun up for
a one-paragraph factual correction):**
[`document-rendering`](pages/document-rendering.md) §"`.pdf` — Playwright Chromium"
— the page named `pdf_render.py:html_template_path_for` as *the* HTML-companion
resolver for the PDF path. This branch's own diff (B1a, the stale-imported-template-
companion fix) changes that: `generator.py:_render_pdf_from_json` (`:259-261`) now
calls `docx_to_persona_html.py:resolve_companion_html`, which regenerates a
companion whose sidecar-stamped `skeleton_version` predates the shipped skeleton;
`html_template_path_for` is demoted to an internal existence check
`resolve_companion_html` calls, not the entry point callers use directly. Corrected
in place, with a pointer to the diagnosis dossier. `[synthesis]` unchanged elsewhere
on the page.

**Pages verified no-edit (checked every page citing the three changed files, or the
specific new/changed symbols, by name — not assumed from the classifier alone):**

- `docx_to_persona_html` symbols (`resolve_companion_html`, `generate_companion`,
  `skeleton_version`, `companion_stamp_is_current`) — zero hits anywhere under
  `docs/wiki/pages/` before this entry's own edit. The persona-companion resolution
  subsystem is a coverage gap, not a drift case: nothing existed to go stale.
- [`deterministic-llm-boundary`](pages/deterministic-llm-boundary.md) — cites
  `docx_to_persona_html.py` as one of the 8 deterministic (no-LLM) modules and
  describes it as "emits an HTML+CSS live-preview companion." Still true; this
  branch adds a staleness-refresh path to the same deterministic module, no LLM
  call anywhere in the diff (verified: `git grep -n anthropic` over the branch's
  changed files returns nothing).
- [`code-module-map`](pages/code-module-map.md) — cites `pdf_render.py:
  html_template_path_for` in its module table as one notable function of
  `pdf_render.py`. The function still exists with its original pure-resolver
  contract (`tests/test_pdf_render.py:41-62` still asserts exactly that shape,
  unchanged by this branch) — the table doesn't claim callers use it directly, so
  it isn't made false by the routing change; left as is.
- [`corpus-to-output-reach`](pages/corpus-to-output-reach.md) — describes
  `blueprints/templates.py:preview_application_html`'s three-tier
  `composition_overrides` priority (frozen / cached / fresh JSON Resume content).
  Orthogonal to this branch: the diff changes *which HTML template file* backs a
  render, never *which JSON Resume content* is rendered.
- [`editing-and-refining`](pages/editing-and-refining.md) — cites
  `blueprints/templates.py:preview_edited_html` once, in the frontmatter source
  list only; no body claim describes its internal companion-resolution mechanism.
- [`resume-templates`](pages/resume-templates.md) — cites `docx_to_persona_html.py`
  for `extract_persona_style` (typography extraction), a different function this
  branch does not touch.
- `frontend-wizard.md:378`'s "companion editor" is the co-located preview-pane UI
  concept (`#resumePreview`/`#coverPreviewFrame`), an unrelated sense of the word —
  confirmed by reading, not assumed from the string match.

Checked, not skipped.

---

## 2026-08-12 — scoped close-out relevance check (`fix/n1-invoker-loop`)

**Trigger:** branch close-out, scoped to this branch's own diff (not a full ingest).

**Wiki-relevant paths in this diff (per `scripts/wiki_relevance.py`): 1** —
[`../dev/RELEASE_ARC.md`](../dev/RELEASE_ARC.md). Classifier run over the full staged
diff, not eyeballed. (The pipeline script under `.claude/workflows/`, the runbook
`docs/dev/n1-baseline-pipeline.md`, the sprint-brief template and briefs under
`docs/dev/handoffs/`, `docs/dev/diagnosis/`, `docs/dev/ledger/`, `docs/dev/work/`, and
`tests/` all classify irrelevant — same classifications as the two prior n1 branches.)

**Pages edited (0). Pages verified no-edit:** the `RELEASE_ARC.md` change is a dated
amendment to §"Session models" (invoking-session model for N=1 pipeline runs = owner's
choice of Fable or Opus, stated at invocation; sprint-internal casting unchanged).
Grep over `docs/wiki/` for "Session models" / "Fable" / model-assignment prose: zero
hits outside this log's own prior entries — no page restates the session-model table
or its surrounding rules, exactly as the 2026-08-11 fold-in entry found. Checked, not
skipped.

## 2026-08-13 — scoped close-out relevance check (`fix/b1-education-render`, B1b)

**Trigger:** intra-epic sprint close-out (Epic B, B1b — 2 of 3), scoped to this
branch's own staged diff, not a full ingest. Per `epic-b-design-brief.md`
§"Close-out intervals," the full wiki pass (ingest + `.last_ingest_sha` advance) is
**deferred to the epic close** unless drift exceeds the 40-file margin —
`python -m scripts.wiki_freshness` reports **17 of 75** at this branch's tip
(pre-commit; unchanged from B1b's own predecessor sprint), well under the margin, so
that deferral stands. This entry is the still-owed scoped relevance check, not the
deferred pass.

**Wiki-relevant paths in this diff (per `scripts/wiki_relevance.py`, run over the
full staged diff — 5 of 10 changed files):** `corpus_to_json_resume.py`,
`generator.py`, `json_resume.py`, `personas/bundled/classic.html`,
`personas/bundled/spacious.html`. (`docs/dev/blast-radius/`, `docs/dev/diagnosis/`,
and `tests/` classify irrelevant, matching every prior branch's classification.)

**Pages edited (0). Pages verified no-edit** (grepped for the new/changed symbols
by name, then read the surrounding claim, not assumed from the classifier alone):

- `education_position_text`, `split_education_position`,
  `EDUCATION_FIELD_SEPARATOR`, `_collect_education`, `run_font_name` — zero hits
  anywhere under `docs/wiki/pages/`. New symbols this sprint introduces; nothing
  existed to go stale.
- [`document-rendering`](pages/document-rendering.md) — the only page citing
  `classic.html`/`spacious.html` by name (`:164`, the PDF-render fallback path) and
  `generator.py:_write_docx_from_json_resume` (`:36`, `:120`, plus
  `downloading-your-documents.md:11`). Both mentions describe *which file/function
  renders*, not education-field completeness or font-capture completeness — neither
  claim is made false by this branch (which adds a `studyType` span and a captured
  `run_font_name`, changes no routing).
- [`code-module-map`](pages/code-module-map.md) — cites
  `generator.py:_write_docx_from_json_resume` in its module table as one notable
  function; same reasoning, a name citation with no behavioral claim.
- [`deterministic-llm-boundary`](pages/deterministic-llm-boundary.md) — cites the
  companion generator's font capture (a different module,
  `docx_to_persona_html.py`, unrelated to this branch's `generator.py` proto-dict
  change).

Checked, not skipped.

## 2026-08-14 — scoped close-out self-update (`feat/ats-conformance`, Epic B sprint B2)

- **Mode:** diff, scoped to this branch's own window `b0aaed3 → HEAD` (B2
  ATS-conformance landing). **Checkpoint `.last_ingest_sha` deliberately NOT
  advanced:** it sits 64 commits behind this branch's base, so advancing it
  from a branch-scoped pass would silently absolve the un-ingested middle
  window; `scripts/wiki_freshness.py` keeps that backlog visible for the
  epic-close catch-up pass.
- **Sources read:** 17 wiki-relevant changed files (json_resume.py,
  blueprints/generation.py, blueprints/corpus/{_shared,experiences,curation}.py,
  web_infra/openapi.py, onboarding/{corpus_import,extract_experiences}.py,
  generator.py, docx_to_persona_html.py, pdf_render.py, analyzer.py,
  static/{app.js,style.css}, personas CSS ×2, plus the new
  docs/dev/board-forge-sync-review.md — classified deliberately IRRELEVANT in
  scripts/wiki_relevance.py this same branch).
- **Pages changed (7, scribe-per-page, Haiku):** career-corpus,
  importing-your-experience, document-rendering, openapi-api-reference,
  route-surface, prompt-version-discipline, tailoring-a-resume. No pages
  created; index.md entries unchanged (topics unchanged).
- **Auditor catch-rate (per-page grounding audit, Haiku, author≠auditor):**
  2 caught / 7 pages — both PRE-existing, neither scribe-introduced:
  1. DRIFTED (openapi-api-reference): route count "117 total" vs 119 at HEAD —
     re-anchored (117→119, 112→114).
  2. UNSUPPORTED (route-surface.md:235-236, pre-existing): "`proposals.py` …
     the only corpus submodule on the `anthropic` egress allowlist" — FALSE at
     HEAD: tests/test_egress_allowlist.py also lists
     blueprints/corpus/skills.py. **Left flagged, not silently rewritten**
     (loop rule); owner decision pending — suggested fix: "one of two corpus
     submodules on the allowlist (with skills.py)".
- **Deterministic gate:** scripts/check_doc_links.py OK (483 files, no broken
  links/cites); full quality gate runs at branch close.

## 2026-09-04 — `feat/install-onboarding-preflight` (diff, branch-scoped)

- **Mode:** diff, but deliberately **branch-scoped** (`main`…`HEAD`), NOT the
  checkpoint window. `.last_ingest_sha` sits at `f42b2ea` with **213 files**
  changed since — far past a steady-state increment. That backlog is item 98 /
  item 65 (the checkpoint-ratchet defect), not this branch's to absorb.
- **`.last_ingest_sha` deliberately NOT advanced.** Advancing it to HEAD would
  stamp coverage over 213 changed files when this pass read 7. That false
  advance *is* the ratchet defect, so the checkpoint stays at `f42b2ea` and the
  drift stays visible. Recorded here rather than left implied (C-0).
- **Sources read (7, this branch's own diff):** `preflight.py` (new), `app.py`,
  `pdf_render.py`, `blueprints/users.py`, `templates/index.html`,
  `docs/install.md`, `README.md`. Tests and the diagnosis dossier classify
  IRRELEVANT and were not ingested as sources (the dossier was read as
  *evidence* by the scribes, which is the intended use).
- **Pages created (1, scribe-authored, Haiku):** `machine-capability-preflight`
  — the tri-state capability probes behind `--doctor`, `--setup`, and the PDF
  gate. Scaffolded by the orchestrator (the scribe holds `Edit`, not `Write`,
  so it cannot create a file); body authored by the scribe, so author≠auditor
  still holds.
- **Pages changed (5, scribe-per-page, Haiku):** `document-rendering`,
  `troubleshooting`, `downloading-your-documents`, `non-dependency-downloads`,
  `code-module-map`. One `index.md` entry added for the new page.
- **Auditor catch-rate (author≠auditor, Haiku, 2 audit contexts / 6 pages):**
  **5 caught** — 3 DRIFTED, 2 UNSUPPORTED.
  1. DRIFTED ×3 (`machine-capability-preflight`): bare line-range cites
     (`preflight.py:16–38`, `:419–450`, `:352–367`). All three ranges were
     *correct*, but SCHEMA prefers a symbol over a line number because line
     numbers drift — re-anchored to `preflight.py:api_key_capability`,
     `preflight.py:pdf_available`, and the module docstring.
  2. UNSUPPORTED (`troubleshooting`): the page said Sartor **hides** the PDF
     option. The code *disables* it (`disabled aria-disabled="true"` plus a
     visible reason) and leaves it in the DOM — materially different UX states.
     Corrected to "greys the button out, with a note saying why".
  3. UNSUPPORTED (`code-module-map`): the new `preflight.py` row was placed in
     a table headed "The deterministic floor (P1 hardening — no LLM calls)",
     which implies membership in the **C-6 boundary list**. `AGENTS.md`
     enumerates eight modules there and `preflight.py` is not among them. The
     module *is* deterministic and stdlib-only; the row now says so explicitly
     and disclaims the governed-set membership. Same disclaimer added to the
     new page's "Determinism and stated limits" section.
- **Caught by the orchestrator, not the auditors (recorded so the catch-rate
  is not overstated):** 5 further defects in the scribe's new page — a dangling
  `[[pdf-available-design]]` backlink to a page that does not exist, a
  `drivers/package/` path typo (real path is `driver/`), `pdf_render()` for
  `render_pdf()`, an "items 100/108" attribution (108 is the gate memory
  preflight, unrelated), and a misread of the O-5 cost table that rendered the
  control/absence arms as "heads/headless".
- **Corrected in SOURCE, not just the wiki:** the audit surfaced that
  `preflight.api_key_capability`'s own docstring claimed "the value is never
  read or shown". It *is* read — testing for a non-blank key requires it. The
  docstring and the page now state the narrower, true guarantee: the value
  never reaches `detail`, `remedy`, a log, or a return value. (The first
  auditor passed this claim as SUPPORTED; it was caught on independent re-read.)
- **Deterministic gate:** dangling-backlink sweep over all 39 pages — none;
  `index.md` ↔ pages reconciled; `ruff` clean on the touched module. Full
  quality gate runs at branch close.
