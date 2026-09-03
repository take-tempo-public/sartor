```toml
schema = 1
id = 3
kind = "item"
title = "[HUMAN] GitHub toggles: repo rename, PyPI Trusted Publisher, GHCR visibility, enforce_admins"
status = "blocked"
decision_owner = "user"
blocked_on = "owner-only GitHub settings actions, no repo file changes; enforce_admins is a standing open decision"
refs = ["docs/dev/RELEASE_CHECKLIST.md:1397-1418", "RELEASE_ARC.md step 16"]
summary = "Repo rename to take-tempo-public/sartor gates PyPI Trusted Publisher + GHCR visibility; enforce_admins still false."
```

Merges two previously-separate entries that were the same underlying
blocker: `RELEASE_CHECKLIST.md`'s PyPI-wheel row ("still open: [HUMAN], the
PyPI Trusted Publisher config + GHCR package visibility, both blocked on the
GitHub repo rename") and `RELEASE_ARC.md` step 16. The packaging fix itself
landed (`fix/packaging-install`, `chore/packaging-floor`) — only the
owner-only GitHub-settings actions remain: (a) rename repo to
`take-tempo-public/sartor` + flip public; (b) PyPI Trusted Publisher —
project `sartor`, environment `pypi`; (c) GHCR package visibility → public;
(d) `enforce_admins` on `main` branch protection — currently `false`, so an
admin can bypass the 6 required checks; standing open decision, not
resolved by this item.

## Updates

### 2026-07-28 — filed during chore/work-item-tracking (migrated, merged two duplicate entries)

### 2026-09-02 — partially stale; publication state verified

Found while a non-maintainer attempted a live install (item 99).

- **(a) is done.** The remote is already `https://github.com/take-tempo-public/sartor` —
  this item's "blocked on the repo rename" framing no longer holds.
- **Nothing has been published regardless.** Verified with `gh` authenticated:
  `git ls-remote --tags origin` returns nothing (all ten local tags `v0.2.0`–`v1.0.9` are
  local-only), `gh run list` is empty for both `release.yml` and `docker.yml`, and
  `gh release list` is empty. Both workflows trigger on `push: tags: ["v*"]`, so neither has
  ever fired.
- So (b) PyPI Trusted Publisher and (c) GHCR visibility remain untested rather than merely
  unset — the first tag push is what will exercise them.
