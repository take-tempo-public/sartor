# Release Checklist — callback.

> **Purpose:** the ship-list. What must be true before tagging a
> release, in what order, to what quality bar. The verify-before-
> ship gates for the next release.
> **Audience:** humans driving a release; LLM agents proposing
> version-bump work or release-blocking fixes.
> **Authoritative for:** the *active* release definition (v1.0.1
> at time of writing); the minimum-bar tests / ruff / mypy / eval
> gates; which items are shipping-blockers vs nice-to-haves.
>
> **Companion:** see
> [`docs/PRODUCT_SHAPE.md`](../PRODUCT_SHAPE.md) §10 for the full
> deferred-items table that drives the v1.0.1 / v1.1 / v2 ladder.

---

## Active release — v1.1.0 (public release — user-owned tag)

**Tag history (all local-only — no public release until the user-owned
v1.1.0 tag):** v1.0.1 tagged 2026-05-28, v1.0.2 tagged 2026-05-30,
v1.0.3 tagged 2026-06-02, v1.0.4 tagged 2026-06-02 (commit `072e290`, eval
tuning loop), v1.0.5 tagged 2026-06-07 (UI/UX redesign + diagnostics/tuning
console — **shipped**; all seven §Phase 4 tag criteria met, gate green incl.
`pytest -m ux`). **Versioning model (2026-06-08):** the **patch digit is an epic**
(a bounded set of one-branch sprints); the **minor digit is a tag marker** for a
public version (**1.1.0 = the public release**). Three internal epics now sit
between v1.0.5 and the public tag — **v1.0.6** (walkthrough polish + WS-4 wiki
substrate + corpus completion), **v1.0.7** (the app knows itself: self-documenting
wiki + doc-grounded assistant + pre-public hardening), and **v1.0.8** (monolith →
blueprints; absorbs the type scan) — folded into the arc on 2026-06-08 from the
v1.0.5 walk-through sprint plan + the excellence-walk workstreams + a backlog
grooming; see [`RELEASE_ARC.md`](RELEASE_ARC.md) §Phase 4.5 / §4.7 / §4.8. Deferred
feature ideas live in [`nursery.md`](nursery.md). The immediate next epic is
**v1.0.6**, which **opens with a fresh end-to-end walkthrough**. The public
**v1.1.0** tag remains **owned by the user** — the public cut of the complete
product (assistant + self-documenting wiki + clean blueprints). The v1.0.5 items
below are reconciled in place (shipped → `[x]`); still-open items are carried into
v1.0.6 / v1.0.7 / v1.0.8 / v1.1.0 as noted.

### v1.0.6 — Walkthrough polish + knowledge substrate + corpus completion (NEXT)

Authoritative branch sequence + acceptance: [`RELEASE_ARC.md`](RELEASE_ARC.md)
§Phase 4.5. Gates for the v1.0.6 tag:

- [ ] **E2E walkthrough kickoff (Sprint 6.0)** — user drives the whole product
      (app + evals + tuning) on a real corpus to collect findings; decompose into
      the 6.x buckets (the v1.0.5 method). Doubles as **real-data capture**: the UX
      findings + the real corpus/annotation labels v1.0.7 calibration needs + the
      first outcome data (B.8). Also the signing / re-confirmation pass for the
      **unsigned** `V1_0_5_VERIFICATION.md` and the named-but-unlanded V5-B parity
      fixes (#9 download ≠ preview, #10 step-6 edit not reflected).
- [ ] **Sprints 6.1–6.6 merged** — 6.1 wizard-flow (incl. **B.8 Part 1** outcome
      capture) · 6.2 diagnostics-console · 6.3 forms + a11y (**the axe a11y gate
      lands first**) · 6.4 IA + onboarding (corpus-first) · 6.6 corpus-item completers
      (**B.4** ExperienceSummaryItem, **B.5** SkillGroupItem) · 6.5 in-app education sweep.
- [ ] **Corpus-item completers B.4/B.5** merged **before** the 6.5 sweep (so they're
      documented); **B.8 Part 1** outcome capture complete + verified end-to-end (the
      capture UI already exists — this *completes* it; unblocks the B.8-Part-2 +
      nursery learning layer).
- [ ] **WS-4a landed early; WS-4b before the 6.5 sweep** (the binding gate):
      `docs/system-model.md` (← seven-functions language) + the committed
      `docs/wiki/` skeleton + the `/wiki-*` skills exist; **the preserved
      excellence-walk source ([`excellence-walk/`](excellence-walk/)) is ingested
      into the wiki** (then may retire into its `raw/` layer); the code architecture
      is cold-ingested (`path:line`-grounded); a **user-facing wiki section is
      reserved so 6.5 authors INTO the wiki**.
- [ ] **Governance extraction** (its own gated branch, after the wiki proves out) —
      ⚠ **preserve agent rule-access**: `AGENTS.md`/`CLAUDE.md` are harness-auto-
      loaded; extraction must keep the rules reachable via `@import`/pointer or every
      future agent loses its guardrails. 3 open sub-decisions resolved first
      (Governance home name; per-doc extraction boundaries; AGENTS.md
      shell-vs-inline). *(May spill to a later epic — not a hard v1.0.6 gate.)*
- [ ] **`docs/eval-stack-install-guide` (#17)** — the user-facing install/prepare
      guide authored from the excellence walk's **Q3** deliverable (now preserved at
      [`excellence-walk/q3-downloads.md`](excellence-walk/q3-downloads.md)) + a
      README/`install.md` "what gets downloaded & why" section.
- [ ] `ruff + mypy + pytest + pytest -m ux` green; `chore/version-bump-v1.0.6`.

> **Source preserved (no longer at-risk).** The excellence-walk drafts — the system-
> model/whys, the five-question deliverables (Q1–Q3), the sprint plan — were promoted
> from gitignored scratch into tracked **[`excellence-walk/`](excellence-walk/)** on
> 2026-06-08 and the originals deleted; git now holds them. WS-4a **ingests that
> folder into the wiki early** in this epic, after which the flat folder may retire
> into the wiki's `raw/` layer.

### Discovered during the v1.0.5 stream (tracked, deferred)

- [ ] **Grounding/hallucination metric inserted into the v1.0.5 sequence**
      (user-approved re-sequence 2026-06-05). `eval/grounding-metric-l0` (the
      deterministic, label-free L0 fabricated-specifics rate) now lands **before**
      `feat/diagnostics-console-redesign` so the dashboard is designed around a
      real metric contract. The **calibrated** model-based layers + the never-run
      v1.0.4 live loop + the evals/tuning update are deferred to **pre-v1.1.0**
      (no labeled data exists yet — `evals/fixtures/real/` is empty). Authoritative
      detail: [`RELEASE_ARC.md`](RELEASE_ARC.md) §Phase 4 re-sequence note +
      [`GROUNDING_METRIC.md`](GROUNDING_METRIC.md); deferred follow-up tracked in
      [`docs/PRODUCT_SHAPE.md` §10](../PRODUCT_SHAPE.md) "Grounding / hallucination
      metric — calibrated layers (B)".
      **Status (2026-06-06):** the **A / L0 slice shipped** via
      `eval/grounding-metric-l0` — `hardening.compute_fabricated_specifics`
      (typed, severity-weighted, tolerance + entity aliasing) +
      `hardening.assemble_source_union`, with a single `groundedness` composite
      (L0-only by default; L1/L2-enriched under `--grounding-signals`) riding
      every eval record in `deterministic_metrics`. **Box stays unchecked** — the
      calibrated layers (B) are still open, and this item only closes when B lands.
      **Now scheduled as v1.0.7 Sprint PV / PV-2** (`eval/grounding-calibration`;
      [`RELEASE_ARC.md`](RELEASE_ARC.md) §Phase 4.7).

- [x] **Diagnostics console → interactive self-tuning loop (the "finish the
      faceplate" arc)** — sourced 2026-06-06 from a walkthrough finding
      (user-approved). The `feat/diagnostics-console-redesign` + `feat/annotation-tab`
      surfaces shipped but stop at CLI hand-offs (grounding only via the
      `--grounding-signals` flag, Tuning tab a stub, `collate` returns a paste-this
      `run_command`). This arc completes them into a browser-driven loop (produce →
      annotate → grounding-score → run eval → A/B → see deltas); the irreversible
      **promote** stays the agent's job. Authoritative sequence + acceptance:
      [`RELEASE_ARC.md`](RELEASE_ARC.md) §Phase 4 "Diagnostics console — interactive
      completion". **Status (2026-06-07):** Steps 1–2 shipped. Step 1
      `feat/grounding-scorers-in-console` (merged `bc29a07`) made the scorers reachable
      from the Annotate tab (opt-in bootstrap + "Score grounding" backfill) and browser
      bootstraps now capture a `seed.json`; Step 2 `feat/run-eval-from-console` extracted
      `evals.runner.run_suite` (the importable core `main()` is now a thin wrapper over)
      and added the localhost SSE `POST /api/eval/run`, a Quality-tab "Run eval" control,
      and an Annotate-tab "Run this fixture" button — the eval is now runnable from the
      browser; Step 3 `feat/tuning-tab-ab` (2026-06-07) replaced the Tuning stub with a
      real in-browser candidate-vs-baseline A/B — a dedicated localhost SSE
      `POST /api/tune/run` drives `run_suite` twice (baseline + candidate via
      `analyzer.prompt_overrides()`) and renders the `evals.tune` delta table; the
      irreversible **promote** stays the agent's job (no route edits `analyzer.py`).
      Step 4 `docs/tuning-loop-discoverability` (2026-06-07, docs only) closed the arc:
      the in-app diagnostics-modal/pill/settings copy now advertises the interactive
      loop, the end-to-end console walkthrough landed in [`evals/README.md`](../../evals/README.md)
      (the dev-doc home) with [`walkthrough.md`](../walkthrough.md) carrying a flag +
      link to it, and [`GROUNDING_METRIC.md`](GROUNDING_METRIC.md) was updated to note
      the label-producing loop is now browser-driven. **All four steps shipped — arc
      complete.**

- [x] **Standalone one-click corpus-seed export (`feat/seed-export-button`)** —
      flagged 2026-06-07 during the `docs/tuning-loop-discoverability` close-out.
      Generating a corpus `seed.json` should be a one-click, **LLM-free** unit, but
      today the only in-browser trigger is bundled inside the **paid** Annotate-tab
      bootstrap (`POST /api/annotation/bootstrap`); the deterministic
      `python -m scripts.export_corpus_seed --user <name>` CLI exists but is the only
      no-cost path. Proposed: a small **localhost** route + an Annotate-tab button
      calling `scripts.export_corpus_seed.export_seed` directly — deterministic, no
      paid call, reusing the existing write-guard (`_safe_username` + `_within(seed,
      ANNOTATION_ROOT)` + `secure_filename`, the same guard the bootstrap/score routes
      use). Separate functional unit from the docs arc; **next small `feat/` branch**
      after this docs branch (user-approved sequencing 2026-06-07).
      **Status (2026-06-07): shipped** via `feat/seed-export-button` (commit
      `3aa6a45`). Added the synchronous, localhost-only `POST /api/annotation/seed/export`
      (reads the live DB via `export_seed`, no model calls, no SSE) + an Annotate-tab
      "Export seed (no LLM)" button distinct from the paid "Run bootstrap"; factored a
      shared `_write_seed_json` writer out of the bootstrap route (bootstrap behavior
      byte-identical). Security trio enforced; unknown user → 400, config-only user with
      no corpus → 409. Tests in `TestSeedExport`; no `PROMPT_VERSION` bump, no new dep.

- [ ] **Compose custom bullet order visually reverts on reload when an
      experience has no LLM recommendations** — surfaced 2026-06-04 while
      building the `feat/playwright-ux-suite` bullet-drag regression test. The
      saved `composition_overrides.bullet_order` round-trips correctly through
      `POST`/`GET /api/applications/<id>/composition`, and `generate()` still
      honors it (`_stable_user_prefix`), so the *persisted* order is intact.
      But [`_renderComposeCard`](../../static/app.js) routes
      no-recommendation experiences through `_dropoffPick`, which re-sorts the
      fallback bullets by **score** — so the *on-screen* order reverts after a
      Compose reload even though the data is correct. The common path
      (recommendations present → bullets land in the `visible` set → the GET
      array order is preserved) is unaffected, and the bullet-drag regression
      test covers that path. Fix belongs in a future Compose-render branch:
      honor the GET array order on the no-recommendations fallback path too,
      instead of re-sorting by score. **Now scheduled as v1.0.6 Sprint 6.1**
      (`fix/compose-order-no-recommendations`; [`RELEASE_ARC.md`](RELEASE_ARC.md)
      §Phase 4.5).

The v1.0.1 item list below was **reconciled in place at the v1.0.3 tag
(2026-06-02)**: completed items are checked; still-open items are flagged
`→ OPEN` with their current owning release. The v1.0.0 release landed in
commit `075d830` (with subsequent template curation, paged.js pagination,
and docs reworks landing on the same branch before tag); v1.0.1 was the
first follow-up release.

### Must do before tag (shipping blockers)

- [x] **~~Manual fresh-clone verification~~** — ✅ done (user-confirmed
      2026-06-02): clean-directory clone → `pip install -e .` +
      `python -m playwright install chromium` + `python app.py` → one
      application completed end-to-end. Evergreen — re-run at the v1.1.0
      public-release cut (risk register D.4 below).
- [x] **~~Eval baseline check~~** — ✅ verified 2026-05-26.
      `python evals/runner.py --suite synthetic --subset smoke`
      run twice (cost ~$0.79 across both); second run clean with
      all three synthetic fixtures at or within ±0.0 of
      `evals/results/baseline_v1.json` (data-scientist-junior 4.8
      = 4.8; pm-senior 4.8 = 4.8; sre-mid-level 4.7 = 4.7). First
      run surfaced a transient judge JSON parse failure on
      data-scientist-junior; see the "Judge JSON parse failures
      mis-categorized as `status=ok`" entry under "Should do" for
      the one-line `evals/runner.py:289` follow-up that would have
      prevented the false-positive regression alarm.
- [x] **~~Quality gate~~** — ✅ verified 2026-05-28. `ruff check .` +
      `mypy .` (81 files, no issues) + `pytest` (637 passed) all
      clean on branch `chore/quality-gate-version-bump-v1.0.1`.
- [x] **~~`pyproject.toml` version bump~~** — ✅ done 2026-05-28.
      `version = "1.0.1"` in [`pyproject.toml:7`](../../pyproject.toml).
      Landed in `chore/quality-gate-version-bump-v1.0.1`.
- [x] **~~`CHANGELOG.md` flip~~** — ✅ confirmed 2026-05-28. The
      `[1.0.1] — 2026-05-28` section was written ahead of time and is
      correct; `[Unreleased]` placeholder is clean. "Resume Optimizer"
      name in line 3 fixed to "callback." in this branch.
- [ ] **Push to GitHub + verify the `https://github.com/amodal1/callback`
      URL resolves** **→ OPEN, owner v1.1.0** — pushed **when the user is
      ready to push the v1.1.0 public-release tag**; the repo stays
      local-only until then (no `origin` remote configured). Action at the
      v1.1.0 cut: create the GitHub repo (public, name `callback`, under
      `amodal1`), `git remote add origin
      git@github.com:amodal1/callback.git`, push `main` and the
      release tag, then verify that `pyproject.toml` Homepage /
      Repository / Issues / Changelog URLs and `README.md`/
      `docs/install.md` clone instructions all resolve.

### Should do (v1.0.1 polish; document if skipped)

- [x] **Step 6 (Output) redesign** **✓ SHIPPED v1.0.5** (`feat/step6-redesign`,
      merged `43a60dc`; cover-letter styling landed with `feat/cover-letter-formats`
      `5fa186b`)
      (`feat/step6-redesign`, RELEASE_ARC §Phase 4) — surfaced during the
      v1.0.0 review: cut the obsolete tabs + raw/rendered toggle
      (replaced by paged.js preview); preview at the top of
      the step; edit-raw via modal; Changes → info-icon modal;
      cover letter → single "+ Generate" button until generated.
      **Cover-letter styling decisions (user-confirmed 2026-05-26
      for the B-phase work):**
      - **Header treatment:** terser than the résumé — business-
        letter style. No big name banner / contact bar repeat;
        use fonts appropriate to (i.e., matching) the chosen
        résumé template, but plain — nothing fancy.
      - **Body line spacing:** business-letter dense (single-
        spaced or near it), NOT breathy / generous line-height.
      - **Addressee block** (`Hiring Manager,` / company name /
        date): rendered **inline** with the body — no separately
        styled block, no boxed treatment.
- [x] **~~BACK / Continue spacing polish on Compose~~** — ✅ verified
      2026-05-28 (commit `8d59361`). Spacing confirmed correct; no
      visual change needed. Listed in PRODUCT_SHAPE §10 as deferred
      from v1.0.0.
- [x] **~~`docs/install.md` updated~~** — ✅ resolved 2026-05-28.
      Test count updated (`627+` → `637+`); Windows section now
      covers PowerShell `$env:` syntax for the API-key step, a
      `python -m pip` fallback for Windows Store Python installs,
      and the `sysdm.cpl` shortcut for setting a permanent env var.
- [x] **~~Accessibility scan of all user-facing documentation~~** —
      ✅ resolved 2026-05-28. Full audit of
      [`README.md`](../../README.md),
      [`docs/install.md`](../install.md),
      [`docs/walkthrough.md`](../walkthrough.md),
      [`docs/walkthrough_example.md`](../walkthrough_example.md),
      [`vision.md`](../../vision.md), and the 10 PNGs in
      [`docs/screenshots/`](../screenshots/).
      - **Alt text** — all 10 images have substantive, descriptive
        alt text. No "a screenshot" placeholders.
      - **Mermaid diagrams** — the second diagram already had
        "Read this top-down: …". Added an equivalent
        "Read this left-to-right: …" prose summary immediately
        after the first (user-flow) diagram in `walkthrough.md`.
      - **Heading hierarchy** — no skipped levels in any file.
      - **Link text** — no "click here" / "see this" patterns.
      - **Color-only meaning** — first diagram: explicit 4-class
        text legend. Second diagram: semantic subgraph labels
        encode meaning independently of color.
      - **Tables** — all use markdown `| Header |` syntax;
        no hand-rolled HTML tables found.
- [x] **~~Doc-vs-UI label drift on the corpus import button~~** —
      ✅ resolved 2026-05-26. Button renamed
      `+ Drop résumé (AI extract)` → `+ Import résumé` (cleaner
      action verb than "Drop" which conflated drag-and-drop with
      the action itself; the parenthetical leaked the AI-extract
      implementation detail into a button label). Live docs
      ([`docs/walkthrough.md`](../walkthrough.md),
      [`docs/install.md`](../install.md),
      [`docs/ux/screenshot_capture.md`](../ux/screenshot_capture.md))
      synced to the new label. The audit at
      [`docs/ux/onboarding_audit_2026-05-25.md`](../ux/onboarding_audit_2026-05-25.md)
      is left as the historical record (the audit accurately
      reports the doc/UI mismatch as it existed on 2026-05-25).
      The internal API route `/api/users/<user>/import-legacy`
      keeps its name — route rename is a separate cleanup, v1.1.
- [x] **~~Bullet-dedup gap in corpus re-import~~** — ✅ resolved
      2026-05-26. Changed `_merge_into_existing_experience` in
      [`onboarding/import_legacy.py`](../../onboarding/import_legacy.py)
      to dedup on **normalized bullet text** instead of
      `(source, text)`. The old key missed same-file re-imports
      because the source flips from `primary:<file>` to
      `supplemental:<file>` on the merge path, so the same text
      under two different sources slipped through as a "new"
      bullet. The new key matches regardless of source; different
      phrasings from different files still survive (they have
      different normalized text). Test
      `test_merge_dedupes_identical_bullet_text_across_sources`
      in [`tests/test_onboarding_import_legacy.py`](../../tests/test_onboarding_import_legacy.py)
      pins the new behavior; all 24 tests in that file pass.
- [x] **~~Wizard rail step buttons don't re-enable after prior step
      completes~~** — ✅ resolved 2026-05-26. Added a
      `_wizardRender()` call in `runAnalysis()`'s success path
      (after `lastContextPath` is set), so the rail picks up
      step 2 as `_wizardReachable` immediately. `runGeneration()`
      was already calling `_wizardAdvanceTo(6)` (which includes
      a `_wizardRender`), so the step-6 side of the bug was
      already covered — the bug only existed on the analyze →
      step 2 transition.
      [`scripts/capture_screenshots.py`](../../scripts/capture_screenshots.py)
      still navigates forward via the in-flow Continue buttons;
      that's fine and matches the real-user happy path, but rail
      clicks would now work too.
- [x] **Playwright UX clickthrough regression suite** **✓ SHIPPED v1.0.5**
      (`feat/playwright-ux-suite`, merged `aeb3e51`; `pytest -m ux` = 12 tests:
      happy-path-stubbed flows + the backfilled 2026-05-26/2026-06-04/2026-06-06
      regression tests, shared `ui_pages/` driver)
      (`feat/playwright-ux-suite`, RELEASE_ARC §Phase 4) —
      surfaced during the screenshot-capture pass (2026-05-26). The
      screenshot script at
      [`scripts/capture_screenshots.py`](../../scripts/capture_screenshots.py)
      drives the wizard end-to-end and incidentally exposed
      several UI bugs above (rail re-enable, corpus render,
      bullet-dedup gap, label drift) that the existing `pytest`
      unit suite doesn't catch because they live in JS render
      paths, not Python. Build a proper UX regression suite
      under `tests/ux/` so future PRs can't reintroduce these
      classes of bug. Structure (industry-standard
      Playwright + Page Object Model):
      - **`tests/ux/conftest.py`** — session Flask fixture on
        an ephemeral port; per-test browser context with a
        **console-error sentinel** (any `pageerror` or
        `console.error` fails the test — this alone would have
        caught the silent corpus-render failure); autouse
        fixture that isolates `configs/` / `resumes/` /
        `output/` + cleans demo-user DB rows on teardown.
      - **`tests/ux/pages/`** — one POM class per panel
        (`user_picker.py`, `corpus.py`, `wizard_step1_job.py`
        through `wizard_step6_output.py`, `cover_letter.py`).
        Mechanical refactor of the navigation already in
        [`scripts/capture_screenshots.py`](../../scripts/capture_screenshots.py).
      - **`tests/ux/fixtures/`** — `factories.py` (lift
        `write_priya_docx` + `PRIYA_JD` from the screenshot
        script); `api_stubs.py` (`page.route()` handlers
        returning canned LLM JSON for fast/free runs); a JD
        corpus with diverse shapes (Kafka backend, frontend,
        junior IC, exec).
      - **`tests/ux/flows/`** — full multi-step journeys:
        happy-path-stubbed, happy-path-real-llm, navigation
        (forward/back/jump/rail-disabled invariants),
        interruptions (reload mid-LLM, user-switch
        mid-wizard, close+reopen), state-reset, iteration
        loop (`parent_context_path` chain integrity).
      - **`tests/ux/error_handling/`** — stubbed API 5xx /
        timeout / offline / invalid input / concurrent-tab
        writeback. The category most likely to surface
        regressions.
      - **`tests/ux/regression/`** — one test per shipped
        bug, named `test_<YYYYMMDD>_<slug>.py`, never
        deleted. Backfill the five bugs from the 2026-05-26
        pass first (rail re-enable, corpus render, bullet
        dedup, doc-vs-UI label, plus any others the
        Playwright debug pass surfaces).
      - **`tests/ux/a11y/test_axe_smoke.py`** —
        `@axe-core/playwright` against each panel; no
        serious/critical violations.
      Two-tier execution via pytest markers (add `ux` +
      `real_llm` to `pyproject.toml`'s existing `markers`
      list):
      - `pytest -m "ux and not real_llm"` — stubbed, ~30s,
        $0; runs on every PR.
      - `pytest -m "ux and real_llm"` — one happy-path
        real-API smoke, ~$0.30 + ~6min; gated on `.api_key`
        presence (skip if absent so forks don't fail).
      Wire `pytest -m ux` into `.git/hooks/pre-push` (or a
      `make pre-pr` target) and document in
      [`CONTRIBUTING.md`](../../CONTRIBUTING.md) as the standard
      pre-PR ritual. **Defer if time-bound:** land the harness
      + `conftest.py` + one happy-path-stubbed test in v1.0.1;
      backfill the `regression/` + `error_handling/` +
      `flows/` tests across v1.0.1 and v1.1 as the screenshot-
      pass bugs get fixed (each fix lands with its regression
      test). **Prereq:** the screenshot script itself must
      stabilize first (currently being debugged) — the POMs
      lift directly from its navigation logic, so a moving
      script means churning POMs.
- [x] **~~Corpus tab render-after-refresh bug~~** —
      ✅ resolved 2026-05-27 (downstream of thread-race fix).
      Root cause confirmed: the `/personas` 500 thread-race
      (`fix/personas-500-thread-race`, commit `a32bc1b`) was
      corrupting upstream state on first user-select after restart,
      leaving `_corpusExperiences` in a bad state before
      `_renderCorpusList` ran. After the `threading.Lock()` fix
      landed, the corpus tab renders cards correctly on first load
      with no `console.error`. The try/catch instrumentation from
      `16d7ad4` stays in place as a safety net for future regressions.
- [x] **~~`/personas` 500 on first user-select after server restart~~** —
      ✅ resolved 2026-05-27. Added `threading.Lock()` around the
      check-and-init block in [`db/session.py`](../../db/session.py)
      `init_db()` (three lines: `import threading`, `_init_lock =
      threading.Lock()` at module level, `with _init_lock:` wrapping
      the entire check-then-`_initialized_paths.add()` sequence). The
      race: `onUserSelect` fires multiple concurrent requests on first
      user-select after restart; all threads saw an empty
      `_initialized_paths`, all attempted `command.upgrade()`
      simultaneously, corrupting alembic's module-level globals. The
      lock makes the check-and-add atomic — only the first thread runs
      `upgrade()`; the rest short-circuit once it completes. Branch
      `fix/personas-500-thread-race`.
- [x] **~~Judge JSON parse failures mis-categorized as `status=ok`~~** —
      ✅ resolved 2026-05-26.
      [`evals/runner.py:289`](../../evals/runner.py) now returns
      `{"score": 0, "reasons": [...], "raw": raw, "status": "judge_error"}`
      so the existing `judge_error` path in `_detect_regression` /
      summary logic skips these records correctly. New test
      `test_unparseable_json_marks_status_judge_error` in
      [`tests/test_eval_runner.py`](../../tests/test_eval_runner.py)
      pins the behavior; all 25 tests in that file pass. The
      false-positive WARN observed in
      [`evals/results/20260526_170400Z.jsonl`](../../evals/results/20260526_170400Z.jsonl)
      (`data-scientist-junior × grounding`, -4.8 delta) won't
      recur — re-running the smoke pass should produce a clean
      result.
- [x] **~~Re-baseline eval scores for v1.0.1~~** — ✅ superseded 2026-06-02
      by the **v1.0.2 schema-3 baseline** (`eval/baseline-v1-0-2`; TUNING_LOG
      "BASELINE — v1.0.2 — 2026-05-28"): five back-to-back synthetic runs at
      the shipping `PROMPT_VERSION 2026-05-24.4` replaced the stale
      `2026-05-12.1`-sourced baseline, resolving the apples-to-apples concern
      this item raised. Original detail retained below for the audit trail.
      [`evals/results/baseline_v1.json`](../../evals/results/baseline_v1.json)
      was sourced from
      [`evals/results/20260513_221926Z.jsonl`](../../evals/results/20260513_221926Z.jsonl)
      on `prompt_version=2026-05-12.1` (recorded 2026-05-25), but
      [`analyzer.py`](../../analyzer.py)'s current `PROMPT_VERSION`
      is `2026-05-24.4` — three prompt revisions shipped with
      v1.0.0 between the baseline source-run and tag. The
      baseline file's own `notes` field already calls this out
      ("a re-baseline is recommended early in v1.0.1 once the
      streaming/split-analyze changes from docs/dev/perf/PERF_ANALYZE.md
      land"). The smoke pass on 2026-05-26 showed the two
      successfully-graded fixtures essentially unchanged
      (`pm-senior`: 4.8 = 4.8; `sre-mid-level`: 4.8 vs 4.7,
      Δ=+0.1), so the drift appears benign — but the "Eval
      baseline check" Must-do at
      [`docs/RELEASE_CHECKLIST.md:32-35`](RELEASE_CHECKLIST.md)
      is comparing against scores no longer apples-to-apples
      with shipping code. Action: once the
      [`evals/runner.py:289`](../../evals/runner.py) judge-error
      fix lands AND the v1.0.1 prompt landscape is final (R2
      streaming work either in or explicitly deferred), run
      the full synthetic suite (`python evals/runner.py --suite
      synthetic`, ~$1.50, all five rubrics × three fixtures)
      and replace `baseline_v1.json` with a v1.0.1 baseline.
      Document the cut as a dated entry in
      [`evals/TUNING_LOG.md`](../../evals/TUNING_LOG.md) per its
      four-question structure. **Defer:** v1.0.1 CAN ship
      against `baseline_v1` (smoke noise from the judge-error
      bug aside, the underlying scores are stable); the
      re-baseline is hygiene, not a blocker — slip to early
      v1.1 if v1.0.1 ships fast.
- [x] **Walkthrough documentation pass — three fixes** —
      ✅ resolved 2026-05-27.
      (a) Corpus→Application transition paragraph added to
      `docs/walkthrough.md` between Setup and Step 1 —
      instructs the reader to click the **Application** tab and
      select Step 1 in the wizard rail before pasting a JD.
      (b) `scripts/capture_screenshots.py` `run_step2()` now
      calls
      `page.locator("#clarifyQuestions").scroll_into_view_if_needed()`
      + `wait_quiet(page, 300)` before `cap()`, so re-running
      the script will produce a properly-scrolled PNG showing
      the actual questions.
      (c) `docs/walkthrough_example.md` confirmed intentional —
      purpose statement at lines 1–14 establishes it as the
      Priya companion to the abstract walkthrough; no file
      change needed.
- [x] **~~CSP `unsafe-eval` violation on script execution~~** —
      ✅ investigated 2026-05-28. Full grep of `static/app.js`,
      `static/vendor/paged.polyfill.js` (33 K lines), and
      `templates/index.html` found **zero** instances of `eval(`,
      dynamic-Function constructor, or string-form
      `setTimeout`/`setInterval`. The app sets **no**
      `Content-Security-Policy` response header; there is no
      server CSP to be violated. Root cause of the original
      dev-console message: Chrome surfaces sandbox-block events
      using CSP-style error text. Before the 2026-05-27 sandbox
      fix ("`Sandboxed iframe blocks script execution ×17`"
      item above), the preview iframes carried `sandbox` without
      `allow-scripts` — effectively `script-src 'none'` — which
      blocked paged.js and appeared as an `unsafe-eval` violation
      in the console. The sandbox fix (`allow-scripts
      allow-same-origin`) resolved it. The absence of a real
      `Content-Security-Policy` header is documented as an
      accepted-risk entry in [`SECURITY.md`](../../SECURITY.md)
      (appropriate for localhost-only v1.0.1; add before any
      networked deployment).
- [x] **~~Sandboxed iframe blocks script execution ×17~~** —
      ✅ resolved 2026-05-27. Both preview iframes (`#livePreviewFrame`
      in the Compose step and `#outputPreviewFrame` in Step 6) now
      use `sandbox="allow-scripts allow-same-origin"`, which lets
      paged.js polyfill execute inside the frame. `allow-same-origin`
      stays so `_updatePreviewPageCount` can read
      `frame.contentDocument` for the page-count chip; the two flags
      together effectively neutralize the sandbox per spec, but the
      iframe content is our own generated HTML (corpus + persona
      template + injected paged.js polyfill), not user-supplied
      markup — security posture is acceptable for v1.0.1 with a
      load-bearing comment at the call sites explaining the
      tradeoff. A future refactor could host paged.js outside the
      iframe and message-pass for true sandboxing (v1.0.2 or v1.1
      polish).
      **Downstream resolution:** this also closes the
      "Template preview pagination — blank pages between sections"
      tracked item below — paged.js is what handles intelligent
      `page-break-inside: avoid` layout; the blanks were the
      browser's naive fallback when paged.js couldn't run.
- [x] **~~Form fields without `id` or `name` attribute~~** —
      ✅ resolved 2026-05-28 (commit `b904a87`). Added `sr-only`
      `<label for="…">` elements for the six new-user form fields
      (`newUsername`, `newName`, `newEmail`, `newPhone`,
      `newLinkedin`, `newWebsite`) and the `memoryKindFilter`
      select in [`templates/index.html`](../../templates/index.html).
      All seven Chrome-flagged "violating nodes" now have
      associated labels; browser-autofill and screen-reader
      association restored. No functional change.
- [x] **~~Two `POST /api/analyze 409`s observed during Corpus-tab
      session~~** — ✅ investigated + logged 2026-05-28. Code
      audit confirmed:
      - **Single 409 trigger in `/api/analyze`:** both
        `_run_analysis_corpus_backed` and its streaming sibling
        return 409 only when `build_context_set_from_db` raises
        `ValueError` — i.e., the selected user has no `Candidate`
        row in the DB yet. Message: `"No candidate with
        username=..."`. No other 409 branches exist in these two
        functions.
      - **Corpus tab cannot implicitly call analyze:** `onUserSelect`
        fires `loadConfig`, `refreshApplications`,
        `_loadPersonaOptions`, `wizardInit` — none touch
        `/api/analyze`. The Corpus-tab 409 handler
        (`refreshCorpus`, `refreshMemory`, `refreshApplications`)
        is a *separate* set of routes, not analyze.
      - **Conclusion: expected behavior.** The two 409s were
        triggered by a user clicking Analyze for a user not yet
        onboarded (or by the post-onboarding-modal retry path).
        The JS correctly responds by opening the onboarding modal
        (`openOnboardingModal(runAnalysis)`); after successful
        import the analyze call retries and succeeds.
      - **Logging added** (commit on this branch): both 409
        branches now emit `logger.warning("[analyze 409] user=X
        needs_onboarding: ...")` so future occurrences are
        self-describing in the Flask log. Response payload
        unchanged.
      **Aside on console noise:** the bulk of the dev-console
      output during the original capture was
      `content.js:360 The kernel 'X' for backend 'webgl|cpu'
      is already registered` from a browser extension's content
      script (TensorFlow.js classifier running in `content.js`
      + `classifier.js`) — NOT our code.

- [x] **~~Template preview pagination — blank pages between
      sections~~** — ✅ resolved 2026-05-27 alongside the
      "Sandboxed iframe blocks script execution" entry above.
      Diagnosis was wrong in the original entry — the blanks
      were NOT caused by `page-break-inside: avoid` doing its
      job too aggressively; they were caused by paged.js (which
      handles intelligent break-vs-fit decisions for that CSS
      rule) being blocked from executing inside the
      `sandbox="allow-same-origin"` iframe. Once paged.js is
      allowed to run via `sandbox="allow-scripts allow-same-origin"`,
      it lays out content efficiently. If pagination quality is
      still imperfect after the sandbox fix (e.g., specific
      experience cards still push to new pages with blanks), the
      original fix paths remain valid for future polish:
      (a) tighten template densities, (b) drop
      `page-break-inside: avoid`, (c) add a "compact" mode.
      **Follow-up (2026-06-04, `feat/template-pagination`, v1.0.5):** path (b)
      landed — Modern/Spacious/Tech carried `section { page-break-inside: avoid }`
      (Classic did not), which forced paged.js to keep each whole section
      together and shoved oversize Experience sections onto blank/short pages.
      Dropped the section-level rule (kept the correct per-entry
      `article { page-break-inside: avoid }`) and added Classic's
      `h2 { page-break-after: avoid }`. Pinned by
      `tests/ux/regression/test_20260604_template_pagination.py` (no blank page
      across all four bundled templates). Closes the v1.0.5 tag criterion
      "Pagination fixed for all 4 bundled templates."

- [x] **~~Chrome "multiple downloads blocked" silently kills 2nd download~~** —
      ✅ resolved 2026-05-27 (UI hint). Added a one-line hint paragraph
      below the download button row in Step 6 (`templates/index.html`)
      pointing users to the Chrome address-bar ↓ icon → "Always allow
      downloads from this site". The underlying JS mechanism (programmatic
      anchor click) is unchanged; a server-side `Content-Disposition:
      attachment` redirect that avoids the per-page gesture requirement is
      tracked for v1.0.2. Branch `fix/chrome-multi-download-hint`.
- [x] **~~paged.js polyfill "Cannot read getBoundingClientRect of
      null"~~** — ✅ **console symptom contained** 2026-06-04
      (`feat/template-pagination`, v1.0.5), option (a). **Not** root-cause
      elimination — read this carefully so a future agent doesn't over-read
      "resolved": the throw still fires *inside* the vendored paged.js
      (`static/vendor/paged.polyfill.js` v0.4.3); we catch-and-ignore it. The
      polyfill's auto-run (~L33239) `await`s `previewer.preview()` with **no
      `.catch()`**, so a sparse-content layout throw escaped as an uncaught
      rejection. The injection in `app.py` (`_PAGED_PREVIEW_INJECTION`) now
      disables auto-run (`window.PagedConfig = { auto: false }`) and drives
      `new Paged.Previewer().preview()` itself inside `try/catch` + `.catch()`;
      the sibling `node.getAttribute is not a function` *sync* throw (fired off
      the awaited chain) stays covered by the paged-origin `window.error`
      swallow. The `tests/ux/conftest.py` `getBoundingClientRect` allowlist is
      **removed** — the sentinel is now unconditional, so a *new/different*
      paged.js error is not swallowed and WILL fail the suite — and
      `tests/ux/regression/test_20260604_template_pagination.py` asserts a clean
      console across all four bundled templates. Safe **only** because the
      render completes correctly despite the throws (that test also asserts no
      blank pages). **Root-cause elimination** = leave paged.js (option (c));
      tracked in [`docs/PRODUCT_SHAPE.md` §10](../PRODUCT_SHAPE.md) "paged.js
      preview-render fragility — contained, not eliminated".
- [x] **~~Cover-letter download honors the chosen output format~~** —
      ✅ resolved 2026-05-28 (path b, UI hint). Added a one-line hint
      paragraph below the download button row in
      [`templates/index.html`](../../templates/index.html):
      *"Cover letter downloads as .docx in v1.0.1. PDF and Markdown
      format support coming in v1.0.2."* The underlying
      `generator.generate_cover_letter` still hardcodes `.docx` (no
      change — path (a), full format support, is v1.0.2 alongside
      B3 persona styling work).
- [x] **Prior-application click resumes the wizard at that
      application's last state** **✓ SHIPPED v1.0.5** (`feat/prior-app-resume`,
      merged `cc74f90`)
      (`feat/prior-app-resume`, RELEASE_ARC §Phase 4) (user-surfaced
      2026-05-26 during round-6 smoke). Today, clicking a card in the "Prior
      applications" panel of Step 1 shows a one-line toast with
      title/status/iter-count and nothing else — that's an
      acknowledged placeholder per the comment at
      [`static/app.js:3404-3406`](../../static/app.js#L3404):
      *"Lightweight info display in the toast for now — resuming an
      application into the live editing flow ships in D.3.1."*
      Expected behavior (user-confirmed): clicking should load the
      application's context_path + selected persona + last-generated
      résumé/cover letter into the wizard and jump to the most
      advanced step that has data (typically Step 6 — Generated
      output). Implementation: the application row's runs[] already
      carries a `context_path` per iteration; the most recent run's
      context_path is the load target, the run's persona_template_id
      drives the template selection, and the run's resume_path /
      cover_letter_path hydrate the editors. Defer to v1.0.2; user
      can re-create from scratch in v1.0.1.

### Nice to have (defer to v1.1 if time-bound)

- [ ] **Visual assets** **→ OPEN, owner v1.1.0** (`release/visual-assets`,
      RELEASE_ARC §Phase 5) — screenshots, demo GIF, onboarding HTML
      page. PRODUCT_SHAPE §10 defers this to v1.0.1; if the
      planned UI redesign hasn't started, ship visual assets
      against the current UI rather than wait.
- [x] **~~R2 — stream `analyze()` output~~** — ✅ done in v1.0.1
      (CHANGELOG [1.0.1] "Added — Performance (R2 streaming)"):
      `/api/analyze/stream` + `/api/generate/stream` SSE routes shipped with
      spinner-default UX; the v1.0.3 two-pass split later layered the `phase`
      sentinel on top. (docs/dev/perf/PERF_ANALYZE.md, $0, perceived latency
      90s → 10-15s.)

### Pre-tag cleanup + review stage (do last, before v1.0.1 tag)

User-stated 2026-05-26: cull temporary exploration artifacts so
they don't continue to track. Run this as a focused stage AFTER
B1–B3 land and AFTER the fresh-clone verification, immediately
before the version-bump commit.

- [x] **~~Remove `docs/mockups/`~~** — ✅ resolved 2026-05-28.
      Grepped `templates/`, `scripts/`, `docs/` for `docs/mockups`
      — the only hit was a comment in `templates/index.html:126`
      (no live consumer). Deleted the directory (6 files including
      the undocumented `index.html`); stripped the comment
      reference. Branch `chore/pre-tag-cleanup-docs`.
- [x] **~~Audit `docs/archive/`~~** — ✅ resolved 2026-05-28.
      Only file: `docs/archive/2026-05-25_doc_audit.md` (pre-release
      v1.0.0 documentation audit). Confirmed not referenced anywhere
      outside itself. Deleted outright — all recommendations in that
      audit were implemented in v1.0.0 commits. Branch
      `chore/pre-tag-cleanup-docs`.
- [x] **~~Strip dead-link references from CHANGELOG history~~** —
      ✅ resolved 2026-05-28. Extracted all 17 relative-path links
      from `CHANGELOG.md`; all 17 resolve. No broken links found.
      Branch `chore/pre-tag-cleanup-docs`.
- [x] **~~`scripts/perf_baseline.py`~~** — ✅ resolved 2026-05-28.
      Added to `docs/architecture.md` module map as a release-cycle
      tool (p50/p90 latency snapshot before/after perf interventions).
      Branch `chore/pre-tag-cleanup-code`.
- [x] **~~`r1-attempted-2026-05-26` branch~~** — **DELETED 2026-06-02** (tip
      `09815a1`; reflog-recoverable ~90 days). Supersedes the earlier "KEPT as
      historical reference" decision. v1.0.3 R1 Phase 2 is complete; all R1
      branches (`structural-context-probe`, `hidden-qualities-schema`,
      `analyze-split-cache-reclaim`, `clarify-model-trial`) merged, and
      **all of its learnings are already incorporated on `main`** (verified
      via `git log`/`git diff`): the two-pass split was rebuilt fresh (the
      branch predated the Pydantic migration, so it was never cherry-picked),
      the `context_probe` wording + typed `hidden_qualities` redefinition
      landed in the two ✓ schema branches, and the failure diagnosis +
      recruiting consultation are preserved in `evals/TUNING_LOG.md`
      (2026-05-26 entries, on `main`). With nothing on it still needed, the
      museum snapshot was deleted at the v1.0.4 cut; the commit stays
      reachable via reflog (~90 days) if ever required.
- [x] **~~Retire `/api/users/<username>/import-legacy` route~~** —
      ✅ resolved 2026-05-28. (a) Confirmed only consumer was
      `scripts/capture_screenshots.py`, which already calls
      `run_import` directly, not via the Flask route. (b) Removed
      `import_legacy_user` route from `app.py`; `onboarding/import_legacy.py`
      kept — `ingest_one_resume` is still used by the live
      `/corpus/ingest-resume` route. (c) Updated comment in
      `scripts/capture_screenshots.py` that referenced the deleted
      route. (d) No references in `walkthrough.md` or `README.md`.
      Removed `tests/test_import_legacy_route.py`; updated
      `docs/architecture.md` route reference to the live
      `ingest-resume` route. Branch `chore/pre-tag-cleanup-code`.
- [x] **~~Grep for TODO / FIXME / XXX comments~~** — ✅ resolved
      2026-05-28. Grepped `*.py`, `*.html`, `static/app.js` — zero
      hits in our own code. All TODOs/FIXMEs are in the vendored
      `static/vendor/paged.polyfill.js` (not our code). No action
      needed. Branch `chore/pre-tag-cleanup-code`.
- [x] **~~`lcars-*` CSS class rename → `cb-*`~~** — ✅ resolved
      2026-05-26. After surfacing during the B1 smoke, the user
      reviewed the actual scope (the visual redesign had already
      landed in commits `dc062e4` Phase 1 → `3a3f891` Phase 2; only
      class NAMES were leftover) and chose to close the rename out
      in v1.0.1. Mechanical `lcars-` → `cb-` substitution across
      [`static/style.css`](../../static/style.css) (73 refs →  0),
      [`static/app.js`](../../static/app.js) (19 → 0), and
      [`templates/index.html`](../../templates/index.html) (147 → 0).
      Zero behavior change; class shape preserved
      (`lcars-btn` → `cb-btn`, `lcars-bg-*` → `cb-bg-*`, etc.).
      Historical CHANGELOG entries still describe the original
      `lcars-*` names as they existed at the time — those are
      not rewritten.

---

## Forward-looking — v1.1 and v2

v1.1 + v2 items are tracked in
[`docs/PRODUCT_SHAPE.md §10`](../PRODUCT_SHAPE.md). Don't duplicate
the list here — the strategy doc is the single source of truth
for the deferred table.

Highlights pulled from §10:

- **v1.0.2:** R1 (split analyze: Haiku-fast + Sonnet-deep)
  **— ATTEMPTED + REVERTED in v1.0.1, deferred to v1.0.2.**
  Three iterations attempted on 2026-05-26 (`2026-05-26.1`
  naive split, `2026-05-26.2` atomic extraction + context_probe
  clarify fix); each degraded `clarification_quality` further
  vs. the pre-R1 baseline (pm-senior went 4.2 → 3.2 → 2.1,
  ds-junior 4.2 → 4.2 → 3.2). Performance was a real win
  (analyze p50 103s → ~72s, ~30% reduction) but the
  "no quality loss" floor was hard-binding. The R1.2 attempt
  is preserved on the `r1-attempted-2026-05-26` branch as the
  starting point for v1.0.2; see `evals/TUNING_LOG.md` entries
  `2026-05-24.4 → 2026-05-26.1` and `2026-05-26.1 → 2026-05-26.2`
  for the full diagnosis and recruiting-specialist consultation.
  **v1.0.2 plan:** use the `/prompt-tune` skill for smaller
  iteration cycles (cheaper than full eval runs each change) +
  the new `.claude-plugin/agents/headhunter.md` agent for
  sharper diagnosis between attempts.
- **v1.1:** field-filter chips for templates by role tag,
  master résumé operationalization, Docker.
- **v2:** `recommend_template` Haiku call per JD class (gated
  on outcome data + an `ApplicationOutcome` table).

### v1.0.2 — Live preview = downloaded résumé (true WYSIWYG) (new 2026-05-26)

**The ask** (user-stated, 2026-05-26): *"the live preview should
be on the selected corpus and json produced in the JD specific
resume corpus and title selections. the user should see a live
preview of what will be produced."*

**Current state after v1.0.1.** The Step 6 iframe (preview route
`/api/applications/<id>/preview`) is now properly bounded — it
only renders when `llm_recommendations` exists; otherwise it
returns a placeholder HTML explaining that curation is needed.
This stops the misleading 3-page un-curated render. But the
preview is still **corpus-rendered**, while the downloaded file
is **LLM-rendered**. They can diverge:

- **Preview path**: `build_json_resume_from_corpus()` reads
  Candidate + Experience + Bullet rows from the DB, filters by
  `composition_overrides` (pin/exclude/added) and
  `llm_recommendations`, renders through the persona's HTML
  template via `pdf_render.render_html_string`.
- **Download path**: `analyzer.generate()` produces markdown the
  LLM wrote (informed by the same corpus + curation, but free to
  reword each bullet for sharpness / JD relevance). The markdown
  lands in `#resumePreview` (editable), then
  `/api/download-edited` renders it to `.docx`.

So the LLM rewrite can change bullet wording, ordering within an
experience, and sometimes the summary phrasing — the preview
doesn't see any of that.

**Implementation options for v1.0.2** (pick one when planning):

1. **Render preview from the LLM markdown when one exists.** The
   most recent generate's `last_generated_resume` (in the
   context_set) is the canonical "what the LLM wrote." Convert
   that markdown → JSON Resume via a deterministic parser, then
   render through the same template pipeline. Pre-generate
   (mid-wizard, before the user has clicked Generate), the
   preview falls back to the corpus-based render OR the v1.0.1
   placeholder. **Pro:** matches download exactly once Generate
   has run. **Con:** needs a robust markdown → JSON Resume
   parser; resume markdown has a lot of shape variation (sections,
   subsections, dash-vs-bullet, multiple title formats).
2. **Make the LLM produce structured JSON Resume directly.**
   Change the generate() prompt to emit JSON Resume instead of
   markdown. The download path renders that JSON through the
   template (same as preview). **Pro:** preview = download is
   trivially byte-identical. **Con:** large prompt change,
   PROMPT_VERSION bump, full eval re-run, AND the editor (a
   contenteditable markdown surface) needs replacement — users
   can't hand-edit raw JSON; needs a structured-edit UI or a
   JSON Resume → markdown → JSON Resume round-trip with parser
   on each save.
3. **Dual-render approach.** Keep the markdown path for the
   editor (humans edit markdown well), but also store a parallel
   JSON Resume artifact updated whenever the markdown changes
   (debounced server-side). Preview reads the JSON Resume; the
   editor / download read the markdown. **Pro:** preserves the
   markdown editor; gives the preview ground truth. **Con:**
   keeps two artifacts in sync, which is exactly the kind of
   "two sources of truth" the v1 architecture was designed to
   avoid.

**Recommendation when planning v1.0.2:** option 1 (markdown →
JSON Resume parser) is the lowest-risk path that preserves the
markdown editor. The parser is bounded scope (markdown shape is
known) and doesn't touch the generate prompt or the editor UX.
Option 2 is the long-term cleanest answer but bigger surface.

**Eval implication:** none of the three options changes the LLM
output by itself; preview shape is a rendering concern. No new
rubric needed unless option 2 is chosen.

### v1.1 — User-driven bullet ordering on Compose stage (new 2026-05-26)

**The ask** (user-stated, 2026-05-26): bullets in the Compose
stage should be ordered intentionally, with most-valuable
bullets at the top of each experience and least-valuable at the
bottom. The user should be able to click-and-drag to reorder
these. Functional change + documentation to support.

**Current state.** Bullets are already sorted server-side in
[`app.py:get_application_composition`](../../app.py) by
`(not (pinned or recommended or added), -score, id)` —
pinned / LLM-recommended / drawer-added bullets sink to the top,
then by descending `score_corpus_bullet()` (deterministic fit
score against JD keywords + analysis essentials), then by id
for a stable tiebreaker. **There is no explicit user
ordering today**; pin/exclude/add are the only user
affordances over order.

**Why this matters beyond UI polish.** The order influences the
final document in two ways the user may not see directly:

1. **Recruiter scan order.** Surveys consistently report
   recruiters initial-scan résumés top-down in 6–8 seconds.
   The first bullet under each role does the load-bearing
   work of selling that role's relevance. (The literature on
   exact scan times is messy — see the R1 researcher's note
   that the half-remembered "TheLadders eye-tracking" study
   wasn't verifiable in our session. Treat the 6–8s as
   directionally true, not citation-quality.)
2. **LLM prompt order shapes the generated bullets.** The
   `_corpus_block` in [`analyzer.py`](../../analyzer.py)
   iterates experiences and bullets in the order they appear
   in the corpus payload. The Sonnet generate prompt
   processes bullets in that order — when it picks which
   bullets to keep in a constrained-length résumé, the
   earlier-listed ones are weighted by sequence position,
   not just by score. So a user reordering on Compose isn't
   cosmetic; it's a prompt-engineering knob the user holds.

**Design notes (my own thoughts, deferred to v1.1
implementation):**

1. **Persistence shape.** Extend `composition_overrides` in the
   context file with `bullet_order: {[experience_id]:
   [bullet_id, ...]}`. When present, this is authoritative
   over the server-computed sort. Absent ⇒ fall back to the
   current `(not pinned, -score, id)` ordering. Same context
   file already carries `pinned` / `excluded` / `added` — the
   ordering data lives in the same place for the same lifecycle.
2. **Render impact in `_stable_user_prefix`.** Honor
   `bullet_order` when building the `<career_corpus>` block so
   the user's reordering propagates into the generate prompt.
   This is the load-bearing piece — without it, drag-and-drop
   is cosmetic and the LLM's output won't reflect the user's
   intent.
3. **UI.** HTML5 native drag-and-drop on bullet cards. No new
   dependency needed — the rest of the codebase avoids
   framework dependencies. Add a small grab-handle ("≡")
   on each card; whole card is the drop zone. Cursor
   changes to `grab` on the handle and `grabbing` while
   dragging so the affordance is discoverable without a
   tooltip.
4. **In-interface instructions (user-stated 2026-05-26).**
   Docs alone are insufficient — users in the wizard won't
   reread the walkthrough mid-flow. Add a short
   instructional line at the top of each experience's
   bullet list:

   > *"Bullets are ranked by callback's AI by fit to this job.
   > Drag to reorder — your order shapes the final résumé."*

   Two load-bearing words there: "AI" (sets expectation that
   the default order is already intentional, not random or
   chronological) and "shapes" (telegraphs that the order
   isn't cosmetic — see point 2). Keep it ONE sentence;
   anything longer gets skipped. Pair with an info "(i)"
   icon that reveals the longer "why ordering matters"
   explanation on hover/click, for the curious user who
   wants depth without forcing depth on everyone.
5. **Accessibility floor.** Keyboard-controlled reordering is
   non-negotiable (deprecated `aria-grabbed` / `aria-dropeffect`
   should NOT be used). Add Up/Down buttons on each row with
   `aria-label="Move bullet up"` etc. — these are the
   keyboard path; drag-and-drop is the pointer path. Both
   write to the same persistence layer.
6. **Persistence trigger.** Debounced (~300ms) POST to
   `/api/applications/<id>/composition/order` (new route, or
   extend the existing PATCH) with the full new order
   per-experience. Optimistic UI update; reconcile on response.
7. **Reset affordance.** "Reset to AI ranking" button
   per experience (matches the in-interface instruction's
   "ranked by callback's AI" framing — consistent vocabulary
   beats clever vocabulary). Clears `bullet_order` and falls
   back to the server sort. Disabled state when no custom
   order exists, so the user sees they're already on the
   default.
8. **Edge case — bullets added later.** If the user added a
   bullet via the drawer AFTER setting an explicit order,
   default to slotting it at the END of the list with a
   subtle "newly added — drag to reposition" hint. Don't
   silently re-sort, which would erase the user's other
   choices.
9. **Documentation impact.** Update
   [`docs/walkthrough.md`](../walkthrough.md) Step 3 (Compose) to
   teach the WHY of ordering (recruiter scan + LLM
   sequence-position bias), not just the HOW (drag to
   reorder). The educational depth is the differentiator vs.
   "click and drag" docs that just describe the affordance.
10. **Eval implication.** This is a UX change with prompt-
    structure side effects (point 2). After implementation,
    run a manual eval against synthetic fixtures with one
    reordered ⇄ one default-order condition to confirm the
    generated résumé honors the reorder. Not a full
    `PROMPT_VERSION` bump — the prompt template doesn't
    change, only the order of the data fed to it — but worth
    capturing in `evals/TUNING_LOG.md` as a behavior shift.

---

## Risk register — verify before every release

These are evergreen — re-check on every release cut.

1. **PII in fixtures.** Any `evals/fixtures/real/` files crept
   into the main suite? Run `pytest -k 'real'` separately,
   verify they're gitignored.
2. **Anthropic model availability.** Sonnet 4.6 + Haiku 4.5 IDs
   in `analyzer.py` — confirm still GA when the release cuts.
3. **Cross-platform path handling.** `_safe_username` + `_within`
   are POSIX-friendly; verify on Windows with users that have
   spaces / unicode in their username.
4. **First-run experience.** Time-to-first-generation < 5
   minutes from a clean clone, following `docs/install.md`.
5. **Eval baseline.** Diff against
   `evals/results/baseline_v1.json`; surface deltas in CHANGELOG
   if any rubric moved more than 0.3 points.

---

## Archive — v1.0.0 release completed items

Below: what shipped during the v1.0.0 release arc. Kept for the
audit trail; do NOT re-run on subsequent releases.

### A — Codebase hygiene (DONE)

- **A.1 PII scrub** — completed in the α-phase scaffolding pass.
  `configs/`, `resumes/`, `output/`, `evals/fixtures/real/`,
  `logs/` are all gitignored. Synthetic fixtures + testuser are
  the only fixtures in tree.
- **A.2 Stray-code sweep** — completed in
  `6f56461 chore(hygiene): retire dead LCARS chrome`.
- **A.3 Semantic naming consistency** — completed in
  `24dbc71 chore(naming): JS convention audit`.
- **A.4 CSS cleanup** — completed in
  `41a0a35 chore(css): migrate 220 alias refs to canonical
  callback. tokens`.

### B — Visual polish (DONE except v1.0.1 items)

- Wizard rail, top bar, panels, buttons → token-bound in Phase 1.
- Compose step `.exp-card` / `.bullet` mockup-staged; wiring
  to live UI deferred to v1.0.1 (see "Should do" above).

### C — Documentation pass (DONE)

- **C.1** README rewrite + `docs/install.md` — landed in
  `319ae1b` (initial) and `67ae017` (substantial body rewrite).
- **C.2** CLAUDE.md + `docs/architecture.md` — landed in
  `9d36761`. Four Mermaid diagrams in `docs/diagrams/`.
- **C.3** `docs/onboarding.html` — deferred per PRODUCT_SHAPE
  §10 (README + `docs/install.md` cover the same ground).
- **C.4** `SECURITY.md` threat model — refreshed in
  `e880451`.
- **C.5** `CHANGELOG.md` + version cut — `[1.0.0] —
  2026-05-25` entry written; version bumped to `1.0.0` in
  `075d830`.
- **C.6** Project-meta files — `LICENSE`, `CONTRIBUTING.md`,
  `CODE_OF_CONDUCT.md`, issue/PR templates, `.editorconfig` all
  shipped. `FUNDING.yml`, `Dockerfile` deferred to v1.1.

### D — Risk register (CLEARED)

D.1–D.5 all verified before the v1.0.0 tag.

---

## When to revisit this file

After every release tag:

1. Move "Active release" items that shipped → "Archive — v1.X.Y
   release completed items" subsection.
2. Bump the "Active release" header to the next planned version.
3. Pull next release's items from PRODUCT_SHAPE §10 (move them
   in, don't duplicate them).
4. Re-check the Risk register evergreen items.

If a release cut surfaces a new "Forward-looking" item that
isn't in PRODUCT_SHAPE §10, add it there first, then reference
here.
