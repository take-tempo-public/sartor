# Blast radius — role-summary-drafting

> **Branch:** `feat/role-summary-drafting` (Epic A, sprint A3)
> **Status:** enumeration complete for the surfaces named below; written BEFORE the
> first production edit on this branch.

---

## Note on which of these surfaces the guard actually fires on (C-0 / C-12)

The sprint brief handed to this implementer stated that `hardening.py` is a
`require-consumer-enumeration` gated surface and that the hook would block the first
edit to it without this dossier. **That is not true at HEAD.** `hardening.py` is in
`ACKNOWLEDGED_NOT_GATED`, not `GATED`
(`scripts/enforcement/blast_radius.py:196-201`: "13 non-test importers. The
context_set write helpers ARE a shared contract, but this module is also the ordinary
home for per-branch pipeline work. Watched, not gated"). `analyzer.py`,
`db/build_context.py` and `blueprints/**` are likewise acknowledged-not-gated or
below threshold. **No file this branch touches is in `GATED` / `GATED_PREFIXES`**, so
the PreToolUse guard does not fire on any of them.

This dossier is written anyway, because charter **C-10** binds on *"a schema, a shared
contract, or a widely-consumed helper"* — which `assemble_source_union` and the
`ContextSet` TypedDict both are — independently of whether the path-level guard
happens to cover them. The guard is the floor, not the definition.

---

## Surface

Four production surfaces change on this branch.

1. **`hardening.py`**
   - `assemble_source_union()` (`hardening.py:1904`) — the single source-union
     definition shared by `compute_iteration_signals` and the eval-time L0
     fabricated-specifics check. **Widened** to fold in the candidate's per-role
     intro-variant texts (`context_set["experience_summary_items"]`).
   - `ContextSet` TypedDict (`hardening.py:156`) — **new optional key**
     `experience_summary_items`, typed `list[Any]`.
     **Corrected during implementation, recorded rather than rewritten away:**
     the first attempt typed it as `list[ExperienceSummaryGroup]` with two new
     supporting TypedDicts. `mypy` immediately failed with *"Statement is
     unreachable"* at `analyzer.py:3459` and `hardening.py:2000` and a
     list-invariance `[assignment]` error at `analyzer.py:3476` — because a
     precise element type makes the existing defensive
     `isinstance(g, dict)` guards statically dead, even though at RUNTIME this
     value is read back off JSON on disk and those guards are live. Both new
     TypedDicts were removed. This is row 16 of the table below actually firing
     — the enumeration named `recommend_experience_summaries` as a consumer of
     this key, and it is what the type change hit first.
2. **`db/build_context.py`** — `build_context_set_from_db()` now stages
   `experience_summary_items` **durably** on the corpus-mode context (one batched
   query, not per-role), so the widened union has something to read on a persisted
   `context_*.json`. This is the D5/`prior_clarifications` pattern applied to the
   same problem.
3. **`analyzer.py`** — new `DRAFT_EXPERIENCE_SUMMARIES_SYSTEM_PROMPT` constant, new
   `DraftExperienceSummariesResponse` model, new batched
   `draft_experience_summaries()` call (`call_kind="draft_experience_summary"`), new
   `_BASE_SYSTEM_PROMPTS` entry, `PROMPT_VERSION` bump.
4. **`static/app.js` + `static/style.css`** — the Compose draft card
   (`_renderRoleIntroDraftCard`, `_decideRoleIntroDraft`,
   `_fireDraftExperienceSummaries`, `_renderRoleIntroDraftControls`) and the
   widened toggle gate. **See `## The consumer this enumeration missed` below** —
   the JS half of a C-10 enumeration is exactly the blind spot
   `scripts/enforcement/blast_radius.py`'s own module docstring warns about,
   and it caught me on this branch.
5. **`blueprints/applications.py`** — two new routes
   (`/draft-experience-summaries`, `/experience-summary-decide`) and one new
   `composition_overrides` key (`retired_experience_summary_keys`) + one new
   transient context key (`llm_experience_summary_drafts`).

Test/harness surfaces that change with them: `tests/ux/stubs.py`
(`install_llm_stubs`), `tests/test_call_kind_telemetry.py` (`EXPECTED_CALL_KINDS` +
a probe), `demo_fixtures.py`.

---

## Enumeration

All commands run from the repo root against the branch base
(`f35b22d`), whole tree, ripgrep via the Grep tool (equivalent to
`rg -n <pattern>` with no path restriction).

```
rg -n "assemble_source_union"              -> 2 production .py hits, 1 eval hit,
                                              5 test-file hits, 20 doc hits
rg -n "compute_grounding_overlap|compute_fabricated_specifics" -g '*.py'
                                           -> 2 defs + 3 call sites + tests
rg -n "experience_summary_items"           -> 4 analyzer hits, 2 blueprint hits,
                                              2 demo_fixtures hits, 6 test hits,
                                              0 hits in static/, 0 in templates/
rg -n "frozen_composition_doc"             -> (read as the worked example for the
                                              most recent gated-surface dossier)
rg -n "ExperienceSummaryItem"              -> corpus_to_json_resume.py (2),
                                              blueprints/applications.py (5),
                                              blueprints/corpus/{_shared,experiences}.py,
                                              db/models.py
rg -n "_get_client" blueprints/            -> analysis(4), applications(7),
                                              diagnostics(2), assistant(2),
                                              generation(5), corpus/curation(2),
                                              corpus/proposals(3), corpus/skills(2)
rg -n "_BASE_SYSTEM_PROMPTS"               -> registry at analyzer.py:4566 (16 keys
                                              at base), 1 drift-guard test
rg -n "prior_clarifications"               -> read as the precedent for a durable
                                              context key feeding the same union
```

**Negative results (findings, recorded deliberately):**

- `experience_summary_items` has **0 hits in `static/app.js`, `templates/`, and
  `dashboard/`.** The key never crosses to the client under that name; the client
  sees per-role variants as `exp.summary.variants` from the composition GET. So
  widening the key's *contents* cannot break a JS consumer.
- `assemble_source_union` has **0 hits in `blueprints/`, `app.py`, `static/`,
  `templates/`, `dashboard/`, `onboarding/`, `recall/`.** Its only two runtime
  callers are `hardening.compute_iteration_signals` and `evals/runner.py`.
- `assemble_source_union` has **0 raw-SQL / column-name form** — it is a pure
  function over an in-memory dict, so there is no aliased or stringly-typed name to
  miss.
- `evals/schemas/context_set.schema.json` (a **gated** file) declares
  `"additionalProperties": true` at the top level, so a new optional context key
  needs **no schema edit** and this branch does not touch that gated path. Verified
  by loading the schema and printing `additionalProperties` / `required`.

---

## Consumers

### A. `hardening.assemble_source_union` — every call site and every doc claim

| # | Site (`path:line`) | Decision | Rationale |
|---|---|---|---|
| 1 | `hardening.py:1975` (`compute_iteration_signals`) | **no change (behavior widens automatically)** | Passes the union straight to `compute_grounding_overlap` against the *current draft*. A role intro chosen or drafted at Compose is part of that draft; folding intro variants into the union makes the iteration clarifier stop treating legitimately-chosen intro text as ungrounded. Strictly reduces false positives; cannot introduce one. |
| 2 | `evals/runner.py:1363` | **no change (behavior widens automatically)** | Same union, feeding the L0 `compute_fabricated_specifics` check. Same direction of effect. Widening the ground-truth set can only *lower* `fabricated_specifics_rate`; it can never flag something previously grounded. |
| 3 | `evals/runner.py:75` (import) | no change | Import only. |
| 4 | `tests/test_hardening.py:613-656` (`TestAssembleSourceUnion`) | **update — add a case** | The existing four cases assert the 4-source union exactly. A 5th source needs its own case (present → folded; absent → unchanged, i.e. legacy/file-based contexts stay byte-identical). |
| 5 | `docs/wiki/pages/generation-and-grounding.md:106,112,114` | **deferred to the epic close** | Wiki pass + `.last_ingest_sha` advance is explicitly scheduled at the Epic A close, not per sprint (`docs/dev/epic-a-chain-design-corrections.md` §15.2). Named here so the closer does not have to re-derive it. |
| 6 | `docs/wiki/pages/eval-harness.md:117` | **deferred to the epic close** | Same. Carries the countable claim "primary + supplementals + …" — a §15.5 canary target once the union is 5 sources. |
| 7 | `docs/wiki/pages/context-set-contract.md:8,97` | **deferred to the epic close** | Same; also needs the new `experience_summary_items` key documented. |
| 8 | `AGENTS.md:248` | **no change on this branch** | Describes the D5 three-drafting-call carve-out. Still true; this branch adds a fourth drafting call rather than changing what it says about the three. Flagged in the report as a wording-refresh candidate for the epic close. |
| 9 | `evals/TUNING_LOG.md:404,443,2865` | **no change (historical entries)** | Dated log entries describing past states. Appending a new entry is the correct update, which this branch does; editing old entries would falsify the record. |
| 10 | `CHANGELOG.md:3674,6527,7632` | **no change (historical entries)** | Same reasoning. A new `[Unreleased]` entry is added instead. |
| 11 | `docs/dev/COMPOSE_REWRITE_DIAL.md:122`, `docs/dev/generation-experience-rearchitecture.md:845,852`, `docs/dev/RELEASE_CHECKLIST.md:481,1484,3070`, `docs/dev/reviews/**` | **no change** | Dated design/review documents describing the state at their own time. Not live contracts. |

### B. `ContextSet` — the new `experience_summary_items` key

| # | Site (`path:line`) | Decision | Rationale |
|---|---|---|---|
| 12 | `hardening.py:156` (`ContextSet`) | **update** | Add the optional key + its two element TypedDicts. `total=False`, so every existing context round-trips unchanged. |
| 13 | `db/build_context.py:210-231` (the returned dict) | **update** | Stage the key durably in corpus mode. One `WHERE experience_id IN (...)` query grouped in Python — deliberately not a per-role query (N+1). |
| 14 | `hardening.build_context_set` (file-based path) | **no change** | Legacy file-based contexts have no `ExperienceSummaryItem` rows to stage. The key stays absent, `assemble_source_union` skips it, and `--suite synthetic` stays byte-identical. This is the same posture `prior_clarifications` takes. |
| 15 | `evals/schemas/context_set.schema.json` | **no change (verified, not assumed)** | `additionalProperties: true`; the key is not in `required`. The `validate-context` hook therefore passes unchanged. |
| 16 | `analyzer.py:3427,3445,3447` (`recommend_experience_summaries`) | **no change** | Already reads this key with the exact same shape (`{experience_id, company, items:[{id,text,label,has_outcome}]}`). The route continues to stage a fresh copy in memory; a durable copy underneath is at worst redundant, never conflicting. **Verified the shapes match field-for-field** before reusing the key rather than inventing a second one. |
| 17 | `blueprints/applications.py:2958` (recommend route staging) | **no change** | Left alone deliberately — see `## Deferred` #D1. |
| 18 | `demo_fixtures.py:395` (`demo_recommend_experience_summaries`) | **no change** | Reads the same shape; unaffected. |
| 19 | `tests/test_recommend_experience_summaries.py:304` (`assert "experience_summary_items" not in ctx`) | **CHECKED — still passes** | This asserts the *recommend route* strips its transient staging from the persisted context. That test seeds its own context file directly and never goes through `build_context_set_from_db`, so the durable staging does not reach it. **This is the single most likely place a missed consumer would have surfaced, and it is why the key was grepped for before the edit.** |
| 20 | `tests/test_demo_mode.py:66`, `tests/test_call_kind_telemetry.py:293` | **no change** | Hand-built contexts; unaffected. |

### C. New call kind `draft_experience_summary` — the four-leg checklist

| # | Site (`path:line`) | Decision | Rationale |
|---|---|---|---|
| 21 | `tests/test_call_kind_telemetry.py:73` (`EXPECTED_CALL_KINDS`) | **update** | The AST inventory guard fails closed on an unreviewed literal — by design (item 22, rival b6). 20 → 21 literals. |
| 22 | `tests/test_call_kind_telemetry.py:242` (`TestNeverLoggedKindsEmitTelemetry`) | **update — add a probe** | A brand-new kind is by definition a never-logged kind. |
| 23 | Pricing keys — `hardening.MODEL_PRICING` | **no change (verified, not assumed)** | Pricing is keyed by **model**, not by call kind (`hardening.py:414`, consumed by `compute_call_cost` at `hardening.py:1485`). The new call uses `SONNET_MODEL`, already a `MODEL_PRICING` key, so the probe's `_assert_priced_ok_row` model-in-`MODEL_PRICING` assertion passes with no pricing edit. **The brief's "pricing keys" leg is satisfied by construction here, not by an edit** — recorded so a reviewer does not read the absent diff as a skipped leg. |
| 24 | `tests/ux/stubs.py` (`install_llm_stubs`) | **update** | New stub `fake_draft_experience_summaries` + patch. |
| 25 | `analyzer.py:4566` (`_BASE_SYSTEM_PROMPTS`) | **update** | `tests/test_prompt_overrides.py:135` fails closed on any unregistered `*_SYSTEM_PROMPT` module constant. 16 → 17 keys. |
| 26 | `analyzer.py:393` (`PROMPT_VERSION`) | **update** | Mandatory in the same changeset as new prompt text (AGENTS.md, charter D-4). |
| 27 | `demo_fixtures.py` | **update** | Every analyzer call has a demo short-circuit; a new one without it would make a real billed call in demo mode. |
| 28 | `dashboard/` cost + call-kind views | **no change (verified)** | `_cost_by_call_kind` aggregates whatever `call` values appear in `logs/llm_calls.jsonl`; there is no hard-coded call-kind allow-list to extend. |

### D. Item 34 — `install_llm_stubs` `_get_client` coverage

| # | Site (`path:line`) | Decision | Rationale |
|---|---|---|---|
| 29 | `blueprints/corpus/skills.py:29` | **update — patch it** | Named in item 34. Real billed-API risk. |
| 30 | `blueprints/corpus/proposals.py:22` | **update — patch it** | Named in item 34. |
| 31 | `blueprints/corpus/curation.py:28` | **update — patch it** | **NOT named in item 34** — found by this branch's own `rg -n "_get_client" blueprints/`. Item 34's hand-written list was stale in the omitting direction, exactly as C-10 rule 3 predicts. |
| 32 | `blueprints/assistant.py:50` | **update — patch it** | Also not named in item 34, also unpatched, also a real billed-call path (`avatar_answer`). Same class; fixing it is one line and leaving it would re-file the identical item next month. |
| 33 | `blueprints/{analysis,applications,diagnostics,generation}.py` | no change | Already patched. |
| 34 | *(mechanism)* `tests/test_ux_stub_coverage.py` | **new — C-11 gate** | Item 34 is the **second** instance of this exact class (item 21 fixed the same shape for `check_refinement_scope`; item 22's diagnosis found a third). Under C-11 the compliant response to a recognized recurrence is a mechanism that fails closed, not another enumeration that rots. New test: AST-walk every `blueprints/**.py`, collect the modules that import `_get_client`, and assert the set equals the set `install_llm_stubs` patches. A future blueprint that imports `_get_client` fails the test until it is either patched or explicitly exempted with a reason. |

---

## Deferred

**D1 — `blueprints/applications.py:2913-2958` still re-stages `experience_summary_items`
from the DB inside the recommend route.** With `build_context_set_from_db` now staging
the same key durably, that re-stage is arguably redundant. Deliberately left alone:
(a) the route's copy is *fresher* (variants added after analyze would be missing from
the durable copy), and (b) removing it would change what
`recommend_experience_summaries` sees, which is behavior this sprint has no mandate to
touch and no eval coverage for. Recorded as a real, known redundancy rather than
quietly folded in.

**D2 — the wiki pages in rows 5/6/7 are not updated on this branch.** Deferred *by the
epic cadence* (§15.2), not by choice, and named individually above so the epic-close
wiki pass has the list rather than re-deriving it. `python -m scripts.wiki_freshness`
must be re-checked at the epic close against the §15.2 threshold of 40.

**D3 — no Playwright UX regression test for the new Compose card.** The sprint brief
forbids touching `ui_pages/selectors.py`, which is this repo's single selector
registry and the only sanctioned way a UX test names a new DOM surface. Writing the
test with inline selectors would fork that registry — the exact drift `ui_pages/`
exists to prevent — so the UI surface is covered server-side (route tests) plus a JS
unit-level assertion, and the Playwright arm is left for whoever is allowed to add the
selector. **This is a real coverage gap, stated rather than papered over.**

**D4 — the legacy `Experience.summary` column (item 59) is not touched.** See the
report and the `## Relationship to item 59` section below.

**D5 — a kept draft becomes a pending variant with NO cross-application leak
guard, and gap-fill's equivalent has one.** `/experience-summary-decide`'s keep
creates `ExperienceSummaryItem(is_active=1, is_pending_review=1)`. Every reader of
those rows — the composition GET's `role_summary_variants`, the
`/recommend-experience-summaries` staging, and
`corpus_to_json_resume._resolve_chosen_experience_summary_text` — filters on
`is_active=1` **only**, never on `is_pending_review`. So an intro drafted for
application A appears in application B's picker for the same role before anyone
has reviewed it. Gap-fill's accepted Bullet has an explicit "pending-leak guard"
for exactly this (`composition_overrides.accepted_generated_bullet_ids`, cited in
`corpus_to_json_resume.py`'s highlights block); intro variants have no
equivalent, and adding one would mean changing three existing read sites this
sprint has no mandate over. **Deferred deliberately, and it is a real behavioural
difference between the two lanes** — not an oversight, and it should be a work
item at the epic close.

---

## The consumer this enumeration missed — recorded, not quietly fixed

**Observed** (`pytest -m ux`, 2026-08-09): 35 failed + 36 errors across the UX
tier, every one of them a timeout on
`#composeList[data-compose-ready]:not([data-compose-bg-pending])`.

**Root cause, from the artifact rather than from reading**: a Playwright
`pageerror` listener attached for the diagnosis printed

```
PAGEERROR: anyRoleVariants is not defined
```

I had removed the `const anyRoleVariants = …` declaration in `loadComposition()`
while widening the toggle gate — and there was a **second consumer 25 lines
further down**, gating `_applyRoleIntros()` and the per-role recommend fire. The
uncaught `ReferenceError` aborted `loadComposition()` before
`_settleComposeIfIdle()` / `data-compose-ready`, so every Compose-touching UX
test hung.

**A/B, not inference:** `git stash push -- static/app.js` → the failing test
passes → `git stash pop` → it fails again. That is what identified the file
before any fix was written.

**Why it belongs in THIS file.** `blast_radius.py`'s own docstring states the
limit: *"the computed offenders check covers first-party Python imports only.
JS (`static/app.js`), Jinja templates and CSS are curation-only."* My Enumeration
section above grepped `assemble_source_union`, `experience_summary_items` and
`_get_client` — all Python — and recorded "0 hits in `static/`" as a negative
result for those symbols. It never enumerated consumers of the local `const` I
was about to delete inside the 8,000-line file I was editing. A single-file local
binding is not what C-10 was written for, and it cost the same way anyway.

**Also worth knowing:** nothing else caught it. `node --check static/app.js`
passed (it is valid syntax), `ruff` passed, `mypy` passed, and all **2,423**
non-UX tests passed. Only `pytest -m ux` failed. A branch that touches
`static/app.js` and skips the UX tier is not verified.

---

## Relationship to item 59 (two existing summary editors)

Item 59 records that a **corpus** role card already offers two ways to write a role
summary: the legacy `Experience.summary` textarea in `_renderExperienceFieldGroup`,
and the canonical `ExperienceSummaryItem` variants section in
`_renderExperienceSummarySection`. The item's own text is explicit that which one wins
is **not established** — it is filed as an observation, not a diagnosis.

The new card added here is **not a third editor of either store**, and the decision is
recorded before the code was written:

- It lives on the **Compose** step, not the corpus role card — a different tab and a
  per-application surface, not a corpus-editing surface.
- Its content is a **transient per-application draft** held on
  `ctx["llm_experience_summary_drafts"]`, exactly like `llm_gap_fill_proposals`. It is
  not a corpus row and never becomes one implicitly.
- It writes to the corpus **only** on an explicit Keep, and then only into the
  **canonical** store (`ExperienceSummaryItem`, `source='llm_proposed'`,
  `is_pending_review=1`) — i.e. it feeds surface (2), never surface (1).
- It **never reads or writes `Experience.summary`.** Item 59's unanswered questions
  stay exactly as unanswered as they were; this branch neither depends on the answer
  nor changes it.

So the count of summary editors on the corpus role card is unchanged at two. What is
added is one drafting affordance on a different step that lands in the canonical one.

---

## Verification

How a missed consumer would surface, and what was run:

1. **`tests/test_prompt_overrides.py::test_registry_covers_every_named_system_prompt_constant`**
   — exact-set assertion over every `*_SYSTEM_PROMPT` module constant. A new persona
   constant left out of `_BASE_SYSTEM_PROMPTS` fails loudly.
2. **`tests/test_call_kind_telemetry.py::test_call_kind_inventory_is_exactly_expected`**
   — AST walk over every production `.py`, exact-set assertion. A new `call_kind`
   literal not reviewed into `EXPECTED_CALL_KINDS` fails loudly, in **both** directions
   (stale entries too).
3. **`tests/test_ux_stub_coverage.py`** (new) — exact-set assertion between "blueprint
   modules importing `_get_client`" and "modules `install_llm_stubs` patches". This is
   the mechanism that makes rows 29-33 not need to be re-derived by hand ever again.
4. **`tests/test_hardening.py::TestAssembleSourceUnion`** — the union's contents are
   asserted element-wise, including the "key absent → unchanged" case that pins
   legacy/file-based byte-identity.
5. **`mypy .`** — `ContextSet` is a TypedDict; a consumer reading the new key with the
   wrong element shape is a type error, not a runtime surprise. (Editor Pyright
   diagnostics in this repo are known stale; mypy is the signal.)
6. **`python -m scripts.gate`** — run by the orchestrator, not this implementer.
