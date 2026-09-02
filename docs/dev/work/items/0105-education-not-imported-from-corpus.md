```toml
schema = 1
id = 105
kind = "item"
title = "Corpus import produced bullets and skills but no education entries"
status = "open"
decision_owner = "agent"
branches = ["docs/container-persistence-guidance"]
refs = [
  "corpus_to_json_resume.py:906",
  "blueprints/corpus/_shared.py:270",
  "onboarding/corpus_import.py",
]
summary = "Corpus import produced bullets and skills but no education rows; parse-vs-persist not yet distinguished."
```

**Observed by the owner during a live import** (2026-09-02, macOS native install). Bullets
and skills imported correctly. Education did not appear.

**Two rival explanations, not yet distinguished** — the owner explicitly flagged this as
unresolved: either the source document's education section was never parsed, or it was
parsed and never persisted through the import path.

**Distinguishing evidence needed** (do not fix before collecting it, C-7): whether education
rows exist in the DB at all, versus reaching the proposal/review stage and being dropped
there. Instrument the import run; do not reason from the code alone.

**Candidate mechanism — HYPOTHESIS, not a finding.** `Education` is documented in two places
as lacking the pending-review/curation lifecycle the other corpus entities carry:
`corpus_to_json_resume.py:906` ("`Education` (db/models.py) has no pending-review/curation
lifecycle") and `blueprints/corpus/_shared.py:270`. If the import flow routes everything
through proposal-and-review, an entity with no review lifecycle is the right shape to be
silently dropped while bullets and skills — which have one — come through. **This is
read-from-code plausibility about a run nobody has inspected.** It is exactly the kind of
plausible mechanism C-7 exists to stop being treated as the diagnosis.

**Good signal worth keeping:** bullets and skills landing clean narrows this to something
specific to education rather than a broken import path.

## Updates

### 2026-09-02 — filed at owner request during a live install session

Owner's words: "not sure if it just wasn't parsed or missing from import." Filed as a thing
to verify, not a defect with a known cause.
