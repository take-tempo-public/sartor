```toml
schema = 1
id = 108
kind = "item"
title = "scripts/gate.py should refuse to start below a free-memory floor instead of dying mid-run as a mystery kill"
status = "open"
decision_owner = "agent"
branches = ["docs/first-run-account-naming-finding"]
depends_on = [1]
refs = [
  "scripts/gate.py:22-36",
  "docs/dev/work/items/0001-gate-unrunnable-by-agent.md",
]
summary = "Gate dies mid-run as an OOM'd xdist worker; add a fail-closed free-memory preflight that refuses to start."
```

**Observed** (2026-09-02, this machine). Four consecutive attempts to run
`python -m scripts.gate` on a docs-only branch failed to complete. No test failed.
The decisive artifact, from the fourth attempt:

```
[gw0] node down: Not properly terminated
```

That is an xdist worker killed by the OS at 73% through the non-UX tier, not a test
failure and not a flake. Free physical memory fell from 1.8 GB to 0.7 GB across the
attempts on a 15.7 GB box. The competing load was identified: a **sibling project's**
gate running concurrently in the same OS —
`C:\Dev\spolia\.venv\Scripts\python.exe scripts/gate.py` plus its pytest child.
`-n auto` spawns one worker per core, and the box could not feed them.

**Why this is a recurrence, not a first sighting.** Item 1 already records "gate
unrunnable by agent," and `scripts/gate.py`'s own docstring (lines 22-36) says the
plainest version of the problem:

> the full suite's real runtime is ~30min … long enough that a foreground/short-timeout
> agent call always got cut off — **which every prior session read as a mysterious kill,
> when it was really just an unmeasured runtime.**

The docstring diagnosed the *runtime* half and left the *resource* half uncovered. Three
of this session's four attempts were misread exactly as the docstring predicts — as
unexplained kills — until the fourth produced the `node down` line. The message reads like
a flake and is actually memory exhaustion, which is what makes it cost a session every time.

**The mechanism (owner-approved 2026-09-03, not yet built).** A **fail-closed preflight**
in `scripts/gate.py`, before the pytest steps: read free physical memory, and if it is
below a floor, **refuse to start** and print what is holding the memory — naming any other
`python.exe` running a gate or pytest, since a sibling project's suite is the observed
culprit. Refusing up front converts a 30-minute mid-run mystery into an immediate, legible
message.

**Design notes, not decisions** (whoever builds this makes the calls, and should measure
rather than inherit these):

- The floor is a number nobody has measured. Derive it from an actual observation of what
  `-n auto` peaks at on this box, and say in a comment where the number came from — an
  unmeasured threshold is the same class of defect as the one being fixed.
- Consider whether the right response below the floor is a hard refusal or a documented
  fallback to a lower `-n`. A refusal is fail-closed and therefore C-11-compliant; an
  automatic fallback silently changes what "gate green" means, which is worse.
- Keep it stdlib-only if possible. `os.cpu_count()` is stdlib; free physical memory is not
  portable stdlib, so this may need a platform branch or a small dependency — weigh that
  against the value, and if it lands as a dependency it needs a `pyproject.toml` entry plus
  a `CHANGELOG.md` line.
- The preflight must not itself become a reason a legitimate gate run is blocked. An
  override exists in this repo's tradition only when the owner explicitly directs it; do
  not add an env-var hatch on your own initiative.

**Stated limit (C-0).** This closes the "you cannot tell why it died" gap. It does not make
the gate runnable on a loaded machine — the operator still has to free memory or wait. That
is the correct scope: the defect is the illegibility, not the resource contention.

## Updates

### 2026-09-03 — filed at owner direction

Surfaced during a close-out where the gate could not be completed and the branch was
therefore not merged on the agent's own authority. Owner's response: "the mechanism is
sound. log it as a task." Filed rather than built, because building it is a code change on
a docs-only branch and it cannot be gate-verified while the gate cannot run.
