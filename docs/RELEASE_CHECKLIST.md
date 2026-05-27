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
- [ ] **Quality gate** — `ruff check .` + `mypy .` + `pytest`
      all clean.
- [ ] **`pyproject.toml` version bump** — `1.0.0` → `1.0.1`
      in the release commit.
- [ ] **`CHANGELOG.md` flip** — rename `[Unreleased]` →
      `[1.0.1] — <date>`; add new empty `[Unreleased]` block.
- [ ] **Push to GitHub + verify the `https://github.com/amodal1/callback`
      URL resolves** — the repo is still local-only (no `origin`
      remote configured). Multiple shipping artefacts already
      reference the GitHub URL as if it exists:
      - [`pyproject.toml:56-59`](../pyproject.toml) — Homepage,
        Repository, Issues, Changelog package metadata.
      - [`README.md:34`](../README.md) — quick-install
        `git clone` line.
      - [`docs/install.md:45, 90, 143`](install.md) — Windows /
        macOS / Linux clone instructions.
      Anyone following those docs against the unpublished repo
      hits a 404. Action before tag: create the GitHub repo
      (public, name `callback`, under `amodal1`), `git remote add
      origin git@github.com:amodal1/callback.git`, push
      `feat/v1-unified-corpus` and `main`, push the v1.0.1 tag,
      then spot-check that all four pyproject URLs resolve and
      that `git clone https://github.com/amodal1/callback` works
      from a separate machine (or fresh clone path) without
      auth prompts.

### Should do (v1.0.1 polish; document if skipped)

- [ ] **Step 6 (Output) redesign** — surfaced during the v1.0.0
      review: cut the obsolete tabs + raw/rendered toggle
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
- [x] **~~Bullet-dedup gap in corpus re-import~~** — ✅ resolved
      2026-05-26. Changed `_merge_into_existing_experience` in
      [`onboarding/import_legacy.py`](../onboarding/import_legacy.py)
      to dedup on **normalized bullet text** instead of
      `(source, text)`. The old key missed same-file re-imports
      because the source flips from `primary:<file>` to
      `supplemental:<file>` on the merge path, so the same text
      under two different sources slipped through as a "new"
      bullet. The new key matches regardless of source; different
      phrasings from different files still survive (they have
      different normalized text). Test
      `test_merge_dedupes_identical_bullet_text_across_sources`
      in [`tests/test_onboarding_import_legacy.py`](../tests/test_onboarding_import_legacy.py)
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
- [ ] **Corpus tab render-after-refresh bug** *(instrumented
      2026-05-26; root cause TBD)* — surfaced during
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
      **Status:** instrumentation landed 2026-05-26 —
      `_renderCorpusList` is now wrapped in try/catch with an
      element-presence guard, and `_renderCorpusSummary` calls
      are guarded per-iteration so a single bad row doesn't
      blank the whole list. Any future trigger will surface the
      culprit via `console.error` instead of failing silently.
      Root-cause chase still open: needs a repro that exhibits
      the bug with DevTools open to read the error. Most likely
      candidates per static read of the code: a missing DOM
      element (`corpusToolbar` / `corpusCount`) at the moment
      `_renderCorpusList` runs, or a property access on `exp`
      that the API doesn't always provide.
- [ ] **Corpus tab: 5xx on first-load API calls** — surfaced
      2026-05-26 during a dev-console capture of the Corpus tab
      load. Distinct from the render-after-refresh bug above
      (that one is a 200 OK that leaves the DOM empty; this one
      is a real 5xx that hits the `!res.ok` branch at
      [`static/app.js:1834`](../static/app.js) and shows
      "Failed to load corpus."), but they likely share a root
      cause — both are "first-load Corpus tab from a fresh
      session" stories. The `refreshCorpus()` flow at
      [`static/app.js:1801`](../static/app.js) calls four
      endpoints in sequence — all four returned 500:
      `GET /api/users/<user>/experiences`
      ([`app.py:2341`](../app.py)),
      `GET /api/users/<user>/summaries`
      ([`app.py:2718`](../app.py)),
      `GET /api/users/<user>/personas`
      ([`app.py:1690`](../app.py)), and
      `GET /api/users/<user>/applications`. A page reload via
      the corpus reload link recovers and subsequent loads
      succeed. Repro:
      1. Restart `python app.py`.
      2. Open a fresh browser tab to `http://localhost:5000`.
      3. Select an existing user from the dropdown.
      4. Click the Career Corpus tab.
      5. Observe in dev-console: four 500 responses; UI shows
         "Failed to load corpus."
      6. Click the corpus reload link → all four routes return
         200 and the list renders.
      Fix probably starts by adding server-side exception
      logging on those four route handlers so the 5xx's
      traceback is visible in the Flask log; current behavior
      is a silent 500 with no Python-side stack trace. Once
      the underlying exception is visible, this and the
      render-after-refresh bug above can probably be closed
      together.
- [x] **~~Judge JSON parse failures mis-categorized as `status=ok`~~** —
      ✅ resolved 2026-05-26.
      [`evals/runner.py:289`](../evals/runner.py) now returns
      `{"score": 0, "reasons": [...], "raw": raw, "status": "judge_error"}`
      so the existing `judge_error` path in `_detect_regression` /
      summary logic skips these records correctly. New test
      `test_unparseable_json_marks_status_judge_error` in
      [`tests/test_eval_runner.py`](../tests/test_eval_runner.py)
      pins the behavior; all 25 tests in that file pass. The
      false-positive WARN observed in
      [`evals/results/20260526_170400Z.jsonl`](../evals/results/20260526_170400Z.jsonl)
      (`data-scientist-junior × grounding`, -4.8 delta) won't
      recur — re-running the smoke pass should produce a clean
      result.
- [ ] **Re-baseline eval scores for v1.0.1** —
      [`evals/results/baseline_v1.json`](../evals/results/baseline_v1.json)
      was sourced from
      [`evals/results/20260513_221926Z.jsonl`](../evals/results/20260513_221926Z.jsonl)
      on `prompt_version=2026-05-12.1` (recorded 2026-05-25), but
      [`analyzer.py`](../analyzer.py)'s current `PROMPT_VERSION`
      is `2026-05-24.4` — three prompt revisions shipped with
      v1.0.0 between the baseline source-run and tag. The
      baseline file's own `notes` field already calls this out
      ("a re-baseline is recommended early in v1.0.1 once the
      streaming/split-analyze changes from PERF_ANALYZE.md
      land"). The smoke pass on 2026-05-26 showed the two
      successfully-graded fixtures essentially unchanged
      (`pm-senior`: 4.8 = 4.8; `sre-mid-level`: 4.8 vs 4.7,
      Δ=+0.1), so the drift appears benign — but the "Eval
      baseline check" Must-do at
      [`docs/RELEASE_CHECKLIST.md:32-35`](RELEASE_CHECKLIST.md)
      is comparing against scores no longer apples-to-apples
      with shipping code. Action: once the
      [`evals/runner.py:289`](../evals/runner.py) judge-error
      fix lands AND the v1.0.1 prompt landscape is final (R2
      streaming work either in or explicitly deferred), run
      the full synthetic suite (`python evals/runner.py --suite
      synthetic`, ~$1.50, all five rubrics × three fixtures)
      and replace `baseline_v1.json` with a v1.0.1 baseline.
      Document the cut as a dated entry in
      [`evals/TUNING_LOG.md`](../evals/TUNING_LOG.md) per its
      four-question structure. **Defer:** v1.0.1 CAN ship
      against `baseline_v1` (smoke noise from the judge-error
      bug aside, the underlying scores are stable); the
      re-baseline is hygiene, not a blocker — slip to early
      v1.1 if v1.0.1 ships fast.
- [ ] **Walkthrough documentation pass — three fixes** —
      surfaced 2026-05-26 during a user review of
      [`docs/walkthrough.md`](walkthrough.md).
      1. **Add Corpus → Application transition.** Setup section
         (lines ~154-182) tells the reader to use the Career
         Corpus tab for résumé import, then jumps straight to
         `## Step 1 — Job + Analyze` with no instruction to
         navigate back to the Application tab + click Step 1 in
         the wizard rail. A sequential reader is left on the
         Corpus tab when the doc says "paste the JD." Fix: one
         short paragraph between Setup and Step 1, e.g. *"Once
         the corpus is populated, click the **Application** tab
         in the top bar and select **Step 1 — Job + Analyze**
         in the wizard rail."*
      2. **Re-capture `walkthrough_step2_clarify-questions.png`
         scrolled to show the actual questions.** The current
         capture at
         [`scripts/capture_screenshots.py:285-315`](../scripts/capture_screenshots.py)
         waits for questions to render and types a partial
         answer, then snapshots at 1440×900 without scrolling.
         Panel header + "Continue" + clarify-instructions push
         the exemplar question content past the fold, so the
         screenshot shows framing instead of the questions
         themselves. Fix: one line before the `cap()` call —
         `page.locator("#clarifyQuestions").scroll_into_view_if_needed();
         wait_quiet(page, 300)`. Then re-run Step 2 capture (or
         the whole script; the rest of the screenshots are
         current and stable).
      3. **Confirm `docs/walkthrough_example.md` is intentional,
         not a leftover.** Its purpose statement at
         [`docs/walkthrough_example.md:1-14`](walkthrough_example.md)
         establishes it as the concrete Priya companion to the
         abstract walkthrough — same synthetic candidate used by
         [`scripts/capture_screenshots.py`](../scripts/capture_screenshots.py)
         `write_priya_docx()`. No file change needed; this
         sub-bullet exists so a future skim doesn't mistake the
         file for orphaned scaffolding.
- [ ] **CSP `unsafe-eval` violation on script execution** —
      surfaced 2026-05-26 in the browser dev-console while
      loading the Corpus tab. Some code path calls a
      string-evaluating JavaScript primitive — `eval`, the
      dynamic-Function constructor, or string-form `setTimeout`
      / `setInterval` — and is being blocked by the site's CSP
      `script-src` directive. Likely a vendor library (paged.js
      is a candidate — page-rendering libraries sometimes
      synthesize CSS / JS at runtime via dynamic-string code
      paths) but could be our code too. Action: (1) grep
      `static/` and any bundled vendor directories for the
      blocked primitives; (2) decide whether to narrow the
      offending callsite or relax the CSP with `unsafe-eval`.
      **Prefer narrowing the callsite** — `unsafe-eval`
      reopens inline-script-injection risk per
      [`SECURITY.md`](../SECURITY.md)'s threat model. If the
      offender is a vendor lib with no easy workaround,
      document the trade-off as an accepted-risk entry in
      `SECURITY.md` rather than relax the CSP silently.
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
- [ ] **Form fields without `id` or `name` attribute** —
      surfaced 2026-05-26 in the dev-console. Chrome flagged
      seven form-field elements ("violating nodes") with neither
      an `id` nor a `name` attribute, which prevents
      browser-autofill and is a soft a11y signal. Distinct from
      the "Accessibility scan of all user-facing documentation"
      entry above — that one covers `docs/screenshots/` alt-text
      + Mermaid prose summaries + heading hierarchy; this one is
      about live form inputs in
      [`templates/index.html`](../templates/index.html) and any
      partials. Fix: find the seven offending elements via
      Chrome's `Inspect → Issues → "A form field element should
      have an id or name attribute"` view, add stable `id`s, and
      add matching `<label for="…">` elements where missing.
      Cheap; bundle with the doc-side a11y scan if that one
      lands first.
- [ ] **Two `POST /api/analyze 409`s observed during Corpus-tab
      session (investigation needed)** — surfaced 2026-05-26 in
      the dev-console. `POST /api/analyze` returned 409 twice
      during a session whose other primary activity was loading
      the Corpus tab. The 409 path is used elsewhere in the
      codebase as an onboarding-needed / reconcile signal (see
      `_needsOnboarding(res, data)` at
      [`static/app.js:1818`](../static/app.js)), so 409 may be
      expected when analyze is called against an un-onboarded
      user — but it shouldn't fire unless the user actually
      triggered analyze. User confirmed they don't recall
      whether they were mid-application or fresh-session when
      the 409s fired, so this is filed as "investigation
      needed" rather than asserted-bug. Investigation steps:
      (1) grep `app.py` for the `/api/analyze` route and
      enumerate all branches returning 409; (2) check whether
      anything on the Corpus tab can implicitly call analyze
      (e.g., a pre-warming side effect, an iteration-resume on
      tab switch); (3) add request-context logging on the
      analyze route's 409 paths so the next observed 409
      carries the reason in the Flask log. Outcome: either
      close as "expected, document the triggering UI path" or
      file a follow-up bug if the call is truly unsolicited.
      **Aside on console noise:** the bulk of the dev-console
      output during this capture was
      `content.js:360 The kernel 'X' for backend 'webgl|cpu'
      is already registered` from a browser extension's content
      script (TensorFlow.js classifier running in `content.js`
      + `classifier.js`) — NOT our code. Do not chase those
      warnings; they originate outside the app.

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

- [ ] **Cover-letter download honors the chosen output format**
      (user-surfaced 2026-05-26 round-7 smoke). Today
      `downloadCoverLetter()` passes `original_format: lastResumeFormat`
      to `/api/download-edited`, but `generator.generate_cover_letter`
      hardcodes `.docx` (see [`generator.py:194-201`](../generator.py#L194)
      with comment *"Generate the cover letter as .docx (always — no
      template needed)"*). The PDF and Markdown format buttons appear
      to apply to both résumé and cover letter, but only the résumé
      actually honors them. Two paths: (a) update
      `generate_cover_letter` to accept output_format + render markdown
      via the same path as the résumé (md → docx via template, or md
      → pdf via paged.js). (b) Surface the limitation in the UI
      explicitly: a small "Cover letter is .docx-only in v1.0.1; PDF
      + Markdown coming in v1.0.2" hint on the Cover letter tab. Path
      (b) is the v1.0.1 fix; (a) is v1.0.2 alongside the B3 persona
      styling work.
- [ ] **Prior-application click resumes the wizard at that
      application's last state** (user-surfaced 2026-05-26 during
      round-6 smoke). Today, clicking a card in the "Prior
      applications" panel of Step 1 shows a one-line toast with
      title/status/iter-count and nothing else — that's an
      acknowledged placeholder per the comment at
      [`static/app.js:3404-3406`](../static/app.js#L3404):
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

- [ ] **Visual assets** — screenshots, demo GIF, onboarding HTML
      page. PRODUCT_SHAPE §10 defers this to v1.0.1; if the
      planned UI redesign hasn't started, ship visual assets
      against the current UI rather than wait.
- [ ] **R2 — stream `analyze()` output** (PERF_ANALYZE.md, $0,
      perceived latency 90s → 10-15s). Owns its own commit
      and eval cycle.

### Pre-tag cleanup + review stage (do last, before v1.0.1 tag)

User-stated 2026-05-26: cull temporary exploration artifacts so
they don't continue to track. Run this as a focused stage AFTER
B1–B3 land and AFTER the fresh-clone verification, immediately
before the version-bump commit.

- [ ] **Remove `docs/mockups/`** — five HTML files
      ([`a-step-zones.html`](mockups/a-step-zones.html),
      [`b-brand-accent.html`](mockups/b-brand-accent.html),
      [`b-refined.html`](mockups/b-refined.html),
      [`b-refined-v2.html`](mockups/b-refined-v2.html),
      [`c-hybrid.html`](mockups/c-hybrid.html)) created during the
      visual-IA exploration on `feat/release-visual-ia`. They
      reference a fixture user ("Casey Rivera") in a dropdown that
      doesn't match any live UI surface, and they aren't linked
      from any user-facing doc. Confirm none of the live app
      consumes them (`grep -r "docs/mockups"`) before deleting.
- [ ] **Audit `docs/archive/`** — already-archived material. If
      anything in here predates v1.0.0 and is no longer load-
      bearing reference material, move it to a separate `archive/`
      branch or delete outright.
- [ ] **Strip dead-link references from CHANGELOG history** —
      pre-v1.0.0 changelog entries link to files that may have
      moved or been deleted (the dashboard refactors moved files
      around in May 2026). Run `grep -oP '\[.+?\]\(.+?\)' CHANGELOG.md`,
      verify each link resolves, mark broken ones with `(removed
      <date>)` rather than deleting the entry (preserves history).
- [ ] **`scripts/perf_baseline.py`** — useful for v1.0.2 R1
      iteration cycles; keep it, but document its purpose in the
      [`docs/architecture.md`](architecture.md) module map so a
      future reader knows it's a release-cycle tool, not part of
      the runtime.
- [ ] **`r1-attempted-2026-05-26` branch** — keep through v1.0.2;
      it's the starting point for that release's R1 rework. After
      v1.0.2 ships (R1 successful or formally abandoned), delete
      this branch. Tracked here so it doesn't drift.
- [ ] **Grep for TODO / FIXME / XXX comments added during v1.0.1
      development** — `grep -rn 'TODO\|FIXME\|XXX' --include='*.py'
      --include='*.js' --include='*.html'`. Either close them in
      this release or convert to RELEASE_CHECKLIST entries for
      v1.0.2. Don't ship the tag with floating reminders.
- [x] **~~`lcars-*` CSS class rename → `cb-*`~~** — ✅ resolved
      2026-05-26. After surfacing during the B1 smoke, the user
      reviewed the actual scope (the visual redesign had already
      landed in commits `dc062e4` Phase 1 → `3a3f891` Phase 2; only
      class NAMES were leftover) and chose to close the rename out
      in v1.0.1. Mechanical `lcars-` → `cb-` substitution across
      [`static/style.css`](../static/style.css) (73 refs →  0),
      [`static/app.js`](../static/app.js) (19 → 0), and
      [`templates/index.html`](../templates/index.html) (147 → 0).
      Zero behavior change; class shape preserved
      (`lcars-btn` → `cb-btn`, `lcars-bg-*` → `cb-bg-*`, etc.).
      Historical CHANGELOG entries still describe the original
      `lcars-*` names as they existed at the time — those are
      not rewritten.

---

## Forward-looking — v1.1 and v2

v1.1 + v2 items are tracked in
[`docs/PRODUCT_SHAPE.md §10`](PRODUCT_SHAPE.md). Don't duplicate
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
[`app.py:get_application_composition`](../app.py) by
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
   `_corpus_block` in [`analyzer.py`](../analyzer.py)
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
   [`docs/walkthrough.md`](walkthrough.md) Step 3 (Compose) to
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
