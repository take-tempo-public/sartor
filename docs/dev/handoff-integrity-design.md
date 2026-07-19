# Handoff integrity — design (supersedes the chat-text-only handoff policy)

> **Purpose:** the settled design a later `feat/handoff-integrity-kit` implementation
> branch executes against, so that branch re-decides nothing. Documents the evidence
> that motivates it, supersedes `feedback-handoff-process.md`'s 2026-06-08 "handoffs are
> ephemeral chat text, never a committed file" policy, and specifies exactly what ships:
> a provenance stamp, a generation/consumption fingerprint validator, and an append-only
> event ledger, vendored from spolia (formerly ai-research) where the same design has
> already run through one real branch.
> **Audience:** the agent implementing `feat/handoff-integrity-kit`, and the owner
> reviewing this design. Precedent for a design-branch deliverable:
> [`governance-extraction-design.md`](governance-extraction-design.md) (`design/` branch,
> implementation is separate and later).
> **Authoritative for:** the decision to commit handoff files (superseding the June 8
> chat-text policy), the file/directory layout, the template changes, and the rollout
> sequencing (script first, hook only if the script proves ignorable). On conflict with
> an older process note (including `feedback-handoff-process.md`), this doc governs for
> handoff-transfer scope.
> **Source of record (read-only, outside this repo):**
> - spolia (`c:/Dev/spolia`, renamed from `ai-research` 2026-07-17) —
>   `docs/dev/prov/SPEC.md` (the stamp/privacy-tier/ledger spec this doc vendors),
>   `scripts/verify_doc_template.py` (the validator, already fixed for a CRLF/LF
>   false-positive — see §6), `docs/dev/GOVERNANCE_KIT_PLAN.md` (the original design),
>   `docs/execution-log.md`'s "Governance kit" and "B06 freshrss" entries (the kit's
>   first two real branches, including the CRLF bug found and fixed on the second one).
> - The investigation itself: Claude Code session `4e0f4842-2d72-47ea-9759-e01bfde3c2bb`,
>   filed under the pre-rename project slug `c--Dev-ai-research` (transcript persists at
>   `~/.claude/projects/c--Dev-ai-research/4e0f4842-2d72-47ea-9759-e01bfde3c2bb.jsonl`,
>   2026-07-17, ~578 turns). Distilled into spolia project memory
>   `handoff-transfer-corruption.md` and `sartor-governance-migration-pending.md`.
> - This doc was authored in a **separate, cross-project session** continuing that
>   investigation (spolia session `6bc1f477-7493-4ca3-9d60-86d0ebcfd812`, 2026-07-17),
>   after the owner confirmed the June 8 chat-text policy should change in light of the
>   evidence in §2 below.

---

## 0. What this is, in one paragraph

Handoff prompts copy-pasted between Claude Code sessions have been silently arriving
corrupted — in sartor and in spolia/ai-research both — with agents on the receiving end
reconstructing the damage instead of surfacing it. Spolia's `feat/governance-kit`
built the fix (a committed handoff file, validated at generation and consumption by a
generic template/fingerprint checker, logged to an append-only ledger) and has now run
it through two real branches, including catching a real bug in the validator itself
before it could bite a second time. This doc is the evidence record + adoption plan for
bringing that fix into sartor, which requires **explicitly overriding** sartor's own
June 8 decision that handoffs must never be committed files.

---

## 1. Provenance and history

| Date | Event | Session / commit |
|---|---|---|
| 2026-06-08 | Owner corrects an agent for writing a handoff to `output/NEXT_AGENT_HANDOFF.md` instead of generating copyable chat text: *"this is not how we do handoffs… we have a process. use it."* Codified as `feedback-handoff-process.md`. | sartor session `f5176693-2794-4bfa-bf7a-07ef6f663577` |
| ~2026-06-13 – 2026-07-16 | Handoff template hardened twice more (`docs/handoff-carryforward-rule`, `chore/harden-hook-closeout-discipline`) — **within** the chat-text convention; neither addresses transport integrity. | commits `d610d53`, `323989c` |
| 2026-07-17, early | `fix/plan-approval` branch (sartor) receives a garbled handoff. Agent notes "the handoff text arrived garbled, so I want to confirm paths" in one subordinate clause, then proceeds without a full stop. | sartor session `b4d99d72-ecc2-484d-a3f0-0db5674e55b7` (first event `2026-07-17T02:53:14Z`) |
| 2026-07-17 | Owner opens an investigation in ai-research (pre-rename spolia) after noticing an agent silently reconstructing damaged input rather than surfacing it: *"i've discovered that there's a bug that is biting me in a another project [sartor] where the handoff gets garbled in the copy and paste between sessions."* Forensics run against both projects' recent session transcripts (§2). Design settled same session: provenance stamp + generic template/fingerprint validator + per-session ledger + one new binding rule (corrupted/fingerprint-mismatched input is a blocked gate). | ai-research/spolia session `4e0f4842-2d72-47ea-9759-e01bfde3c2bb` |
| 2026-07-17 | `feat/governance-kit` lands in spolia: `docs/dev/prov/SPEC.md`, `scripts/verify_doc_template.py`, `docs/dev/handoffs/` + `docs/dev/ledger/`, template + `AGENTS.md` updates. Rollout guidance recorded same session: *"Start advisory-but-loud; elevate the validator to a hook (sartor-style) only if advisory proves ignorable."* Same session also seeds `c:/Dev/behavior-corpus`, whose `TODO.md` names the exact sequencing this doc executes: *"Receive the provenance/governance kit into `kits/`... Unblocked when: the kit has survived real use in BOTH spolia... and sartor (vendored second, unblocks its release)."* | commit `bd95f8b` (spolia) |
| 2026-07-17 | `b06-freshrss` (spolia) — the kit's first live exercise on a real numbered branch — immediately hits a `BLOCKED` consumption check: the validator's own fingerprint function hashed raw file bytes, so a Windows checkout with `core.autocrlf=true` produced a false-positive "content changed since generation." Diagnosed, fixed (`fix/doc-fingerprint-crlf`: hash newline-normalized text instead), regression-tested, merged, then re-verified the original consumption check passed. | commits `7254866`, `2be210f` (spolia) |
| 2026-07-17 | Owner directs: the June 8 policy changes; vendor the proven fix into sartor, durably, in this repo. | this session |

---

## 2. Evidence — what was actually observed, not inferred

Per charter **C-7**: this section states only what was directly observed, with its
source. Curated from spolia's `handoff-transfer-corruption.md` memory (itself built
from directly reading the affected session transcripts, not from a plausible-sounding
theory).

**The corruption signature (confirmed, both projects, same shape):** a fixed-length run
of characters silently deleted mid-line, with the flanking fragments fused together —
consistent with copying a rendered terminal screen grid (wrapped rows lost, or
overwritten by in-place TUI redraw) rather than a generation defect.

- **ai-research/spolia, B3 branch** (the cleanest example in the corpus): the handoff
  received read `"nodit.com/prefs/apps"`. Decoded: `no` + `dit.com/prefs/apps` — the
  middle of `"credentials no[t yet created (user task: red]dit.com/prefs/apps"` is gone,
  the flanks fused into a word that reads as plausible but isn't.
- **sartor, `fix/plan-approval` branch** (session `b4d99d72`): the same shape —
  `"owaude Code reliability problems"` decodes to `ow[ing to this week's Cl]aude Code
  reliability problems`.
- **ai-research B2** (both attempts): also confirmed garbled, e.g. two list items fused
  with the middle deleted.

**The behavioral failure was worse than the transport failure.** Of four confirmed
garbled arrivals, three agents (two on ai-research B2, one on B3) said nothing and
proceeded to silently reconstruct the damaged text as if it were correct. The sartor
`fix/plan-approval` agent did marginally better — one subordinate clause noting the
handoff "arrived garbled" — but still proceeded without a full stop or forensic pass;
that only happened once the owner asked directly. **Nothing in either project's binding
rules said damaged input was a stop condition** — blocked hooks were a stop condition,
garbled instructions weren't. That gap, not the transport bug itself, is the part this
design closes with a binding rule, not just a tool.

**Transport mechanism, pinned by the owner:** VS Code's integrated terminal (xterm.js) →
manual drag-selection of the rendered handoff → Ctrl+C → Ctrl+V into a second session's
terminal. Drag-selection copies the rendered character grid, not the underlying text
stream — consistent with every element of the signature (fixed-column space padding from
padded grid rows; dropped-segment-with-fused-flanks from rows lost to scrollback reflow
or TUI redraw before the selection completed). Which exact xterm.js internal path drops
the rows was never pinned, and doesn't need to be: transfer-by-reference deletes the hop
entirely regardless of the exact internal mechanism.

**A second, independent corruption mechanism was found in sartor specifically:** Bash
heredoc EOF failures causing write-time truncation — a different transport (no
clipboard, no session boundary involved) producing the same underlying failure class
(a large single-shot text transfer silently loses data, and nothing checked that what
landed matched what was sent). This is separate evidence for the same fix (read back and
validate any large write, don't trust it), not a duplicate finding.

**Reported but not independently re-verified by this doc:** the originating session's
notes state sartor's own `RELEASE_CHECKLIST.md` once contained a ledger note "found
truncated mid-sentence" that had to be reconstructed against `CHANGELOG.md` — cited from
sartor's own prior handoff text at the time, not from directly re-opening that historical
diff. Flagged here per C-7 rather than silently upgraded to a confirmed fact: **if
durable-doc contamination matters to how urgently this ships, verify it first** by
`git log -p -- docs/dev/RELEASE_CHECKLIST.md` around the affected date rather than
trusting this restatement.

---

## 3. Current-state survey — sartor's handoff/governance infra vs. the gap

Verified against `main` at `fda2717` (2026-07-17). Legend: ✅ already covers it ·
🟡 partial · ❌ gap this design closes.

| Concern | Sartor today | |
|---|---|---|
| A structured next-agent template | `docs/dev/AGENT_HANDOFF_TEMPLATE.md` — Documents-to-read, Where-we-are, What-landed, Carried-forward (mirrors `RELEASE_CHECKLIST.md`'s ledger), close-out checklist | ✅ exceeds spolia's original template in some ways (richer carry-forward integration, hook awareness) |
| Cumulative open-items discipline | `RELEASE_CHECKLIST.md` Carry-forward ledger, single authoritative home, reduction-sprint threshold | ✅ exceeds — spolia's equivalent (`execution-log.md`) is less structured |
| Mechanism over instruction | `.claude-plugin/hooks/` — `require-evidence-before-fix`, `require-feature-branch`, `block-merge-to-main`, `restore-evidence` (SessionStart), etc. | ✅ exceeds — spolia's kit is currently advisory-only (a manually-run script), not hook-enforced |
| **Handoff transfer channel** | **Copyable chat text, generated after merge, explicitly required to never be a committed file** (`feedback-handoff-process.md`, 2026-06-08) | ❌ **this is the actual gap** — the channel itself (human clipboard / terminal render) is the unvalidated, lossy hop |
| **Generation/consumption integrity check** | None — a handoff is trusted on arrival, with no mechanical check that what the next session received matches what the closing session wrote | ❌ gap |
| **Provenance stamp on the handoff artifact** | None — no session/branch/commit/actor/timestamp header | ❌ gap |
| **Event ledger of handoff generated/consumed/blocked** | None | ❌ gap |
| **Binding rule: damaged input is a stop condition** | Not present — hooks blocking a tool call are a stop condition; a garbled prose handoff is not named as one anywhere in `AGENTS.md` or the charter | ❌ gap — this is the rule that would have prevented all four confirmed silent reconstructions in §2 |

**Read together:** sartor is *ahead* of spolia on almost everything **except** the one
thing that actually caused data loss. The June 8 policy was a reasonable response to a
different, real problem (an agent institutionalizing scratch files in `output/`) — but
it also happens to be the exact mechanism (transfer by value, through a lossy
human-mediated channel) that produced every confirmed corruption event in §2. Fixing the
gap requires changing that specific policy, not just adding tooling alongside it.

---

## 4. The policy conflict and its resolution

`feedback-handoff-process.md`'s stated rationale for chat-text-only: committing a
handoff (a) bypasses the structured template, (b) institutionalizes scratch files in the
repo, (c) leaves a stale snapshot that rots — the durable record was meant to be
`RELEASE_ARC.md` / `RELEASE_CHECKLIST.md` / `PRODUCT_SHAPE.md`, never the handoff.

Each concern is addressed by this design without reverting to chat text:

- **(a) bypasses the structured template** — it doesn't: the template's fixed sections
  (Documents to read, Hard constraints, Close-out checklist) still transfer verbatim,
  now byte-hash-checked against the canonical template instead of trusted on faith.
- **(b) institutionalizes scratch files** — a committed, frozen, per-branch file under
  `docs/dev/handoffs/` is not a scratch file in the `output/`-liberty sense the June 8
  correction was actually about; it's a versioned artifact with the same status as a
  diagnosis dossier under `docs/dev/diagnosis/`, which sartor already treats as durable.
- **(c) leaves a stale snapshot that rots** — a handoff was already a snapshot,
  whether chat-pasted or committed; committing it makes the staleness *checkable*
  (fingerprint mismatch, git history) instead of invisible. `RELEASE_ARC.md` /
  `RELEASE_CHECKLIST.md` remain the authoritative planning record — this design doesn't
  touch that boundary.

**Resolution (owner-directed, this doc):** `feedback-handoff-process.md` is superseded
for the handoff-transfer-channel question specifically. Its still-valid content (don't
write session scratch into `output/`) stays true and unaffected. The implementation
branch should update that memory file to point here rather than deleting it — memory is
distilled judgment, and "this was superseded and why" is itself worth keeping (P14,
append-only history, per the behavior-corpus principle spolia's design cites).

---

## 5. Decisions

| # | Decision | Resolution | Rationale (one line) |
|---|---|---|---|
| (i) | Handoff transfer channel | **Committed file** at `docs/dev/handoffs/<branch-slug>.md`, frozen once written; the human-carried pointer is one line (path + branch + short hash) | Deletes the lossy clipboard/terminal-grid hop entirely — the fix that actually addresses §2's evidence |
| (ii) | Vendored vs. reinvented | **Vendor spolia's `docs/dev/prov/SPEC.md` and `scripts/verify_doc_template.py` as a pinned copy**, adapted only for sartor's path conventions | Spolia is the explicit reference implementation per `behavior-corpus/TODO.md`; it has already survived two real branches including a real bug fix (CRLF) — reinventing it here would re-risk the exact bug already found and fixed once |
| (iii) | Template integration | **Extend sartor's existing `AGENT_HANDOFF_TEMPLATE.md`**, not replace it with spolia's — add the provenance-stamp line + mark its existing Documents-to-read / Hard-constraints / Close-out-checklist sections `<!-- verbatim -->` | Sartor's template already has richer, sartor-specific sections (RELEASE_ARC pointer, hook awareness, evals/TUNING_LOG); spolia's kit was designed to be structure-agnostic (the verbatim-section marker works on *any* template) precisely so it doesn't need to be replaced |
| (iv) | Enforcement level at launch | **Advisory script, not a hook**, matching the originating session's own stated rollout arc | "Start advisory-but-loud; elevate... only if advisory proves ignorable" — don't build enforcement for a failure mode not yet observed *after* the fix lands; sartor's hook infra makes a future escalation cheap if needed |
| (v) | `feedback-handoff-process.md` | **Superseded for the transfer-channel question**, left in place with a pointer to this doc, not deleted | Append-only history (P14); the "why we changed it" is worth keeping alongside the "why we did it originally" |
| (vi) | Ledger sharding | **Per-session JSONL shards** under `docs/dev/ledger/<session>.jsonl`, matching spolia | Concurrent sessions writing one shared ledger file would merge-conflict; per-shard is git-mergeable by construction |

---

## 6. What ships (file-by-file plan for `feat/handoff-integrity-kit`)

1. **`docs/dev/prov/SPEC.md`** — vendored from spolia's `docs/dev/prov/SPEC.md`
   (schema 1: stamp vocabulary, privacy tiers, ledger event schema), paths adjusted for
   sartor's layout. No sartor-specific content needed — the spec was designed generic
   (behavior-corpus constraint: "generic names, self-contained, stdlib only, no
   daemons/databases").
2. **`scripts/verify_doc_template.py`** — vendored from spolia's **current** version
   (post-`fix/doc-fingerprint-crlf`, commit `2be210f`), i.e. the fingerprint function
   must hash newline-normalized text, not raw bytes, from day one — do not
   re-introduce the bug spolia already found and fixed. Add to sartor's own
   `scripts/gate.py` step list or leave as a manually/pre-close-invoked check,
   consistent with decision (iv).
3. **`docs/dev/ledger/`** — new directory, `.gitkeep` or first real shard; sharded per
   writing session per decision (vi).
4. **`docs/dev/handoffs/`** — new directory for committed handoff files, starting with
   whatever branch first exercises this (see §7).
5. **`docs/dev/AGENT_HANDOFF_TEMPLATE.md`** — add the provenance-stamp line (schema,
   session, branch, commit, actor, agent, generated_at) as the file's first line, mark
   the existing Documents-to-read / Hard-constraints-equivalent / Close-out-checklist
   sections with the `<!-- verbatim -->` marker, add the "transfer by reference, never
   by value" purpose-note paragraph (adapt spolia's wording).
6. **`AGENTS.md`** — rewrite close-out step 4 (currently: "generate the next-agent
   handoff prompt... as copyable chat text (never a file written into `output/`)") to
   the file-based flow: write `docs/dev/handoffs/<branch-slug>.md`, validate with
   `scripts/verify_doc_template.py ... --event generated`, commit it, give the user only
   the one-line pointer as copyable chat text. Add the binding rule from §2: corrupted /
   fingerprint-mismatched input is a blocked gate — surface as first output and STOP.
7. **`docs/governance/charter.md`** — consider whether the new binding rule belongs as
   an explicit addition near C-7/C-8 (evidence before mechanism / durable before deep are
   both directly load-bearing for this fix) — **left as an open question for the
   implementation branch**, not decided here, since charter changes go through the
   amendment ceremony and this design doc doesn't have standing to pre-empt that.
8. **`tests/test_verify_doc_template.py`** — port spolia's test suite (24+ tests
   including the CRLF regression test), adjusted for sartor's `scripts/` import path.
9. **`CHANGELOG.md`** — implementation branch only (this design doc is docs-only, no
   CHANGELOG entry, matching the `kit-adoption-design.md` precedent).
10. **`feedback-handoff-process.md`** (sartor project memory, not this repo) — update to
    note supersession per decision (v).

---

## 7. Rollout sequencing

Per decision (iv): land as an advisory script first. First real exercise should be the
`feat/handoff-integrity-kit` implementation branch's **own** close-out — i.e. the first
committed file under `docs/dev/handoffs/` should be that branch's own handoff to
whatever branch runs next, mirroring exactly how spolia's `b06-freshrss` became the
kit's first live test in that project. This is deliberately not slotted into
`RELEASE_ARC.md`'s v1.1.0 phase sequence — it's a process/governance change orthogonal
to the version stream, matching the `docs/handoff-carryforward-rule` and
`feat/governance-extraction` precedents (both landed as their own small streams, not ARC
phases). Whether it eventually deserves an ARC line is the owner's call, not this doc's.

---

## 8. Acceptance criteria

- `python -m scripts.gate` green on the implementation branch (ruff/mypy/pytest,
  including the ported test suite).
- A real handoff file, generated and validated (`--event generated`), then consumed and
  validated (`--event consumed`) by the next session, with both events visible in the
  ledger.
- `AGENTS.md` and `AGENT_HANDOFF_TEMPLATE.md` reflect the new flow; the old chat-text
  instruction is gone, not just supplemented.
- `feedback-handoff-process.md` updated to point here.
- This doc's own §2 "reported but not independently re-verified" claim is either
  confirmed or explicitly dropped — not carried forward silently a third time.

---

## 9. Open items for the implementation branch

- Charter amendment for the new binding rule (§6 item 7) — needs the owner's amendment
  ceremony, not pre-decided here.
- Whether to eventually escalate the validator to a `SessionStart` hook (mirroring
  `restore-evidence.sh`'s pattern) — explicitly deferred per decision (iv); revisit only
  if the advisory step is observed being skipped.
- The RELEASE_CHECKLIST.md truncation claim (§2) — verify or drop.

## 10. Addendum (2026-07-18): the pointer line's hash was a separate, unhardened channel

This design hardened the **file** transfer — content that must survive verbatim now
travels as a committed, fingerprint-validated artifact, not a clipboard paste — and that
part held up: a real-world corruption attempt on that channel has not recurred since
`feat/handoff-integrity-kit` shipped. But the one-line **pointer** itself (`Handoff: <path>
@ <branch> (<short-hash>)`, §5 iii above) was left as agent-typed prose, with no mechanism
forcing or checking its commit hash. That gap was hit for real on `fix/plan-approval-hook-scope`'s
own handoff: the closing agent fabricated a short hash from pattern completion after a
`git merge --no-ff` whose output doesn't include one — full evidence in
[`diagnosis/handoff-pointer-verification.md`](diagnosis/handoff-pointer-verification.md).
Closed on `fix/handoff-pointer-verification`: `scripts/print_handoff_pointer.py` generates
the line from git directly, and `scripts/check_handoff_pointer.py` independently
re-verifies it against git state on both the generation and consumption side. Two different
integrity problems, two different fixes — the file-transfer fix does not cover the pointer
line, and vice versa.
