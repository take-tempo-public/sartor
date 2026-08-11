```toml
schema = 1
id = 73
kind = "item"
title = "PriorAppsPage.open_detail() coverage-mode shift -- four test files went from UI-click to direct-JS-invocation with zero diff"
status = "watching"
decision_owner = "user"
refs = [
  "docs/dev/blast-radius/prior-apps-pipeline.md",
  "ui_pages/prior_apps.py",
  "tests/ux/flows/test_output_surface_seeded.py",
  "tests/ux/regression/test_20260707_generate_surface_download.py",
  "tests/ux/regression/test_20260708_step6_full_hydration.py",
  "tests/ux/regression/test_20260809_wizard_rail_frozen_gate.py",
  "tests/ux/regression/test_20260707_recruiter_roster_pipeline.py",
]
summary = "open_detail() moved from DOM click to page.evaluate; four files still pass but now cover a direct-JS path, not a click."
```

**What changed.** `feat/prior-apps-pipeline` (Epic A, sprint A4) rewrote
`PriorAppsPage.open_detail()` (`ui_pages/prior_apps.py`) from driving real DOM
— wait for the panel, expand if collapsed, click a real card, wait for the
modal — to calling internal JS directly:

```python
self.page.evaluate("(id) => _showApplicationDetail(id)", app_id)
```

This was the correct fix for the branch's actual problem (the panel it used
to click into is gone, and rerouting through a live Pipeline-row click risked
resetting wizard state some tests build up first — see the dossier's `## The
consumer this enumeration almost missed`). The dossier itself calls this "a
more correct isolation than before, not a workaround." That judgment is not
being second-guessed here.

**What the A4 dossier's row 38 originally understated.** Four test files call
`open_detail()` indirectly (via `resume_application()`) and needed zero code
changes:

- `tests/ux/flows/test_output_surface_seeded.py:74`
- `tests/ux/regression/test_20260707_generate_surface_download.py:204,239`
- `tests/ux/regression/test_20260708_step6_full_hydration.py:114`
- `tests/ux/regression/test_20260809_wizard_rail_frozen_gate.py:343`

Row 38 originally classified this as "no change" with rationale "transparent
once row 11 lands" — mechanically true (nothing errors, nothing references a
removed selector), but it did not say that **what these four files exercise
changed**: before, each drove a real click through the panel into the modal;
after, each opens the modal via direct JS invocation, with no click and no DOM
traversal. `test_output_surface_seeded.py:74`'s own docstring is now stale
evidence of the shift — it still reads *"click the prior app → 'Resume in
wizard' → Step 6"*, but no click occurs anywhere in that path post-A4.

**Current state of coverage.** Post-A4, the only test in the suite that
verifies a user can click their way into the detail modal is
`test_20260707_recruiter_roster_pipeline.py::test_pipeline_board_groups_by_status_and_switches_candidate`.
The orchestrator A/B-verified this test genuinely fails against the pre-A4
behavior — it is a real pin, not a hollow one — but it means the click journey
now rests on exactly one test where it previously rested on five.

**Not a defect in what A4 shipped; a coverage question worth tracking on its
own.** The dossier has been amended (row 38, `## Deferred` #3) to state this
plainly rather than leave it implicit in "transparent." This item exists so
the coverage-mode question is tracked as backlog, not just as a decision
record entry.

**Candidate options, not evaluated or endorsed:** (a) leave as-is — one
click-path test may be sufficient coverage for a single production entry
point; (b) add a second, cheaper click-path assertion to one of the four
converted files so the click journey isn't a single point of failure; (c)
rename/update the stale docstring in `test_output_surface_seeded.py` regardless
of (a)/(b), since it describes behavior that no longer occurs.

## Updates

### 2026-08-09 — filed at `feat/prior-apps-pipeline` close-out (Epic A, sprint A4)

Filed following the A4 adversarial refuter's one confirmed finding: dossier
row 38 stated a mechanical "no change" without disclosing the underlying
coverage-mode shift. `decision_owner = "user"` because whether the current
one-test click-path coverage is acceptable, or whether to add a second
assertion, is a product/testing-strategy call, not a mechanical one.
