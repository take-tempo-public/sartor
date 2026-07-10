# Compliance log

> Append-only record of [`/compliance-witness`](../../commands/compliance-witness.md)
> governance-drift runs. **Newest entry last.** Each run records the pinned-sha window,
> the per-tier flag counts (FLAG / WATCH / AFFIRM, plus withheld over the cap), and the
> gate verdict. The witness **reports; it never edits, blocks, or commits** — the
> read-only subagent is [`agents/compliance-witness.md`](../../agents/compliance-witness.md).
> Severity anchor: [`charter.md`](charter.md).

## 2026-06-16 — pilot run (`feat/compliance-agent-pilot`)

- **Window:** `e299ac8` (v1.0.6 tag) → HEAD `1741ab1`. Primary surface: the
  freshly-graduated `docs/governance/` (charter / enforcement / metrics, added 7.2).
- **Counts:** FLAG 1 · WATCH 2 · AFFIRM 3 · 0 withheld (cap 12).
- **Gate verdict:** **needs attention** (1 FLAG-tier).
- **FLAG — CW-01:** [`RELEASE_CHECKLIST.md:64`](../dev/RELEASE_CHECKLIST.md) marks Sprint
  7.2 (`feat/governance-extraction`) `[ ]` "feat/ half pending", but the branch merged
  (`2b35551`), `docs/governance/` exists at HEAD, and `CHANGELOG.md` records it landed.
  Plan vs. repo + git + changelog. Surfaced for the owner; the witness does not fix it.
- **WATCH:** CW-02 (a wiki page anticipates a `raw/` that governance-extraction merged
  without — already self-noted in [`../wiki/log.md`](../wiki/log.md)); CW-03 (an
  enforcement-vocabulary count is loose — definitional, reconcilable).
- **AFFIRM:** the charter's "lands this branch" self-claims are accurate in code/docs —
  PX-24 (`block-merge-to-main.sh`), PX-28 (`check-plan-approved.sh`), and the W-1 reframe
  (cited in `RELEASE_ARC.md`).
- **Rubric outcome (owner-scored 2026-06-16):** CW-01 = **true drift** →
  **flag-precision 1/1 = 1.0 ≥ 0.66 → pilot PASSES.** CW-01 corrected at owner direction
  (the 7.2 plan row flipped to `[x]`/DONE on this branch); the witness surfaced, the human
  decided. Per the design's Arc, a passing pilot graduates the witness toward the standing
  pre-tag companion at v1.1.x.
- **Note:** first run; the registered `/sartor:compliance-witness` surfaces on the next
  Claude Code reload — this pilot reproduced the Sonnet subagent in-session (the
  registered Task-delegated path is contract-identical).

## 2026-07-08 — pre-tag companion run (`chore/compliance-witness-2026-07-08`)

- **Window:** `44d6814` (v1.0.7 tag) → HEAD `80febb2` (189 commits). Primary surface:
  `docs/governance/`, `RELEASE_ARC.md`/`RELEASE_CHECKLIST.md`, `CHANGELOG.md`, the
  post-blueprint-split wiki, and AGENTS.md's C-6 module list.
- **Counts:** FLAG 3 · WATCH 3 · AFFIRM 6 · 0 withheld (cap 12).
- **Gate verdict:** **needs attention** (3 FLAG-tier).
- **FLAG — CW-101:** `AGENTS.md:50,167` names `docx_to_persona_html.py` as C-6-deterministic,
  but `tests/test_construction_boundary.py`'s `DETERMINISTIC_MODULES` gates only 7 modules,
  omitting it — a C-0 enforcement gap (module is clean today; the gate just doesn't check).
  New, not previously tracked.
- **FLAG — CW-102:** `charter.md:81-83,138-139` + `enforcement.md:51-52` (touched as recently
  as `f1b3193`, 2026-07-08) still mark PX-19/PX-20 "owed — v1.0.8"; both shipped Sprint 8.3a
  (`RELEASE_CHECKLIST.md:81`). Pure doc catch-up.
- **FLAG — CW-103:** `route-surface.md`, `code-module-map.md`, `diagnostics-console.md`,
  `PRODUCT_SHAPE.md` still cite `app.py` as route-bearing; it's a 297-line zero-route
  composition root post-8.3a-h. Already tracked (`RELEASE_ARC.md:1061` PX-40/PX-41, v1.0.9) —
  this run confirms the gap persists and flags its size (a whole wiki page) as worth a
  pull-forward judgment call before the v1.0.8 tag.
- **WATCH:** CW-104 (charter D-6 Chromium-classification cite stale, already fixed by PX-31);
  CW-105 (`RELEASE_ARC.md:23` top-of-doc v1.0.8 summary undersells realized scope —
  within-doc only); CW-106 (wiki `PROMPT_VERSION` cite stale but correctly hedged
  "at this ingest" per D-5).
- **AFFIRM:** `CHANGELOG.md` current with all Train 3/4 merges; `RELEASE_CHECKLIST.md`
  Carry-forward open-count (8) matches actual rendered rows; `SECURITY.md` post-split-correct;
  `tests/test_egress_allowlist.py` matches the blueprint split; `pyproject.toml` version
  correctly un-bumped pre-tag; portable-enforcement-core description matches
  `scripts/enforcement/guards/` + `.githooks/`.
- **Full findings-register table:** rendered to chat this run (not filed to a doc — no
  `output/` write, per the witness's write envelope). CW-101 is the one net-new,
  unscheduled item; CW-102/103 are known items this run reconfirms are still open.

## 2026-07-09 — pre-v1.0.8-tag ceremony run (`chore/version-bump-v1.0.8`)

- **Window:** `44d6814` (v1.0.7 tag) → HEAD `cb976cc` (223 commits). Primary surface: this
  session's 4-commit pre-tag docs stack (diagnostics round-2 capture · #14 run-health review ·
  UX Cohesion Epic + diagnostics-DX slot · version bump), cross-read against
  `docs/governance/{charter,enforcement,metrics}.md`, `RELEASE_ARC.md`/`RELEASE_CHECKLIST.md`,
  `CHANGELOG.md`, `AGENTS.md`/`CLAUDE.md`.
- **Counts:** FLAG 2 · WATCH 2 · AFFIRM 5 · 0 withheld (cap 12).
- **Gate verdict:** **needs attention** (2 FLAG-tier) — **neither blocks the v1.0.8 tag** (both
  pure doc-reconciliation drift inside this session's own docs stack).
- **FLAG — CW-107 (CLOSED this branch):** RELEASE_ARC's resume anchor still framed the GitHub
  repo push as pending (`RELEASE_ARC.md:1005/1034/1060`) while `RELEASE_CHECKLIST.md:825` recorded
  it done — and the RELEASE_ARC Phase table is what the resume protocol says to read first.
  Reconciled the three RELEASE_ARC spots on `chore/version-bump-v1.0.8` (W-1.4 single accurate home).
- **FLAG — CW-108 (CLOSED this branch):** the grounding-metric ledger row
  (`RELEASE_CHECKLIST.md:570-578`) still framed PV-2 as "awaiting the owner's annotation pass"; the
  #14 run-health review shows the pass ran (53 annotations) + surfaced the NLI/MiniCheck 100%-null
  annotate-flow persistence gap as the real blocker. Appended a `→ Update` note folding it into the
  v1.0.9 Diagnostics-DX thread.
- **WATCH:** CW-109 (wiki-staleness "219" vs 223 at the pinned sha — soft descriptive number in a row
  already deferred to `docs/wiki-refresh-v1.0.9`, self-healing there; left as-is per the witness's
  no-action call). CW-110 (stray unmerged local branches from the hook-blocked capture lane — a
  pre-close branch-prune item; the stack merges at the tag ceremony, the empty
  `docs/diagnostics-triage-capture` prunes with owner OK).
- **AFFIRM:** CW-111 (`#15` + `threaded=True` citations exact at the sha) · CW-112 (C-6 8-module
  gate incl. `docx_to_persona_html.py` — the prior CW-101 close held) · CW-113 (prior CW-102/104
  reconciles held, not re-drifted) · CW-114 (version-bump/CHANGELOG cut correct; `evals/fixtures/real/`
  gitignored) · CW-115 (ledger open-count = 7, matches the head-note).
- **Note:** run reproduced the Sonnet subagent in-session (registered `/sartor:compliance-witness`
  surfaces on reload; the Task-delegated path is contract-identical). The two FLAGs were closed on
  the branch **before** the tag (AGENTS.md pre-close sweep — reconcile drift before the merge, not
  after), not deferred.

## 2026-07-09 — Diagnostics-DX bug-fix stack pre-close witness (`fix/diagnostics-01-run-lock` @ `8a40ae8`)

- **Window:** `main` (`eb96357`) → `8a40ae8` — the four-commit unattended Diagnostics-DX bug-fix
  stack (`272f05a` #15 · `7c25e9b` #11 · `3068563` #8 · `8a40ae8` #1). 7 files touched (no
  `analyzer.py`, no `pyproject.toml`, no migrations, no new deps). Cross-read against
  `docs/governance/charter.md` (W-1, C-0, C-6), `RELEASE_ARC.md`, `RELEASE_CHECKLIST.md`,
  `CHANGELOG.md`, the diagnostics round-2 review, and `evals/runner.py` at the pinned sha.
  Delegated to the `sartor:compliance-witness` Sonnet subagent (read-only; rides the plan).
- **Counts:** FLAG 1 · WATCH 1 · AFFIRM 5 · 0 withheld (cap 12).
- **Gate verdict:** **needs attention** (1 FLAG) — a doc-reconciliation drift inside this session's
  own docs; **does not block** the (owner-gated) merge. Closed on-branch before the manifest.
- **FLAG — CW-116 (CLOSED this branch):** the carry-forward ledger + the RELEASE_ARC Diagnostics-DX
  epic section still described all 17 round-2 items as un-landed while `CHANGELOG.md` recorded 4 as
  shipped on this stack (charter **W-1** clause 4 — the ledger must be the single authoritative,
  current home). Reconciled both on the tip: `RELEASE_CHECKLIST.md` UX-round-2 row got a
  Progress note (four fixes built + shas, open subset #2–#7/#9–#10/#12–#17 + run-cancel +
  `threaded=True`), and `RELEASE_ARC.md:1167-1186` got a "Built 2026-07-09" status marker. Precedent:
  CW-107/CW-108 (same-branch close).
- **WATCH — CW-117 (tracked):** the #1 run-lock's categorical "can't deadlock locked" claim rested
  on hand-wired release at 10 sites with only the eval `_closed` path test-enforced, and
  bootstrap/grounding-score don't route through the shared streamer (forward-drift risk; verified
  correct today by direct read). Grounded the `CHANGELOG.md` #1 wording to match actual enforcement
  and filed the fold-through-streamer / extend-test hardening as a WATCH sub-note in the
  Diagnostics-DX ledger row for the epic.
- **AFFIRM:** PROMPT_VERSION discipline (no prompt text / no `analyzer.py` in the diff; `CHANGELOG`
  "no PROMPT_VERSION" accurate) · C-6 boundary (`evals/bootstrap.py` skills-parser stayed pure regex,
  no LLM call; never on the deterministic-module list) · route-security gate (both `_jd_filename()`
  call sites still behind the pre-existing `_within` containment check) · #11 root cause exact
  (`runner.py:1769` `--fixture` overrides `--suite`; `_select_fixtures` ignores `--seed`) · per-fix
  CHANGELOG capture complete (each commit carries its own dated entry).
- **Note:** the one FLAG was a pre-close capture gap, closed on the branch before the manifest per
  the AGENTS.md pre-close sweep — not deferred past the merge.
