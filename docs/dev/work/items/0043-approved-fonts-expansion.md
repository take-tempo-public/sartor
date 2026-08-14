```toml
schema = 1
id = 43
kind = "item"
title = "Approved-fonts list expansion beyond Arial/Calibri/Georgia"
status = "deferred"
decision_owner = "user"
blocked_on = "post-1.1.0 - additions only after per-font ATS verification, owner-gated"
refs = ["docs/dev/RELEASE_ARC.md", "docs/template_authoring.md"]
summary = "v1.1.0 ships an approved-fonts list of Arial, Calibri, Georgia (sprint B2); verified additions considered later."
```

Owner-captured 2026-08-03: the ATS conformance pass (sprint B2) enforces an
approved-fonts list of exactly Arial, Calibri, and Georgia. Possible additions
come later, one at a time, once verified ATS-safe.

## Updates

### 2026-08-04 — filed during chore/v11-march-kickoff

### 2026-08-14 — B2 landed the list (`feat/ats-conformance`)

The dependency this item waits on is now satisfied: `json_resume.APPROVED_FONTS`
(Arial/Calibri/Georgia) + `map_to_approved_font` shipped, enforced at every
output write boundary and gated by `tests/test_ats_structure.py` (allow-list-
exact assertions on generated `.docx`). Expansion remains deferred and
owner-gated — adding a family is now: extend `APPROVED_FONTS` + `_FONT_MAP`,
and the structural gate accepts it everywhere at once.
