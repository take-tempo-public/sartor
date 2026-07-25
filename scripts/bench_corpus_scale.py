"""Tier-1 corpus-scale benchmark — server-side cost per surface, per corpus size.

Measures wall-clock, SQL query count, and response size for the four corpus
surfaces named in carry-forward ledger item 10, across a size curve anchored on
a real corpus shape. No browser, no LLM calls: this is the cheap tier, and it is
the one that establishes complexity ORDER.

Two corpus profiles are seeded because they stress different terms:

``realistic``
    Distinct companies, low near-duplicate density. Models an ordinary corpus.
``duplicate``
    Near-identical companies/titles/dates. Maximizes the pairwise SIMILAR band
    that ``/corpus/merge-suggestions`` renders, isolating that term.

Run one size per invocation to stay well inside a single command's wall clock::

    python -m scripts.bench_corpus_scale --size 1x --profile realistic
    python -m scripts.bench_corpus_scale --all --out docs/dev/perf/data/curve.json

Results are appended to ``--out`` as JSON so a partial run is never lost.
"""

from __future__ import annotations

import argparse
import json
import shutil
import statistics
import tempfile
import time
from pathlib import Path
from typing import Any

# Curve points. Anchored on the real corpus shape (8 experiences / 122 bullets /
# 20 applications) and scaled ratio-preserving, so near-duplicate density stays
# realistic instead of being amplified by scaling roles in isolation.
CURVE: dict[str, dict[str, int]] = {
    "1x": {"experiences": 8, "bullets": 122, "applications": 20},
    "3x": {"experiences": 24, "bullets": 366, "applications": 60},
    "6x": {"experiences": 48, "bullets": 732, "applications": 120},
    "12x": {"experiences": 96, "bullets": 1464, "applications": 240},
}

# Bullet text is generated at realistic length because the pairwise scorer runs
# difflib.SequenceMatcher over bullet text; short filler would understate cost.
_BULLET_TEMPLATES = [
    "Led a {n}-person team through the {sys} migration, cutting {metric} by {pct}% over {mo} months.",
    "Rebuilt the {sys} pipeline in {lang}, reducing {metric} from {a}s to {b}s at peak load.",
    "Owned the {sys} roadmap end to end, shipping {n} releases and lifting {metric} {pct}%.",
    "Partnered with {n} teams to consolidate {sys} tooling, retiring {a} services and saving ${b}k annually.",
    "Introduced {lang} service-level objectives for {sys}, taking {metric} from {a}% to {b}%.",
]
_SYSTEMS = ["billing", "ingest", "identity", "search", "reporting", "scheduling", "payments"]
_LANGS = ["Python", "Go", "TypeScript", "Rust", "Java"]
_METRICS = ["p95 latency", "error rate", "cost per request", "time to recover", "churn"]
_COMPANIES = [
    "Polaris",
    "Northwind",
    "Contoso",
    "Initech",
    "Umbrella",
    "Globex",
    "Vandelay",
    "Stark",
    "Wayne",
    "Tyrell",
    "Cyberdyne",
    "Soylent",
    "Hooli",
    "Pied Piper",
]


def _bullet_text(i: int) -> str:
    """Deterministic realistic-length bullet text (no RNG — runs must be comparable)."""
    t = _BULLET_TEMPLATES[i % len(_BULLET_TEMPLATES)]
    return t.format(
        n=3 + i % 12,
        sys=_SYSTEMS[i % len(_SYSTEMS)],
        lang=_LANGS[i % len(_LANGS)],
        metric=_METRICS[i % len(_METRICS)],
        pct=5 + i % 40,
        mo=2 + i % 10,
        a=1 + i % 9,
        b=1 + (i * 3) % 9,
    )


def _seed(shape: dict[str, int], profile: str, username: str) -> dict[str, Any]:
    """Bulk-seed a corpus of the given shape. One commit per entity tier."""
    from db.models import Application, Bullet, Candidate, Experience, ExperienceTitle
    from db.session import get_session

    n_exp = shape["experiences"]
    n_bullets = shape["bullets"]
    n_apps = shape["applications"]
    per_exp = max(1, round(n_bullets / n_exp))

    session = get_session()
    try:
        cand = Candidate(username=username, name="Bench User")
        session.add(cand)
        session.commit()

        exps = []
        for i in range(n_exp):
            if profile == "duplicate":
                # Near-identical: same company family, drifted dates — the shape
                # the SIMILAR band is designed to catch.
                company = "Polaris Systems" if i % 2 == 0 else "Polaris Systems Inc"
                start = f"20{15 + (i % 2):02d}-0{1 + (i % 9)}"
            else:
                company = _COMPANIES[i % len(_COMPANIES)] + ("" if i < len(_COMPANIES) else f" {i}")
                start = f"20{(i % 20) + 5:02d}-0{1 + (i % 9)}"
            exps.append(
                Experience(
                    candidate_id=cand.id,
                    company=company,
                    start_date=start,
                    end_date=None if i == 0 else f"20{(i % 20) + 6:02d}-01",
                    display_order=i,
                )
            )
        session.add_all(exps)
        session.commit()

        titles = []
        bullets = []
        for i, e in enumerate(exps):
            title = "Senior Engineer" if profile == "duplicate" else f"Engineer L{i % 7}"
            titles.append(
                ExperienceTitle(
                    experience_id=e.id,
                    title=title,
                    is_official=1,
                    is_pending_review=0,
                    source="official",
                )
            )
            for k in range(per_exp):
                # In the duplicate profile bullets repeat across roles, which is
                # what drives both bullet_overlap and shared_bullet_count.
                idx = k if profile == "duplicate" else i * per_exp + k
                bullets.append(
                    Bullet(
                        experience_id=e.id,
                        text=_bullet_text(idx),
                        display_order=k,
                        is_active=1,
                        is_pending_review=0,
                        source="primary:bench.md",
                        has_outcome=1,
                    )
                )
        session.add_all(titles)
        session.add_all(bullets)
        session.commit()

        apps = [
            Application(
                candidate_id=cand.id,
                title=f"Staff Engineer {i}",
                company=_COMPANIES[i % len(_COMPANIES)],
                jd_text=f"Job description body {i}. " * 40,
                jd_fingerprint=f"{i:016x}",
                status="draft",
                is_active=1,
            )
            for i in range(n_apps)
        ]
        session.add_all(apps)
        session.commit()

        return {
            "candidate_id": cand.id,
            "experiences": len(exps),
            "bullets": len(bullets),
            "applications": len(apps),
            "bullets_per_experience": per_exp,
            "first_application_id": apps[0].id if apps else None,
        }
    finally:
        session.close()


class _QueryCounter:
    """Count SQL statements issued during a block — the N+1 detector."""

    def __init__(self) -> None:
        self.count = 0
        self._engine: Any = None

    def __enter__(self) -> _QueryCounter:
        from sqlalchemy import event

        from db.session import get_engine

        self._engine = get_engine()
        event.listen(self._engine, "before_cursor_execute", self._on)
        return self

    def _on(self, *args: Any, **kwargs: Any) -> None:
        self.count += 1

    def __exit__(self, *exc: Any) -> None:
        from sqlalchemy import event

        event.remove(self._engine, "before_cursor_execute", self._on)


def _time_route(client: Any, url: str, repeats: int) -> dict[str, Any]:
    """Time one GET, reporting spread rather than a single number."""
    # One warm-up so import/compile cost is not attributed to the surface.
    warm = client.get(url)
    samples = []
    for _ in range(max(1, repeats)):
        t0 = time.perf_counter()
        client.get(url)
        samples.append((time.perf_counter() - t0) * 1000.0)

    with _QueryCounter() as qc:
        client.get(url)
    queries = qc.count

    body = warm.get_data()
    return {
        "url": url,
        "status": warm.status_code,
        "ms_median": round(statistics.median(samples), 2),
        "ms_min": round(min(samples), 2),
        "ms_max": round(max(samples), 2),
        "queries": queries,
        "bytes": len(body),
        "samples": [round(s, 2) for s in samples],
    }


def run_point(size: str, profile: str, repeats: int) -> dict[str, Any]:
    """Seed one curve point and measure every surface against it."""
    shape = CURVE[size]
    tmp = Path(tempfile.mkdtemp(prefix="bench-corpus-"))
    username = "bench"
    try:
        db_file = tmp / "bench.sqlite"

        import db.session as db_session_mod

        db_session_mod.DEFAULT_DB_PATH = db_file
        db_session_mod._engine = None
        db_session_mod._SessionLocal = None

        from app import create_app
        from config import Config

        app = create_app(Config(base_dir=tmp))
        (tmp / "configs").mkdir(parents=True, exist_ok=True)
        (tmp / "configs" / f"{username}.config").write_text("{}", encoding="utf-8")

        from db.session import init_db

        init_db(db_file)

        t0 = time.perf_counter()
        seeded = _seed(shape, profile, username)
        seed_ms = (time.perf_counter() - t0) * 1000.0

        client = app.test_client()
        surfaces = {
            "corpus_list": f"/api/users/{username}/experiences",
            "merge_suggestions": f"/api/users/{username}/corpus/merge-suggestions",
            "applications": f"/api/users/{username}/applications",
        }
        if seeded["first_application_id"] is not None:
            surfaces["compose_composition"] = (
                f"/api/applications/{seeded['first_application_id']}/composition"
            )

        results = {name: _time_route(client, url, repeats) for name, url in surfaces.items()}
        return {
            "size": size,
            "profile": profile,
            "shape": shape,
            "seeded": seeded,
            "seed_ms": round(seed_ms, 1),
            "repeats": repeats,
            "surfaces": results,
        }
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def run_render(size: str, profile: str) -> dict[str, Any]:
    """Tier 2 — measure what the Corpus tab actually renders at this corpus size.

    Tier 1 says what the server costs; this says what the browser is handed.
    Deliberately narrow: DOM node counts and rendered pixel heights, plus the
    wall-clock to settle. Sizes and node counts are stable quantities; the
    settle time is reported but is the noisiest number here and should be read
    as an order of magnitude, not a benchmark.
    """
    import threading

    from playwright.sync_api import sync_playwright
    from werkzeug.serving import make_server

    shape = CURVE[size]
    tmp = Path(tempfile.mkdtemp(prefix="bench-render-"))
    username = "bench"
    try:
        db_file = tmp / "bench.sqlite"

        import db.session as db_session_mod

        db_session_mod.DEFAULT_DB_PATH = db_file
        db_session_mod._engine = None
        db_session_mod._SessionLocal = None

        from app import create_app
        from config import Config

        app = create_app(Config(base_dir=tmp))
        for key in ("configs", "output", "resumes"):
            (tmp / key).mkdir(parents=True, exist_ok=True)
        app.config["CONFIGS_DIR"] = tmp / "configs"
        app.config["OUTPUT_DIR"] = tmp / "output"
        app.config["RESUMES_DIR"] = tmp / "resumes"
        (tmp / "configs" / f"{username}.config").write_text("{}", encoding="utf-8")

        from db.session import init_db

        init_db(db_file)
        _seed(shape, profile, username)

        server = make_server("127.0.0.1", 0, app, threaded=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch()
                page = browser.new_page(viewport={"width": 1280, "height": 900})
                try:
                    from ui_pages.selectors import Corpus, Help, TopTabs, UserPicker

                    # Without this the first-run help/tour modal's full-screen
                    # backdrop intercepts the tab click. Same suppressor the UX
                    # suite and capture_screenshots.py use.
                    page.add_init_script(
                        Help.suppress_tour_init_script(list(Help.TOUR_STOP_BLOCKS))
                    )
                    page.goto(base, wait_until="networkidle")

                    page.wait_for_selector(UserPicker.SELECT, timeout=30_000)
                    page.select_option(UserPicker.SELECT, username)
                    page.wait_for_function(
                        "(u) => document.getElementById('userSelect').value === u",
                        arg=username,
                        timeout=30_000,
                    )

                    # refreshCorpus() fires refreshMergeSuggestions() fire-and-forget,
                    # so `networkidle` can go quiet BEFORE that request is even issued
                    # — measuring there reports an empty panel that later fills in.
                    # Synchronize on the merge-suggestions response itself, then flush
                    # two animation frames so the synchronous append has painted.
                    t0 = time.perf_counter()
                    with page.expect_response(
                        lambda r: "corpus/merge-suggestions" in r.url, timeout=300_000
                    ):
                        page.click(TopTabs.CORPUS)
                        page.wait_for_selector(Corpus.PANEL, state="visible", timeout=60_000)
                    page.wait_for_selector(Corpus.CARD, timeout=120_000)
                    page.evaluate(
                        "() => new Promise(r => requestAnimationFrame("
                        "() => requestAnimationFrame(r)))"
                    )
                    settle_ms = (time.perf_counter() - t0) * 1000.0

                    metrics = page.evaluate(
                        """() => {
                            const box = (id) => {
                                const el = document.getElementById(id);
                                if (!el) return null;
                                return {
                                    scrollHeight: el.scrollHeight,
                                    children: el.children.length,
                                    nodes: el.querySelectorAll('*').length,
                                };
                            };
                            return {
                                mergeSuggestionsList: box('mergeSuggestionsList'),
                                corpusExperienceList: box('corpusExperienceList'),
                                documentNodes: document.querySelectorAll('*').length,
                                documentScrollHeight:
                                    document.documentElement.scrollHeight,
                            };
                        }"""
                    )
                    return {
                        "size": size,
                        "profile": f"{profile}+render",
                        "shape": shape,
                        "settle_ms": round(settle_ms, 1),
                        "render": metrics,
                    }
                finally:
                    browser.close()
        finally:
            server.shutdown()
            thread.join(timeout=5)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def measure_existing(db_path: Path, username: str, repeats: int) -> dict[str, Any]:
    """Measure the surfaces against an ALREADY-POPULATED database.

    Calibration path: a shape-matched synthetic corpus can still misstate cost,
    because the pairwise scorer runs difflib over bullet TEXT and difflib is
    quadratic in string length. Pointing this at a real database replaces the
    estimate with the real number. Read-only apart from the schema upgrade
    ``init_db`` performs, so point it at a COPY, never at a live database.
    """
    from db.models import Application, Bullet, Candidate, Experience

    tmp = Path(tempfile.mkdtemp(prefix="bench-existing-"))
    try:
        import db.session as db_session_mod

        db_session_mod.DEFAULT_DB_PATH = db_path
        db_session_mod._engine = None
        db_session_mod._SessionLocal = None

        from app import create_app
        from config import Config

        app = create_app(Config(base_dir=tmp))
        (tmp / "configs").mkdir(parents=True, exist_ok=True)
        (tmp / "configs" / f"{username}.config").write_text("{}", encoding="utf-8")

        from db.session import get_session, init_db

        init_db(db_path)

        session = get_session()
        try:
            cand = session.query(Candidate).filter_by(username=username).first()
            if cand is None:
                raise SystemExit(f"no candidate {username!r} in that database")
            n_exp = session.query(Experience).filter_by(candidate_id=cand.id).count()
            exp_ids = [
                e.id for e in session.query(Experience).filter_by(candidate_id=cand.id).all()
            ]
            n_bullets = (
                session.query(Bullet)
                .filter(Bullet.experience_id.in_(exp_ids), Bullet.is_active == 1)
                .count()
                if exp_ids
                else 0
            )
            apps = session.query(Application).filter_by(candidate_id=cand.id).all()
            shape = {
                "experiences": n_exp,
                "bullets": n_bullets,
                "applications": len(apps),
            }
            first_app = apps[0].id if apps else None
        finally:
            session.close()

        client = app.test_client()
        surfaces = {
            "corpus_list": f"/api/users/{username}/experiences",
            "merge_suggestions": f"/api/users/{username}/corpus/merge-suggestions",
            "applications": f"/api/users/{username}/applications",
        }
        if first_app is not None:
            surfaces["compose_composition"] = f"/api/applications/{first_app}/composition"

        return {
            "size": "real",
            "profile": "real",
            "shape": shape,
            "seeded": {"source": "existing database"},
            "repeats": repeats,
            "surfaces": {n: _time_route(client, u, repeats) for n, u in surfaces.items()},
        }
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _append(out: Path, record: dict[str, Any]) -> None:
    """Append a result, so a partial or interrupted run is never lost."""
    out.parent.mkdir(parents=True, exist_ok=True)
    existing: list[dict[str, Any]] = []
    if out.exists():
        try:
            existing = json.loads(out.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = []
    existing = [
        r
        for r in existing
        if not (r["size"] == record["size"] and r["profile"] == record["profile"])
    ]
    existing.append(record)
    out.write_text(json.dumps(existing, indent=2), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--size", choices=sorted(CURVE), help="one curve point")
    ap.add_argument("--all", action="store_true", help="every curve point")
    ap.add_argument("--profile", choices=["realistic", "duplicate"], default="realistic")
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--out", type=Path, default=Path("docs/dev/perf/data/large-corpus-curve.json"))
    ap.add_argument(
        "--db",
        type=Path,
        help="measure an already-populated database instead of seeding (point at a COPY)",
    )
    ap.add_argument("--username", default="bench", help="candidate username for --db")
    ap.add_argument(
        "--render",
        action="store_true",
        help="Tier 2 — measure browser render cost instead of server cost",
    )
    args = ap.parse_args()

    if args.render:
        if not args.size:
            ap.error("--render needs --size")
        rec = run_render(args.size, args.profile)
        _append(args.out, rec)
        r = rec["render"]
        print(f"--- {args.size} / {args.profile} / render ---", flush=True)
        print(f"  settle {rec['settle_ms']:.0f}ms", flush=True)
        for key in ("mergeSuggestionsList", "corpusExperienceList"):
            box = r[key]
            if box is None:
                print(f"  {key:22s} (absent)", flush=True)
            else:
                print(
                    f"  {key:22s} height={box['scrollHeight']:7d}px  "
                    f"children={box['children']:5d}  nodes={box['nodes']:6d}",
                    flush=True,
                )
        print(
            f"  {'document':22s} height={r['documentScrollHeight']:7d}px  "
            f"nodes={r['documentNodes']:6d}",
            flush=True,
        )
        print(f"\nwrote {args.out}")
        return 0

    if args.db:
        rec = measure_existing(args.db, args.username, args.repeats)
        _append(args.out, rec)
        print(f"--- real / {rec['shape']} ---", flush=True)
        for name, r in rec["surfaces"].items():
            print(
                f"  {name:22s} status={r['status']} "
                f"{r['ms_median']:9.2f}ms (min {r['ms_min']:.2f} / max {r['ms_max']:.2f})  "
                f"queries={r['queries']:5d}  bytes={r['bytes']}",
                flush=True,
            )
        print(f"\nwrote {args.out}")
        return 0

    sizes = sorted(CURVE, key=lambda s: CURVE[s]["experiences"]) if args.all else [args.size]
    if not sizes or sizes == [None]:
        ap.error("pass --size or --all")

    for size in sizes:
        print(f"--- {size} / {args.profile} ---", flush=True)
        rec = run_point(size, args.profile, args.repeats)
        _append(args.out, rec)
        for name, r in rec["surfaces"].items():
            print(
                f"  {name:22s} status={r['status']} "
                f"{r['ms_median']:9.2f}ms (min {r['ms_min']:.2f} / max {r['ms_max']:.2f})  "
                f"queries={r['queries']:5d}  bytes={r['bytes']}",
                flush=True,
            )
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
