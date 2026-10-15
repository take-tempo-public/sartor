# Diagnosis — `GET /api/applications/<id>/composition` reads and parses the same context file 11 times per request

> **Status:** count and cost **observed** (O-1 to O-4). The mechanism is not in doubt: eleven
> helpers each open the file themselves. What is **not** established is how much of the block's
> cost is parsing (O-4). The fix is a consolidation, not the repair of a wrong result.
> **Branch:** `fix/compose-single-context-parse`
> **Item:** 161 (`docs/dev/work/items/0161-get-composition-repeated-context-parses.md`)

---

## Symptom

Item 161 filed the count as *"counted from the code, not measured"*. Compose calls this GET on
every arrival and after most Compose actions (the re-render cascade), so the per-request cost
repeats. Nothing is wrong in the response; the work done to produce it is eleven times what one
read needs.

---

## Observed

All from the instrument `measure_compose_parse.py` (source at the end of this
document), run on `main` at `5c6e721` (the branch has no production edit yet), by this command:

```
python measure_compose_parse.py /c/Dev/sartor 200 before.json
```

- **O-1 — environment.** Python 3.13.14, Windows-11-10.0.26200-SP0, N = 200 timed GETs per case
  after 4 warm-up GETs, in-process Flask test client. Three real contexts under `output/`
  (n = 128 files; sizes min 24,173 / p50 66,867 / p90 130,946 / max 204,996 bytes) were
  **copied** to a temp OUTPUT_DIR; nothing was modified or committed, only sizes and timings are
  recorded here.
- **O-2 — read count.** `Path.read_text` patched to count reads of the context file during one
  GET: **`reads_per_get = 11` at all three sizes** (fenced artifact below).
- **O-3 — timings** (ms, median / p95):

  | case | context bytes | whole GET | one read+parse | the 11-helper block |
  |---|---|---|---|---|
  | p50 | 66,867 | 21.469 / 36.229 | 0.488 / 0.800 | 12.519 / 20.441 |
  | p90 | 130,946 | 29.896 / 46.214 | 1.022 / 1.471 | 19.890 / 32.746 |
  | max | 204,996 | 29.033 / 46.301 | 1.481 / 2.280 | 23.156 / 38.980 |

- **O-4 — the block is not 11 × one read+parse.** At p50, 11 × 0.488 ms = 5.4 ms against a block
  median of 12.519 ms (2.3×); at max, 16.3 ms against 23.156 ms (1.4×). **The remainder is not
  attributed and was not measured.** It includes things other than parsing: the `_within`
  containment resolve and `exists()` in each helper, `frozen_composition_doc`, and
  `composition_is_stale`'s inputs digest in `_read_freeze_state`.
- **O-5 — the fixture's database is empty.** The seeded application has a candidate and no
  experiences, bullets, titles or skills, so the whole-GET figure carries almost no ORM or
  scoring work. **The block's share of a real GET is therefore overstated here** (21–30 ms total,
  of which the block is 12.5–23 ms); the absolute block figures are the ones to carry forward.

```
{"python":"3.13.14","platform":"Windows-11-10.0.26200-SP0","n":200,"helper_signature_mode":"path",
 "cases":{"p50":{"context_bytes":66867,"reads_per_get":11,"get_total":{"median_ms":21.469,"p95_ms":36.229},"read_and_parse_once":{"median_ms":0.488,"p95_ms":0.8},"helper_block":{"median_ms":12.519,"p95_ms":20.441}},
          "p90":{"context_bytes":130946,"reads_per_get":11,"get_total":{"median_ms":29.896,"p95_ms":46.214},"read_and_parse_once":{"median_ms":1.022,"p95_ms":1.471},"helper_block":{"median_ms":19.89,"p95_ms":32.746}},
          "max":{"context_bytes":204996,"reads_per_get":11,"get_total":{"median_ms":29.033,"p95_ms":46.301},"read_and_parse_once":{"median_ms":1.481,"p95_ms":2.28},"helper_block":{"median_ms":23.156,"p95_ms":38.98}}}}
```

- **O-6 — consumers, grep-complete** (`blueprints/applications.py:1117-1176` for the calls;
  definitions at `:730-1086`). Every name searched: the eleven `_read_*` identifiers, as symbol,
  string form (`"_read_composition_overrides"` in monkeypatches) and in docs.
  No caller of any of the eleven exists outside `get_application_composition`.
  `blueprints/applications.py` has no entry in `scripts/enforcement/blast_radius.py` (searched
  `applications`: no match), so `require-consumer-enumeration` does not gate it; the list below is
  written anyway.

---

## Consumers

| Site | Decision |
|---|---|
| `blueprints/applications.py:1117-1176` (`get_application_composition`), sole caller of all eleven | **Change**: load once, pass `ctx` |
| `tests/ux/regression/test_20260718_compose_unawaited_reloads.py:121` monkeypatches `applications_module._read_composition_overrides` with a `*args, **kwargs` delay wrapper | **Keep name and single call site.** The wrapper is signature-agnostic; the delay still lands inside the GET |
| `tests/ux/regression/test_20260722_compose_bare_reload_settle.py:97` (same shape, `_delayed_read_overrides`) | **Keep**, same reason |
| `tests/test_composition_summary.py:15` (docstring mentions `_read_summary_overrides`) | **Deferred**: descriptive, the name is unchanged |
| `docs/wiki/pages/route-surface.md:174-177` says the read is validated with `_within(cp, ...)`; it becomes `resolve_within` | **Change** in this branch's scoped wiki pass |
| `docs/wiki/pages/context-set-contract.md:96` cites `applications.py:_read_freeze_state` | **Keep**: it still calls `frozen_composition_doc` |
| `docs/dev/diagnosis/codeql-path-injection-context.md:50` cites `applications.py:689–930` | **Deferred**: a dated record of that session's lines |
| `docs/dev/diagnosis/compose-unawaited-reloads.md:160` and `docs/dev/blast-radius/frozen-composition-staleness.md` (`## Deferred`) | **Keep**: history; the second is closed by this branch and says so in item 161's `## Updates` |
| `corpus_to_json_resume._read_skill_overrides`, `_read_skill_recommendations`, `_read_summary_text_override`; `hardening.frozen_composition_doc`, `composition_is_stale` | **Untouched**: already take a context dict |

---

## Falsified

_(Nothing yet.)_

---

## Inferred

**Not observed; do not build on these.**

- **I-1 — one read also gives the GET a consistent snapshot.** Today a `/composition` POST landing
  between two of the eleven reads could mix two versions of the file into one response. Not
  reproduced and not tested; if the fix removes it, that is a side effect, not the reason for it.
- **I-2 — the remainder of the block (O-4) is dominated by per-helper `_within` resolution and the
  freeze-state digest.** A guess from reading the helpers. The after-run's `helper_block` figure
  is the check: whatever is still there once the reads are single is not parsing.

---

## Falsification

**Pre-registered before the fix is written** (the after-run uses the same instrument, unchanged).

1. **Guard test**, `tests/test_composition_single_context_read.py`: the GET reads the context file
   **exactly once**, and a context whose JSON is `null` returns the empty payload with 200.
   **Must fail on `main`** (`11 != 1`, and the `null` case is an `AttributeError` 500 there). If the
   count assertion passes on HEAD, the hypothesis that the helpers read independently is dead:
   stop and widen the instrument.
2. **Predicted after-run** (stated now, judged afterwards, whatever the outcome):
   - `reads_per_get == 1` at all three sizes.
   - `helper_block` median falls by **at least 10 × the `read_and_parse_once` median** at each size
     (p50 ≥ 4.9 ms, p90 ≥ 10.2 ms, max ≥ 14.8 ms). A smaller drop means the cost I predicted
     is not where the time goes, and I-2 is the place to look next.

---

## The fix

_Only after the experiment above has actually failed._

---

## Acceptance bar

- The guard test is red on `main`, green on the branch, run once with no retry (no `RERUN` line).
- The existing `/composition` route tests (12 files) and the two UX monkeypatch tests pass unchanged.
- The after-run is recorded here against the predictions above, whichever way they fall.
- `python -m scripts.gate --result` cited for the tip.

---

## Instrument source

The exact file that produced O-1 to O-5 and is re-run for the after-run.

```python
"""Item 161 instrument: how often does GET /composition read the context file, and what does it cost?

Usage: python measure_compose_parse.py <repo_root> <N> <results.json>

Run from any directory; the repo is put on sys.path. Real context files under
<repo_root>/output are COPIED into a temp OUTPUT_DIR (never modified, never committed);
only their sizes and the timings are printed. The same script is run before and after the
fix: it adapts to the helper signature (`context_path: str` before, a loaded `ctx` dict after).
"""

from __future__ import annotations

import inspect
import json
import os
import platform
import shutil
import statistics
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(sys.argv[1]).resolve()
N = int(sys.argv[2])
RESULTS = Path(sys.argv[3])
sys.path.insert(0, str(REPO))
os.chdir(REPO)

HELPERS = [
    "_read_composition_overrides",
    "_read_bullet_order",
    "_read_recommendations_and_added",
    "_read_summary_overrides",
    "_read_summary_draft",
    "_read_gap_fill",
    "_read_title_overrides",
    "_read_experience_summary_overrides",
    "_read_experience_summary_drafts",
    "_read_skill_composition",
    "_read_freeze_state",
]


def pct(xs: list[float], p: float) -> float:
    s = sorted(xs)
    return s[max(0, min(len(s) - 1, int(round(p * len(s))) - 1))]


def summarize(xs_s: list[float]) -> dict[str, float]:
    ms = [x * 1000 for x in xs_s]
    return {"median_ms": round(statistics.median(ms), 3), "p95_ms": round(pct(ms, 0.95), 3)}


def pick_real_contexts() -> list[tuple[str, Path]]:
    files = sorted(
        (p for p in (REPO / "output").rglob("context_*.json") if p.is_file()),
        key=lambda p: p.stat().st_size,
    )
    if not files:
        raise SystemExit("no real context files under output/ to measure")
    n = len(files)
    return [
        ("p50", files[(n + 1) // 2 - 1]),
        ("p90", files[max(1, int(n * 0.9)) - 1]),
        ("max", files[-1]),
    ]


def main() -> None:
    import db.session as dbs

    tmp = Path(tempfile.mkdtemp(prefix="sartor-item161-"))
    dbs.DEFAULT_DB_PATH = tmp / "measure.sqlite"
    dbs._engine = None
    dbs._SessionLocal = None

    from app import create_app
    from config import Config

    cfg = Config(base_dir=tmp)
    app = create_app(cfg)
    (cfg.configs_dir / "casey.config").write_text("{}", encoding="utf-8")
    (cfg.output_dir / "casey").mkdir(exist_ok=True)

    from db.models import Application, Candidate
    from db.session import get_session, init_db

    init_db()
    s = get_session()
    try:
        c = Candidate(username="casey", name="Casey Rivera")
        s.add(c)
        s.flush()
        a = Application(
            candidate_id=c.id, title="Senior PM", jd_text="Senior PM building platforms.",
            jd_fingerprint="f" * 16,
        )
        s.add(a)
        s.commit()
        aid = a.id
    finally:
        s.close()

    import blueprints.applications as A

    sig = inspect.signature(A._read_composition_overrides)
    mode = "path" if "context_path" in sig.parameters else "ctx"

    # Count every read_text of the context file during a GET.
    real_read_text = Path.read_text
    counter = {"target": None, "n": 0}

    def counting_read_text(self: Path, *args, **kwargs):  # type: ignore[no-untyped-def]
        if counter["target"] is not None and str(self) == counter["target"]:
            counter["n"] += 1
        return real_read_text(self, *args, **kwargs)

    out: dict = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "n": N,
        "helper_signature_mode": mode,
        "cases": {},
    }
    client = app.test_client()
    for label, src in pick_real_contexts():
        dst = cfg.output_dir / "casey" / f"ctx_{label}.json"
        shutil.copy2(src, dst)
        size = dst.stat().st_size
        url = f"/api/applications/{aid}/composition?context_path={dst}"

        r = client.get(url)
        if r.status_code != 200:
            raise SystemExit(f"{label}: GET returned {r.status_code}: {r.get_data(as_text=True)[:200]}")
        for _ in range(3):
            client.get(url)

        Path.read_text = counting_read_text  # type: ignore[method-assign]
        counter["target"], counter["n"] = str(dst), 0
        try:
            client.get(url)
            reads_per_get = counter["n"]
        finally:
            Path.read_text = real_read_text  # type: ignore[method-assign]
            counter["target"] = None

        get_times = []
        for _ in range(N):
            t0 = time.perf_counter()
            client.get(url)
            get_times.append(time.perf_counter() - t0)

        # One unit of "read + parse", the floor the helpers pay per call.
        unit = []
        for _ in range(N):
            t0 = time.perf_counter()
            json.loads(real_read_text(dst, encoding="utf-8"))
            unit.append(time.perf_counter() - t0)

        # The context-reading block of the route: the 11 helpers (plus the loader after the fix).
        block = []
        with app.test_request_context():
            for _ in range(N):
                t0 = time.perf_counter()
                if mode == "path":
                    for name in HELPERS:
                        getattr(A, name)(str(dst))
                else:
                    ctx = A._load_compose_context(str(dst))
                    for name in HELPERS:
                        getattr(A, name)(ctx)
                block.append(time.perf_counter() - t0)

        out["cases"][label] = {
            "context_bytes": size,
            "reads_per_get": reads_per_get,
            "get_total": summarize(get_times),
            "read_and_parse_once": summarize(unit),
            "helper_block": summarize(block),
        }

    RESULTS.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
```
