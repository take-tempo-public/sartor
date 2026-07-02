---
status: review-artifact
evidence_sha: c6e0437
graduation: docs/governance/compliance-agent.md + .claude-plugin spec (v1.0.7 pilot)
---

# Compliance-agent design — sartor.

> A witness for the Regulation function. The compliance agent reads the
> project's governance, history, and provenance and **emits a ranked drift
> report** — places where what the docs/code/plan *say* has drifted from
> what the repo *is* at a given sha. It cautions and suggests; it never
> changes anything.
>
> Severity anchor: the SIGNED Product Charter
> ([`../00-interview/product-charter.md`](../00-interview/product-charter.md)).
> Evidence base: the [findings register](../02-assessment/findings-register.md)
> and [verification log](../02-assessment/verification-log.md), cited by
> F-id rather than re-derived. Honors C-0 — mechanism-and-effort language,
> no absolutes about LLM behavior, no marketing.

## This review *is* the prototype run

This product-excellence review is the compliance agent executed by hand,
once, by a human-directed reviewing agent — and saying so is the honest
way to specify it. The review held the same posture the standing agent
must hold: it **witnessed**, it did not edit (every output is a
prescription, never a patch to a source file); it **cited at a sha**
(everything pinned at `c6e0437`); it **ranked by a fixed severity anchor**
(the signed charter, not the reviewer's taste); and it **submitted its own
claims to adversarial verification** before asserting them (the
verification log — 42 P0/P1 findings re-derived, 6 WEAKENED, 0 REFUTED).

How that posture performed is itself the strongest argument for the agent.
The witness-only stance produced no collateral damage and surfaced
real drift — F-vision-03 (a shipped outcome-capture loop the docs still
call "(Future v2)"), F-sec-03/F-docs-02 (a SECURITY.md no-CDN claim a
committed test proves false), F-gov-01 (a merge-blocker hook that passes
the dominant merge direction). The adversarial pass *trimmed* six findings
rather than inflating them, which is the behavior a cautioner wants: the
WEAKENED set (e.g. F-arch-03 downgraded from a live security hole to a
latent guardrail-coverage gap) shows the value of forcing every flag
through falsification before it reaches the owner. The standing agent
inherits that discipline as its **self-evaluation rubric** (below): a
witness whose flags don't survive scrutiny is noise, and the review's own
6-of-42-trimmed rate is the calibration baseline.

The agent is, in system-model terms, **the Regulation function made
agentic** — the same place that holds the hooks and the quality gate,
turned from per-edit machine gates into a periodic narrative read of
whole-repo coherence. The hooks block one unsafe action at the moment it
happens; the compliance agent notices that the *charter* and the *release
arc* and the *code* have quietly diverged across a release. Different
altitude, same function.

## Charter — what it reads, what it emits

**Reads (all read-only, all at a pinned sha):**

- **Governance docs** — the graduated charter (`docs/governance/charter.md`
  once it exists), `vision.md`, `AGENTS.md`/`CLAUDE.md`, the 10-Principles
  annotations. The prescriptive layer.
- **The release arc + checklist** — `docs/dev/RELEASE_ARC.md`,
  `RELEASE_CHECKLIST.md`. The stated plan and its gates.
- **`CHANGELOG.md`** — the declared history.
- **Git history** — `git log`, tags, the branch/merge record. The actual
  history.
- **Wiki provenance** — `docs/wiki/` pages, `.last_ingest_sha`, the
  `[[backlink]]` / `path:line` cite graph. What the self-documenting loop
  claims to know, and how fresh it is.

**Emits (one artifact):** a **drift report** — a ranked list of places
where two of those sources disagree, or where a categorical claim is not
backed by the construction C-0 requires. Nothing else. The report is
advisory text handed to the owner; it is not committed as a source of
truth, it is not an issue, it is not a patch.

## HARD non-goals

These are the agent's constitution. Each is a *never*, and — per C-0 — each
is a *never* precisely because it is enforceable by construction (the
agent's tool grant), not a behavioral hope.

- **Never edits.** No `Edit`, no `Write` to any source file. Its only
  write is its own report artifact (and, like `/wiki-lint`, an append to a
  log). Enforced by the tool allow-list, exactly as F-gov-09's read-only
  subagents are.
- **Never blocks.** It is not a hook on the critical path. It cannot fail a
  merge, a commit, or a gate. The blocker-hook class (F-gov-04: seven
  reachable `exit 2` blockers) is a *different* class from the
  witness class (F-gov-04: three `exit 0` witnesses) — the compliance
  agent is firmly in the witness class.
- **Never files issues or PRs autonomously.** It surfaces; the human
  decides whether anything becomes a tracked item. (The owner's budget is
  ~2 hrs/week of planning and agent management per W-3; an agent that
  autonomously generates issue debt would tax exactly that budget.)
- **Never a source of truth.** It **cites, it does not assert.** Every flag
  points at evidence at a sha; the charter and the code remain the
  authorities. A drift report is a question ("these two disagree — which is
  right?"), never a ruling. This mirrors the review itself: the reviewer
  ranked against the charter and never *became* the charter.

## Inputs + cadence

**Recommended cadence — two triggers, both deliberate:**

1. **Per-release-tag.** The natural unit of drift is a release: a tag is
   exactly when the charter, the arc, the changelog, and the code are
   supposed to be coherent, and exactly when they have had a sprint's worth
   of chances to diverge. The agent runs as a **pre-tag gate companion** in
   the `RELEASE_CHECKLIST` discipline — the same slot `/wiki-lint` already
   occupies. (Per P-3/D-4 this is a machine-run check tied to a tag, not a
   recurring human-promised audit — no calendar SLA.)
2. **On-demand slash command.** `/compliance-witness [--since <sha>]`, run
   by an operator whenever a large change lands or before a governance
   amendment. The charter's amendment ceremony already names "a flag in the
   compliance agent's next drift report (witness, not approver)" as a step
   — this is the on-demand invocation that produces it.

**The noise failure mode — explicitly out of scope: per-merge.** Running on
every merge is the wrong cadence and would retire the agent by the rubric
below. Most merges touch no governance surface; a flag on every merge
trains the reader to ignore flags. `/wiki-freshness-reminder` already
models the correct restraint: it is silent until a real baseline exists and
silent when nothing relevant changed (F-gov-06). The compliance agent
adopts the same honest-silence discipline — **a report with zero drift
flags is a valid, expected, frequent output**, not a failure to find
something.

## Output contract

The drift report follows the **findings-register format** — the format this
review proved out — so a reader already fluent in the register can read a
drift report with no new vocabulary:

- **A ranked list of drift flags**, severity-ordered by the charter (a flag
  is a flag only if it threatens something the charter states — the same
  test the register uses), then by leverage tier (P0…P3).
- **Each flag carries:** a stable id; a one-line claim; the **two-or-more
  sources that disagree**, each cited as `path:line @ <sha>` (or a doc
  clause id / F-id); a disposition verb (FLAG / WATCH / AFFIRM); and a
  suggested direction — never an edit, a *suggestion* ("vision.md:50 and
  signed C-0 disagree; one must move").
- **Capped at N** (default N = 12, tunable). The cap is load-bearing: an
  uncapped witness that emits everything is back to per-merge noise. Over
  the cap, the agent emits the top-N and a single line stating how many
  were withheld, so the reader knows the tail exists without drowning in
  it. Ranking-then-capping is what makes the report actionable.
- **A gate verdict line**, `/wiki-lint`-style: *clean* (no FLAG-tier drift)
  or *needs attention* (FLAG-tier drift present), so a release driver can
  act on a glance.

## Self-evaluation rubric

A witness earns its standing only if its flags are real. The agent is held
to a measurable bar — and **retired or retuned if it falls below it**:

- **Flag precision over the first 3 reports.** For each FLAG-tier item, the
  owner records a verdict: *true drift* (acted on or consciously accepted)
  vs *noise* (the two sources did not actually disagree, or the
  disagreement is immaterial). **Precision = true-drift / total-FLAG.**
- **Threshold: ≥ 0.66 across the first three reports** — i.e. no worse than
  the review's own calibration, where 6 of 42 verified findings were
  trimmed (~0.86 survived intact, none refuted). Below 0.66, the agent is
  **retuned** (tighten the drift heuristics, narrow the source set) before a
  next run; if a retune does not clear the bar, the agent is **retired** to
  on-demand-only and the standing pre-tag slot reverts to the human
  checklist. A noisy cautioner is worse than none — it trains the reader to
  skip the report, which is the precise harm this rubric exists to prevent.
- **No false-affirm credit.** AFFIRM-tier items (the agent confirming a
  surface is coherent) do not count toward precision — only FLAG-tier does,
  so the agent cannot inflate its score by affirming the obvious.

## Arc introduction point

- **Design now (this review, v1.0.x).** This document is the design
  artifact; it ships zero code.
- **PILOT at v1.0.7 — once `docs/governance/` exists.** The agent has no
  graduated governance home to read until the v1.0.7 governance-extraction
  epic creates `docs/governance/charter.md` (F-vision-01, F-gov-05). The
  pilot is one supervised run against that freshly-graduated surface, scored
  by the rubric above. v1.0.7 is also where the charter's amendment ceremony
  goes live, so the pilot validates the "flag in the next drift report"
  step against a real ceremony.
- **Standing at v1.1.x.** If the pilot clears the precision bar, the agent
  becomes the standing pre-tag witness companion in `RELEASE_CHECKLIST`,
  plus the on-demand command. Per W-4, the witness pattern is a named
  extraction candidate ("governance rulebook + compliance agent → product")
  — the standing form is the in-place maturation that a future breakout
  starts from.

---

## Appendix — buildable prototype spec (zero code)

This is the spec the v1.0.7 pilot branch starts from. It composes two
**existing** plugin primitives, both verified present at `c6e0437`: the
**read-only subagent** pattern (F-gov-09 — `prompt-archaeologist.md`: a
`Read`/`Grep`/`Glob`-only agent that diagnoses and outputs a diff but
*never* applies it) and the **witness command** pattern
(`/wiki-lint`: read-only, severity-tiered ERROR/WARN/INFO, states a gate
verdict, appends to a log, fixes nothing). No new dependency (D-1); no new
hook on the critical path.

### A. The slash command — `.claude-plugin/commands/compliance-witness.md`

Frontmatter (mirroring `wiki-lint.md`):

```
---
description: Read-only governance drift witness. Reads charter/RELEASE_ARC/
  CHANGELOG/git-history/wiki provenance at a pinned sha and emits a ranked,
  capped drift report in findings-register format. Reports, never edits,
  never blocks. Pre-tag companion + on-demand.
argument-hint: [--since <sha>] [--cap <N>]
allowed-tools: [Bash, Read, Grep, Glob, Task]
---
```

Body (prose instructions, no code): resolve the sha (`--since` or the last
release tag); delegate the read to the subagent below via `Task`; receive
its ranked candidate flags; apply the cap; render the findings-register
table; print the gate verdict; append a dated counts-per-tier line to
`docs/governance/compliance-log.md`. The command's **only** writes are the
report (to the review/handoff surface, never `output/`) and that log
append — exactly the `/wiki-lint` write envelope.

### B. The subagent — `.claude-plugin/agents/compliance-witness.md`

Modeled byte-for-pattern on `prompt-archaeologist.md`:

```
---
name: compliance-witness
description: Use to produce a governance drift report. Reads governance docs,
  RELEASE_ARC, CHANGELOG, git history, and wiki provenance at a pinned sha;
  identifies where two sources disagree or a C-0 categorical lacks
  by-construction backing; outputs ranked drift flags. Does NOT edit anything.
model: claude-sonnet-4-6
tools: [Read, Grep, Glob, Bash]
---
```

The tool grant is the enforcement of every HARD non-goal: **no `Edit`, no
`Write`, no `Task`** — the agent cannot change a file, cannot spawn a
sub-writer, cannot file an issue, because it was never handed the tools to.
This is the same construction that makes `prompt-archaeologist` safe
(F-gov-09), applied to governance. `Bash` is present for read-only git
(`git log`, `git diff --name-only`, `git show <sha>:path`) and is the one
tool to scope-guard in the system prompt to read-only invocations.

System-prompt contract (the agent's standing instructions):

1. **Read, never recall.** Re-derive every cited line at the pinned sha
   with `git show`/`Read` — never from memory (the
   `prompt-archaeologist` "do not work from memory" rule).
2. **Pairwise drift only.** A flag requires *two named sources that
   disagree* (or one categorical claim + the absent construction C-0 would
   require). No single-source opinions — that is how the review avoided
   asserting beyond evidence.
3. **Rank against the charter, cap at N.** Charter-severity first, leverage
   second; emit top-N + a withheld count.
4. **Cite, never assert.** Each flag is a question with evidence, plus a
   *suggested direction*, never an edit.
5. **Honest silence.** Zero drift → a clean report. Do not manufacture
   flags to look useful (the F-gov-06 honest-sentinel precedent).

### C. Why not a hook

A PostToolUse witness hook (the `wiki-freshness-reminder` shape) was
considered and **rejected for the standing trigger**: a hook fires per tool
call, which is the per-merge noise failure mode the cadence section rules
out, and a hook's `systemMessage` channel cannot carry a ranked N-item
table. The witness-*hook* pattern still informs the design — its
always-exit-0, silent-when-nothing-changed discipline (F-gov-06) is exactly
the honest-silence rule the subagent inherits — but the **command +
subagent** composition is the right vehicle for a periodic, ranked,
human-read report. The pre-tag slot is a checklist line invoking the
command, not a hook.

### D. Graduation

On a passing v1.0.7 pilot, this design graduates to
`docs/governance/compliance-agent.md` (the standing spec) and the two
`.claude-plugin/` files above land on the v1.0.7 branch. Until then this
appendix is the complete starting point — a spec, not a line of code.
