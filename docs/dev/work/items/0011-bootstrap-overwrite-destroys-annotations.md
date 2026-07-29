```toml
schema = 1
id = 11
kind = "item"
title = "Bootstrap run overwrites prior annotation work with no merge or versioning"
status = "open"
decision_owner = "agent"
refs = ["blueprints/diagnostics.py:817-820"]
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
