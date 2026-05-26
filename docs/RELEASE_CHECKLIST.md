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
> [`docs/PRODUCT_SHAPE.md`](PRODUCT_SHAPE.md) §10 for the full
> deferred-items table that drives the v1.0.1 / v1.1 / v2 ladder.

---

## Active release — v1.0.1

The v1.0.0 release landed in commit `075d830` (with subsequent
template curation, paged.js pagination, and docs reworks landing
on the same branch before tag). v1.0.1 is the first follow-up
release.

### Must do before tag (shipping blockers)

- [ ] **Manual fresh-clone verification** — clone in a clean
      directory; run `pip install -e .` + `python -m playwright
      install chromium` + `python app.py`; complete one
      application end-to-end. Time-to-first-generation < 5
      minutes (D.4 below).
- [ ] **Eval baseline check** — run
      `python evals/runner.py --suite synthetic --subset smoke`;
      confirm no regression against
      `evals/results/baseline_v1.json`.
- [ ] **Quality gate** — `ruff check .` + `mypy .` + `pytest`
      all clean.
- [ ] **`pyproject.toml` version bump** — `1.0.0` → `1.0.1`
      in the release commit.
- [ ] **`CHANGELOG.md` flip** — rename `[Unreleased]` →
      `[1.0.1] — <date>`; add new empty `[Unreleased]` block.

### Should do (v1.0.1 polish; document if skipped)

- [ ] **Step 6 (Output) redesign** — surfaced during the v1.0.0
      review: cut the obsolete tabs + raw/rendered toggle
      (replaced by paged.js preview); preview at the top of
      the step; edit-raw via modal; Changes → info-icon modal;
      cover letter → single "+ Generate" button until generated.
- [ ] **BACK / Continue spacing polish on Compose** — listed
      in PRODUCT_SHAPE §10 as deferred from v1.0.0.
- [ ] **`docs/install.md` updated** for any platform-specific
      lessons learned during v1.0.0 hands-on testing.
- [ ] **Accessibility scan of all user-facing documentation** —
      surfaced during the screenshot-capture pass (2026-05-26).
      Run an a11y audit across the user-facing doc set
      ([`README.md`](../README.md),
      [`docs/install.md`](install.md),
      [`docs/walkthrough.md`](walkthrough.md),
      [`docs/walkthrough_example.md`](walkthrough_example.md),
      [`vision.md`](../vision.md)) and the screenshots that just
      landed in [`docs/screenshots/`](screenshots/). Specifically
      check:
      - **Alt text on every image** — the manifest at
        [`docs/ux/screenshot_capture.md`](ux/screenshot_capture.md)
        has drafts; verify they get applied during the markdown
        insertion pass and that none describe the image only
        cosmetically ("a screenshot") instead of substantively.
      - **Mermaid diagrams** — the two flow diagrams in
        `walkthrough.md` render as SVG that most screen readers
        can't traverse meaningfully. Add a prose summary
        immediately after each diagram (the existing "Read this
        top-down: …" line is already this pattern; check whether
        the user-flow diagram needs an equivalent paragraph).
      - **Heading hierarchy** — no skipped levels (H1 → H3 with
        no H2 between).
      - **Link text** — no "click here" / "see this" links;
        link text should describe its destination ("see
        [Cost guidance](../README.md#cost)" rather than "see
        [here](../README.md#cost)").
      - **Color-only meaning in diagrams** — the four-color
        classDef vocabulary (gate/llm/det/opt) carries semantic
        load; verify the per-diagram legend prose makes that
        meaning available without color.
      - **Tables** — verify column headers are real `<th>` (the
        markdown `| Header |` syntax already produces them; just
        a sanity check after any handwritten HTML tables).
      Tooling: axe DevTools or WAVE for the rendered HTML
      preview; a manual VoiceOver / NVDA sweep is the gold
      standard but a30-min axe pass surfaces the obvious
      issues. **Defer the actual scan** to a focused later pass;
      this entry just tracks the obligation.
- [x] **~~Doc-vs-UI label drift on the corpus import button~~** —
      ✅ resolved 2026-05-26. Button renamed
      `+ Drop résumé (AI extract)` → `+ Import résumé` (cleaner
      action verb than "Drop" which conflated drag-and-drop with
      the action itself; the parenthetical leaked the AI-extract
      implementation detail into a button label). Live docs
      ([`docs/walkthrough.md`](walkthrough.md),
      [`docs/install.md`](install.md),
      [`docs/ux/screenshot_capture.md`](ux/screenshot_capture.md))
      synced to the new label. The audit at
      [`docs/ux/onboarding_audit_2026-05-25.md`](ux/onboarding_audit_2026-05-25.md)
      is left as the historical record (the audit accurately
      reports the doc/UI mismatch as it existed on 2026-05-25).
      The internal API route `/api/users/<user>/import-legacy`
      keeps its name — route rename is a separate cleanup, v1.1.
- [ ] **Bullet-dedup gap in corpus re-import** — surfaced during
      the screenshot-capture pass (2026-05-26). Re-running
      [`onboarding/import_legacy.py`](../onboarding/import_legacy.py)
      with `with_llm=True` against the same source `.docx` correctly
      dedupes experiences (by `(company, start_date)`) but creates
      a fresh batch of bullets each time, so each re-import
      doubles the bullet count for already-imported experiences
      (observed: a 22-bullet first import grew to 44 bullets on the
      second import of the same file). The current behavior is
      documented as intentional in
      [`onboarding/import_legacy.py:387-388`](../onboarding/import_legacy.py)
      ("Bullets are NOT deduped — different resume files often
      have different phrasings"), but the same-file case
      shouldn't trigger that path. Add a `(experience_id,
      normalized_text)` dedup at the same-file boundary.
- [x] **~~Wizard rail step buttons don't re-enable after prior step
      completes~~** — ✅ resolved 2026-05-26. Added a
      `_wizardRender()` call in `runAnalysis()`'s success path
      (after `lastContextPath` is set), so the rail picks up
      step 2 as `_wizardReachable` immediately. `runGeneration()`
      was already calling `_wizardAdvanceTo(6)` (which includes
      a `_wizardRender`), so the step-6 side of the bug was
      already covered — the bug only existed on the analyze →
      step 2 transition.
      [`scripts/capture_screenshots.py`](../scripts/capture_screenshots.py)
      still navigates forward via the in-flow Continue buttons;
      that's fine and matches the real-user happy path, but rail
      clicks would now work too.
- [ ] **Playwright UX clickthrough regression suite** — surfaced
      during the screenshot-capture pass (2026-05-26). The
      screenshot script at
      [`scripts/capture_screenshots.py`](../scripts/capture_screenshots.py)
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
        [`scripts/capture_screenshots.py`](../scripts/capture_screenshots.py).
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
      [`CONTRIBUTING.md`](../CONTRIBUTING.md) as the standard
      pre-PR ritual. **Defer if time-bound:** land the harness
      + `conftest.py` + one happy-path-stubbed test in v1.0.1;
      backfill the `regression/` + `error_handling/` +
      `flows/` tests across v1.0.1 and v1.1 as the screenshot-
      pass bugs get fixed (each fix lands with its regression
      test). **Prereq:** the screenshot script itself must
      stabilize first (currently being debugged) — the POMs
      lift directly from its navigation logic, so a moving
      script means churning POMs.
- [ ] **Corpus tab render-after-refresh bug** — surfaced during
      the screenshot-capture pass (2026-05-26).
      [`static/app.js:1795`](../static/app.js) `refreshCorpus()`
      fetches `/api/users/<user>/experiences` successfully and
      populates `_corpusExperiences` (observed length 3 against a
      DB that had 3 experiences for the demo user), then calls
      [`_renderCorpusList()`](../static/app.js) at
      [`static/app.js:2000`](../static/app.js) — but the DOM
      doesn't end up with any `.corpus-card` elements. The list
      element's `innerHTML.length` is ~65 chars (placeholder-sized)
      even though the JS state shows 3 experiences. Either
      `_renderCorpusList()` is throwing silently inside its
      `forEach`, or some later code path is clearing the list
      back to placeholder state. Repro:
      1. Hit `/api/users/<user>/import-legacy` with `with_llm=True`
         against a user with an existing résumé in `resumes/<user>/`.
      2. Open the Career Corpus tab in a fresh browser session.
      3. Observe: the UI shows the empty-corpus hint despite the
         DB having experiences (`GET /api/users/<user>/experiences`
         returns them).
      Workaround currently used by [`scripts/capture_screenshots.py`](../scripts/capture_screenshots.py):
      `page.reload()` + re-select user clears the bad state.
      Real fix: instrument `_renderCorpusList` / `_renderCorpusSummary`
      with a try/catch + console.error so the silent failure becomes
      visible, then chase the root cause.

### Nice to have (defer to v1.1 if time-bound)

- [ ] **Visual assets** — screenshots, demo GIF, onboarding HTML
      page. PRODUCT_SHAPE §10 defers this to v1.0.1; if the
      planned UI redesign hasn't started, ship visual assets
      against the current UI rather than wait.
- [ ] **R2 — stream `analyze()` output** (PERF_ANALYZE.md, $0,
      perceived latency 90s → 10-15s). Owns its own commit
      and eval cycle.

---

## Forward-looking — v1.1 and v2

v1.1 + v2 items are tracked in
[`docs/PRODUCT_SHAPE.md §10`](PRODUCT_SHAPE.md). Don't duplicate
the list here — the strategy doc is the single source of truth
for the deferred table.

Highlights pulled from §10:

- **v1.1:** R1 (split analyze: Haiku-fast + Sonnet-deep),
  field-filter chips for templates by role tag, master résumé
  operationalization, Docker.
- **v2:** `recommend_template` Haiku call per JD class (gated
  on outcome data + an `ApplicationOutcome` table).

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
