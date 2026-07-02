# System model — sartor.

> **Purpose:** the canonical self-model of the whole repository — not the code
> architecture (that is [`architecture.md`](architecture.md)), but the *shape of the
> entire system*: seven functions, one dependency law, and the split between **the
> Product you run** and **the Work that evolves it**. One page that lets a reader —
> human or LLM — place any file in the repo and know what it is *for*.
> **Audience:** humans meeting the project (portfolio / open-source / contributors);
> LLM agents orienting before a change. Written to read plainly to a well-informed
> layman and to ground the agent's mental map.
> **Authoritative for:** the seven-functions vocabulary
> (Substrate · Production · Evaluation · Operation · Memory · Regulation ·
> Governance), the one-way dependency law, and the Product / Work split. The short
> version in [`PRODUCT_SHAPE.md`](PRODUCT_SHAPE.md) §11 defers to this doc.
> Sibling docs:
> [`architecture.md`](architecture.md) (the code-level module map + LLM routing),
> [`PRODUCT_SHAPE.md`](PRODUCT_SHAPE.md) (product-data-model intent),
> [`vision.md`](../vision.md) + the 10 Principles (the Governance north-star),
> [`dev/excellence-walk/`](dev/excellence-walk/) (the preserved reasoning this was
> distilled from).
>
> This doc is the **seed for the WS-4 wiki `overview.md`**; ingesting it into the
> wiki is a later branch ([`dev/RELEASE_ARC.md`](dev/RELEASE_ARC.md) §Phase 4.5),
> not this one.

---

## What it is

sartor. is a local-first app that tailors your résumé — and, optionally, a cover
letter — to a specific job, **grounded in what's actually true about you, not
invented**. You paste in a job description; it reads the posting, asks a few sharp
questions, helps you choose which of your real accomplishments fit, then writes a
tailored draft grounded entirely in your actual history and renders it to Word or
PDF. It runs on your own machine; your career data never leaves it, apart from the
calls to the AI model that does the writing.

The thing that makes it trustworthy is a rule it holds itself to: it may
**select, rephrase, and emphasize** what is already true about you, but it is built
**not to fabricate** — no invented titles, numbers, or dates. A grounding check in the
generation prompt enforces that rule and a witness metric measures whether it held — a
constraint on the model, not a guarantee about every output. That single constraint
shapes the entire design, and it recurs at every scale of the system below.

## Two subjects: the Product and the Work

There are really two things in this repository, and telling them apart is the key to
reading the whole project:

- **The Product** — what the user runs. Two functions: **Production** (the pipeline)
  over its **Substrate** (your material).
- **The Work** — everything that produces the Product and keeps it improving:
  **Evaluation**, **Operation**, **Memory**, and **Regulation**. Remove the Work and
  the Product still *runs* — but no one could safely change it, and the agent could
  not navigate it. So the Work is load-bearing *for the Work of evolving the Product*,
  not for the Product at runtime.

Above both sits **Governance** — the written intent the Work answers to. The most
unusual thing about the project is that **the Work is engineered as deliberately as
the Product**, with an AI coding agent treated as a first-class inhabitant of it.

## The seven functions

### Substrate — the material
The stored state the product reads and writes: your career history, the job
descriptions you feed it, the documents it produces, and the per-iteration
`context_*.json` audit trail. It stays on your machine. *(Lives in: `configs/`,
`resumes/`, `output/`, `db/resume.sqlite`.)*

### Production — synthesizes the output *(this is the Product)*
The pipeline that does the work: read the job → ask clarifying questions → recommend
your strongest material → generate the tailored draft → let you refine it.
**Everything that talks to the AI is isolated in one place** (`analyzer.py`);
everything that must be exact and repeatable — parsing files, rendering the document,
checking that nothing was fabricated — is kept deliberately *away* from the AI, in
plain deterministic code. *(Lives in: `app.py` web layer · `analyzer.py` — **all** AI
calls · the deterministic core `hardening.py` / `generator.py` / `parser.py` /
`pdf_render.py` / `json_resume.py` · `db/` · `personas/` · the frontend.)*

### Evaluation — measures, verifies, improves Production
How the project knows the Product is actually good: an automated test suite, plus a
measurement harness that scores the AI's output on quality and flags any change that
makes things worse. It is **active**, not passive — when it finds a weakness it drives
the fix. *(Lives in: `tests/`, `evals/`, `dashboard/`, the build/perf `scripts/`.)*

### Operation — the active labor that builds and reshapes
The people and assistants who change the system. Notably, **AI coding agents are
first-class contributors here** — much of the work is done by agents working under
strict, mechanically-enforced rules. *(Lives in: `commands/` +
`agents/`; the human + AI operators; the operating contract in
[`../AGENTS.md`](../AGENTS.md) / [`../CLAUDE.md`](../CLAUDE.md).)*

### Memory — recallable knowledge and rules
The project's drawn-upon knowledge: the documentation, the design rationale, and the
contributor contract that both humans and AI read *before* changing anything. It is
pulled when needed, not pushed. *(Lives in: `docs/`, `CHANGELOG.md`, and the planned
knowledge wiki.)*

### Regulation — gates, enforces, advances
The rules, enforced by machines rather than by vigilance: automated checks that block
unsafe changes (leaked secrets, missing security guards, edits on the wrong branch)
and a release discipline that gates what ships. *(Lives in: `.claude-plugin/hooks/`,
the `ruff` + `mypy` + `pytest` quality gate, the branch/release discipline in
[`dev/RELEASE_ARC.md`](dev/RELEASE_ARC.md) / [`dev/RELEASE_CHECKLIST.md`](dev/RELEASE_CHECKLIST.md).)*

### Governance — the north-star answered to
The written vision and the set of principles stating what sartor. is *for* and what
it must never do. Everything else is measured against this. **Honest seam:** this is
the one layer that is deliberately **prescribed** rather than emergent — it is the
human intent the rest is held to, not something the system discovers on its own.
*(Lives in: [`vision.md`](../vision.md) and the 10 Principles.)*

## The one law

> **Every dependency points inward toward Production; Production answers only upward
> to Governance.**

This is not an imported metaphor — it is **the codebase's own internal rule, scaled
up to the whole system**. Inside the code, dependencies already point one way and
never reverse: the deterministic core never calls the AI (`hardening.py` ↛
`analyzer.py`), the AI layer never reaches into the web layer (`analyzer.py` ↛
`app.py`), and Production never depends on the tooling that tests it (production ↛
`evals/`). The whole-system model obeys the *same* one-way law — which is exactly why
it maps so cleanly onto what is already there: the seven functions inherit the
architecture's own dependency discipline. You can always remove an outer layer of the
Work and the Product still stands on its own; you can remove the Product's AI brain
and the deterministic core still runs. That discipline is why the codebase stays
navigable as it grows.

## Where it lives

| Function | In the repo |
|---|---|
| **Substrate** | `configs/`, `resumes/`, `output/`, `db/resume.sqlite` |
| **Production** | `app.py` (web layer) · `analyzer.py` (**all** AI calls) · the deterministic core `hardening.py` / `generator.py` / `parser.py` / `pdf_render.py` / `json_resume.py` · `db/` |
| **Evaluation** | `tests/` · `evals/` · `dashboard/` |
| **Operation** | `commands/` + `agents/` · [`../AGENTS.md`](../AGENTS.md) / [`../CLAUDE.md`](../CLAUDE.md) (the operating contract) |
| **Memory** | `docs/` · `CHANGELOG.md` · (the planned knowledge wiki) |
| **Regulation** | `.claude-plugin/hooks/` · the `ruff` + `mypy` + `pytest` gate · [`dev/RELEASE_ARC.md`](dev/RELEASE_ARC.md) / [`dev/RELEASE_CHECKLIST.md`](dev/RELEASE_CHECKLIST.md) |
| **Governance** | [`vision.md`](../vision.md) · the 10 Principles |

> **Self-similarity worth naming:** the *Product* is a grounding-and-synthesis engine
> (raw history → tailored draft, no invention). The constitutional discipline of the
> *Work* is the same move at a larger scale — the descriptive layers (code, synthesized
> docs) may not drift beyond what the prescriptive Governance layer sanctions. The
> product's own grounding contract, turned on the project itself.

---

## Open revision points (raised 2026-06-07, not yet resolved — carry into the wiki `overview.md` refinement)

These four were flagged when the source draft ([`dev/excellence-walk/q1-overview.md`](dev/excellence-walk/q1-overview.md))
was written and are **deliberately not resolved here** — they are framing calls best
settled when this doc seeds the wiki `overview.md`. Recorded so they are not silently
dropped.

1. **The Governance honesty note.** This doc keeps the seam visible ("deliberately
   prescribed rather than emergent"). For a portfolio audience: strength
   (self-awareness) or distraction? *Author lean: keep.*
2. **The "AI agents are first-class contributors" line** (emphasized in two places).
   A distinctive showcase hook, but could invite skepticism. Dial up / down / leave?
3. **The "Where it lives" file map.** Right for an overview, or too technical for the
   portfolio reader — split into a linked sibling doc?
4. **The opening.** Lead with the grounding / no-fabrication promise (as it does
   now), or lead with the *problem* (the pain of hand-tailoring résumés)?

---

## Provenance

Distilled from the **settled** output of the 2026-06-07 "excellence walk" — the
seven-functions vocabulary and the one law were form-found and user-locked there:

- [`dev/excellence-walk/excellence-walk.md`](dev/excellence-walk/excellence-walk.md)
  — the SETTLED seven-functions table + the one law + the Product/Work split.
- [`dev/excellence-walk/q1-overview.md`](dev/excellence-walk/q1-overview.md) — the
  layered layman draft this prose tightens, and the source of the four revision
  points above.
- [`PRODUCT_SHAPE.md`](PRODUCT_SHAPE.md) §11 — the one-paragraph summary that defers
  to this canonical write-up.

Scheduling for the WS-4 knowledge substrate that this seeds lives in
[`dev/RELEASE_ARC.md`](dev/RELEASE_ARC.md) §Phase 4.5.
