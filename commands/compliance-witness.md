---
description: Read-only governance drift witness. Reads charter/RELEASE_ARC/CHANGELOG/git-history/wiki provenance at a pinned sha and emits a ranked, capped (default 12, --cap N) drift report in FLAG/WATCH/AFFIRM findings-register format, appended to docs/governance/compliance-log.md. Reports, never edits, never blocks. Pre-tag companion + on-demand.
argument-hint: [--since <sha>] [--cap <N>]
allowed-tools:
  - Bash
  - Read
  - Grep
  - Glob
  - Task
---

Run the **compliance witness**: a read-only, periodic read of whole-repo coherence
that emits a **ranked, capped drift report** — places where what the project's
governance, plan, changelog, code, or wiki provenance *say* has drifted from what the
repo *is* at a pinned sha. It is the [`/wiki-lint`](wiki-lint.md) witness posture
turned on the **governance** surface: this command **orchestrates and renders**; it
does not analyze drift itself — it delegates the read to the model-pinned
[`compliance-witness`](../agents/compliance-witness.md) subagent (Sonnet, read-only),
receives ranked candidate flags, caps them, and prints the report. The design is
[`compliance-agent-design.md`](../docs/dev/reviews/2026-06-product-excellence/03-prescriptions/compliance-agent-design.md);
the severity anchor is [`docs/governance/charter.md`](../docs/governance/charter.md).

> **This is the Regulation function made periodic.** The hooks block one unsafe action
> at the moment it happens; this witness notices that the *charter*, the *release arc*,
> the *changelog*, and the *code* have quietly diverged across a release. It **cautions
> and suggests; it never edits, never blocks, never files an issue** (the subagent's
> tool grant enforces this by construction). A report with **zero drift flags is a
> valid, expected, frequent output** — honest silence, not a failure to find something.

> **Why a command + subagent, not a hook.** A PostToolUse witness hook fires *per tool
> call* — the per-merge noise failure mode this cadence rules out — and a hook's
> `systemMessage` cannot carry a ranked N-item table. The command + Sonnet subagent
> composition is the right vehicle for a periodic, ranked, human-read report. The
> pre-tag slot is a checklist line invoking this command, not a hook. It mirrors the
> [`/wiki-self-update`](wiki-self-update.md) → [`wiki-scribe`](../agents/wiki-scribe.md)
> orchestrator-delegates-to-model-pinned-subagent shape.

## Steps

1. **Resolve the pinned sha.** Use `--since <sha>` if given; otherwise the last release
   tag (`git describe --tags --abbrev=0`, falling back to the first commit if no tag
   exists). Echo the resolved sha and the `<sha>→HEAD` window so the read is reproducible.

2. **Delegate the read to the `compliance-witness` subagent via `Task`.** Hand it the
   pinned sha and the read corpus: the governance docs
   ([`docs/governance/`](../docs/governance/) — charter / enforcement / metrics),
   the plan ([`RELEASE_ARC.md`](../docs/dev/RELEASE_ARC.md) +
   [`RELEASE_CHECKLIST.md`](../docs/dev/RELEASE_CHECKLIST.md)),
   the declared history ([`CHANGELOG.md`](../CHANGELOG.md)), the actual history
   (`git log` / tags / the merge record), and the wiki provenance
   ([`docs/wiki/`](../docs/wiki/) pages + `.last_ingest_sha` + the cite graph). The
   subagent (Sonnet; read-only `Read`/`Grep`/`Glob`/`Bash`) re-derives every cited line
   at the sha, finds pairwise disagreements (and C-0 categoricals lacking by-construction
   backing), and returns **ranked candidate flags**. It changes nothing.

3. **Apply the cap.** Default **N = 12** (override `--cap N`). The cap is load-bearing —
   an uncapped witness that emits everything is back to per-merge noise. If the subagent
   returns more than N flags, render the **top-N** (charter-severity first, leverage tier
   P0…P3 second) and a single line stating how many were withheld, so the reader knows
   the tail exists without drowning in it.

4. **Render the findings-register table.** One row per flag, in the format this project's
   product-excellence review proved out — a reader fluent in the findings register needs
   no new vocabulary:
   - a **stable id**;
   - a **one-line claim**;
   - the **two-or-more sources that disagree**, each cited `path:line @ <sha>` (or a doc
     clause id / F-id);
   - a **disposition verb** — **FLAG** (a real drift threatening something the charter
     states) / **WATCH** (worth tracking, not yet a breach) / **AFFIRM** (a surface
     confirmed coherent);
   - a **suggested direction** — never an edit, a *suggestion* ("vision.md:50 and signed
     C-0 disagree; one must move").

5. **Print the gate verdict** ([`/wiki-lint`](wiki-lint.md)-style, so a release driver
   can act at a glance): **clean** (no FLAG-tier drift) or **needs attention** (FLAG-tier
   drift present). The verdict is advisory — it informs the release driver; it does not
   fail a gate.

6. **Append a dated counts-per-tier line** to
   [`docs/governance/compliance-log.md`](../docs/governance/compliance-log.md) (creating
   it with its header on first run; newest entry last): the date, branch, the
   `<sha>→HEAD` window, the per-tier counts (FLAG / WATCH / AFFIRM, plus withheld), and
   the gate verdict. This log is the witness's append-only record — do **not** touch the
   root [`CHANGELOG.md`](../CHANGELOG.md).

## Cadence

Two deliberate triggers, both human-invoked — there is **no scheduler** (a timer would
flag on no-op windows and train the reader to ignore flags):

- **Pre-release-tag.** A tag is exactly when the charter, the arc, the changelog, and the
  code are supposed to be coherent — and exactly when they have had a sprint's worth of
  chances to diverge. Run as a **pre-tag gate companion** in the
  [`RELEASE_CHECKLIST.md`](../docs/dev/RELEASE_CHECKLIST.md) discipline — the same slot
  [`/wiki-lint`](wiki-lint.md) occupies.
- **On-demand.** Run `/compliance-witness [--since <sha>]` when a large change lands or
  before a governance amendment — the charter's amendment ceremony names "a flag in the
  compliance agent's next drift report (witness, not approver)" as a step, and this is the
  invocation that produces it.

**Out of scope — per-merge.** Most merges touch no governance surface; a flag on every
merge trains the reader to ignore flags. This witness adopts the
[`wiki-freshness-reminder`](../hooks/wiki-freshness-reminder.sh)
honest-silence discipline instead.

## What this command does NOT do

- It **never commits** and **never advances a checkpoint** — its only writes are the
  rendered report (to the chat / handoff surface, **never** `output/`) and the
  `compliance-log.md` append. Exactly the `/wiki-lint` write envelope.
- It **never edits a source file**, **never blocks** a merge / commit / gate, and
  **never files an issue or PR** — it surfaces; the human decides whether anything
  becomes a tracked item.
- It is **not a source of truth** — it **cites, it does not assert**. Every flag is a
  question with evidence ("these two disagree — which is right?"); the charter and the
  code remain the authorities.
- It does **not** touch product code, a route, a dependency, or `PROMPT_VERSION`.
