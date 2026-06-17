# Accessibility status

> **Purpose:** an honest status page for callback.'s accessibility — what is
> machine-checked today, what was hand-walked, and what is not yet covered.
> It describes mechanisms and effort, not a conformance grade.
> **Audience:** anyone evaluating callback. who relies on assistive technology,
> keyboard-only operation, zoom/reflow, or sufficient contrast; contributors
> landing UI changes.
> **Authoritative for:** the current accessibility posture and its honest
> limits. This is **not** a conformance claim and **not** a release gate.
> Sibling docs: [`SECURITY.md`](SECURITY.md) (threat model),
> [`CONTRIBUTING.md`](CONTRIBUTING.md) (workflow).

## What this page is (and is not)

callback. is a local-first, single-user tool with one screen — a single-page
web app you run on your own machine. Accessibility has been built in as design,
not bolted on afterward. This page states plainly what that work covers so far.

It makes **no conformance claim** (no "WCAG 2.x AA compliant" badge), sets **no
tag gate** (a release is not blocked on an accessibility score), and promises
**no recurring manual-audit cadence**. Screen-reader and keyboard feedback are
treated as **priority bugs** — see [Reporting an issue](#reporting-an-issue).

## What is machine-checked today

A vendored, dependency-free [axe-core](https://github.com/dequelabs/axe-core)
4.10.2 engine runs as part of the browser-driven UX test tier
([`tests/ux/a11y/test_axe_smoke.py`](tests/ux/a11y/test_axe_smoke.py),
`pytest -m a11y`, inside `pytest -m ux`). It is injected into the live DOM via
Playwright, so it checks the real rendered page, not a static snapshot. What it
covers:

- **axe scan, `serious`/`critical` impacts only**, across the landing page, the
  new-user form, the Tailor step-1 panel, the Career Corpus / Candidate Memory /
  Personas tabs, the Settings drawer, the Compose and Template steps, and all
  five `/_dashboard` diagnostics tabs (plus the help modal). Hidden panels are
  excluded by axe; same-origin preview iframes are out of scope for the app's
  own form-label gate.
- A **keyboard bullet-reorder alternative** to pointer drag, pinned by a
  "must-pass a11y floor" regression
  ([`tests/ux/regression/test_20260604_bullet_drag_reorder.py`](tests/ux/regression/test_20260604_bullet_drag_reorder.py))
  that drives the keyboard path through a real save + re-read.
- A single **live region** (`aria-live="polite"`) announced at every async
  completion — analysis ready, clarify ready, iteration done, edits saved, and
  the rest — via one `_announce()` helper in
  [`static/app.js`](static/app.js), designed against over-feeding the region.
- **Modal discipline**: focus-trap with Tab-wrap, Escape to close, and focus
  returned to the opener, consistent across the edit and diagnostics modals.
- **Contrast**: the muted foreground tokens (`--fg-2` / `--fg-3` in
  [`static/style.css`](static/style.css)) were retuned to clear WCAG-AA 4.5:1 on
  the darkest surfaces.

## What is hand-walked

- A bounded, one-time **NVDA screen-reader walkthrough** of the wizard is
  **planned for pre-public hardening and has not been performed yet.** When it
  runs, this section will record the date, the NVDA version, and the panels
  walked. Until then, treat screen-reader coverage as machine-checked (axe) plus
  the live-region/keyboard/modal mechanisms above — not as screen-reader-verified
  end to end.

## Known gaps (not yet covered)

These are stated openly rather than implied away:

- **The axe / UX tier does not yet run in continuous integration.** It needs a
  Chromium binary that CI does not install today, so it runs on the maintainer's
  machine, not unattended on every change. Wiring it into CI as a required check
  is scheduled for the public-release work.
- **axe gates `serious`/`critical` only.** `moderate`/`minor` best-practice
  items (some heading-order, region, and name-role-value cases) can pass the
  current gate.
- **Some surfaces are not yet in the scanned set**: the Clarify step, the
  Output/Download step, the cover-letter flow, and dialog content beyond the
  scanned modals.
- **No machine assertion yet** for tab-order, reflow/zoom (200%/400%), or
  browser back/history behavior. (Browser **Back** currently exits the
  single-page app rather than stepping back a wizard stage — a known
  limitation slated for the blueprint-split work.)

## Direction

The intent for the public release is a dated, methodology-backed self-evaluation
of the **whole app** (including `/_dashboard`) against **WCAG 2.2 Level AA**,
published as a status update to this page — alongside running the machine-checked
tier in CI. That is a goal, not a present claim and not a commitment to a fixed
schedule.

## Reporting an issue

If something is hard or impossible to use with a screen reader, keyboard, zoom,
or because of contrast, please report it — these are treated as priority bugs.
Open an issue on the repository, or use the private channel in
[`SECURITY.md`](SECURITY.md#reporting-a-vulnerability) if you'd rather not file
publicly. This is a solo, best-effort project: reports are acknowledged and
addressed as quickly as is feasible, with no fixed-timeline promise.
