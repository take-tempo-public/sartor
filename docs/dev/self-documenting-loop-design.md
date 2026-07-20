# Self-documenting wiki loop — design (Sprint 7.3, v1.0.7)

> **Purpose:** the settled design `feat/self-documenting-wiki` executes against.
> Settles the three the arc names — **trigger / cost / scope** — plus the
> orchestration shape, the autonomy / human-gate boundary, and the trust model, for
> the **autonomous self-documenting / self-tuning docs loop** named in
> [`RELEASE_ARC.md`](RELEASE_ARC.md) §Phase 4.7. Produced on
> `design/self-documenting-loop` (the design half of 7.3); the implementation is a
> separate, later branch.
> **Audience:** the agent implementing `feat/self-documenting-wiki`, and the owner
> reviewing the plan. Precedent for a design-branch deliverable:
> [`governance-extraction-design.md`](governance-extraction-design.md) (the 7.2 design
> half, whose 8-section shape this mirrors) and
> [`memory-architecture.md`](memory-architecture.md) (the shared `recall/` substrate
> this loop rides at the conceptual level).
> **Authoritative for:** the trigger model, the cost envelope, the `docs/wiki/`-only
> scope boundary, the orchestrator + two-subagent artifact set, the never-auto-commit
> rule, and the deterministic-backstop trust model. On conflict with an older plan,
> this doc governs for the 7.3 self-documenting-loop scope only; it defers to
> [`RELEASE_ARC.md`](RELEASE_ARC.md) §4.7 and [`memory-architecture.md`](memory-architecture.md)
> for the surrounding arc.

---

## 0. What this is, in one paragraph

[`RELEASE_ARC.md`](RELEASE_ARC.md) §4.7 names a **design-first** row: the **autonomous
self-documenting / self-tuning docs loop** — the wiki ingests + lints itself on change
"so the docs track the code without a human author," but **performant and not
overdone**: a **Haiku-class** model, **bounded triggers (not per-commit)**, cost-aware.
The arc is explicit that "the design pass settles trigger / cost / scope before any
build." The capability is **already three composable primitives** —
[`/wiki-ingest`](../../commands/wiki-ingest.md) (diff-driven synthesis),
[`/wiki-lint`](../../commands/wiki-lint.md) (deterministic structural check, no LLM), and
[`/wiki-audit`](../../commands/wiki-audit.md) (adversarial per-page grounding) — plus a
**witness trigger substrate**,
[`wiki-freshness-reminder.sh`](../../hooks/wiki-freshness-reminder.sh)
(commit-time, always-exit-0 nudge). 7.3's design job — this doc — is to **bound and
sequence** those primitives into a loop that runs Haiku at steady state against
[`SCHEMA.md`](../wiki/SCHEMA.md) + baked-in exemplars + the deterministic backstop, so
the later `feat/` branch re-decides nothing. **It invents little; it composes and bounds
what exists.**

**The loop is a Claude Code dev-harness capability, not product code.** It is an
orchestrator command + two model-pinned subagents that *compose* the existing `/wiki-*`
ops — exactly the shape of the sibling `feat/compliance-agent-pilot` (a command + a
read-only subagent composing existing primitives,
[`compliance-agent-design.md`](reviews/2026-06-product-excellence/03-prescriptions/compliance-agent-design.md)).
It adds **no product route, no Python dependency, no `PROMPT_VERSION` concern**, and
**does not touch the C-6 deterministic/LLM boundary** ([`charter.md`](../governance/charter.md)
C-6): its LLM calls are the Claude Code agent running a skill, exactly as the existing
`/wiki-ingest` op already does — they never enter `hardening.py`/`analyzer.py`/the
product modules.

**Load-bearing safety condition.** The wiki is **committed history**
([`SCHEMA.md`](../wiki/SCHEMA.md) "What this wiki is"). The Haiku synthesis is the
"unreliable narrator" the wiki's one grounding rule guards against
([`SCHEMA.md`](../wiki/SCHEMA.md) "The one grounding rule"); **trust lives in the
deterministic layer below the small model** ([`memory-architecture.md`](memory-architecture.md)
Thesis #1: "the small model reads + phrases; trust lives in the deterministic layer
below it"). Therefore the loop produces a **reviewable diff, never a silent push**:
autonomy is in *synthesis/execution*; the **spend boundary and the commit boundary stay
human-gated.**

---

## 1. Decisions resolved (the three the arc names + orchestration + autonomy)

Owner-confirmed 2026-06-16 at the recommended defaults (Trigger / Auto-commit / Auditor).

| # | Decision | Resolution | Rationale (one line) |
|---|---|---|---|
| (A) | **Trigger** | **Bounded-checkpoint convention** (branch close-out + pre-tag) as primary; the **freshness witness hook escalates its message** past a drift threshold (secondary); **no scheduler** | Mirrors [`/wiki-lint`](../../commands/wiki-lint.md)'s designated "periodic + pre-release gate" and the compliance-agent's per-release cadence; a cron has no precedent and removes the human from the spend boundary ([`enforcement.md`](../governance/enforcement.md) §D: "a human decides when to pay"). |
| (B) | **Cost** | **Haiku steady-state**, **diff-scoped**, **warm-start exemplars** (never re-runs the cold pass), **cost surfaced before spend**, **per-run page cap** | A typical diff pass touches 1–4 pages ([`log.md`](../wiki/log.md): 1 / 4 / 2); the from-scratch taxonomy + synthesis-boundary calls stay the capable cold pass (WS-4b, 16 pages), which the loop never repeats. |
| (C) | **Scope** | **`docs/wiki/`-only**: diff-pass ingest → pages/index/backlinks → advance `.last_ingest_sha` → log; deterministic `/wiki-lint`; Haiku adversarial audit on changed pages; surface DRIFTED/UNSUPPORTED | Does NOT touch: cold re-ingest, governance/contract-doc link-checking (the **separate** tracked follow-on — [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md) Carry-forward Open #4), product code, root `CHANGELOG.md`. |
| (D) | **Orchestration** | **New `/wiki-self-update` orchestrator command** (not an `--auto` mode of `/wiki-ingest`); a **Haiku `wiki-scribe` subagent** for per-page synthesis; a **separate Haiku `wiki-grounding-auditor` subagent** (author≠auditor); **exemplars by-reference** (name canonical pages, no new file); [`/wiki-lint`](../../commands/wiki-lint.md) reused as the no-model structural gate | Commands cannot pin a model (frontmatter keys: `description`/`argument-hint`/`allowed-tools`) → a Haiku steady-state pass **must** be a model-pinned subagent an orchestrator delegates to (the [`tune-from-annotations`](../../commands/tune-from-annotations.md)→[`tune-drafter`](../../agents/tune-drafter.md) pattern). |
| (E) | **Autonomy boundary** | **Autonomous synthesis + deterministic gate + adversarial gate; human-gated at spend and at commit.** The loop **never auto-commits** in the default build; UNSUPPORTED findings surfaced, never auto-deleted | [`AGENT_FAILURE_PATTERNS.md`](AGENT_FAILURE_PATTERNS.md) 5c (user-visible changes surfaced as a plan BEFORE the edit); [`/wiki-audit`](../../commands/wiki-audit.md)'s "never silently rewrite committed history"; the witness posture. |
| (F) | **Self-eval** | **Track auditor catch-rate across the first ~3 runs as a tuning signal — NOT a hard gate** | The loop's trust is *structural* (`/wiki-lint` + the auditor are the trust layer, and a human reviews every diff), not a precision score; a hard rubric isn't load-bearing for correctness (contrast the compliance agent, whose only output *is* judgment). |

---

## 2. The trigger model — "autonomous" reconciled with "a human decides when to pay"

**The largest reconciliation, and the section the §4.7 mandate most depends on.** The
arc demands the loop be **autonomous** *and* **bounded, cost-aware, with the human at
the spend boundary**. These are reconciled by **splitting "autonomous" across two
boundaries**:

- **Autonomous in synthesis + execution.** Once authorized, the loop selects the changed
  files, drafts each affected page, reconciles `index.md` + `[[backlinks]]`, runs the
  structural + grounding gates, classifies drift, and produces the finished diff — **with
  no human authoring.** That is the "without a human author" the §4.7 row names.
- **Bounded + human-authorized at the trigger/spend boundary, and again at the commit
  boundary.** An ingest costs LLM tokens; per
  [`enforcement.md`](../governance/enforcement.md) §D and the freshness-hook header, *a
  human decides when to pay.* The loop is **invoked**, never self-firing.

### Options evaluated

| Option | Verdict | Reasoning |
|---|---|---|
| **A1 — bounded-checkpoint convention** (branch close-out + pre-tag) | **PRIMARY** | Direct parallel to [`/wiki-lint`](../../commands/wiki-lint.md)'s designated "periodic + pre-release gate" and the compliance-agent's two deliberate triggers (per-release-tag + on-demand). A close-out / pre-tag is exactly when code-vs-docs has had a sprint's worth of chances to drift and when the spend is justified by a coherent unit of change. Realized as a [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md) line ("run `/wiki-self-update` before the version-bump") + on-demand invocation — **not** a hook that fires it. |
| **A2 — accumulated-drift escalation in the freshness hook** | **ADOPT as the secondary nudge** | [`wiki-freshness-reminder.sh`](../../hooks/wiki-freshness-reminder.sh) already counts tracked files changed since `.last_ingest_sha`, is silent under the sentinel, and is silent when nothing changed (the F-gov-06 honest-witness precedent). It **stays a witness (always exit 0)**; the only change is its *message* tiers — below the threshold, the current "consider `/wiki-ingest`" copy; at/above it, "the diff is large enough to run the loop — consider `/wiki-self-update`." It **informs** the human's spend decision; it does **not** invoke the loop. The named amendment-ceremony precedent (the freshness reminder + honest sentinel, [`charter.md`](../governance/charter.md) Amendment ceremony) is preserved unchanged. |
| **A3 — scheduler / cron** | **REJECT** | No scheduler exists in the repo; no precedent. A timer fires regardless of whether code changed → pays tokens on no-op windows (the time-domain form of the "per-merge noise" the compliance design rules out). It removes the human from the spend boundary, directly clashing with the witness posture — [`charter.md`](../governance/charter.md) C-0 bars LLM-behavior categoricals and D-4 bars recurring-human-SLA hard commitments, and a standing cron is the machine equivalent of a standing obligation to pay. The latent GitHub CI (active at Sprint 8.7) is the *only* future automation surface, and even there the loop should be a **reporting/diff** step, never an auto-committing one. |

**Resolution.** Primary trigger = **bounded checkpoint** (a `RELEASE_CHECKLIST` convention
+ on-demand `/wiki-self-update`). The **freshness hook stays the witness** that tells the
human *when the spend is worth it*, escalating its copy past a drift threshold. **The loop
never fires itself.**

---

## 3. Cost model + scope boundary

### Cost model (B)

| Lever | Design |
|---|---|
| **Model** | **Haiku** at steady state, pinned on the scribe + auditor subagents (`model: claude-haiku-4-5-20251001`, as [`eval-judge.md`](../../agents/eval-judge.md) does). The from-scratch taxonomy / synthesis-boundary calls stay the **capable cold pass** (WS-4b), which the loop **never repeats**. |
| **Diff-scoping** | Only files in `git diff --name-status <.last_ingest_sha> HEAD` (the [`/wiki-ingest`](../../commands/wiki-ingest.md) diff-pass mechanic), excluding `docs/wiki/` itself. |
| **Warm-start exemplars** | The WS-4b pages are the baked-in few-shot exemplars — **referenced, not copied** (§4). The scribe reads 2–3 canonical pages as worked examples of the SCHEMA conventions, so it never re-derives the page taxonomy. |
| **Cost surfaced before spend** | The orchestrator surfaces the changed-file list + affected-page estimate **before** synthesizing — the [`/wiki-ingest`](../../commands/wiki-ingest.md) "Surface the scope before you start — like `/eval`" precedent. |
| **Per-run page cap** | A page cap (mirror the compliance agent's load-bearing output cap). If a diff would touch more than the cap, the orchestrator **stops and asks** the human to scope down or fall back to the capable cold/manual pass — an oversized diff is a signal the change isn't a steady-state increment. |

**Cost-envelope reasoning.** A typical diff pass touches **1–4 pages** — the
[`log.md`](../wiki/log.md) record: Chart.js refresh = 1 page; v1.0.6 PX band = 4;
Sprint 6.5 education = 2. Each page is one Haiku read (changed source + the page + 2–3
exemplars → a surgical edit) plus one Haiku adversarial re-read (the audit). That is a
small, bounded, per-page token cost — the basis for "bounded, cost-aware autonomy." The
cold pass (whole-repo, chunked per module, 16 pages) is categorically more expensive and
is exactly what the warm-start strategy keeps off the steady-state path.

### Scope boundary (C)

| The loop DOES | The loop DOES NOT |
|---|---|
| Diff-pass ingest into `docs/wiki/pages/` (create/update affected pages per SCHEMA) | Cold re-ingest / from-scratch taxonomy / synthesis-boundary calls (stay the capable cold pass) |
| Reconcile [`index.md`](../wiki/index.md) + bidirectional `[[backlinks]]` | Touch the root [`CHANGELOG.md`](../../CHANGELOG.md) (the `/wiki-ingest` rule: `log.md` is the wiki changelog, not CHANGELOG) |
| Advance [`.last_ingest_sha`](../wiki/.last_ingest_sha) to HEAD on a successful pass | Governance-doc / contract-doc `[text](path)` link-checking — the **separate** tracked follow-on ([`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md) Carry-forward **Open #4**, cross-document link/cite checker); the loop is `docs/wiki/`-scoped only |
| Run the deterministic [`/wiki-lint`](../../commands/wiki-lint.md) structural backstop | Restate canonical rules from `AGENTS.md`/`CLAUDE.md`/`vision.md` ([`SCHEMA.md`](../wiki/SCHEMA.md) D5 — referenced, never duplicated) |
| Run the Haiku adversarial audit on changed pages | Auto-delete or silently rewrite an UNSUPPORTED claim |
| Surface DRIFTED (offer re-anchor) + UNSUPPORTED (human decision) | Any product code, route, dependency, or `PROMPT_VERSION` bump |
| Append a dated run entry to [`log.md`](../wiki/log.md) | Build a portable-enforcement-core, a scheduler, or any 7.4–7.7 substrate |

---

## 4. The exact `feat/self-documenting-wiki` file plan (D)

### CREATE — orchestrator command

**`commands/wiki-self-update.md`** — a **new orchestrator command**. Frontmatter mirrors
the existing wiki commands (`description`, `argument-hint: [--since <sha>] [--cap <N>]`,
`allowed-tools: [Bash, Read, Edit, Write, Grep, Glob, Task]` — `Task` is the only
addition, for subagent delegation). Body (prose, no code): (1) resolve the diff window
off `.last_ingest_sha`→HEAD; **surface the changed-file list + page estimate + cost
before synthesizing** (the `/wiki-ingest` discipline); enforce the per-run page cap;
(2) **delegate per-changed-page synthesis to `wiki-scribe`** via `Task`; (3) **delegate
the per-changed-page grounding audit to `wiki-grounding-auditor`** via `Task`
(author≠auditor); (4) **run the deterministic `/wiki-lint` structural gate**; (5)
reconcile `index.md`/backlinks, advance `.last_ingest_sha`, append to `log.md`; (6)
**present the finished diff for human review — do not commit** (§5). This is the
orchestrator-delegates-to-subagent-in-prose pattern of
[`tune-from-annotations.md`](../../commands/tune-from-annotations.md)→[`tune-drafter`](../../agents/tune-drafter.md).

> **Argument — new command, not `--auto` on `/wiki-ingest`.** [`/wiki-ingest`](../../commands/wiki-ingest.md)
> owns the from-scratch cold/diff **author** path and its frontmatter cannot pin a model.
> An `--auto` flag would entangle the cold-pass-capable op with a Haiku steady-state
> delegation, blur "the loop never repeats the cold pass," and force the model split into
> one command that cannot express it. A thin **new orchestrator** that *composes* the
> primitives keeps `/wiki-ingest` exactly as-is (the capable cold author) and isolates the
> loop's bounded steady-state behavior — consistent with the compliance-agent
> "command + subagent composing existing primitives" template.

### CREATE — model-pinned subagents

**`agents/wiki-scribe.md`** — Haiku subagent, `model: claude-haiku-4-5-20251001`, tight
tool grant `tools: [Read, Grep, Glob, Edit]` (no `Write` of new infra, no `Task`, no
broad `Bash` — kept tight like [`eval-judge.md`](../../agents/eval-judge.md) /
[`tune-drafter.md`](../../agents/tune-drafter.md)). System prompt: given one changed
source + its affected page(s) + the named exemplars, produce the **minimal
SCHEMA-conformant page edit** (one-concept, kebab slug, `[[backlinks]]`,
`path:line`/symbol cites preferred over bare line numbers, `[synthesis]` tags), holding
the one grounding rule. Work from the file **at HEAD, never from memory** (the
`prompt-archaeologist` / `tune-drafter` discipline).

**`agents/wiki-grounding-auditor.md`** — Haiku subagent, `model: claude-haiku-4-5-20251001`,
**read-only tool grant `tools: [Read, Grep, Glob]`** (the grant *is* the enforcement of
"never silently rewrite," exactly as the compliance subagent's read-only grant enforces
its non-goals). Per changed page: quote-match each `path:line` cite + each `[synthesis]`
claim against source at HEAD; classify **SUPPORTED / DRIFTED / UNSUPPORTED**; return the
classification to the orchestrator. **Does not edit** — re-anchoring DRIFTED and
surfacing UNSUPPORTED are the orchestrator's human-gated steps.

> **Argument — separate auditor subagent vs reuse `/wiki-audit`** (owner-confirmed:
> separate). It realizes the WS-4b **author≠auditor** discipline that caught drift on
> **8 of 16** cold-pass pages ([`log.md`](../wiki/log.md) 2026-06-13: the scribe must not
> grade its own synthesis); it can be **Haiku-pinned** where the [`/wiki-audit`](../../commands/wiki-audit.md)
> *command* cannot; and the orchestrator can fan it out per-changed-page in one run.
> [`/wiki-audit`](../../commands/wiki-audit.md) the **command remains** the human's
> on-demand single-page deep tool.

### Exemplars — by reference, no new file

**No new exemplars file.** The orchestrator + scribe **name 2–3 canonical existing pages
by reference** as the few-shot set (candidates: [`pages/route-surface.md`](../wiki/pages/route-surface.md)
and [`pages/deterministic-llm-boundary.md`](../wiki/pages/deterministic-llm-boundary.md) —
dense `path:line`/symbol cites, clean `[[backlinks]]`, correct `[synthesis]` tagging; both
authored **and** audited in WS-4b). Rationale: **no duplication / git-as-engine ethos** —
copying pages into an exemplars artifact creates a second copy that rots (the same
`raw/`-at-zero, "don't copy a live git-tracked doc" discipline in
[`SCHEMA.md`](../wiki/SCHEMA.md) "The `raw/` constitutional layer"). The exemplars are the
committed pages themselves, cited by slug. (Exactly which 2–3 pages is a §H knob.)

### EDIT — the freshness hook (witness escalation only)

**`hooks/wiki-freshness-reminder.sh`** — add a **threshold escalation** to
the existing `CHANGED` count: below the threshold, the current "wiki may be stale… consider
`/wiki-ingest`" copy; at/above it, escalate to "consider running the loop
(`/wiki-self-update`)." **Stays always-exit-0, silent under the sentinel, silent when
nothing changed** — the witness posture is unchanged; only the message tiers. (Threshold
number is a §H knob.)

### EDIT — discoverability / registration

- **`CLAUDE.md`** "Skill catalog" + "Subagent catalog" and **`README.md`** plugin section —
  register `/wiki-self-update` + the two subagents (the 7.1 activation pattern: components
  live at the plugin root `commands/`/`agents/`, default scan, namespaced `/sartor:…` and
  `sartor:…`).
- **[`docs/wiki/SCHEMA.md`](../wiki/SCHEMA.md)** "Ops" — add `/wiki-self-update` to the named
  ops (currently read/query/ingest/lint/audit) and note the bounded-checkpoint trigger.
- **[`docs/dev/RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md)** — add the pre-tag "run
  `/wiki-self-update`" convention line to the release discipline.

### Order

scribe + auditor subagents → orchestrator command (it delegates to them) → freshness-hook
escalation → SCHEMA/CHECKLIST/CLAUDE/README discoverability.

### `PROMPT_VERSION`

**Not touched** — no product prompts change. (The loop's prompts live in the dev-harness
command/subagent `.md` files, not in `analyzer.py`.)

---

## 5. Autonomy / human-gate boundary (E) + the never-auto-commit sequencing

**What is autonomous:** changed-file selection, per-page Haiku synthesis, backlink/index
reconciliation, the deterministic structural gate, the adversarial grounding gate, the
DRIFTED/UNSUPPORTED classification, and the `log.md` entry — all **without a human
author.**

**What stays human-gated (three gates):**
1. **Spend.** Cost is surfaced before synthesis; the human authorizes the run (the
   `/wiki-ingest` + `/eval` precedent; the witness "human decides when to pay").
2. **Commit.** The loop's output **lands as a reviewable diff, not a silent push.** The
   wiki is committed history; per [`AGENT_FAILURE_PATTERNS.md`](AGENT_FAILURE_PATTERNS.md)
   5c, user-visible changes are surfaced *before* they land in history. The default build
   **does not auto-commit.**
3. **UNSUPPORTED findings.** Surfaced for human decision, **never auto-deleted** (the
   [`/wiki-audit`](../../commands/wiki-audit.md) "never silently rewrite committed history"
   rule — an unsupported claim may signal a real code/doc change worth tracing).

**Should the loop ever auto-commit? Not in the default build** (owner-confirmed). A
possible *future, narrow* exception — recorded here as **decide-now / migrate-later**, the
same shape the 7.2 design used for enforcement-portability, and **not built now**:
auto-commit could be weighed **only** when **all** of (a) `/wiki-lint` returns zero ERROR,
(b) the auditor returns **zero DRIFTED and zero UNSUPPORTED** (a pure-SUPPORTED pass), (c)
the diff is within the per-run cap, and (d) it runs on a dedicated branch under an explicit
`--auto-commit` opt-in (the `CLAUDE_CONFIRM_MERGE`-style precedent). Even then a human
reviews the branch before merge. The natural home to weigh it is **alongside the Sprint-8.7
CI activation**, where a server-side backstop exists to make any automation honest. The
conservative default — **always produce a diff for review** — is the recommended ship, and
the only thing `feat/self-documenting-wiki` builds.

---

## 6. The deterministic backstop & trust model (F)

The Haiku synthesis is the **unreliable narrator**; trust does **not** live in it. Two
layers beneath it are the trust model:

- **[`/wiki-lint`](../../commands/wiki-lint.md) (deterministic, no LLM judgment)** —
  staleness (`.last_ingest_sha` vs HEAD), `[[backlink]]` resolution, `path:line` existence,
  orphans, index↔pages agreement, coverage. This is the **structural gate** that needs no
  model and cannot itself hallucinate — the "trust lives in the deterministic layer below
  the small model" ([`memory-architecture.md`](memory-architecture.md) Thesis #1) realized
  for the wiki.
- **The Haiku auditor (the [`/wiki-audit`](../../commands/wiki-audit.md) discipline,
  author≠auditor)** — quote-matches each claim against source at HEAD and classifies; the
  **falsification step** that keeps a synthesis error from silently becoming a "fact"
  ([`SCHEMA.md`](../wiki/SCHEMA.md) "The one grounding rule"; the WS-4b discipline that
  caught drift on 8/16 pages).

Together they are the trust layer beneath Haiku synthesis: **a small model writes, a
deterministic check and an adversarial check falsify, and a human reviews the diff.**

**Does the loop need a compliance-style precision rubric?** **Lightly, as a tuning signal —
not a hard gate.** The compliance agent needs a ≥0.66 precision rubric because it is a *pure
witness whose only output is judgment* (a noisy witness is its whole failure mode). The loop
is different: its trust is **structural** (lint + audit are deterministic/adversarial
checks, and the human reviews every diff), so a numeric precision gate is not load-bearing
for correctness. **Recommendation:** track the **auditor catch-rate** (DRIFTED+UNSUPPORTED
caught per run) across the first ~3 runs as a calibration signal — if the auditor stops
catching drift that the human review then finds, that is the signal to retune the scribe —
but **do not block the loop on a threshold.** Whether to harden this into a formal rubric is
a §H knob.

---

## 7. What the *design* branch ships + the `feat/` verification contract

### What `design/self-documenting-loop` ships (docs only)

No command, no subagent, no hook edit — all of that is `feat/`:

1. **This file** (`docs/dev/self-documenting-loop-design.md`).
2. **[`RELEASE_ARC.md`](RELEASE_ARC.md) §4.7** — the `design/self-documenting-loop →
   feat/self-documenting-wiki` row annotated **"Design DONE 2026-06-16"** with a pointer
   here + a one-line of the settled trigger/cost/scope (mirrors the 7.2 governance row's
   "Design half DONE… full spec in …").
3. **[`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md)** — the **7.3** row annotated "Design
   half DONE 2026-06-16; `feat/` half pending" + a pointer here; plus a one-line
   Carry-forward-ledger confirmation that the cross-document link/cite checker (**Open #4**)
   **stays the named separate follow-on** and is **not** absorbed by this loop (the open
   count stays 7 — this design adds no open item).

No `CHANGELOG.md` entry on the design branch (dev-internal planning artifact; the
user-facing entry rides `feat/`, noting "dev-harness only — no product code/route/LLM/dep;
`PROMPT_VERSION` unchanged").

### `feat/` verification contract

The quality gate (`ruff && mypy && pytest`) is **docs+shell-blind** — no Python changes,
and the command/subagent `.md` + bash hook are out of ruff/mypy/pytest scope — so it stays
green but **does not prove the loop.** `feat/` therefore adds, beyond the gate:

- **Manual smoke on a real diff (the real verification).** Point the loop at an actual
  `.last_ingest_sha`→HEAD window with 1–4 changed source files; confirm it (i) surfaces cost
  first and enforces the cap, (ii) the scribe produces SCHEMA-conformant page edits, (iii)
  the auditor catches at least the known-DRIFTED cites, (iv) `/wiki-lint` passes, (v)
  `.last_ingest_sha` advances, and (vi) **the output is a reviewable diff, not a commit.**
- **Subagent tool-grant check.** Confirm `wiki-grounding-auditor` has no `Edit`/`Write`
  (read-only by construction) and `wiki-scribe` has no `Task`/`Write`-of-infra.
- **Hook witness check.** `wiki-freshness-reminder.sh` still always-exit-0 and silent under
  the sentinel; only the message tiers at the threshold. Hand-test with byte-correct JSON via
  a `python json.dumps` heredoc (not `echo`), per the project's hook-testing lesson.
- **Registration check.** The command + two subagents surface as `/sartor:…` /
  `sartor:…` (the 7.1 activation contract) — verifiable only on a human reload.

---

## 8. Source map (where everything comes from)

| Artifact | Source / precedent | Lands on |
|---|---|---|
| `/wiki-self-update` orchestrator | [`tune-from-annotations.md`](../../commands/tune-from-annotations.md) (orchestrator-delegates-in-prose) + [`compliance-agent-design.md`](reviews/2026-06-product-excellence/03-prescriptions/compliance-agent-design.md) (command+subagent composing primitives) | `feat/` → `commands/wiki-self-update.md` |
| `wiki-scribe` (Haiku) | [`eval-judge.md`](../../agents/eval-judge.md) (Haiku `model:` pin) + [`tune-drafter.md`](../../agents/tune-drafter.md) (read-mostly drafting subagent, work-from-file) | `feat/` → `agents/wiki-scribe.md` |
| `wiki-grounding-auditor` (Haiku, read-only) | the compliance subagent / `prompt-archaeologist` (read-only tool grant = enforcement) + WS-4b author≠auditor ([`log.md`](../wiki/log.md) 2026-06-13) | `feat/` → `agents/wiki-grounding-auditor.md` |
| Warm-start exemplars | WS-4b pages (`route-surface`, `deterministic-llm-boundary`, …) — **by reference** | (no new file — cited by slug) |
| Trigger escalation | [`wiki-freshness-reminder.sh`](../../hooks/wiki-freshness-reminder.sh) (witness, F-gov-06 honest sentinel) | `feat/` → hook message tiering |
| Deterministic backstop | [`/wiki-lint`](../../commands/wiki-lint.md) (unchanged) + [`/wiki-audit`](../../commands/wiki-audit.md) (the discipline the auditor realizes) | (reused as-is) |
| This design doc | [`governance-extraction-design.md`](governance-extraction-design.md) (8-section structure) | `design/` → this file |

**Relationship to PX-33 (related, not authority).** [`prescriptions.md`](reviews/2026-06-product-excellence/03-prescriptions/prescriptions.md)
**PX-33** ("WS-4b cold-ingest grounding + rot-detection at module scale", banded
*post-public*) is a **distinct** prescription — its subject is the *cold* pass's
module-scale grounding + the `sha→HEAD` rot-detection. The self-documenting loop
**operationalizes that rot-detection idea** at steady state (the freshness witness +
`/wiki-lint` staleness check + the auditor), but the **authority** for this design is
[`RELEASE_ARC.md`](RELEASE_ARC.md) §4.7 + [`memory-architecture.md`](memory-architecture.md),
not PX-33. Cited so the implementer doesn't conflate the two.

---

## H. Open sub-decisions (resolved vs left open)

**Resolved by this design** (the `feat/` build re-decides none of these): primary trigger =
bounded checkpoint; freshness hook stays a witness that escalates copy; Haiku steady-state,
diff-scoped, cost-surfaced, page-capped; scope = `docs/wiki/`-only (the link/cite checker
explicitly out); new orchestrator command (not `--auto`); a separate Haiku auditor subagent
(author≠auditor); exemplars by-reference (no new file); the loop **never auto-commits** by
default; lint + audit are the trust layer; the design branch ships docs only.

**Left open for the `feat/` build or the owner** (knobs, not architecture):
- The exact **command name** (`/wiki-self-update` vs `/wiki-loop` vs `/wiki-refresh`).
- The exact **drift-threshold number** for the hook escalation and the per-run **page cap**
  (`--cap N`).
- The exact **2–3 exemplar pages** named in the scribe prompt.
- Whether to harden the **auditor catch-rate signal** into a formal precision rubric.
- The narrow **zero-drift `--auto-commit`** opt-in (decide-now / migrate-later; weigh near
  the Sprint-8.7 CI activation, not in the default build).
