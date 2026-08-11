```toml
schema = 1
id = 86
kind = "item"
title = "Four stale load-bearing claims in extraction/governance docs reconciled to HEAD"
status = "closed"
decision_owner = "agent"
branches = ["docs/extraction-governance-drift-reconcile"]
refs = [
  "docs/dev/EXTRACTION.md",
  "docs/dev/governance-extraction-design.md",
  "docs/governance/enforcement.md",
  "docs/dev/kit-adoption-design.md",
]
closure_exception = "agent, this session (2026-08-11) -- docs-only prose reconciliation has no automated verifier for factual accuracy; verification was four manual checks against HEAD (recorded below and in the branch handoff), not a repeatable gate. scripts.gate / scripts.work_items check confirm the repo stays structurally green, not that the prose is correct."
resolution = "Four claims verified stale against HEAD and reconciled at their canonical home per governance-extraction-design.md's own cite-don't-re-fix rule (single-home): (1) EXTRACTION.md's recall/ 'design-only, not committed' -> committed + boundary-lint green (tests/test_recall_boundary.py, 5/5 verified this session); (2) EXTRACTION.md's 'compliance agent does not exist yet' -> points at agents/compliance-witness.md + commands/compliance-witness.md (shipped 4e8b1df, Sprint 7.7); (3) governance-extraction-design.md Sec5's portable-enforcement-core framed as pending -> status note added, past tense, pointing at enforcement.md as canonical (migration landed 2026-07-08 on feat/portable-enforcement-core); (4) enforcement.md's 'CI latent until the git remote activates' -> corrected in place (canonical home) -- live branch protection verified via gh api, 6 required contexts, strict:true; AGENTS.md's live-CI description was already correct, needed no edit. Two bonus same-class findings folded in: enforcement.md's stale '4 required checks' -> 6; kit-adoption-design.md's header blockquote contradicting its own DOC-STATUS banner, and a matching 'no remote' claim in its temporal map, both reconciled to point at the DOC-STATUS/enforcement.md instead of re-asserting. Also retired a Callback->Sartor rename survivor found in the same file (EXTRACTION.md:114, product sense, per doc-style-guide.md Sec1)."
summary = "Four stale extraction/governance claims verified against HEAD and reconciled at their canonical home, cite-don't-re-fix."
```

**Origin.** An external read-only survey (isidium architecture-research phase,
2026-08-11) reviewed sartor's extraction/governance docs and surfaced four
claims it judged stale. Per C-7, each was verified against HEAD independently
before any edit — none were trusted on the survey's word alone.

**Verification method, per finding (all against HEAD `3fa20a3`, this
session):**

1. `recall/` committed status — `ls recall/ recall/sources/`; ran
   `pytest tests/test_recall_boundary.py -q` → 5 passed. Second-consumer gate
   checked via `grep -rn "recall.assemble\|import recall"` across the tree —
   only in-repo consumer found (`blueprints/assistant.py`); left open, not
   upgraded (C-12 — declared, not filled).
2. Compliance agent existence — `ls agents/compliance-witness.md
   commands/compliance-witness.md`; `git log --diff-filter=A` for the add
   commit (`4e8b1df`, 2026-06-16).
3. Portable-enforcement-core landed state — `ls scripts/enforcement/guards
   scripts/enforcement/adapters scripts/enforcement/ci_backstop.py`;
   cross-checked against `enforcement.md`'s own "Implementation status"
   paragraph, which already recorded the landing (internal contradiction
   within the same file — §5 vs §"Implementation status" disagreed before
   this fix).
4. Live vs latent CI — `gh api
   repos/take-tempo-public/sartor/branches/main/protection` (note: the repo
   owner is `take-tempo-public`, not the git user's account — an early probe
   against the wrong owner 404'd and needed correcting first). Returned live
   protection: 6 required contexts, `strict: true`. Cross-checked against PR
   #123's actual `statusCheckRollup` (merged this session) showing real,
   passing check runs.

**Scope guard honored.** Docs-only branch; no code, no prompt constants, no
charter clause text touched. No dependency or path reference to the external
project added (self-containment) — its existence is noted only as empirical
provenance for the `recall/` second-consumer gap.

## Updates

### 2026-08-11 — filed and closed same session, `docs/extraction-governance-drift-reconcile`

Filed and closed together: this item exists to keep the board's record of
"why these four files changed" durable, not to track open work — the
reconciliation is the branch's entire content and is already done at filing
time.
