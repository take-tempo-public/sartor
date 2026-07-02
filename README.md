# Sartor

> **Purpose:** the product front door — what Sartor is, who it's for, and where to go deeper. Also the home page the hosted docs site renders.
> **Audience:** `user` — the one place all three audiences (job seeker · coach · developer) meet; routes developers onward to the dev-tier homes.
> **Authoritative for:** the product positioning, the three-audience cumulative ladder, and at-a-glance orientation + the documentation map. Everything else is **cited**; the linked canonical home governs on conflict.

> Tailor a résumé — and an optional cover letter — to **one** specific job, on your own machine, without inventing anything about the candidate.

**Sartor** is a local-first web app that takes a single job description and a person's real career history, then produces a tailored draft — by *discovering* what's true about them (including real experience left off the résumé, surfaced through a short interview in their own words) and *phrasing* it for the posting. It runs on your laptop and calls the Claude API for the reasoning; nothing else leaves your machine. It produces documents — it never submits an application or sends an email.

The core discipline: **the LLM discovers and phrases — it does not invent.** No fabricated titles, numbers, or dates. A grounding check in the prompt plus a deterministic "witness" metric measure how much of the output traces back to real material. That's a *mechanism and a constraint*, **not** a guarantee a language model can never hallucinate — the full rationale lives in [`vision.md`](vision.md).

<!-- PLACEHOLDER: badges row (CI · license · Python versions) -->

> **Documentation map.** This README orients; the depth lives in single-home docs:
> [`vision.md`](vision.md) (intent + scope) ·
> [`docs/install.md`](docs/install.md) (install + first run) ·
> [`docs/walkthrough.md`](docs/walkthrough.md) (screen-by-screen) ·
> [`docs/architecture.md`](docs/architecture.md) (system + module map + diagrams) ·
> [`docs/PRODUCT_SHAPE.md`](docs/PRODUCT_SHAPE.md) (data model + roadmap ladder) ·
> [`docs/system-model.md`](docs/system-model.md) (the seven pillars + one law) ·
> [`docs/governance/`](docs/governance/) (the charter + enforcement) ·
> [`AGENTS.md`](AGENTS.md) / [`CLAUDE.md`](CLAUDE.md) (agent contract + tooling) ·
> [`CONTRIBUTING.md`](CONTRIBUTING.md) (dev loop) ·
> [`SECURITY.md`](SECURITY.md) (threat model) ·
> [`ACCESSIBILITY.md`](ACCESSIBILITY.md) (a11y status). The committed [`docs/wiki/`](docs/wiki/) is the synthesized, cited layer the docs assistant reads.

---

## What Sartor does

Generic AI résumé tools pad a history with claims that fall apart in an interview, and emit formats that automated résumé screeners (ATS) choke on. Sartor is the opposite bet:

- **It only asserts what's true.** It discovers real, undocumented experience — in the candidate's own words — then rewrites and synthesizes toward the job, without inventing.
- **It's ATS-safe by default.** Bundled templates are single-column, plain-bullet, standard-font. Non-ATS-safe templates were retired.
- **The human stays in control.** Two required review gates, plus optional clarifying interviews. It hands you documents (`.md` / `.docx` / `.pdf`); submitting is yours to do.
- **It builds a career corpus that compounds.** Import a résumé once and it becomes a structured, reusable body of experience; every clarifying answer, edit, and approved bullet is saved and improves the next résumé.

---

## Who it's for

Sartor does one thing — tailor the right résumé for one posting — but three audiences build on each other, each adding one capability to the tier below:

```
  Job seeker      Tailor YOUR résumé to one job, grounded in your real history.
    └─ + Coach     Do that for MANY people — a separate, persistent career file per client.
         └─ + Dev   EXTEND or TUNE what both experience — new features, better grounding.
```

Each tier gets everything the tier above it does. A coach is a job seeker with many career files and the tools to run them; a developer makes Sartor better at the job seeker's and the coach's work, or adds new capabilities to it.

| You are… | You build on… | …and add | Section |
|---|---|---|---|
| **A job seeker** | the core product | — | [For job seekers](#for-job-seekers) |
| **A coach / headhunter** | everything a job seeker gets | managing **many** candidates | [For coaches & headhunters](#for-coaches--headhunters) |
| **A developer** | everything both get | **extending & tuning** the tool itself | [For developers](#for-developers) |

---

## How it works

A sequence of small, inspectable stages — full sequence + diagrams in [`docs/architecture.md`](docs/architecture.md); stage detail in the wiki ([`pipeline-stages`](docs/wiki/pages/pipeline-stages.md)).

```
1. Job + Analyze   — paste the job description; the LLM reports skill match + ATS warnings
2. Clarify (opt)   — a short interview surfaces real-but-undocumented experience, in your own words
3. Compose         — pin / exclude / add bullets, pick the summary variant, curate skills (scored vs. the JD)
4. Template        — pick one of 4 ATS-safe templates with a live, paginated preview
5. Generate        — produce the tailored résumé (.docx, .pdf, or .md)
6. Download        — review, refine via natural-language notes, download
                     Optional: + generate a cover letter against the finalized résumé
```

**Two required human gates** bracket the work; the clarification interviews between them are optional and cheap. **Discover, don't invent:** output is grounded in the union of (corpus + clarifying answers + the candidate's own typed edits); a grounding check and a deterministic witness metric measure that it holds — see [`generation-and-grounding`](docs/wiki/pages/generation-and-grounding.md) and [`docs/dev/GROUNDING_METRIC.md`](docs/dev/GROUNDING_METRIC.md).

**Model routing** (canonical: [`docs/architecture.md`](docs/architecture.md) · [`llm-call-catalog`](docs/wiki/pages/llm-call-catalog.md)): heavy reasoning (analyze, clarify, generate, cover letter) runs on **Claude Sonnet**; structured selection (recommend, extract, critique) and the docs assistant run on **Claude Haiku**. Sartor's tailoring uses the **hosted Claude API only** — no fine-tuned generation model, nothing trained on your data. "Tuning" here means *prompt, eval, and retrieval* tuning, never model fine-tuning.

---

## For job seekers

**The core.** Tailor your own résumé to one specific posting, grounded in your real history. Walkthrough: [`docs/walkthrough.md`](docs/walkthrough.md).

- **Import once, then reuse.** Your résumé becomes a structured **career file** — experiences, bullets, summaries, skills — that every future application draws on and improves.
- **Tailor to one posting:** paste the JD → analyze fit + ATS warnings → two short clarifying interviews surface real experience you left off (in your own words) → curate the recommended bullets and summary → pick an ATS-safe template with a live preview → generate `.md` / `.docx` / `.pdf`.
- **Discover, don't invent.** New bullets and rewrites trace back to your corpus + your answers + your edits — a constraint you can check, not a promise an AI can never slip.
- **You stay in control.** Two required review gates; edit anything before downloading. It never submits or emails anything.
- **Runs on your machine**, on your own Anthropic key — a few cents per run, no subscription.

*The honest catch:* you run it yourself (Python + your own API key). A capable tool, not a one-click consumer app.

---

## For coaches & headhunters

**Everything a job seeker gets — but for every client you carry.** *(Résumé writers and in-house recruiters prepping candidates, too.)* The difference is **scale**: a job seeker manages one career file; you manage many, and your name is on every résumé you send.

**The new capability — managing many candidates.** Each client gets a **separate, persistent career file** you switch between, each compounding independently:
- its own **corpus** (experiences, bullets, summaries, skills);
- its own **interview memory** — every clarifying answer that client has ever given, saved and reusable across all their applications (see [`candidate-memory`](docs/wiki/pages/candidate-memory.md));
- its own **application history and outcome status** (draft → submitted → interview → rejected);
- its own **standing rules** it honors on every résumé for that client ("remote only," "never surface the 2020 gap").

**The professional layer that scale demands:**
- **Defensible output.** The grounding check + witness metric mean you're never sending a hiring manager fiction under your name.
- **ATS-safe → more clients past the parser → more placements.**
- **Better margin.** Cents of API usage instead of an hour of your time; ~5–10 minutes of your attention per résumé, dropping as each client's file fills out.
- **Client data stays on your machine** — no cloud service holding someone else's career history.

*Honest scope:* single-user by design — it's *you* running many client files locally, not a multi-seat agency platform with a shared team workspace. The threat model is in [`SECURITY.md`](SECURITY.md); the multi-profile-vs-multi-tenant line is in [`vision.md`](vision.md).

---

## For developers

**Everything the job seeker and coach experience — and the ability to change it.** Sartor is deliberately **two things at once**: a working résumé product, *and* a testbed for reusable, substrate-independent capacities (memory, governance, grounding, evaluation) engineered to be importable beyond this app. A developer doesn't use Sartor for a different purpose; you make it better at the other two's purposes, add new ones, or lift a capacity out. The canonical write-up is [`docs/system-model.md`](docs/system-model.md).

**One discipline, applied recursively.** "Discover/cite; never assert beyond source" governs the résumé generator, the doc-assistant avatar, *and this documentation itself* (the wiki may not assert beyond its cited sources; every fact has one home). The same `user`/`dev` audience plane the assistant gates disclosure on is the plane this documentation's navigation gates on — one mechanism, two consumers.

**Tune — change behavior without new features** (improves the grounding, recommendations, and tone the other two feel directly):
- an A/B prompt-override primitive (`/prompt-tune`, `/tune-from-annotations`) that tests a candidate prompt **without editing the live persona** — the default path stays byte-identical; candidate runs are quarantined from the score-over-time chart;
- an LLM-as-judge eval harness + deterministic metrics (the grounding witness, verb diversity, specificity, cost) with a regression gate — see [`eval-harness`](docs/wiki/pages/eval-harness.md), [`evals/TUNING_LOG.md`](evals/TUNING_LOG.md);
- `PROMPT_VERSION` discipline + a `/_dashboard` score-over-time view, so a regression is caught in testing.

**Extend — add new capability the other two then use:**
- the **Corpus Item** pattern — add new curatable kinds (same shape powers bullets, summaries, skills) — see [`docs/PRODUCT_SHAPE.md`](docs/PRODUCT_SHAPE.md);
- the **memory substrate** (`recall/`): hybrid retrieval (lexical `git grep` + curated wiki + session buffer + static-embedding semantic), fused with Reciprocal Rank Fusion, every retrieved unit carrying a mandatory `path:line` / `[[wiki]]` citation — behind a **machine-enforced extraction boundary** (an AST test fails the build if `recall/` imports the app or a Sartor-specific literal leaks into a retrieval tier, so "reusable substrate" is *enforced*, not narrated). See [`docs/dev/memory-architecture.md`](docs/dev/memory-architecture.md), [`deterministic-llm-boundary`](docs/wiki/pages/deterministic-llm-boundary.md);
- a deterministic core with **every LLM call quarantined to one module**, and **typed contracts as the seams between pillars** — pydantic is in the control loop (`model_validator`s enforce semantic rules; a validation failure is fed back as a structured retry), and frozen `Unit`/`Scope`/`Context` are the substrate's interface;
- new ATS-safe templates; the **JSON Resume v1.0** open intermediate; a roadmap **provider abstraction** at the single LLM boundary (local / alternative models).

*Note:* the résumé generator is **not** RAG — it assembles the whole corpus into the prompt. Retrieval-as-RAG is the doc-assistant's mechanism, not the generator's.

**Governed by construction.** Extensions stay trustworthy because the rules are machine-enforced — a written constitution, git hooks (secret-blocking, branch discipline, route-security, merge gates), a read-only compliance-witness agent, and the seven-pillar law (every dependency points inward to Production; Production answers only upward to Governance). In keeping with the project's own claims discipline (C-0), **two enforcement gates are openly flagged as still owed** — the C-1 loopback-bind test and the C-6 import-boundary lint, scheduled in **v1.0.8, before the public tag**; until the linter lands, the deterministic boundary holds "by convention, AST-verified," not yet fail-closed. Canonical: [`docs/governance/`](docs/governance/) (the owed-gates table is in [`enforcement.md`](docs/governance/enforcement.md)) · [`docs/system-model.md`](docs/system-model.md).
<!-- DOC-STATUS(governance-boundary): C-6 boundary is convention-only until the PX-20 import-linter (v1.0.8); C-1 bind is unpinned until PX-19 (v1.0.8). Remove this caveat when both gates land. Canonical: docs/governance/enforcement.md -->

---

## Architecture & developer reference

Pointers to the canonical homes; depth lives there, not here.

- **Deterministic boundary (P1).** Every LLM call is quarantined to `analyzer.py`; the rest of the core (`hardening.py`, `parser.py`, `generator.py`, `scraper.py`, `json_resume.py`, `corpus_to_json_resume.py`, `pdf_render.py`) is LLM-free by rule, enforced by tests + a route-security hook. Full map: [`docs/architecture.md`](docs/architecture.md).
- **Persistence.** A per-candidate SQLite corpus (SQLAlchemy 2.0 + Alembic); `Clarification` is cross-application memory; `Application` / `ApplicationRun` / `ProposalReview` persist every generation, edit, and human accept/reject. Schema home: `db/models.py` · [`corpus-data-model`](docs/wiki/pages/corpus-data-model.md).
- **Claude Code plugin** (catalog home: [`CLAUDE.md`](CLAUDE.md) · [`commands/`](commands/) · [`agents/`](agents/)):

  | Commands | Subagents |
  |---|---|
  | `/eval` · `/replay` · `/prompt-tune` · `/tune-from-annotations` · `/bench` · `/inspect-context` · `/wiki-*` · `/compliance-witness` | `eval-judge` · `prompt-archaeologist` · `tune-drafter` · `headhunter` · `git-flow` · `ux-onboarding-designer` · `wiki-scribe` · `wiki-grounding-auditor` · `compliance-witness` |

- **Tech stack.** Python + Flask (localhost-bound) · vanilla JS (no build step) · SQLAlchemy 2.0 + SQLite + Alembic · pydantic v2 · Playwright + headless Chromium (PDF) · JSON Resume v1.0. Detail: [`docs/architecture.md`](docs/architecture.md), `pyproject.toml`.
- **Dev loop** (canonical: [`CONTRIBUTING.md`](CONTRIBUTING.md)):
  ```bash
  ruff check . && mypy . && pytest        # the minimum bar; CI runs the same
  python evals/runner.py --suite synthetic --subset smoke   # grounding-only, ~$0.10
  ```

---

## Install

```bash
git clone https://github.com/take-tempo-public/sartor
cd sartor
pip install -e .
python -m playwright install chromium     # optional — one-time ~150 MB, only for PDF output
export ANTHROPIC_API_KEY=your-key-here     # or put it in a .api_key file at the repo root
python app.py
```
Then open `http://localhost:5000`. Full setup (Windows/macOS/Linux), cost guidance, and troubleshooting: [`docs/install.md`](docs/install.md). Cap spend via [Anthropic usage limits](https://console.anthropic.com/settings/limits) — Sartor has no built-in budget guard.

---

## What stays on your machine

Local-first: nothing leaves your computer except the Claude API calls (and the optional opt-in LinkedIn/portfolio scrape). This isn't only policy — it's **machine-verified**: a test (`tests/test_egress_allowlist.py`, green at HEAD) confines outbound traffic to exactly two sanctioned classes (the Anthropic API; the opt-in scrape) and fails the build if any module opens a socket elsewhere or a template references an off-box CDN. Configs, source résumés, generated output, the corpus DB, and per-call logs all live gitignored under the repo root. No telemetry, no analytics, no runtime third-party CDN. Full threat model + the file-by-file table: [`SECURITY.md`](SECURITY.md).
<!-- DOC-STATUS(egress): claim backed by tests/test_egress_allowlist.py (charter C-2, PX-08), green at HEAD; pinning the loopback bind in the same test is owed at v1.0.8 (PX-19). Canonical: SECURITY.md + docs/governance/enforcement.md. -->

---

## Status

At-a-glance snapshot — the authoritative schedule is [`docs/dev/RELEASE_ARC.md`](docs/dev/RELEASE_ARC.md) (+ [`docs/PRODUCT_SHAPE.md`](docs/PRODUCT_SHAPE.md)):

- ✅ **Shipped:** the tailoring pipeline, two-point clarifying interview, the compounding corpus (cross-application memory + human-gated curation), multiple persistent candidate profiles, grounding check + witness metric, ATS-safe templates, human gates, `.md`/`.docx`/`.pdf`, the recall substrate + doc-grounded avatar, and the eval/test stack.
- 🟡 **Governance — extracted & live, two boundary gates owed.** The constitution (charter C-0…C-6), the read-only compliance-witness auditor, and the enforcement hooks are shipped. **Two boundary gates are still owed** — the C-1 loopback-bind test (PX-19) and the C-6 import-boundary lint (PX-20) — **scheduled in v1.0.8, before the public v1.1.0 tag.** A further enforcement-hardening set (C-5 template assertions, the required UX/a11y CI job, supply-chain badges) lands with the v1.1.0 cut. *Snapshot — updated as those sprints close; canonical: [`enforcement.md`](docs/governance/enforcement.md).*
- 🚧 **In the codebase:** the static-embedding semantic search tier (local, no hosted DB).
- 🔭 **Roadmap:** outcome-weighted recommendations · master files per role · provider-agnostic / local models.
- ⛔ **Out of scope by design:** multi-user / multi-tenant (the threat model is a single trusted local user).
<!-- DOC-STATUS(governance): PROVISIONAL — update when: v1.0.8 lands PX-19 (C-1 loopback-bind test) + PX-20 (C-6 import-boundary gate, F-arch-01); v1.1.0 lands C-5 template-property assertions + the required UX/a11y/PDF CI job + the E-2 supply-chain badges. Canonical homes: docs/governance/enforcement.md (owed-gates table) + docs/dev/RELEASE_ARC.md (schedule). -->

---

## What it isn't

An ATS · a job board · a sourcing/scraping platform · an auto-apply bot · a multi-tenant SaaS. It never submits an application or sends an email. The scope is narrow on purpose — see [`vision.md`](vision.md) ("what's out of scope").

---

## License

<!-- PLACEHOLDER --> MIT — see [`LICENSE`](LICENSE).
