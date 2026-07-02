<!--
  TEMPORARY / UNTRACKED ARTIFACT — lives in output/ (gitignored), like the other
  excellence-walk scratch. Do NOT commit. This is the Q1 deliverable (draft v1),
  produced 2026-06-07. It will be fed into the planning process (RELEASE_ARC /
  PRODUCT_SHAPE integration) once the five-question walk is finished — and is a
  candidate to become the WS-4 wiki `docs/wiki/overview.md`.

  Decisions it was written under (see output/_dev-notes/excellence-walk.md):
   - Audience: MIXED / portfolio-facing (portfolio + open-source + personal tool).
   - Medium: LAYERED (overview.md candidate) — plain top → structure → file map.
   - Caveat: use ONLY the organization the ecology lens surfaced (the seven
     functions + the one-way dependency law + the Product/Work split). Do NOT
     import ecological vocabulary (no soil / metabolism / fauna). Plain, literal.
-->

# sartor. — what it is, and how it's built

*An overview for someone meeting the project for the first time.*

## What it is

sartor. is a local-first app that tailors your résumé — and, if you want, a
cover letter — to a specific job, **without inventing anything about you**. You
paste in a job description; it reads the posting, asks you a few sharp questions,
helps you choose which of your real accomplishments fit, then writes a tailored
draft grounded entirely in your actual history and renders it to Word or PDF. It
runs on your own machine; your career data never leaves it, apart from the calls
to the AI model that does the writing.

The thing that makes it trustworthy is a rule it enforces on itself: it may
**select, rephrase, and emphasize** what is already true about you, but it may not
**fabricate** — no invented titles, numbers, or dates. That single constraint
shapes the entire design.

## How it's organized

There are really two things in this repository: **the product you run**, and **the
work that produces it and keeps it improving**. Telling them apart is the key to
reading the whole project. Underneath both sits one rule — *dependencies only ever
point one way* — so you can always remove an outer layer and the inner one still
stands on its own.

**The Product** is two functions:

- **Production** — the pipeline that does the work: read the job → ask clarifying
  questions → recommend your strongest material → generate the tailored draft →
  let you refine it. Everything that talks to the AI is isolated in one place;
  everything that must be exact and repeatable — parsing your files, rendering the
  document, checking that nothing was fabricated — is kept deliberately *away* from
  the AI, in plain, predictable code.
- **Substrate** — your material: the career history it draws from, the job
  descriptions you feed it, and the documents it produces. The product reads and
  writes here; it's the raw stuff, and it stays on your machine.

**The Work** is everything that tends the Product:

- **Evaluation** — how the project knows the product is actually good: an automated
  test suite, plus a measurement harness that scores the AI's output on quality and
  flags any change that makes things worse. It isn't passive — when it finds a
  weakness, it drives the fix.
- **Operation** — the people and assistants who build and reshape it. Notably,
  **AI coding agents are first-class contributors here** — much of the work is done
  by agents working under strict, mechanically-enforced rules.
- **Memory** — the project's recallable knowledge: the documentation, the design
  rationale, and the contributor contract that both humans and AI read *before*
  changing anything. It's drawn on when needed, not pushed.
- **Regulation** — the rules, enforced by machines rather than by vigilance:
  automated checks that block unsafe changes (leaked secrets, missing security
  guards, edits on the wrong branch) and a release discipline that gates what ships.
- **Governance** — the north-star the whole thing answers to: a written vision and
  a set of principles stating what sartor. is *for* and what it must never do.
  Everything else is measured against this. *(Honestly: this is the one layer that
  is deliberately **prescribed** rather than emergent — it's the human intent the
  rest is held to.)*

## Where it lives

| Function | In the repo |
|---|---|
| **Substrate** | `configs/`, `resumes/`, `output/`, `db/resume.sqlite` |
| **Production** | `app.py` (web layer) · `analyzer.py` (**all** AI calls) · the deterministic core `hardening.py` / `generator.py` / `parser.py` / `pdf_render.py` / `json_resume.py` · `db/` |
| **Evaluation** | `tests/` · `evals/` · `dashboard/` |
| **Operation** | `.claude-plugin/commands/` + `agents/` · `AGENTS.md` / `CLAUDE.md` (the operating contract) |
| **Memory** | `docs/` · `CHANGELOG.md` · (the planned knowledge wiki) |
| **Regulation** | `.claude-plugin/hooks/` · the `ruff` + `mypy` + `pytest` gate · `RELEASE_ARC.md` / `RELEASE_CHECKLIST.md` |
| **Governance** | `vision.md` · the 10 Principles |

The one-way rule shows up at every level: the exact, deterministic core never calls
the AI; the AI layer never reaches into the web layer; the product never depends on
the tooling that tests it. That discipline is why the codebase stays navigable as
it grows — and the most unusual thing about it is that **the Work is engineered as
deliberately as the Product**, with an AI agent treated as a first-class inhabitant
of it.

---

## Open revision points (raised 2026-06-07, not yet resolved — carry into refinement)

1. **The Governance honesty note.** Draft keeps the seam visible ("deliberately
   prescribed rather than emergent"). For a portfolio audience: strength
   (self-awareness) or distraction? *Author lean: keep.*
2. **The "AI agents are first-class contributors" line** (emphasized twice). A
   distinctive showcase hook, but could invite skepticism. Dial up / down / leave?
3. **Layer 3 (the file map).** Right for an overview, or too technical for the
   portfolio reader — split into a linked sibling doc?
4. **The opening.** Lead with "without inventing anything about you," or lead with
   the *problem* (the pain of hand-tailoring résumés)?

*Status: DRAFT v1. Faithful to the audience/medium/caveat decisions above. Feeds the
planning process after the five-question walk completes; candidate `docs/wiki/overview.md`.*
