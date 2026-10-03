```toml
schema = 1
id = 138
kind = "item"
title = "The Settings drawer has no help bubble"
status = "open"
decision_owner = "user"
branches = ["feat/docs-assets-enforcement"]
refs = [
  "static/app.js:2383",
  "templates/index.html:1316",
]
summary = "_initHelp attaches only to .cb-panel; Settings is a drawer, so it gets no (i) bubble or Learn more link."
```

**Observed (2026-10-01, `feat/docs-assets-enforcement`, read in code):** `_initHelp`
returns early unless the block has class `cb-panel` (`static/app.js:2383`). The Settings
drawer is `<aside id="settingsDrawer" class="settings-drawer">`
(`templates/index.html:1316`), with no `cb-panel` inside it, so it has no help bubble.

Carried as a declared gap since the `user-docs` handoff. **Owner decision, 2026-10-01:** not
built in D4; filed here. Adding it is a product change (a new bubble, copy, and a "Learn
more" target), so whether it's wanted is the owner's call.

### 2026-10-02 — re-parented out of epic 39 (`chore/release-v1.1.0`)

Epic 39 merged as PR #150 and closed. The owner directed its open children to stand on their own under Open, rather than hold the epic open.
