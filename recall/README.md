# `recall/` — the Memory substrate (Stage 0 skeleton)

> **Status:** Stage 0 skeleton (Sprint 7.4, `feat/recall-skeleton`). The seams
> only — no real source tier, no LLM. The S1 wiki + S2 `git grep` tiers and the
> Haiku avatar are Sprint 7.5; the S3 vector tier is 7.6.
> **Authoritative design:** [`../docs/dev/memory-architecture.md`](../docs/dev/memory-architecture.md).
> This README is the package contract; the design doc is the why.

`recall/` is callback's **Memory** function made first-class: a reusable,
deterministic retrieval/assembly layer that *feeds* a small-LLM "avatar" with
**cited source units**. Retrieval is a *feed*, not an end — the substrate
assembles a bounded, cited `Context`; the avatar (a separate, later module) is
the only thing that phrases an answer.

## Public surface (the whole API)

```python
from recall import assemble, Unit, Source, Scope, Context, Tier, Audience

ctx = assemble(query, scope, sources)   # -> Context
```

| Type | Role |
|---|---|
| `Unit` | one provenance-stamped source unit: `(text, tier, source_id, citation, audience, sha, score)`. Frozen; cannot exist without a non-empty `text` + `citation` (the stamp is mandatory). |
| `Source` | the tier interface (`Protocol`): `refresh(since_sha)` + `search(query, scope) -> Sequence[Unit]`. Every tier (wiki, git, vector, session) implements this one shape. |
| `Scope` | the caller's allowed window: `allow_dev` toggle, `enabled_tiers`, `token_budget`. |
| `Context` | the assembled, budgeted, cited feed for one avatar turn: `(query, units, token_estimate, truncated)`. |
| `Tier` / `Audience` | the source-family (`S1`…`S5`) and access-tag (`user`/`dev`) enums. |
| `assemble()` | the one entry point: search → fuse (RRF) → access-filter → token-budget pack → `Context`. |

`assemble(query, scope, sources)` injects the sources explicitly so the substrate
stays project-agnostic. The canonical 2-arg `assemble(query, scope)` in the design
doc is the thin project-wired convenience 7.5 adds once the real sources are
registered via config.

## The two cross-cutting planes

- **Provenance / grounding plane** — every `Unit` carries its stamp
  (`tier · source_id · citation · audience · sha`), enforced at construction.
  `assemble()` only filters, reorders, and truncates units; it never rewrites
  `text`, so the stamp survives into the `Context`. (Lives in `models.py`.)
- **Access / disclosure plane** — `Scope` resolves the user/dev toggle into an
  allowed-audience set; units exceeding scope (over-audience or disabled tier)
  are dropped. Model-detected progressive disclosure *proposes* depth; this plane
  *disposes*. (Lives in `planes.py`.)

## The hard dependency rule (refactor-immune)

`recall/` may import **stdlib only** (Stage 0). It must **never** import `app.py`,
`analyzer.py`, the callback DB models, or Flask — mirroring the P1 / charter-C-6
determinism boundary. This is what makes the v1.0.8 blueprint split a *move*, not
a rewrite, and future extraction packaging-only. The rule is enforced by
[`../tests/test_recall_boundary.py`](../tests/test_recall_boundary.py) (an AST
walk, mirroring the PX-08 egress gate) — not a hook (enforcement-portability is
the Sprint 8.7 work).

## Files

| File | Purpose |
|---|---|
| `models.py` | the value types + the provenance plane (the mandatory `Unit` stamp). |
| `source.py` | the `Source` protocol. |
| `planes.py` | the access/disclosure plane (pure filter functions). |
| `assemble.py` | `assemble()` + RRF fusion + token-budget packing. |
| `memory_source.py` | `InMemorySource` — the reference `Source` (worked example + the future S5-P1 session-buffer shape). |
