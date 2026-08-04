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
