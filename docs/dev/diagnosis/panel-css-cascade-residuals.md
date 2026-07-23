# Diagnosis — `.cb-panel` collapse snaps instead of easing; mobile `.panel-body` padding never applies

> **Status:** root cause PROVEN (static cascade trace + live `getComputedStyle` capture)
> **Branch:** `fix/panel-css-cascade-residuals`

---

## Symptom

Two residual defects surfaced during the `refactor/css-cascade-collapse` (PX-51)
selector census, filed as carry-forward ledger items #11 and #12, deliberately left
unfixed on that branch:

1. Toggling a `.cb-panel`'s collapsed state appears to snap open/closed instantly
   rather than easing, as the `grid-template-rows` transition intends.
2. On narrow (mobile, ≤768px) viewports, `.panel-body` padding appears identical to
   the desktop value — the mobile-specific override appears to have no effect.

---

## Observed

- **Static cascade trace, `static/style.css`:**
  - `.cb-panel` (`:3355`) sets `transition: border-color var(--t-fast) var(--ease),
    box-shadow var(--t-med) var(--ease);` (`:3363–3365`) — no `grid-template-rows`
    entry. `git log --oneline -- static/style.css` shows this is the sole surviving
    `.cb-panel {` block post-PX-51 (`dd30c82`, "collapse duplicate-selector cascade") —
    `grep -c "^\.cb-panel {" static/style.css` = 1.
  - Three rules set `.panel-body { padding }`: `:519` (`.panel-body`, inside
    `@media (max-width:768px)`, spec 0,1,0, value `12px 16px`); `:2462`
    (`.cb-main .panel-body`, spec **0,2,0**, unconditional, value `18px 22px`); `:3403`
    (`.panel-body`, spec 0,1,0, unconditional, value `18px 22px 20px`).
  - `grep -n "panel-body\|cb-main" templates/index.html`: every `.panel-body` in the
    app's markup (7 sites) is nested inside a `.cb-main` ancestor. So `:2462`'s
    (0,2,0) specificity beats the (0,1,0) mobile override on every real panel,
    independent of source order.
- **Live capture** (Playwright, Chromium, viewport 375×800, against `python app.py` on
  `localhost:5000`, `.panel-body` = `#panelUser`'s body, first panel in the DOM):
  ```
  panel-body padding @375px: 18px 22px
  cb-panel transitionProperty: border-color, box-shadow
  ```
  Confirms both: the mobile padding override (`12px 16px`) never applies (`18px 22px`
  observed instead — the `.cb-main .panel-body` unconditional value), and
  `transitionProperty` excludes `grid-template-rows` entirely.

---

## Falsified

- **First attempted fix: raise `:519`'s selector to `.cb-main .panel-body` (same
  (0,2,0) specificity as `:2462`) — FALSIFIED by live re-test.** Re-running the
  Playwright capture after this edit still showed `panel-body padding @375px:
  18px 22px` (unchanged). Equal specificity does not favor the media-query rule —
  CSS breaks specificity ties by **source order**, and `:2462` (unconditional)
  appears later in the file than `:519` (inside the `@media` block), so `:2462`
  still wins regardless of the viewport. Raising to *equal* specificity was the
  wrong target; it needed to be strictly higher.

---

## Inferred

_(None needed — both mechanisms are directly observed, not inferred: the cascade
math is deterministic given the confirmed specificities and DOM nesting, and the
live `getComputedStyle` result matches the static prediction exactly.)_

---

## Falsification

Not applicable in the test-file sense (this is a CSS cascade defect, not a
nondeterministic runtime bug) — the live capture above already **is** the
falsification experiment: it directly measures the computed values the hypothesis
predicted, with no room for an alternative explanation (specificity is deterministic
arithmetic, and the DOM-nesting grep is exhaustive over the one template file).

---

## The fix

1. Add `grid-template-rows var(--t-med) var(--ease)` to the `.cb-panel` transition
   list (`:3363–3365`) — restores the eased collapse (owner-chosen duration:
   `--t-med` = 240ms, over the slower `--t-slow`/original-0.35s alternative).
2. Raise the mobile override at `:519` from `.panel-body` to
   `body .cb-main .panel-body` — (0,3,0), strictly higher than `:2462`'s (0,2,0),
   so it wins regardless of source order (see Falsified: equal specificity ties
   fall back to source order, which favors `:2462`).

---

## Acceptance bar

- Re-running the same Playwright capture after the fix must show: `.panel-body`
  padding @375px = `12px 16px`; `.cb-panel` `transitionProperty` includes
  `grid-template-rows`. **Met** — live re-test (`fix/panel-css-cascade-residuals`,
  2026-07-23) confirmed both, plus a desktop-viewport (1280px) control showing
  `.panel-body` padding stays `18px 22px` (unaffected — the media query still
  correctly scopes the override to ≤768px).
- `python -m scripts.gate` green (ruff + format + mypy + pytest), no reruns in the
  pytest log.
