```toml
schema = 1
id = 116
kind = "item"
title = "Dynamically-created 'Run this fixture' help bubble (renderCollateResult) never verified to open in a browser"
status = "open"
decision_owner = "agent"
branches = ["feat/dashboard-copy-discovery"]
refs = [
  "dashboard/templates/dashboard.html",
  "tests/ux/regression/test_20260925_dashboard_copy_discovery.py",
  "tests/test_annotation_routes.py",
]
summary = "Post-Collate help circle is wired at runtime; C3's UX test never reaches it, only render-with-no-error is verified."
```

**Filed by the closer (C3, `feat/dashboard-copy-discovery`), from the implementer's own
close-out report** (source (c) of the closer's filing obligations, per the invoker note),
under Observations 2(b) and 11 of
`docs/dev/blast-radius/dashboard-copy-discovery.md`.

`renderCollateResult()` (`dashboard/templates/dashboard.html:2730-2764`) builds the
"Run this fixture (real --seed)" button and its `.help-info` circle (`runHelp`,
`:2757-2764`) **after** a Collate action, so the once-at-load `data-help` click wiring
(`:1272`, `document.querySelectorAll('.help-info[data-help]')…`) never reaches it — the
opener has to be exposed on `window` instead (`annCollateRunBtn`, `:2120-2160`) and
attached to this element specifically.

**What is and isn't verified:**
- `tests/test_annotation_routes.py`'s collate flow test runs the real collate route and
  passed with no console errors, so the button and its circle render without throwing.
- `tests/ux/regression/test_20260925_dashboard_copy_discovery.py`'s
  `test_every_tile_shows_lay_line_and_its_help_opens` iterates every **static** `.tile` on
  page load (`_TILES_PER_TAB`) — it never triggers a Collate, so it never reaches this
  dynamically-created circle.
- Nothing in the current suite clicks the "Run this fixture" bubble in a real browser and
  asserts `#helpModal` opens with `dashTileCollateRun`'s (or equivalent registry key's)
  title, the same way `_assert_help_opens()` does for every static tile.

**Suggested shape:** extend
`tests/ux/regression/test_20260925_dashboard_copy_discovery.py` (or add a case to
`tests/ux/flows/test_annotation_tab.py`, which already drives a live Collate) to run a
real Collate, locate the dynamically-created help circle by its `aria-label`, and reuse
`_assert_help_opens()` against it — closing the same static-vs-dynamic gap this project
has hit before (Observation 2b in the blast-radius dossier).

## Updates

### 2026-09-25 — filed during `feat/dashboard-copy-discovery` close-out (Epic C C3 closer)
