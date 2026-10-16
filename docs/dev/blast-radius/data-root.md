# Blast radius — data-root

> **Branch:** `feat/data-root` (item 145, branch 1 of 3)
> **Status (2026-10-16):** enumeration complete; instrument run (`## Observed`); writers routed through
> `sartor_home` (rows 1-11, 14-15 done); the Dockerfile (12) is edited but not built; install.md (13)
> is still to do on this branch.

**Why this branch exists.** Item 145's container contract is `-v sartor-data:/data -e SARTOR_HOME=/data`.
Only `config._default_base_dir()` reads `SARTOR_HOME` (below). The SQLite DB, the LLM log, `.api_key`
and the onboarding CLI's paths resolve from the install directory, so that one mount would lose them.
No file this branch edits is a gated surface (`scripts/enforcement/blast_radius.py:190-205` lists
`analyzer.py` and `db/session.py` under `ACKNOWLEDGED_NOT_GATED`; `config.py` is absent from every
list). The dossier is written anyway: charter C-10 orders the enumeration before the first edit, and
the first edit here changes where user data is written.

---

## Surface

A new stdlib-only leaf, `sartor_home.py`, becomes the one resolution of the user-data root. These
sites then resolve through it:

- `config.py:71` `_is_dev_checkout`, `:86` `_default_base_dir` — become aliases of the helper.
- `analyzer.py:568` `LOG_DIR` (and `:569` `LOG_PATH`, `:575` the `mkdir`).
- `db/session.py:24-25` `DEFAULT_DB_PATH` (`_REPO_ROOT` stays for `alembic.ini` at `:153`).
- `preflight.py:415` `api_key_path` default root.
- `web_infra/clients.py:34,61` `_REPO_ROOT` / key fallback.
- `onboarding/corpus_import.py:57-60,557` `CONFIGS_DIR`, `OUTPUT_DIR`, `RESUMES_DIR`, key fallback.
- `evals/annotation.py:155`, `evals/bootstrap.py:81` `ALLOWED_ROOT`.
- `evals/runner.py:94,156` log path and key fallback (lockstep with `analyzer.LOG_PATH`).
- `Dockerfile` (`SARTOR_HOME`, `VOLUME`, `HEALTHCHECK`) and `docs/user/install.md:137-142` (five mounts).

Not changing: the read-only shipped-content roots (`config.TEMPLATES_DIR`, `STATIC_DIR`,
`bundled_personas_dir`), the vector index, and `alembic.ini` (see `## Deferred`).

---

## Enumeration

Run with the Grep tool over the whole tree (`C:\Dev\sartor`), `*.py`, no path exclusions unless noted.

1. `SARTOR_HOME|_default_base_dir|_is_dev_checkout` →
   - **Reads of the env var in non-test code: exactly one**, `config.py:106`
     (`os.environ.get("SARTOR_HOME")`). Every other non-test hit is a docstring or comment
     (`config.py:33,94,128`, `instance.py:136`, `dashboard/routes.py:47-48`, `preflight.py:54`).
   - `_default_base_dir` importers: `dashboard/routes.py:32` (`PROJECT_ROOT = _default_base_dir()`, `:53`),
     `config.py` itself (`:132,178,193,206`), `tests/test_packaging.py:171,182`.
   - `_is_dev_checkout`: `config.py:71,109`; `tests/test_packaging.py:160,169` (the latter monkeypatches it).
   - Negative: `0` hits in `static/`, `templates/`, `blueprints/`, `web_infra/`, `db/` for the env-var name.
2. `Path\(__file__\)|_REPO_ROOT|PROJECT_ROOT|REPO_ROOT` → the full list was read; the **runtime** sites
   are the ones in `## Surface`. The rest are dev/CI tooling under `scripts/**` (doc lints, wiki, hooks,
   `release_version.py`) that locate the *checkout*, not user data.
3. `LOG_DIR|LOG_PATH|DEFAULT_DB_PATH|\.api_key|vector_index|ALLOWED_ROOT` → **192 occurrences across 57
   files**, of which the non-test runtime files are: `analyzer.py` (5), `app.py` (9, all key-prompt text
   and the `--setup` index build), `config.py` (1), `blueprints/assistant.py` (2), `dashboard/routes.py`
   (1), `db/session.py` (6), `onboarding/corpus_import.py` (6), `web_infra/clients.py` (4),
   `preflight.py` (8), `evals/{annotation,bootstrap,corpus_drafting_probe,runner}.py` (6/7/3/5),
   `recall/sources/*` (4, comments only), and 11 files under `scripts/`.
4. `BASE_DIR|PERSONAS_DIR|BUNDLED_PERSONAS_DIR` in `blueprints/templates.py` → resolves a persona row's
   stored path as `BASE_DIR / row.path` at `:151, :770, :796, :857, :922`; the bundled default HTML
   uses `BUNDLED_PERSONAS_DIR` at `:1051, :1278, :1413`. Seeded rows store `personas/bundled/<n>.docx`
   (`db/migrations/versions/0002_seed_bundled_templates.py:35-68`; renamed in `0005`).
5. Test seams on the names being changed (these are consumers — they must keep working or be updated on purpose):
   - `monkeypatch.setattr(analyzer, "LOG_PATH", …)` and `DEFAULT_DB_PATH` — ~30 sites in 17 files
     (e.g. `tests/test_demo_mode.py:171`, `tests/conftest.py`). **Preserved**: the constants stay
     module-level, computed at import.
   - `corpus_import.CONFIGS_DIR` monkeypatched at `tests/test_corpus_import.py:45,342`. **Preserved.**
   - `web_infra_clients._REPO_ROOT` monkeypatched at `tests/test_demo_mode.py:154`; asserted at
     `tests/test_setup_api_key.py:60`. **These two change on purpose** (see Consumers #6, #7).
   - `config_module._is_dev_checkout` monkeypatched at `tests/test_packaging.py:169`; the
     `_default_base_dir() == dashboard_routes.PROJECT_ROOT` pin at `:182`. **Must keep working.**
6. Packaging: `pyproject.toml` `py-modules` is pinned by `tests/test_packaging.py` (`:123` per the design
   pass — **I have not re-read that line**); a new top-level module must be added there, and to the mypy roster.

---

## Consumers

| # | Site (`path:line`) | Decision | Rationale |
|---|---|---|---|
| 1 | `config.py:71,86` `_is_dev_checkout`, `_default_base_dir` | **update** → aliases of `sartor_home` | Keeps `Config.base_dir`'s `default_factory` and `bundled_personas_dir`'s `== _default_base_dir()` test working unchanged. |
| 2 | `dashboard/routes.py:32,53` | **no change** | Already follows `_default_base_dir()`; stays in lockstep once that is an alias. |
| 3 | `analyzer.py:568-576` `LOG_DIR`/`LOG_PATH` | **update** → `data_path("logs")`; `mkdir(parents=True, exist_ok=True)` | The writer of `llm_calls.jsonl`; the dashboard already *reads* the data root, so today read and write split under `SARTOR_HOME`. `parents=True` because a fresh platform dir may not exist. |
| 4 | `db/session.py:24-25,89-90,140` `DEFAULT_DB_PATH` | **update** → `data_path("db", "resume.sqlite")` | The DB is user data. `_REPO_ROOT` stays for `alembic.ini` (`:153`), which is code. `:89` already uses `parents=True`. |
| 5 | `preflight.py:415` `api_key_path` | **update** default root → `sartor_home.base_dir()` | The single resolver both the `--setup` writer (`app.py:220,275`) and the doctor use. Explicit `base_dir` stays the test seam. |
| 6 | `web_infra/clients.py:34,61` | **update** → call `preflight.api_key_path()` at use time; drop `_REPO_ROOT` | One resolver, not two that agree by coincidence. Changes `tests/test_demo_mode.py:154` (redirect via `SARTOR_HOME` instead) and `tests/test_setup_api_key.py:60`. |
| 7 | `tests/test_setup_api_key.py:60`, `tests/test_demo_mode.py:154` | **update** | Reword to the new invariant: the client reads the key from `preflight.api_key_path()`, proven by redirecting `SARTOR_HOME`. |
| 8 | `onboarding/corpus_import.py:57-60,557` | **update** → `data_path(...)` for the three dirs and the key fallback (`preflight.api_key_path()`) | CLI that writes into the same configs/output/resumes the app reads. Constants stay module-level (`tests/test_corpus_import.py:45,342`). |
| 9 | `evals/annotation.py:155`, `evals/bootstrap.py:81` `ALLOWED_ROOT` | **update** → `data_path("evals","fixtures","real")` | Must equal `Config.annotation_root` (`config.py:167`), which follows `SARTOR_HOME`; otherwise the localhost annotation routes' containment check rejects the real directory. Identical in a clone. |
| 10 | `evals/runner.py:94,156` | **update** log path and key fallback | A dev who sets `SARTOR_HOME` would otherwise read a log `analyzer` no longer writes (silent zero-cost telemetry). One-line each. |
| 11 | `blueprints/templates.py:151,796,922` (resolve, download, preview) | **update** — H1 observed (O2, O5) | One helper, `_persona_row_location(source, path)`: a `bundled` row's `personas/bundled/<n>` maps to `BUNDLED_PERSONAS_DIR` with that directory as the containment root; every other row stays `BASE_DIR / path` inside `PERSONAS_DIR`. Keyed on `source`, not the prefix, because a candidate may be named "bundled". |
| 11a | `blueprints/templates.py:770` (delete) | **no change** | Returns 403 for `source == "bundled"` before it reaches the join (`:767-768`); only user uploads get here, and those are data-root-relative. |
| 11b | `blueprints/templates.py:857` (copy) | **no change** | Returns 400 unless `source.source == "user_upload"` (`:847-848`); user data, data-root-relative. |
| 11c | `blueprints/templates.py:82` (`_persona_dict`) | **no change** | Serialises the stored `path` string to the client; no filesystem access. |
| 12 | `Dockerfile` | **update** | `SARTOR_HOME=/data`, `/data` owned by uid 10001 *before* `VOLUME`, `HEALTHCHECK`. |
| 13 | `docs/user/install.md:137-142` (the command), `:157-174` ("declares no `VOLUME`"), `:176-193` (the bind-mount trap), `:201-226` (bulk output; the two unverified notes) | **update** | One `-v sartor-data:/data`. The trap is gone: `/data` holds only data, and nothing under `/app` is a mount point. `:160` stated the `Dockerfile` "declares no `VOLUME`", which this branch makes false. The "fresh `/app/db` mount shadows the recall index" note (`:219-226`) is obsolete for the same reason. |
| 13a | `docs/user/install.md:439-440, 661-662, 675-679` (key file "in the repo root"; "all under the repo root") | **update** | True for a source install, incomplete for a wheel or a container: both now name the data root. |
| 13b | `README.md:148-152, 159-163` | **update** | Carries the same two-mount command and the "`/app/db` must be a named volume" rule. Found by a grep for `sartor-db` / `/app/db`, which the first pass did not run. |
| 13c | `SECURITY.md:144-182` (where the key, the DB and the telemetry live on disk) | **update** | States the data root and `SARTOR_HOME`, plus the container healthcheck's loopback-only scope. |
| 13d | `docs/wiki/pages/troubleshooting.md:42-51` ("a `.api_key` file in the repo root"; the data directory) | **update** via the scoped `/wiki-self-update` at close-out | A wiki page; edited by the loop, not by hand. |
| 13e | `docs/dev/work/items/0101-container-run-defaults-to-data-loss.md` (closed; its resolution describes the five-mount layout) | **update**: an `## Updates` entry only | Status stays `closed`. It records that item 145 branch 1 superseded the layout and made two of its reasons obsolete. |
| 13f | `CHANGELOG.md` `[Unreleased]` | **update** | Behaviour change for installed-wheel users (the key and logs move from `site-packages/` to the data root) and the container layout. |
| 13g | `docs-site/content/docs/*.mdx` (`index.mdx:157`, `user-install.mdx:146-148,183-226`) | **no change** | Generated by `scripts/project_docs_to_mdx.py` and **gitignored** (only `.gitkeep` is tracked, verified with `git ls-files`); a local copy, stale at `HEAD` already (`check_docs_projection_fresh.py` exits 1). Never edited by hand. |
| 13h | `docs/dev/handoffs/*.md` (`feat-install-onboarding-preflight.md:176`, `fix-ci-wait-required-from-protection.md:131`, `single-instance-and-quit.md:219-221`) | **no change** | Historical records of what was true when written. |
| 13i | `CONTRIBUTING.md:41`, `evals/README.md:1001`, `dashboard/README.md:115` | **no change** | "a local `.api_key` file" / "at the project root": exactly right for the dev checkout those docs address. |
| 14 | `pyproject.toml` `py-modules`, mypy roster, `scripts/wiki_relevance.py` | **update** | Register `sartor_home`. |
| 15 | `tests/test_packaging.py:169,182` | **update** (corrected after reading it) | `:169` patches `config_module._is_dev_checkout`, which `_default_base_dir()` stops consulting once it delegates; patch `sartor_home.is_dev_checkout` instead. `:153,161,174` keep `config_module._PROJECT_ROOT`, so that name stays. `:123` is the `py-modules` roster pin (verified): `sartor_home` must be registered. |

---

## Deferred

- **Vector index** (`blueprints/assistant.py:84`, `preflight.py:380`, `scripts/build_vector_index.py:44`,
  `app.py:307`): stays code-rooted. It is derived from shipped source, not user data; a copy under `/data`
  would freeze a stale index across image updates.
- **`alembic.ini`** (`db/session.py:153`): code, not data. Whether a wheel ships it is branch 2's wheel smoke.
- **`generator.py:267,362`, `docx_to_persona_html.py:67`**: read shipped content. Whether
  `personas/cover_letter.html` is packaged is branch 2's instrument.
- **`blueprints/assistant.py:60,203`** `PROJECT_ROOT` for the git-grep tier: a checkout-only tier by its own comment.
- **`scripts/**`** (doc lints, wiki, hooks, `smoke_phase_b1.py:43,205`, `export_corpus_seed.py:45`,
  `build_vector_index.py`): dev/CI tooling run from a clone. Stated cost: a dev who exports `SARTOR_HOME`
  in their shell and runs `smoke_phase_b1.py` reads the old location.
- **Migrating existing five-volume container data**: out of scope, nothing is published. `install.md` gets a note.
- **`STOPSIGNAL SIGINT`** (not added). Python as PID 1 has no SIGTERM handler, so `docker stop` may wait out
  its 10 s grace and SIGKILL. That is a prediction from how PID 1 signals work, not an observation, and the
  fix changes shutdown behaviour; it waits for a measured `stop` with and without it.
- **`/app` left owned by `sartor`** (the plan's "leave it root-owned so a missed writer fails loudly"
  is not done). It needs a container run to prove nothing else writes under `/app` at runtime, and an
  unverified ownership change could ship a broken image. The ratchet test covers the same risk at
  review time instead.
- **Building and running the image.** Not done: a full build installs Chromium and its OS libraries
  through the owner's Podman machine under memory pressure, and needs the owner's go-ahead.
- **Podman and `HEALTHCHECK`.** Podman builds the OCI format by default, which does not record a
  `HEALTHCHECK`; `podman build --format docker` does. Not verified here. `docker.yml` builds with buildx.
- **H2** (the image's index build may always fall to its WARN branch): not this branch; goes to the owner
  or branch 2.

---

## Inferred

*Hypotheses from reading code. None is established until the instrument commit runs.*

- **H1 — promoted to Observed (O2/O3 below).** With `SARTOR_HOME` set (or any wheel install),
  `Config.bundled_personas_dir` resolves to the packaged directory, but `blueprints/templates.py:151`
  joins the DB row's `personas/bundled/x.docx` onto `BASE_DIR`, a directory that has no
  `personas/bundled/`.
- **H2.** `.dockerignore:6` excludes `.git`, and `scripts/build_vector_index.py:55-67` `_git()` raises
  `SystemExit` on a git failure, so the Dockerfile's best-effort index build falls through to its WARN branch.

## Observed

Instrument: `tests/test_data_root.py`, run 2026-10-16 on `feat/data-root` with `--runxfail` so the
failures print. One run each, Windows 11, Python 3.13.14. The committed form is `2 xfailed`.

**O1 — the path probe** (`test_every_user_data_writer_honours_sartor_home`: a fresh interpreter,
`SARTOR_HOME=<tmp>` set before import, `.api_key` placed in `<tmp>`). 12 of 13 sites ignore it:

```text
analyzer.LOG_PATH: C:\Dev\sartor\logs\llm_calls.jsonl
db.session.DEFAULT_DB_PATH: C:\Dev\sartor\db\resume.sqlite
preflight.api_key_path(): C:\Dev\sartor\.api_key
web_infra.clients reads the key from SARTOR_HOME: False
onboarding.corpus_import.CONFIGS_DIR: C:\Dev\sartor\configs
onboarding.corpus_import.OUTPUT_DIR: C:\Dev\sartor\output
onboarding.corpus_import.RESUMES_DIR: C:\Dev\sartor\resumes
onboarding.corpus_import reads the key from SARTOR_HOME: False
evals.annotation.ALLOWED_ROOT: C:\Dev\sartor\evals\fixtures\real
evals.bootstrap.ALLOWED_ROOT: C:\Dev\sartor\evals\fixtures\real
evals.runner.LLM_LOG_PATH: C:\Dev\sartor\logs\llm_calls.jsonl
dashboard reads the log analyzer writes: False
```

The one site that already honoured it is `Config().annotation_root`. The last line is the
read/write split the enumeration predicted: `dashboard/routes.py` follows `SARTOR_HOME` while
`analyzer.py` writes beside the code, so under `SARTOR_HOME` the dashboard reads a file nothing writes.

**O2 — H1 is real** (`test_a_bundled_template_resolves_when_sartor_home_redirects_the_base_dir`:
in-process, a copy of the migrated template DB, `SARTOR_HOME=<tmp>`, `Config()` default base dir,
packaged `classic.docx` present, `<tmp>/personas/bundled` absent). The resolver returned `None` and
the app logged its own warning:

```text
WARNING  blueprints.templates:templates.py:153 Persona template id=1 has invalid path personas/bundled/classic.docx
```

Controls held: `Config().base_dir == <tmp>`, `bundled_personas_dir` was the packaged directory and
`classic.docx` existed there. So the failure is the `BASE_DIR / row.path` join at
`blueprints/templates.py:151`, not a missing shipped file. This promotes H1 from Inferred.

**O3 — H1 is not an edge case.** `Config.bundled_personas_dir` takes the packaged-directory branch
whenever `base_dir == _default_base_dir()` (`config.py:206`), which is exactly the `SARTOR_HOME` and
installed-wheel case. The same branch makes `BUNDLED_PERSONAS_DIR` correct while `BASE_DIR` stays wrong.

**O4 — after routing the writers (same probe, no code change to it):** all 13 sites resolve under
`SARTOR_HOME`; `test_every_user_data_writer_honours_sartor_home` passes (1 run, 4.8 s). The
suites that import the routed modules pass: 403 passed, 1 skipped across `test_demo_mode`,
`test_setup_api_key`, `test_preflight`, `test_corpus_import`, `test_annotation*`, `test_bootstrap`,
`test_packaging`, `test_config`, `test_cli_setup`, `test_analyzer_model_selection`,
`test_call_kind_telemetry`, `test_llm_credential_gate`, `test_export_corpus_seed`, `test_web_infra`.
In a clone `base_dir()` is the repo root, so those paths are byte-identical; that is argued from the
code (`sartor_home.base_dir`, branch 2), and the 403 are consistent with it, not a proof.

**O5 — H1 fixed, with the red-before.** Against `HEAD` before the fix (a detached scratch worktree, the
new test file copied in; removed afterwards), the download route for a seeded bundled persona under
`SARTOR_HOME` returned `404 {"error":"Persona file missing on disk"}`, and the resolver arm failed as in
O2. After the fix: `tests/test_data_root.py` 18 passed, and the persona and route suites pass
(`test_persona_routes`, `test_default_template_resolver`, `test_live_preview_route`,
`test_route_containment_gate`: 112 passed together). The preview route (`:922`) shares the helper but
has no test of its own here; it is covered by the helper and by `test_live_preview_route` for the
checkout case only. **Not observed:** the preview route under `SARTOR_HOME`.

**O6 — the real app under `SARTOR_HOME`** (one run, Windows 11, `FLASK_DEBUG=0`,
`SARTOR_HOME=<scratch>`, `python app.py --no-browser --port 5057`, driven by a scratch script):

```text
healthz 200 {"app": "sartor", "idle_timeout_s": null, "pid": 21932, "version": "1.0.9", ...}
personas/bundled 200 list  -> 4 rows; first: id 1 "Classic Single-Column" personas/bundled/classic.docx
download 200 37354
shutdown 202 {"status":"stopping"}
server gone after 1.44s
files under SARTOR_HOME: db/resume.sqlite 303104, db/resume.sqlite-shm 32768, db/resume.sqlite-wal 0
```

The `/healthz` request used the same `urllib.request.urlopen(..., timeout=3)` call the Dockerfile
`HEALTHCHECK` runs (port aside). The bundled-persona download that returned 404 before the fix (O5)
returns the 37,354-byte file. The DB and its migrations landed under `SARTOR_HOME`. No `logs/` appeared
because no LLM call was made, and no `sartor-instance.json` remained because the shutdown released it.
**The owner's real files were not touched:** `logs/llm_calls.jsonl` (502803 B), `db/resume.sqlite`
(2134016 B) and `.api_key` (108 B) had identical size and mtime before and after. Afterwards the
`python.exe` count was back to its starting value (1), and port 5057 had only client-side `TIME_WAIT`
entries, no listener.

**Not observed — the container itself.** No image was built, so the `HEALTHCHECK` reaching `healthy`,
the named-volume copy-up of `/data` ownership under rootless Podman, and data surviving `rm` and
recreate are all unverified. See `## Deferred`.

**Mechanism authored for the recurrence (C-11), same branch:** `TestNoUnclassifiedFileAnchoredPath`
in `tests/test_data_root.py` scans every runtime `.py` (root modules and `blueprints`, `dashboard`,
`db`, `evals`, `onboarding`, `recall`, `ui_pages`, `web_infra`) for `Path(__file__)` and requires the
exact set to match `_CODE_ANCHORS` (10 files today, each with a reason). A new file-anchored path
fails the test until someone decides whether it is shipped code or user data. Its control arm
builds a scratch tree with an unclassified file and asserts the scan finds it. **Known limit (C-0):**
it sees `Path(__file__)` only; a path built from `os.path.dirname(__file__)`, `__file__` in a string
join, or `importlib.resources` is invisible to it, and `scripts/**` is out of scope.

**Not observed:** H2. No image was built.

**Row 15 correction (found while reading `tests/test_packaging.py:163-172`):** that test
monkeypatches `config_module._is_dev_checkout` and expects `_default_base_dir()` to honour the
patch. Once `_default_base_dir` delegates to `sartor_home`, the patch has no effect. Row 15 said "no
change expected"; that was wrong. The test must patch `sartor_home.is_dev_checkout` instead.

---

## Verification

How a missed consumer would surface:

- **The instrument itself** (step 2): a subprocess with `SARTOR_HOME=<tmp>` prints each resolved path and
  asserts all sit under `<tmp>`. A writer I did not find shows up only if it is imported there, so the
  instrument imports every module in `## Surface` plus the whole `blueprints` tree.
- **A grep ratchet in the same test**: no non-test `.py` outside `sartor_home.py`/`config.py` assigns a
  runtime data path from `Path(__file__)`. The allow-list is the `## Deferred` set, so a new writer fails loudly.
- **The existing suite unchanged in a clone**: in a clone `base_dir()` is the repo root, so every path is
  byte-identical; the ~30 monkeypatch seams stay valid.
- **A real run**: `SARTOR_HOME=<scratch> python app.py --no-browser`, then confirm `db/resume.sqlite`,
  `logs/llm_calls.jsonl` and `sartor-instance.json` appear under `<scratch>` and nowhere in the checkout.
