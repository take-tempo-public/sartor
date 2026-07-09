# Big-push orchestration playbook

> **Purpose:** the model-agnostic conductor guide for the merge-train pattern
> used by the 2026-07 big-push (Trains 1–5+). A fresh orchestrator session —
> any model — resumes from this file + the durable state listed in
> [`RELEASE_ARC.md`](RELEASE_ARC.md) §"Big-push scope brief". Written 2026-07-09
> after five merged trains; every rule below was learned the expensive way.
> **Companion:** the scope brief (phase/train map), `RELEASE_CHECKLIST.md`
> (ledger + train state), `AGENT_HANDOFF_TEMPLATE.md` (single-branch sessions).

---

## Roles and model assignment (owner-directed, 2026-07-09)

- **Orchestrator:** Opus. Dispatches lanes, reviews reports, assembles trains,
  talks to the owner. Never does lane work inline.
- **Lanes (feature/fix branches):** Sonnet, pinned explicitly per Agent call.
  Well-defined execution with a scope block.
- **Bulk doc/wiki synthesis:** Haiku (the `/sartor:wiki-self-update` scribes are
  already Haiku-pinned by design).
- Never let a subagent silently inherit the session model.

## Economy rules (binding — owner budget directive, 2026-07-09)

1. Lane reports capped ~300 words: branch+sha, diffstat, design bullets, gate
   numbers, deviations. No prose tours.
2. No per-lane relays to the owner; report at train level only (manifest).
3. Lane prompts cite this playbook by reference + a scope block — do not
   restate the discipline sections inline.
4. Max ONE read-only investigation agent per surprise; verify-then-build.
5. Never re-verify what a green gate already proves.
6. Spend cap: $10 cumulative API (running total in train manifests; $0.26 used
   through Train 5). Real-LLM validations only where a prompt/LLM path changed.

## Lane lifecycle

1. **Launch:** Agent tool, `isolation: worktree`, model pinned. Prompt =
   scope block (authorizing ledger/register row, file anchors, owner decisions)
   + "follow docs/dev/ORCHESTRATION_PLAYBOOK.md §Lane discipline".
2. **Quiesce:** lane commits on its named branch in its worktree, gate green,
   report delivered. A lane that died without a report: its work is judged by
   `git log`/`git status` in its worktree — commits survive; resume via
   SendMessage from the exact stopping point.
3. Lanes NEVER merge, never touch `main`, never touch the owner's e2e clone
   (`C:\Dev\sartor-e2e` — read-only for everyone, writes only on explicit
   owner instruction).

## Lane discipline (cite this section in every lane prompt)

- Create the named branch BEFORE any edit (`require-feature-branch` hook).
- Hook blocked? Surface name + message verbatim and STOP. Never bypass; never
  hand-create a checked file. (`CLAUDE_CONFIRM_MERGE=1` is orchestrator-only,
  under an owner-confirmed train.)
- **Gates run FOREGROUND.** You will NEVER receive a background-task
  notification — never end a turn waiting for one. If the harness
  auto-backgrounds a long run, block on its output file in a bounded poll loop
  until the summary line appears. Split pytest into complementary marker runs
  (`-m "not ux and not slow"` / `-m "ux or slow"`) when the 10-minute tool cap
  requires; the union must equal the full suite.
- Gate = `ruff check .` + `ruff format --check .` (format only touched files)
  + `mypy .` + `node --check static/app.js` if touched + full pytest incl. ux.
  Exactly one known-flaky Compose-class failure → isolate-re-run, report both,
  never patch code for it.
- Deterministic modules stay LLM-free (charter C-6). Prompt-text change ⇒
  PROMPT_VERSION discipline (see §Versions). Route edits keep
  `_safe_username`/`_within` visible in the edit window (route-security-lint
  scans the new_string). No new deps. Minimal targeted edits.
- Capture-before-merge: CHANGELOG entry + surgical ledger clauses ride the
  lane branch, never a post-merge follow-up.
- Frontend gotchas: UX copy is CSS-uppercased (assert case-insensitively via
  text_content()); style.css defines some selectors twice — later wins, edit
  the LIVE rule; `<option>` waits use state="attached"; never disturb
  `data-compose-ready`/`data-compose-bg-pending` or `bgDraftFiring`; config
  fields persist only via `saveConfig()`/`_collectCompositionState()`.
- DB: never `batch_alter_table` on a CASCADE parent (see
  `db/migrations/_sqlite_check_constraint.py` for the safe CHECK-swap).
- Commit message records what/why + trailer
  `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>` (or the acting
  model's name).

## Train choreography

1. **Quiesce all lanes** (reports or worktree-verified commits).
2. **Rebase chain** (one Sonnet agent): rebase lanes into a strict linear
   chain in train order (docs-only first, `app.js`-heaviest last). Union
   resolution rules: CHANGELOG stacks newest-lane-on-top above prior-train
   entries, texts byte-preserved; RELEASE_CHECKLIST clauses union, none
   duplicated/lost; `app.js`/`index.html`/`style.css`/`selectors.py` keep BOTH
   sides of adjacency conflicts; `node --check` after every app.js step;
   STOP-AND-REPORT on genuinely incompatible logic. Never `git rebase -i`.
   Conflict-marker grep clean at the end. Ancestry proof via
   `git log --pretty='%H %P'`.
3. **Versions (single-writer rule):** the chain assigns PROMPT_VERSION
   suffixes — one `.N` per prompt-changing lane, in train order, with an
   attribution comment; a lane that adds/edits prompt text but defers the bump
   gets its version assigned (and its CHANGELOG/TUNING_LOG text updated)
   inside its rebased commit. AVATAR_PROMPT_VERSION is independent.
4. **Full gate on the final tip** (foreground, same definition as lanes).
5. **Capture commit** on the final tip: ledger row resolutions/additions
   (verify the rendered `- [ ]` open count programmatically), nursery filings,
   any doc reconciles. ruff+mypy re-check for docs-only captures.
6. **Manifest to the owner** — the ONE checkpoint: train order + tips + scope
   + diffs, gate numbers, conflicts resolved, version evidence, ledger delta,
   cumulative spend, watch items, and exactly what executes on confirm.
7. **On confirm:** `CLAUDE_CONFIRM_MERGE=1 git merge --no-ff <branch>` per
   manifest order, via the Bash tool (so cleanup hooks fire) —
   `git diff --quiet main <tip>` tree-identity check — cleanup (remove lane
   worktrees, delete lane + `worktree-agent-*` branches) — re-arm the plan
   marker (`touch ~/.claude/plans/.approved`; authorized POST-TRAIN ONLY by
   the owner-approved plan's standing grant, never to unblock unapproved
   edits) — close-out report.
8. Merges to `main` and branch pruning happen ONLY inside an owner-confirmed
   train. Tags are owner-confirmed ceremonies (v1.1.0 is owner-executed).

## Known failure modes (all observed this push)

| Symptom | Response |
|---|---|
| Lane ends turn "waiting for background notification" | SendMessage: run/poll FOREGROUND from `git status`; never start a second concurrent full suite |
| Lane/agent dies on session limit or connection drop | Worktree + commits survive. Resume via SendMessage from the exact stopping point; if it died post-commit pre-report, the chain gate is its verification (+ a diff scrutiny) |
| `ruff-changed` flags files the tree-wide run ignores | Explicit-path invocation bypasses `extend-exclude` (e.g. `db/migrations/versions/`) — fix the lint, don't bypass |
| Plan-file mtime newer than `.approved` marker | Only the EnterPlanMode→ExitPlanMode ceremony refreshes it (owner click). Never hand-create outside the post-train grant |
| Two lanes bump PROMPT_VERSION to the same value | Prevented by §Versions single-writer rule |
| Owner-reported bug contradicts a green gate | Verify-first: read-only investigation; check the owner's clone version/DB state before building |

## Owner checkpoints (never automate past these)

Train confirms · tag confirms (v1.0.8, v1.0.9; v1.1.0 owner-executed) ·
PV-1 annotation session · `[HUMAN]` GitHub repo/PyPI Trusted Publisher/required
checks · any write to the e2e clone · destructive/data-rewriting scripts
(dry-run shown first) · charter/arc amendments.

## State pointer (as of 2026-07-09, Trains 1–5 merged)

Durable state: `RELEASE_ARC.md` §"Big-push scope brief" (phase/train map) ·
`RELEASE_CHECKLIST.md` (ledger; train notes) · `CHANGELOG.md` [Unreleased].
Remaining: residuals lane close → owner freeze call → assets lanes + Train 4b →
`[HUMAN]` GitHub/PyPI → v1.0.8 tag ceremony → Phase 2 (owner-gated PV-1) →
Phase 6 **FULL** (owner decision 2026-07-09: Fumadocs, diagrams-a11y,
pagedjs spike, and the mypy-strict burn all stay in v1.0.9; budget overage
accepted) → v1.0.9 tag → Phase 7 → v1.1.0 (owner act).
