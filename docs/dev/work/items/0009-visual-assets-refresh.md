```toml
schema = 1
id = 9
kind = "item"
title = "release/visual-assets refresh - stale screenshots"
status = "closed"
decision_owner = "agent"
epic = 39
refs = ["RELEASE_ARC.md step 15", "scripts/capture_screenshots.py"]
summary = "10 committed PNGs were ~7.5 weeks stale as of 2026-07-21 (predate the diagnostics redesign); README hero never wired in."
resolution = "Done on feat/docs-assets-enforcement (Epic D D4, 2026-10-01). All 10 PNGs regenerated with scripts/capture_screenshots.py (they still showed the pre-rename product name). The README hero is wired under How it works. Two defects found on the way are fixed: the capture fixture's year-only dates (the month-precision gate refused Generate) and the projector's image links (all 10 images broke the docs-site build since D2). Follow-ons: item 139 (capture leaves demo state behind) and item 140 (bullet-id leak and invented letter date visible in two shots)."
verified_by = [
  "scripts/check_docs_site_mermaid.py in .github/workflows/docs-deploy.yml: every published page's same-origin images must return 200 (seeded: hero PNG removed -> HTTP 404, exit 1)",
  "tests/test_docs_site_checks.py::test_projected_images_point_at_the_copied_screenshots",
]
branches = ["feat/docs-assets-enforcement"]
```

Capture is a working, debugged Playwright run (`scripts/capture_screenshots.py`,
~$0.27 Anthropic spend, ~8 min, requires `python app.py` running locally
first) — the 3 staleness bugs found in `fix/capture-screenshots-welcome-modal`
are fixed. Gap to close: `readme_hero_wizard-step1-filled.png` was captured
for the README hero but never wired into `README.md`. Open, separate owner
decision (not this item's scope): the capture script has zero periodic/CI
coverage, which is what let staleness accumulate silently for ~7 weeks.

## Updates

### 2026-07-28 — filed during chore/work-item-tracking (migrated, not new)

### 2026-08-04 — folded into Final March epic D (sprint D4)

Executed as sprint D4 of epic 39, deliberately last-but-one in the march so the
screenshots capture the post-A/B/C UI exactly once. README hero wiring rides the
same sprint.
