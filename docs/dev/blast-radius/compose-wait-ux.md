# Blast radius — compose-wait-ux

> **Branch:** `feat/compose-wait-ux` (Epic A, sprint A2)
> **Status:** enumeration complete — written before the first edit to any file
> named below. Every `path:line` was read at this branch's base
> (`2a174bb`, stacked on A1b `5474763`); A1a/A1b moved line numbers, so the
> `RELEASE_ARC.md` A2 brief's own cites are re-derived here rather than trusted.

---

## Surface

Three distinct surfaces, one of them gated:

1. **`ui_pages/selectors.py`** — GATED (`scripts/enforcement/blast_radius.py:141-146`:
   *"the one selector registry; 14 non-test importers, consumed by the whole
   `pytest -m ux` tier AND `scripts/capture_screenshots.py`"*). The symbols in scope
   are `Compose.READY` (`:557`) and `Compose.SETTLED` (`:566`) — the settle contract
   the ARC brief names — plus **new** members added for this sprint's UI
   (`Compose.PENDING`, `Compose.SKILL_PIN`, `Compose.BULLET_EDIT`, `Compose.BUSY_BANNER`).
2. **`static/app.js`** — `_markComposeBgReload` (`:7331`, the counter behind
   `data-compose-bg-pending`), `loadComposition` (`:7345`), `_fireRecommendThenCompose`
   (`:1537`), `submitClarifications` (`:1453`), `skipClarifications` (`:1501`),
   `_renderSkillRow` / `_toggleSkillPin` / `_toggleSkillDrop` (`:7993`, `:8041`, `:8050`),
   `_renderBulletRow_compose` (`:8900-8927`, the `is_pending_review`-only Edit button).
3. **`templates/index.html`** — the Compose panel body (`:324-348`), gaining a
   `#composePending` in-panel wait block on the `#analysisPending` idiom (`:275-278`).

**The contract question this dossier exists to answer.** `Compose.SETTLED` is
`#composeList[data-compose-ready]:not([data-compose-bg-pending])`. The A2 brief calls for
a "Composing…" wait gate *held until the background volley settles* — i.e. a **second,
in-product consumer of the same settle signal the test harness owns**. The decision taken
here (see `## Consumers`) is that the gate **reads** that signal and does not **redefine**
it: `data-compose-ready` and `data-compose-bg-pending` keep byte-identical
set/clear semantics, so no existing consumer's meaning changes.

---

## Enumeration

Ripgrep over the whole tree (the `Grep` tool, i.e. `rg`, not a directory-local grep).
Counts are occurrences / files as reported.

```
rg -c "data-compose-ready"        →  60 occurrences, 21 files
rg -c "data-compose-bg-pending"   →  50 occurrences, 20 files
rg -c "Compose\.SETTLED|Compose\.READY|_wait_settled"
                                  →  94 occurrences, 20 files
rg -c "Compose\."                 → 120 occurrences, 36 files
rg -c "from ui_pages.selectors import|from ui_pages import|ui_pages\.selectors"
                                  → 116 occurrences, 72 files
rg -n "_markComposeBgReload\(1\)"  static/app.js   → 12 sites
rg -n "_markComposeBgReload\(-1\)" static/app.js   → 12 sites
rg -n "_busyBanner|cb-busy|_setBusy" tests/        → 2 files
rg -n "skill-pin|skill-drop|SKILL_DROP|📌|📍|✕|↩" (py,js,css,html)
                                  → 0 test assertions on the glyphs
```

**Every name the thing goes by, searched:**

| Name searched | Where it lives | Result |
|---|---|---|
| `data-compose-ready` (string form) | JS setter/clearer, Python selector, tests, docs | 21 files — table below |
| `data-compose-bg-pending` (string form) | JS setter/clearer, Python selector, tests, CSS comment, `ci.yml` comment | 20 files |
| `_markComposeBgReload` (symbol) | `static/app.js` only + prose | 24 call sites in one file |
| `Compose.READY` / `Compose.SETTLED` (symbol) | `ui_pages/wizard_compose.py` + tests | see below |
| `_wait_settled` (the only consumer of `SETTLED`) | `ui_pages/wizard_compose.py` (17), tests (many) | see below |
| `composeReady` (JS-side alias in test probes) | `tests/ux/regression/test_20260604_bullet_drag_reorder.py:78`, work item 30 | probe-local, not a contract |
| `#composeBgChip` (the chip driven off the same counter) | `templates/index.html:334`, `static/app.js:7341`, `static/style.css:1724`, one test | 4 sites |
| `#_busyBanner` / `_setBusy` / `body.cb-busy` | `static/app.js:5478`, 2 test files | 2 test files |
| `.skill-pin` / `.skill-drop` (template selectors) | `static/app.js`, `ui_pages/selectors.py:551` | 1 selector consumer |
| raw SQL / DB column named `compose_ready` etc. | — | **0 hits — negative result** |

### Negative results (findings, not absences of work)

- **`Compose.READY` has ZERO consumers.** `rg "Compose\.READY"` returns only its own
  definition at `ui_pages/selectors.py:557`. Every waiter uses `Compose.SETTLED`. So the
  READY constant is documentation, and changing *it* would break nothing — which is
  exactly why it must not be changed casually: it is the written definition of half the
  settle contract.
- **`.github/workflows/ci.yml:141` mentions `data-compose-bg-pending` in a COMMENT only**
  (the ux-tier `--reruns 2` flake-policy rationale). Not a consumer; no CI wiring reads
  the attribute. Recorded because a name-only grep makes it look like one.
- **No raw SQL, no DB column, no Jinja `{{ }}` expression** references either attribute.
  `templates/index.html` carries the attribute name only in an HTML comment (`:332`)
  explaining the chip; the attributes themselves are set from JS at runtime.
- **No test asserts on the Skills-card emoji glyphs** (`📌 📍 ✕ ↩`). The only Python
  consumer of those buttons is `Compose.SKILL_DROP = ".skill-drop"` →
  `WizardComposePage.drop_skill()` (`ui_pages/wizard_compose.py:222`), which selects by
  **class**, not by text. Replacing the glyph with a word is therefore invisible to it.
- **No test asserts on the compose bullet-row Edit button.** `rg "_editComposeBullet"`
  and `rg "Edit bullet"` return app.js + the corpus-tab flow only.
- **`scripts/capture_screenshots.py` uses `Compose.` once** (and `ui_pages` twice) — it
  consumes page objects, not the settle attributes directly, so it inherits whatever
  `_wait_settled` does and needs no edit.
- **No existing blast-radius dossier covers `ui_pages/selectors.py`.**
  `docs/dev/blast-radius/experience-soft-retire.md` (A1b) deliberately left it untouched
  and said so in its own `## Deferred`.

---

## Consumers

**One row per site. Every decision taken before the first edit.**

### A. `ui_pages/selectors.py` — the gated surface

| # | Site (`path:line`) | Decision | Rationale |
|---|---|---|---|
| 1 | `ui_pages/selectors.py:557` `Compose.READY` | **no change to the VALUE**; comment extended | Zero consumers (negative result above). Its comment is the written definition of the settle contract and now needs to record that the product reads the same signal. Changing the selector string would silently redefine a contract nothing would catch. |
| 2 | `ui_pages/selectors.py:566` `Compose.SETTLED` | **no change to the VALUE**; comment extended | 17 `_wait_settled` uses in `ui_pages/wizard_compose.py` + direct uses in 6 test modules depend on this exact string. The A2 gate reads the *same two in-app signals* from JS instead of widening this selector — see `## Deferred` note 1 for the widening that was considered and rejected. |
| 3 | `ui_pages/selectors.py` (new) `Compose.PENDING` | **add** | New `#composePending` in-panel wait block needs a selector for the new tests. Additive; no existing name changes. |
| 4 | `ui_pages/selectors.py` (new) `Compose.SKILL_PIN` | **add** | `.skill-drop` already had a selector; `.skill-pin` did not. The word-button change makes the pair testable symmetrically. |
| 5 | `ui_pages/selectors.py` (new) `Compose.BULLET_EDIT` | **add** | The extended in-place Edit needs a stable hook (`.compose-bullet-edit`) rather than a text match. |
| 6 | `ui_pages/selectors.py` (new) `Compose.BUSY_BANNER` | **add** | `#_busyBanner` is currently hand-written as a literal in `tests/ux/regression/test_20260708_busy_states_and_chip.py:49`. The A2 tests need it too; two literals of the same string in two files is the drift this registry exists to prevent. |

### B. Consumers of the settle contract (`data-compose-ready` / `data-compose-bg-pending`)

**These are the sites the ARC brief ordered audited BEFORE changing settle semantics.**
The audit's conclusion is that settle semantics are **not** changed, so every row below is
"no change" — but each was checked against the specific way it would break if they were.

| # | Site (`path:line`) | Decision | Rationale |
|---|---|---|---|
| 7 | `static/app.js:7362` `list.removeAttribute('data-compose-ready')` (loadComposition entry) | **no change** | Clearing at entry, before the fetch, is the invariant every waiter rests on. |
| 8 | `static/app.js:7483` `list.setAttribute('data-compose-ready','1')` (terminal render) | **augment, do not move** | A synchronous settle-waiter flush is inserted immediately BEFORE this line so the product's busy overlay is already down when SETTLED first becomes observable. The attribute set itself is unmoved and unconditional. |
| 9 | `static/app.js:7331-7343` `_markComposeBgReload` | **augment, semantics unchanged** | Gains (a) an optional second `label` argument for the chip text and (b) a synchronous waiter flush immediately BEFORE `removeAttribute('data-compose-bg-pending')`. `_composeBgReloads` arithmetic, the `Math.max(0, …)` floor, the set-at->0 / remove-at-0 attribute rule and the never-`="0"` invariant are all byte-identical. |
| 10 | `ui_pages/wizard_compose.py:63-95` `_wait_settled` | **no change** | Reads `Compose.SETTLED` unchanged. Verified by re-reading: the only thing that could break it is a settle state that never arrives, and the gate adds no new path that suppresses the terminal render. |
| 11 | `ui_pages/wizard_compose.py` — the 17 `_wait_settled` call sites (`:61,115,125,179,195,200,204,212,221,232` + inherited) | **no change** | All inherit row 10. |
| 12 | `tests/ux/regression/test_20260706_compose_settle_bg_reload.py` (5 `data-compose-ready`, 5 `bg-pending`, 3 `_wait_settled`) | **no change; MUST RUN** | Pins "the counter increment lands before the ready marker is re-set". My insert is *between* the flush and the mutation, not between the increment and the marker. Run it. |
| 13 | `tests/ux/regression/test_20260718_compose_unawaited_reloads.py` (8 / 5 / 2) | **no change; MUST RUN** | Captures, synchronously inside the bg-pending clear, whether `data-compose-ready` is already back. My waiter flush runs **in that same synchronous block, before the clear** — the highest-risk interaction in this sprint. Run it. |
| 14 | `tests/ux/regression/test_20260722_compose_bare_reload_settle.py` (5 / 2 / 5) | **no change; MUST RUN** | Asserts `data-compose-ready` is ABSENT immediately after a rail click — a test that deliberately observes an UNSETTLED state. This is the documented deadlock trap; the gate is therefore **not** attached to `wizardGoTo(3)` (see `## Deferred` note 2). Run it. |
| 15 | `tests/ux/regression/test_20260708_busy_states_and_chip.py:406-462` (the two clarify busy tests) | **UPDATE — they encode the OLD invariant** | Both do `wait_for_selector(PANEL_COMPOSE, visible)` then assert the banner is not showing. Under A2 the banner is deliberately still up ("Composing…") at that instant. Tightened to the new invariant: banner still up at panel-visible, cleared once settled. This is a real contract change and is the reason this row is not "no change". |
| 16 | `tests/ux/regression/test_20260708_busy_states_and_chip.py:502-539` (chip test) | **no change; MUST RUN** | Observes the chip's `hidden` class via MutationObserver off the same counter. The label change touches `textContent`, not `class`. |
| 17 | `tests/ux/regression/test_20260604_bullet_drag_reorder.py:78` (`composeReady` probe) + 12 `_wait_settled` | **no change** | Diagnostic probe reading `hasAttribute('data-compose-ready')`; semantics preserved. |
| 18 | `tests/ux/regression/test_20260708_compose_gap_fill_regenerate.py` (17 `Compose.` uses, 3 `_wait_settled`) | **no change; MUST RUN** | Heaviest `Compose.` consumer; exercises the gap-fill leg of the volley the gate waits on. |
| 19 | `tests/ux/regression/test_20260706_compose_gap_fill.py` (10 `Compose.` uses) | **no change; MUST RUN** | Same leg. |
| 20 | `tests/ux/regression/test_20260706_compose_summary_draft.py` (4) | **no change; MUST RUN** | The draft-summary leg — the one whose failure produced the "settled but empty" hole (`docs/dev/diagnosis/compose-summary-draft-settle-hole.md`). |
| 21 | `tests/ux/regression/test_20260708_step6_full_hydration.py` (3 `Compose.`, 2 `_wait_settled`) | **no change; MUST RUN** | Drives clarify→compose→…→step 6, i.e. it traverses the exact path the new hold is attached to. |
| 22 | `tests/ux/regression/test_20260611_compose_add_title.py`, `_order_no_recommendations.py`, `test_20260612_experience_summary_item.py`, `test_20260613_skill_corpus_item.py`, `test_20260707_ux_w1_skills_education.py`, `test_20260707_ux_w4_aesthetic.py` | **no change; run the compose subset** | Compose-surface consumers via page objects. |
| 23 | `tests/ux/flows/test_happy_path_stubbed.py`, `test_demo_mode_journey.py`, `test_output_surface_seeded.py` | **no change; MUST RUN** | Full-flow drivers that pass through clarify→compose. If the hold ever failed to release, these hang — they are the honest detector for that. |
| 24 | `scripts/capture_screenshots.py` | **no change** | Consumes page objects; inherits row 10. |
| 25 | `static/style.css:1718-1747` `.compose-bg-chip` | **no change** | Chip text is set from JS; the rule styles the box and its `::before` dot, neither of which depends on the string. |
| 26 | `templates/index.html:328-334` `#composeBgChip` + its comment | **update comment only** | The comment asserts the chip is *"driven from the SAME data-compose-bg-pending counter… never toggled independently."* Still true after the label change, and the comment now says so explicitly rather than leaving a reader to check. |
| 27 | `.github/workflows/ci.yml:141` | **no change** | Comment only (negative result above). |
| 28 | `docs/wiki/pages/frontend-wizard.md:172` | **deferred to close-out** | Wiki page cites the `_markComposeBgReload` mechanism. Wiki edits are a close-out step (`AGENTS.md` pre-close sweep) owned by the closer, not the implementer. Named here so it is not silently skipped. |
| 29 | `CHANGELOG.md` (6 + 3 historical mentions) | **deferred to close-out** | Historical entries; the new entry is the closer's step. |
| 30 | `docs/dev/RELEASE_CHECKLIST.md`, `docs/dev/ORCHESTRATION_PLAYBOOK.md`, `docs/dev/diagnosis/*.md`, `docs/dev/work/items/*.md` | **no change** | Historical evidence records. C-8 forbids rewriting them; they describe what was observed then. |

### C. `_markComposeBgReload` call sites — all 12 (the brief said 9)

**Finding: the ARC brief's "(9)" is stale.** It quotes the count fixed by
`fix/compose-unawaited-reloads`, preserved verbatim in `static/app.js:7138`'s own comment
(*"unlike the 9 sites `fix/compose-unawaited-reloads` fixed"*). At this branch's base there
are **12** increment sites and 12 matching `finally` decrements. Enumerating all 12:

| # | `path:line` (the `(1)`) | Function | Kind | Decision |
|---|---|---|---|---|
| 31 | `static/app.js:2906` / `:2919` | `_acceptRefinementProposal` | user action | **no change** — not part of the arrival volley; a labelled chip here would describe an action the user just took and already sees. |
| 32 | `static/app.js:7606` / `:7624` | `_fireRecommendSummary` | **arrival volley** | **label added** — "Choosing your positioning…". Counter untouched. |
| 33 | `static/app.js:7657` / `:7683` | `_fireDraftSummary` | **arrival volley** | **label added** — "Drafting your positioning summary…". This is the site whose latch/finally interaction produced the settled-but-empty hole; the bracket is left exactly as-is. |
| 34 | `static/app.js:7713` / `:7738` | `_fireDraftGapFill` | **arrival volley** (also the explicit Regenerate) | **label added** — "Finding gaps this résumé doesn't cover…". |
| 35 | `static/app.js:7905` / `:7916` | `_togglePositioningPin` | user action | **no change** |
| 36 | `static/app.js:8105` / `:8118` | `_fireRecommendSkills` | **arrival volley** (also explicit Tailor) | **label added** — "Tailoring skills to this job…". |
| 37 | `static/app.js:8128` / `:8146` | `_fireSuggestSkills` | user action | **no change** — always explicit; `_setBtnPending` already covers it. |
| 38 | `static/app.js:8179` / `:8191` | `_reviewPendingSkill` | user action | **no change** |
| 39 | `static/app.js:8240` / `:8252` | `_decideGapFill` | user action | **no change** |
| 40 | `static/app.js:8430` / `:8442` | `_fireRecommendExperienceSummaries` | **arrival volley** (opt-in) | **label added** — "Choosing role intros…". |
| 41 | `static/app.js:8463` / `:8477` | add-role-intro modal submit | user action | **no change** |
| 42 | `static/app.js:8772` / `:8776` | add-title modal submit | user action | **no change** |

The five labelled sites (32, 33, 34, 36, 40) are exactly the five the `loadComposition`
auto-cascade fires (`static/app.js:7418-7476`). Nothing about the counter changes at any
of the 12; `label` is an optional second parameter, so all 12 keep working unmodified.

### D. The wait-gate attachment point

| # | Site (`path:line`) | Decision | Rationale |
|---|---|---|---|
| 43 | `static/app.js:1580` `wizardGoTo(3)` in `_fireRecommendThenCompose` | **update — the hold is raised here** | The single funnel for both `submitClarifications` and `skipClarifications` (and `#btnSkipFromAnalysis`, `templates/index.html:285`). One insert covers all three entries. |
| 44 | `static/app.js:1498` `_setBusy(false)` (submitClarifications tail) | **update** | Runs AFTER the hold is raised and would tear it down. Routed through a new `_clearBusyUnlessComposing()`. |
| 45 | `static/app.js:1530` `_setBusy(false)` (skipClarifications `finally`) | **update** | Same reason. |
| 46 | `static/app.js:1577` `_setBusy(false)` (`_fireRecommendThenCompose` `finally`) | **no change** | Runs BEFORE `wizardGoTo(3)`, so it cannot clobber the hold. |
| 47 | `static/app.js:7128` `wizardGoTo` (all other steps + rail nav to 3) | **no change** | See `## Deferred` note 2 — attaching the hold here is what would deadlock row 14. |
| 48 | `static/app.js:5478` `_setBusy` | **no change** | Left byte-identical; 22 other call sites (ingest/analyze/generate/refine/clarify) depend on its exact behavior. The hold composes on top of it rather than changing it. |

### E. The two smaller brief items

| # | Site (`path:line`) | Decision | Rationale |
|---|---|---|---|
| 49 | `static/app.js:8016-8028` `_renderSkillRow` pin/drop buttons | **update** | Emoji → word buttons on the `.corpus-action-btn` idiom the bullet rows already use (`:8812-8825`). Classes `.skill-pin` / `.skill-drop` **kept** so row 4/`Compose.SKILL_DROP` and `drop_skill()` keep working. |
| 50 | `static/app.js:8041-8060` `_toggleSkillPin` / `_toggleSkillDrop` | **update** | They re-write `textContent` with the glyphs on every toggle; they must write the words and the `.on` state class instead, or the first toggle would revert the idiom. **This is the site an emoji-only edit would have missed.** |
| 51 | `static/app.js:8900-8927` `_renderBulletRow_compose` Edit/Approve block | **update** | Edit lifted out of the `if (b.is_pending_review)` guard so every compose bullet row has it; Approve stays gated (approving a non-pending bullet is meaningless). |
| 52 | `static/app.js:8958-8978` `_refreshComposeRow` | **no change, and this constrains the fix** | It addresses the row's action buttons **by index** (`btns[0..2]`). Edit is therefore appended to `.row-meta` (where the pending-review Edit already lived), **not** to `.row-actions` — appending there would shift nothing today but makes the index contract one edit away from breaking. |
| 53 | `static/app.js:8938-8956` `_editComposeBullet` | **update (copy only)** | `PUT /api/bullets/<id>` is unchanged. The modal subtitle currently says "Edit this proposed bullet"; on a non-pending corpus bullet that is wrong, and the corpus-wide effect must be stated. |
| 54 | `templates/index.html:336-342` Compose panel body | **update** | Adds `#composePending` on the `.analysis-pending` idiom (`:275-278`). |
| 55 | `blueprints/**`, `db/**`, `analyzer.py` | **no change** | A2 is client-side. `rg` confirms no server route reads any of these attributes or the Edit/pin affordances; `PUT /api/bullets/<id>` and `POST /composition` already exist and are unchanged. |

---

## Deferred

1. **Widening `Compose.SETTLED` to also require the busy banner to be down.** Considered
   and rejected. It would make the harness's settle gate depend on a *product* affordance,
   inverting the direction of the contract, and would break row 14's deliberate
   observation of an unsettled state. Instead the product reads the same two in-app
   signals the selector encodes, and the release is flushed **synchronously before** the
   DOM mutation that makes `SETTLED` observable — so `_wait_settled()` returning already
   implies the banner is down, without `SETTLED` mentioning the banner.
2. **Attaching the "Composing…" hold to every `wizardGoTo(3)` (rail navigation).** Not
   done. `tests/ux/regression/test_20260722_compose_bare_reload_settle.py:110` clicks the
   rail and immediately asserts `data-compose-ready` is absent — a test that *depends on
   observing the unsettled state*. Raising a full-page busy banner on that path adds a
   fixed-position element at `top:14px; z-index:2000` over the rail for the duration of
   every rail hop into Compose, which is both a new click-interception surface for the ux
   tier and a heavier affordance than a re-visit warrants. The brief's gate is about the
   *arrival* volley after recommend; that is where it is attached. **Gap this leaves:** a
   user who navigates back to Compose via the rail during a still-running volley sees only
   the `#composeBgChip`, not the banner. That is the pre-A2 behavior, unchanged, and the
   chip is now labelled with what is actually running.
3. **`body.cb-busy` has no CSS rule.** `rg "cb-busy"` over `static/style.css` finds
   `.cb-busy-banner`, `.cb-busy-banner.show`, `.cb-busy-dot` — and no `body.cb-busy`
   rule at all. So `_setBusy` does **not** block input anywhere in the app today, despite
   its "please wait, don't navigate away" copy. Deliberately **not** fixed here: adding
   pointer-blocking would change the behavior of all 22 `_setBusy` call sites (ingest,
   analyze, generate, refine) and is a user-visible behavioral change outside this brief.
   Filed for the ledger rather than taken.
4. **The 20 s cap (`_COMPOSE_SETTLE_CAP_MS`) clears the wait state whether or not the
   volley finished.** Declared, not papered over. The cap exists so a POST that rejects
   in a way that never reaches a terminal render cannot strand a "don't navigate away"
   banner over a usable page. Its cost: if a leg of the arrival volley genuinely runs
   longer than 20 s, the panel reads as **done** while the render may still be cascading
   underneath — a delayed, rarer form of the exact "visible ≠ ready" gap A2 exists to
   close. The tradeoff is taken deliberately (a stuck banner is the worse and more
   frequent failure, and the `#composeBgChip` remains visible and labelled for the
   duration of any leg still running past the cap), but it is a real hole, not an
   absence of one. Not mitigated here: a cap-driven release is indistinguishable from a
   settle-driven one to the user, and no telemetry counts how often the cap wins.
5. **`docs/wiki/pages/frontend-wizard.md:172`** — see row 28; wiki refresh is the
   closer's close-out step, not the implementer's.
6. **Item 20 (the Step-5 wizard-rail hard gate)** — explicitly out of scope; it keeps its
   own `fix/*` branch so the C-7 evidence guard, which only fires on `fix/*`, is not
   silently disabled (`RELEASE_ARC.md:1739-1742`,
   `docs/dev/epic-a-chain-design-corrections.md` finding 5). Nothing on this branch
   touches it.

---

## Verification

**How a missed consumer would surface, and what was run.**

The enumeration's weak point is stated plainly: C-10's own declared blind spot is that the
computed audit covers first-party **Python** import fan-in only, so the JS half of this
surface is curation-only. The counter-measure used here is that the JS contract has an
unusually complete *test* fan-in — four regression modules exist for the sole purpose of
pinning it (rows 12, 13, 14, 16) — so running them is a real check, not a proxy.

Specifically:

- **A missed settle-semantics change surfaces as a hang, not a wrong value.** Rows 12–14
  and 18–23 either wait on `Compose.SETTLED` or assert on its absence. A change that made
  the terminal render unreachable hangs them at their 15 s/30 s timeouts; a change that
  made it reachable *too early* fails row 13's synchronous "was ready already back?"
  capture. Both are loud.
- **A1b's lesson applied (a targeted green is not evidence about a file it does not
  execute).** The compose-surface UX modules are run as a group, not individually
  hand-picked per edit.
- **Row 15 is the falsifiable statement of the contract change.** The two clarify tests
  are tightened to assert the *new* invariant (banner up at panel-visible, down at
  settle) rather than deleted or relaxed — so a regression that dropped the hold, or one
  that never released it, both fail.

Commands run and their terminal lines are recorded in the implementer's report for this
sprint (the sprint's evidence lives with the run, not restated here where it would rot).
