---
status: review-artifact
evidence_sha: 4196d0c
graduation: none
---

# Area A findings — agent-process & governance DX

> Surfaces: `.claude-plugin/hooks/` (10 hooks) + `.claude/settings.json`
> wiring, plugin manifest + 12 commands + 9 subagents, session-start context
> (~40KB always-on), memory dir (88 files), the close-out ceremony.
> Finders: A1 config-surface, A2 session-tax.
>
> Area summary (A1): the config surface has a real, measured latency
> problem — 5 PreToolUse hooks fire serially on every Edit/Write at ~10.9s
> measured wall time on this machine, before any tool work happens. Version
> and permission-list drift is present but lower-value. Commands/agents
> themselves show no meaningful overlap or dead weight.

## F-adx-01 — 5 serial PreToolUse hooks on every Edit/Write cost ~10.9s measured wall time (process-spawn tax)

- **Disposition:** FIX · **Leverage:** P0 · **Simplification:** YES
- **Metric:** measured per-hook on this machine: check-plan-approved 1.6s, require-feature-branch 1.4s, block-secrets 3.5s, validate-context 2.1s, route-security-lint 2.3s = **10.9s serial per Edit/Write call** (bash spawn ~77ms, python3 spawn ~230ms; each hook shells out 1–4 python3 processes to re-parse the same stdin JSON). A session with dozens of Edit/Write calls burns minutes of pure hook overhead with zero added correctness.
- **Evidence:**
  - `.claude/settings.json:12-38` — 5 hooks wired serially on the Edit|Write PreToolUse matcher.
  - `.claude-plugin/hooks/check-plan-approved.sh:1-43` (1 python3 subprocess); `block-secrets.sh:8-26` (3 subprocesses parsing the same JSON three times); `validate-context.sh:1-62` (4); `route-security-lint.sh:1-84` (2).
- **Dedup:** distinct from ledger #5 (portable-enforcement-core = cross-tool portability of hook LOGIC) and #7 (gate hardness) — this is a dispatcher-consolidation opportunity on the current implementation, valid regardless of when the portable core lands.

## F-adx-02 — Hook timeouts (5s) sit uncomfortably close to measured runtime (up to 3.5s standalone)

- **Disposition:** WATCH · **Leverage:** P1 · **Simplification:** no
- **Metric:** block-secrets.sh measured 3.481s against its 5s timeout — a ~30% margin that machine load, antivirus, or cold cache could erase, silently turning a security/plan gate into a false pass or false block depending on the harness's timeout default.
- **Evidence:** `.claude/settings.json:17-21,26-30` (block-secrets and validate-context wired with timeout: 5 despite 3.5s/2.1s measured).
- **Dedup:** not cfg-01's serial-latency concern — this is per-hook timeout headroom/reliability, independent of merging.

## F-adx-03 — plugin.json version (1.0.6) two releases stale vs pyproject (1.0.7) and the v1.0.8-era tree

- **Disposition:** FIX · **Leverage:** P2 · **Simplification:** no
- **Metric:** 1-line bump; a visible correctness signal any agent/human reads first when orienting in the plugin.
- **Evidence:** `.claude-plugin/plugin.json:4` vs `pyproject.toml:7`; CHANGELOG [Unreleased] sits above 1.0.7 with v1.0.8 packaging work already merged.
- **Dedup:** pure manifest-field drift; orthogonal to ledger #1 (wheel packaging) and #5 (why the manifest declares no hooks).

## F-adx-04 — settings.local.json carries ~9 dead pre-rename path entries + several one-shot debug-curl allow-strings

- **Disposition:** DEBUFF · **Leverage:** P2 · **Simplification:** YES
- **Metric:** 9 of ~63 entries (~14%) reference /c/Dev/callback or callback-review (stale post-rename paths); 6 more are byte-exact one-off curl payloads that will never match again.
- **Evidence:** `.claude/settings.local.json:24,25,28,29,48,49,50,52,53` (stale paths); `:8,10,11,38,39,40` (one-off payloads).
- **Dedup:** gitignored machine-local file, so not the tracked-file absolute-path rule; plain hygiene prune not previously tracked.

## F-adx-05 — Subagent model pins mix two conventions: dated snapshots (Haiku) vs undated aliases (Sonnet)

- **Disposition:** FIX · **Leverage:** P2 · **Simplification:** no
- **Metric:** 3 Haiku agents pin claude-haiku-4-5-20251001; 6 Sonnet agents pin claude-sonnet-4-6 (no date) — the two families carry different exposure to silent model-version drift.
- **Evidence:** `agents/eval-judge.md:4`, `agents/wiki-scribe.md:4` (dated) vs `agents/compliance-witness.md:4`, `agents/git-flow.md:4` (undated).
- **Dedup:** a model-ID pin surface D-4's spirit should cover but doesn't; not in ledger/PX.

> Area summary (A2): session-start context (~10k tokens) and the close-out
> ceremony carry real, quantifiable fat. Biggest hit: CLAUDE.md's skill +
> subagent catalogs largely re-narrate what the harness auto-injects every
> session. 16 of 88 memory files are blow-by-blow logs of completed work,
> fully superseded by RELEASE_CHECKLIST.md's narrative. CLAUDE.local.md is
> doubly stale. Constraint honored throughout: AGENTS.md stays a full
> standalone contract for non-Claude agents — no import-shell proposals.

## F-adx-06 — CLAUDE.md's skill + subagent catalogs duplicate the harness's auto-injected listings

- **Disposition:** FIX · **Leverage:** P1 · **Simplification:** YES
- **Metric:** lines 101-190 = 90 of 190 lines (47%), ~4.4KB of 8.5KB, loaded every session; the harness independently injects the same skill/agent descriptions from commands/*.md and agents/*.md frontmatter at session start.
- **Evidence:** `CLAUDE.md:101-150` (skill catalog, 16 hand-maintained one-liners); `CLAUDE.md:150-190` (subagent catalog, 12 more); harness system-prompt injection observed carrying the same content sourced from frontmatter.
- **Dedup:** catalog format/duplication itself — not in PX-01..36 or ledger items.

## F-adx-07 — 16 memory files are completed-migration logs superseded by RELEASE_CHECKLIST.md

- **Disposition:** FIX · **Leverage:** P1 · **Simplification:** YES
- **Metric:** 9 app-blueprints-family + 7 kit-phase-family files = ~78.9KB (~19-20k tokens if opened); their MEMORY.md index lines (~2KB) tax the always-loaded 16.9KB index permanently.
- **Evidence:** memory `reference-app-blueprints-design.md` vs `docs/dev/RELEASE_CHECKLIST.md:82` (full 8.3a-h seam narrative); `RELEASE_CHECKLIST.md:612-765` (kit Phase 1/2 narrative) vs the 7 `reference-kit-phase*-built.md` files.
- **Dedup:** backward-looking memory bookkeeping of shipped work — distinct from ledger #7 (forward-looking kit exit criteria).

## F-adx-08 — CLAUDE.local.md gives two actively-wrong operational facts

- **Disposition:** FIX · **Leverage:** P2 · **Simplification:** no
- **Metric:** 2 of 34 lines wrong; file loads every session on this machine.
- **Evidence:** `CLAUDE.local.md:12` ("/c/Dev/callback" — path does not exist post-rename); `CLAUDE.local.md:27` (".claude/hooks/check-plan-approved.sh … moves to .claude-plugin/ once Step 4 lands" — the migration already landed; `.claude/hooks/` confirmed absent, hook lives at `.claude-plugin/hooks/`).
- **Dedup:** gitignored local file missed by the rename/plugin sprints; distinct from the tracked-file absolute-path rule.

## F-adx-09 — AGENTS.md restates the 8-file deterministic-boundary list verbatim twice

- **Disposition:** FIX · **Leverage:** P3 · **Simplification:** YES
- **Metric:** identical (reordered) list at AGENTS.md:50 and AGENTS.md:166 (~60 tokens); the boundary is machine-gated (test_construction_boundary, PX-20), so one restatement can become an in-file pointer without weakening the raw-reader contract.
- **Evidence:** `AGENTS.md:50` vs `AGENTS.md:166`; `tests/test_construction_boundary.py` (the enforcement).
- **Dedup:** in-file duplication not covered by PX/ledger; stays within AGENTS.md (no import-shell risk).

## F-adx-10 — Carry-forward ledger's "Open" head-note is an unbounded historical narrative

- **Disposition:** FIX · **Leverage:** P2 · **Simplification:** YES
- **Metric:** the line-490 head-note runs ~500+ words of chronological branch-by-branch open-count deltas — history git already holds — prepended to what every closing agent's pre-close sweep and every handoff must read; grows every branch.
- **Evidence:** `docs/dev/RELEASE_CHECKLIST.md:490` (narrative) vs `:492-509` (the terse, well-formed actual bullets).
- **Dedup:** the head-note FORMAT ballooning, distinct from F-doc-02 (the count-accuracy drift) and from the ledger's intended discipline (feedback-cumulative-open-ledger documents the discipline, not this drift).

## F-adx-11 — No unified quality-gate script: ruff/mypy/pytest as 3 manual invocations in CI and every close-out

- **Disposition:** FIX · **Leverage:** P3 · **Simplification:** no
- **Metric:** 3 separate commands (AGENTS.md:95; ci.yml:36,39,42) with zero sharing; a 1-file wrapper collapses each gate-check to one invocation, ≥1×/branch + several dev iterations.
- **Evidence:** `AGENTS.md:95`; `.github/workflows/ci.yml:36,39,42`; `scripts/` (7 utilities, none combine the triad).
- **Dedup:** narrower and immediately shippable vs ledger #5's portable-core architecture migration; neither requires nor blocks it.
