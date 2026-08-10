```toml
schema = 1
id = 51
kind = "item"
title = "Flake-rate budget gate: report --check against a committed threshold"
status = "watching"
decision_owner = "agent"
refs = [
  "scripts/flake_rates.py",
  "docs/dev/flake-rates/README.md",
]
summary = "flake_rates.py is an instrument, not a gate; report --check against a committed budget is a named, unbuilt successor."
```

Filed at close-out of `feat/flake-rate-measurement`, the branch that built the
instrument this item is the successor to — per charter **C-12**, a declared future
capability belongs in a tracked item, not left implicit in a README's prose.

`scripts/flake_rates.py` extracts real per-test, per-attempt CI failure rates into a
committed store (`docs/dev/flake-rates/`), but **nothing built on that branch fails
closed on a test's rate** — deliberately: a threshold cannot be set before there is
data, and the first backfill (30 runs, 2026-08-03 → 2026-08-06) is nowhere near
enough history to set one responsibly. `docs/dev/flake-rates/README.md`'s own LIMITS
section names this gap explicitly rather than letting the store read as enforcement.

**What this item is, when someone picks it up:** a `report --check` mode that exits
nonzero when any test's Wilson lower bound exceeds a committed per-tier budget,
wired into `scripts/gate.py` or CI as an optional/advisory step first. The budget
itself needs enough accumulated history to set without guessing — this is explicitly
**not** ready to build the moment this item is filed.

**Why `watching` and not `open` or `deferred`:** there is no decision blocking it
(`deferred` would need a `blocked_on`) and no active work queued (`open` would claim a
WIP slot) — it needs *time and accumulated data*, not a decision. Escalate once
`docs/dev/flake-rates/runs/` spans enough calendar time and run count that a budget
could be set from real distributions rather than a guess (no fixed number chosen here
on purpose — that number is itself part of the future work, not a precondition to
filing this item).

## Updates

### 2026-08-06 — filed during feat/flake-rate-measurement
