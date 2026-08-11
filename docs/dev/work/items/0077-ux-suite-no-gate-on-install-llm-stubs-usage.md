```toml
schema = 1
id = 77
kind = "item"
title = "Nothing asserts a UX test that can reach an LLM route actually calls install_llm_stubs -- third instance of this class"
status = "watching"
decision_owner = "agent"
refs = [
  "tests/ux/stubs.py",
  "tests/test_ux_stub_coverage.py",
  "tests/ux/flows/test_dashboard_console.py",
  "tests/ux/flows/test_output_surface_seeded.py",
  "logs/llm_calls.jsonl",
]
summary = "pytest -m ux is documented LLM-free; nothing gates that each LLM-reachable UX test calls install_llm_stubs."
```

**How this was found.** Epic A's PR was red because
`test_resumed_application_with_a_frozen_composition_can_reach_step5` omitted
`install_llm_stubs`, so a resumed application drove `loadComposition()` ->
the positioning-draft auto-fire -> the REAL
`analyzer.draft_positioning_summary`. Locally, with `.api_key` present, that
was a **billed** Sonnet-5 call that returned 200 and the test PASSED; in CI
(no key) the SDK raised `TypeError` at request-build -> unhandled 500 ->
red. **7 confirmed billed rows for fixture user `alice` in
`logs/llm_calls.jsonl`** trace to this test before it was fixed.
`pytest -m ux` is documented LLM-free and offline
(`AGENTS.md` / `CLAUDE.md` "Testing and validation") -- this test broke that
contract silently, and only a CI cost/behavior divergence surfaced it.

**What the existing gate covers, and what it doesn't.**
`tests/test_ux_stub_coverage.py` (added by A3 for board item 34) asserts the
*blueprint `_get_client` list* is complete -- i.e. every blueprint that can
construct an Anthropic client is enumerated. Its own docstring discloses
this does NOT prove every analyzer entry point is stubbed, and it says
nothing about which **UX tests** actually call `install_llm_stubs`
(`tests/ux/stubs.py:488`). A blueprint being stubbable and a specific test
actually stubbing it before driving a flow that can reach it are two
different claims, and only the first one is checked.

**The enumeration, measured this session (heuristic, not a gate).** Of 59
files under `tests/ux/**`, **33 never call `install_llm_stubs`** at all.
Of those 33, **13 reference at least one LLM-route trigger** (keyword scan
for the routes/handlers that can fire an analyzer call) and are the real
candidates for the same failure class:

- `flows/test_dashboard_console.py`
- `flows/test_output_surface_seeded.py`
- `regression/test_20260604_template_pagination.py`
- `test_20260611_diagnostics_chart_corrections.py`
- `test_20260611_prior_app_resume_robustness.py`
- `test_20260616_assistant_panel.py`
- `test_20260619_assistant_no_user.py`
- `test_20260706_new_tailoring_reset.py`
- `test_20260706_refinement_scope_modal.py`
- `test_20260707_recruiter_roster_pipeline.py`
- `test_20260708_review_surface_and_flows.py`
- `test_20260711_dashboard_assistant.py`
- `test_20260725_merge_suggestions_render_cap.py`

**Record explicitly: this list came from a keyword heuristic that
over-approximates.** It is a starting point for triage, not the gate's
logic -- some of the 13 may already be safe by construction (e.g. a route
gate that can't fire given the fixture state, the same shape that bounded
item B below), and the heuristic itself may be missing trigger patterns it
didn't know to look for.

**Why this is a C-11 case, not a fresh finding.** This is the *third*
instance of the same failure class -- board items 21, 22, and 34 are the
prior history of a missing new-call-kind leg going unstubbed and reaching a
real LLM client. Each time, the response has been a note plus a partial
gate (item 34's blueprint-level `_get_client` enumeration was exactly that
kind of response, and its own docstring says so). C-11: "a constraint with
no mechanism that fails closed is not a constraint" -- a fourth recurrence
of this class is now a named risk, not a surprise, and the honest framing
is that no fail-closed mechanism exists yet for "this specific test, which
can reach an LLM route, called the stub."

**Candidate shape, not evaluated or endorsed:** a static or runtime check
that cross-references (a) which routes/handlers a UX test's Playwright
actions can reach (via the URLs/selectors it drives, or via an allowlist of
known LLM-triggering actions) against (b) whether `install_llm_stubs` (or
an equivalent monkeypatch) ran in that test's setup -- failing the suite
if a test can reach (a) without (b). This is materially harder than the
blueprint-level check because it requires reasoning about test *behavior*,
not just import-time client construction; that's likely why item 34's fix
stopped at the easier boundary.

## Updates

### 2026-08-10 -- filed following Epic A close-out (PR #117, merge commit 162c1dc)

Filed as the primary finding from the post-Epic-A review. `decision_owner =
"agent"` -- deciding the shape of the missing gate is an engineering
judgment call (how to detect "this test can reach an LLM route" without a
prohibitive false-positive rate), not a product or governance call.
