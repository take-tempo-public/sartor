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
