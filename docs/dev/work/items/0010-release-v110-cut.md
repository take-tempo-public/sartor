```toml
schema = 1
id = 10
kind = "item"
title = "chore/release-v1.1.0 - version bump, CHANGELOG cut, tag"
status = "blocked"
decision_owner = "user"
epic = 40
depends_on = [3, 6, 7, 9, 19]
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

### 2026-07-29 — owner directs the UX-flake sprint (item 19) must land before this cut

`depends_on` widened from `[3, 6, 7, 9]` to `[3, 6, 7, 9, 19]` — owner direction, captured on
`fix/eval-judge-parse-failure`, that item 19 (UX-suite flakiness solution sprint) must be
solved before v1.1.0, not just scheduled alongside it. See item 19's own 2026-07-29 update and
`docs/dev/diagnosis/ux-scroll-position-flake.md` O-14 for the evidence that prompted this.

### 2026-08-04 — folded into Final March epic E (sprint E1)

This item is the terminal step of epic 40; its mechanics are unchanged. The march
adds the pre-tag gate list (eval smoke, wiki-lint, compliance-witness, fresh-clone
re-verify, the type-scan) and the post-tag steps (PyPI publish verification,
`gh release create`) around it — see `RELEASE_ARC.md` §"v1.1.0 Final March" epic E.
