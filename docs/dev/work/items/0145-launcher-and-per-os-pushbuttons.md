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

### 2026-10-16 — taken up (owner pick); cut into three branches

Owner decisions, chat, 2026-10-15/16:

- **Keep 145 whole, in three sequential branches:**
  1. `feat/data-root` — every user-data writer honours `SARTOR_HOME`, plus the Dockerfile
     `SARTOR_HOME`/`VOLUME`/`HEALTHCHECK` and `install.md`'s single mount. Dossier:
     `docs/dev/blast-radius/data-root.md`.
  2. `feat/launcher` — the launcher and both backends.
  3. `feat/pushbuttons` — the per-OS wrappers.
- **Shape: one distribution, `sartor`, with a stdlib-only core.** The verbs import only the stdlib;
  the server is imported lazily; the heavy dependencies move to a `sartor[app]` extra that
  `install --native` puts in a managed venv. No second distribution name.
- **Why:** the launcher serves the two *published* paths (wheel, GHCR container), not the source
  clone. Nothing is published yet (item 3), so the end-to-end test waits on it; branch 1 does not.

Why branch 1 comes first: item 2's `-v sartor-data:/data -e SARTOR_HOME=/data` loses the SQLite DB,
the LLM log, `.api_key` and the onboarding CLI's paths today, because only `config._default_base_dir()`
reads `SARTOR_HOME` (enumeration in the dossier above).

**Branch 2 outline (not started; written down so it survives this session):**

- A stdlib-only `sartor_cli/` package: dispatch, state file, a `Runner` protocol for subprocesses,
  a lazy `serve`, a `doctor` reusing stdlib `preflight` and `instance`.
- Native backend: a managed venv with `sartor[app]==V`. Container backend: Podman, then Docker;
  `create -p 127.0.0.1:P:5000 -v sartor-data:/data -e SARTOR_HOME=/data`.
- Dependencies move to the `[app]` extra, with `dev` self-referencing it; the entry point becomes
  `sartor_cli.main:main`; bare `sartor` keeps serving in a clone. An AST stdlib-only boundary test;
  a two-phase `release.yml` smoke.
- **First commit is an instrument** (C-7): does a built wheel ship `alembic.ini` (H3) and
  `personas/cover_letter.html` (H4)? Both are hypotheses from reading code.
- **Owner questions at its start:** the C-2 wording (charter.md:98-100 names "the single-instance
  probe"; the launcher adds a loopback shutdown POST and a health read); the PEP 668 fallback for
  `pip install --user`; whether bare `sartor` with no runtime runs `up`; H2 (the image's index build
  may always fall to its WARN branch); separate native/container data; whether `sartor` is free on PyPI.

**Branch 3 outline:** `packaging/launchers/{windows/sartor.cmd, macos/sartor.command,
linux/sartor.sh + sartor.desktop}`, each three steps (find Python 3.11+, `pip install --user sartor`
only if `import sartor_cli` fails, then `python -m sartor_cli up`); `.gitattributes` EOL rules and the
exec bit in the index; static plus stub-Python tests; the Gatekeeper and Mark-of-the-Web caveats documented.
