---
status: review-artifact
evidence_sha: c6e0437
graduation: none
---

# Findings - Product experience & accessibility

## Domain verdict

The a11y mechanisms are real and well-built: a disciplined _announce()
live-region, keyboard bullet-reorder pinned as "the a11y floor", focus-trap +
Escape + focus-return in modals/drawers, a vendored dependency-free axe gate,
and a mathematically-verified WCAG-AA contrast fix. The charter's load-bearing
gap is the phrase "in CI, free forever" (E-2): every one of these checks runs
only on the maintainer's laptop - CI runs ruff/mypy/pytest and never installs
Chromium, so the UX/a11y tier silently skips. The taxonomy is also only partly
machine-checked (axe = names/labels + contrast; tab-order, reflow/zoom,
back/history, live-region announcements have no dedicated check), there is no
ACCESSIBILITY.md the charter requires, the cold no-API-key user is error-dumped
mid-analyze rather than guided, and the S-3/M-2 explainability surfaces (lay
metrics legend, corpus-first onboarding) ride unbuilt Sprints 6.4/6.5. None of
the working mechanisms are charter-blocking; the CI gap, the absent status page,
and the keyless-onboarding dump are the P1 items before the public tag.

---

## Register findings

### F-expa11y-01 - A11y/UX taxonomy is local-only; CI never runs it
- disposition: FIX
- leverage: P1
- charter-trace: E-2 ("machine-checked in CI, free forever"), A-2
- question-refs: QB-exp-a11y-01, QB-exp-a11y-04 (CI half)
- evidence: .github/workflows/ci.yml@c6e0437 runs only ruff check . / mypy . /
  pytest (the quality job) and a label-gated eval-smoke job; it is the only
  workflow file (git ls-tree c6e0437 .github/workflows/ -> ci.yml alone). No
  Chromium / Playwright / "pytest -m ux" step exists (git grep -i
  chromium/playwright over .github/ -> no hits). tests/ux/conftest.py:80-89@c6e0437
  pytest.skips the whole UX tier when the Chromium binary is absent - which it
  always is on the CI runner. So the vendored axe gate and every UX regression
  test never execute unattended.
- finding: The charter's E-2 line item is precisely "machine-checked in CI, free
  forever" - not "runnable locally." At the pin the entire a11y/UX tier (axe
  smoke + 16 UX regression tests) is local-only and skips on the CI runner by
  construction. This confirms product-map DEBUFF-1 ("gates that silently skip").
  The mechanism gap is one CI job that installs Chromium and runs "pytest -m ux";
  until it exists, "free forever in CI" is not yet true and any a11y regression
  lands undetected.
- coordinate: (none - predates Sprint 6.x; a standalone CI change)

### F-expa11y-02 - No ACCESSIBILITY.md honest-status page exists
- disposition: FIX
- leverage: P1
- charter-trace: E-2 ("ACCESSIBILITY.md as an honest status page"), P-3
- question-refs: (E-2 taxonomy; adjacent to QB-exp-a11y-04)
- evidence: git ls-tree -r c6e0437 --name-only piped to grep -i accessib -> no
  match anywhere in the tree (no ACCESSIBILITY.md, no docs/ACCESSIBILITY.md).
- finding: E-2 names ACCESSIBILITY.md as a required artifact: "an honest status
  page; screen-reader feedback treated as priority bugs; no conformance claim, no
  tag gate." It is absent at the pin. This is the charter-sanctioned vehicle for
  stating what is and isn't checked (which, given F-expa11y-01 and F-expa11y-03,
  is itself non-trivial) without making a conformance claim. Its absence means
  there is no honest public surface describing the real a11y posture - the exact
  "mechanisms and effort, not absolutes" register C-0 wants.
- coordinate: Sprint 6.5 (in-app education sweep is the natural home)

### F-expa11y-03 - axe gate covers names/labels+contrast only; rest of taxonomy unchecked
- disposition: FIX
- leverage: P1
- charter-trace: E-2 (enumerated taxonomy)
- question-refs: QB-exp-a11y-04
- evidence: tests/ux/a11y/ contains exactly one test file (test_axe_smoke.py)
  plus the vendored engine; no tab-order, reflow/zoom, keyboard-completeness,
  live-region, or back/history test exists (git ls-tree -r c6e0437 tests/ux/a11y/).
  The test gates serious/critical only, excludes iframes, and scans landing +
  new-user form + Tailor Step-1 + Corpus/Memory/Personas + Settings drawer +
  Compose + Template + 5 dashboard tabs (the four test_axe_* functions, lines
  110/129/165/194). NOT scanned: wizard Step-2 (clarify), Step-5/6
  (generate/download), the edit modal, the diagnostics modal.
- finding: axe enforces the names/labels line (and, via the contrast retune, the
  contrast line) on a first-cut surface set - a genuine start. But E-2 enumerates
  nine+ taxonomy lines (tab order, keyboard completeness, no traps,
  Escape/focus-return, focus on dynamic content, live-region at every async
  completion, back/history, reflow/zoom, contrast); most have no dedicated machine
  check, and several reachable surfaces are unscanned. The gap is
  scope-of-coverage, not a defect in what exists. Pairs with F-expa11y-01: even
  the covered lines don't run in CI.
- coordinate: Sprint 6.4/6.5 (new surfaces should be scanned as they land)

### F-expa11y-04 - Cold no-API-key user is error-dumped mid-analyze, not guided
- disposition: FIX
- leverage: P1
- charter-trace: A-1 (API-key step = acknowledged friction), M-2 (first-run)
- question-refs: QB-exp-a11y-05
- evidence: _get_client() (app.py:87-95@c6e0437) reads ANTHROPIC_API_KEY then
  .api_key, with no preflight and no key-check route (git grep over app.py finds
  no /health or key-validation route). Dynamically verified in a sandbox:
  anthropic.Anthropic(api_key empty-string) (anthropic 0.88.0) constructs without
  raising - the failure is deferred to call time. The new-user form
  (templates/index.html:79-108) collects username/name/email/phone/LinkedIn/
  website but no API key. A keyless 401 (AuthenticationError) is not in the
  streaming analyze handler's named excepts (it catches APIConnectionError +
  LLMResponseError), so it falls to the bare except Exception (app.py:~673) -> SSE
  error "Internal error during analysis." / HTTP 500.
- finding: A first-time user can complete onboarding, ingest a resume, paste a JD,
  and click Analyze before discovering the key is missing - and the resulting
  message ("Internal error during analysis.") names neither the key nor a remedy.
  A-1 explicitly flags API-key setup as the audience's known friction; nothing in
  the UI mitigates it. The mechanism gap is a cheap preflight (a guarded
  key-presence check surfaced as guided setup before the first paid call). This
  bears directly on the M-2 "fresh-clone first run" experience.
- coordinate: Sprint 6.4 (onboarding IA) is the natural home

### F-expa11y-05 - Diagnostics legends are dev-register where M-2/S-3 want lay
- disposition: FIX
- leverage: P2
- charter-trace: S-3 (owner's furthest-below-bar), M-2 (v1.0.7 lay legend), A-2
- question-refs: QB-exp-a11y-07, QB-eval-04 (legend specifics)
- evidence: dashboard/templates/dashboard.html@c6e0437: the groundedness tile
  reads "groundedness (L0)", "fabricated rate", "flagged", and stamps
  prompt_version (lines 308-315); the trend legend says "Each point labels its
  prompt_version on hover" (line 614); the L0 legend (line 693) reads "L0 is a
  flag-for-review signal (high precision on novel specifics; will false-positive
  on paraphrase). Uncalibrated until labels exist - see
  docs/dev/GROUNDING_METRIC.md"; the annotation legend (line 461) uses
  keep/fix/omit/fabricated/forbidden_pattern regex jargon.
- finding: Diagnostics are a charter-sanctioned power-user surface (R2-12.2) on
  the user->power-user->dev continuum (A-2), and S-3 is the owner's self-named
  furthest-below-bar area: "clear understanding... explainable to users, through
  the UI and the diagnostics." The current copy is honest and accurate but speaks
  in internals (L0, fabricated-rate, prompt_version, links into docs/dev/). The
  M-2 v1.0.7 criterion explicitly wants "a lay metrics legend in diagnostics,"
  which is unwritten at the pin. The fix is additive copy (a non-coder legend),
  not a redesign - and per S-2, incomplete-for-elegance is acceptable, so this
  need not be exhaustive.
- coordinate: Sprint 6.5 (in-app education / lay metrics legend)

### F-expa11y-06 - Keyboard bullet-reorder is the a11y floor (AL-2 OVERTURNED)
- disposition: KEEP
- leverage: P1
- charter-trace: E-2 (keyboard reorder alternative), C-4, AL-2
- question-refs: QB-exp-a11y-02
- evidence: static/app.js:4812-4827@c6e0437 builds up/down buttons with real
  aria-labels ("Move bullet up"/"Move bullet down") wired to _moveBulletRow(row,
  +/-1). _moveBulletRow (static/app.js:4995-5008) and the pointer-drag drop
  handler (static/app.js:~5037) call the IDENTICAL persistence pair
  _markCustomOrder(list) + _scheduleCompositionSave(). The regression test
  docstring (tests/ux/regression/test_20260604_bullet_drag_reorder.py:9-12) names
  keyboard as "the a11y floor, must-pass" and asserts both paths round-trip
  bullet_order through the real /composition POST + GET re-read.
- finding: AL-2 (lead) suspected the drag-reorder was keyboard-inaccessible (WCAG
  2.1.1 candidate on a core feature). OVERTURNED by evidence: a fully
  keyboard-operable reorder exists with real labels, writes the same persistence
  as drag, and is pinned by a must-pass test. This is the E-2 "bullet-reorder
  alternative" line item in working form and a C-4 candidate-control affordance.
  Protect it under any Compose refactor - the shared-persistence equality and the
  must-pass test are the guard.
- coordinate: Sprint 6.6 (Compose touches B.4/B.5 corpus completers)

### F-expa11y-07 - _announce() live-region discipline is intact (but unguarded by a test)
- disposition: KEEP
- leverage: P2
- charter-trace: E-2 (live-region at every async completion), C-4
- question-refs: QB-exp-a11y-09
- evidence: Single hidden aria-live=polite aria-atomic=true region
  (templates/index.html:18@c6e0437), driven by _announce() (static/app.js:2237)
  whose own comment warns "DON'T announce every status microstep - aria-live
  polite can drone if over-fed." Exactly 7 call sites, one per async completion:
  analysis (591), clarify-ready (795), iteration-done (1124), cover-letter (1226),
  edits-saved (1527), iteration-refined (1632), iterate-clarify-ready (1695) - git
  grep _announce(. No test asserts srAnnounce content: the only UX test
  referencing the area spies scrollIntoView, not the live region
  (tests/ux/regression/test_20260611_wizard_flow_polish.py:109-115).
- finding: This is the E-2 "live-region announcements at every async completion"
  line in working, deliberate form - including the anti-over-feed discipline E-2's
  WATCH note flags. Confirmed intact at the pin. The one caveat (WATCH): the
  mechanism has no regression test, so a refactor that drops a call site or
  re-introduces over-feeding would pass CI silently. Protect it; consider pinning
  it when F-expa11y-01 lands (a test only helps once CI runs the tier).
- coordinate: (none)

### F-expa11y-08 - Focus-trap + Escape + focus-return + skip-link + focus-visible
- disposition: KEEP
- leverage: P2
- charter-trace: E-2 (no traps, Escape/focus-return, focus on dynamic content)
- question-refs: (E-2 taxonomy KEEP)
- evidence: Edit modal, diagnostics modal, and settings drawer each implement
  Tab-wrap focus trap, Escape->close, and focus-return to the trigger element
  (static/app.js:1279-1391@c6e0437). Skip-link present (templates/index.html:12,
  "Skip to main content"). Comprehensive :focus-visible 2px ring across
  .cb-btn/tabs/inputs/.preview-editable (static/style.css:914-930).
- finding: The E-2 "no traps, Escape/focus-return, focus on dynamic content" lines
  are implemented in working form, plus a skip-link (bypass blocks) and a
  keyboard-only focus-visible ring that doesn't regress mouse UX. One narrow note
  (WATCH, not a defect): the edit modal's trap focusable set is
  button[data-modal-dismiss] only, so a richer future edit modal would need its
  focusable query widened - surgical, not blocking. Protect under refactor.
- coordinate: (none)

### F-expa11y-09 - WCAG-AA contrast fix is real and mathematically verified
- disposition: KEEP
- leverage: P2
- charter-trace: E-2 (contrast), C-0 (deterministic, so a categorical OK is allowed)
- question-refs: (E-2 contrast line; rides QB-exp-a11y-04)
- evidence: Commit efbe66b retuned --fg-2/--fg-3; the CSS comment records the old
  values were sub-AA (static/style.css:20). Sandbox-computed WCAG ratios against
  the exact --bg-0 #0c0d14 (static/style.css:13): --fg-2 #9b9ba7 ~ 7.0:1, --fg-3
  #8f8f9b ~ 6.0:1 (both pass AA 4.5:1 normal text; fg-2 clears AAA 7:1), vs the
  prior #6c6c7a ~ 3.7:1 and #4a4a56 ~ 2.2:1 (both failed AA).
- finding: Unlike LLM-behavior claims (C-0 bars absolutes there), contrast is
  deterministic and the fix is verifiably correct: the retuned secondary/tertiary
  text colors clear WCAG-AA on the dark surface where the old ones failed. The
  vendored axe gate also flags color-contrast, so this is double-guarded - when
  the gate runs. A clean, checkable strength to affirm so the retune isn't churned
  back to a prettier lower-contrast grey.
- coordinate: (none)

### F-expa11y-10 - Corpus-first onboarding + smart landing not landed (S-3 path open)
- disposition: WATCH
- leverage: P1
- charter-trace: S-3 (discoverability), M-2 (first-run bars + explainability artifacts)
- question-refs: QB-exp-a11y-08, QB-exp-a11y-06 (first-run half)
- evidence: Top tabs still open Tailor-first (templates/index.html:49-51@c6e0437,
  topTabTailor carries active + aria-selected=true). Sprint 6.4
  (feat/corpus-first-tab-onboarding, smart landing: empty->Corpus,
  non-empty->Tailor) and Sprint 6.5 (in-app education + lay metrics legend) are
  described as planned future branches in RELEASE_ARC.md:538-615 and are NOT
  merged at the pin (git log c6e0437 shows no corpus-first-tab-onboarding merge).
  The product-map records a Kickoff-KW1 observation that a new user currently
  lands on empty JD entry - the dead-end the smart-landing fix targets.
- finding: The S-3 discoverability path and the M-2 v1.0.7 explainability
  artifacts both ride Sprints 6.4/6.5, which are unbuilt at c6e0437. A new user
  with an empty corpus is routed to JD entry (a dead-end) rather than to corpus
  building. This is correctly WATCH (scheduled, in-flight epic) rather than FIX -
  but it is on the v1.1.0 critical path because M-2 gates the public tag on the
  two first-run bars and the explainability artifacts. Coordinate with the Sprint
  6.4/6.5 owners; do not duplicate.
- coordinate: Sprint 6.4 (IA/onboarding), Sprint 6.5 (in-app education)

---

## Appendix (beyond the register cap)

### A-expa11y-01 - Design-token system is partial, not absent (spacing/type scale missing)
- disposition: WATCH . leverage: P3 . charter-trace: A-4, S-2
- evidence: static/style.css@c6e0437 has a real :root token layer (--fg-*,
  --brand, --shadow-*, --grad-*, --bg-*) with 554 var(--...) references but ZERO
  --space-* tokens (grep -c var(-- = 554; grep -c --space- = 0) and no type-scale
  tokens.
- finding: "No design tokens" would be inaccurate - color/radius/shadow/gradient
  tokens are real and heavily used. What is thin is spacing and typography tokens
  and a documented token->component map (the A-4 portfolio bar). Per S-2
  (incomplete-for-elegance acceptable) this is P3/opportunistic, not blocking; the
  WATCH is token sprawl - a partial system growing ad-hoc without a spacing/type
  scale risks the worst of both. Not register-grade.

### A-expa11y-02 - Back/history discards wizard state (AL-3 confirmed)
- disposition: WATCH . leverage: P2 . charter-trace: E-2 (back/history), S-1 (data-loss-adjacent)
- evidence: Zero History API usage in static/app.js@c6e0437 (git grep
  pushState/replaceState/popstate/beforeunload -> no hits).
- finding: AL-3 confirmed: with no History API and no beforeunload guard, browser
  Back exits the SPA and discards expensive wizard state (analysis,
  clarifications, composition). The arc schedules the real fix as a v1.0.8
  back-nav item; a cheap interim is a beforeunload guard. Held in the appendix
  because it is scheduled (v1.0.8) and the data-loss is recoverable via the
  audit-trail context chain; severity is a11y+friction, not PII. Coordinate: v1.0.8.
