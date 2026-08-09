# Consistency tracks enforcement

> **Audience:** `dev`
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

## What happened next: the finding became a constitutional clause (2026-08-05)

The Q2 finding above is descriptive — *consistency tracks enforcement*. Two months
later the project turned it into a **binding rule** with the opposite polarity: **a
constraint with no mechanism that fails closed is not a constraint**
([`docs/governance/charter.md`](../../governance/charter.md), **C-11**, adopted
2026-08-05, owner-directed). The first time a failure mode is recognized as a
*recurrence*, the compliant response is a mechanism authored on that branch; a note, a
memory, a ledger row, or a new prose rule is explicitly **not** compliant on its own.
New governance now **defaults to a gate**, and prose discipline is the exception that
must be labeled *unenforced* in the same breath. This page's "the fix isn't 'be more
disciplined'" line is exactly the position C-11 makes binding `[synthesis]`.

C-11 was adopted from **measurement, not friction** — the charter's own `[src: …]` tag
cites ~20 merged branches on UX-suite flakes in 40 days, one branch merged three times
over the same flake, item 30 recurring in CI five days after closure, and three of epic
19's five closures resting on weaker evidence than they claimed. Its sibling **C-12**
("declare the gap; never fill it") and the earlier **C-10** (enumerate consumers before
changing a contract) complete the family; the charter's clause range is now
**C-0…C-12** and the amendment ceremony covers all of them.

Three concrete escalations from "convention" to "gate" are worth naming, because they
land on rows this table graded on convention:

- **The C-11 closure bar** — `status = "closed"` on a work item now requires a
  falsifiable `verified_by` artifact or a named, attributed `closure_exception`; a
  *reopened* item requires a `guardrail` (or an explicit `guardrail_deferred` saying
  why none was possible). It rides `scripts/gate.py` and CI, so it binds every agent
  ([`docs/dev/work/SCHEMA.md`](../../dev/work/SCHEMA.md),
  [`scripts/work_items.py`](../../../scripts/work_items.py)). The pre-adoption closures
  are **grandfathered exactly once**, and the grandfather list is itself pinned by
  `tests/test_work_items_closure_bar.py::TestGrandfatherListIsClosed` so adding an id
  requires editing that test in the same diff.
- **The handoff recurrence section** — [`docs/dev/AGENT_HANDOFF_TEMPLATE.md`](../../dev/AGENT_HANDOFF_TEMPLATE.md)
  now requires a `## Recurrences observed this session → guardrail authored` section,
  and [`scripts/verify_doc_template.py`](../../../scripts/verify_doc_template.py)
  refuses a handoff without it — not by a special case, but because
  `required_headings` treats **every** template heading at `##` or deeper as
  mandatory and in order, so adding the section to the template *is* the gate
  ([`scripts/verify_doc_template.py:required_headings`](../../../scripts/verify_doc_template.py),
  [`scripts/verify_doc_template.py:match_headings`](../../../scripts/verify_doc_template.py))
  `[synthesis]`.
- **`require-consumer-enumeration`** — the C-10 gate; plus a registry audit
  (`tests/test_blast_radius_classification.py`) with **both** a `stale` and an
  `offenders` half, because a curated list with only a stale check rots in the *safe*
  direction and gives false confidence
  ([`docs/governance/enforcement.md`](../../governance/enforcement.md) §C2).
- **The "LLM instrumentation — every call routes through `_call_llm`" row above was
  optimistic when written.** `check_refinement_scope` opened its own
  `client.messages.create` until item 21 (2026-08-02). The row is left as the
  2026-06-07 source recorded it; the correction is [[deterministic-llm-boundary]]
  `[synthesis]`.

### The reach gap, named

[`docs/governance/enforcement.md`](../../governance/enforcement.md) §"Enforcement reach"
records a split that is invisible from any single file and went unrecorded until
2026-08-05: guards reach agents through **three adapters with different coverage**. The
git-hook adapter is tool-agnostic (Codex, Cursor, Aider, a human on the CLI);
`ci_backstop.py` + `scripts/gate.py` bind everyone even with no hooks installed; but
`require_evidence_before_fix` (C-7), `require_consumer_enumeration` (C-10), the C-8/C-12
context hooks, and `verify_binary_on_path` are **Claude Code only**. Of the C-11/C-12
mechanisms, only the closure bar binds every agent.

So the honest statement of this page's thesis at HEAD is narrower than it looks:
consistency tracks enforcement, **and enforcement tracks which agent you are**. That
gap is declared rather than papered over (C-0), carried by work item 50, and kept
honest by construction — `tests/test_enforcement_coverage.py` *derives* the routing
from the adapter at runtime and fails if a guard is added without declaring its reach,
if the declared table drifts, or if that section stops naming the gapped guards
`[synthesis]`.

## Related

- [[excellence-walk]] — the walk this finding belongs to.
- [[engineering-workstreams]] — WS-1 (monolith) + WS-2 (typing) are the two unenforced gaps.
- [[project-self-assessment]] — the same gaps, from the state-of-the-work view.
- [[governance-extraction]] — extends "consistency tracks enforcement" to the vision itself.
- [[route-surface]] — the hook-guarded security gate (the headline "enforced" example), at HEAD.
- [[deterministic-llm-boundary]] — the LLM-instrumentation consistency win, in code.
- [[openapi-api-reference]] — a later instance of the same pattern: `mode="strict"` +
  a 5-path self-check keep the OpenAPI spec from silently over- or under-claiming
  route coverage.
