```toml
schema = 1
id = 70
kind = "item"
title = "`tests/test_ux_stub_coverage.py`'s AST walker only matches `from web_infra import _get_client` -- a module-attribute form would evade it in either direction (minor, not exploitable today)"
status = "watching"
decision_owner = "agent"
refs = [
  "tests/test_ux_stub_coverage.py",
]
summary = "Every current blueprint uses the matched ImportFrom form; an attribute-access blueprint would escape the gate."
```

**The gate, and its blind spot.** `tests/test_ux_stub_coverage.py::_binds_get_client`
(`tests/test_ux_stub_coverage.py:57-72`, added on `feat/role-summary-drafting`, A3, as
the C-11 fail-closed mechanism for item 34's class) walks each `blueprints/**.py`
module's AST and matches only `ast.ImportFrom` nodes of the shape
`from web_infra import _get_client` (bare or parenthesized, module-level or local). It
does not match `import web_infra` followed by attribute access
(`web_infra._get_client()`) anywhere in the module body.

**Why this matters in both directions of the gate's own assertion.** The test asserts
an exact-set equality between "modules that bind `_get_client`" (as the walker finds
it) and "modules `install_llm_stubs` patches"
(`tests/test_ux_stub_coverage.py:86-106`):

- A future blueprint written as `import web_infra` + `web_infra._get_client()` would
  not be flagged as binding the name, so it could go unpatched by
  `install_llm_stubs` and reach a real, billed Anthropic API call under `pytest -m ux`
  on a machine with a live `.api_key` -- the exact failure mode item 34 and this gate
  exist to close, just via the one import form the walker does not recognize.
- Symmetrically, if such a module *were* added to `_GET_CLIENT_BLUEPRINT_MODULES` by
  hand (anticipating the need) but never actually bound the name via `ast.ImportFrom`,
  the walker's `found` set would never contain it, and the "stale entry" assertion
  (`:101-106`) would falsely fire even though the module genuinely needs patching --
  a false positive in the disclosure direction, not just a false negative in the
  coverage direction.

**Not exploitable today, checked directly.** Every module currently under
`blueprints/**.py` that resolves `_get_client` does so via the matched
`from web_infra import _get_client` form -- confirmed by the walker itself finding
`>= 4` modules and the exact-set assertions passing at HEAD (`fab794d`,
`python -m scripts.gate`, all steps passed). No blueprint in this repo uses the
module-attribute form. This is a latent gap in the gate's own coverage, not a live
unstubbed call path.

**Disclosure added to the test's own docstring on this branch** (trivial, doc-only):
`_binds_get_client`'s docstring now states the module-attribute form is unmatched,
pointing at this item, so the limit is stated where the mechanism lives rather than
only in this file (charter C-0 -- a mechanism's stated limits belong next to the
mechanism).

**Candidate fix, not evaluated or endorsed:** widen `_binds_get_client` to also walk
for `ast.Import` nodes binding the module name `web_infra` and then check the
function/module body for `ast.Attribute` access chains resolving to
`<bound-name>._get_client`. Low priority: no blueprint uses the pattern today, and
the fix is a pure test-harness hardening with no production-code change.

## Updates

### 2026-08-09 — filed at `feat/role-summary-drafting` close-out (Epic A, sprint A3)
