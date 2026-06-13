---
status: review-artifact
evidence_sha: c6e0437
graduation: none
---

# Findings — Product experience & accessibility

> Severity anchor: the signed Product Charter. Claims-discipline C-0 honored —
> mechanisms and effort, no absolutes about LLM behavior, no marketing register.
> All `path:line` evidence read via `git show c6e0437:<path>` (worktree HEAD is
> the Phase-3 partial `b85be08`; every cite below is pinned at `c6e0437`).

## Domain verdict

callback. has a genuinely strong a11y *foundation* built as design, not
afterthought: a disciplined `_announce()` live-region, a keyboard bullet-reorder
alternative pinned by a "must-pass a11y floor" regression test, modal
focus-trap/Escape/focus-return, and a vendored dependency-free axe gate that
already scans `/_dashboard`. The decisive gap is **enforcement reach and honest
status**: the entire a11y/UX tier — axe gate included — runs only on a machine
that has Chromium, and CI installs none, so E-2's load-bearing phrase ("machine-
checked *in CI, free forever*") is not true at the pin; there is no
ACCESSIBILITY.md status page E-2 asks for; the cold no-API-key user is dumped
into a generic error mid-analyze rather than guided (A-1); and the power-user
diagnostics surface speaks in dev-register where S-3/M-2 want a lay legend. None
of these block the *experience* — they block the *charter promises about* the
experience. Sprints 6.4/6.5 (corpus-first IA, in-app education, lay legend)
carry the S-3/M-2 explainability load and are unbuilt at the pin — WATCH, not
yet FIX-able.

---

## Register

### F-expa11y-01 — a11y taxonomy is NOT machine-checked in CI (local-only gate)
- **disposition:** FIX
- **leverage:** P1
- **charter-trace:** E-2 (machine-checked in CI, free forever), A-2
- **question_refs:** QB-exp-a11y-01; verifies product-map DEBUFF-1
- **coordinate:** (none — predates the open sprints; a CI-matrix change)
- **evidence:** `.github/workflows/ci.yml@c6e0437` (quality job runs only
  `ruff check .` / `mypy .` / `pytest`; no `playwright install`, no `pytest -m
  ux`); `tests/ux/conftest.py@c6e0437` `_browser` fixture `pytest.skip(...)` when
  `chromium.launch()` raises; `pyproject.toml@c6e0437:128-129` (ux/a11y markers).
- **finding:** The vendored axe gate, the keyboard-reorder "a11y floor" test, and
  the whole `ux` tier skip silently whenever Chromium is absent, and CI never
  installs Chromium — so on PRs and `main` the agreed a11y taxonomy is unchecked.
  The mechanism is sound (graceful skip keeps default `pytest` green everywhere);
  the gap is that "free forever in CI" is a CI-matrix line that was never added.
  This is the single highest-leverage exp-a11y item: it converts every other
  a11y KEEP below from "runs on the maintainer's laptop" to "enforced
  unattended." Confirms product-map DEBUFF-1 as a real finding, not a candidate.

### F-expa11y-02 — cold no-API-key user is error-dumped mid-analyze, not guided
- **disposition:** FIX
- **leverage:** P1
- **charter-trace:** A-1 (API-key step = acknowledged friction), M-2 (first-run)
- **question_refs:** QB-exp-a11y-05
- **coordinate:** Sprint 6.5 (first-run onboarding modal, KW3) — a preflight could
  ride that sweep
- **evidence:** `app.py@c6e0437:87-95` `_get_client()` builds
  `anthropic.Anthropic(api_key=api_key)` with no preflight even when key is empty
  (dynamically confirmed in a sandbox: `Anthropic(api_key='')` does NOT raise at
  construction — the failure is deferred to call time); streaming analyze
  `app.py@c6e0437:657-678` catches only `anthropic.APIConnectionError` then a
  generic `except Exception` → `"Internal error during analysis."` (http 500);
  non-stream path `app.py@c6e0437:742-744` → `"Connection to AI service failed."`
  (503). Neither path catches `anthropic.AuthenticationError` (the 401 an
  empty/invalid key actually produces — enumerated from the SDK in-sandbox).
- **finding:** A first-run user without a configured key reaches `analyze()` and
  receives a generic connection/internal error with no mention of the API key —
  the one friction A-1 names explicitly. There is no UI preflight (a "no key
  detected — here's how" state) and the error copy actively misleads (it implies
  a network failure, not a missing credential). For the M-2 "< 5-min skip-clarify
  smoke," a keyless stranger's first action dead-ends opaquely. Cheap fix: a
  startup/route preflight that detects empty key and routes to setup guidance
  before any LLM call; minimally, catch `AuthenticationError` with key-specific copy.

### F-expa11y-03 — no ACCESSIBILITY.md honest-status page exists at the pin
- **disposition:** FIX
- **leverage:** P1
- **charter-trace:** E-2 ("ACCESSIBILITY.md as an honest status page"), P-3
- **question_refs:** (beyond QB cap — E-2 line item; surfaced by domain-guide §1)
- **coordinate:** v1.0.7 pre-public hardening / Sprint 6.5
- **evidence:** `git ls-tree -r c6e0437` finds no `ACCESSIBILITY.md` (root or
  `docs/`); the only a11y-named files are `tests/ux/a11y/*`.
- **finding:** E-2 spells out the a11y *deliverable* posture precisely — "no
  conformance claim, no tag gate, no recurring manual-audit promise," but
  **ACCESSIBILITY.md as an honest status page** plus a one-time NVDA walkthrough.
  At the pin the status page does not exist, so the charter's chosen way of being
  honest about a11y (state what is machine-checked, what was NVDA-walked, what is
  not covered) has no home. This is the C-0-aligned artifact: it lets callback.
  describe mechanism-and-effort instead of making (or implying) a conformance
  claim. Low-cost, P1 because it is a named pre-public a11y deliverable and the
  natural place to disclose F-expa11y-01/04/05's known gaps.

### F-expa11y-04 — diagnostics legends are dev-register; the lay metrics legend is unwritten
- **disposition:** FIX
- **leverage:** P1
- **charter-trace:** S-3 (owner's self-named furthest-below-bar), M-2 (v1.0.7
  lay metrics legend), E-2 (diagnostics in a11y scope), A-2
- **question_refs:** QB-exp-a11y-07, QB-eval-04
- **coordinate:** Sprint 6.5 (in-app education + lay legend); M-2 v1.0.7 criterion
- **evidence:** `dashboard/templates/dashboard.html@c6e0437:302-315` ("L0
  fabricated-specifics metric", `deterministic_metrics.groundedness`, "fabricated
  rate", "flagged"), `:326-328` (`prompt_version=candidate:<hash>`, "bump
  `PROMPT_VERSION`"), `:461-475` ("needs honest_rewrite", "needs a
  forbidden_pattern regex", "fail-closed, same as the CLI", "Save
  annotations.json"), `:432-434` (`[eval-grounding]` extras), `:614/632`
  (prompt_version-on-hover legends).
- **finding:** Every legend on the groundedness/tuning/annotate panes reads as
  internals — layer codes (L0), source-file references, candidate-hash mechanics,
  regex/contract jargon. The charter puts diagnostics *in* the a11y scope (axe
  does scan `/_dashboard` — good) but S-3 is the owner's explicitly-named
  weakest area and M-2 lists "a lay metrics legend in diagnostics" as a v1.0.7
  artifact. A non-coder power-user (A-2 continuum) cannot read what a 4.2/5
  groundedness score or "fabricated rate 6%" means here. The fix is copy/legend,
  not chart rework — it rides Sprint 6.5, and that sprint is unbuilt at the pin.

### F-expa11y-05 — axe scope is a first cut; several agreed taxonomy lines have no machine check
- **disposition:** FIX
- **leverage:** P2
- **charter-trace:** E-2 (the enumerated taxonomy)
- **question_refs:** QB-exp-a11y-04
- **coordinate:** (none — gate-expansion work; pairs with F-expa11y-01)
- **evidence:** `tests/ux/a11y/test_axe_smoke.py@c6e0437` — four tests cover
  landing, new-user form, tailor-step1, corpus, memory, personas, settings-drawer,
  compose, template, and 5 `/_dashboard` tabs; docstring gates `serious`/`critical`
  only, excludes iframes, and does not navigate to wizard clarify (Step 2),
  output/download (Step 6), cover-letter, or any modal. No dedicated check exists
  for tab-order assertion, back/history (see F-expa11y-06), or reflow/zoom
  (`grep` of `tests/ux` finds none).
- **finding:** The gate is an honest first cut, not the full E-2 taxonomy. Gating
  `serious`/`critical` only lets `moderate` items (heading order, region, some
  name-role-value) pass; the clarify/output/cover-letter surfaces and modals — the
  dynamically-rendered, highest-risk DOM — are unscanned; and several enumerated
  lines (tab-order, reflow/zoom, back/history) have no machine assertion at all.
  P2 because the *foundation* is there and trustworthy as far as it reaches; the
  charter just enumerates more than this scans. Sequence behind F-expa11y-01 (a
  gate that doesn't run in CI gains little from more scope).

### F-expa11y-06 — zero History API: browser Back exits the SPA and discards wizard state
- **disposition:** WATCH
- **leverage:** P2
- **charter-trace:** E-2 (back/history behavior), S-1 (data-loss-adjacent)
- **question_refs:** QB-exp-a11y-03; AL-3
- **coordinate:** v1.0.8 back-nav item (arc)
- **evidence:** `static/app.js@c6e0437` — `grep` for
  `history.(push|replace)State|popstate` returns 0 matches across the whole file.
- **finding:** With no History API usage, browser Back during the wizard leaves
  the single-page app entirely and discards expensive accumulated state (analyze
  output, clarify answers, composition edits) rather than stepping back a wizard
  stage. This is the E-2 "back/history behavior" line and an S-1-adjacent
  data-loss surface, not cosmetic — a user who reflexively hits Back mid-clarify
  loses a paid analyze round. Rated WATCH (not FIX) because the real fix is the
  arc's scheduled v1.0.8 back-nav work; a cheap interim (a `beforeunload` guard)
  is available but is a mitigation, not the fix. Confirms AL-3 at the pin.

### F-expa11y-07 — keyboard bullet-reorder alternative, pinned by a real "a11y floor" test
- **disposition:** KEEP
- **leverage:** P1
- **charter-trace:** E-2 (keyboard completeness incl. reorder alternative), C-4
  (candidate-edit affordance), AL-2
- **question_refs:** QB-exp-a11y-02
- **coordinate:** (none — protect under any Compose refactor and under v1.0.8 split)
- **evidence:** `static/app.js@c6e0437:4816-4827` up/down are real
  `<button type="button">` with `aria-label` "Move bullet up/down", wired to
  `_moveBulletRow` (`:4996-5008`) which calls `_markCustomOrder` +
  `_scheduleCompositionSave` — byte-identical persistence to the pointer-drag
  path (`:5025-5050`); regression
  `tests/ux/regression/test_20260604_bullet_drag_reorder.py@c6e0437:56-83`
  (`test_keyboard_reorder_persists_and_reset_reverts`) drives the keyboard path
  through a real `/composition` POST + GET re-read and asserts persistence + reset;
  the module docstring names keyboard "the a11y floor, must-pass."
- **finding:** This is the AL-2 concern fully resolved and *guarded*: a real
  focusable keyboard alternative to a pointer-only affordance, sharing one
  persistence path with drag, with a named must-pass regression test that
  genuinely exercises the keyboard route (not just the drag). It is exactly the
  E-2 "bullet-reorder alternative" line in working form. KEEP-protect: the only
  way it silently rots is via F-expa11y-01 (the test that pins it doesn't run in
  CI) — protect the test's reach as much as the code.

### F-expa11y-08 — `_announce()` live-region discipline intact at every async completion
- **disposition:** KEEP
- **leverage:** P1
- **charter-trace:** E-2 (live-region announcements at every async completion), C-4
- **question_refs:** QB-exp-a11y-09
- **coordinate:** (none — protect under the v1.0.8 app.js/static refactor)
- **evidence:** single hidden region `templates/index.html@c6e0437:18`
  (`aria-live="polite" aria-atomic="true"`); helper
  `static/app.js@c6e0437:2237-2245` (toggles textContent off-then-on for
  re-announce; its own comment warns against over-feeding polite regions); exactly
  7 call sites at the cited lines 591, 795, 1124, 1226, 1527, 1632, 1695 —
  analysis-complete, clarify-ready, iteration-done, cover-letter, edits-saved,
  iteration-refined, iteration-questions-ready.
- **finding:** A disciplined, single-region announcement architecture fires at
  each meaningful async completion and nowhere noisy — the E-2 "live-region at
  every async completion" line in working form, with the over-feed risk
  explicitly designed against. The mechanism is small and easy to break under a
  refactor (a moved call site, a renamed region id). KEEP-protect; do not let the
  v1.0.8 monolith split drop a call site silently. WATCH-adjacent: any new async
  completion added later must add its `_announce()`.

### F-expa11y-09 — modal focus-trap + Escape + focus-return, and the vendored dependency-free axe gate
- **disposition:** KEEP
- **leverage:** P1
- **charter-trace:** E-2 (no traps, Escape/focus-return, focus on dynamic content;
  diagnostics in a11y scope), C-4
- **question_refs:** QB-exp-a11y-04 (KEEP side), QB-exp-a11y-07 (diagnostics-in-scope)
- **coordinate:** (none — protect under refactor)
- **evidence:** `static/app.js@c6e0437:1279-1330` (`_showEditModal` Tab-wrap focus
  trap, `Escape`→cancel, focus restored to `triggerEl`); `:1321-1326`
  `openDiagnosticsModal` mirrors the same posture; axe gate is genuinely vendored
  (`tests/ux/a11y/vendor/axe.min.js@c6e0437` = axe v4.10.2, MPL-2.0; no pip dep per
  `pyproject.toml@c6e0437:129`) and scans every `/_dashboard` tab
  (`test_axe_smoke.py@c6e0437` `test_axe_dashboard_console`).
- **finding:** The modal a11y posture (no trap, Escape closes, focus returns to
  the opener) is implemented consistently across the edit and diagnostics modals —
  the E-2 dynamic-content lines in working form — and the axe gate's vendoring
  choice means it can never silently skip from a missing pip extra (only from a
  missing Chromium, which is F-expa11y-01's separate problem). Diagnostics being
  inside the a11y scope honors E-2's "diagnostics surfaces in scope." KEEP. (Cross-
  domain pointer, not re-litigated here: the vendored axe is MPL-2.0, relevant to
  oss-security QB-sec-06 license-completeness.)

### F-expa11y-10 — corpus-first IA + the two M-2 first-run bars are unbuilt at the pin
- **disposition:** WATCH
- **leverage:** P2
- **charter-trace:** S-3 (discoverability), M-2 (first-run bars + explainability)
- **question_refs:** QB-exp-a11y-06, QB-exp-a11y-08
- **coordinate:** Sprint 6.4 (corpus-first IA + smart landing), Sprint 6.5
  (education), v1.1.0 first-run release pass
- **evidence:** `templates/index.html@c6e0437:47-58` top tabs still open
  Tailor-first (`id="topTabTailor"` carries `active` + `aria-selected="true"`;
  Corpus is second); `RELEASE_ARC.md@c6e0437:538-547` Sprint 6.4
  `feat/corpus-first-tab-onboarding` (reorder to Corpus-first + smart landing) is
  *planned*; `:615-619` Sprint 6.5 education sweep planned; `:790-797` fresh-clone
  < 5 min lives in the v1.1.0 release pass. No artifact at the pin evidences either
  first-run time bar being met.
- **finding:** The S-3 discoverability path (a new user with an empty corpus
  currently lands on JD entry, per the arc's KW1 note) and the M-2 first-run bars
  (< 5-min skip-clarify smoke; ~15-min clarify-inclusive "surprisingly good") both
  ride unbuilt sprints. This is correctly WATCH, not FIX: the work is scheduled,
  the charter gates the v1.1.0 tag on it (M-2), and re-litigating unbuilt sprints
  is out of scope. Flagged so the Sprint 6.4/6.5 owner knows these two QB lines
  resolve there, and so v1.1.0 doesn't tag before the first-run bars are actually
  measured (T-D risk: machinery unexercised on real first-run timing).

---

## Appendix (beyond the register cap)

### A-expa11y-01 — partial design-token system: real color/radius/shadow tokens, no spacing/type scale, no documented map
- **disposition:** DEBUFF (the *sprawl risk*, not the tokens)
- **leverage:** P3
- **charter-trace:** A-4 (portfolio "whoa, robust"), S-2 (incomplete-for-elegance
  is acceptable)
- **evidence:** `static/style.css@c6e0437` is 3,463 LOC with a real `:root` layer —
  52 custom-property declarations, 554 `var(--…)` references (color, radius,
  shadow, easing, gradients incl. the `--fg-2: #9b9ba7` / `--fg-3: #8f8f9b` WCAG-AA
  contrast retune at `:23-24`); but `grep` for `--space-`/`--text-`/`--font-size-`
  returns 0 — no spacing or type-scale tokens — and there is no documented
  design-system artifact tying tokens to components.
- **finding:** "No design tokens" (a recurring map framing) is inaccurate — there
  is a substantive token layer. The genuine risk is the *partial* one the
  domain-guide WATCH names: a token system with color/radius/shadow but no spacing
  or type scale and no documented map can grow ad-hoc into "the worst of both."
  Per S-2, polishing this beyond what serves A-4/the continuum is explicitly *not*
  required — so the only actionable move is the cheap one: add spacing/type tokens
  *if/when* the v1.0.8 split or a design-system doc lands, and write the token→
  component map as part of the A-4 exhibit, not as polish for its own sake. P3,
  opportunistic. DEBUFF the *ad-hoc-growth* pattern, not the existing tokens.

### A-expa11y-02 — DEBUFF guard: do not let a11y work breach C-5 (plain-bullet ATS) or C-4 (edit affordances)
- **disposition:** WATCH
- **leverage:** P3
- **charter-trace:** C-5 (ATS-safe always), C-4 (candidate edits), E-2
- **evidence:** domain-guide §3 DEBUFF clause; no breach observed at the pin —
  the keyboard-reorder (F-expa11y-07) and `_announce` (F-expa11y-08) work both
  *preserve* edit affordances and ATS output.
- **finding:** Recorded as a standing guard, not a current defect: future a11y
  tightening (e.g., adding ARIA grid semantics to the bullet list, or
  conformance-driven markup changes) must not break the plain-bullet ATS contract
  (C-5) or the candidate's ability to edit at every step (C-4). Equally, the
  charter forbids pursuing WCAG-conformance *language* or a tag gate (E-2) — so
  none of the FIX items above should be framed as "reaching conformance." No
  action at the pin; a lens for reviewers of the open sprints.
