# The recruiter Pipeline tab — every candidate's applications at a glance

> **Purpose:** the user-facing explanation of the **Pipeline** tab — the
> cross-candidate board that groups every candidate's applications by status.
> **Not** the résumé-generation sequence (analyze → clarify → compose → …) —
> see the disambiguation note below.
> **Audience:** `user` — anyone using sartor with more than one candidate
> (a recruiter or agency user); no technical background assumed.
> **Grounding:** the Pipeline tab in `templates/index.html` (`#tab-pipeline`,
> `#pipelineBoard`) driven by `static/app.js` (`refreshPipeline`,
> `_renderPipelineBoard`, `_renderPipelineRow`), backed by the aggregate
> `GET /api/candidates/roster` route (`blueprints/users.py:candidate_roster`).

---

## What it is

The **Pipeline** tab is a read-only board that shows **every candidate's
applications in one place**, grouped into five columns by where each one
stands:

- **Draft** — started but not yet marked submitted.
- **No response yet** — submitted, still waiting to hear back.
- **Got interview** — an interview was scheduled.
- **Rejected**
- **Withdrawn**

Each card in a column shows the candidate's name, the job title, the
company (when known), and how long ago it last changed
(`static/app.js:_renderPipelineRow`). It's the same five statuses your
individual application list uses per candidate — see [[tailoring-a-resume]]
— just laid out across everyone at once instead of one person at a time.

## Not the résumé-generation pipeline

sartor uses the word "pipeline" for a second, unrelated thing: the internal
analyze → clarify → compose → generate → iterate sequence that builds one
tailored résumé (documented for developers, not here, since it's implementation
detail you don't need to use the app). If you came here looking for how a
*single* résumé gets built, see [[tailoring-a-resume]] instead — this page is
about the cross-candidate status board.

## Who sees it and why

The Pipeline tab sits alongside the other top-level tabs (Career corpus,
Tailor, Résumé templates, Candidate memory) and is always available — it
doesn't wait for a minimum number of candidates the way the searchable
candidate picker does. If you're using sartor for yourself, your own
applications simply show up as a single set of cards across the five columns.
The tab earns its keep once you're tracking **more than one person** — see
[[managing-users]] — where "which of my candidates are waiting to hear back?"
becomes a real question instead of one you can answer by memory.

## Using it

1. Open the **Pipeline** tab. The board loads automatically; use **Refresh**
   to pull the latest statuses without switching tabs.
2. Scan the five columns — the count at the top of each tells you how many
   applications are in that state, and the header line above the board shows
   the total across everyone.
3. **Click any card** to jump straight to that application: sartor switches
   the active candidate and opens that specific application's detail view, so
   you land exactly where you'd need to act next, not just on the candidate's
   general list.

## What it doesn't do (yet)

This is a **read-only, v1 view** — a snapshot, not a workflow tool. You can't
drag a card between columns or bulk-edit statuses from here; to change an
application's status, open it (click its card) and update it from there, the
same way you would for a single candidate.

## Related

- [[managing-users]] — adding candidates and how their data stays separate;
  the reason a Pipeline view is useful once you have more than one.
- [[tailoring-a-resume]] — the six-step wizard that produces the applications
  this board tracks status for.
- [[using-sartor]] — the whole first run, for the single-candidate path.
