```toml
schema = 1
id = 5
kind = "item"
title = "Grounding-score persistence gap blocks calibrated L1/L2 metric layers"
status = "blocked"
decision_owner = "agent"
blocked_on = "the annotate-flow scorer never writes NLI/MiniCheck scores back into the fixture's annotations.json"
refs = ["docs/dev/RELEASE_CHECKLIST.md:1458-1497", "blueprints/diagnostics.py:119-156", "evals/README.md"]
summary = "First diagnosed 2026-07-09 on robert-bootstrap; independently re-found 2026-07-28 on the SAME fixture, still unfixed."
```

This is a single bug found twice, three weeks apart — a direct, concrete
illustration of why this tracking system exists. The 2026-07-09 ledger entry
(`docs/diagnostics-round2-capture`) diagnosed it first: "both automated
grounding signals (NLI + MiniCheck) are 100% null, an annotate-flow
persistence gap (the scorer works in the eval result records; the scores
never write back to the fixture)." It was "folded into the v1.0.9
Diagnostics-DX thread" and never updated again.

2026-07-28 (this session), exercising the same `robert-bootstrap` fixture
independently, found the identical symptom: `annotations.json`'s per-bullet
`minicheck_grounding_score`/`nli_entailment_score` fields are null across
all 32 bullets despite `bootstrap.json`'s `grounding_signals` block having
full scores (mean NLI 0.97, mean MiniCheck 0.90). `_patch_annotation_scores`
(`blueprints/diagnostics.py:119-156`) is correctly implemented and should
patch by `cluster_index` — the gap is in call ordering between when
grounding scoring runs and when `annotations.json` gets saved, not the patch
logic itself. Root-causing the exact ordering (does Save-annotations.json
overwrite a patch that already landed, or does Score-grounding run before
`annotations.json` exists?) is the next step, not yet done.

Consequence: `improvement_brief.md`'s "Scorer agreement" section is
vacuously "no disagreements" — there are no scores to compare against, not
zero real disagreements. Independently found at least one real disagreement
by cross-referencing `bootstrap.json` directly: a bullet about mentoring
students whose work won Academy Awards scored MiniCheck 0.03 (near-total
non-entailment) yet was correctly human-verdicted "keep" — a Category-2
(categorization, not invention) false-negative from the lexical scorer,
matching `COMPOSE_REWRITE_DIAL.md`'s predicted metric-conflict.

Blocks the L1/L2 calibrated grounding metric layers (PV-2,
`eval/grounding-calibration`) — no reliable labeled data can accumulate
while scores don't persist.

## Updates

### 2026-07-28 — filed during chore/work-item-tracking (migrated + merged with independently re-found evidence)
