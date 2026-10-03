```toml
schema = 1
id = 145
kind = "item"
title = "Stdlib launcher (doctor/install/up/down/status/logs/update/open) + per-OS pushbutton wrappers"
status = "open"
decision_owner = "agent"
branches = ["chore/release-v1.1.0"]
refs = ["app.py", "Dockerfile", ".github/workflows/release.yml", ".github/workflows/docker.yml", "docs/dev/work/items/0099-*.md", "docs/dev/work/items/0100-*.md"]
summary = "Owner pre-launch requirement (2026-08-16), unfiled till now: stdlib launcher, two backends, per-OS one-click wrappers."
```

**Owner decisions, 2026-08-16** (chat, sartor session `77c25381`). Until now they lived only in
the agent's memory note `project-launch-requirements-launcher-pushbutton`, which says the work
items were "owed on the next branch". A grep of `docs/dev/work/items/` on 2026-10-02 found none
filed. They are filed here on the owner's direction.

1. **Both distribution paths stay.**
   - The app wheel on PyPI (`release.yml`).
   - The GHCR container (`Dockerfile` + `docker.yml`).
   - The container is the encouraged default; the wheel is the dev / opt-out path.
2. **One thin stdlib launcher on PyPI,** with the verbs `doctor / install / up / down / status /
   logs / update / open` and two backends:
   - **`install --container`:** pull GHCR by tag/digest, using Podman or Docker.
     `-p 127.0.0.1:5000:5000 -v sartor-data:/data -e SARTOR_HOME=/data`.
   - **`install --native`:** a managed venv; pip the app wheel; run `--setup`.
   - **`up` opens the host browser.** The image sets `SARTOR_NO_BROWSER=1`, because
     `webbrowser.open` inside the container can't reach the host.
   - Add a `HEALTHCHECK` to the image.
   - Collapse install.md's five `-v` mounts to the single `SARTOR_HOME` root.
3. **Per-OS pushbutton wrappers for both paths:** `sartor.cmd` (Windows), `sartor.command` (mac),
   `sartor.sh` + `.desktop` (Linux).
   - Each is a thin "python present? → `pip install --user sartor` → `sartor up`" wrapper.
   - All the logic lives in the Python launcher.
   - On Windows, `doctor` says plainly that the container backend needs WSL2 plus Podman or
     Docker Desktop, and points at the native path as the fallback.
4. **Rejected: bundling a browser in the image.** Use the host browser via the port map.

**Depends on:**
- **Item 146** (health endpoint and single-instance check). `up`, `status` and `down` are built
  on it.
- **Item 3** (PyPI/GHCR publish) for the end-to-end path.

**Sequencing (owner, 2026-10-02):** part of the Open drawdown before the 1.1.0 alpha. The
owner's fresh-clone e2e test exercises it.

## Updates

### 2026-10-02 — filed on `chore/release-v1.1.0` (owner-directed)
