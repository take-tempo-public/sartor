```toml
schema = 1
id = 167
kind = "item"
title = "A strict xfail whose controls are bare asserts reports a broken drive as the expected defect, and nothing enforces the convention"
status = "closed"
decision_owner = "agent"
branches = ["fix/recurrence-guardrails"]
refs = [
  "tests/test_regenerate_cover_letter.py",
  "tests/ux/regression/test_20261012_regenerate_keeps_cover_letter.py",
  "tests/test_ux_toast_wait_gate.py",
  "docs/dev/diagnosis/recurrence-guardrails.md",
]
summary = "The ControlFailed + raises=AssertionError convention is prose only; ControlFailed is defined twice."
resolution = "2026-10-14, fix/recurrence-guardrails. ControlFailed and control live once in tests/_controls.py; tests/test_xfail_controls_gate.py fails on a strict xfail without raises=AssertionError (or with Exception, BaseException or ControlFailed), on a module holding one that does not import the shared helper, and on a second ControlFailed definition. The decorator shape is gated; whether each step uses control instead of a bare assert is not mechanizable without a call graph, and is declared so."
verified_by = [
  "tests/test_xfail_controls_gate.py::TestScannerCatchesEachShape",
  "tests/test_xfail_controls_gate.py::TestTheRepo",
]
```

**Observed** (`docs/dev/diagnosis/recurrence-guardrails.md` O5). `ControlFailed` and
`_control` are defined identically in two files
(`tests/test_regenerate_cover_letter.py:61-67`,
`tests/ux/regression/test_20261012_regenerate_keeps_cover_letter.py:70-76`). There is no
`xfail_strict` setting in pyproject, and no test asserts that a strict xfail carries
`raises=`.

**Declared limit (C-0):** "a bare `assert` before the invariant in an xfail test" is not
mechanizable without a call graph through the drive helpers. The gate covers the decorator
shape only: `strict=True` requires `raises=AssertionError`, and the module must import the
shared `ControlFailed`.

## Updates

### 2026-10-14 — filed on `fix/recurrence-guardrails`

First instance of the class, caught while writing the browser arm of item 162 by no
mechanism. C-11 asks for a mechanism on first recognition as a class member.

### 2026-10-14 — closed on `fix/recurrence-guardrails`

The gate passes on the shipped tree by construction (no strict xfail exists at HEAD), so its
teeth are shown two ways: 14 synthetic-source tests, one per shape, and a probe run
(`docs/dev/diagnosis/recurrence-guardrails.md` O14) that dropped a violating file into `tests/`
and got both violations back, then removed it.

**Declared, not mechanized (C-0):** the part of the convention the gate cannot see, a bare
`assert` inside a drive helper, stays prose. It is labeled **unenforced** in `tests/_controls.py`
and in the memory note.
