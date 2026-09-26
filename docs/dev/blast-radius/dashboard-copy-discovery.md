# Blast radius — dashboard-copy-discovery

> **Branch:** `feat/dashboard-copy-discovery` (Epic C, sprint C3, run 5 of 5)
> **Status:** enumeration complete (written before the first edit to the gated surface)

---

## Surface

`ui_pages/selectors.py`: the `Dashboard` class. C3 adds new selector constants for the
per-tile lay line and per-tile help circle (`TILE`, `TILE_CELL`, `TILE_LAY`,
`TILE_HELP`), the filter-scope note (`FILTER_SCOPE`), and the bootstrap spend line
(`ANN_BS_SPEND`). The change is **additive only**. No existing `Dashboard` attribute or
static method is renamed, removed, or given a new value.

`dashboard/templates/dashboard.html` gets markup, copy, and a small amount of JS. It is
**not** a gated surface: 0 hits for `dashboard/` in `GATED_SURFACES` / `GATED_PREFIXES`
in `scripts/enforcement/blast_radius.py`. Even so, this change has one markup-structure
consequence that consumers could feel, and it is enumerated below: each `.tile` button
is now wrapped in a `.tile-cell` div, and the `.span-2` class moves from the button to
that wrapper.

---

## Enumeration

```
$ grep -rln "Dashboard\." tests/ ui_pages/ scripts/ --include=*.py | sort
tests/ux/a11y/test_axe_smoke.py
tests/ux/flows/test_annotation_tab.py
tests/ux/regression/test_20260612_required_field_and_dropdown.py
tests/ux/regression/test_20260615_education_diagnostics_annotate.py
tests/ux/regression/test_20260709_diagnostics_run_lock.py
tests/ux/regression/test_20260720_diagnostics_run_cancel.py
tests/ux/regression/test_20260923_dashboard_polish_ux.py
tests/ux/regression/test_20260924_run_detail_modal.py
ui_pages/dashboard_console.py
```
That is 9 sites that read `Dashboard.<attr>`.

```
$ grep -rn "from ui_pages.selectors import.*Dashboard\|selectors import Dashboard\|S\.Dashboard" --include=*.py . | sort
```
This finds 8 importers: 7 test files plus `ui_pages/dashboard_console.py`. There are 0
`S.Dashboard` hits, and `scripts/capture_screenshots.py` has 0 hits for `Dashboard` or
`_dashboard`, so the screenshot tool does not drive this console.

```
$ grep -rn "TILE\b\|TILE_CELL\|TILE_LAY\|BS_SPEND\|MODULE_HELP" --include=*.py ui_pages tests scripts
```
0 hits, so the new names collide with nothing.

The markup change was checked the same way, as a raw-selector consumer search:
```
$ grep -rn "\.tile\b\|'\.tile'\|\"\.tile\"\|\.bento" --include=*.py tests ui_pages scripts
ui_pages/dashboard_console.py:71 / :75, ui_pages/selectors.py:453  (Dashboard.tile(detail) = ".tile[data-detail='…']")
$ grep -rn "\.bento\|\.tile\b" static/*.css static/*.js
```
The second search finds 0 hits. `.tile` and `.bento` are styled only inside
`dashboard.html`'s own `<style>` block.

---

## Consumers

| # | Site (`path:line`) | Decision | Rationale |
|---|---|---|---|
| 1 | `ui_pages/selectors.py` (`Dashboard` class) | update (additive) | New constants only. `tile(detail)` keeps its value `.tile[data-detail='…']`, and the button still carries `data-detail`. |
| 2 | `ui_pages/dashboard_console.py:69-75` (`tile`, `open_tile`) | no change | It clicks `.tile[data-detail=…]`. The button still exists and is still clickable. The new help circle is a sibling positioned at the bottom-right, so it does not cover the button's centre, which is where Playwright clicks. |
| 3 | `tests/ux/a11y/test_axe_smoke.py` | no change | It scans every tab. The help circle is deliberately a **sibling** of the tile button, not a child: a button nested inside a button is axe's `nested-interactive` (serious). The new circles carry `aria-label` / `title` just like the existing ones. |
| 4 | `tests/ux/regression/test_20260615_education_diagnostics_annotate.py` | no change | The five tab-level `help-icon-<id>` ids and their `aria-label`/`title` are untouched. The legend-substring asserts (`true and usable as written`, `not supported by the candidate`) are kept verbatim. |
| 5 | `tests/ux/regression/test_20260923_dashboard_polish_ux.py:86-120` | no change | The new copy avoids the strings `Read-only` and `only write surface`, and keeps `read-write surface` in the Annotate intro and in the Annotate explainer. |
| 6 | `tests/ux/flows/test_dashboard_console.py:177` | no change | The `A/B a candidate prompt` module heading is kept. |
| 7 | `tests/test_dashboard_routes.py:591-595` | no change | The empty-state strings (`Nothing to chart yet`, `No eval scores yet`, `No groundedness scores yet`, `No call records`) are kept. `:662` / `:668` (`jd-label` count == 2): the change adds no `jd-label` spans. |
| 8 | the remaining `Dashboard.`-using tests (`test_annotation_tab`, `_required_field_and_dropdown`, `_run_lock`, `_run_cancel`, `_run_detail_modal`) | no change | These tests address ids (`#annCollate`, `#bsRun`, `#fixtureSelect`, `.run-link`, …). No id is renamed. |

---

## Deferred

- **Nothing on the selector surface is deferred.**
- The out-of-scope audit findings that border this copy (UX-12, UX-22, UX-27, UX-30,
  UX-33, UX-35; item 112 / item 113) are **not** touched. The new copy is written so that
  it does not *repeat* their false claims. See Observations 5 and 6.

---

## Verification

- `tests/test_dashboard_copy.py` renders the populated page through a Flask test client
  and parses it. Every `.tile` must carry a non-empty `.lay` line, and its `.tile-cell`
  must hold a `.help-info[data-help]` whose id is a key of `_DASH_HELP`. Every
  `data-help` on the page must also resolve. A tile added later without copy fails this
  test by construction.
- `tests/ux/regression/test_20260925_dashboard_copy_discovery.py` checks the same thing
  in a real browser: it clicks every tile's help circle and requires the shared
  `#helpModal` to open with the registered title.
- The existing axe smoke (`test_axe_dashboard_console`) is the backstop for a
  nested-interactive regression.

---

## Observations — brief/audit cites re-derived at `fe7d64c` before writing copy (C-0)

These are recorded here because this branch has no diagnosis dossier (it is `feat/*`)
and the facts have to survive the context window (C-8).

1. **Registry location drifted.** The `_DASH_HELP` registry sits at
   `dashboard/templates/dashboard.html:1077-1227`. The audit and brief said
   `:1003-1152`. It held **14** entries: 5 tab-level (`dashPipeline` … `dashAnnotate`)
   and 9 field-level. None of them described a tile or a module, which confirms UX-9.
2. **"Entries + copy only" (RELEASE_ARC C3) is not reachable as written, for two
   reasons.**
   (a) Every `.tile` is a `<button>` (`:322-347`, `:397-433`, `:451-462`, `:559-570`),
   so a `.help-info` button cannot be placed inside it without creating nested
   interactive content. Each tile therefore needs a wrapper.
   (b) The click wiring (`:1272`,
   `document.querySelectorAll('.help-info[data-help]')…`) runs once at load, so it never
   reaches a help circle created later. The dynamic "Run this fixture (real --seed)"
   button (`renderCollateResult`, `:2219-2251`) is one of those, so its circle needs the
   opener exposed on `window`.
3. **UX-18 reproduced.** `dashAnnScore` (`:1218-1226`) says that a missing seed or
   missing extras "just means nothing scores, not an error".
   - The server does not agree. `blueprints/diagnostics.py:503-510` returns **409**
     `"No seed.json for this fixture — re-run the bootstrap to capture the corpus
     snapshot, then score."`, and `:566` / `:600-606` stream an `error` event
     `"Grounding extras not installed."` with the `pip install -e '.[eval-grounding]'`
     remedy.
   - Observed: `python -m pytest tests/test_annotation_routes.py -k
     test_no_seed_returns_409` gave `1 passed`, and that test asserts the 409.
4. **UX-15: the existing slug-reuse hover copy is false.** `dashboard.html:609` says
   `title="… Reuse an existing slug to add more JDs to that same fixture."`.
   - The server does something else. Every bootstrap run writes its own
     `bootstrap-<timestamp>.json`, and it contains **only that run's JDs**
     (`blueprints/diagnostics.py:104-118` `_new_bootstrap_path`, `:924-929`). It also
     overwrites the fixture's `seed.json` (`:930-933`).
   - An existing `annotations.json` stays pinned to the bootstrap it was built from
     (`:120-165` `_resolve_bootstrap_pin`), so the editor keeps showing the old run.
     Only an unannotated fixture moves to the newest run.
   - What a reused slug actually does is "a new, separate run in the same folder", not
     "add JDs to the fixture". The new copy says that, and states that the way to
     annotate JDs together is to put them in the **same** run.
5. **UX-30 (out of scope, item 113) — do not repeat it.** The trace legend `:868` ("share
   of wall-clock") is false per the audit. The new trace tile copy says only "longer bar
   = slower call", which holds for `bar_pct` scaled to the longest span. The legend
   itself is left as it is.
6. **UX-27 (out of scope, item 113) — cost figures left as found.** The contradictory
   dollar estimates (`:1092`, `:1158`, `:1827-1829`, `:1891-1893`) are untouched. The
   new copy introduces no dollar figure of its own.
7. **Filter scoping is confirmed.** `dashboard/routes.py:1015-1016` applies
   Since/User/Model to the call log only, and `:1020-1022` + `:1047` run every
   Quality / Groundedness / baseline aggregation over **all** eval results. Tuning's
   baseline tile reads the baseline file directly. So the filters scope the Pipeline tab
   only.
8. **Sources for the numbers the new copy states.** Every number below is traced to a
   file, and no new number was minted.
   - Pass means `score ≥ 4.0`: `routes.py:209-238`.
   - Health bands are Δ < −0.5 regressed and Δ < −0.3 watch: `routes.py:905-908`.
   - The Pareto classes are defined at `routes.py:548-559`.
   - Percentiles use linear interpolation: `routes.py:142-156`.
   - NLI contradiction fires when P(contradiction) > 0.4: `evals/grounding_signals.py:28-30`.
   - MiniCheck scores 0–1, higher means more likely grounded, and < 0.5 counts as low:
     `evals/grounding_signals.py:233-234` and `:329`.
   - The model download is ~3.2 GB to the Hugging Face cache: `CONTRIBUTING.md:140-143`
     and `docs/install.md:361-365`.
   - MiniCheck is licensed for academic/research use: `CONTRIBUTING.md:145-151`.
   - Scoring takes ~2–4 s per bullet on CPU, and a typical résumé has 15–25 bullets:
     `CONTRIBUTING.md` "CPU inference time".
   - Each JD gets 3–5 clarifying questions: `analyzer.py:749`.
   - The `failed_rules` vocabulary is at `evals/annotation.py:90-135`. Verdict
     requirements are at `:204-218`, and collation is at `:586-594`.
   - The worked regex examples come from the committed `forbidden_inventions` in
     `evals/fixtures/synthetic/sre-mid-level/expected.json` and `pm-senior/expected.json`.
   - Collate writes `expected.json`, `improvement_brief.md` and `jd.txt`:
     `diagnostics.py:373-472`.
9. **UX-20 gap, declared rather than filled (C-12).** No source gives a *skills*-per-JD
   count. There is also no local bootstrap to measure one from:
   `evals/fixtures/real/*/` holds only `seed.json` files, and a count-only probe over
   `bootstrap-*.json` found no files. The copy gives the sourced figures (15–25 bullets
   and 3–5 questions per JD, before de-duplication) and says "plus its skills list" with
   no number.
10. **UX-14 spend estimate.** No dollar-per-JD figure exists for the bootstrap. The live
    estimate therefore counts paid pipeline runs and approximate time (the existing
    "~70s per JD" figure), not dollars.
11. **The run-detail modal gets no dedicated `_DASH_HELP` entry, by decision.** The modal
    (`dashboard.html:979-989`) and its two triggers — a `.run-link` button (run id shown in
    the trace panel, the calls table, the "Recent runs" fold, or the recent-evals table) and
    an `.err-link` button (a nonzero error count in the reliability table) — are a **result
    view**, not a tile or a module, so they get no `data-help` circle of their own. Their
    behaviour is instead explained where a reader already is when they can click one:
    the four tile-level `_DASH_HELP` entries `dashTileCalls` (`:1499-1507`), `dashTileErrors`
    (`:1508-1517`), `dashTileTrace` (`:1518-1526`), and `dashTileRecent` (`:1604-1611`), plus
    the four detail-pane `.legend` paragraphs for `throughput` (`:1023`), `reliability`
    (`:1044`), `trace` (`:1062`), and `recent` (`:1182`) — each names what clicking a run id
    or a red error count does. This decision was made and implemented (four registry entries,
    four legends, all shipped) but was not written down anywhere until now; recorded here per
    the mandatory First-move step 4 / §11.8 "decide AND record" obligation.
