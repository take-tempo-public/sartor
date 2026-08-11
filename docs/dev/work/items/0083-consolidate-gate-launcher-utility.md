```toml
schema = 1
id = 83
kind = "item"
title = "Consolidate the ad hoc nohup+redirect+poll gate-launch pattern into one canonical utility"
status = "watching"
decision_owner = "user"
refs = [
  "docs/dev/epic-a-chain-design-corrections.md",
]
summary = "F1/F2/F3/F5/F11/F13 each independently got a different piece of backgrounding wrong; codify the pattern once."
```

**The pattern.** Epic A's friction register (`docs/dev/epic-a-chain-design-corrections.md`
§12.2) documents **six separate findings**, each an independent mistake in the
same underlying task — launching `python -m scripts.gate` detached and
polling it reliably on this machine:

- **F1** — a subagent ran the gate itself and returned a non-report when its
  own context compacted mid-run.
- **F2** — `| tee` died with the harness's Bash wrapper while the gate kept
  running headless, writing nowhere; produced two false mechanisms in a row.
- **F3** — `kill -0 <pid>` is invalid on Windows PIDs under Git Bash, so a
  waiter built on it returned instantly and lied; a second gate raced the
  first on 1.35 GB free RAM.
- **F5** — background waiters were culled unpredictably regardless of their
  stated timeout.
- **F11** — a detached gate emits no completion signal the harness surfaces;
  ~40 minutes of dead wall-clock before anyone noticed it had finished.
- **F13** — the harness's own `run_in_background` is not equivalent to
  `nohup … &`; a gate launched via the former was culled wholesale mid-run
  even with a correct `> file 2>&1` redirect.

**The pattern, not the instances, is the problem.** §11.9 now carries the
accumulated prose lessons ("launch it detached with `nohup … > file 2>&1 &`
from a foreground call, never `| tee`, never the harness's own
`run_in_background`, poll in short windows with `tasklist`/`Get-CimInstance`
not `kill -0`") — but as **prose**, not code, meaning the next session that
needs to launch a long-running gate has to re-derive or re-remember all six
lessons correctly, in order, under time pressure, exactly the condition each
of the six findings above was produced under.

**Candidate shape, not evaluated or endorsed:** one script
(`scripts/run_gate_detached.py` or similar) that launches the gate correctly
by construction — `nohup`-equivalent detachment, direct `> file 2>&1`
redirect, a poll loop using a Windows-correct liveness check, and a
completion signal the harness can actually surface — so a future session
calls one command instead of reconstructing six independently-learned
lessons.

**No mechanism authored here** — new production tooling, out of scope for a
governance-interval branch. `decision_owner = "user"` — a new tooling
investment.

## Updates

### 2026-08-11 — filed during the pre-Epic-B robustness design pass

Filed as a recommended follow-on branch from the pass's full-lifecycle
friction review (`docs/dev/epic-a-chain-design-corrections.md` §16).
