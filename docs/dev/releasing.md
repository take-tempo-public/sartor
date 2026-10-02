# Releasing Sartor — the one-time publishing setup

> **Purpose:** the maintainer runbook for publishing Sartor: the one-time console setup
> that CI can't do, and the recurring tag that fires both publish workflows. Moved out of
> the user install guide in Epic D sprint D3, because a first-time installer never needs it.
> **Audience:** `dev` — the maintainer (the steps below are `[HUMAN]`: they need GitHub,
> PyPI and GHCR console access).
> **Authoritative for:** the publishing prerequisites and the release trigger. Versioning
> rules live in [`../governance/charter.md`](../governance/charter.md) (D-7); the
> release-cut checklist lives in [`RELEASE_ARC.md`](RELEASE_ARC.md) (Epic E); publication
> status is tracked in
> [`work/items/0099-install-docs-document-unpublished-paths.md`](work/items/0099-install-docs-document-unpublished-paths.md).

> **Status, re-verified 2026-09-29 (first verified 2026-09-02): nothing has been published.**
> `git ls-remote --tags origin` returns no tags (all local tags `v0.2.0`–`v1.0.9`
> exist only in the maintainer's clone), `gh release list` is empty, and neither
> workflow below has ever run. Until step 5 happens, the container and PyPI
> sections of [`docs/user/install.md`](../user/install.md) describe an intended future state, and the source clone is the
> only working install.

Two workflows do the release automatically on a version tag (`vX.Y.Z`):
[`docker.yml`](../../.github/workflows/docker.yml) builds + pushes the multi-arch
image to `ghcr.io/take-tempo-public/sartor`; [`release.yml`](../../.github/workflows/release.yml)
builds the wheel and publishes to PyPI via **Trusted Publishing** (OIDC, no
stored token). A maintainer only does the console setup CI can't do, then pushes
the tag:

1. **GitHub** — create org + repo `take-tempo-public/sartor` (the image namespace,
   the PyPI publisher, and the in-app citation URLs all key off it).
2. **PyPI** — [pypi.org](https://pypi.org) → *Your account → Publishing* → add a
   pending publisher: project `sartor`, owner `take-tempo-public`, repo `sartor`,
   workflow `release.yml`, environment `pypi`. Then in the GitHub repo →
   *Settings → Environments* → create the `pypi` environment.
3. **GHCR** — after the first image push, set the package public and link it to the
   repo (org → Packages → package settings).
4. **Un-gate PyPI** — the `release.yml` publish job is intentionally gated (a `GATE`
   step) until the wheel ships the app's data dirs. Fix that packaging follow-up,
   verify a fresh-venv `pip install <wheel>` serves a page, then delete the `GATE`
   step. Until then, ship via the container or a source install.
5. **Each release (recurring)** — bump `version` in `pyproject.toml`, commit/merge,
   then `git tag vX.Y.Z && git push --tags`. The tag fires both workflows.
