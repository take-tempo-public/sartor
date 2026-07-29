```toml
schema = 1
id = 11
kind = "item"
title = "Bootstrap run overwrites prior annotation work with no merge or versioning"
status = "closed"
decision_owner = "agent"
resolution = "Fixed on fix/bootstrap-annotation-overwrite: every run now writes a never-colliding bootstrap-<timestamp>.json (bootstrap.json kept only as a disposable latest-mirror for backward compat); reads pin to whatever annotations.json's own bootstrap_source names, when it still exists, so a later run can no longer even semantically hijack an in-progress annotation's cluster_index. Reproduced live first (docs/dev/diagnosis/bootstrap-annotation-overwrite.md) with a new regression test, tests/test_annotation_routes.py::TestBootstrapStream::test_second_run_does_not_destroy_first_runs_bootstrap, which fails on the pre-fix code and passes after."
refs = ["blueprints/diagnostics.py:_resolve_bootstrap_path", "blueprints/diagnostics.py:_new_bootstrap_path", "docs/dev/diagnosis/bootstrap-annotation-overwrite.md"]
summary = "Every /api/annotation/bootstrap call overwrites bootstrap.json wholesale - no merge, no versioning, no history."
```

Found 2026-07-28 exercising the real annotate/bootstrap workflow. Every
"Run bootstrap" click does an unconditional full overwrite:
`(fixture_dir / "bootstrap.json").write_text(...)` (`blueprints/diagnostics.py:817-820`),
built only from `result["per_jd"]`, itself built only from the JDs in that
one POST body. There is no read-existing-and-merge step anywhere in the
route. This is true regardless of the grounding-scorers checkbox — running
the same JD twice (once without grounding, once with) is enough to trigger
it, since `generate()` is non-deterministic and re-clusters from scratch
each run.

Live-confirmed on the `robert-bootstrap` fixture: the currently-saved
`annotations.json` (32 bullets, all carefully human-verdicted) points at
`cluster_index` values up to 31, but the current `bootstrap.json` only has
31 clusters (indices 0-30) — one index is provably orphaned from a
generation that no longer exists on disk. Real annotation work — an
expensive, time-consuming human process — was silently discarded.

Owner-directed fix shape: **never overwrite.** Use a versioned/timestamped
naming scheme for bootstrap runs (preserving uniqueness + provenance)
instead of one fixed `bootstrap.json` path per slug, so a later run adds a
new, dated artifact rather than destroying the prior one. Related: item 14
(no JD-identifying metadata) is the same underlying gap from a different
angle — a provenance-bearing naming scheme would likely fix both together.

## Updates

### 2026-07-28 — filed during chore/work-item-tracking

### 2026-07-29 — closed on fix/bootstrap-annotation-overwrite

The original `robert-bootstrap` fixture cited above no longer exists in this
clone (`evals/fixtures/real/` is gitignored real user data, since rotated) —
its exact numbers could not be re-verified, so the fix was proven instead
with a fresh, on-demand live reproduction (see the diagnosis doc). Item 14's
"same underlying gap" note above turned out to be only partially true: this
fix adds RUN provenance (a timestamped filename, surfaced in the bootstrap
SSE `done` event as `bootstrap_file`) but not JD-NAME provenance (company/
role) — item 14 remains open, unresolved by this fix. Item 13 (anchor-JD
selection) is also untouched — `pick_anchor_jd`'s widest-cluster-span
heuristic is unchanged; this fix only guarantees collate reads the bootstrap
version an annotation was actually built from, not that anchor selection
matches what the annotation data represents.
