```toml
schema = 1
id = 101
kind = "item"
title = "Container quickstart defaults to a throwaway container and hides a bind-mount trap"
status = "closed"
decision_owner = "agent"
branches = [
  "feat/install-onboarding-preflight","docs/container-persistence-guidance"]
refs = [
  "docs/install.md:46-71",
  "Dockerfile:37-56",
  ".dockerignore:33-39",
  "blueprints/generation.py:1699-1721",
]
summary = "Documented `podman run` makes a throwaway container; bind-mounting /app/db would break startup."
resolution = "Rewritten on feat/install-onboarding-preflight (2026-09-03). The named, volume-bearing `podman run` is now the primary command; the bare form is explicitly a throwaway and carries --rm so the discard is visible rather than leaving an unnamed orphan holding a corpus. The named-volume-vs-bind-mount rule is stated WITH ITS REASON (db/ is a Python package baked into the image plus the recall index, so a bind mount over /app/db shadows it and the app fails to import db at startup; only output/, configs/ and resumes/ are excluded from the image and safe to bind-mount). Adds host-access guidance -- the app's own browser download needs no mount at all, which is the right answer for one-off retrieval -- and the `podman ps -a` / `podman start` recovery line. README carried the same bare-run command and is corrected alongside. TWO CLAIMS ARE MARKED UNVERIFIED RATHER THAN ASSERTED OR SILENTLY DROPPED (C-0/C-12): rootless-Podman bind-mount writability for uid 10001, and whether a fresh /app/db mount shadows the baked recall index. The latter WAS previously stated as fact at install.md:69; named-volume copy-up semantics suggest it is wrong for the named form now recommended, and it was never verified either way, so the claim is removed rather than restated. Neither can be settled without a container run on supported hardware, and item 99 established the image has never been published -- so the guidance is written, the two gaps are declared, and the verification is owed when an image first ships."
verified_by = [
  "tests/test_doc_links.py (the new install.md anchors resolve, incl. the one README now links to)",
  "docs/install.md 'Named volumes, not bind mounts' section + README container block (both carry the rule and the reason; a reviewer can diff them against Dockerfile:37-56 and .dockerignore:33-39)",
]
```

**Found while answering a user's question about container persistence** (2026-09-02).

**The default is data loss.** `docs/install.md:46-53` presents a bare `docker run` /
`podman run` — no `-v`, no `--name`, no `--rm` — as *the* container path. The `Dockerfile`
declares no `VOLUME`, so every write under `/app` lands in the container's writable overlay
layer. Data survives `stop`→`start` of the same container, but a second `run` creates a new
container with an empty layer. Because the documented command also omits `--name`, the first
container becomes an unnamed entry in `podman ps -a` the user has no reason to know holds
their corpus. Volumes appear afterwards under a "Persisting your data" heading, reading as
an optional enhancement rather than the correct default.

**The sharp edge: `/app/db` and `/app/personas` must be named volumes, never bind mounts.**
`db/` is not a data directory — it is a Python package baked into the image (`__init__.py`,
`models.py`, `session.py`, `migrations/`) plus the vector index built at `Dockerfile:49`;
`.dockerignore:38-39` keeps `personas/bundled/` in the image via `!personas/bundled/`. A
user who reads "mount volumes to keep them across runs" and reaches for the bind-mount form
they know shadows the package and the app fails to import `db` at startup. The doc's example
happens to use named volumes but never says the distinction is load-bearing, so it does not
survive being adapted. `output/`, `configs/` and `resumes/` are excluded from the image
(`.dockerignore:33-37`) and are the only three safe to bind-mount.

**No host-access guidance.** The doc never covers getting generated files onto the host, nor
that the app's own download route (`/api/download/<path>`, `send_file(as_attachment=True)`)
already does this with no mount at all — which is the right answer for one-off retrieval and
makes most of the volume complexity unnecessary for a first-time user.

**Unverified, stated rather than asserted (C-0/C-12):** a host bind mount is not writable by
the container's uid 10001 (`Dockerfile:53`) under rootless Podman without
`--userns=keep-id:uid=10001,gid=10001`. Reasoned from the image definition; never executed.
Also unresolved: `install.md:69` claims a fresh `/app/db` mount shadows the baked recall
index, which volume copy-up semantics suggest is wrong for a *named* volume. Both need a run
on supported hardware to settle.

**Proposed fix.** Promote the volume-bearing command with `--name` to the primary path;
demote the bare form to an explicit "data is discarded" note; state the
named-volume-vs-bind-mount rule with its reason; add a host-access section covering both the
bind mount and the browser download; add the `podman ps -a` / `podman start` recovery line.

## Updates

### 2026-09-02 — filed from a live macOS install session

Drafted before the session discovered the image was never published (item 99). The guidance
is still owed — it just cannot be tested until an image exists.
