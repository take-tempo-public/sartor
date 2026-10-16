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

**Branch 1 (`feat/data-root`) — what it did, and what it leaves open.** Evidence is in the dossier's
`## Observed` (O1–O6); this lists only the obligations.

- *Done and observed:* every user-data writer now follows `SARTOR_HOME` through `sartor_home.py`
  (12 of 13 probed sites ignored it before, 13 of 13 follow it after); bundled personas resolve from
  the shipped directory (download route: 404 before, 200 after, on the real app); a derived-set test
  fails when an unclassified runtime file anchors a path on itself.
- *Open, container (needs the owner's go-ahead; a build installs Chromium through the owner's Podman
  machine):* build the image and observe (a) `HEALTHCHECK` reaching `healthy`, (b) a named `/data`
  volume taking uid 10001 ownership under **rootless** Podman, (c) data surviving `rm` and recreate,
  (d) `podman stop` time with and without `STOPSIGNAL SIGINT` (Python as PID 1 may ignore SIGTERM; a
  prediction, not an observation). Only then consider `/app` root-owned (so a writer that missed
  `SARTOR_HOME` fails loudly). **Before a local build, run `git ls-files --eol Dockerfile`**: this
  machine's working copy is CRLF (`core.autocrlf=true`) though the committed blob is LF.
- *Open, hypothesis H2 (first instrument of branch 2):* the image's recall-index build probably always
  falls to its `WARN` branch, because `.dockerignore:6` drops `.git` and
  `scripts/build_vector_index.py:55-67` `_git()` raises `SystemExit` on a git failure. Also affects a
  wheel's `--setup`. `install.md` now says the index claim is unchecked; it is not fixed.
- *Open, not observed:* the template **preview** route under `SARTOR_HOME` (it shares the fixed helper;
  tested only for a checkout); a real installed wheel (the same code path as `SARTOR_HOME`, argued from
  `config.bundled_personas_dir`, not run).
- *Left for branch 2:* `platformdirs` has no runtime importer now (only the parity test), so it moves
  to the dev extra when the dependencies are reorganised. **H4 stands:** `personas/cover_letter.html`
  sits outside every package, so a wheel does not ship it. Branch 1 only made the routes read it from
  the code root (`Config.cover_letter_shell`), which is right for a checkout and the container image
  (`/app/personas/`) and still wrong for a wheel; `generator.py:363` has always read it from the code
  root. The cover-letter preview under `SARTOR_HOME` was a second find of the bundled-persona class
  (dossier O7), caught late: the Dockerfile edit would otherwise have broken the container's preview.
- *Open, not observed:* the second cover-letter site (`preview_edited_html`) under `SARTOR_HOME`.

**Branch 3 outline:** `packaging/launchers/{windows/sartor.cmd, macos/sartor.command,
linux/sartor.sh + sartor.desktop}`, each three steps (find Python 3.11+, `pip install --user sartor`
only if `import sartor_cli` fails, then `python -m sartor_cli up`); `.gitattributes` EOL rules and the
exec bit in the index; static plus stub-Python tests; the Gatekeeper and Mark-of-the-Web caveats documented.
