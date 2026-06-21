# Design — `app.py` → Flask blueprints (v1.0.8, item 8.1)

> **Status:** APPROVED design (owner decisions locked 2026-06-21). Read-only investigation
> of the monolith; **no route moved in this document's branch** (`design/app-blueprints`).
> **Authorizes:** the 8.2+ decomposition branches.
> **Authorized by:** [`RELEASE_ARC.md`](RELEASE_ARC.md) §Phase 4.8 "`design/app-blueprints`"
> bullet + [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md) item **8.1**.
> **Precedents (same kind of artifact):**
> [`governance-extraction-design.md`](governance-extraction-design.md),
> [`self-documenting-loop-design.md`](self-documenting-loop-design.md).
> **Do not deviate without owner sign-off** — multiple future sessions execute against this.

---

## 1. Context & authorization

[`app.py`](../../app.py) is an **8,251-LOC, 93-route** Flask monolith that grew ad-hoc
across the v1.0.x epics. Epic **v1.0.8** decomposes it into Flask blueprints (WS-1) so the
public **v1.1.0** cut ships on clean architecture. The decomposition is a dedicated
**low-churn window** that **must not interleave** with feature work — it rewrites routes
**~35 test files import from** — so it is preceded by this design session (item 8.1), which
resolves the architecture *with the owner* before any code moves.

**Owner directives (2026-06-21), binding on this design:**
1. **This is the re-architecture moment.** "The app developed a bit ad-hoc and this is THE
   TIME when we re-architect. Most development from here on will build on what we do in this
   epic." → optimize for long-term soundness + portfolio-grade craft, **not**
   churn-minimization.
2. **Architectural, not a spot fix.**
3. **Absolute-minimum tech debt at the v1.1.0 tag.** The design specifies a *complete*
   migration; **no half-finished hybrid state may survive to 1.1**.

**Owner decisions locked this session:**
- **App architecture = "Crafted":** a `create_app(config)` **application-factory** (with a
  retained module-level `app = create_app()` WSGI/console handle); path constants become an
  injected **typed Config** object (ending the monkeypatch-the-global test smell);
  cross-cutting helpers move to a **small shared web-infra package** that both `app.py` and
  every blueprint import.
- **Seams = 8 domain seams** — splitting the user-facing application tracker from the dev
  diagnostics backend: **analysis · generation · corpus · templates/personas · applications
  · users/config · diagnostics · assistant**.

What this design does **not** touch: [`analyzer.py`](../../analyzer.py) and the LLM-call
boundary, any prompt, `PROMPT_VERSION` / `AVATAR_PROMPT_VERSION`, the DB models, or the
analyze→generate cache prefix. The decomposition is a **pure refactor**: every route's URL,
method, request shape, and response body stays byte-identical.

---

## 2. Current state — the ad-hoc tells we are correcting

| Tell | Evidence (`file:line`) | Why it's debt |
|---|---|---|
| **Module-global `app` with import-time side effects** | `app.py:56` `app = Flask(__name__)`; `:57-58` blueprint registration; `:85-86` `for d in (...): d.mkdir` (only CONFIGS/RESUMES/OUTPUT — **not** ANNOTATION_ROOT/PERSONAS); constants at `:70-82`, **plus** `PERSONAS_DIR`/`BUNDLED_PERSONAS_DIR` defined mid-file at `:2303-04` | Importing the module *does things* (mkdir, env reads, registration). Hard to test in isolation; no config injection. |
| **Monkeypatch-the-global test harness** | ~35 files: `import app as app_module` then `app_module.app.test_client()` + `monkeypatch.setattr(app_module, "OUTPUT_DIR", tmp)` (also `CONFIGS_DIR`, `BASE_DIR`, `RESUMES_DIR`, `PERSONAS_DIR`, `BUNDLED_PERSONAS_DIR`, `ANNOTATION_ROOT`) | Tests reach *into* the module to mutate globals because there is no config seam. This is the smell the factory removes. |
| **A *second* monkeypatch front** | `onboarding/corpus_import.py:51-53` defines its OWN `CONFIGS_DIR`/`OUTPUT_DIR`/`RESUMES_DIR`; `_safe_load_config` (`:111-117`) + `import_candidate_from_config` (`:120-133`) read them import-bound; reached at runtime from `_get_or_provision_candidate` (`app.py:135`). ~7 tests `monkeypatch.setattr(corpus_import_mod, "CONFIGS_DIR", …)` | A `current_app.config` `TestConfig` does **not** reach this layer — the factory alone leaves this monkeypatch debt. Must fold into the Config seam (§3.3, §7). |
| **Helper duplication across the layer** | `blueprints/assistant.py:191-211` re-inlines `_safe_username` / `_get_client` / `_sse` from `app.py`, its docstring (`:18-21`) saying so "pending the Sprint 8.1 shared-helpers home" | Two copies of security-critical helpers. This design *is* that home. |
| **Security lint scoped to one file** | `.claude-plugin/hooks/route-security-lint.sh:15` matches `(^|/)app\.py$` only | The moment a route leaves `app.py`, it leaves the hook's coverage. Must widen *before* any move (PX-21). |
| **Untyped route bodies** | ~15 Flask handlers with unannotated signatures → mypy skips their bodies (`feat/wysiwyg-option1` 2026-06-02 surfaced the `annotation-unchecked` notes) | `check_untyped_defs` can't see route bodies; PV-4 closes this as routes move. |
| **Boundary held by convention** | the deterministic ↔ LLM split (charter C-6) is enforced for `recall/` only (`tests/test_recall_boundary.py`), not for `hardening`/`parser`/`generator`/… | PX-20 commits the construction gate so a deterministic module importing `analyzer`/`anthropic` fails by test, not by review. |

The two **already-correct** precedents we extend: `blueprints/assistant.py` and
`dashboard/routes.py` both create `Blueprint(...)`, **never import `app.py`**, and re-derive
`PROJECT_ROOT = Path(__file__).resolve().parent.parent`. The decomposition makes the
remaining seven seams look like these two.

---

## 3. Target architecture

### 3.1 Application factory

```python
# app.py becomes thin: factory + WSGI handle + main().
def create_app(config: Config | None = None) -> Flask:
    app = Flask(__name__)
    config = config or Config()                 # default = production paths
    app.config.from_object(config)              # OUTPUT_DIR, CONFIGS_DIR, ... injected
    config.ensure_dirs()                         # the :85-86 mkdir moves here (no import side effect)
    register_blueprints(app)                     # all 8 seams, one place
    return app

app = create_app()                               # WSGI / console-script / back-compat handle
```

- **Import-time side effects move into the factory.** Importing `app` no longer mkdirs or
  reads env; `create_app()` does, when called.
- **The module-level `app = create_app()` is retained** — it is the WSGI entry and the
  `pyproject.toml [project.scripts] callback` console target. This is standard in exemplary
  Flask apps (it is *not* a compromise of the factory pattern).
- **`main()` + `_should_open_browser` stay in `app.py`** (`app.py:8238-8297`); the bind line
  `app.run(debug=debug_mode, port=5000)` (`:8293`) gains **`host="127.0.0.1"`** — see PX-19
  in §5.

### 3.2 Typed `Config` (the injected paths/flags)

A typed config object replaces the eight module-global path constants and the
`ALLOWED_EXTENSIONS` set. Tests construct a `TestConfig(tmp_path)` instead of monkeypatching
the `app` module.

```python
@dataclass(frozen=True)
class Config:
    base_dir: Path = BASE_DIR
    configs_dir: Path = ...      # base_dir / "configs"
    resumes_dir: Path = ...
    output_dir: Path = ...
    annotation_root: Path = ...  # base_dir / "evals" / "fixtures" / "real"
    personas_dir: Path = ...
    bundled_personas_dir: Path = ...
    allowed_extensions: frozenset[str] = frozenset({".docx", ".pdf", ".md"})
    host: str = "127.0.0.1"      # PX-19 — pinned by construction
    def ensure_dirs(self) -> None: ...
```

`ensure_dirs()` **mirrors today's `app.py:85-86` exactly** — it creates only `configs_dir` /
`resumes_dir` / `output_dir` (the three the import loop makes today), **not** `annotation_root`
/ `personas_dir` / `bundled_personas_dir` (created lazily by their writers today). Creating all
seven would be a *behavior change*; the pure-refactor rule (§8) forbids it.

> **Config-access convention (load-bearing):** blueprints and helpers read paths from
> `current_app.config[...]` at **request time** (or take an explicit `Config` arg in non-request
> helpers), **never** via a module-level `from somewhere import OUTPUT_DIR` binding. That single
> rule is what makes a `TestConfig` fully effective and is what permanently retires the
> monkeypatch-the-global pattern. The exact `Config` shape (dataclass vs. Flask config dict vs.
> a settings object on `app.extensions`) is finalized in the 8.3-foundation branch; the
> **contract** — injected, not global; read via `current_app`, not import-bound — is fixed here.

### 3.3 Shared web-infra home

The cross-cutting helpers move out of `app.py` into a small, cohesive **web-infra package**
that `app.py` and **every** blueprint import (so `assistant.py` drops its duplicates). Exact
module names are settled in the foundation branch; the **grouping** is fixed here:

| Group | Members (from `app.py`) | Notes |
|---|---|---|
| **security** | `_safe_username` (`:112`), `_within` (`:126`) | The hook's two required guards. Used in 38+/40+ sites. |
| **http / sse** | `_sse` (`:357`, pure formatter), `_error_detail_payload` (`:365`) | `_error_detail_payload` is refactored to read **`current_app.debug`** instead of the imported `app.debug` — behavior-identical (`current_app.debug` is the same Flask flag SECURITY.md:210-217 names as "the gate's mechanism"), but breaks the `app` import. |
| **clients** | `_get_client` (`:89`) | Anthropic client from env/`.api_key`. |
| **config-io** | `_load_config` (`:100`), `_save_config` (`:107`) | PX-21 closes their `secure_filename` gap (see §5). |
| **provisioning** | `_get_or_provision_candidate` (`:135`) | Lazy candidate row from config. |
| **request-gates** | `_is_localhost_request` (`:153`) | The localhost gate for the dev/diagnostics write surface. |

**Hard rule (enforced, see §8):** the web-infra package **never imports `app.py` or any
blueprint** — it is leaf infrastructure. This is what keeps the import graph acyclic and
lets every blueprint import it freely.

**Two adjacent homes fold in too (required for zero-debt — see §7):**
- **`onboarding/corpus_import.py`** carries its own `CONFIGS_DIR`/`OUTPUT_DIR`/`RESUMES_DIR`
  (`:51-53`), read import-bound by `_safe_load_config`/`import_candidate_from_config` and
  reached from `_get_or_provision_candidate`. **Parameterize** those functions with an explicit
  `configs_dir` (sourced from the injected `Config` at the call site) so the onboarding layer
  stops holding a second copy and its ~7 `corpus_import_mod` monkeypatches retire with the rest.
  (`corpus_import` is deterministic / LLM-free — passing a path arg keeps it so.)
- **`dashboard/routes.py`** re-derives `PROJECT_ROOT` and has its own loopback
  `before_request`; it should consume the infra `_is_localhost_request` rather than keep a
  *third* copy of the gate.

### 3.4 The 8 blueprint seams

All seam modules live in the existing [`blueprints/`](../../blueprints/) package (born 7.5,
"deliberately blueprint-shaped so the v1.0.8 refactor is a *move*, not a rewrite"). Each
seam owns its **domain helpers** (the serializers / builders / readers scoped to it), which
move *with* the routes.

| # | Seam | Blueprint | Routes | SSE | Domain helpers that move with it (examples) |
|---|---|---|---:|---|---|
| 1 | **analysis** | `analysis_bp` | 5 | 1 | `_run_analysis_corpus_backed[_streaming]`, `_persist_clarifications_to_memory` |
| 2 | **generation** | `generation_bp` | 7 | 1 | `_check_date_grounding`, `_persist_corpus_generation_to_db`, `_persist_cover_letter_to_db` |
| 3 | **corpus** | `corpus_bp` (likely a **sub-package**) | 42 | 0 | `_experience_detail_dict`, `_tag_list`, `_find_or_create_tag`, `_skill_to_dict`, `_summary_item_to_dict`, … |
| 4 | **templates/personas** | `templates_bp` | 11 | 0 | `_persona_dict[s_safe]`, `_resolve_persona_template_path`, `_inline_persona_css`, `_inject_paged_polyfill`, `_preview_placeholder_html` |
| 5 | **applications** | `applications_bp` | 13 | 0 | `_application_summary_dict`, `_build_resume_state`, `_find_context_path_for_run`, `_read_*_overrides`, `_apply_chosen_summary`, `_apply_recommended_skills` |
| 6 | **users/config** | `users_bp` | 6 | 0 | (config-io helpers live in the infra package) |
| 7 | **diagnostics** | `diagnostics_bp` (+ existing `dashboard_bp`) | 9 | 5 | `_annotation_fixture_path`, `_load_bootstrap_doc`, `_write_seed_json`, `_patch_annotation_scores` |
| 8 | **assistant** | `assistant_bp` (exists) | — | (stream) | **move-only / verify** — already a blueprint since 7.5 |

**Total: 93** (5 + 7 + 42 + 11 + 13 + 6 + 9). Full route→seam mapping in
[Appendix A](#appendix-a--full-route--seam-map).

Two structural notes:
- **`corpus` is large (42 routes)** — experiences, bullets, titles, summaries,
  experience-summaries, skills, tags, duplicates, ingest, accept-pending, proposals,
  promote-to-bullet. It is best authored as a **sub-package** (e.g.
  `blueprints/corpus/{experiences,skills,tags,curation,proposals}.py` registered onto one
  `corpus_bp`, or a small handful of blueprints under a shared prefix). The 8.3 corpus branch
  decides the internal split; as a **seam/domain** it is one.
- **`diagnostics` = the existing read-only `dashboard_bp` (HTML at `/_dashboard`) + the 9
  localhost annotation/eval/tune API routes** (the diagnostics console's write/SSE backend).
  Both are dev/localhost surfaces; they form one domain. (The owner's "9 seams" option —
  splitting the read-only dashboard from the write backend — was **not** chosen; they stay
  one seam.)

### 3.5 SSE handling across the split

`_sse` (the pure formatter, `app.py:357`) moves to the infra `http/sse` group. The **6 SSE
routes move with their domain seam**, unchanged:

| Route | `app.py` | → seam |
|---|---|---|
| `POST /api/analyze/stream` | `:402` | analysis |
| `POST /api/generate/stream` | `:1537` | generation |
| `POST /api/annotation/fixture/<u>/<slug>/score` | `:7545` | diagnostics |
| `POST /api/annotation/bootstrap` | `:7749` | diagnostics |
| `POST /api/eval/run` | `:7948` | diagnostics |
| `POST /api/tune/run` | `:8074` | diagnostics |

The streaming shape is preserved verbatim: a generator `stream()` yielding
`_sse(event, payload)` returned as
`Response(stream(), mimetype="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})`
(`app.py:8231-8235`). Where a generator touches the request/session it keeps
`stream_with_context`. SSE event kinds (`chunk`/`retry`/`phase`/`done`/`error`) are unchanged.

---

## 4. Test-harness migration (the zero-debt crux)

The ~35 files that do `monkeypatch.setattr(app_module, "<CONST>", tmp)` + `app_module.app`
are migrated to a **canonical fixture** built from the factory:

```python
# tests/conftest.py (canonical, added in the 8.3-foundation branch)
@pytest.fixture
def app(tmp_path):
    return create_app(TestConfig(base_dir=tmp_path))   # dirs under tmp, no globals
@pytest.fixture
def client(app):
    return app.test_client()
```

- Each test stops monkeypatching globals and instead receives an isolated app whose `Config`
  points at `tmp_path`.
- **Migrate seam-by-seam:** each 8.3 seam branch updates *its own* tests as it moves the
  routes, so every branch lands green and **debt-free**. By the end of 8.3 **zero
  module-global monkeypatching remains** — the single most important zero-debt outcome.
- The one helper-import test (`tests/test_browser_open.py:12`, `from app import
  _should_open_browser`) keeps working — `_should_open_browser` stays in `app.py`.

---

## 5. Hook & gate sequencing

### 5.1 PX-21 — widen `route-security-lint` **before any route moves** (8.2)

Today the hook (`.claude-plugin/hooks/route-security-lint.sh:15`) early-exits unless the
edited file matches `(^|/)app\.py$`. The widen branch (**8.2
`refactor/route-security-lint-widen`, lands BEFORE 8.3**):
- widen the matcher to **`app.py` + `blueprints/**.py`** (and any route-bearing module),
  keeping the `@app.route`/`@<bp>.route`/`@<bp>.get|post` detection;
- keep the existing rule (a FS-touching route must contain `_safe_username` **and**
  `_within`);
- **close the `_load_config` / `_save_config` `secure_filename` gap** PX-21 names — these
  build `CONFIGS_DIR / f"{username}.config"` directly from an unsanitized `username`
  (`app.py:100-109`); route through `_safe_username` (or `secure_filename`) so the
  containment guarantee holds at the helper, not only at the call site;
- **scope `SECURITY.md:211`** (currently "app.py-resident routes") to the post-split layout;
- add **route-level traversal tests** (the `_within` containment behavior, now living in the
  infra package, gets direct unit coverage in addition to per-route coverage).

> The hook is wired in `.claude/settings.json` (PreToolUse `Edit|Write`), not the plugin
> manifest — widening it is editing the `.sh` + (optionally) the settings matcher, both
> owner-visible. This must merge **before** any seam branch, or moved routes leave the
> guard's coverage (RELEASE_ARC §4.8, 2026-06-15).

### 5.2 PX-20 — commit the C-6 deterministic-LLM boundary gate (rides 8.3)

Extend the `tests/test_recall_boundary.py` AST pattern to a gate that **fails when a
deterministic module imports `analyzer` or `anthropic`** — covering `hardening`, `parser`,
`generator`, `scraper`, `json_resume`, `corpus_to_json_resume`, `pdf_render` (the modules
charter **C-6** names "deterministic by design"). A ~15-line AST test or an `import-linter`
contract; no new runtime dep. The blueprint split moves code near this boundary, so the gate
lands in the same epic, by construction not convention. *(Panel lean: PX-20 is the
single-highest-durability item; if WS-1 slips it decouples and lands first.)*

### 5.3 PV-4 — `ResponseReturnValue` annotations (ride each seam move)

As each route moves, annotate its return with `flask.typing.ResponseReturnValue` so
`check_untyped_defs` sees the body. Scope = the post-v1.0.4 route surface. At the v1.1.0 cut
this is a *verify-it-held* check, not fresh work (RELEASE_ARC §Phase 5).

### 5.4 PX-29 — KEEP-ledger guard tests (8.4, after the seams)

Convert the load-bearing affirmations (route containment, zero-PII clone, bullet-reorder,
live-region, hook count) into do-not-regress guard tests so the split + the public tag can't
quietly weaken them. Sequenced after the moves so the guards assert the *final* layout.

### 5.5 Riders

- **PX-19 — loopback bind:** add `host="127.0.0.1"` at `app.run(...)` (`app.py:8293`) /
  carry it on `Config.host`; add a test; note `SERVER_NAME` as a third silent-flip vector.
  Rides the **users/config** seam (per RELEASE_CHECKLIST 8.3) or the 8.3-foundation branch
  (the bind site is in `app.py`'s `main()`).
- **PX-22 — wizard back-nav:** add a History API (`pushState`/`popstate`) entry so browser
  Back navigates wizard steps. Rides the **templates** seam (the wizard's
  route/state handling reorganizes there).
- **Help-opener duplication (carry-forward ledger #7):** fold opportunistically into the
  **diagnostics** seam (the dashboard file is already open there).

---

## 6. Branch sequencing (refines the checklist)

The locked decisions add one **foundation** branch before the seam moves. Proposed
(owner-signed-off via this session; the RELEASE_ARC/CHECKLIST edits in this branch record it):

```
8.2  refactor/route-security-lint-widen        (PX-21; hook covers blueprints) ── must precede 8.3
8.3a refactor/app-factory-and-infra            (create_app + Config + web-infra package +
                                                 assistant.py dedup + canonical test fixture;
                                                 PX-20 boundary gate; NO route moves)
8.3b analysis        ┐
8.3c generation      │
8.3d corpus          │  one seam per branch; each updates its own tests; each green + debt-free.
8.3e templates       │  PV-4 annotations + the security guards ride every moved route.
8.3f applications    │  (assistant = move-only/verify, no separate branch needed)
8.3g users/config    │  PX-19 rides here (or 8.3a); PX-22 rides templates; #7 rides diagnostics
8.3h diagnostics     ┘
8.4  test/keep-ledger-guards                   (PX-29; guards assert the final layout)
8.5+ gated test window → correction → public-prep → tag   (unchanged)
```

The 7 letters **8.3b–h** are the 7 seam *moves* (assistant is already a blueprint → the 8th
seam is verify-only), which lines up with the checklist's "8.3a–g" intent — only renamed to
make room for the explicit **8.3a foundation** branch the "Crafted" decision requires.

---

## 7. Zero-tech-debt definition of done (the owner's bar for v1.1.0)

The epic is **not** done until **all** of these hold — no item may be carried past the 1.1
tag as debt:

- [ ] `create_app(config)` is the composition root; `app.py` has **no import-time side
  effects** (mkdir/env/registration all inside the factory).
- [ ] **Zero** `monkeypatch.setattr(app_module, "<CONST>", ...)` remains in the test suite;
  all tests build a `TestConfig` app via the canonical fixture.
- [ ] **The second monkeypatch front is gone too:** no `monkeypatch.setattr(corpus_import_mod,
  ...)` remains — `onboarding.corpus_import` reads its config dir from the injected `Config`,
  not an import-bound global.
- [ ] `blueprints/assistant.py` **imports** the infra helpers — its duplicated
  `_safe_username` / `_get_client` / `_sse` are deleted.
- [ ] No **third** copy survives: `dashboard/routes.py` consumes the infra
  `_is_localhost_request` (no re-implemented loopback gate).
- [ ] All 93 routes live on a domain blueprint; `app.py` registers them in one place.
- [ ] Every moved route is typed (`ResponseReturnValue`); `mypy` with `check_untyped_defs`
  is clean over the surface.
- [ ] `route-security-lint` matches every route-bearing file; the
  `_load_config`/`_save_config` `secure_filename` gap is closed.
- [ ] The C-6 deterministic-LLM boundary gate (PX-20) is committed and green.
- [ ] PX-29 KEEP-ledger guard tests pass against the final layout.
- [ ] No **half-migrated** seam — each seam is fully moved or not started; no route lives in
  two places.
- [ ] Docs current: [`architecture.md`](../architecture.md) module map + the four
  `docs/diagrams/*.mmd` reflect the blueprint layout; [`SECURITY.md`](../../SECURITY.md):210-217
  re-cites the 5xx gate's mechanism as `current_app.debug` (it moved out of `app.py`);
  CHANGELOG updated; the wiki's `app.py` `path:line` citations re-anchored (the 8.6
  `/wiki-ingest`).
- [ ] `ruff + mypy + pytest + pytest -m ux` green; **no behavior change** (the route map —
  Appendix A — is unchanged URL-for-URL).

---

## 8. Risks & invariants

- **Circular imports.** *Invariant:* the web-infra package never imports `app.py` or any
  blueprint; blueprints never import `app.py`; the factory imports blueprints (one
  direction). Mirrors the working `dashboard`/`assistant` precedent. The PX-20 gate + an
  optional `import-linter` contract pin it.
- **The `app.debug` → `current_app.debug` move.** `_error_detail_payload` must stay
  behavior-identical — `current_app.debug` is the same Flask flag SECURITY.md:210-217 calls
  "the gate's mechanism," so the information-disclosure contract is preserved. A direct unit
  test on both debug/non-debug branches guards it.
- **No behavior change.** Routes/URLs/methods/responses are byte-identical; **no
  `analyzer.py` edit**, so the analyze→generate cache prefix and `PROMPT_VERSION` are
  untouched. Verification = full `pytest` (+ `-m ux`) green and a URL-for-URL route-map diff
  before/after each seam.
- **Big-bang risk.** Mitigated by the seam-by-seam sequencing (one domain per branch) and
  the foundation branch landing the factory/infra/fixtures *before* any route moves, so each
  later branch is a mechanical, independently-green move.
- **The 35-vs-32 count.** The plan said "32 test files"; the live count is ~35 (3 files
  added since). The tag criterion "all test files import cleanly" binds the **live** set.

---

## 9. Explicitly unchanged by this epic

`analyzer.py` and the LLM-call boundary · all prompt constants · `PROMPT_VERSION` /
`AVATAR_PROMPT_VERSION` · the DB models + migrations · the `context_set` JSON contract · the
deterministic modules' behavior (only their *boundary enforcement* is added, via PX-20).

---

## Appendix A — full route → seam map

All 93 `@app.route` handlers in `app.py`, with line number, mapped to the 8 seams.
**S** = SSE. (Source: `app.py` route scan, this branch.)

### analysis (5)
| `app.py` | Route | Handler | |
|---|---|---|---|
| 334 | `POST /api/analyze` | `run_analysis` | |
| 402 | `POST /api/analyze/stream` | `run_analysis_stream` | **S** |
| 843 | `POST /api/clarify` | `run_clarify` | |
| 1007 | `POST /api/answer-clarifications` | `submit_clarifications` | |
| 1100 | `POST /api/iterate-clarify` | `run_iterate_clarify` | ‡ |

### generation (7)
| `app.py` | Route | Handler | |
|---|---|---|---|
| 1245 | `POST /api/save-edits` | `save_edits` | |
| 1323 | `POST /api/generate` | `run_generation` | |
| 1537 | `POST /api/generate/stream` | `run_generation_stream` | **S** |
| 1759 | `POST /api/validate-refinement` | `validate_refinement` | |
| 1771 | `POST /api/generate-cover-letter` | `run_generate_cover_letter` | |
| 4980 | `GET /api/download/<path:filepath>` | `download_file` | ‡ |
| 4993 | `POST /api/download-edited` | `download_edited` | |

### corpus (42)
| `app.py` | Route | Handler |
|---|---|---|
| 288 | `POST /api/upload` | `upload_resume` |
| 322 | `GET /api/users/<username>/resumes` | `list_resumes` |
| 1899 | `POST /api/proposals/<id>/critique` | `critique_proposal_route` |
| 2022 | `POST /api/proposals/<id>/decide` | `decide_proposal_route` |
| 2158 | `POST /api/clarifications/<id>/promote-to-bullet` | `promote_clarification_route` |
| 3436 | `GET /api/users/<username>/experiences` | `list_experiences` |
| 3474 | `POST /api/users/<username>/experiences` | `create_experience` |
| 3539 | `GET /api/experiences/<id>` | `get_experience` |
| 3557 | `PUT /api/experiences/<id>` | `update_experience` |
| 3608 | `DELETE /api/experiences/<id>` | `delete_experience` |
| 3640 | `POST /api/experiences/<id>/bullets` | `create_bullet` |
| 3708 | `PUT /api/bullets/<id>` | `update_bullet` |
| 3764 | `DELETE /api/bullets/<id>` | `delete_bullet` |
| 3818 | `GET /api/users/<username>/summaries` | `list_summary_items` |
| 3858 | `POST /api/users/<username>/summaries` | `create_summary_item` |
| 3909 | `PUT /api/summaries/<id>` | `update_summary_item` |
| 3956 | `DELETE /api/summaries/<id>` | `delete_summary_item` |
| 4013 | `GET /api/users/<username>/skills` | `list_skills` |
| 4056 | `POST /api/users/<username>/skills` | `create_skill` |
| 4117 | `PUT /api/skills/<id>` | `update_skill` |
| 4180 | `DELETE /api/skills/<id>` | `delete_skill` |
| 4240 | `GET /api/experiences/<id>/summaries` | `list_experience_summaries` |
| 4280 | `POST /api/experiences/<id>/summaries` | `create_experience_summary` |
| 4333 | `PUT /api/experience-summaries/<id>` | `update_experience_summary` |
| 4384 | `DELETE /api/experience-summaries/<id>` | `delete_experience_summary` |
| 4416 | `POST /api/experiences/<id>/titles` | `create_experience_title` |
| 4475 | `PUT /api/experience-titles/<id>` | `update_experience_title` |
| 4534 | `DELETE /api/experience-titles/<id>` | `delete_experience_title` |
| 4570 | `GET /api/users/<username>/tags` | `suggest_tags` |
| 4763 | `POST /api/bullets/<id>/tags` | `link_bullet_tag` |
| 4769 | `DELETE /api/bullets/<id>/tags/<tag_id>` | `unlink_bullet_tag` |
| 4775 | `POST /api/experience-titles/<id>/tags` | `link_title_tag` |
| 4781 | `DELETE /api/experience-titles/<id>/tags/<tag_id>` | `unlink_title_tag` |
| 4788 | `POST /api/skills/<id>/tags` | `link_skill_tag` |
| 4794 | `DELETE /api/skills/<id>/tags/<tag_id>` | `unlink_skill_tag` |
| 4800 | `GET /api/users/<username>/duplicates` | `list_corpus_duplicates` |
| 4906 | `POST /api/users/<username>/corpus/ingest-resume` | `ingest_resume_to_corpus` |
| 5055 | `POST /api/bullets/<id>/accept` | `accept_bullet` |
| 5085 | `POST /api/experience-titles/<id>/accept` | `accept_experience_title` |
| 5113 | `POST /api/experiences/<id>/accept-all` | `accept_experience_all` |
| 5148 | `POST /api/users/<username>/accept-all-pending` | `accept_all_pending` |
| 5196 | `GET /api/users/<username>/pending-counts` | `pending_counts` |

### templates/personas (11)
| `app.py` | Route | Handler | |
|---|---|---|---|
| 2457 | `GET /api/personas/bundled` | `list_bundled_personas` | |
| 2491 | `GET /api/users/<username>/personas` | `list_user_personas` | |
| 2534 | `POST /api/users/<username>/personas` | `upload_user_persona` | |
| 2588 | `GET /api/personas/<id>` | `get_persona` | |
| 2606 | `PUT /api/personas/<id>` | `update_persona` | |
| 2654 | `DELETE /api/personas/<id>` | `delete_persona` | |
| 2689 | `GET /api/personas/<id>/download` | `download_persona` | |
| 2737 | `POST /api/personas/<id>/preview` | `preview_persona_with_resume` | |
| 2784 | `GET /api/applications/<id>/preview` | `preview_application_html` | |
| 3018 | `GET /api/applications/<id>/cover-letter-preview` | `preview_cover_letter_html` | |
| 3151 | `GET /api/users/<username>/preview` | `preview_candidate_html` | |

### applications (13)
| `app.py` | Route | Handler |
|---|---|---|
| 5295 | `GET /api/users/<username>/applications` | `list_applications` |
| 5382 | `GET /api/applications/<id>` | `get_application` |
| 5581 | `PUT /api/applications/<id>/status` | `update_application_status` |
| 5623 | `PUT /api/applications/<id>/notes` | `update_application_notes` |
| 5649 | `PUT /api/applications/<id>/meta` | `update_application_meta` |
| 6142 | `GET /api/applications/<id>/composition` | `get_application_composition` |
| 6460 | `POST /api/applications/<id>/composition` | `save_application_composition` |
| 6699 | `POST /api/applications/<id>/recommend` | `recommend_application_bullets` |
| 6809 | `POST /api/applications/<id>/recommend-summary` | `recommend_application_summary` |
| 6893 | `POST /api/applications/<id>/recommend-experience-summaries` | `recommend_application_experience_summaries` |
| 6991 | `POST /api/applications/<id>/recommend-skills` | `recommend_application_skills` |
| 7072 | `POST /api/applications/<id>/suggest-skills` | `suggest_application_skills` |
| 7179 | `GET /api/users/<username>/clarifications` | `list_clarifications` ‡ |

### users/config (6)
| `app.py` | Route | Handler |
|---|---|---|
| 166 | `GET /` | `index` |
| 181 | `GET /api/users` | `list_users` |
| 187 | `POST /api/users` | `create_user` |
| 215 | `GET /api/users/<username>/config` | `get_config` |
| 223 | `PUT /api/users/<username>/config` | `update_config` |
| 234 | `POST /api/users/<username>/profile/fetch` | `fetch_profile` |

### diagnostics (9 + the existing `dashboard_bp` HTML)
| `app.py` | Route | Handler | |
|---|---|---|---|
| 7355 | `GET /api/annotation/fixtures` | `annotation_fixtures` | |
| 7386 | `GET /api/annotation/fixture/<u>/<slug>` | `annotation_load` | |
| 7429 | `POST /api/annotation/fixture/<u>/<slug>` | `annotation_save` | |
| 7472 | `POST /api/annotation/fixture/<u>/<slug>/collate` | `annotation_collate` | |
| 7545 | `POST /api/annotation/fixture/<u>/<slug>/score` | `annotation_score_grounding` | **S** |
| 7684 | `POST /api/annotation/seed/export` | `annotation_seed_export` | |
| 7749 | `POST /api/annotation/bootstrap` | `annotation_bootstrap_stream` | **S** |
| 7948 | `POST /api/eval/run` | `eval_run_stream` | **S** |
| 8074 | `POST /api/tune/run` | `tune_run_stream` | **S** |

### assistant (existing blueprint — move-only/verify)
`assistant_bp` @ `blueprints/assistant.py` — `POST /api/assistant/ask` (SSE). Already split
in 7.5; the only work is dropping its duplicated helpers (§3.3) in the 8.3a foundation branch.

> **‡ judgment calls (finalize at move time, no behavior impact):**
> `iterate-clarify` (Step-6 refinement — placed in *analysis* for clarify-family cohesion;
> could ride *generation*); `download_file`/`download-edited` (generic output downloads —
> placed in *generation*; could be a shared files concern); `list_clarifications`
> (user-scoped read of application clarifications — placed in *applications*; could ride
> *users/config*). Each is a single route whose seam choice does not change its behavior.
