# 00 — System Map

> The whole product at a glance, so the persona walkthroughs have a shared
> frame. Everything here was confirmed against the running app and the code.

## What sartor. is

sartor. is a local-first résumé-tailoring web app. Instead of editing a Word
file per application, you build a **career corpus** once — a structured store of
your experiences, bullets, titles, skills, and summary variants — and then, for
each job, the app analyzes the posting against your corpus, helps you compose a
targeted selection, and renders a résumé (and optional cover letter) through an
ATS-safe template. It runs on your machine; your data stays in local files and a
local SQLite DB.

It targets three users, in widening order of technical depth:

- **Job seeker** — the primary user. Imports a résumé, tailors it per job,
  downloads polished documents.
- **Headhunter / coach** — manages several candidates, each as a separate
  "user," and tailors on their behalf.
- **Technical user** — self-hosts, extends, or contributes. Lives in the eval
  harness, the diagnostics dashboard, the Claude-Code plugin, and the docs/wiki.

## Information architecture

The shell is a single page with a top bar and four section tabs.

- **Top bar**: the `sartor.` wordmark (routes home), a **search/assistant**
  magnifier pill (opens the doc-grounded assistant), a **Settings** pill (profile
  drawer + diagnostics link), a **Diagnostics** link (to `/_dashboard`), and a
  live **status pill** (Ready / Analyzing / Generation complete / error).
- **Four tabs**: **Career corpus**, **Tailor** (default), **Résumé templates**,
  **Candidate memory**.
- **The wizard** lives inside the Tailor tab: a 6-step rail
  (Job+Analyze → Clarify → Compose → Template → Generate → Download). Above it on
  the Tailor tab sit the **User Selection** panel and the **Prior Applications**
  list.
- **Separate app**: `/_dashboard` — the read-only diagnostics console (localhost
  only), with its own five tabs.

## The pipeline, step by step (and where the LLM actually runs)

This is the spine of the product. The important, non-obvious fact — confirmed
from live call telemetry — is that **the LLM work is front-loaded into Analyze
and Compose; the final Generate step in the UI is deterministic assembly.**

| Step | What happens | LLM calls (observed) | Model |
|---|---|---|---|
| **1. Job + Analyze** | Paste a JD; the app analyzes it against the corpus and renders fit, matched/missing keywords, gaps, per-experience suggestions, and a strategy. Creates an Application + Run. | `analyze_extraction` then `analyze_synthesis` (two-phase) | Haiku → **Sonnet** |
| **2. Clarify** | Optional. The app asks 3–5 targeted interview questions to surface facts not in the résumé; answers persist to candidate memory. | `clarify` | Haiku |
| **3. Compose** | The heart of tailoring: fit-ranked bullets (pin/exclude/reorder), a per-JD title, a drafted positioning summary, a skills card, and **gap-fill** — grounded NEW bullets for uncovered JD requirements, each shown with "Covers: …". | `recommend`, `draft_summary`, `draft_gap_fill` (+ `recommend_skills`, `recommend_experience_summaries` when used) | Haiku + **Sonnet** |
| **4. Template** | Pick one of 4 bundled ATS-safe templates (or an uploaded `.docx`); a live, paginated WYSIWYG preview shows exactly what the PDF will render. | none | — |
| **5. Generate** | Choose format (DOCX / PDF / Markdown) and generate. On the happy path (a frozen composition exists) the **résumé body is assembled deterministically** — no LLM call; a legacy fallback still calls the LLM when no frozen composition is present. | none for the body on the happy path (`generation.py:585-603`) | — |
| **6. Download** | Preview the result, edit inline, refine (a scoped content adjustment), generate a cover letter, ask post-generation follow-up questions, download, and mark submitted. | `generate_cover_letter` on demand; `iterate_clarify` on demand | Sonnet / Haiku |

Two consequences worth stating plainly:

- **Output is reproducible.** Because the résumé body is assembled
  deterministically from a frozen snapshot (`generation.py:585-603`,
  `_frozen_composition`), the same composition renders the same document every
  time. This is a real strength — but the UI never tells the user, so it reads
  like any other "generate" button. (Carve-outs: a legacy path still calls
  `analyzer.generate()` when no frozen composition exists, and the cover letter is
  always a separate LLM call.)
- **The eval harness tests a different generation path.** `evals/runner.py` runs
  `analyze → clarify → generate` where `generate` **is** a real LLM call
  (~27 s, confirmed in a smoke run) — i.e. it exercises the fallback
  `analyzer.generate()` path, not the frozen-composition assembly the primary UI
  uses. The eval numbers are still meaningful for prompt quality, but they do not
  measure what a user actually downloads on the happy path. (See F-11.)

## The complete surface — every path and tool

### Web routes (grouped by blueprint)

The full route table with file anchors lives in the surface inventory; the
grouping:

- **`users`** — SPA shell, user CRUD, profile config, opt-in profile scrape.
- **`analysis`** — analyze (+ SSE stream), clarify, answer-clarifications,
  iterate-clarify.
- **`generation`** — save-edits, generate (+ SSE stream), validate-refinement,
  generate-cover-letter, download, download-edited.
- **`templates`** — bundled + user personas (list/upload/rename/default/delete/
  download/preview), the résumé WYSIWYG preview, the cover-letter preview.
- **`applications`** — the tracker (list/detail/status/notes/meta/retire/
  restore) and the whole **Compose** engine (composition read/save, recommend,
  recommend-summary, draft-summary, draft-gap-fill, gap-fill-decide,
  recommend-experience-summaries, recommend-skills, suggest-skills) plus the
  candidate-memory list.
- **`corpus/*`** (~42 routes) — experiences/bullets/titles/summaries/skills/tags
  CRUD, duplicate-role **merge**, resume upload + **ingest**, accept-pending
  flows, proposal **critique/decide**, promote-clarification-to-bullet.
- **`assistant`** — the doc-grounded Q&A (SSE, cited).
- **`diagnostics`** — the annotation/eval/tune write+SSE surface (localhost).
- **`dashboard`** (`/_dashboard`) — read-only telemetry (localhost).

### Technical tools

- **Eval harness** — `evals/runner.py` (`--suite synthetic|real|anchor`,
  `--subset smoke`, `--prompt-overrides`, `--seed`, `--grounding-signals`),
  8 rubrics judged by Haiku, results as JSONL + a composite, baseline regression
  alerting.
- **Diagnostics dashboard** — `/_dashboard`: Pipeline / Quality / Groundedness /
  Tuning / Annotate.
- **CLI + scripts** — `sartor`/`python app.py`, `sartor --setup`,
  `scripts/` (screenshots, seed export, vector index, bundled templates, perf).
- **Claude-Code plugin** — 12 slash commands + 9 subagents (eval, tune, wiki,
  compliance-witness, …) loaded via a local marketplace.
- **Docs system** — README/AGENTS/CONTRIBUTING/SECURITY/vision, `docs/`
  (architecture, product-shape, governance charter, diagrams), and a 36-page
  compiled **wiki** (24 dev / 12 user audience) with a self-updating loop.

## Data model (one paragraph)

A **Candidate** owns **Experiences**, each with **Bullets**, **ExperienceTitles**,
and per-role **ExperienceSummaryItems**; the candidate also owns candidate-level
**SummaryItems** (positioning variants), **Skills**, and **Tags**. Every
tailoring run is an **Application** with **ApplicationRuns** (the iteration audit
chain). Nothing is hard-deleted — retire sets `is_active=0` to preserve audit
foreign keys. The JSON `context_set` is the contract passed between pipeline
stages; each generate writes a new timestamped child, and the
`parent_context_path` chain is the iteration trail. Education and certifications
are the exception: backing DB tables exist (`db/models.py` `Education`,
`Certification`) and are read for context, but they have **no corpus panel or
CRUD** — they are edited only as flat free-text fields in the Settings drawer
(see F-04).

## Where each persona enters

- **Job seeker**: lands on Tailor → (empty corpus) is routed to Career corpus to
  import → back to Tailor to run the wizard. Documented in
  [10-job-seeker.md](10-job-seeker.md).
- **Headhunter**: creates one "user" per candidate, switches between them via the
  User Selection dropdown; otherwise the same flows. Documented in
  [20-headhunter.md](20-headhunter.md).
- **Technical user**: never needs the wizard first — starts at the README, the
  dashboard, or the eval harness. Documented in
  [30-technical-user.md](30-technical-user.md).

**📸 Screenshot (system map):** The empty first-run state — dark UI, `sartor.`
wordmark top-left, the four section tabs (Career corpus / Tailor / Résumé
templates / Candidate memory), the "USER SELECTION" panel with an empty
"— Select User —" dropdown and an amber "New user" button, and the amber-bordered
"Welcome to sartor" modal centered over it reading "sartor tailors your résumé to
a specific job from a career corpus it builds out of your past résumés." Use this
as the one-image "what is this" hero.
