# Blast radius — data-root

> **Branch:** `feat/data-root` (item 145, branch 1 of 3)
> **Status:** enumeration complete for the runtime sites; **the instrument (step 2) has not run yet**, so
> nothing below is `## Observed` except the greps themselves. Hypotheses are under `## Inferred`.

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
| 11 | `blueprints/templates.py:151,770,796,857,922` | **conditional** — change only if the instrument observes H1 | See `## Inferred`. A fix is one resolver, `personas/bundled/*` → `BUNDLED_PERSONAS_DIR`, else `BASE_DIR / rel`. |
| 12 | `Dockerfile` | **update** | `SARTOR_HOME=/data`, `/data` owned by uid 10001 *before* `VOLUME`, `HEALTHCHECK`. |
| 13 | `docs/user/install.md:137-142,176-193` | **update** | Collapse five mounts to one; delete the "`/app/db` is a package" trap, which no longer applies. |
| 14 | `pyproject.toml` `py-modules`, mypy roster, `scripts/wiki_relevance.py` | **update** | Register `sartor_home`. |
| 15 | `tests/test_packaging.py:169,182` | **no change expected** | Patches `config_module._is_dev_checkout`; the alias must still be the name `_default_base_dir()` consults. Verified by running it. |

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
- **H2** (the image's index build may always fall to its WARN branch): not this branch; goes to the owner
  or branch 2.

---

## Inferred

*Hypotheses from reading code. None is established until the instrument commit runs.*

- **H1.** With `SARTOR_HOME` set (or any wheel install), `Config.bundled_personas_dir` resolves to the
  packaged directory, but `blueprints/templates.py:151` joins the DB row's `personas/bundled/x.docx` onto
  `BASE_DIR`, a directory that has no `personas/bundled/`. Expected: a bundled template resolves to `None`.
- **H2.** `.dockerignore:6` excludes `.git`, and `scripts/build_vector_index.py:55-67` `_git()` raises
  `SystemExit` on a git failure, so the Dockerfile's best-effort index build falls through to its WARN branch.

## Observed

*(empty until the instrument commit; filled in the same turn it runs — C-8.)*

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
