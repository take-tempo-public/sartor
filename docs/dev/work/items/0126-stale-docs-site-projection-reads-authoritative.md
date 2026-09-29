```toml
schema = 1
id = 126
kind = "item"
title = "A stale local docs-site projection reads as authoritative"
status = "open"
decision_owner = "agent"
branches = ["feat/docs-ia-design", "feat/docs-split"]
refs = [
  ".gitignore:134-137",
  "scripts/project_docs_to_mdx.py",
  "docs/dev/reviews/2026-09-docs-ia/10-ux-onboarding.md",
]
summary = "An audit cited a months-stale gitignored docs-site/content/docs/*.mdx as the live site; nothing marks it stale."
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
