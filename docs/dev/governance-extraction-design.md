# Governance extraction — design (Sprint 7.2, v1.0.7)

> **Purpose:** the settled design `feat/governance-extraction` executes against.
> Resolves the three open implementation sub-decisions from
> [`RELEASE_ARC.md`](RELEASE_ARC.md) §Phase 4.7, reconciles the pre-authored
> governance-draft against current `main`, folds in PX-23/24/27/28, and records the
> owner-directed **enforcement-portability** decision + sequencing. Produced on
> `design/governance-extraction` (the design half of 7.2); the implementation is a
> separate, later branch.
> **Audience:** the agent implementing `feat/governance-extraction`, and the owner
> reviewing the plan. Precedent for a design-branch deliverable:
> [`memory-architecture.md`](memory-architecture.md) (the design doc the
> self-documenting-loop branches build against).
> **Authoritative for:** the governance-home location, the per-doc extraction
> boundaries, the AGENTS.md shape, the cite-don't-refix drift rule, the four PX
> foldings, and the enforcement-portability decision. On conflict with an older
> plan, this doc governs for the 7.2 governance scope only.

---

## 0. What this is, in one paragraph

The 2026-06 product-excellence review named the **"mixed-doc crux"**: callback.'s
prescriptive *governance* rules (security gate, `PROMPT_VERSION` discipline, the
deterministic/LLM boundary, branch conventions, the ruff+mypy+pytest bar, API-key
rules, the v1→v2 ladder, the sign-off gate) are tangled into six *descriptive* docs.
The decision of record (`docs/wiki/pages/governance-extraction.md`, affirmed
register-grade by **F-gov-05**) is **extract, don't register-in-place**: lift each rule
into ONE canonical home (`docs/governance/`), stated once; each source doc keeps its
descriptive prose and gains a **pointer** back. The review already pre-authored the
*content* as a four-file **governance-draft** under
[`reviews/2026-06-product-excellence/03-prescriptions/`](reviews/2026-06-product-excellence/03-prescriptions/).
7.2's design job — this doc — is to resolve the open sub-decisions, drift-reconcile the
draft to current `main`, and specify the exact `feat/` file plan so the implementation
re-decides nothing.

**Load-bearing safety condition (F-gov-05).** `AGENTS.md`/`CLAUDE.md` are
harness-auto-loaded — the agent's operating instructions at session start. Extraction
MUST preserve agent rule-access via `@import`/pointer (CLAUDE.md already does
`@AGENTS.md`) **or every future agent loses its guardrails**. `AGENTS.md` stays the
entry point; it imports/links Governance, it does not surrender the rules.

---

## 1. Decisions resolved (RELEASE_ARC §4.7 sub-decisions + the portability question)

| # | Decision | Resolution | Rationale (one line) |
|---|---|---|---|
| (i) | Governance home location | **`docs/governance/`** (a directory) | Function-named (not format-named); every signal already leans here; a directory cleanly houses `charter.md` + `enforcement.md` + `metrics.md` and gives `wiki-lint` / the future compliance agent one tree to point at. Reject `raw/` (descriptive source-shed, wrong register) and root `GOVERNANCE.md` (monolith). |
| (ii) | Per-doc extraction boundaries | **§3 table** — spine is the constitution's `[src: …]` citation map | Each source doc loses only its *canonical* rule (descriptive prose stays) + gains a pointer; the draft already specifies the spans clause-by-clause. |
| (iii) | AGENTS.md shape | **Inline rules + pointer** (NOT a pure import shell) | AGENTS.md is read raw by non-Claude agents (Codex/Cursor/Aider per its own purpose statement); `@import` is a Claude-Code convention. A pure shell would leave a dangling import and strip every guardrail for non-Claude agents — a direct F-gov-05 violation. Extract-don't-restate is still honored: the charter is *binding*; AGENTS.md holds an explicitly-subordinate operational mirror. |
| — | Graduation scope | **All four draft files graduate on `feat/`** | `constitution.md`→`charter.md`, `enforcement-practices.md`→`enforcement.md`, `metrics-and-rubrics.md`→`metrics.md` (all v1.0.7-targeted in their own front-matter), and `extraction-playbook.md`→`docs/dev/EXTRACTION.md` as a low-risk one-event graduation. |
| — | Enforcement portability | **Split: decide now, migrate later** | Target architecture recorded below (§5); the two hook fixes (PX-24/28) land in place on `feat/`; the portable-core migration is a follow-on branch clustered with the v1.0.8 gate epic when the remote/CI activates (Sprint 8.7). |

---

## 2. Drift reconcile — draft (pinned `c6e0437`) vs current `main` (cite, don't re-fix)

**The most important section for the implementer.** The governance-draft was assessed
at review pin `c6e0437`; `main` has since moved (the v1.0.6 PX doc batch + Sprints
6.4/6.5/6.6/7.1 landed). **~8 of the draft's "owed corrections" already shipped.** The
`feat/` branch must **cite the already-corrected text — not re-correct it** — or it
re-introduces the very drift it is meant to retire. Verified via `git log c6e0437..HEAD`
+ grep against HEAD.

| Draft "owed correction" (clause / finding) | Status at HEAD | Implication for `feat/` |
|---|---|---|
| vision.md "the LLM cannot invent facts" absolute → C-0 reword (F-vision-02 / F-docs-03) | **LANDED** (PX-09) — vision.md:50-56 / :153 already mechanism-framed; grep for "cannot invent"/"no invention" → 0 hits | Charter C-0/C-3 `[src:]` → "already corrected; cited." **Do NOT touch grounding copy.** |
| `GROUNDING_METRIC.md` four-part-union overstatement → three-source (F-eval-04) | **LANDED** (PX-14) — doc now states the three-source union; typed edits excluded | `metrics.md` cites the corrected text; do not re-fix. |
| Chart.js runtime CDN fetch (F-vision-05 / F-sec-03) → vendor | **LANDED** (PX-01) — vendored + SRI-pinned; "no external CDN at runtime" | Charter C-2 cites as resolved. |
| dead profile/website scrape (F-docs-04) → re-wire | **LANDED** (PX-02) | Cite as resolved. |
| phantom third JD-URL egress class (F-sec-04 / F-docs-01) | **LANDED** (PX-03) — SECURITY enumerates two classes; a JD URL is provenance-only, never fetched | Two-class enumeration is canonical; charter C-2 reflects it. |
| egress falsifiability test owed (F-qe-rel-02 P0 / F-sec-01) | **LANDED** (PX-08) — `tests/test_egress_allowlist.py` | `enforcement.md` marks the egress gate **SHIPPED** (cite the test), not "ships v1.0.7." |
| hard 5-day/30-day SLAs → soften (F-qe-rel-08 / F-sec-07, D-4) | **LANDED** (PX-05/07) — SECURITY best-effort; 0 day-count hits | **Do NOT re-soften SECURITY.** (Check `CODE_OF_CONDUCT.md` separately — outside the 6-doc scope; flag if still hard.) |
| eval gate exit-2 path unguarded (PX-13) | **LANDED** | `metrics.md` cites the gate as guarded. |
| `require-feature-branch` not worktree-aware | **LANDED** | W-1: cite the worktree-local precedent that **PX-24 reuses** (`git rev-parse --abbrev-ref HEAD`). |
| C-1 loopback bind pinned by construction (F-sec-02) | **STILL-OPEN** — `app.run()` has no `host=` | Charter C-1 keeps "owed gate — **v1.0.8**" (PX-19). |
| C-6 import-boundary gate (F-arch-01 / F-qe-rel-04) | **STILL-OPEN** — no boundary test | Charter C-6 keeps "owed gate — **v1.0.8 WS-1**" (PX-20). |
| F-gov-01 block-merge misses the dominant `--no-ff` direction | **STILL-OPEN** — hook matches only `git merge … main` / `git push … origin main` | **PX-24 fixes it on THIS `feat/` branch.** |
| F-gov-07 hand-create-marker hint | **STILL-OPEN** — `check-plan-approved.sh:31-32` prints the `New-Item -Force … .approved` hint | **PX-28 removes it on THIS `feat/` branch.** |
| F-gov-03 serial-session framing | **PARTIAL** — only `RELEASE_ARC.md:390` + the hard-constraint line remain (the draft's second `~863` cite moved as the file grew) | **PX-23 retires it on THIS `feat/` branch.** |
| admitted audiences / ATS escape-hatch / single-tenant-as-value | **STILL-OPEN** | **PX-27 on THIS `feat/` branch.** |

**Implementer rule:** every graduated `[src:]` tag the draft wrote as "to be reworded /
fix the drift / owed" for a **LANDED** row must be rewritten to *"already corrected at
`<commit>`; cited here."* Only **C-1 (bind)** and **C-6 (boundary)** keep their
forward-sequenced "owed gate — v1.0.8" notes. Re-verify each cited line against HEAD
before writing it (per the project's "prescription metrics can re-stale" lesson — a
doc-accuracy figure can drift between authoring and landing).

---

## 3. Per-doc extraction boundaries (sub-decision ii)

For each source doc: the section(s) whose *canonical* rule lifts into governance
(descriptive prose stays in place) and the pointer that is added. Spine = the
constitution's `[src: …]` citation map.

### Generic pointer block (SECURITY / CONTRIBUTING / PRODUCT_SHAPE / RELEASE_ARC)
> **Canonical rule home.** The binding rules referenced in this section live once in
> [`docs/governance/`](docs/governance/) (`charter.md` + `enforcement.md`). This doc keeps
> its descriptive guidance and operational detail; on any conflict the governance home governs.

### `vision.md` — heaviest footprint
- **Lifts (canonical rule → charter):** "Self-imposed constraints" → C-1/C-2 (Local-first,
  single-tenant; Egress); D-5 (open standards) + D-1 (minimal deps); C-6 (deterministic/LLM
  boundary); the three goals → C-3/C-5/C-4; the "Grounding mechanism" block → C-3 (**already
  C-0-corrected — cite, don't edit**); the 10 Principles backbone → frozen block in charter.
- **PX-27 edits (this is also a vision.md content change, not just a pointer):**
  (a) add the ATS **escape hatch** to goal 2 — "users who want non-ATS output edit the
  document they produced"; (b) name the admitted **audiences** A-2/A-3/A-5 in "What it is";
  (c) **demote** "single-tenant *as a value*" to a threat-model statement (keep the
  single-unauthenticated-user threat model) at the "Local-first, single-tenant" heading and
  the "What's out of scope" multi-tenant bullet.
- **Pointer:** add the vision-specific block at the top of "Self-imposed constraints":
  > **Canonical governance.** The *binding* form of these constraints — the C-0…C-6 clauses,
  > the D-1…D-6 defaults, and the working-model rules — now lives in
  > [`docs/governance/charter.md`](docs/governance/charter.md). This section keeps the *why*
  > and the worked detail; the charter states each rule once and is the home audits and gates
  > read against. Where a line below restates a rule, the charter governs on conflict.

### `AGENTS.md` — inline-with-pointer (rules stay; no deletions)
Add this block immediately after the purpose blockquote:
> **Canonical governance.** The *binding* constitution — claims discipline (C-0), the
> C-1…C-6 clauses, the D-1…D-6 defaults, the parallel-session working model (W-1), and the
> amendment ceremony — lives in [`docs/governance/charter.md`](docs/governance/charter.md),
> with enforcement detail in [`docs/governance/enforcement.md`](docs/governance/enforcement.md).
> The rules restated below are the at-a-glance operational mirror every agent needs at
> session start; the charter is canonical and governs on conflict. **Do not let this file
> become a pure import shell** — non-Claude agents (Codex/Cursor/Aider) read it raw and an
> `@import` would silently drop their guardrails.

(The final sentence is self-documenting so a future "DRY" pass does not collapse AGENTS.md
into a shell.) Sections that gain a pointer-note but keep their inline rule: 10-Principles
note, deterministic-file list / P1, `PROMPT_VERSION`, the security gate, "What NOT to do",
the close-out / no-hand-create-marker / merge-confirm prose.

### `CONTRIBUTING.md`
Generic pointer for branch conventions + the PR-checklist bar + D-1. **Also replace the
stale "Step 6 of the OSS migration once landed" wording** (≈ :87) with a charter pointer.

### `SECURITY.md`
Generic pointer in Scope (C-1), Threat-model / "What it does NOT do" (C-2 — **already
two-class; cite**), Reporting (D-4 — **already soft; cite**), Security-architecture.
**Do NOT re-correct egress or re-soften SLAs.**

### `docs/PRODUCT_SHAPE.md`
Light: a pointer where the seven-functions / prescriptive ladder maps to W-2 + D-1..D-6.
Descriptive ladder content stays.

### `docs/dev/RELEASE_ARC.md`
- **PX-23:** rewrite the serial-session framing at `:390` ("strictly sequential — one branch
  at a time") to the worktree-per-session model + a pointer to charter W-1; reframe the
  hard-constraint "one branch per session" line the same way.
- Pointer at the sign-off-gate line (`:6` "Do not edit without sign-off") → charter amendment
  ceremony.
- Mark §4.7's sub-decisions **RESOLVED** (done on the *design* branch — see §6 below).

### 10 Principles
Freeze the five load-bearing principles (P1/P2/P5/P8/P9 per vision.md) into `charter.md` as
a short frozen block + a pointer to the framework; vision.md keeps the write-up + a pointer.

---

## 4. The exact `feat/governance-extraction` file plan

### CREATE
1. `docs/governance/charter.md` ← `governance-draft/constitution.md`. Strip review
   front-matter; apply §2 drift-reconcile to the `[src:]` tags; embed **PX-23** (W-1 is
   already drafted in the constitution) + **PX-27** (C-1/C-5 tiering, ATS hatch, A-2/A-3/A-5
   audiences, single-tenant→threat-model); freeze the load-bearing 10 Principles.
2. `docs/governance/enforcement.md` ← `governance-draft/enforcement-practices.md`. Strip
   front-matter; update the ship columns/order to the LANDED state (egress gate **SHIPPED**,
   Chart.js vendored, SLAs soft, eval-gate guarded); keep **PX-24 + PX-28** as this-branch
   items; keep import-boundary / UX-in-CI / bind as forward-sequenced (v1.0.8 / v1.1.0).
3. `docs/governance/metrics.md` ← `governance-draft/metrics-and-rubrics.md`. Strip
   front-matter; update §2 to cite the LANDED three-source `GROUNDING_METRIC.md` (do not
   re-fix F-eval-04). SC-1..SC-5 become the v1.1.0 tag checklist; §3 is the future compliance
   agent's standing rubric.
4. `docs/dev/EXTRACTION.md` ← `extraction-playbook.md`. Strip front-matter; light reconcile.
   (Incubant-maturity discipline; downstream of this in-repo move — keep its register.)

### EDIT (pointers + PX content)
5. `vision.md` — governance pointer + the three PX-27 content edits. **Do NOT touch the
   grounding copy (already C-0-corrected).**
6. `AGENTS.md` — inline-with-pointer block; **no rule deletions**.
7. `CONTRIBUTING.md` — generic pointer; replace the stale OSS-migration-step text.
8. `SECURITY.md` — generic pointer in Scope / Threat-model / Reporting. **No re-correction.**
9. `docs/PRODUCT_SHAPE.md` — light pointer.
10. `docs/dev/RELEASE_ARC.md` — PX-23 serial-framing rewrite + sign-off-gate pointer.

### EDIT (hooks, in place)
11. `.claude-plugin/hooks/block-merge-to-main.sh` — **PX-24**: after the existing
    `TARGETING_MAIN` detection (after the two `grep` checks), add a current-branch check —
    if `git rev-parse --abbrev-ref HEAD` is `main`/`master`, set `TARGETING_MAIN=1`. Keep the
    `CLAUDE_CONFIRM_MERGE=1` opt-in and `exit 2`. `--abbrev-ref HEAD` is worktree-local (safe
    under W-1; mirrors the landed `require-feature-branch` precedent). Closes the dominant
    `checkout main; git merge feature --no-ff` path that currently passes unblocked.
12. `.claude-plugin/hooks/check-plan-approved.sh` — **PX-28**: delete the
    `"…or for simple tasks run:"` line and the `New-Item -Force … .approved` hint (the two
    lines after `NO EDIT APPROVAL`); keep `exit 2`. The no-marker message becomes exactly
    `echo "Write a plan and call ExitPlanMode." >&2`.

### EDIT (housekeeping)
13. `CLAUDE.md` — fix the **stale hook path** ("`.claude/hooks/check-plan-approved.sh`" →
    "`.claude-plugin/hooks/check-plan-approved.sh`"; the "Once Step 4 lands, this moves to
    `.claude-plugin/hooks/`" note is now done). Optional one-line governance pointer. **Do
    NOT alter the `@AGENTS.md` import line.**
14. `CHANGELOG.md` — `[Unreleased]` → `### Added` entry for the governance home + the six
    source-doc pointers + PX-23/24/27/28, explicitly noting **"no product code / route / LLM
    call; `PROMPT_VERSION` unchanged; no dependency; no migration."**

### Order
charter → enforcement + metrics → EXTRACTION → **hook fixes early** (independent, low-risk,
and PX-24 improves this very branch's own merge safety) → the six source-doc pointers (anchors
now exist) → CLAUDE.md path fix → CHANGELOG.

### `PROMPT_VERSION`
**Not touched** — no prompts change. Stays at its current value.

---

## 5. Enforcement-portability decision + sequencing (the owner agenda item)

**Context (verified at HEAD).** The portable-capable hooks (`require-feature-branch`,
`block-merge-to-main`, `block-secrets`, `route-security-lint`, `ruff-changed`,
`validate-context`) are wired **Claude-only** in `.claude/settings.json`. CI
(`.github/workflows/ci.yml`: ruff+mypy+pytest 3-version matrix + label-gated eval-smoke)
exists but is **latent** — no git remote until Sprint 8.7, so nothing runs server-side
today. There is no `core.hooksPath` / pre-commit layer. The plan-mode lifecycle hooks
(`check-plan-approved`, `mark-plan-approved`, `cleanup-plan-on-merge`) are inherently
Claude-specific. **Today the Claude hooks are the only *active* mechanical enforcement;
non-Claude agents (Codex/Cursor/Aider) rely on `AGENTS.md` prose alone.**

**Decision: SPLIT — decide now, migrate later.**

**Target architecture (recorded; built on the follow-on branch).** One **shared portable
enforcement core** — the deterministic guard logic as plain POSIX scripts in a
tool-agnostic home — invoked by **both** (1) committed git-hooks via `core.hooksPath` (or a
pre-commit config) so the guards fire for *any* contributor or agent, and (2) the existing
Claude plugin PreToolUse wiring (earlier, richer interception), with (3) CI as the
server-side backstop once the remote lands. This is DRY enforcement mirroring DRY
governance: one `block-merge-to-main` logic (post-PX-24) becomes the single source for the
git hook, the Claude hook, and a CI branch-protection check. **Plan-mode lifecycle hooks
stay Claude-only.** Separately, the F-gov-02 global-marker collision (one global
`~/.claude/plans/.approved`) wants session/worktree-scoping — tracked with the portability
work.

**What lands now regardless:** **PX-24 and PX-28 fix the two hooks in place on `feat/`** —
narrow corrections to the existing Claude-only scripts; PX-24 even improves this branch's
own merge safety, so it must not wait.

**Sequencing — a follow-on branch, NOT this docs-shaped branch.** The portable-core
migration clusters with the **v1.0.8 gate epic**, where the import-boundary gate (PX-20),
the loopback-bind gate (PX-19), and the UX-in-CI required job (PX-25) already sit — and
where the **git remote arrives (Sprint 8.7)** to make CI non-latent. The portable core
wants to land with its sibling gates and a live backstop, not bolted onto a governance-docs
branch.

**Tradeoffs.** *Split-pro:* a clean docs+2-fix unit; portability lands with its gates + live
CI; cross-agent testing done deliberately. *Split-con:* in the 7.2→v1.0.8 window the portable
hooks stay Claude-only, so a non-Claude agent gets no `block-merge`/`block-secrets` guard —
**mitigated** precisely by keeping AGENTS.md rules **inline** (decision iii: the tribal
guardrail any agent reads) and by landing PX-24/PX-28 now (the Claude authoring path is
correct immediately). The risk is fully reversible either way.

---

## 6. What the *design* branch (`design/governance-extraction`) itself ships

Docs only — no `docs/governance/`, no source-doc edits, no hook edits (all of that is
`feat/`):

1. **This file** (`docs/dev/governance-extraction-design.md`).
2. `docs/dev/RELEASE_ARC.md` §4.7 — the "Open implementation sub-decisions" bullet replaced
   by a **Resolved (2026-06-15)** bullet pointing here.
3. `docs/dev/RELEASE_CHECKLIST.md` — 7.2 annotated *design-half complete* → pointer here;
   the deferred "Enforcement portability" item converted to **Decided 2026-06-15: split**,
   leaving the migration as a tracked follow-on for the v1.0.8 gate epic.

No CHANGELOG entry on the design branch (dev-internal planning artifact; the user-facing
CHANGELOG entry rides `feat/`).

---

## 7. `feat/` verification contract

The quality gate (`ruff && mypy && pytest`) is **docs+shell-blind** — no Python changes, and
the bash hooks are out of ruff/mypy/pytest scope — so it stays green but **does not prove the
extraction**. (Verified: only `tests/test_egress_allowlist.py` even mentions these names, in
comments; nothing asserts on AGENTS.md / vision.md / charter / hook-script content.) `feat/`
therefore adds, beyond the gate:

- **Manual hook smoke.** Run `block-merge-to-main.sh` with HEAD on `main` (expect block) and
  with `CLAUDE_CONFIRM_MERGE=1` (expect pass); run `check-plan-approved.sh` with no marker
  (expect the single-line ExitPlanMode message + `exit 2`). Hand-test with byte-correct JSON
  via a `python json.dumps` heredoc (not `echo`), per the project's hook-testing lesson.
- **Link integrity.** A `/wiki-lint` (or manual) pass confirming every new
  `docs/governance/*` pointer and every source-doc back-pointer resolves.
- `tests/test_egress_allowlist.py` is untouched and stays green.

---

## 8. Source map (where everything comes from)

| Artifact | Source (review archive) | Graduates to |
|---|---|---|
| Charter | `…/governance-draft/constitution.md` | `docs/governance/charter.md` |
| Enforcement | `…/governance-draft/enforcement-practices.md` | `docs/governance/enforcement.md` |
| Metrics & rubric | `…/governance-draft/metrics-and-rubrics.md` | `docs/governance/metrics.md` |
| Extraction playbook | `…/03-prescriptions/extraction-playbook.md` | `docs/dev/EXTRACTION.md` |
| Decision of record | `docs/wiki/pages/governance-extraction.md` | (stays — the design-rationale wiki page) |
| PX-23/24/27/28 | `…/03-prescriptions/prescriptions.md` (rows 128/129/132/133 + §v1.0.7 band) | folded into charter / enforcement / vision / hooks |
