```toml
schema = 1
id = 20
kind = "item"
title = "Legacy generate() reachable via wizard rail without freezing Compose"
status = "open"
decision_owner = "user"
refs = [
  "static/app.js:6958-6965",
  "static/app.js:7002-7011",
  "blueprints/generation.py:786-804",
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
