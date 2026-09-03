```toml
schema = 1
id = 99
kind = "item"
title = "install.md documents two distribution paths that have never been published"
status = "open"
decision_owner = "agent"
branches = ["docs/container-persistence-guidance"]
depends_on = [3]
refs = [
  "docs/install.md:40-71",
  ".github/workflows/docker.yml:12-15",
  ".github/workflows/release.yml",
  "docs/dev/work/items/0003-human-github-toggles.md",
]
summary = "install.md documents a GHCR image and a PyPI wheel that have never been published; every documented path fails."
```

**Found during a live macOS install by a non-maintainer** (2026-09-02). `docs/install.md`
presents `docker run ghcr.io/take-tempo-public/sartor` as "the lowest-friction path" and a
PyPI wheel as the alternative. Neither artifact exists.

**Verified, not inferred** (all four checks run 2026-09-02 with `gh` authenticated, against
a working tree whose other workflows show recent runs):

- `git ls-remote --tags origin` returns **nothing**. All ten local tags (`v0.2.0`
  through `v1.0.9`) exist only in the maintainer's clone.
- `.github/workflows/docker.yml` and `release.yml` both trigger on
  `push: tags: ["v*"]`. Neither has ever run — `gh run list --workflow=` is empty for both.
- `gh release list` is empty.

**Consequence.** A user following the install doc today fails at the first command on any
operating system. The container path fails with a manifest error; the pip path fails with
"no matching distribution". The doc describes an intended future state in the present tense,
with no indication that these are unreleased.

**Distinct from item 3.** Item 3 tracks the owner-only GitHub toggles that gate publication
(and its "repo rename" half is now stale — the remote *is* `take-tempo-public/sartor`).
This item is about the **documentation** asserting availability regardless of whether those
toggles are ever flipped. Both need to be true before install.md is honest; only one is an
agent's to fix.

**Proposed fix.** Until a tag is pushed and both workflows are green, install.md's container
and pip sections need an unmissable pre-release marker, and the source-clone path — the only
one that works today — needs to be documented as the current install method rather than a
developer footnote.

## Updates

### 2026-09-02 — filed from a live macOS install session

Found only because a user got far enough to attempt an install. The macOS version floor
(item 100) blocked the container path first and masked this one; had that user been on a
supported macOS, the image pull would have failed instead.
