# Consistency tracks enforcement

> **Concept:** the Q2 finding — the code is consistent **exactly where a hook or the
> linter enforces it**, and the only real inconsistencies are the two unenforced ones
> already on the backlog. The consistency map *is* the enforcement map.
> **Sources:** [`q2-consistency.md`](../../dev/excellence-walk/q2-consistency.md).
> **Grounding:** per [`SCHEMA.md`](../SCHEMA.md). The figures below are the Q2
> deliverable's own **2026-06-07** evidence (an `app.py` grep-count sample + four module
> headers); the source flags the counts as **proxies**, and that hedge is preserved
> here. A later `/wiki-audit` should re-read the source, not re-grep live code.

---

## The headline

**Yes mechanically; partially by hand — and the line between the two is exact.**
Consistency here **tracks enforcement**: every pattern a hook or the linter *guards* is
uniform to a fault; the only real inconsistencies are the ones left to discipline — and
both are already named on the backlog. This is the **Regulation** function
([`../../system-model.md`](../../system-model.md)) doing visible work: mechanized rules
produce mechanical consistency `[synthesis]`.

## Surface consistency (style, naming, structure) — STRONG

- **Module docstrings** present everywhere; the core ones thread principle tags.
- **Import ordering** stdlib → third-party → local, with isort (`I`) in the ruff gate —
  so it *cannot* drift.
- **Naming** snake_case throughout; private helpers `_`-prefixed; routes under `/api/...`;
  the LLM `call_kind` taxonomy is 10 uniform, descriptive kinds with a `{kind}_retry`
  sibling convention.
- **Nit (🟡, cosmetic):** `from __future__ import annotations` is present in newer modules
  but absent in the older core; docstring richness varies.

## Structural consistency (patterns repeated the same way) — MIXED, predictably

**Strong where enforced:**
- **Security / route gate** — `_safe_username` + `_within` + `secure_filename` across the
  surface (**145 refs / 75 routes**), with a `route-security-lint` hook blocking any new
  route that skips it. Cannot regress.
- **Response / error idiom** — a shared `_error_detail_payload` + `jsonify` + `abort`
  (**~350 refs**); the "degrade to a streamed `warning`, never a 500" pattern is applied
  the same way each time.
- **LLM instrumentation** — every call routes through `_call_llm` / `_parse_or_retry`
  with uniform `call_kind` + `run_id` propagation.

**Gaps where unenforced:**
- **Return-type annotations** — ~43 `->` across ~130 functions in `app.py` (~1 in 3).
  → WS-2 / PV-4.
- **Data-contract typing** — Pydantic guards the LLM boundary (excellent), but
  request/response payloads and the `context_set` contract are `dict`/TypedDict
  (**29 `: dict` in `app.py`**) — prose + JSON-schema, not a type. → WS-2.
- **Module size / route shape** — **75 routes in one 6,290-line file**; navigability is
  the cost. → WS-1.

## Per-area grades (2026-06-07 sample)

| Area | Grade | Enforced? | Feeds |
|---|---|---|---|
| Import ordering | A | ✅ ruff | — |
| Naming + `call_kind` taxonomy | A | convention | — |
| Security / route gate | A | ✅ hook | — |
| LLM-call instrumentation | A | convention | — |
| Module docstrings | A− | convention | — |
| Response / error idiom | A− | convention | — |
| `__future__` annotations | B | none | tidy-up |
| Data-contract typing | B− | none | **WS-2** |
| Return-type annotations | C+ | none | **WS-2 / PV-4** |
| Module size / route shape | C | none | **WS-1** |

## The one-line finding

> Consistency here is a function of enforcement: every pattern a hook or linter guards is
> uniform; the only real inconsistencies are the two unenforced ones already on the
> roadmap. The fix isn't "be more disciplined" — it's "extend the enforcement surface"
> (model the contracts → WS-2; split the monolith → WS-1).

## Related

- [[excellence-walk]] — the walk this finding belongs to.
- [[engineering-workstreams]] — WS-1 (monolith) + WS-2 (typing) are the two unenforced gaps.
- [[project-self-assessment]] — the same gaps, from the state-of-the-work view.
- [[governance-extraction]] — extends "consistency tracks enforcement" to the vision itself.
