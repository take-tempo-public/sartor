```toml
schema = 1
id = 74
kind = "item"
title = "refreshPipeline() refetches the entire cross-candidate roster on 7 trigger sites -- wider payload, no N+1, revisit if roster grows"
status = "watching"
decision_owner = "agent"
refs = [
  "docs/dev/blast-radius/prior-apps-pipeline.md",
  "static/app.js",
  "blueprints/users.py",
  "tests/test_roster_avoids_n_plus_1_query_growth.py",
]
summary = "refreshApplications() (1 candidate) replaced by refreshPipeline() (whole roster) at 7 sites -- disclosed trade, no N+1."
```

**What changed.** `feat/prior-apps-pipeline` (Epic A, sprint A4) removed the
Applications panel and its `refreshApplications()` (`GET
/api/users/<u>/applications` — one candidate's applications) and replaced
every call site with `refreshPipeline()` (`static/app.js:203`, `GET
/api/candidates/roster` — every candidate's applications). All **7** converted
call sites now trigger a full-roster refetch: `runAnalysis`'s completion
handler (`:1101`), the generate-completion handler (`:1794`),
`markCurrentApplicationSubmitted()` (`:3458`), `_renderAppDetailStatusActions`
(`:6272`), `_renderAppDetailAdminRow`'s restore and retire handlers
(`:6289`, `:6303`), and the `_saveMeta` closure inside
`_showApplicationDetail` (`:6506`) — i.e. on every analyze completion, generate
completion, status change, restore, retire, and meta-save.

**`refreshPipeline()`'s own guard never actually short-circuits this in
practice.** `if (!board) return` (`static/app.js:206`) is a no-op guard:
`#pipelineBoard` (`templates/index.html:940`) is always present in the DOM,
inside a `.hidden` tab panel that is never destroyed, whether or not the
Pipeline tab is currently visible. So every one of the 7 triggers fires a real
network request regardless of which tab the user is looking at.

**Disclosed as a deliberate trade in the A4 dossier's `## Efficiency`
section, not a defect.** The panel this replaced is gone, and no
per-candidate endpoint remains wired to any surviving frontend surface — a
narrower refetch isn't available without adding one back, which would be new
feature work beyond this sprint's scope. The trade is mitigated, not raw:
`GET /api/candidates/roster` (`blueprints/users.py::candidate_roster`) is a
fixed 2-query aggregate regardless of candidate or application count, guarded
by `test_roster_avoids_n_plus_1_query_growth`. So this branch introduced a
**wider payload per trigger, not an algorithmic regression** — no N+1 was
added.

**Why file this anyway.** Even a fixed 2-query aggregate has a real
per-request cost that scales with total roster size (rows returned, JSON
serialized, DOM re-rendered) — and that cost is now paid on every status
change, not just on an explicit refresh. At today's roster sizes this is
unlikely to matter; it is worth a look if the candidate/application roster
grows large enough that a full-roster refetch on every retire/restore/status
click becomes a felt cost.

**Candidate directions, not evaluated or endorsed:** (a) leave as-is until
roster size actually motivates a change; (b) debounce/coalesce rapid
sequential triggers (e.g. status-change immediately followed by a modal
re-render already calls `refreshPipeline()` once per action); (c) reintroduce
a narrower per-candidate or per-application refresh path if a future surface
needs one anyway.

## Updates

### 2026-08-09 — filed at `feat/prior-apps-pipeline` close-out (Epic A, sprint A4)

Filed following the A4 adversarial refuter's efficiency finding (verified: 7
call sites, roster-wide fetch, guard never short-circuits, mitigated by the
2-query aggregate). `decision_owner = "agent"` — no product decision is
implied here (the trade is already made and disclosed); revisiting is a
mechanical/performance question to pick back up if roster size warrants it,
not a call that needs the owner's product judgment.
