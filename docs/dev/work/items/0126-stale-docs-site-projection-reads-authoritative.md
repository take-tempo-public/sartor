```toml
schema = 1
id = 126
kind = "item"
title = "A stale local docs-site projection reads as authoritative"
status = "closed"
decision_owner = "agent"
branches = ["feat/docs-assets-enforcement", "feat/docs-ia-design", "feat/docs-split"]
refs = [
  ".gitignore:134-137",
  "scripts/project_docs_to_mdx.py",
  "docs/dev/reviews/2026-09-docs-ia/10-ux-onboarding.md",
]
summary = "An audit cited a months-stale gitignored docs-site/content/docs/*.mdx as the live site; nothing marks it stale."
resolution = "Fixed on feat/docs-assets-enforcement (Epic D D4, 2026-10-01). Every projected page now carries the commit it came from: sourceCommit in its frontmatter, plus a visible banner comment. +uncommitted marks a projection made from local source edits. scripts/check_docs_projection_fresh.py compares the stamps to HEAD. On the July-era local copy it reported STALE (36 unstamped pages); after re-projection it reported OK. Stated limit (C-0): nothing forces the check to run before someone reads the files; the stamp in every page is the always-visible half."
verified_by = [
  "tests/test_docs_site_checks.py (test_every_projected_page_is_stamped, test_verdict_fresh_only_when_every_page_is_from_head, test_stamps_reads_a_long_frontmatter)",
  "scripts/check_docs_projection_fresh.py (exit 1 on stale/unstamped/mixed/uncommitted)",
]
```

**Observed.** During D1, the UX-onboarding auditor read a 2026-07-26 local copy of the
gitignored projection (`docs-site/content/docs/*.mdx`) as the published site. Its headline
finding was void as a result (correction block at the top of `10-ux-onboarding.md`). This is a
member of a known class: treating a derived copy as the source.

**Not fixed by D2.** The publication registry (`scripts/doc_registry.py`) controls *what* is
projected, not whether a local copy is current.

**Candidate mechanism (D4):** the projector stamps each generated file with the source
commit (frontmatter), so a stale copy is visibly stale. A check could also compare the stamp
to `HEAD`.

## Updates

### 2026-09-28 — filed on `feat/docs-split` (Epic D D2), carried from the D1 handoff
