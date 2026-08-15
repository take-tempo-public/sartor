# Board → forge sync review (design-sprint input, item 97)

> **Status:** design-sprint INPUT, not a decision record. Written 2026-08-14 at the
> owner's direction ("review our board as it is and the possible integrations with
> github/gitea/gitlab... describe needed changes, and document for the next design
> session") after the external-orchestration redirect (item 97) and the owner's
> selection of `claude-code-action` as the factory dispatcher. Everything here is
> input for the design agent to probe, not scope of record. The companion research
> report (the "Dark Factory Dispatch" artifact) carries the tool-landscape evidence.

## 1. The board as it is (facts, verified at `feat/ats-conformance`)

- **Storage:** one file per item under `docs/dev/work/items/` — markdown with a
  fenced ` ```toml ` frontmatter block (`schema = 1`), parsed by stdlib `tomllib`.
  97 files at this writing. `docs/dev/work/BOARD.md` is **generated** from them
  (`python -m scripts.work_items board`) and gate-checked against them
  (`work_items check`, run inside `python -m scripts.gate` and CI).
- **Fields** (`docs/dev/work/SCHEMA.md`): `id` (canonical, immutable), `kind`
  (item/epic, nesting depth 1), `title`, `status`
  (`open|blocked|deferred|watching|closed`), `decision_owner` (`user|agent` — the
  schema's own "highest-value field"), `blocked_on`, `resolution`, `epic`,
  `depends_on` (array of ids — peer sequencing), `branches`, `refs`, `summary`
  (≤120 chars), `verified_by` / `closure_exception` (the C-11 closure bar),
  `guardrail` / `guardrail_deferred` (reopen discipline), and an opaque `[x]`
  table the validator ignores wholesale.
- **What the board does NOT have today** (each verified, not assumed):
  - **No `priority` field.** Sequencing exists only as `depends_on`/`epic` and
    prose in `RELEASE_ARC.md`.
  - **No "next ready item" query.** `scripts/work_items.py` has exactly two
    subcommands: `check` and `board`.
  - **No dispatch payload.** An item names `refs`, but the executable brief for a
    task lives in separate handoff/brief docs by convention, not in a field.
  - **Known header quirk:** the BOARD.md count line mixes populations (open
    includes epic-nested items; other counts are top-level only) — item 82.
- **Governance already attached to the board:** the C-11 closure bar
  (`verified_by`/`closure_exception`, reopened-item `guardrail`) runs in the gate
  and CI, so it binds every agent. **Any sync design must not route around it.**
- **`docs/dev/work/SCHEMA.md` is a GATED surface** (`scripts/enforcement/
  blast_radius.py` registry) — the schema changes proposed below trigger
  `require-consumer-enumeration`; the design sprint owes a C-10 dossier before
  the first schema edit.

## 2. What the GitHub-native factory needs from a board

From the chosen dispatcher shape (cron workflow → picker → `claude-code-action`
headless run → PR → human gate):

1. **Priority ordering** over dispatchable items.
2. **Ready detection**: `status = open`, all `depends_on` closed, **and**
   `decision_owner = agent` — a `decision_owner = user` item must never be
   auto-dispatched; that field is already exactly the human-gate marker the
   factory needs, which is a genuine head start.
3. **A dispatch payload**: the text the agent receives (brief path or inline body).
4. **Writable execution state** that does NOT create a second writer on the
   canonical record: claimed / attempted-failed / done.
5. **Failure surfacing**: a failed run marks the task so the next cycle skips it,
   and notifies the owner (the "human steps in only on issues" gate).

## 3. Canonicality (item 97 Q1) — resolved 2026-08-14: the board is the queue

Forge-issue integration is **not part of the factory design** — not as a
prohibition to record, simply as scope: the owner reviewed the projection
sketch (kept in §3b for reference) and chose to leave it out. Design as it
stands:

- **The repo board is BOTH the canonical record AND the dispatch queue.** The
  factory's picker reads `docs/dev/work/items/*.md` directly in the repo
  checkout (via the `work_items next` query below) — no projection layer, no
  second writer, no sync code at all. The single-writer question dissolves
  completely rather than being managed.
- Tasks enter the board the way they always have: the owner files them
  (typically shaped in a design session). Because the picker reads only the
  board, nothing outside it can feed the factory — dispatch of an unapproved
  task is removed by construction, the same shape as item 97 itself.
- **Factory triggers** are cron + `workflow_dispatch` only. The board file
  changing on `main` could later become a push trigger; not needed for v1.
- **Open question this scope creates (design sprint):** where failed-run state
  lives. A merged task PR updates the item file, but a FAILED run has no PR
  to ride. Candidates: a bot-committed status note on a factory branch +
  notification; an Actions artifact/cache the picker consults; or "notify
  owner + skip-list in the workflow run" (simplest). Must fail closed (a
  failed task never silently re-picked next cycle).

## 3b. The projection design (considered, not pursued — kept for the record)

The earlier analysis below survives as reference in case a forge-issue view is
ever wanted (e.g. a public roadmap). **None of it is planned work.**

**Option A — repo board canonical; GitHub Issues are a one-way PROJECTION.**

- A projector script maps ready items → issues (create/update, idempotent via an
  issue number stored in the item's `[x]` table — **note: `[x].forge` needs no
  schema change at all**, the validator already ignores it; promoting it to a
  first-class field can come later with the C-10 pass).
- **The write-back problem dissolves instead of being solved**: the per-task
  coding agent runs *inside the repo* (hook-bound) and updates the item file —
  status, `verified_by`, Updates entry — **as part of its own task commit**, so
  the board is maintained by the same PR that does the work; the issue closes via
  the PR's `Fixes #N`. No machine ever writes the board from outside a PR; the
  single-writer rule (`SCHEMA.md`: "two files agreeing... is exactly the drift
  class this schema exists to remove") is preserved by construction.
- Drift control: a freshness check comparing open projected issues against the
  board (the `wiki_freshness` / egress-allowlist dual-check pattern), run in the
  factory workflow itself — detect-and-report, not auto-correct.

**Option B — Issues canonical for dispatchable work; repo board keeps
governance/watching items.** Less sync code and native tooling, but it splits the
board into two populations (item 82's confusion class, made structural), puts
task state outside the C-11 closure bar, and makes multi-forge portability a
migration instead of a driver swap. Not recommended.

## 4. Field mapping under Option A (sketch for the design sprint)

| Board | GitHub projection | Notes |
|---|---|---|
| `id`, `title` | Issue title `[#84] <title>` | id stays canonical in-repo |
| `summary` + `refs` + brief path | Issue body | body regenerated on project; never hand-edited |
| NEW `priority` | Projects v2 Priority field (or `P1`/`P2`/`P3` labels) | schema addition — C-10 pass required |
| `depends_on` | Native issue-dependencies API (blocked-by) | shipped GitHub feature, 2026 — no label hack |
| `status = open` + ready + `decision_owner = agent` | `factory:ready` label | the picker's query |
| `status = blocked/deferred` | not projected (or `factory:hold`) | watching items not projected at all |
| `decision_owner = user` | `needs-owner` label, never dispatched | human gate |
| run failed | `attempted-failed` label + issue comment + notification | next cycle skips |
| item closed (PR merged) | `Fixes #N` auto-close | write-back-free |

**Forge portability:** keep the projector behind a thin driver interface (issues
CRUD + labels + dependencies). GitHub driver first (`gh` CLI / GraphQL); **Gitea/
Forgejo** has first-class issue dependencies (`/issues/{n}/dependencies`) and
GH-compatible Actions, so the same shape ports; **GitLab CE** (MIT core) does it
with the Issues API + CI schedules — its native blocked-by links may be
Premium-gated (UNVERIFIED; label fallback if so).

## 5. Needed changes (the concrete list)

1. **Schema:** add `priority` (proposal: int, lower = sooner, required when
   `status = "open"` and `decision_owner = "agent"`). **C-10 dossier first** —
   SCHEMA.md is gated, and consumers include `scripts/work_items.py`, the board
   generator, the closure-bar checks, and every doc that restates the field
   table. (The `[x].forge` convention is not needed — no projection in scope.)
2. **`scripts/work_items.py`:** a `next` subcommand — ready query (open,
   deps-closed, agent-owned = `decision_owner = "agent"`), priority-ordered,
   `--json` output. Deterministic, stdlib-only, testable. **This IS the
   factory's queue interface now** — the picker step calls it in the checkout.
3. **Dispatch payload convention:** how an item names its executable brief
   (a `refs` entry by convention? a dedicated frontmatter field? — design
   sprint decides; C-10 rides with the schema change above).
4. **Workflow:** `.github/workflows/factory.yml` — cron + `workflow_dispatch`
   only, `concurrency` serial group, checkout → `work_items next --json` picker
   step → `claude-code-action` step (`prompt` = brief + standing rules;
   `claude_args` restrictions; `max_turns`; job timeout) → failure step
   (notify owner + fail-closed skip marker; see §3's open question).
   Self-hosted runner on the agent station.
5. **Runner hygiene:** the runner's machine-local Claude settings must NOT carry
   `bypassPermissions` (hardening-review residue, still standing); smoke-test
   that repo hooks fire in a headless run and that the item-87 witness costs
   exactly one self-clearing retry per run.

**Out of scope (per §3):** the projector script, the projected-issues
freshness check, the issue-dependencies/Projects-v2 field mapping (§4 above
is record-only), and any forge driver interface.

## 6. Open questions for the design sprint (deliberately unanswered here)

- Priority scale + who sets it (owner-only at filing? re-prioritization flow?).
- Multi-project namespacing: one workflow per repo vs an org-level dispatcher;
  where the cross-project priority view lives.
- Per-task budget controls (`max_turns` tiers by item size? Console spend cap
  per workspace — decided: subscription first, API workspace when volume
  demands).
- What of the N=1 pipeline survives as design input (its escalation taxonomy and
  refuter/judge stages could become later factory workflow steps — or be
  deliberately dropped for v1's "implement → PR → human review" simplicity).
- Which items are grandfathered: the current 6 open / 45 watching population was
  filed without priority; the first dispatch pass needs a triage.

## 7. The board design pass (owner-flagged 2026-08-14 — a first-class work package)

The owner's call, and §1's facts back it: **the board as it stands is not ready
to carry factory dispatch**, and the design sprint owes it a dedicated pass —
not just the two field additions in §5. What that pass covers, at minimum:

- **Readiness semantics as a designed thing**, not a derived convenience:
  what exactly makes an item dispatchable (`status`, `depends_on` closure,
  `decision_owner`, priority present, brief attached — and what else?), stated
  once and enforced by `work_items check`.
- **Priority model** (scale, required-when, who sets, re-prioritization flow).
- **Dispatch payload**: how an item carries its executable brief (field vs.
  `refs` convention), and what the factory prompt assembles around it.
- **Execution-state fields**: claimed / attempted-failed / done transitions the
  factory writes through task PRs, plus the fail-closed home for failed-run
  state (§3's open question) — decided as schema, not workflow improvisation.
- **Structural debts that bite under automation**: the item-82 header
  population mix; epic nesting vs. dispatch (are epic children dispatchable
  individually?); the 97-file population triage (what gets priority, what
  stays watching).
- **The C-10 dossier** for `docs/dev/work/SCHEMA.md` covering all of the above
  in ONE enumeration pass — one schema change-set, not field-by-field edits.
