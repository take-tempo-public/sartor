---
description: The self-documenting wiki loop — a bounded, cost-aware Haiku diff-pass that brings docs/wiki/ back into agreement with the code. Resolves the .last_ingest_sha→HEAD diff, surfaces cost before spending, delegates per-page synthesis to the wiki-scribe subagent and per-page grounding audit to the wiki-grounding-auditor subagent (author≠auditor), runs /wiki-lint as the deterministic gate, reconciles index/backlinks, advances the checkpoint, logs, and presents a reviewable diff. NEVER commits. Bounded-checkpoint trigger (branch close-out / pre-tag) + on-demand.
argument-hint: [--since <sha>] [--cap <N>]
allowed-tools:
  - Bash
  - Read
  - Edit
  - Write
  - Grep
  - Glob
  - Task
---

Run the **self-documenting wiki loop**: a bounded, cost-aware steady-state pass that
updates the committed LLM-wiki under `docs/wiki/` so it tracks the code **without a human
author**, while keeping the human at the **spend** boundary and the **commit** boundary.
This command **orchestrates**; it does not synthesize or grade itself — it delegates
synthesis to the `wiki-scribe` subagent (Haiku) and grounding audit to the separate
`wiki-grounding-auditor` subagent (Haiku, read-only), then runs the deterministic
[`/wiki-lint`](wiki-lint.md) as the structural backstop. The full design is
[`docs/dev/self-documenting-loop-design.md`](../docs/dev/self-documenting-loop-design.md);
the rulebook is [`docs/wiki/SCHEMA.md`](../docs/wiki/SCHEMA.md).

> **This is an LLM op — a human decides when to pay.** Like [`/wiki-ingest`](wiki-ingest.md)
> and [`/eval`](eval.md), it surfaces its scope and cost **before** spending. It is
> **invoked, never self-firing** — the commit-time [freshness reminder](../.claude-plugin/hooks/wiki-freshness-reminder.sh)
> only *tells the human when the spend is worth it*; it does not run this loop.

> **Why a new command, not `--auto` on `/wiki-ingest`.** [`/wiki-ingest`](wiki-ingest.md)
> owns the from-scratch **cold pass** and its frontmatter cannot pin a model. The loop's
> whole cost story is *Haiku at steady state, never repeat the cold pass* — which can only
> be expressed by delegating to **model-pinned subagents**. So this is a thin orchestrator
> that **composes** `/wiki-ingest`'s diff mechanic, the scribe, the auditor, and `/wiki-lint`,
> leaving `/wiki-ingest` exactly as-is (the capable cold author). It mirrors the
> [`/tune-from-annotations`](tune-from-annotations.md) → [`tune-drafter`](../agents/tune-drafter.md)
> orchestrator-delegates-to-subagent shape.

## Steps

1. **Resolve the diff window.** Read [`docs/wiki/.last_ingest_sha`](../docs/wiki/.last_ingest_sha)
   (or use `--since <sha>`). If it is the sentinel (no 40-char SHA), **stop** — a cold pass
   is pending; that is [`/wiki-ingest --full`](wiki-ingest.md)'s job, not this loop's (the
   loop never repeats the cold pass). With a real SHA, select changed sources with
   `git diff --name-status <sha> HEAD`, **excluding `docs/wiki/` itself** (the wiki is the
   artifact, not a source) and the review archive under `docs/dev/reviews/` (provenance
   model — never ingested).

2. **Surface scope + cost BEFORE spending, and enforce the page cap.** From the changed-file
   list, work out the **affected pages** — remember the wiki **references, never duplicates**
   canonical/contract docs (D5), so changes to `AGENTS.md` / `CLAUDE.md` / `vision.md` /
   `docs/governance/` / `CONTRIBUTING.md` etc. usually map to **no** page; only changes a
   page actually cites (`path:line`/symbol) or a genuinely new concept produce work. Print:
   the changed-source list, the affected-page list (created vs updated), and the estimated
   spend (≈ 2 Haiku calls per affected page — one scribe synthesis, one auditor pass).
   - **Page cap (default 8, override `--cap N`).** If the affected pages exceed the cap,
     **stop and ask** the human to scope down (`--since` a tighter window) or to raise
     `--cap` — an oversized diff is a signal this is not a steady-state increment but a
     cold/consolidated pass that wants the capable [`/wiki-ingest`](wiki-ingest.md) (or an
     explicit cap raise). Do not silently synthesize past the cap.
   - Proceed only once the human authorizes the spend.

3. **Synthesize — delegate per affected page to `wiki-scribe`.** For each affected page,
   launch the **`wiki-scribe`** subagent via `Task`, naming the changed source file and the
   page slug(s) it maps to. The scribe (Haiku; `Read`/`Grep`/`Glob`/`Edit` only) makes the
   **minimal SCHEMA-conformant page edit** from the source **at HEAD** + the named exemplars
   ([`route-surface`](../docs/wiki/pages/route-surface.md),
   [`deterministic-llm-boundary`](../docs/wiki/pages/deterministic-llm-boundary.md),
   [`using-callback`](../docs/wiki/pages/using-callback.md)), holding the one grounding rule.
   It edits the page and hands back a one-line summary of what changed and which source
   line(s) ground it. It does **not** grade itself or touch index/log/checkpoint.

4. **Audit — delegate per changed page to `wiki-grounding-auditor` (author≠auditor).** For
   each page the scribe touched, launch the **`wiki-grounding-auditor`** subagent via `Task`
   — a **different** context from the scribe that wrote it. The auditor (Haiku; read-only
   `Read`/`Grep`/`Glob`) quote-matches every `path:line` cite and every `[synthesis]` claim
   against source at HEAD and classifies each **SUPPORTED / DRIFTED / UNSUPPORTED**, returning
   the verdict. It changes nothing.
   - **Re-anchor DRIFTED** cites (prefer a symbol/anchor over a bare line number) — you hold
     `Edit`; apply the auditor's suggested anchor.
   - **Surface UNSUPPORTED** claims to the human for a decision — **never auto-delete or
     silently rewrite** (the page is committed history; an unsupported claim may signal a real
     change worth tracing). If the human confirms a correction, apply it; otherwise leave it
     flagged.

5. **Run the deterministic gate.** Run [`/wiki-lint`](wiki-lint.md) (no LLM) over the result:
   staleness, `[[backlink]]` resolution, `path:line` existence, orphans, index↔pages
   agreement. Resolve any **ERROR** before finishing — the loop does not leave the wiki
   internally inconsistent.

6. **Reconcile, advance, log.** Add/revise the one-line [`index.md`](../docs/wiki/index.md)
   entry per created/changed page; reconcile `[[backlinks]]` bidirectionally. Write the
   current `git rev-parse HEAD` (full 40-char SHA) into
   [`.last_ingest_sha`](../docs/wiki/.last_ingest_sha). Append a dated entry to
   [`log.md`](../docs/wiki/log.md) (newest last): the branch, mode (**diff** + the
   `<sha>→HEAD` window), files read, pages created/changed, and the **auditor catch-rate**
   for this run (DRIFTED + UNSUPPORTED caught / pages audited). `log.md` is the wiki's
   changelog — do **not** touch the root [`CHANGELOG.md`](../CHANGELOG.md).

7. **Present the diff for human review — do NOT commit.** Show `git status` + a summary of
   the page diffs and the checkpoint advance. The loop's output is a **reviewable diff,
   never a silent push**: autonomy is in synthesis + execution; the commit stays human-gated.
   Stop here and let the human review and commit.

## Trigger + cadence

The loop runs at **bounded checkpoints**, not per-commit: a **branch close-out** or a
**pre-tag** refresh (the [`/wiki-lint`](wiki-lint.md) "periodic + pre-release gate" slot —
e.g. the `chore/version-bump-*` step in [`docs/dev/RELEASE_CHECKLIST.md`](../docs/dev/RELEASE_CHECKLIST.md)),
plus on-demand. There is **no scheduler** — a timer would pay tokens on no-op windows and
remove the human from the spend boundary.

## The auditor catch-rate is a tuning signal, not a gate

Track the per-run catch-rate (DRIFTED + UNSUPPORTED caught) logged in `log.md` across the
first few runs. If the auditor stops catching drift that the human review then finds, that
is the signal to **retune the scribe** — but the loop is **not blocked** on a threshold.
Its trust is structural: `/wiki-lint` (deterministic) + the auditor (adversarial) + **a
human reviews every diff**.

## What this loop does NOT do

- It **never auto-commits** — always a reviewable diff. (A narrow zero-drift `--auto-commit`
  opt-in is a deliberately-deferred future, not built.)
- It does **not** run the cold pass / from-scratch taxonomy (that stays
  [`/wiki-ingest --full`](wiki-ingest.md), which it never repeats).
- It does **not** check `[text](path)` links across `docs/governance/` or the contract docs
  — that cross-document link/cite checker is a **separate** tracked follow-on; this loop is
  `docs/wiki/`-scoped only.
- It does **not** restate canonical rules from `AGENTS.md`/`CLAUDE.md`/`vision.md`/
  `docs/governance/` (D5 — referenced, never duplicated), nor touch product code, a route, a
  dependency, or `PROMPT_VERSION`.
