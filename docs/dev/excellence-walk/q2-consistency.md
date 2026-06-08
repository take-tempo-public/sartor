<!--
  TEMPORARY / UNTRACKED ARTIFACT — output/ (gitignored). Do NOT commit.
  Q2 deliverable (draft v1), 2026-06-07. Feeds the planning process after the
  five-question walk; the gaps it names feed WS-1 (monolith) and WS-2 (typing) +
  the plan's PV-4 type scan.

  Decisions (see output/_dev-notes/excellence-walk.md):
   - Shape: LAYERED — prose read on top, per-area grade table beneath.
   - Method: separate SURFACE consistency (style/naming) from STRUCTURAL
     (patterns repeated the same way). Evidence-grounded, sampled (not exhaustive).
   - Evidence basis: app.py grep counts + 4 module headers (app/analyzer/db.models/
     dashboard.routes), 2026-06-07. Counts are proxies; flagged where inferred.
-->

# callback. — is the code consistent?

## The headline

**Yes mechanically; partially by hand — and the line between the two is exact.**
Consistency here **tracks enforcement**. Every pattern a hook or the linter
*guards* is uniform to a fault; the only real inconsistencies are the ones left to
discipline — and both of those are already named on the backlog (**types → WS-2**,
**the monolith → WS-1**). The consistency map is the *enforcement* map. (That is
the **Regulation** function from Q1 doing visible work: mechanized rules produce
mechanical consistency.)

## Surface consistency (style, naming, file structure) — STRONG

- **Module docstrings:** all four sampled modules open with a top docstring; the
  core ones thread principle tags (`app.py` P7/P8, `analyzer.py` P6/P9). Present
  everywhere.
- **Import ordering:** stdlib → third-party → local in every module, and isort is
  in the ruff gate (`I` selected) — so it *cannot* drift.
- **Naming:** snake_case throughout; private helpers `_`-prefixed; routes under
  `/api/...`; the LLM `call_kind` taxonomy (10 kinds: `analyze_extraction`,
  `analyze_synthesis`, `clarify`, `iterate_clarify`, `generate`,
  `generate_cover_letter`, `recommend`, `recommend_summary`, `critique_proposal`,
  `promote_clarification_to_bullet`) is uniform + descriptive, with a `{kind}_retry`
  sibling convention.
- **Nit (🟡):** `from __future__ import annotations` is present in the newer modules
  (`db/models.py`, `dashboard/routes.py`) but absent in the older core (`app.py`,
  `analyzer.py`); docstring richness varies (terse in app/analyzer, structured in
  db/dashboard). Cosmetic, not load-bearing.

## Structural consistency (patterns repeated the same way) — MIXED, and predictably so

**Strong where enforced:**
- **Security/route gate** — `_safe_username` + `_within` + `secure_filename` across
  the surface (**145 refs / 75 routes**), and the `route-security-lint` hook blocks
  any new route that skips it. Cannot regress.
- **Response/error idiom** — a shared `_error_detail_payload` helper + `jsonify` +
  `abort` (**350 abort/jsonify/error refs**); the "degrade to a streamed `warning`,
  never a 500" pattern in the eval/grounding routes is applied the same way each
  time.
- **LLM instrumentation** — every model call routes through `_call_llm` /
  `_parse_or_retry` with a uniform `call_kind` + `run_id` propagation.

**Gaps where unenforced:**
- **Return-type annotations** — **~43 `->` across ~130 functions in `app.py` (~1 in
  3)**. Route handlers are largely unannotated → the `check_untyped_defs` notes
  already tracked for PV-4. → **WS-2**.
- **Data-contract typing** — Pydantic guards the LLM boundary (the fuzziest surface
  — excellent), but request/response payloads and the `context_set` contract are
  `dict`/TypedDict (**29 `: dict` in `app.py`**). The contract is prose + JSON-schema,
  not a type. → **WS-2**.
- **Module size / route shape** — **75 routes in one 6,290-line file**; route bodies
  vary in size and shape; the file mixes many concerns. Navigability is the cost.
  → **WS-1**.

## Ambiguous / not-yet-audited (honest about the evidence basis)
- `evals/` modules *appear* highly consistent (the architecture module-map shows a
  repeated "`_within` guard + not-part-of-runtime + deterministic" docstring
  pattern), but I sampled them via the map, not directly. Likely ✅; unconfirmed.
- Route-size *variance* is asserted from the 6,290-LOC / 75-route ratio, not a
  per-route line count. Direction is certain; the distribution is unmeasured.

## Per-area grade table

| Area | Grade | Evidence | Enforced? | Feeds |
|---|---|---|---|---|
| Import ordering | **A** | isort (`I`) in the ruff gate | ✅ ruff | — |
| Naming + `call_kind` taxonomy | **A** | 10 uniform kinds + `{kind}_retry` | convention | — |
| Security / route gate | **A** | 145 gate refs / 75 routes | ✅ hook | — |
| LLM-call instrumentation | **A** | uniform `_call_llm`/`_parse_or_retry` + `run_id` | convention | — |
| Module docstrings | **A−** | 4/4 sampled have top docstrings + principle tags | convention | — |
| Response / error idiom | **A−** | shared `_error_detail_payload`; 350 refs; "never 500" | convention | — |
| `__future__` annotations | **B** | present in db/dashboard, absent in app/analyzer | none | tidy-up |
| Data-contract typing | **B−** | Pydantic at the LLM edge; 29 `: dict` payloads | none | **WS-2** |
| Return-type annotations | **C+** | ~43 `->` / ~130 defs in app.py (~33%) | none | **WS-2 / PV-4** |
| Module size / route shape | **C** | 75 routes in one 6,290-line file | none | **WS-1** |

## The one-line finding (for presentation, Q5)

> *Consistency here is a function of enforcement: every pattern a hook or linter
> guards is uniform; the only real inconsistencies are the two unenforced ones
> already named on the roadmap. The fix isn't "be more disciplined" — it's "extend
> the enforcement surface" (model the contracts → WS-2; split the monolith →
> WS-1).*

---

*Status: DRAFT v1. Evidence-grounded (app.py grep counts + 4 module headers,
2026-06-07); counts are proxies, evidence basis stated above. Gaps feed WS-1 +
WS-2 + the plan's PV-4. Completes the five-question spine (Q1–Q5).*
