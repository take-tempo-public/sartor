```toml
schema = 1
id = 101
kind = "item"
title = "Container quickstart defaults to a throwaway container and hides a bind-mount trap"
status = "open"
decision_owner = "agent"
branches = ["docs/container-persistence-guidance"]
refs = [
  "docs/install.md:46-71",
  "Dockerfile:37-56",
  ".dockerignore:33-39",
  "blueprints/generation.py:1699-1721",
]
summary = "Documented `podman run` makes a throwaway container; bind-mounting /app/db would break startup."
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
