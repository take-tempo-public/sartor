# Vision — sartor.

sartor. answers one question, honestly:

> *"What résumé and (optional) cover letter should I send for
> this specific job?"*

Acronyms used throughout: **JD** = job description; **LLM** =
large language model (Anthropic's Claude, here); **ATS** =
applicant tracking system (résumé-parsing software employers run
on incoming files).

> **Purpose:** the high-level guide to what sartor. is, what
> it isn't, and the self-imposed constraints that shape every
> decision. The "why" behind the architecture and the product
> shape.
> **Audience:** humans evaluating whether to use or contribute
> to sartor.; LLM agents proposing significant changes who
> need to check their proposal against the project's stance.
> **Authoritative for:** the product's intent, the 10 Principles
> grounding, the open / standards / minimal-dependencies stance,
> what counts as in vs out of scope for v1.x. Sibling docs:
> [`docs/PRODUCT_SHAPE.md`](docs/PRODUCT_SHAPE.md) (architecture
> details + sequencing ladder), [`docs/architecture.md`](docs/architecture.md)
> (module map + diagrams), [`AGENTS.md`](AGENTS.md) (operational
> contract for AI agents and human contributors), [`README.md`](README.md)
> (user-facing overview).

---

## What it is

It's a single-tenant local-first web app that takes a job
description and a candidate's career corpus, then produces a
tailored résumé using the Claude API. Everything lives on the
candidate's own machine. Nothing leaves it except the LLM
calls themselves.

It is **not** an applicant tracking system, a job board, a
LinkedIn scraper, a multi-tenant SaaS, or a generic résumé
template generator. The scope is narrow on purpose: one
person, one machine, one job at a time.

"One person, one machine, one job at a time" is the *unit of
work*, not an exclusion of readers. sartor. admits a
continuum of audiences: the everyday job-seeker; the **power
user** who reads the diagnostics and tunes prompts; the
**developer / builder** who extends it; and — the reason
ATS-safety is goal 2 — the applicant **blocked by an ATS**
whose résumé never reaches a human until it parses cleanly.
The tool's surfaces are written to be legible to all of them.

---

## What it's trying to accomplish

Three goals, in order of priority:

1. **Honest tailoring.** A grounding check in the generate
   prompt — backed by the eval harness's `grounding_overlap`
   witness metric — holds every bullet, title, and summary to
   what traces back to either (a) the candidate's existing
   corpus or (b) a first-person clarification they typed. It
   measures and constrains; it is not a categorical guarantee
   the LLM can't invent.

2. **ATS-safe output by default.** Most applications are
   parsed by software before any human sees them. sartor.
   ships templates that are single-column, plain-bullet, in
   standard fonts, with no tables / text boxes / icons / sidebars.
   Templates that *aren't* ATS-safe are retired — even when
   they look prettier. The escape hatch is the user's, not the
   tool's: anyone who wants a non-ATS design edits the document
   sartor. produced. See
   [`docs/PRODUCT_SHAPE.md §5.3`](docs/PRODUCT_SHAPE.md) for
   the bundled-template curation rationale.

3. **The candidate stays in control.** Two required human
   review gates (analyze review + post-generation refinement)
   plus optional clarification interviews between them. The
   user can edit anything before downloading. The LLM never
   submits an application or sends an email — only produces a
   document the user then chooses what to do with.

---

## Self-imposed constraints

These are the lines sartor. won't cross, even when crossing
them would be convenient. Together they define what kind of
software this is.

> **Canonical governance.** The *binding* form of these constraints — the
> C-0…C-6 clauses, the D-1…D-6 defaults, and the working-model rules — now
> lives in [`docs/governance/charter.md`](docs/governance/charter.md). This
> section keeps the *why* and the worked detail; the charter states each rule
> once and is the home audits and gates read against. Where a line below
> restates a rule, the charter governs on conflict.

### Local-first, single-tenant

"Single-tenant" here is a **threat-model boundary, not a product
value**: sartor. trusts exactly one unauthenticated user — the
person who owns the machine — and leans on the OS for access
control. Local *multi-profile* support (several candidates on one
machine, via `list_users()`) is convenience inside that single
trust boundary; it is not multi-tenancy.

- The Flask server binds to `127.0.0.1:5000` only. There is
  no auth, no CSRF, no rate-limit, no multi-user logic. The
  threat model assumes the user owns the machine.
- All artifacts (configs, résumés, generated documents,
  iteration history, LLM call logs) stay on disk in the repo
  root. Gitignored. Never uploaded.
- The ONLY network calls are: (a) the Anthropic API, (b) the
  optional LinkedIn / portfolio URL scrape if the user opts in.
  No telemetry, no analytics, no error reporting, no
  third-party CDN fetches at runtime — see
  [`SECURITY.md`](SECURITY.md) for the full disclosure.

### Open standards over proprietary formats

- **JSON Resume v1.0** as the canonical intermediate. The LLM
  emits Markdown; a deterministic post-pass lifts it into JSON
  Resume; renderers consume the JSON Resume. This means
  sartor.'s structured candidate data is portable to any
  jsonresume.org-compatible tool.
- **Standard fonts only** in the bundled templates: Arial,
  Calibri, Georgia, Helvetica, Roboto, Times New Roman. No
  font hosting, no Google Fonts at runtime, no `@font-face`
  with custom files. The PDF renders offline.
- **MIT-compatible licensing throughout.** Vendored
  dependencies (paged.js, jsonresume-theme-class adaptations)
  preserve their MIT headers. Bundled templates inspired by
  community jsonresume themes credit the upstream by name.

### Minimal dependencies, audited surface

The dependency list is intentionally short
([`pyproject.toml`](pyproject.toml)):

- Flask + SQLAlchemy + Alembic (the web/persistence layer)
- Anthropic Python SDK (the only LLM client)
- python-docx + pdfplumber + Playwright (parsing + rendering)
- beautifulsoup4 + requests (the scraper)
- markdown (rendering preview HTML)

Adding a dependency requires a `pyproject.toml` update AND a
CHANGELOG entry. The bar is "this could not be reasonably
implemented in pure Python or with an existing dep." See
[`CONTRIBUTING.md`](CONTRIBUTING.md).

### Deterministic where possible; LLM only for fuzzy work

This is **P1 Hardening** from the [10 Principles framework](https://jdforsythe.github.io/10-principles/overview/).
Per-file responsibility:

- `hardening.py`, `parser.py`, `generator.py`, `scraper.py`,
  `json_resume.py`, `corpus_to_json_resume.py`,
  `pdf_render.py` — **no LLM calls allowed**. These are the
  deterministic core: file I/O, keyword extraction, ATS
  format checks, document rendering, schema transformations.
- `analyzer.py` — the only module that calls the LLM. Every
  call has a stated `call_kind`, a model assignment (Sonnet
  4.6 for heavy reasoning; Haiku 4.5 for structured
  selection), and a logged cost. The prompt set is
  versioned via `PROMPT_VERSION` so the eval dashboard can
  attribute behavior to specific prompt revisions.
- `app.py` — Flask routes only; never originates LLM calls;
  always proxies through `analyzer.py`.

The deterministic boundary is enforced by tests
(`tests/test_response_validation.py`,
`tests/test_safe_username_within.py`) and by the
`route-security-lint` hook.

### Grounding mechanism, not a guarantee

Three layers of best-effort defense against LLM hallucination:

1. **The SYSTEM_PROMPT carries an explicit no-invention rule**
   with worked examples (OK / NOT OK pairs) for the failure
   modes we've actually observed in real runs.
2. **Clarifications widen ground truth surgically.** When the
   user provides first-person clarification text, the LLM
   treats it as citable ground truth — but the no-invention
   rule still applies beyond the union of (résumé +
   clarifications + typed edits).
3. **The eval harness's `grounding_overlap` metric** measures
   whether the output's tri-grams overlap the input corpus
   above a threshold. Below threshold = regression alert in
   the dashboard.

### Auditable iterations

Every `/api/generate` writes a NEW timestamped child context
file rather than mutating the parent. The `parent_context_path`
chain forms the iteration audit trail. A user (or a developer
debugging an issue) can always trace what the LLM saw at each
step.

---

## Principles backbone

sartor. follows the [10 Principles framework](https://jdforsythe.github.io/10-principles/overview/).
The codebase is annotated with principle references (P1, P2,
P5, P6, P8, P9) where they apply. Five principles are
load-bearing for sartor. specifically:

- **P1 Hardening** — deterministic Python for mechanical
  work, LLM only for fuzzy reasoning. Drives the file
  boundary above.
- **P2 Context Hygiene** — `context_set` is the structured
  JSON contract between stages. Iteration state is
  `total=False` so pre-iteration files round-trip safely.
- **P5 Institutional Memory** — ALWAYS / NEVER BECAUSE rules
  in `analyzer.py:SYSTEM_PROMPT`; tuning history in
  `evals/TUNING_LOG.md`; release reasoning in
  [`docs/PRODUCT_SHAPE.md`](docs/PRODUCT_SHAPE.md).
- **P8 Human Gates** — two required review checkpoints plus
  optional clarification interviews. Skipping any clarification
  step does not degrade output below the prior behavior.
- **P9 Observability** — JSONL telemetry per LLM call (model,
  tokens, latency, cost) in `logs/llm_calls.jsonl`; read-only
  dashboard at `/_dashboard` aggregates trends.

These are not decoration. When a proposed change conflicts
with one, the proposal usually loses.

---

## Learnings + direction

This section is the project's running record of what we
discovered as we built. Updated as new learnings land.

### The Corpus Item asymmetry (v1.0 unified pattern)

The first version of sartor. treated `Bullet` as the only
first-class curatable element — it had its own table, variants,
tags, scores, pin-per-application logic, and a Haiku
`recommend_bullets` LLM call. Everything else (summaries,
skills, titles, cover letter content) was either a freeform
text column on the parent or generated fresh each time.

This asymmetry meant the LLM couldn't help the user pick the
best summary variant the way it could pick the best bullets,
and the user couldn't pin a great summary across similar
applications. v1.0 introduced `SummaryItem` as the second
specialization of an emerging "Corpus Item" base concept.
[`docs/PRODUCT_SHAPE.md`](docs/PRODUCT_SHAPE.md) covers the
full pattern and the v1.1 / v1.2 plan to extend it to
`ExperienceSummaryItem`, `SkillGroupItem`,
`CoverLetterChunkItem`.

### PDF rendering: WeasyPrint → Playwright

Initial implementation used WeasyPrint (pure-Python HTML→PDF,
no system deps). On Windows it required GTK3/Pango at the OS
level despite pip-install. The honest answer was to switch to
Playwright + headless Chromium: ~150 MB one-time download to
the OS user cache (not in the repo), but works identically
across Windows / macOS / Linux. The renderer pairs naturally
with the in-browser preview, which uses the same HTML.

### Cover letters are optional

Empirically, the user almost never sends one. Earlier versions
generated a résumé + cover letter together on every
`/api/generate` call. v1.0 detached the cover letter to a
dedicated `/api/generate-cover-letter` route, gated behind a
single "+ Generate cover letter" button. Saves about $0.05
per typical application by skipping the unwanted call.

### ATS-safety is the product

v1.0 shipped with 5 bundled templates. Two of them
(Compact's sidebar layout; Hybrid Tech's inline `<code>`
chips) turned out to be ATS-unsafe — they broke parser
expectations in subtle ways. Both retired. The bundled set is
now 4 templates, all single-column, all using standard fonts,
all explicitly tested against ATS rules. The Template-step UI
now badges each card with its ATS status. Templates that look
prettier but don't parse don't ship.

### The analyze step is the latency floor

`analyze` is the slowest call on the critical path (p50 ~90s
on Sonnet 4.6 for ~4500 output tokens). Two v1.1 optimizations
are queued: streaming the response so perceived latency drops
to 10-15s, and splitting the call into a Haiku-fast first
pass (structured JD fields) + Sonnet-deep second pass (prose
analysis). See [`docs/dev/perf/PERF_ANALYZE.md`](docs/dev/perf/PERF_ANALYZE.md)
(dev-facing) for the audit.

---

## What's out of scope

Listed explicitly so future feature proposals can check
themselves:

- **Multi-user / multi-tenant** — there is no per-user
  authentication or data isolation; the single-unauthenticated-user
  threat model is the boundary (the OS owns access control). Local
  multi-*profile* support is not multi-tenancy. Adding auth /
  isolation would change the threat model fundamentally; we won't.
- **Auto-apply** — the LLM produces documents; it doesn't
  submit them. There is no "click to send to LinkedIn"
  affordance and there won't be.
- **Job-board scraping** — the candidate pastes one JD at a
  time. We don't iterate over job boards, we don't queue
  applications, we don't watch postings.
- **Generic résumé templates / themes / marketplace** — the
  4 bundled ATS-safe templates exist to support the tailoring
  loop. Adding more (user-uploaded) is supported. Building a
  template marketplace is not.
- **Telemetry, analytics, error reporting to a server** —
  see [`SECURITY.md`](SECURITY.md). Local-only by design.

---

## Working agreement with AI agents

If you're an AI coding agent (Claude Code, Cursor, Codex,
Continue, Aider, etc.) reading this file to propose changes:

- Check your proposal against the **Self-imposed constraints**
  section above. If it conflicts with one, default to "no" or
  ask the user.
- The **operational contract** lives in
  [`AGENTS.md`](AGENTS.md) — branch conventions, security
  guardrails, the ruff + mypy + pytest gate, what NOT to do.
  Claude-Code-specific overrides are in
  [`CLAUDE.md`](CLAUDE.md), which imports AGENTS.md.
- Document new learnings in the **Learnings + direction**
  section above as they emerge. This file should grow over
  the project's lifetime — it's the running record of why
  sartor. looks the way it does.
