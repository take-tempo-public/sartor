# Enforcement practices — what becomes a gate, what stays witness

> **Purpose:** which load-bearing rules in [`charter.md`](charter.md) graduate to
> machine enforcement (blocker hook / witness hook / CI gate) and which stay
> best-effort, by design — and the ship state of each. Honors **C-0**: categorical
> claims are made only where a deterministic test enforces them by construction; soft
> rules describe mechanism and effort. Honors **P-3 / D-4 / E-1**: prefer machine-run
> gates that keep themselves honest over recurring human-labor obligations.
> **Audience:** contributors and agents deciding whether a rule should be a gate; the
> future compliance agent.
> **Authoritative for:** the gate/witness/tribal split and each item's ship state.
> Evidence base cited by `F-id` ([`../dev/reviews/2026-06-product-excellence/02-assessment/findings-register.md`](../dev/reviews/2026-06-product-excellence/02-assessment/findings-register.md));
> `F-id` pinned at `c6e0437`, **ship columns reconciled to current `main`.**

## The posture in one line

Three charter categoricals — **egress (C-2)**, the **deterministic–LLM boundary
(C-6)**, and **shipped-template ATS properties (C-5)** — assert "never / only / always".
C-0 says a categorical is licensed *only where a deterministic test enforces it by
construction*. So each **needs** a machine enforcer or the charter overclaims. As of
v1.0.7 the **egress gate has shipped** (PX-08); the boundary and ATS-template gates are
forward-sequenced (v1.0.8 / v1.1.0) and until each lands the honest register stays
mechanism-and-effort. Everything that depends on LLM behavior, owner availability, or
human judgement stays witness/best-effort — and that is correct, not a gap (D-4, E-1,
T-C).

## Enforcement vocabulary

- **Blocker hook** — PreToolUse, `exit 2`, refuses the action. 7 exist
  (F-gov-04, CONFIRMED).
- **Witness hook** — PostToolUse, always `exit 0`, surfaces a nudge. 3 exist; the
  wiki-freshness reminder + honest sentinel are the working amendment-ceremony precedent
  (F-gov-04, F-gov-06).
- **CI gate** — a workflow step whose non-zero exit fails the check. Today: `ruff` +
  `mypy` + `pytest` (3-version matrix) + a label-gated grounding-only eval-smoke
  (F-qe-rel-05, F-qe-rel-10). CI is committed but **latent** until the git remote
  activates (Sprint 8.7).
- **Convention-only** — documented, AST/grep-true, but no mechanism fails on a
  regression.
- **Tribal / witness-prose** — lives in `AGENTS.md`/`CLAUDE.md` or memory; relies on
  the agent reading and complying.

## The enforcement map

### A. C-0 categoricals that NEED a machine enforcer (the spine)

| Rule (charter) | Current | Recommended | Finding | Ship state |
|---|---|---|---|---|
| **C-2 egress** — telemetry never leaves; two sanctioned classes only | **committed test** (pytest-socket / allowlist on the enumerable destination set) | — (shipped) | F-qe-rel-02 **(P0)**, F-sec-01 | **SHIPPED v1.0.6/7** — [`../../tests/test_egress_allowlist.py`](../../tests/test_egress_allowlist.py) (PX-08) |
| **C-2(i) no runtime CDN** | vendored + SRI-pinned; no external CDN at runtime | — (shipped) | F-sec-03, F-docs-02, F-vision-05 | **SHIPPED v1.0.6** (PX-01 — Chart.js vendored) |
| **C-6 deterministic–LLM boundary** — "Inviolable" | convention-only; 7 modules AST-clean but no gate fails on an `import analyzer` | **CI gate**: import-linter/grimp contract *or* ~15-line AST test in the pytest job | F-arch-01, F-qe-rel-04 | **owed — v1.0.8 (WS-1, PX-20)** |
| **C-1 loopback bind** — "binds to 127.0.0.1 only" | implicit Flask default; `app.run()` has no `host=`; SERVER_NAME a silent flip vector | **CI gate / unit test** pinning the bind host (fold into the egress test) | F-sec-02 | **owed — v1.0.8 (PX-19)** |
| **C-5 ATS-safe templates** — "all the time" | template properties asserted in prose; PDF/render path browser-dependent | **CI gate**: shipped-template property assertions (single-column / plain-bullet / standard-font) inside the UX/PDF job below | F-qe-rel-01 (vehicle), C-5 trace | **owed — v1.1.0** |

Each row is a C-0 categorical in a *deterministically-enforceable* domain (network
egress, module boundary, shipped-artifact properties). C-0 makes the gate the
**condition** under which the charter is allowed to keep the absolute. Until the gate
exists, the honest register is mechanism-and-effort, not "never."

### B. New CI gates the release-pass plan adds

| Gate | What it runs | Why it must be CI, not local | Finding | Ship state |
|---|---|---|---|---|
| **UX / a11y / PDF job** | dedicated job that `playwright install chromium` + `pytest -m ux` as a **required** check | E-2 promises "machine-checked in CI, free forever"; the tier *silently skips* without a browser, so the promise is local-only | F-qe-rel-01 **(P0)**, F-expa11y-01, F-expa11y-05 | **owed — v1.1.0** |
| **Egress falsifiability** | socket/allowlist test (row A) | makes C-2 falsifiable; would have caught the CDN fetch | F-qe-rel-02 **(P0)** | **SHIPPED** (PX-08) |
| **Import-boundary** | import-linter contract / AST test (row A) | makes C-6 fail-closed | F-arch-01, F-qe-rel-04 | **owed — v1.0.8** |
| **E-2 machine badges** | Dependabot + lockfile, OpenSSF Scorecard, REUSE/SPDX lint, one-time PVR | E-1 prefers machine-run measures *because they keep themselves honest*; none exist yet | F-qe-rel-03, F-sec-08, F-sec-09 | **owed — v1.1.0** |

The eval-quality regression gate already in CI (`REGRESSION_DELTA` → exit 2 → fails
eval-smoke) is a **KEEP** — affirm and protect it; the exit-2 path is itself guarded
(PX-13). It covers the grounding rubric across 3 synthetic fixtures only, not the full
matrix, and runs only on the `eval` label (F-qe-rel-05). Real-corpus coverage is
sequenced (PV-1/PV-2), not silently assumed (F-qe-rel-07, WEAKENED).

### C. Blocker-hook corrections (existing gates that are wrong)

| Fix | What | Finding | Ship state |
|---|---|---|---|
| **F-gov-01 — block-merge direction** | `block-merge-to-main.sh` matched `git merge … main` and `git push … origin main`, but the **dominant** path — checkout `main`, then `git merge feature --no-ff` — names the branch, not "main", and passed unblocked. Fix: a current-branch check — if `git rev-parse --abbrev-ref HEAD` == `main`/`master`, require `CLAUDE_CONFIRM_MERGE=1`. (`--abbrev-ref HEAD` is worktree-local — safe under W-1, per F-gov-02.) Witness-class, narrow; no new prose. | F-gov-01 (P1, CONFIRMED) | **lands this branch — PX-24** |
| **F-gov-07 — remove the contradictory hand-create hint** | `check-plan-approved.sh` printed `New-Item -Force … .approved`, teaching the agent to hand-create the very marker the never-hand-create rule forbids (AGENTS.md + memory). DEBUFF: delete those hint lines; the failure message says "Write a plan and call ExitPlanMode." and stops. The fix is *removing* an instruction, not adding enforcement. | F-gov-07 (DEBUFF) | **lands this branch — PX-28** |
| **route-security-lint scope** | hook is `app.py`-only; dark on blueprints. Extend the matcher when blueprint routes land (already a RELEASE_ARC task); scope SECURITY.md to app.py-resident routes. **Not** load-bearing today (the one blueprint route is localhost-gated, read-only, builds no path from input). | F-arch-03 (WEAKENED → P2/P3), F-sec-05 | **owed — v1.0.8** |

### D. Rules that stay witness / best-effort by design (do NOT gate)

| Rule | Enforcement | Why it stays soft |
|---|---|---|
| Vulnerability / conduct response time | **best-effort prose** — `SECURITY.md` + `CODE_OF_CONDUCT.md` state no guaranteed timeline | D-4 bans day-count SLAs and recurring human-labor promises; a gate here would tax the owner's life (F-qe-rel-08, F-sec-07). **Already softened in v1.0.6 (PX-05/07)** — cited as done, do not re-soften |
| Wiki freshness | **witness hook** (always exit 0) + honest sentinel | an ingest costs LLM tokens; a human decides when to pay. The freshness reminder is the amendment-ceremony precedent (F-gov-06), not a gate |
| Grounding strictness / no-invention | **prompt mechanism + witness metric** (`grounding_overlap`), never a categorical | C-0 bars LLM-behavior absolutes; the metric *measures*, it does not enforce by construction. The absolute "the LLM cannot invent facts" copy was struck in v1.0.6 (PX-09, F-vision-02/F-docs-03). Over-suppression is uninstrumented (F-eval-01) — instrument as a witness signal, not a gate |
| Parallel-session isolation (W-1) | **written governance + worktree-local hooks** | codify worktree-per-session / global-state ownership as *prose governance* (charter W-1) + make the plan hooks worktree-scoped; the collisions are real (F-gov-02) but the remedy is a written rule + per-session scope, not a blocker (F-gov-03) |
| Close-out sweep / handoff / carry-forward ledger | **tribal (AGENTS.md) — keep tribal** | judgement-shaped, no clean deterministic predicate; honestly separated from the enforced set today (F-gov-04). The cumulative open-ledger discipline (charter W-1.4) is a written rule, not a gate — do not manufacture a brittle predicate |
| New-dependency justification, PROMPT_VERSION bump | **convention + witness** | `ruff-changed` blocks lint, but the "couldn't be done in pure Python" and version-bump rules stay reviewer-judgement; gating them invites false positives |

## Why the split is principled, not lazy

The dividing line is **C-0's own test**: *can a deterministic check enforce this by
construction?* Egress, module boundary, bind host, and shipped-template properties —
**yes**, so they graduate to gates and the categorical earns its keep. LLM grounding,
owner availability, agent close-out judgement — **no**, so they stay witness/prose and
the honest register is mechanism-and-effort (P-3). Same logic E-1/T-C already resolved:
machine-run measures may be inviolable *because they keep themselves honest*;
human-promise measures stay best-effort *because a hard promise becomes an obligation
that consumes its owner* (D-4). Proposing a recurring human SLA as a hard commitment
would itself violate the charter.

## Implementation status (so this maps cleanly)

The v1.0.7 governance slice, with current ship state:

1. **F-gov-07** — delete the `check-plan-approved.sh` hand-create hint. **This branch
   (PX-28).** One-line-class, no risk.
2. **F-gov-01** — add the `HEAD == main` branch check to `block-merge-to-main.sh`.
   **This branch (PX-24).** Witness-class, worktree-local.
3. **Egress falsifiability test** (F-qe-rel-02 P0) — committed socket/allowlist test;
   **SHIPPED** in the v1.0.6 batch (PX-08), landed after PX-01 vendoring so the suite
   stays green. Pinning the loopback bind in the same test (F-sec-02) is **owed —
   v1.0.8**.
4. **D-4 softening** (F-qe-rel-08, F-sec-07) + disclosure-channel fix (F-sec-11) —
   **SHIPPED** in v1.0.6 (PX-05/07).
5. Forward-sequenced: **import-boundary gate** (F-arch-01, v1.0.8), **loopback-bind
   gate** (F-sec-02, v1.0.8), **UX/a11y/PDF required CI job** (F-qe-rel-01 P0, v1.1.0),
   **E-2 machine badges** (F-qe-rel-03, v1.1.0).

The two hook corrections on this branch (PX-24/PX-28) are narrow edits to existing
Claude-only scripts; the **portable-enforcement-core migration** — lifting the portable
guards into a tool-agnostic shared core invoked by both committed git-hooks and the
Claude plugin, with CI as the server-side backstop — is **decided (split) and deferred**
to the v1.0.8 gate epic when the remote/CI activates (charter W-1; design §5;
[`../dev/RELEASE_CHECKLIST.md`](../dev/RELEASE_CHECKLIST.md) Carry-forward ledger).
