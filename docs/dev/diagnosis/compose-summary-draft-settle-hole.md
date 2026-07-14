# Diagnosis — the Compose positioning draft vanishes (settle hole)

> **Purpose:** the durable evidence record for the intermittent failure of
> `tests/ux/regression/test_20260706_compose_summary_draft.py::test_compose_summary_draft_autofills_edits_and_persists`.
> Everything below was *paid for* — in CI runs, in probes, and in one wasted day.
> Read it before touching this bug so nobody buys it twice.
> **Audience:** the agent (or human) picking up `fix/compose-summary-draft-settle-hole`.
> **Status:** **root cause NOT yet proven.** A strong, evidence-backed hypothesis is on the
> table and the experiment that settles it is specified in [Falsification](#falsification).
> **Authoritative for:** what has been *observed*, what has been *falsified*, and what remains
> *inferred*. The separation between those three is the whole point of this document —
> conflating them is what cost the day (charter **C-7**).

---

## Symptom

The Compose step auto-drafts a two-sentence positioning summary on arrival. The regression test
asserts the textarea fills. Intermittently it does not — the page reaches a fully *settled* state
(`data-compose-ready`, background-pending counter at 0) with an **empty** textarea and nothing
left in flight to fill it. For a real user this is a "Drafting your summary…" placeholder that
never resolves.

Under `pytest -m ux --reruns 2` this mostly passes on a retry, so CI usually shows green. About a
quarter of runs it fails all three attempts and `main` goes red.

---

## Observed

Facts with artifacts behind them. Nothing in this section is a deduction.

### O-1. The test was failing **64% of its attempts**, and had been for at least 11 runs

Not a new regression. Not caused by any recent commit. Recovered by pulling per-job logs for 11
CI runs and counting `RERUN` sequences.

| | |
|---|---|
| Per-attempt failure rate | **63.6%** |
| Predicted red-run rate (`0.636³`, i.e. all 3 attempts fail) | **25.8%** |
| **Observed** red-run rate | **27.3%** |

The model fits. Two consequences, both load-bearing:

- **`0e5b9c8` (the governance commit) did not cause the red.** It lost a coin flip. The "green"
  baseline `72b878d` immediately before it **also failed 2 of its 3 attempts** — it was green only
  because the third passed.
- **`--reruns 2` converted a chronically-broken test into a lottery.** `pytest-rerunfailures`
  reports a fail-fail-pass as a bare `PASSED` **with no traceback anywhere in the log**. The
  failed attempts are discarded. `ci.yml`'s flake policy heads itself *"HONEST, not masking"* and
  says a real regression fails all three attempts — a criterion nobody can apply to evidence they
  are never shown.

**Fixed on this branch:** `tests/ux/conftest.py::pytest_runtest_logreport` now prints every
RERUN's traceback and captured output. **A rerun we never look at is a bug we never fix.**

### O-2. The summary **is persisted**, and then it **disappears** — CI run `29303444590`

The instrumented traffic dump, verbatim. Every `/api/applications/` response in order, each
annotated with **the server's own `has_draft`** at that moment:

```
GET  200 1/composition     has_draft=False drafted=''
POST 200 1/draft-summary   summary_text='Stubbed positioning summary, sentenc'   ← persisted
POST 200 1/recommend
GET  200 1/composition     has_draft=False drafted=''   ← gone, and it STAYS gone
POST 200 1/draft-gap-fill
GET  200 1/composition     has_draft=False drafted=''
GET  200 1/composition     has_draft=False drafted=''
```

**What this proves:** `/draft-summary` **did** persist the summary — the route writes the context
file *before* it returns, and a failed write would have 500'd. The very next read of that same
file does not have it, and no later read ever recovers it. **Something overwrote the file.**

This is a **lost update**, not a rendering race and not a stale cache. The data is gone from disk.

### O-3. There were **zero** non-2xx `/api/` responses anywhere in the entire UX tier

So the 400-from-a-torn-read theory (see [F-3](#f-3--atomic-writes-my-first-fix)) is not what
happened here. Nothing errored. Every route returned 200 and the data still vanished.

### O-4. Twelve routes all share a read-modify-write-the-whole-file shape

Every context writer in `blueprints/applications.py` looks like this:

```python
ctx = json.loads(cp.read_text(encoding="utf-8"))   # READ the whole file
result = <SLOW LLM CALL>                            # seconds pass — other routes run
ctx["llm_recommendations"] = by_exp                 # apply its own small delta
write_context_atomic(cp, ctx)                       # write back the WHOLE (now stale) dict
```

All twelve write sites, confirmed at HEAD: `blueprints/applications.py` lines **1708, 1838, 1946,
2086, 2244, 2334, 2365, 2432, 2646, 2730, 2863, 2962**.

The window between the read and the write is **an entire LLM call**. Any other route that writes
in that window has its delta silently erased by the whole-dict write-back. **This shape is the
defect class** — `/draft-summary` and `/recommend` are merely the pair that happen to overlap here.

### O-5. `/recommend` is fired from the wizard transition, **not** from `loadComposition()`

`_fireRecommendThenCompose()` (`static/app.js:1477`) POSTs `/recommend` at `static/app.js:1486`.
It is awaited from `submitClarifications` (`:1432`) and `skipClarifications` (`:1468`) — i.e. it
fires **during the transition into Compose**, concurrently with the Compose page's own
background cascade.

This matters because `bgDraftFiring` — the guard I reached for — is a **local variable inside
`loadComposition()`**. It cannot see, let alone guard, a route fired from a different function.
(See [F-4](#f-4--the-bgdraftfiring-client-guard-my-second-fix).)

### O-6. Windows `os.replace` semantics — **measured, do not re-derive**

Four probes bought these numbers. They are why `write_context_atomic` has a retry loop that looks
superstitious but is not:

| Measurement | Result |
|---|---|
| Naive `write_text` on a ~1 MB context, under concurrent readers | **449 torn reads** |
| `os.replace` (atomic rename), same harness | **0 torn reads**, every platform |
| `os.replace` on **Windows** while a reader holds the destination open | **150/150 writes fail** with `PermissionError` |
| Same, with the reader granting `FILE_SHARE_DELETE` (ctypes-opened handle) | **120/120 still fail** — sharing mode does **not** lift it |

POSIX has no such constraint, so the retry **never fires on Linux** — which is where CI and the
container run. Hence: `_REPLACE_ATTEMPTS = 12`, `_REPLACE_BACKOFF_S = 0.004` (linear backoff) in
`hardening.py`.

**`FILE_SHARE_DELETE` does not work. Do not try it again.**

---

## Falsified

Dead ends, each one paid for. They are recorded because a falsified hypothesis is worth exactly as
much as a confirmed one — and because without this list the next agent will re-chase them.

### F-1 — Dependency float
**Dead.** Green and red CI runs installed **byte-identical 76-package sets** — same Playwright
1.61.0, same Chromium cache down to the byte (274,092,310). Nothing floated. (The repo *does* have
a real no-lockfile problem — see the release notes — but it is not this bug.)

### F-2 — Carry-forward ledger item #2, the un-awaited `loadComposition()`
**Dead as a cause.** The failing path's `loadComposition()` **is** awaited —
`static/app.js:7366`, inside `_fireDraftSummary`. Every un-awaited call site sits off this path.
(The ledger row stays open on its own merits; it is simply not this bug.)

### F-3 — Atomic writes (my first fix)
**A real defect. Not this defect.** Non-atomic `write_text` genuinely tore 449 reads (O-6) and a
torn read genuinely 400s. But **[O-3](#o-3-there-were-zero-non-2xx-api-responses-anywhere-in-the-entire-ux-tier)
shows nothing 400'd** — the observed POST returned 200 and the data vanished anyway.

`write_context_atomic` is **kept**: it closes a real hole, and it is the write primitive the real
fix builds on. It just does not close *this* hole. Atomic writes stop torn **reads**; they do
nothing whatsoever about lost **updates**.

### F-4 — The `bgDraftFiring` client guard (my second fix)
**Structurally incapable of working**, per [O-5](#o-5-recommend-is-fired-from-the-wizard-transition-not-from-loadcomposition):
the guard is a local inside `loadComposition()`; the route it was meant to serialize is fired from
`_fireRecommendThenCompose()`. There is also no evidence it helped — rerun counts went 3 → 2 → 3,
which is noise. **Reverted.**

---

## Inferred

**This is a hypothesis. It has not been proven. Do not treat it as fact, and do not build on it
until the experiment below has been run.**

> `/recommend` read the context file *before* `/draft-summary`'s write landed, spent seconds in
> its LLM call, and then wrote its stale copy back — erasing `summary_text`.

**Why it is the leading candidate:** it is the only other context-writer in the observed window,
and it has exactly the read-modify-write-whole-dict shape that produces lost updates ([O-4](#o-4-twelve-routes-all-share-a-read-modify-write-the-whole-file-shape)).

**Why it is still only a hypothesis:** the traffic dump records **response order, not write
order**. A route's response lands when it finishes; that says nothing about when it *read*. The
dump is consistent with the hypothesis but does not establish it. `/draft-gap-fill` also writes,
and also cannot be excluded on this evidence.

---

## Falsification

**Run this first. It is the next agent's first and only act.** Do not write the fix before this
test exists and **fails on HEAD**.

A route-level test — no browser, no CI, no real race:

1. Seed an app + context (reuse `draft_app` / `_seed` in `tests/test_draft_summary.py`).
2. Stub `draft_positioning_summary` so it **blocks on a `threading.Event`** until `/recommend`
   has completed its read — this makes the interleaving deterministic instead of lucky.
3. Fire both POSTs on two threads.
4. Assert **both** `composition_overrides.summary_text` **and** `llm_recommendations` survive.

**If it fails on HEAD:** the hypothesis is confirmed, the lost update is real and reproducible in
milliseconds, and you may build the fix.

**If it passes on HEAD:** the hypothesis is **dead**. Stop. Do not fix. Widen the instrument and
report. (`/draft-gap-fill` is the next candidate; so is a writer outside this file.)

---

## The fix — build only after the test above fails

`hardening.context_transaction(path)` — a `@contextmanager` that:

- takes a **per-path `threading.Lock`**;
- **re-reads the file fresh inside the lock** (this is the part that closes the hole — the
  caller's optimistic pre-LLM read is discarded);
- yields the fresh dict for the caller to apply **only its own delta**;
- writes via the existing `write_context_atomic` on clean exit;
- **skips the write entirely** if the block raises.

Routes keep their optimistic read for validation and keep the **LLM call outside the lock** — only
the delta application is serialized, so no request waits on another's LLM latency. Convert all
**twelve** sites ([O-4](#o-4-twelve-routes-all-share-a-read-modify-write-the-whole-file-shape));
converting only the two in the observed window fixes the symptom and leaves the defect class.

An in-process lock is the right scope: the Dockerfile runs `CMD ["sartor", "--host", "0.0.0.0"]` —
a single-process **threaded** server. (If that ever becomes multi-process, this needs to become a
file lock, and *that* is the moment to revisit — not before.)

**A bonus that falls out for free:** the transient staging keys (`jd_text`, `career_facts`, …) are
not present on a fresh in-lock read, so every defensive `ctx.pop(transient)` and the whole
"don't leak staging keys into the iteration chain" hazard disappear structurally rather than by
vigilance.

---

## Acceptance bar

**A bare `PASSED` with no `RERUN`, sampled across more than one CI run.**

Green-with-reruns is exactly what hid this for eleven runs and it does not count. With the
`pytest_runtest_logreport` hook now in `tests/ux/conftest.py`, a surviving rerun will print its
own traceback — so "green" is finally checkable.

---

## What shipped on this branch (and what did not)

**Shipped — all real, none of it the root cause:**
- `hardening.write_context_atomic` + the Windows retry ([O-6](#o-6-windows-osreplace-semantics--measured-do-not-re-derive)); 12 call sites converted.
- `_fireDraftSummary`'s once-ever latch turned into an **in-flight claim** released on failure — a
  once-ever latch made any transient failure *permanent*, which is a genuine user-facing defect.
- A surfaced error (`_failDraftSummary`) where the client previously swallowed the failure.
- The visibility layer that actually produced this diagnosis: the RERUN reporter, the widened
  4xx-on-`/api/` sentinel (it was **5xx-only**, which is how a 400 stayed invisible for 11 runs),
  and the traffic dump in the regression test.

**NOT shipped: the fix.** The lost update is still live on `main`.
