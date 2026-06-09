# Project self-assessment (state of the work)

> **Concept:** the descriptive "state of the work" the walk produced (Q5 / PART A) —
> what is genuinely strong, what is worth watching, and what needs a decision. **★**
> marks items worth drawing attention to when presenting.
> **Sources:** [`excellence-walk.md`](../../dev/excellence-walk/excellence-walk.md)
> "PART A — Project self-assessment".
> **Grounding:** per [`SCHEMA.md`](../SCHEMA.md). Evidence figures (docstring counts,
> test totals, LOC) are the walk's own 2026-06-07 readings, preserved with their
> source's framing; conclusions are tagged `[synthesis]`.

---

## ✅ Strengths (true and defensible)

- **★ Disciplined dependency hygiene** — 9 runtime deps, each version-bounded and
  justified inline in `pyproject.toml`; no bloat.
- **★ Runtime type-safety at the fuzziest boundary** — Pydantic v2 models +
  `*_REQUIRED_KEYS` frozensets validate every LLM response in `analyzer.py`. The most
  unpredictable surface is the most rigorously checked.
- **★ Clean deterministic / LLM boundary (the P1 hardening line)** — the deterministic
  core is LLM-free by contract; all model calls live in `analyzer.py`. (Canonical in
  [`../../system-model.md`](../../system-model.md) under Production.)
- **★ Security-by-convention, enforced mechanically** — `_safe_username` + `_within` on
  every filesystem-touching route, enforced by a hook rather than reviewer vigilance.
- **★ Reproducibility / audit trail** — the `context_set` JSON contract +
  `parent_context_path` iteration chain.
- **★ Observability + eval rigor** — an LLM-eval harness with `PROMPT_VERSION`
  attribution + deterministic post-generation metrics.
- **★ Documentation & "explain-why" comments** — every doc carries a
  Purpose/Audience/Authoritative-for/Sibling-docs header; ~212 docstring markers in
  `app.py` alone (2026-06-07 count).
- **Serious, multi-tier test suite** — 955 test functions / 67 files / ~18.2k test LOC
  (≈1:1 with all source); unit + route + Playwright UX + LLM-eval tiers.
- **Principle-driven** — P1/P2/P5/P6/P8/P9 annotations thread architecture intent through
  the code; load-bearing, not decoration.

## ⚠️ Watch-outs (named honestly)

- **★ `app.py` is a 6,290-line / 75-route monolith** — the clearest smell; hurts
  navigability even though each function is readable. → WS-1 ([[engineering-workstreams]]).
- **Typing is "typed, not strict"** — mypy runs in the gate but not `strict=true`;
  payloads are `dict`-typed rather than modelled; ~117/214 core functions carry return
  annotations. → WS-2 ([[engineering-workstreams]]; see [[consistency-tracks-enforcement]]).
- **Heavy process/meta footprint for a solo beta** — ~70 markdown files / ~14k doc lines,
  comparable to the ~12k-line core. Defensible *if* the repo is also a Claude-Code
  methodology showcase, but it is enterprise-scale ceremony on a single-author beta —
  a deliberate decision, not an accident.

## ❓ Ambiguous / needs a decision

- **"TDD" is unprovable as written.** The evidence supports *test-rich +
  regression-driven* (date-stamped regression tests; tests land in the same commit as
  features) — but nothing proves tests were written *first*. Honest phrasing for
  presenting: *"test-rich and regression-driven; tests ship with every change."*
- **Docs sizing / discoverability** — well-headed and cross-linked, but is any file too
  long, and is there a central index? → Q4, which became the wiki ([[llm-wiki-design]]).
- **Process-to-product ratio** — strength or weight, depending on framing.

## The framing (for outsiders)

> This reads like **a staff/principal engineer's personal project that adopted
> big-company rigor** — above the GitHub median on docs, test discipline,
> security-by-convention, and AI-product engineering; the remaining gap to "polished
> production" is **structural** (split the monolith) and **type-strictness**, not
> cultural. `[synthesis]`

That gap is exactly what the [[engineering-workstreams]] backlog targets.

## Related

- [[excellence-walk]] — the walk this assessment belongs to.
- [[consistency-tracks-enforcement]] — Q2; the consistency view of the same gaps.
- [[engineering-workstreams]] — WS-1/WS-2 close the structural + typing gaps named here.
