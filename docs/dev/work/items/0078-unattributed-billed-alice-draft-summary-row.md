```toml
schema = 1
id = 78
kind = "item"
title = "Unattributed billed alice/draft_summary row in llm_calls.jsonl, 2026-07-28 -- source unresolved, leading hypothesis unverified"
status = "watching"
decision_owner = "user"
refs = [
  "logs/llm_calls.jsonl",
  "tests/ux/seeding",
  "tests/conftest.py",
]
summary = "One alice/draft_summary billed row predates the fixed test and doesn't match its token shape -- source unresolved."
```

**The row.** `logs/llm_calls.jsonl` carries one `alice`/`draft_summary` row
at **2026-07-28T22:11:33** with token shape in=1235/out=102. This is
different from the 7 rows the (now-fixed)
`test_resumed_application_with_a_frozen_composition_can_reach_step5`
produced -- those are uniform in=1149/out=10 -- and this row **predates**
that test, which was committed 2026-08-09 (`3e2b8a5`). So the 7-row leak
documented in item 77 does not explain this one; it is a separate,
unattributed billed call.

**Bounded investigation, ruled out this session:**

- No other real call within +-45 minutes of the timestamp.
- No persistent `output/alice/` directory on disk -- `alice` is
  fixture-only, so this isn't a real user's application.
- The two stubless UX files that resume an `alice` application both fail
  the gates guarding the positioning-draft auto-fire:
  `_resumeIntoStep6` only calls `loadComposition()` `if (rs.has_composition)`,
  which needs `composition_overrides` or `llm_recommendations`, and
  hydration returns `None` without `llm_analysis` -- a gate present since
  `0a2e724` (2026-07-08), well before this row's timestamp.

**Leading hypothesis -- explicitly NOT verified, do not treat as the
answer.** A one-off, manually-run sandboxed app walkthrough using the
`tests/ux/seeding` helpers as a standalone script rather than through
pytest. If run that way, `tests/conftest.py`'s autouse `LOG_PATH` redirect
(which keeps test-driven LLM calls out of the real log) would not apply,
and a real call would write to the production `logs/llm_calls.jsonl`
exactly as observed. This fits the facts (fixture-only user, single
isolated row, no matching test) but **no artifact confirms it** -- no
shell history, no session transcript, no script run log was found or
checked that would prove a human or agent actually ran such a script at
that timestamp.

**Why this is filed as open, not closed with a hypothesis.** Per C-12,
information not held is surfaced as missing rather than filled in as
premise. The hypothesis above is plausible and is the best current
candidate, but presenting it as resolved would be exactly the failure
pattern C-12 exists to prevent -- a plausible mechanism standing in for an
observed one.

**Decision needed from the owner:** whether this is worth further
investigation (e.g. checking for any local shell/session history around
2026-07-28T22:11, or asking whether a manual walkthrough was run that day)
or worth accepting as unresolved and closing as a dead end.

## Updates

### 2026-08-10 -- filed following Epic A close-out (PR #117, merge commit 162c1dc)

Filed as an open, unresolved finding from the post-Epic-A review.
`decision_owner = "user"` -- whether to spend more investigation effort on
a single, low-cost, already-bounded anomaly (versus accepting it as an
unresolved dead end) is the owner's call, not a mechanical one.
