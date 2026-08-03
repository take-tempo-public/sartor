```toml
schema = 1
id = 35
kind = "item"
title = "wiki-freshness gate counts process/provenance churn as drift, tripping on false positives"
status = "closed"
resolution = "Fixed on fix/wiki-freshness-relevance-classification: new scripts/wiki_relevance.py is the single source of truth for whether a changed path counts toward wiki-staleness drift, mirroring tests/test_egress_allowlist.py's SANCTIONED_EGRESS_FILES shape (maintained classification + an audit test that fails on anything unclassified in either direction, tests/test_wiki_relevance_classification.py). scripts/wiki_freshness.py's drift_count() and hooks/wiki-freshness-reminder.sh's post-commit nudge both now call into it instead of independently reimplementing a bare docs/wiki/-only exclusion. Verified end-to-end: recomputing drift on the exact 65b0f88->c8eb74d window that tripped fix/extract-experiences-telemetry-pollution's PR gate (79 files) drops to 12 genuinely wiki-relevant files under the new classification, comfortably under the 75-file threshold, with zero wiki content changes needed. Also added a close-out checklist step (AGENTS.md + docs/dev/AGENT_HANDOFF_TEMPLATE.md) making a scoped /wiki-self-update part of normal per-branch close-out when a branch's own diff touches a wiki-relevant path, so small incremental updates become the norm and the merge-blocking gate is the backstop, not the primary mechanism -- per the user's explicit design direction after two prior branches (2026-07-24, 2026-07-30) hit this same false-positive shape and patched it with one-off manual triage instead of a structural fix."
decision_owner = "user"
refs = [
  "scripts/wiki_relevance.py",
  "scripts/wiki_freshness.py",
  "hooks/wiki-freshness-reminder.sh",
  "tests/test_wiki_relevance_classification.py",
  "tests/test_egress_allowlist.py",
  "docs/dev/diagnosis/wiki-freshness-relevance-classification.md",
  "AGENTS.md",
]
summary = "drift_count() counted process churn (handoffs, ledger, work-items, tests) as drift, tripping the gate 3 times."
```

Found 2026-08-03 while closing out `fix/extract-experiences-telemetry-pollution` (item
33) — its own PR (#96) was blocked by the wiki-freshness gate at "79 files changed,"
despite that branch's own diff being 8 test-only files. The user asked why non-wiki
documents (session handoffs, provenance ledgers) would trip a *wiki* freshness gate at
all, correctly suspecting the measurement rather than the branch. `docs/wiki/log.md`
confirmed this exact false-positive shape had already tripped the gate twice before
(`feat/context-structure-review-skill` 2026-07-24, `chore/wiki-refresh-v109`
2026-07-30), each time patched with a one-off manual file-list triage rather than a
structural fix to the counter itself — guaranteeing recurrence.

Filed and fixed same-day, `decision_owner = "user"` because the user drove both the
design direction (a maintained classification mirroring the egress-allowlist gate,
after two design options were researched and presented) and the close-out-ritual
integration (small incremental per-branch wiki updates, CI gate as backstop only).

## Updates

### 2026-08-03 — filed and closed on `fix/wiki-freshness-relevance-classification`
