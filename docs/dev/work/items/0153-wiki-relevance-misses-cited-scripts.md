```toml
schema = 1
id = 153
kind = "item"
title = "wiki_relevance classifies scripts/gate.py and 8 other wiki-cited scripts as irrelevant"
status = "open"
decision_owner = "agent"
branches = ["fix/hook-guard-false-blocks"]
refs = [
  "scripts/wiki_relevance.py",
  "docs/wiki/pages/code-module-map.md",
]
summary = "RELEVANT_OVERRIDES lists 4 scripts; wiki pages cite 13. gate.py (26 cites) changed and the relevance check missed it."
```

**Observed (2026-10-05, `fix/hook-guard-false-blocks`).**
- `python -c "from scripts.wiki_relevance import is_wiki_relevant as r; print(r('scripts/gate.py'))"`
  prints `False`. The same holds for `scripts/ci_wait.py`, `scripts/work_items.py` and
  `scripts/doc_lints.py`.
- `grep -rhoE "scripts/[a-z_]+\.py" docs/wiki/pages | sort | uniq -c` counts 13 distinct
  `scripts/*.py` files cited by wiki pages. The top ones are `gate.py` (26), `project_docs_to_mdx.py`
  (17), `doc_registry.py` (13), `generate_openapi_spec.py` (12) and `doc_lints.py` (9).
  `RELEVANT_OVERRIDES` (`scripts/wiki_relevance.py:108-116`) lists only
  `generate_openapi_spec.py`, `perf_baseline.py`, `export_corpus_seed.py` and
  `enforcement/guards/route_security_lint.py`.
- Consequence, seen this branch: the branch's diff changed `scripts/gate.py`, and the
  close-out relevance check flagged only `CONTRIBUTING.md` and `maintainer-lane.md`.
  The stale `code-module-map` row was caught by grepping the wiki, not by the classifier.

**Fix direction:** derive the overrides instead of hand-listing them. A test should fail when
a wiki page cites a `scripts/` file the classifier treats as irrelevant. That is the same
dual-check pattern the module's own header names, extended from top-level entries to cited
files.

## Updates

### 2026-10-05 — filed on `fix/hook-guard-false-blocks`
