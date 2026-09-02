```toml
schema = 1
id = 102
kind = "item"
title = "sartor --setup's failure summary names both features whenever either step fails"
status = "open"
decision_owner = "agent"
branches = ["docs/container-persistence-guidance"]
refs = ["app.py:160-200"]
summary = "_run_setup names both PDF and recall as degraded whenever either step fails, hiding which one broke."
```

**Observed** (2026-09-02, macOS 12.7.4). `sartor --setup`'s Chromium step failed; the vector
index step succeeded. The closing summary still read:

> Setup finished with warnings (above). `sartor` still runs; PDF export / semantic recall
> may be degraded until resolved.

`_run_setup()` (`app.py:196-199`) prints one fixed string whenever `ok` is false, naming both
features regardless of which of the two steps actually errored. The per-step failure line
above it carries the detail, but the summary — the line users actually read, and the one they
quote when asking for help — flattens it. The user had to be told to `ls db/vector_index/` to
find out whether their search was actually broken.

**Proposed fix.** Track which steps failed and name only those in the summary. The loop
already has the information; it is discarded into a boolean.

## Updates

### 2026-09-02 — filed from a live macOS install session

Cost was small in isolation — one confused exchange — but it landed on a user already five
failures deep, where an ambiguous message about a second broken feature reads as the install
being unsalvageable.
