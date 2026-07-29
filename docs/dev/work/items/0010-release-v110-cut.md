```toml
schema = 1
id = 10
kind = "item"
title = "chore/release-v1.1.0 - version bump, CHANGELOG cut, tag"
status = "blocked"
decision_owner = "user"
depends_on = [3, 6, 7, 9]
blocked_on = "everything else landing first, plus the owner's explicit go"
refs = ["RELEASE_ARC.md step 17"]
summary = "Bump pyproject.toml to 1.1.0, cut CHANGELOG [Unreleased] to [1.1.0], tag - last step, on the owner's go."
```

Exact mechanics already verified (per `RELEASE_ARC.md` step 17): bump
`pyproject.toml:7`; rename CHANGELOG's `## [Unreleased]` to
`## [1.1.0] — <date>`, keeping the `### Fixed vulnerabilities` block inside
it (activates the D-7.4 disclosure gate); cut + push tag `v1.1.0`.

## Updates

### 2026-07-28 — filed during chore/work-item-tracking (migrated, depends_on added to make the real sequencing explicit)
