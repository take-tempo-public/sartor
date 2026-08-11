```toml
schema = 1
id = 72
kind = "item"
title = "Pipeline rows have no pending-proposals indicator -- the removed panel's pill has no equivalent"
status = "watching"
decision_owner = "user"
refs = [
  "docs/dev/blast-radius/prior-apps-pipeline.md",
  "static/app.js",
  "ui_pages/selectors.py",
]
summary = "At-a-glance pending-review discoverability regressed -- count is still reachable in the detail modal, not on the row."
```

**Filed per the A4 dossier's own `## Deferred` #3, tracked here rather than
left to rest only in the dossier.** `feat/prior-apps-pipeline` (Epic A, sprint
A4) removed the Applications panel and its `.application-card-pending` pill
(`PriorApps.PENDING_PILL`, `ui_pages/selectors.py`, removed by that branch's
row 6). The Pipeline board that replaced the panel as the sole surviving
surface has no equivalent — `_renderPipelineRow` shows status, company, title,
and date, but not a pending-proposals count.

**Nothing is unreachable.** The underlying value (`runs[].pending_proposals`)
is still returned by the API and still visible once a candidate opens the
detail modal for a given application — this is a discoverability regression,
not a data-loss one. Before this branch, a user scanning the Applications list
could see which applications had unreviewed proposals without opening
anything; after, they have to open each application's modal to find out.

**Scope note.** The A4 sprint brief was "remove the panel, rewrite
`activate()`" — adding a new indicator to `_renderPipelineRow` (plus its own
selector, plus a new UX regression assertion) is feature work beyond that
scope, which is why A4 deferred it rather than building it inline.

**Candidate shape, not evaluated or endorsed:** a small badge or count on the
Pipeline row driven by the same `pending_proposals` field the modal already
reads, with a new selector (e.g. `Pipeline.ROW_PENDING_COUNT`) and a UX
assertion exercising it.

## Updates

### 2026-08-09 — filed at `feat/prior-apps-pipeline` close-out (Epic A, sprint A4)

Filed per the dossier's own `## Deferred` #3, which named this gap and said
"worth a work item at epic close if the owner wants parity restored." Filed
now, at sprint close, rather than waiting — `decision_owner = "user"` because
whether to restore this parity (and in what shape) is a product/UX call.
