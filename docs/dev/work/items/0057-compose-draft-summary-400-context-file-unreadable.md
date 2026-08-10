```toml
schema = 1
id = 57
kind = "item"
title = "UX flake: /draft-summary 400 'Context file unreadable' — a reader-side signature the settle-hole diagnosis explicitly excluded"
status = "watching"
decision_owner = "agent"
epic = 19
refs = [
  "tests/ux/regression/test_20260706_compose_summary_draft.py",
  "docs/dev/diagnosis/compose-summary-draft-settle-hole.md",
  "blueprints/applications.py",
  "hardening.py",
]
summary = "400 on a context file that exists: JSONDecodeError/OSError on read. Settle-hole dossier's O-3 had zero non-2xx."
```

Observed 2026-08-08 on `docs/epic-a-chain-design-corrections` (a docs-only branch — no
production code in the diff, so this is not caused by the branch that saw it).

## Observed

Full `pytest -m ux` run: **1 failed, 137 passed, 2 xfailed in 476.69s**.

```
FAILED tests/ux/regression/test_20260706_compose_summary_draft.py::
       test_compose_summary_draft_autofills_edits_and_persists
AssertionError: POST /draft-summary returned 400: {"error":"Context file unreadable"}

[ux] non-2xx /api/ responses observed during this test:
  400 POST http://127.0.0.1:51749/api/applications/1/draft-summary
```

Re-run of that single test in isolation (`-p no:randomly`): **1 passed in 20.20s**.

Both results recorded per AGENTS.md's UX-flake rule; not a gate failure, and deliberately
not patched around.

## Why this is not the already-diagnosed defect

`docs/dev/diagnosis/compose-summary-draft-settle-hole.md` solved a failure in this *same
test*, but with the opposite signature:

- **O-3** of that dossier: "There were **zero** non-2xx `/api/` responses anywhere in the
  entire UX tier ... Every route returned 200 and the data still vanished."
- **F-3**: a torn read "genuinely 400s", but that was explicitly **falsified** as the cause
  of the settle hole — `write_context_atomic` was kept because it closes a *different*,
  real hole.

This observation is a **400**, so it is the F-3-shaped hole, not the O-3-shaped one. Citing
the settle-hole dossier as covering it would be wrong.

## Inferred — unproven, do not cite as cause or fix against

The 400 is raised at `blueprints/applications.py:1537-1540` (and eleven sibling sites with
identical shape) **after** `cp.exists()` has already passed — so the file is present and the
failure is in `json.loads(cp.read_text(...))`, i.e. `JSONDecodeError` **or** `OSError`.

O-6 of the settle-hole dossier measured that `os.replace` yields **0 torn reads on every
platform**, which makes `JSONDecodeError` the less likely of the two. The same measurement
recorded that on **Windows** a replace fails with `PermissionError` while another handle is
open — and `hardening.py` carries `_REPLACE_ATTEMPTS = 12` / `_REPLACE_BACKOFF_S = 0.004`
precisely to retry it.

**The hypothesis worth testing first — and only a hypothesis:** the retry is on the
**writer** side only; the **reader** (`cp.read_text()`) has no equivalent retry, so a reader
landing inside a concurrent replace window could raise `PermissionError` (an `OSError`) and
surface as exactly this 400. That would make it **Windows-only**, which is consistent with
it never having been seen on Linux CI.

**None of this is verified.** An instrument that distinguishes `JSONDecodeError` from
`OSError` at the raise site — and records `errno`/`winerror` — is the first commit any fix
branch owes. The two mechanisms imply different fixes, and the dossier above is a worked
record of what picking the plausible one costs.

## Why it was not chased here

`RELEASE_ARC.md` cadence: discoveries are **filed, never chased** mid-branch, and item 19
owns UX-suite flake work. The branch that observed this is a documentation recovery with no
production code; instrumenting a Flask route from it would be scope creep on top of an
unproven mechanism.
