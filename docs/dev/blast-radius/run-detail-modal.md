# Blast radius — run-detail-modal

> **Branch:** `feat/run-detail-modal`
> **Status:** complete

---

## Surface

`ui_pages/selectors.py` — the `Dashboard` class (`:417-...`). C2 (UX-7/UX-8) adds new
selector constants for the run-detail modal (a run-id button, the modal root/backdrop/
close control, the error-record list inside it) and a couple of static-method selectors
for the new clickable run-id buttons and error-rate rows. This is an **additive** change
only: no existing `Dashboard` attribute name, value, or static-method signature is
renamed, removed, or changed.

`dashboard/routes.py` (new `GET /_dashboard/api/run/<run_id>` route) and
`dashboard/templates/dashboard.html` (new modal markup + run-id buttons) are **not**
gated surfaces per `scripts/enforcement/blast_radius.py` as of this branch's tip — verified
directly (see Enumeration) — so only `ui_pages/selectors.py` triggers this dossier.

---

## Enumeration

Grep-complete, whole tree, for every way `ui_pages.selectors` and the `Dashboard` class
specifically are consumed.

```
$ grep -rn "^from ui_pages\.selectors\|^from ui_pages import.*selectors\|import ui_pages\.selectors" --include="*.py" . | grep -v "^\./tests/" | sort
scripts/capture_screenshots.py:59:from ui_pages import selectors as S
ui_pages/base.py:7:from ui_pages.selectors import UserPicker, Wizard
ui_pages/corpus.py:8:from ui_pages.selectors import Corpus, TopTabs
ui_pages/dashboard_console.py:15:from ui_pages.selectors import Dashboard, Help
ui_pages/pipeline.py:6:from ui_pages.selectors import Pipeline, TopTabs
ui_pages/prior_apps.py:6:from ui_pages.selectors import PriorApps
ui_pages/user_picker.py:8:from ui_pages.selectors import UserPicker
ui_pages/wizard_clarify.py:6:from ui_pages.selectors import Wizard
ui_pages/wizard_compose.py:17:from ui_pages.selectors import Compose, Wizard
ui_pages/wizard_generate.py:8:from ui_pages.selectors import Wizard
ui_pages/wizard_job.py:6:from ui_pages.selectors import TopTabs, Wizard
ui_pages/wizard_output.py:9:from ui_pages.selectors import Output
ui_pages/wizard_template.py:12:from ui_pages.selectors import Wizard
```
13 non-test files import something from `ui_pages.selectors`. Plus
`scripts/bench_corpus_scale.py` imports `ui_pages` (confirmed separately: it drives
pages via the `ui_pages` package's page objects, not `selectors` directly) — together
these are the "14 non-test importers" `scripts/enforcement/blast_radius.py`'s own
`Dashboard`-entry comment cites; re-derived here rather than trusted from the comment.
**Of these, only `ui_pages/dashboard_console.py` imports the `Dashboard` class** — the
one class this branch's edit touches. `Corpus`, `TopTabs`, `Wizard`, `PriorApps`,
`UserPicker`, `Compose`, `Output`, `Pipeline` (the other classes in the same file) are
untouched by this branch; 0 hits for those symbols changing.

```
$ grep -rln "Dashboard\." tests/ ui_pages/ scripts/ | sort
tests/ux/a11y/test_axe_smoke.py
tests/ux/flows/test_annotation_tab.py
tests/ux/regression/test_20260612_required_field_and_dropdown.py
tests/ux/regression/test_20260615_education_diagnostics_annotate.py
tests/ux/regression/test_20260709_diagnostics_run_lock.py
tests/ux/regression/test_20260720_diagnostics_run_cancel.py
tests/ux/regression/test_20260923_dashboard_polish_ux.py
ui_pages/dashboard_console.py
```
8 sites reference `Dashboard.<attr>` (attribute access on the selectors class): 7 test
files plus `ui_pages/dashboard_console.py` itself. 0 hits outside this list (`static/`,
`dashboard/templates/`, `blueprints/` — none reference the Python selector class, by
construction: it is a Python-side test-infrastructure registry, not something the app
or the Jinja templates import).

```
$ grep -rln "from ui_pages import DashboardConsolePage\|DashboardConsolePage(" tests/ ui_pages/ | sort
tests/ux/flows/test_dashboard_console.py
tests/ux/regression/test_20260611_diagnostics_chart_corrections.py
tests/ux/regression/test_20260709_diagnostics_run_lock.py
tests/ux/regression/test_20260711_dashboard_assistant.py
tests/ux/regression/test_20260720_diagnostics_run_cancel.py
tests/ux/regression/test_20260923_dashboard_polish_ux.py
ui_pages/__init__.py
```
Separately enumerated `DashboardConsolePage` (the page object, not the selectors class)
consumers, since a new page-object method reading a new `Dashboard` selector could touch
these even without a `Dashboard.*` literal in the test file. 6 test files + the package
`__init__.py` re-export. All 6 test files are covered by the row above or by the
"no change" decision below (none of them touch the run-detail-modal flow today).

---

## Consumers

| # | Site (`path:line`) | Decision | Rationale |
|---|---|---|---|
| 1 | `ui_pages/selectors.py:417` (`Dashboard` class) | update | Add new members (`RUN_MODAL`, `RUN_MODAL_OPEN`, `RUN_MODAL_TITLE`, `RUN_MODAL_BODY`, `RUN_MODAL_CLOSE` constants; `RUN_LINK`/`ERR_LINK` selector constants plus their `run_link(run_id)`/`err_link(call_kind)` static-method helpers) — purely additive, no existing name changed. **(F2 correction, UX-8 closer fix, 2026-09-24: the row previously named an `error_rate_row` static method that was never added; corrected to the members actually present, re-checked directly against the file.)** |
| 2 | `ui_pages/dashboard_console.py` (whole file) | update | Add `DashboardConsolePage` methods `run_link(run_id)`, `open_run_detail(run_id)`, `err_link(call_kind)`, `open_errors_for_kind(call_kind)`, `run_modal()`, `run_modal_open()`, `run_modal_body()`, `close_run_modal()` that consume the new selectors, mirroring the existing tile/detail-panel method pairs. **(F2 correction, UX-8 closer fix, 2026-09-24: the row previously named `open_run_modal(run_id)`/`error_rate_row(call_kind)`, neither of which exists; corrected to the methods actually present, re-checked directly against the file.)** |
| 3 | `tests/ux/regression/test_20260923_dashboard_polish_ux.py` | no change | Asserts C1b's UX-2..6/UX-24 copy and animation state; does not reference run ids or error rows. |
| 4 | `tests/ux/regression/test_20260709_diagnostics_run_lock.py` | no change | Asserts `LOCK_BTN_IDS` lock/unlock behavior on run buttons; unrelated selector names (`Dashboard.tab`/pane helpers only). |
| 5 | `tests/ux/regression/test_20260720_diagnostics_run_cancel.py` | no change | Drives the Cancel flow via `Dashboard` tab/status selectors; no run-id or error-row selector used. |
| 6 | `tests/ux/regression/test_20260615_education_diagnostics_annotate.py` | no change | Drives the help-icon/education flow via `Dashboard`/`Help` selectors; unrelated to the new modal. |
| 7 | `tests/ux/regression/test_20260612_required_field_and_dropdown.py` | no change | Uses `Dashboard` selectors for an unrelated form-field regression, confirmed by reading the file. |
| 8 | `tests/ux/flows/test_annotation_tab.py` | no change | Drives the Annotate tab only. |
| 9 | `tests/ux/a11y/test_axe_smoke.py` | no change | Runs the axe scan over the whole dashboard page; a NEW UX test for the modal (added by this branch, see below) is the one place that could introduce a fresh a11y violation, and that new test itself covers it — this file's own assertions are unrelated to `Dashboard.*` beyond running the scan. |
| 10 | `scripts/capture_screenshots.py` | no change | Confirmed by reading: does not reference the `Dashboard` class or any dashboard-console page today (drives the main wizard/corpus/composer surfaces only). |
| 11 | `scripts/bench_corpus_scale.py` | no change | Drives the corpus-scale benchmark page objects only; no `Dashboard` reference. |
| 12 | `ui_pages/base.py`, `corpus.py`, `pipeline.py`, `prior_apps.py`, `user_picker.py`, `wizard_clarify.py`, `wizard_compose.py`, `wizard_generate.py`, `wizard_job.py`, `wizard_output.py`, `wizard_template.py` | no change | Each imports a *different* class from the same file (`UserPicker`, `Wizard`, `Corpus`, `TopTabs`, `Pipeline`, `PriorApps`, `Compose`, `Output`) — none imports `Dashboard`, confirmed by the first enumeration command above. |
| 14 | `tests/ux/regression/test_20260923_annotate_collate_run_lock.py` | no change | **Re-derivation correction (C2 rerun, 2026-09-24):** landed on `main` via C1a (`150bfb9`), committed before this dossier was first written, but omitted from the original enumeration. Read in full: drives `#annCollate` / `#annCollateRunBtn` lock behavior (UX-1) via `DashboardConsolePage`; no `run-link`/`err-link`/`RUN_MODAL*` selector, no run-id or error-row reference. Confirmed unaffected. |

New consumer added by this branch itself:

| # | Site (`path:line`) | Decision | Rationale |
|---|---|---|---|
| 13 | `tests/ux/regression/test_20260924_run_detail_modal.py` (new) | update (created) | The UX regression test for UX-7/UX-8 — the actual reason the new selectors exist. |

---

## Deferred

Nothing deferred. The edit is additive-only and every existing `Dashboard`-class
consumer was enumerated and confirmed unaffected by reading the file, not by name
pattern alone.

**Re-verification, C2 rerun (2026-09-24), per `epic-c-c2-rerun-brief.md`'s explicit
instruction to re-check a restored dossier against the current tip rather than trust
it stale.** Re-ran both enumeration commands above against the current branch tip
(after C1c's `analyzer.py` change and the restore): identical results except for
consumer #14 above (a real gap in the original enumeration, corrected in place) and
this branch's own new test file. `dashboard/routes.py` / `dashboard/templates/
dashboard.html` are still absent from `scripts/enforcement/blast_radius.py`'s `GATED`
registry (re-checked directly), so the surface stays `ui_pages/selectors.py` only. No
new selector name was added or changed by this sprint's UX-8 finish (`error_type`/
`error_message` ride on the existing `errors` payload shape; no new `Dashboard`
constant, no page-object method rename) — the C-10 surface and consumer list are
otherwise unchanged by finishing UX-8 against C1c's new telemetry fields.

---

## Verification

A missed consumer here would surface as: (a) a `mypy`/import error if a selector name
collided with an existing one (none does — checked against the full `Dashboard` class
body before choosing names), or (b) an existing UX test failing if the new modal markup
accidentally shadowed or removed an id/class an existing selector depends on (it does
not — the new modal is new markup, appended, and no existing `id`/`class` in
`dashboard.html` is renamed or removed by this branch).

**C2 rerun implementer, 2026-09-24 (finishing UX-8 against C1c's `error_type`/
`error_message` fields; see `epic-c-c2-rerun-brief.md`):** re-ran `python -m ruff
check .` and `python -m ruff format --check .` (whole repo, clean) and `python -m
mypy .` (whole repo, 382 source files, clean); `pytest tests/test_dashboard_routes.py`
(74 passed, including a new no-fields-on-legacy-row case) and
`pytest -m ux tests/ux/regression/test_20260924_run_detail_modal.py` (5 passed,
including a new "no message logged" case), plus the same UX-marked consumer set the
original implementer ran (`test_20260923_dashboard_polish_ux.py`,
`test_20260709_diagnostics_run_lock.py`, `test_20260720_diagnostics_run_cancel.py`,
`test_20260611_diagnostics_chart_corrections.py`, `tests/ux/flows/
test_dashboard_console.py`, the dashboard axe a11y smoke case) — 16 passed, all
green. **Still not run by this implementer:** the full `pytest -m "not ux"` tier —
that remains the invoker's gate run, per §11.9.

What was originally run by the C2 implementer (not a substitute for the invoker's own two
full gate runs, owed per `epic-c-c2-brief.md`): `python -m ruff check .` and
`python -m ruff format --check .` (whole repo, clean) and `python -m mypy .` (whole repo,
380 source files, clean); `pytest tests/test_dashboard_routes.py` (73 passed, including 3
new `TestRunDetailRoute` cases); the full UX-marked `Dashboard`-consumer set —
`test_20260924_run_detail_modal.py` (new, 4 passed), `test_20260923_dashboard_polish_ux.py`,
`test_20260709_diagnostics_run_lock.py`, `test_20260720_diagnostics_run_cancel.py`,
`test_20260611_diagnostics_chart_corrections.py`, `tests/ux/flows/test_dashboard_console.py`
(12 passed), and the dashboard axe a11y smoke case (1 passed) — all green. **Not run by
this implementer:** the full `pytest -m "not ux"` tier (~2797 tests) — a backgrounded
attempt produced no output before this session moved on (see the sprint report); that is
the invoker's gate run to make good on, not a substitute claimed here.
