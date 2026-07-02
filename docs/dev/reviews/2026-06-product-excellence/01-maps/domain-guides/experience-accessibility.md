---
status: review-artifact
evidence_sha: c6e0437
graduation: none (rubric portions are v1.0.7 governance candidates)
---

# Domain guide — Product experience & accessibility

> Severity anchor: the signed Product Charter. A gap counts only if it
> blocks a charter clause. Claims-discipline C-0 applies to this guide too:
> mechanisms and effort, no absolutes about LLM behavior, no marketing register.

## 1. What mastery means here

For sartor., experience-and-a11y mastery is not generic WCAG conformance —
the charter is explicit that **no conformance claim, no tag gate, no recurring
manual-audit promise** is made (E-2). Mastery is instead three concrete things,
each charter-anchored:

- **The 15-minute "surprisingly good" bar is real and felt (M-2).** A
  full clarify-inclusive first run finishes in ~15 min and the output survives
  an owner-blind comparison against a hand-tailored resume. The wizard's job is
  to make that path legible and unblocked — and to make the < 5-min skip-clarify
  smoke run feel fast, not empty.
- **The agreed a11y taxonomy is machine-checked *in CI, free forever* (E-2),**
  not just runnable locally. The taxonomy is enumerated: names/labels, tab
  order, keyboard completeness (incl. a bullet-reorder alternative — lead AL-2),
  no traps, Escape/focus-return, focus on dynamic content, live-region
  announcements at every async completion, back/history behavior (lead AL-3),
  reflow/zoom, contrast. Mastery = the gate exists, runs unattended, and the
  honest status lives in ACCESSIBILITY.md.
- **Power-user surfaces are first-class UX on one continuum (A-1/A-2/E-2),**
  and the grounding/clarify/tuning pipelines are explainable *through the UI and
  diagnostics* (S-3, the owner's self-named furthest-below-bar area). The
  candidate stays in control — editable at every step (C-4). Design-system
  maturity matters only insofar as it serves the portfolio "whoa, this is
  robust" reaction (A-4) and the continuum, not as polish for its own sake (S-2:
  incomplete-for-elegance is acceptable).

External best practice (WCAG 2.2 SC 4.1.3 status messages, focus-visible,
single-column reflow) is useful framing, but where it conflicts with the
charter's "honest status, no conformance claim" posture, the charter wins.

## 2. Current state pointers

**Strengths (name them):**
- **A genuine live-region architecture exists.** A single hidden
  `aria-live="polite" aria-atomic` region (`templates/index.html:18@c6e0437`)
  is driven by a disciplined `_announce()` helper used at every async completion
  — analysis, clarify-ready, iteration-done, cover-letter, edits-saved
  (`static/app.js:2237`, call sites 591/795/1124/1226/1527/1632/1695). The
  helper's own comment warns against over-feeding polite regions — this is
  considered design, the E-2 "live-region at every async completion" line item
  in working form.
- **Keyboard reorder (AL-2) is built and treated as the a11y floor.** Up/down
  buttons carry real `aria-label`s ("Move bullet up/down",
  `static/app.js:~4820`) and write the same `bullet_order` persistence as the
  pointer drag; the regression test is named "the a11y floor, must-pass"
  (`tests/ux/regression/test_20260604_bullet_drag_reorder.py:9`).
- **Modals/drawers implement focus-trap + Escape + focus-return** to the
  trigger element (`static/app.js:1279-1391`) — the E-2 "no traps,
  Escape/focus-return, focus on dynamic content" lines, in working form.
- **A vendored axe gate ships** (`tests/ux/a11y/test_axe_smoke.py`), no pip
  dep, scanning landing / new-user form / four top tabs / Settings / a stubbed
  Compose+Template drive / every `/_dashboard` tab; the WCAG-AA contrast fix
  (`--fg-2`/`--fg-3` retune) rode Sprint 6.3.
- **Diagnostics is in the a11y scope** (the axe gate scans `/_dashboard`),
  honoring E-2's "diagnostics surfaces in scope."

**Gaps:**
- **The a11y taxonomy is NOT machine-checked in CI (E-2's load-bearing
  phrase).** `ci.yml@c6e0437` runs `ruff`/`mypy`/`pytest` only; it never
  installs Chromium, and the `ux`/`a11y` tiers skip without it
  (`tests/ux/conftest.py:85`). The gate is local-only — "free forever in CI" is
  not yet true.
- **axe scope is a first cut, not the full taxonomy.** It gates
  `serious`/`critical` only, excludes iframes, and (per its own docstring) does
  not yet cover wizard Step-2/5/6 or modals. Several taxonomy lines — tab-order
  assertion, back/history (AL-3), reflow/zoom — have no dedicated machine check
  yet.
- **Cold-user-with-no-API-key onboarding is unhandled in the UI.**
  `_get_client()` reads env/`.api_key` (`app.py:89-95`) with no preflight; a
  keyless user hits a generic "Anthropic API connection error"
  (`app.py:658/744`) mid-analyze, not guided setup. A-1 names the API-key step
  as acknowledged friction; nothing in the UI mitigates it.
- **Corpus-first onboarding + smart landing is NOT landed at c6e0437.** The top
  tabs still open Tailor-first (`templates/index.html:48`, `topTabTailor active`);
  Sprint 6.4 (corpus-first IA, smart landing) and Sprint 6.5 (in-app education,
  lay metrics legend, the explainability artifacts) are *planned* in
  RELEASE_ARC, not built — so the S-3 explainability bar and the M-2 v1.0.7
  explainability criterion are open.
- **Diagnostics legends are dev-register, not lay (S-3, M-2).** Console copy
  reads like internals — "L0 fabricated-specifics groundedness score",
  `prompt_version` on hover, links to `docs/dev/GROUNDING_METRIC.md`
  (`dashboard/templates/dashboard.html:461-693`). The "lay metrics legend"
  M-2 wants is unwritten.
- **"No design tokens" is inaccurate — but the system is partial.** style.css
  is 3,463 LOC with a real `:root` token layer (~52 custom properties, 554
  `var(--…)` references): color, radius, shadow, easing, gradients. What is
  thin is *spacing and typography* tokens (no `--space-*`/type scale), and there
  is no documented design-system artifact tying tokens to components — the gap
  vs the A-4 portfolio bar is documentation/scale tokens, not "no tokens."

## 3. Rubric

**BOOST** — A taxonomy line moves from local-only to *machine-checked in CI,
unattended* (E-2); a power-user surface (diagnostics/tuning) gets a lay-legible
explainer that a non-coder can read (S-3); the cold no-key user is guided rather
than error-dumped (A-1); the 15-min path is made measurably more legible (M-2).

**KEEP** — The `_announce()` live-region discipline; the keyboard-reorder floor
with real aria-labels (AL-2); focus-trap + Escape + focus-return in modals; the
vendored, dependency-free axe gate; diagnostics being inside the a11y scope.
These are working charter mechanisms — protect them under refactor.

**FIX** — CI does not run the a11y/UX tier (E-2 "in CI"); no API-key preflight
in the UI (A-1); diagnostics copy is dev-register where M-2 asks for lay (S-3);
axe scope omits wizard Step-2/5/6 + modals + tab-order/reflow/history lines.

**DEBUFF** — Pursuing WCAG-conformance language or a tag gate (E-2 explicitly
forbids both); polishing the design system beyond what serves A-4/the continuum
(S-2 says incomplete-for-elegance is fine); a11y tightening that breaks the
plain-bullet ATS contract (C-5) or the candidate-edit affordances (C-4).

**WATCH** — Sprints 6.4/6.5 are unbuilt at c6e0437; the M-2 first-run bars and
S-3 explainability ride them. Over-feeding the polite live region (the helper
warns of this). Token sprawl: a partial token system that grows ad-hoc without
spacing/type scale or a documented map risks the worst of both.

## 4. Sharpest questions

(See structured output.)
