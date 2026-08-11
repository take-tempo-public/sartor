```toml
schema = 1
id = 20
kind = "item"
title = "Legacy generate() reachable via wizard rail without freezing Compose"
status = "closed"
decision_owner = "agent"
epic = 36
branches = ["fix/wizard-rail-frozen-composition-gate"]
refs = [
  "static/app.js:6958-6965",
  "static/app.js:7002-7011",
  "blueprints/generation.py:786-804",
]
resolution = "Step 5 is hard-gated on `hardening.frozen_composition_doc` - one predicate, one implementation, shared by the rail, the freeze response and /api/generate. Two adjacent gaps deferred as items 66 and 68; the server fallback is tracked as item 67."
verified_by = [
  "tests/ux/regression/test_20260809_wizard_rail_frozen_gate.py::test_step5_rail_is_locked_until_compose_freezes_the_composition",
  "tests/ux/regression/test_20260809_wizard_rail_frozen_gate.py::test_freezing_a_composition_the_server_wont_assemble_leaves_step5_locked",
  "tests/ux/regression/test_20260809_wizard_rail_frozen_gate.py::test_resumed_application_with_a_frozen_composition_can_reach_step5",
  "tests/test_application_routes.py::TestResumeState::test_frozen_flag_agrees_with_the_assemble_gate_on_an_empty_corpus",
]
summary = "Step 5 wizard rail gates only on a context path - skipping Compose still runs the retired full-LLM generate()."
```

Found 2026-07-28 during PX-39 (item 6) pipeline verification. `_wizardReachable`
(`static/app.js:6958-6965`) gates Step 5 (Generate) only on having a context
path — nothing requires passing through Compose or clicking "Save and
continue". A user who analyzes and then jumps straight to Step 5 via the rail
has no `approved_composition`, so `_frozen_composition`
(`blueprints/generation.py:786-804`) returns `None` and the legacy Sonnet
`generate()` call fires — the full-LLM path Charter C-6 / the
frozen-composition re-architecture was meant to retire for corpus-mode users.

The code is aware this happens: `_renderGenerateStepCopy`
(`static/app.js:7006-7011`) swaps Step 5's copy between a "legacy" and
"frozen" variant specifically because both paths are live today, with a
comment at `static/app.js:7002-7004` acknowledging "Generate still runs the
real LLM path, so the copy must NOT claim determinism." So this is a known,
accepted-in-code state, not a mystery — but the owner's framing this session
("that is not appropriate behavior") suggests the current behavior (silently
falling back rather than requiring/nudging the user through Compose) is not
actually the intended end state.

Decision needed: should Step 5 be hard-gated on `_compositionFrozen` (forcing
every corpus-mode user through Compose), or is an explicit warning/redirect
sufficient? This is a product-flow decision, not a mechanical fix — flagging
for the owner's direction rather than picking an approach here.

## Updates

### 2026-07-28 — filed during docs/pipeline-truth-and-era4-baseline, per owner's "not appropriate behavior" framing

### 2026-08-04 — owner direction captured; folded into Final March epic A (sprint A2)

The decision this item was waiting on is made: the owner-approved Final March plan
(`RELEASE_ARC.md` §"v1.1.0 Final March", sign-off via the kickoff PR) directs
hard-gating the Step-5 wizard rail on frozen composition — corpus-mode users go
through Compose. `decision_owner` flipped to agent accordingly; executed as part of
sprint A2 on its own `fix/*` branch with the usual evidence dossier.

### 2026-08-09 — closed on `fix/wizard-rail-frozen-composition-gate`

Executed as its own sprint in the Epic A chain. Evidence dossier:
`docs/dev/diagnosis/wizard-rail-frozen-composition-gate.md`; the instrument
(`tests/ux/regression/test_20260809_wizard_rail_frozen_gate.py`) was the first commit and
failed 3/3 on the base tip.

The fix is **not** the obvious "gate on `_compositionFrozen`". Adversarial review found
that predicate too weak: the client asked only whether `approved_composition` was a dict,
while `/api/generate` additionally requires the context to be corpus-mode and the document
to have content — so a contentless freeze opened the rail onto Step-5 copy promising "no
AI variation" over a run the server then handed to the LLM. Resolved as **one predicate
with one implementation**, `hardening.frozen_composition_doc` (the former
`_frozen_composition` body, moved verbatim), called from all three seams: the generate
gate, `_pre_generate_hydration`'s `has_frozen_composition`, and the `/composition` freeze
response's `frozen` field. It lives in `hardening.py` because `applications.py` cannot
import `generation.py` (cycle via `templates.py`), because that module owns the
`ContextSet` contract, and because the predicate is deterministic — no LLM call added,
C-6 intact.

The original `refs` above are left at their filing-time line numbers rather than
re-anchored; they are the historical evidence trail. Current anchors are the symbols
`static/app.js:_wizardReachable`, `static/app.js:_wizardLockReason`, and
`hardening.py:frozen_composition_doc`.

**Not everything adjacent closed.** Three surfaces were deferred, filed rather than fixed:
item 66 (the sticky-stale client flag), item 67 (the server's legacy fallback, still
reachable by direct POST and deliberately so), item 68 (the lock reason naming Compose
only). Reading this item as "the legacy path is gone" would be wrong — see item 67.

Wiki updated on the same branch: `corpus-to-output-reach`, `frontend-wizard`,
`context-set-contract`, `route-surface`.
