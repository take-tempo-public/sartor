```toml
schema = 1
id = 71
kind = "item"
title = "Gather data toward a future design pass: managed/orchestrated epic execution with robust guardrails"
status = "watching"
decision_owner = "user"
refs = [
  "docs/dev/epic-a-chain-design-corrections.md",
  "docs/dev/work/items/0065-wiki-freshness-counter-measures-the-wrong-thing.md",
  "docs/dev/work/BOARD_DEFERRAL.md",
  "scripts/work_items.py",
]
summary = "Pointer + aggregated data for a future orchestrated-epic-execution design pass -- not a proposal."
```

**This item is a pointer, not a proposal.** It exists so a future design pass for
managed/orchestrated epic execution starts from real, named data points instead of
cold — Epic A's chain has surfaced several concrete ones worth aggregating. No design
is attempted here, and none is endorsed. `decision_owner = "user"` and
`status = "watching"` record that scoping *when* that design pass happens is the
owner's call, not something this item schedules or greenlights.

**Data point 1 — a hard gate and a deferral cadence, approved separately, never
reconciled.** `python -m scripts.work_items check` (wired into `scripts/gate.py`)
normally fails the moment `docs/dev/work/BOARD.md` doesn't match a fresh render of
`docs/dev/work/items/*.md`. Separately, `docs/dev/epic-a-chain-design-corrections.md`
§15.2 ("light per sprint") authorized Epic A's later sprints to file items per-sprint
without regenerating `BOARD.md` each time. Both were owner-approved in isolation;
nobody had checked them against each other until A3's own close-out tripped the gate
(commit `4fb60ee`) and this branch had to build `docs/dev/work/BOARD_DEFERRAL.md` +
`check_with_deferral()` to reconcile them after the fact. A managed-execution design
should treat "does a new cadence conflict with an existing gate" as a question asked
*before* the cadence is authorized, not discovered when a gate goes red.

**Data point 2 — the marker-verification gap this same branch just partially
closed.** `BOARD_DEFERRAL.md`'s `epic` field was free text nobody verified against
real backlog state: a well-formed marker granted the exemption regardless of which
epic was actually running, with the only real control being "someone had to write
this file and it's visible in the diff." This branch added a cross-check
(`scripts/work_items.py::_find_deferral_epic()`) confirming the named epic is a real,
open `kind = "epic"` backlog item — but explicitly does **not** verify that the
*current branch* is actually a member of that epic (see `BOARD_DEFERRAL.md`'s own
"What this still does not verify" section, and this item's own filing task). That is
a recurring **shape**, not a one-off: an asserted-but-unverified precondition
granting a real exemption. A future design pass should treat "what does this
mechanism assert vs. what does it actually check" as a standing question for any
guardrail it proposes, not just this one instance.

**Data point 3 — the existing material this design pass should start from, not
duplicate.** `docs/dev/epic-a-chain-design-corrections.md`:

- **§11** — the whole authorization-envelope apparatus: halt points (§11.5, no
  judgment involved), flag stops (§11.6, conditional human need), handbacks (§11.7),
  what the orchestrator decides alone inside the envelope (§11.8), and the delegation
  seam — the orchestrator never touches the working tree directly (§11.9).
- **§12** — the post-Epic-A friction register, F1 through F11, sourced line by line
  (§12.2). Two rows worth flagging by name for this design pass specifically:
  **F6**, subagents compacting silently with no signal to the orchestrator (a
  non-report with unbounded quality risk on any delegated result — directly relevant
  to "how does an orchestrator trust what a managed agent reports back"), and **F9**,
  the wiki freshness counter measuring "files changed since checkpoint" instead of
  "coverage current" (the same *counter-measures-the-wrong-thing* class as data point
  2 above, and the class item 0065 names directly — see data point 4).
- **§13** — the obligation audit of what's enforced vs. what's prose-only, including a
  finding that was raised and then **retracted** (§13.2) — read before re-deriving the
  same audit from scratch.
- **§14** — two instrument proposals (`require-chain-briefing`, delegation
  attribution) that were **drafted and then withdrawn** after adversarial review
  (§14.5), with the reviewers' objections recorded (§14.4 falsifiers, §14.6 what to
  build instead). This is real prior art on what does **not** work for this problem
  class — a future design pass re-proposing something in this shape should read why
  these two were refuted before doing so.
- **§15.7** — what must be true before Epic B starts, including the still-unresolved
  §14.7 finding that the delegation seam is gateable via `agent_id` — flagged as "the
  highest-value unbuilt item" and explicitly deferred past Epic A (§11.6.5: a new
  enforcement surface mid-chain is the owner's call, not a closer's).

**Data point 4 — the closest prior instance of the same failure class.** Board item
`0065` ("wiki freshness counter measures the wrong thing") is not new to this branch —
it is the same *metric-measures-proxy-not-target* shape as data point 2's marker gap,
just in a different subsystem (wiki checkpoint drift vs. board-staleness deferral).
Two independent instances of the same class in one epic is itself a data point worth
the design pass weighing directly, per charter C-11 ("the first time you recognize a
failure mode as a RECURRENCE... author a mechanism").

## Updates

### 2026-08-09 — filed at `feat/role-summary-drafting`, Epic A follow-up task

Filed per explicit owner direction: a tracked backlog item capturing "collect data
toward a full design pass for managed/orchestrated epic execution with robust
guardrails," aggregating this session's concrete findings rather than starting the
future design pass cold. Companion to the same-branch fix closing the marker-epic
gaming gap (data point 2).
