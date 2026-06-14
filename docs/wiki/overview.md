# callback. — system overview

> **Purpose:** the wiki's front door — a one-page orientation to what callback. is and
> how the whole system is shaped. The **canonical** statement of the system model (the
> seven functions, the one law, the Product/Work split, the full "Where it lives" file
> map) is [`../system-model.md`](../system-model.md); this page presents it at the
> wiki's altitude and **defers to it** for the authoritative vocabulary.
> **Audience:** `user` — anyone meeting the project; a human reader, or an LLM agent
> orienting before a change.
> **Grounding:** synthesized from [`../system-model.md`](../system-model.md) (the
> canonical self-model) per [`SCHEMA.md`](SCHEMA.md)'s one grounding rule. Where this
> page and the canonical doc differ, the canonical doc is right.

---

## What it is

callback. is a local-first app that tailors your résumé — and, optionally, a cover
letter — to a specific job, **grounded in what's actually true about you, not
invented**. You paste in a job description; it reads the posting, asks a few sharp
questions, helps you choose which of your real accomplishments fit, then writes a
tailored draft grounded entirely in your actual history and renders it to Word or
PDF. It runs on your own machine; your career data never leaves it, apart from the
calls to the AI model that does the writing.

The thing that makes it trustworthy is a rule it holds itself to: it may **select,
rephrase, and emphasize** what is already true about you, but it is built **not to
fabricate** — no invented titles, numbers, or dates. A grounding check in the generation
prompt enforces that rule and a witness metric measures whether it held — a constraint on
the model, not a guarantee about every output. That single constraint shapes the entire
design, and it recurs at every scale of the system.

## Two subjects: the Product and the Work

Telling these apart is the key to reading the whole repository:

- **The Product** — what the user runs: **Production** (the pipeline) over its
  **Substrate** (your material).
- **The Work** — everything that produces the Product and keeps it improving:
  **Evaluation**, **Operation**, **Memory**, and **Regulation**. Remove the Work and the
  Product still *runs* — but no one could safely change it.

Above both sits **Governance** — the written intent the Work answers to. The most
unusual thing about the project is that **the Work is engineered as deliberately as the
Product**, with an AI coding agent treated as a first-class inhabitant of it.

## The seven functions

| Function | In one line |
|---|---|
| **Substrate** | The stored material the product reads and writes — your history, the job posts, the documents produced, the per-iteration audit trail. Stays on your machine. |
| **Production** | The pipeline (read job → clarify → recommend → generate → refine). *All* AI calls are isolated in one place; everything that must be exact is kept deliberately away from the AI. |
| **Evaluation** | How the project knows the Product is good — tests plus a measurement harness that scores AI output and flags regressions. Active, not passive. |
| **Operation** | The people and assistants who change the system — notably AI coding agents as first-class contributors, working under mechanically-enforced rules. |
| **Memory** | The recallable knowledge — docs, design rationale, and the contributor contract read *before* changing anything (this wiki is part of it). |
| **Regulation** | The machine-enforced gates — checks that block unsafe changes plus the release discipline that gates what ships. |
| **Governance** | The north-star answered to — the written vision and the 10 Principles. The one layer deliberately *prescribed* rather than emergent. |

The full descriptions and the per-function "Where it lives" file map are in the
canonical [`../system-model.md`](../system-model.md) — not duplicated here.

## The one law

> **Every dependency points inward toward Production; Production answers only upward to
> Governance.**

This is the codebase's own internal rule scaled to the whole system: the deterministic
core never calls the AI, the AI layer never reaches into the web layer, and Production
never depends on the tooling that tests it. You can always remove an outer layer of the
Work and the Product still stands; remove the Product's AI brain and the deterministic
core still runs. That one-way discipline is why the codebase stays navigable as it grows.

---

## Open revision points (inherited from `system-model.md`; not yet resolved)

These four framing calls were raised 2026-06-07 in
[`../system-model.md`](../system-model.md) §"Open revision points" and were
deliberately left open to settle here, as this page is refined. Recorded so they are
not silently dropped.

1. **The Governance honesty note.** This page keeps the seam visible ("deliberately
   prescribed rather than emergent"). For a portfolio audience: strength
   (self-awareness) or distraction? *Author lean: keep.*
2. **The "AI agents are first-class contributors" line** (emphasized in two places). A
   distinctive showcase hook, but could invite skepticism. Dial up / down / leave?
3. **The "Where it lives" file map.** Kept canonical in `system-model.md` and only
   *pointed to* here — is that the right split, or should the overview carry a trimmed
   map of its own?
4. **The opening.** Lead with the grounding / no-fabrication promise (as it does now),
   or lead with the *problem* (the pain of hand-tailoring résumés)?
