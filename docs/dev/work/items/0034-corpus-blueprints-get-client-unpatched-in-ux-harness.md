```toml
schema = 1
id = 34
kind = "item"
title = "Corpus blueprints' _get_client is never patched in the UX test harness"
status = "watching"
decision_owner = "agent"
refs = [
  "blueprints/corpus/skills.py:29",
  "blueprints/corpus/proposals.py:22",
  "tests/ux/stubs.py:install_llm_stubs",
  "docs/dev/diagnosis/never-logged-call-kinds.md",
]
summary = "install_llm_stubs patches _get_client on 4 blueprints but not the corpus ones - real API risk if ever hit."
```

Found 2026-08-03 while diagnosing item 22 (`fix/never-logged-call-kinds`). `tests/ux/stubs.py::install_llm_stubs` patches `_get_client` to `lambda: None` on the analysis, generation, diagnostics, and applications blueprint modules — but `blueprints/corpus/skills.py` and `blueprints/corpus/proposals.py` each import `_get_client` at module load time, and neither is covered by any of those four patches.

This is a worse variant of the same shape as the (separately filed, prophylactically fixed) `draft_surgical_refinement` UX-stub gap: that one risks an uncaught `AttributeError`/500 against a `None` client. This one, on a developer machine with a valid `.api_key` present (confirmed the norm — this repo's own `CLAUDE.local.md` documents `.api_key` at the project root), risks a **real, billed Anthropic API call** the moment any future UX test drives `POST /api/users/<username>/skills/suggest-from-corpus` or the clarification-promotion route in `blueprints/corpus/proposals.py` — silently, with no test assertion pointing at cost.

Latent today: a grep of `tests/ux/` found no test currently reaching either route, so there is nothing to reproduce. Filed rather than fixed on the branch that found it, per one-item-per-branch discipline (item 22's own scope was the telemetry gap, not this).

## Updates

### 2026-08-03 — filed during fix/never-logged-call-kinds
