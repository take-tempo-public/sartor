```toml
schema = 1
id = 79
kind = "item"
title = "scripts/ci_wait.py crashed twice in one session on wrapper faults -- correct verdict, failed delivery, exit 2 indistinguishable from a real bug"
status = "watching"
decision_owner = "agent"
refs = [
  "scripts/ci_wait.py",
]
summary = "ci_wait's verdict was right twice but delivery crashed on encoding + TLS faults, both requiring a manual re-run."
```

**Why this matters.** `scripts/ci_wait.py` is the sanctioned, single
definition of "the PR is green" (AGENTS.md close-out step 4) -- every other
mechanism (a hand-rolled watcher, a poll loop, a `gh pr checks | jq`
one-liner) is explicitly disallowed. Its *verdict* was correct both times
below, but its *delivery* failed twice in the same session while it was
load-bearing for Epic A's PR #117.

**Fault 1 -- encoding.** `UnicodeEncodeError: 'charmap' codec can't encode
character 'β'` while dumping a failing check's log tail. This is the
known Windows cp1252-stdout class (see
`reference-windows-console-unicode-print-crash`). It exited **2** (wrapper
error) instead of **1** (failing check), and truncated the log tail exactly
when it mattered -- the one moment a human needs the most detail.

**Fault 2 -- transient network.** `RuntimeError: gh pr checks ... produced
no JSON (exit 1): Post "https://api.github.com/graphql": tls: failed to
verify certificate: x509: certificate signed by unknown authority` -- a
transient TLS fault on a poll cycle, again exiting **2**.

**Both required a manual re-run** to obtain a clean, trustworthy verdict.

**The actual risk.** Exit code 2 is documented as "wrapper error" and is,
by design, indistinguishable from a genuine bug in the wrapper itself. An
agent under time pressure who sees exit 2 with partial, truncated output
has no cheap way to tell "the check state is fine, the reporting layer
choked" from "something is actually wrong with the PR or the script." The
existing exit-code contract (0 = green, 3 = green-after-retries, 1 =
failing check + log tail, 2 = wrapper error, 8 = deadline) does not
currently distinguish "crashed while already holding a known verdict" from
"crashed before determining one" -- both collapse to 2.

**Candidate directions -- record, do not design or endorse here:**

- Force UTF-8 on `ci_wait.py`'s own stdout so non-ASCII log content (test
  names, check output, third-party library messages) cannot crash the
  reporting path.
- Retry transient network/TLS faults during a poll rather than aborting
  the whole run on the first one.
- Distinguish, in the exit code or output, "crashed while reporting a
  KNOWN verdict" (safe to treat as informational) from "crashed before a
  verdict was determined" (must be treated as unknown, not green).

## Updates

### 2026-08-10 -- filed following Epic A close-out (PR #117, merge commit 162c1dc)

Filed as a reliability finding from the post-Epic-A review; both faults
were observed directly during the PR #117 CI-wait cycles, not inferred.
`decision_owner = "agent"` -- the fix shape (encoding, retry policy, exit
code semantics) is an engineering call on the sanctioned tooling, not a
product or governance decision.
