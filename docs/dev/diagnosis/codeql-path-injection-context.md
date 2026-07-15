# Diagnosis — CodeQL `py/path-injection` × 7 on the context-file helpers

> **Status:** mechanism PROVEN-by-observation for *where/what*; the *why CodeQL fires*
> is an inference (the query can't be run locally). The fix is verified by CI, not by me.
> **Branch:** `fix/codeql-path-injection-context`

---

## Symptom

CodeQL (`security-and-quality`, `on: pull_request`/`push`) reports **7 high**
"uncontrolled data used in path expression" (`py/path-injection`) alerts in `hardening.py`,
plus 2 low quality nits in `tests/test_hardening.py`. Required checks are green, so this is
not a merge blocker today — but CodeQL is required for the OpenSSF badge, so "green" must be
earned by construction, not by per-alert dismissal (owner call, 2026-07-14).

---

## Observed

Fetched live from the code-scanning REST API at HEAD `fe5bd59` (the PR #21 merge on `main`),
`state=open` — the actual alerts, not the ledger's paraphrase:

**7 high `py/path-injection`, all in `hardening.py`** (alert number → line → sink):

| # | line | sink |
|---|---|---|
| 353 | 1474 | `path.parent.mkdir(...)` in `write_context_atomic` |
| 354 | 1479 | `tmp.write_text(...)` |
| 355 | 1482 | `os.replace(tmp, path)` |
| 356 | 1482 | `os.replace(tmp, path)` (second flow) |
| 359 | 1491 | `tmp.unlink(...)` |
| 360 | 1509 | `path.resolve()` in `_context_lock` |
| 361 | 1578 | `path.read_text(...)` in `context_transaction` (sink cols 44–48 = `path`) |

Each carries the message *"This path depends on a user-provided value."* (#359 lists the
flow three times.) The code-scanning REST endpoint returns `code_flows: []` for these, so the
full source→sink node chain is not machine-readable via the API — the sink locations above
are what it does return.

**2 low quality nits in `tests/test_hardening.py`** (fold in on this branch):

| # | line | rule |
|---|---|---|
| 362 | 1018 | `py/unreachable-statement` |
| 358 | 897 | `py/empty-except` |

**Context — not flagged, and this is the load-bearing observation:** the reader helpers in
`blueprints/applications.py:689–930` (`_read_composition_overrides`, `_read_bullet_order`, …)
each do `cp = Path(context_path)` → `if not _within(cp, OUTPUT_DIR): return` → `cp.read_text()`
in the **same function**, and CodeQL flags **none** of them. The 7 flagged sinks are all in
`hardening.py`, reached from the routes via `context_transaction(cp)` — i.e. the guard and the
sink are in **different functions**.

**Not introduced by the new atomic-write code's logic** — it is new *relative to `main`*, which
is what the PR-diff scan lit up; CodeQL was already red on the pre-fix tip `5744a10`.

---

## Falsified

**F-1 — the `resolve_within` chokepoint ALONE does not satisfy CodeQL. It moves the taint,
it does not sanitize it.** Observed on PR #22's CodeQL run (`refs/pull/22/merge`, analysis sha
`e637374b`, `Analyze (python)` = success, queried by ref via the code-scanning API):

- The 7 original `hardening.py` alerts (353–361) are **absent** from the merge ref, and the 2
  low test nits (358, 362) are **absent** — those parts worked.
- But **12 NEW high `py/path-injection` alerts** (363–374) appeared: **11 at the new
  `resolve_within(context_path, …)` call sites** in `blueprints/applications.py` (lines 1535,
  1792, 1917, 2057, 2194, 2373, 2562, 2701, 2868, 2993, 3096) **+ 1 inside `resolve_within`
  itself** at `web_infra/security.py:84` (the `Path(candidate).resolve()`).

**Interpretation:** CodeQL propagates taint arg→return through `resolve_within` (its
inter-procedural summary sees `candidate` → `Path(candidate).resolve()` → returned) and does
**not** treat the intervening `if not _within(resolved, root): raise` as a barrier at the
returned value. So relocating containment into a returning helper did not break the flow — it
relabelled the same flow at new sink locations. The chokepoint is still the right *shape* for
humans/enforcement, but CodeQL needs the sanitization made explicit to it (a recognized
sanitizer pattern in the resolver body, or a CodeQL sanitizer model). **Next step is NOT
another blind push** — identify the exact barrier pattern CodeQL's Python `PathInjection` query
recognizes first.

_Open question this raises about the `## Inferred` hypothesis:_ the reader helpers
(`applications.py:689–930`) that guard-then-`read_text` in-function with the SAME `_within` are
unflagged, yet `resolve_within`'s guarded-then-returned value IS flagged. The distinguishing
factor is **use-in-place (dominated by the guard) vs return-through-a-summary** — CodeQL's
barrier guard sanitizes uses dominated by the guard in the same function, but its function
*summary* re-derives arg→return taint without that barrier.

---

## Inferred

**Hypothesis (unproven — CodeQL's dataflow can't be run locally):** CodeQL's `py/path-injection`
does not carry the `_within(...)` barrier **across the function-call boundary** into
`context_transaction` / `write_context_atomic`. When the guard and the sink are in the same
function (the reader helpers) it sees containment and stays silent; when the route guards but the
sink executes inside `hardening.py`, the barrier is lost and every filesystem op on `path` reads
as tainted-from-`context_path`.

What I'd need to SEE to confirm it: the alert's source→sink `code_flows` (empty via REST), or a
CodeQL run that goes green after the barrier is relocated to a value CodeQL propagates.

**If the hypothesis holds**, the fix is to break taint **at the source**: a resolver whose
*return value* is the resolved-and-validated path, so the value flowing into
`context_transaction` derives from a validation branch rather than raw `context_path`. Whether
CodeQL models such a return as sanitized is the residual unknown → **push-and-read-CI**.

---

## Falsification / acceptance bar

CodeQL runs on the branch's PR. The bar is **not** "CI green" (CodeQL is advisory / non-required,
and a rerun-masked green is no evidence — the project's own §5f lesson). The bar is:

- **The 7 high `py/path-injection` alerts (353,354,355,356,359,360,361) transition to
  `fixed`/closed** on this branch's CodeQL analysis, confirmed by re-querying the code-scanning
  API by alert number.
- The 2 low nits (362, 358) likewise close.
- **No new `py/path-injection` alert appears** elsewhere from the refactor.

If the source-side chokepoint alone does not clear them, a CodeQL sanitizer/barrier model under
`.github/codeql/` naming `resolve_within` is the documented fallback — added only after a push
shows the chokepoint insufficient.

---

## The fix

1. `web_infra/security.py`: add `PathTraversalError` + `resolve_within(candidate, root) -> Path`
   — resolve, `_within`-check, raise on escape, **return the resolved path** (the value used
   downstream). `_within` stays (readers + other blueprints still use it).
2. `blueprints/applications.py`: at the ~12 route sites that flow into `context_transaction`,
   replace `cp = Path(context_path); if not _within(...) or not cp.exists(): 400` with
   `cp = resolve_within(...)` in a `try/except PathTraversalError -> 400`, keeping the separate
   `cp.exists()` check. **HTTP semantics unchanged** (same codes + bodies).
3. If needed after CI: the `.github/codeql/` sanitizer model.
4. `route_security_lint.py` + `test_route_containment_gate.py`: accept `resolve_within` as the
   containment proof *by design* (they pass by substring coincidence today) + an explicit test.
5. The 2 low test nits.

---

## Acceptance bar

The 7 high + 2 low alerts closed on CI (verified by API re-query, not a bare green), the full
quality gate green, and no behavior change in the converted routes (same status codes/bodies,
proven by the existing route tests staying green).
