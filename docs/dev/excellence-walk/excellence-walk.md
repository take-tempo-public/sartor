# The "Polished Production Codebase" Walk — durable capture

> **Status:** TEMPORARY / UNTRACKED. This file lives in `output/`
> (gitignored) on purpose — it's insulated from in-flight branch work and
> will be **integrated into `docs/dev/` in a later pass**. Until then, this
> is our living scratch-of-record for the excellence walk.
> **Mode:** form-finding, partnered, evidence-first. No code changes yet.
> **Started:** 2026-06-07.

---

## Context — why we're doing this

After a round-1 assessment of the codebase (typesafe? TDD? bloated?
human-readable? vs. industry?), we aligned on a direction:

1. **Go typesafe-strict** (not the current pragmatic-mypy middle).
2. **Decompose `app.py` (6,290 LOC / 75 routes) into Flask blueprints** —
   needs a dedicated design session + Q&A; load-bearing for all future
   development.
3. **Keep "TDD ~90% in spirit"** but stay diligent and *keep improving* —
   including periodic engineering-design passes over the test suite to find
   efficiencies/redundancies.
4. **Target: a polished production codebase.**
5. **Capture all of this durably** with what/why per item, plus a
   descriptive "state of the work" portion for showing others — and keep
   adding to it. "There will be more before we're done."

---

## DECISIONS LOG (live — appended the moment we decide)

- **2026-06-07 · Pace + working mode** — one question at a time, user steers
  the order. This file is treated as **live**: decisions captured the moment
  they're made, not batched. No waiting for a "final write."
- **2026-06-07 · AI codebase/docs Q&A assistant** — **YES, a real goal**,
  sequenced **after v1.1.0**. So it's a *design constraint we carry forward
  now* (new docs authored to suit it), not something we build yet.
- **2026-06-07 · Starting topic** — begin with **Q4 (knowledge / information
  architecture)**. Rationale: it's the substrate everything else gets stored
  in, the assistant depends on it, and it has a *clock* — the v1.0.6 "6.5
  education sweep" is about to author a large body of new docs (see "Related
  prior artifact" + the Q4 working section).
- **2026-06-07 · Working branch** — `docs/excellence-walk` (off `main`, after
  the other agent merged `feat/run-eval-from-console`). Capture file is
  gitignored so nothing commits; the branch just satisfies the
  `require-feature-branch` hook so live edits flow.
- **2026-06-07 · Q4 ambition — FULL LLM-WIKI NOW.** Adopt the Karpathy
  raw/→wiki/ + ingest/query/lint pattern now (not just conventions). Implies a
  dedicated workstream (**WS-4, promoted to active**) whose substrate must land
  **before Sprint 6.5** so the education sweep authors *into* the wiki rather
  than into throwaway prose. Design being form-found next; ground it in the
  existing Claude-Code implementation (`kfchou/wiki-skills`) + the codebase
  variant rather than reinventing.

- **2026-06-07 · D1 source model — A (git-as-engine).** Code at HEAD is the
  source (diff-driven ingest, no copies); living docs cited not frozen; wiki
  committed. `raw/` kept but redefined →
- **2026-06-07 · raw/ = the CONSTITUTIONAL layer.** Not "homeless external
  knowledge" but the **prescriptive** sources (vision, product direction, the
  10 Principles, durable rationale) everything downstream must stay consistent
  with. Test = *governs vs. describes*, not "low-churn." Friction to be
  **mechanized** (a guard, not just a folder). Git is the raw layer for all
  *descriptive/tracked* material.
- **2026-06-07 · Vision-alignment auditing — CONFIRMED valuable.** With the
  prescriptive layer first-class, `wiki-lint`/`wiki-audit` can check "does what
  we built still match what we said we'd build?"

- **2026-06-07 · Thread order — paused WS-4, walking Q1 next.** User steered off
  the WS-4 design density to a parked spine question, and chose **Q1 (layman
  architecture)** of the three. WS-4 is paused at its resume point (the
  mixed-doc prescriptive/descriptive classification) — nothing unwound. Pace
  unchanged (one-at-a-time, live capture). Before settling Q1's audience/medium,
  the user asked to **make Q1's scope explicit first** (see "Q1 — WORKING").
- **2026-06-07 · Q1 descriptive language SETTLED.** **Ecology omitted as the
  governing frame, but its model accepted (incl. the Governance gap). Keep the
  resulting language + Governance; move on.** Final vocabulary = **seven
  function-nouns + one law**: Substrate · Production · Evaluation · Operation ·
  Memory · Regulation · Governance (the last a named *seam* — designed intent in a
  self-evolving system). Ecology stays a *discovery lens* + candidate *layman skin*
  for the Q1 output, never a category name. Next: settle audience/medium, write Q1.
- **2026-06-07 · SESSION PLAN (user, 4 steps).** *"This is the plan unless
  something pulls us elsewhere."* (1) **resume + finish the WS-4 walk + its
  documentation** [this session]; (2) **write the next-agent handoff** [this
  session]; (3) [next agent] **integrate all temp docs → persistent docs**
  (RELEASE_ARC / CHECKLIST / PRODUCT_SHAPE / etc.) **+ produce the realization
  plan**; (4) [then] **hand off the first prompt of the v1.0.6 epic.** Spine done
  (Q1/Q2/Q3/Q5 ✅); WS-4 is the last thread to walk.

**Still open (design forks for WS-4 — resume here):**
- **The prescriptive/descriptive classification + the mixed-doc split** (the
  important call) — see "WS-4 — Integration & Migration design".
- D2 location/committed · D3 ops/trigger/cost · D5 SCHEMA · D-friction guard ·
  D6 ownership · D4 coverage order · move-vs-register vision.
- Final home + shape of THIS doc when integrated into `docs/dev/`. *Deferred.*

---

## Related prior artifact (read 2026-06-07)

`output/WALKTHROUGH_SPRINT_PLAN_2026-06-07.md` (also temporary/untracked, from
an earlier session) is the **v1.0.5 → v1.1.0 release/sprint plan**: 24
walk-through findings decomposed into sequential one-branch sprints
(V5-A / V5-B → 6.1–6.5 → PV [v1.0.7] → REL [v1.1.0]). Relationships to *this*
excellence walk:

- **WS-2 (strict typing) ⊇ a planned item.** Sprint PV's
  `chore/type-annotation-scan` (item 24) is the explicit v1.1.0 tag criterion —
  but it's modest ("annotate route returns with `ResponseReturnValue` OR flip
  `check_untyped_defs`"). Our "typesafe-strict" goal (full `mypy --strict` +
  typed `context_set`) is an **expansion** of it. Reconcile before executing
  so we don't do it twice or fight the release plan.
- **WS-1 (blueprints) is NOT in that plan.** New ground; needs its own slot.
- **The AI assistant lands past the end of that plan** (after v1.1.0) —
  consistent with the decision above.
- **A lot of new documentation gets written between now and v1.1.0** — every
  sprint handoff + the entire **6.5 in-app education sweep** (per-tab/per-panel
  plain-language summaries). This is the *clock* on Q4.

---

## PART A — Project self-assessment (the descriptive portion)

> Built from round-1 findings, with evidence. Labeled so a reader — including
> someone we're showing this to "as a product and as a work" — sees what's
> genuinely strong, what we're watching, and what's still open.
> **★ = worth drawing attention to when presenting.**

### ✅ Strengths (true and defensible)

- **★ Disciplined dependency hygiene.** 9 runtime deps, every one
  version-bounded (`flask>=3.0,<4.0`, …) and justified inline in
  `pyproject.toml`. No dependency bloat. Reads as a project respectful of the
  people who install it.
- **★ Runtime type-safety at the fuzziest boundary.** Pydantic v2 models +
  `*_REQUIRED_KEYS` frozensets validate every LLM response (`analyzer.py`).
  The most unpredictable surface is the most rigorously checked.
- **★ Clean deterministic / LLM boundary (the "P1 Hardening line").**
  `hardening.py`, `parser.py`, `generator.py`, `scraper.py`,
  `json_resume.py`, `corpus_to_json_resume.py`, `pdf_render.py` are LLM-free
  by contract; all model calls live in `analyzer.py`. Good architecture for
  an AI product.
- **★ Security-by-convention, enforced mechanically.** `_safe_username` +
  `_within` on every fs-touching route, enforced by a `route-security-lint`
  hook (not reviewer vigilance). Only 3 `# type: ignore` in the core.
- **★ Reproducibility / audit trail.** The `context_set` JSON contract +
  `parent_context_path` iteration chain is a maturity most apps never reach.
- **★ Observability + eval rigor.** An LLM-eval harness with `PROMPT_VERSION`
  attribution + deterministic post-gen metrics (verb_diversity,
  specificity_density, grounding_overlap, cost_usd) — rare outside AI-first
  teams.
- **★ Documentation & "explain-why" comments.** ~212 docstring markers in
  `app.py` alone; docstrings cite security reviews by date, explain the SSE
  protocol, flag back-compat carve-outs. Every doc carries a
  Purpose/Audience/Authoritative-for/Sibling-docs header.
- **Serious, multi-tier test suite.** 955 test functions / 67 files / ~18.2k
  test LOC (≈1:1 with all source, ~1.5:1 vs. core). Unit + route +
  Playwright UX + LLM eval tiers.
- **Principle-driven.** P1/P2/P5/P6/P8/P9 annotations thread architecture
  intent through the code; load-bearing, not decoration.

### ⚠️ Watch-outs (real, worth naming honestly)

- **★ `app.py` is a 6,290-line / 75-route monolith.** The clearest smell;
  hurts navigability even though each function is readable. → WS-1.
- **Typing is "typed, not strict."** mypy runs in the gate but isn't
  `strict=true`; `ignore_missing_imports=true` + `follow_imports=silent` are
  loose; payloads are `dict`-typed (`config: dict`, `payload: dict`) rather
  than TypedDict/dataclass; ~117/214 core functions have return annotations.
  → WS-2.
- **Heavy process/meta footprint for a solo beta.** 70 markdown files / ~14k
  doc lines (~comparable to the 12k-line core); RELEASE_ARC, CHECKLIST,
  handoff templates, plugin hooks, skill catalog, agent-failure playbooks.
  Defensible *if* the repo is also a Claude-Code methodology showcase — but
  it's enterprise-scale ceremony on a single-author Beta. (Decide: feature
  or weight?)

### ❓ Ambiguous / needs-a-decision / can't-prove

- **"TDD" is unprovable as written.** Evidence supports *test-rich +
  regression-driven* (14 date-stamped regression tests; tests land in the
  same commit as features) — but nothing proves tests were written *first*.
  Honest phrasing for presenting: *"Test-rich and regression-driven; tests
  ship with every change."* (Your stance: 90% in spirit, stay diligent.)
- **Docs sizing/structure** — well-headed and cross-linked, but is any
  individual file too long, and is there a discoverability index? → Q4.
- **Process-to-product ratio** — strength or bloat depending on framing.

> Suggested framing for outsiders: this reads like **a staff/principal
> engineer's personal project that adopted big-company rigor** — above the
> GitHub median on docs, test discipline, security-by-convention, and
> AI-product engineering; the remaining gap to "polished production" is
> *structural* (split the monolith) and *type-strictness*, not cultural.

---

## PART B — Engineering-excellence backlog (what + why)

> Each item: **What / Why / Status / Notes.** More will be added as we forage.

### WS-1 — Decompose `app.py` into Flask blueprints
- **What:** split the 6,290-line / 75-route monolith into domain blueprints
  (candidate seams: analysis, generation/cover-letter, corpus, dashboard,
  user/config, templates). Preserve the `_safe_username`/`_within` gate + the
  hook that lints it.
- **Why:** navigability + parallel future development; the single biggest
  structural gap to "polished production." Affects all future work → gets a
  **design session + Q&A** before any code.
- **Status:** DESIGN PENDING (do not start coding). Needs its own plan.
- **Open Qs for that session:** blueprint seams & naming; shared-helpers
  location (`_sse`, `_error_detail_payload`, `_safe_username`, `_within`);
  app-factory vs. module-global `app`; streaming (SSE) routes; test-import
  impact (67 test files import from `app`); hook compatibility
  (`route-security-lint` currently targets `app.py`).

### WS-2 — Tighten typing toward strict + model the data contracts
- **What:** move mypy toward `strict=true` (incrementally, per-module
  overrides as a ratchet); model `context_set` and the dict-typed
  request/response payloads as TypedDict/dataclass/Pydantic.
- **Why:** "typesafe-strict" is the stated goal; turns runtime-only
  guarantees into edit-time ones; the `context_set` contract deserves to be a
  *type*, not prose + JSON-schema.
- **Status:** SCOPING. Likely sequenced *with/after* WS-1 (blueprint split
  changes route signatures).
- **Notes:** decide ratchet order (strictest modules first vs. leaf-first);
  whether to adopt a single `ContextSet` Pydantic model as the spine.

### WS-3 — Test-suite engineering-design pass
- **What:** periodic design review of the 955-test suite for efficiencies,
  redundancies, slow tests, coverage gaps, fixture duplication.
- **Why:** stay 90%-in-spirit *and keep getting better*; prevent the suite
  from accreting cost/redundancy as it grows.
- **Status:** RECURRING / future. Define cadence + what "good" looks like.

### WS-4 — LLM-wiki knowledge architecture (ACTIVE — design)
- **What:** adopt the Karpathy LLM-wiki pattern for callback. — a committed,
  human-browseable + LLM-queryable `docs/wiki/` layer (codebase variant: git
  HEAD as source, diff-driven ingest) with `ingest/query/lint` ops as Claude
  Code skills, + a root `llms.txt`. See the **Q4 WORKING / WS-4 design sketch**
  section for the v0 skeleton + the D1–D6 design forks.
- **Why:** Q4 — context-management for the agent, discoverability for humans +
  LLMs, and the substrate for the post-v1.1.0 Q&A assistant. The 6.5 education
  sweep authors *into* it (convergence).
- **Status:** ACTIVE — design form-finding. Decided: **full LLM-wiki now**
  (2026-06-07). Substrate must land **before Sprint 6.5**. Currently on D1
  (source model).
- **Reconcile with:** WS-2 (typing) and the prior sprint plan's PV-4 type scan;
  and the release plan's sequencing (runs parallel; gate before 6.5).

*(room for more — WS-5+ as we forage)*

---

## PART C — Open research agenda (the 5 questions for the walk)

> **Do not jump to fast answers.** Each carries my anticipated approach +
> "further prompts." Research already gathered is captured so we don't refetch.

### Q1 — Describe our architecture & scaffolding to a well-informed layman
- **Approach:** plain-language narrative anchored to the pipeline — paste a
  job post → the tool reads it → asks a few smart questions → you curate your
  experience → it writes a tailored résumé/cover letter grounded in your real
  history → renders to DOCX/PDF, all on your machine. Then "scaffolding" =
  the rails that keep it honest (deterministic core vs. AI brain, the audit
  trail, the test/eval safety nets).
- **Further prompts:** Who is the layman — hiring manager? investor?
  dev-curious friend? Length/medium (a README paragraph? a one-pager?).

### Q2 — Is the code consistent?
- **Approach:** evaluate naming, error-handling, route shape, return-type
  conventions, docstring style, import ordering, dict-vs-model split, module
  headers — across `app.py`/`analyzer.py`/`db/`/`dashboard/`/`ui_pages/`/
  `evals/`. Separate *surface* consistency (style/naming) from *structural*
  (patterns repeated the same way).
- **Early signal:** strong header/docstring/naming conventions; main
  inconsistency risk is dict-typed vs. typed payloads (→ WS-2) and route
  size/shape variance inside the monolith.
- **Further prompts:** rubric + per-area grade, or a prose read?
- **DONE (2026-06-07):** shape = **layered** (prose + grade table). Evidence-
  gathered from `app.py` + 4 module headers. **Key finding: consistency TRACKS
  ENFORCEMENT** — every hook/linter-guarded pattern is uniform; the only real gaps
  are the two unenforced ones already on the backlog (return-types + dict-vs-model
  → WS-2/PV-4; the 6,290-LOC/75-route monolith → WS-1). **Persisted →
  `output/_dev-notes/Q2_consistency_draft.md`** (temp). Completes the five-question
  spine.

### Q3 — Every NON-dependency download to run (a) the basic tool and (b) the full eval suite
*(Mostly factual — research gathered; confirm/refine, don't treat as final.)*

**(a) Basic tool — run the app**
1. **Python 3.10+** — the interpreter; the whole app is Python.
2. **The repo (git clone)** — not shipped as a PyPI wheel for end users;
   install is `pip install -e .` from a clone.
3. **Chromium binary** via `python -m playwright install chromium` (~150 MB,
   into OS user cache, *not* the repo) — drives headless Chromium for
   **deterministic PDF + live HTML preview rendering**. The one big non-pip
   download for normal use.
4. **An Anthropic API key / account** — credential, not a download; required
   because all LLM calls go to Claude.
5. **A modern browser** — the app is a local Flask site you open in-browser.
6. **(Linux only) Chromium system libs** (`libnss3`, `libatk1.0-0`, …) — OS
   packages Chromium needs; surfaced by the playwright installer.

**(b) Full suite + eval harness (grounding signals)**
7. **`pip install -e ".[dev]"`** — pytest/ruff/mypy/pyyaml/types-requests.
8. **torch** (CPU ~200 MB, or a CUDA wheel) — installed **first**, from a
   platform-specific index URL; deliberately *not* in `pyproject.toml`
   because the wheel is platform-specific. Backbone for the grounding models.
9. **`pip install -e ".[eval-grounding]"`** — transformers + MiniCheck
   (git+ install).
10. **DeBERTa-v3 NLI weights** (~180 MB, Apache-2.0) — auto-download to the
    HuggingFace cache on first use; NLI-entailment grounding signal.
11. **MiniCheck flan-t5-large weights** (~3 GB, **academic/research license**
    — never ships to prod) — auto-download to HF cache; factual-grounding
    signal.
12. *(Chromium from #3 is also what `pytest -m ux` drives.)*
- **Further prompts:** audience for this list — a README "what gets
  downloaded & why" section, or an internal provenance note? Include
  on-disk locations + licensing? (Both partly documented in
  `docs/install.md` + `CONTRIBUTING.md`.)
- **DONE (2026-06-07):** shape = **layered** (mixed/portfolio). Facts **verified**
  vs `pyproject.toml` + `install.md` + `CONTRIBUTING.md` (sharpened: exact HF/
  Chromium cache paths, MiniCheck `git+` install, ~3.2 GB first-run total, added
  `git` + the precise `[dev]` extras). **Persisted → `output/_dev-notes/Q3_downloads_draft.md`**
  (temp). Direct input to Sprint 6.5 `docs/eval-stack-install-guide` (#17) +
  candidate README/`install.md` section.

### Q4 — Are docs too big? Well-sized / linked / self-described / discoverable (humans + LLMs)? Restructure for context-management? Would Karpathy's "llm-wiki" approach fit? And re-answer assuming we will build a codebase/docs Q&A assistant.
*(Research started; deliberately NOT answering yet.)*
- **Sizing data:** `docs/` = 19 files / 6,451 lines. Largest:
  `RELEASE_CHECKLIST.md` 941, `architecture.md` 723, `PRODUCT_SHAPE.md` 681,
  `walkthrough.md` 538, `RELEASE_ARC.md` 457. Root: `CHANGELOG.md` 1,224,
  `vision.md` 312, `CONTRIBUTING.md` 232, `SECURITY.md` 208, `README.md` 175.
- **Structure signal:** every doc has a Purpose/Audience/Authoritative-for/
  Sibling-docs header (excellent self-description). Cross-link density high
  for hubs (architecture 44, README 40, PRODUCT_SHAPE 33) but thin for some
  dev docs (RELEASE_ARC 6). No central `docs/README.md` index spotted —
  discoverability rides on sibling-doc headers + README/AGENTS pointers.
- **TODO before answering:** (1) verify exactly what "Karpathy's llm-wiki
  approach" refers to before recommending it; (2) think through
  chunking/retrieval needs *if* the Q&A-assistant goal is real (Decision #2)
  — stable anchors, per-section front-matter, a machine-readable index,
  "answers-this-question" tags spanning the how-do-I-rename-a-job-title ↔
  how-does-the-grounding-suite-work range.
- **Further prompts:** see Open Decision #2.

### Q5 — Descriptive "state of the work" portion → DONE (PART A above)
- Captured + labeled ✅ / ⚠️ / ❓ with ★ presentation-flags. Keep editing as
  findings land.

---

## PART D — What's next (as of 2026-06-07 close)

**Active thread: WS-4 (LLM-wiki).** Resume on the design forks, roughly in order:
1. **Doc classification + the mixed-doc split** — the important call the user
   flagged (prescriptive vs. descriptive; whole-doc vs. split). See "WS-4 —
   Integration & Migration design" → Open migration questions #1–#5.
2. **D2** location/committed → **D3** ops/trigger/cost → **D5** SCHEMA design →
   **D-friction** constitutional guard → **D6** ownership → **D4** coverage order.
3. Then *build*: bootstrap skeleton → adapt wiki-skills ops → cold-ingest code →
   classify + migrate docs → wire maintenance. Substrate **before Sprint 6.5**.

**Still parked (rest of the excellence walk — one at a time):**
- Q1 (layman description), Q2 (consistency), Q3 (downloads — research mostly
  done) — pick up after WS-4 design settles.
- **WS-1** (`app.py` → blueprints) — biggest *code* lever; needs its own design
  session.
- **WS-2** (strict typing) — reconcile with the prior plan's PV-4 type scan.
- **WS-3** (test-suite design pass) — recurring.
- Deferred: final home/shape of THIS doc when integrated into `docs/dev/`.

**Session state:** branch `docs/excellence-walk`, **no commits** (capture is
gitignored / temporary by design — nothing to merge). Durable record = this file
+ `output/WALKTHROUGH_SPRINT_PLAN_2026-06-07.md`.

---

## Q1 — WORKING (active thread, started 2026-06-07)

> Walking Q1 (describe architecture & scaffolding to a well-informed layman).
> Before audience/medium, the user pushed the **binary** (architecture vs.
> scaffolding) as *insufficient* and asked to **find a rudimentary descriptive
> language** for the system as-becoming that maps elegantly to what-is. This
> section is the live form-finding of that language. **Status: LANGUAGE SETTLED
> (2026-06-07)** — see the box just below; the trail of how we got there follows.
> **Audience/medium DECIDED:** mixed / portfolio-facing · **layered** (overview.md
> candidate) — BUT use only the *organization* the ecology surfaced (the seven
> functions + the one-way law + Product/Work split), **NOT the ecological
> language** (no soil/metabolism/fauna). Plain, literal prose, layered. **Q1 draft
> v1 PERSISTED → [`output/_dev-notes/Q1_overview_draft.md`]** (2026-06-07; temp,
> gitignored). Feeds the planning process after the walk; candidate
> `docs/wiki/overview.md`. Four open revision points live in that file's footer.

### ✅ SETTLED — the seven functions + one law (2026-06-07)
Decision: **ecology OMITTED as the governing frame, its model ACCEPTED (incl. the
Governance gap). Keep the resulting language + Governance; move on.**

| Function | Does | Members |
|---|---|---|
| **Substrate** | the material metabolized (state) | `configs/`, `resumes/`, `output/`, `db/`, `context_*.json` |
| **Production** | synthesizes output from Substrate — *the Product* | `app`/`analyzer`/deterministic core/`db`/`personas`/frontend |
| **Evaluation** | measures · verifies · improves Production *(active)* | `evals/`, `tests/`, `dashboard/`, build+perf `scripts/` |
| **Operation** | active labor that builds + reshapes | `.claude-plugin/commands/` + `agents/`, human + AI |
| **Memory** | recallable knowledge + rules drawn upon | `docs/`, wiki, `llms.txt`, the contract, `CHANGELOG` |
| **Regulation** | gates · enforces · advances; keeps in bounds | hooks, quality gate, branch/release discipline |
| **Governance** | prescriptive north-star answered to — **SEAM: designed intent, not emergent; kept + named** | `vision.md`, 10 Principles, direction |

**The law:** every dependency points inward toward **Production**; Production
answers only upward to **Governance** (= the codebase's own one-way dependency
rule, scaled up). **Two subjects:** Production(+Substrate) = the *Product*;
Evaluation + Operation + Memory + Regulation = the *Work* that evolves it;
Governance governs the Work. **Ecology** = discovery lens + candidate layman *skin*
only — never a category name.

### Scope refinements the user locked (2026-06-07)
1. **Load-bearing test for architecture.** Architecture is what *stands on its
   own*. Remove the scaffolding and the architecture still stands. Scaffolding
   exists to let you *access, shape, and engage* the architecture.
2. **as-is INCLUSIVE-OR as-becoming**, mapped to the WS-4 **prescriptive /
   descriptive** split. The description language must hold both poles at once.
3. **The dependency-direction rule.** A thing is scaffolding only if it is
   *exclusive to the production/shaping process*. There may be code in it, but
   **not code that is part of the architecture — if it's part of the
   architecture, it's architecture.** **Scaffolding MAY use architecture;
   architecture MAY NOT use scaffolding.** (Directional, acyclic.)

### The organizing law (the "aha")
Refinement #3 is **the codebase's own internal law, scaled up to the whole
system.** Inside the code: `hardening.py` ↛ `analyzer.py` ↛ `app.py`; the P1
deterministic/LLM boundary; production ↛ `evals/`. Dependencies point one way and
never reverse. The whole-system description should obey the *same* one-way law —
which is *why* it "maps elegantly to what-is": the categories inherit the
architecture's own dependency discipline.

### The binary is insufficient → a rudimentary language (PROPOSED, under exploration)
User's own moves dissolved the binary: the **eval harness is not scaffolding** —
it's a *functional system*, architecture-class, but "a **workshop** attached to
the house"; **docs/wiki are like electrical/plumbing** (integrated utilities, not
external frame); and **production mechanisms** are a distinct thing again. So:
**5 roles + 1 law**, with an estate-metaphor *skin* over a dependency-law *spine*.

| Role (skin) | Relation to Core | Prescriptive/Descriptive | Examples |
|---|---|---|---|
| **Charter** (blueprint / building code) | **governs** the Core (Core conforms; nothing imports it) | prescriptive · as-becoming | `vision.md`, the 10 Principles, product direction (= WS-4 constitutional `raw/`) |
| **Core** (the house) | **bears** the load; the thing itself | descriptive · as-is | pipeline, deterministic core + LLM brain, DB, `context_set`, renderers, **+ runtime honesty rails woven in** (grounding, security gate, Pydantic validation) |
| **Adjacent system** (the workshop) | **uses + improves** the Core (depends on Core; Core doesn't depend on it) | descriptive · as-is | eval harness, tuning loop, `/_dashboard` |
| **Utility** (electrical / plumbing) | **describes + serves** the Core; carries the Charter | renders *both* poles | `docs/`, the WS-4 wiki, `llms.txt`, CHANGELOG |
| **Apparatus** (the build rig — "scaffolding" proper) | **shapes + enforces** the Core; enforces the Charter onto it | mechanizes prescriptive→descriptive | plugin hooks, agent contract (AGENTS/CLAUDE), quality gate, branch/release discipline, handoff method |

**One law:** every dependency points **inward toward the Core**; the Core answers
**only upward to the Charter**. Charter imports nothing; Apparatus & Adjacent may
use the Core but the Core may use neither.

**The flow (relationships, not just bins):** Charter → *governs* → Core ← *improves*
← Workshop; Utility *describes* Core/Workshop and *carries* Charter; Apparatus
*enforces* Charter onto Core (hooks = mechanized constitutional friction). The
**as-is/as-becoming bridge** lives in two places: the **Utility** layer *renders*
both poles (wiki: constitutional pages carry the Charter, synthesized pages
describe the Core), and the **Apparatus** *drags* as-is toward as-becoming.

### Live tensions / open questions (don't paper over)
- **"Scaffolding" mis-connotes "temporary"** — the hooks/contract are permanent.
  Keep the metaphor-name, or pick a truer one (apparatus / forge / build-rig)?
- **Utility vs. Apparatus** — truly two roles? (Utility *delivers knowledge*,
  passive/serving/read-by-all; Apparatus *enforces*, active/gating/run-on-change.)
  Edge case: CHANGELOG / release-arc = Utility-that-the-Apparatus-writes.
- **Where the honesty rails live** — grounding/security/validation are *inside the
  Core* (load-bearing safety). But grounding's *eval-time* cousins (L1/L2
  NLI/MiniCheck) live in the **Workshop** — same concept, two homes by hot-path
  discipline. (The taxonomy doing real work.)
- **The Workshop→Core promotion** — tuning *manufactures a part* (a prompt
  candidate) that gets *installed into the house* (`analyzer.py`) under a
  human-gated **Apparatus** step (promote + PROMPT_VERSION bump). One real
  workflow crosses Workshop→Core under Apparatus supervision.
- **Rudimentary, not baroque** — resist over-splitting; the test is whether 5
  roles + 1 law is the *minimal* set that holds everything.

### Alternate descriptive lenses (to react to — user asked for "different ways")
- **Estate (spatial):** house / workshop / utilities / blueprint / build-rig.
  Layman-friendly; metaphor-risk. *(the skin above)*
- **Dependency law (formal):** strict directional layers, membership by "what
  depends on what." Rigorous, codebase-native, LLM-friendly; dry. *(the spine)*
- **Roles/observers (who engages, when):** user touches the Core; maintainer/agent
  works through the Apparatus; the system studies itself via the Workshop;
  everyone reads the Utility; it all answers to the Charter. Ties to Q5's "as a
  product AND as a work."

### Refinements from the sort (2026-06-07)
- **"Scaffolding" RETIRED as a category name.** It failed its only justification
  (the friction isn't mechanized) and the word smuggled in "temporary," which is
  false (hooks/contract are permanent). Let it go.
- **"Utility as knowledge" judged too frail.** Plumbing/electrical ≈
  circulatory/nervous are *active, complex distribution-and-regulation systems the
  organism depends on*, not passive knowledge. Utility gets upgraded (below).
- **Metaphor → analogue.** A metaphor is a *picture* (mis-leads, e.g.
  "scaffolding"); an **analogue** is a *structural correspondence* (anchored to
  function/relations). **Prefer INTERNAL analogues** — describe each role by
  analogy to the system's *own* trusted laws (one-way dependency, deterministic/
  LLM boundary, grounding source-vs-synthesis, hot-path discipline) rather than
  borrowed pictures. External metaphors are disposable skins kept only where the
  correspondence is exact.

### The sort exercise — what it revealed (2026-06-07)
Ran the real tracked surface through the model. Condensed placement:
- **Core (the Product):** `app.py`, `analyzer.py`, `hardening.py`, `generator.py`,
  `parser.py`, `pdf_render.py`, `json_resume.py`, `corpus_to_json_resume.py`,
  `scraper.py`, `db/*`, `static/`, `templates/`, `ui_pages/`, `personas/` — **+
  the runtime honesty rails woven in** (grounding, `_safe_username`/`_within`,
  Pydantic).
- **Workshop (measures/verifies/improves the Core):** `evals/*`, `dashboard/`,
  `tests/*`, `promptfooconfig.yaml`, and the **build/measure tools** in `scripts/`
  (`perf_baseline`, `export_corpus_seed`, `capture_screenshots`,
  `build_bundled_templates`, `smoke_phase_b1`).
- **Distribution (carries knowledge + rules to all actors)** [the upgraded
  "Utility"]: `docs/*`, the WS-4 wiki, `llms.txt`, the agent contract
  (AGENTS/CLAUDE), `CHANGELOG.md`, `AGENT_HANDOFF_TEMPLATE.md`.
- **Regulation (gates / enforces / advances)** [replaces dead "scaffolding"]:
  `.claude-plugin/hooks/*` (immune/reflex guards), the quality gate
  (ruff/mypy/pytest), branch + release discipline (`RELEASE_ARC`/`CHECKLIST`),
  `AGENT_FAILURE_PATTERNS.md`.
- **Operators/effectors:** `.claude-plugin/commands/*` + `agents/*` — the labor
  that *drives* the above (actors, not an organ; see "observer" lens).

**Friction cases = the gold:**
1. **Co-location ≠ category.** `dashboard/` is mounted in the product's Flask app
   but is **Workshop** by dependency/function; `ui_pages/` lives in the product yet
   is **Core** that the Workshop *uses* (legal direction). Sort by dependency, not
   by where it lives.
2. **The Workshop manufactures parts installed elsewhere, human-gated.**
   `build_bundled_templates` → Core assets; `capture_screenshots` → Distribution
   assets; the tuning loop → a Core prompt. The *install* step is always a
   **Regulation** gate (promote + `PROMPT_VERSION` bump; the checklist).
   Recurring flow: **Workshop → (Regulation gate) → Core/Distribution.**
3. **Data/state isn't in the structural taxonomy.** `configs/`, `resumes/`,
   `output/`, `db/resume.sqlite` are the user's *content* — what the Core *bears*,
   not a room. Out of the structural language (or its own "State" note).
4. **Mixed docs split across organs.** `AGENTS.md` is **Distribution** (carries
   rules) + **Charter** (its prescriptive portion) + it *defines* **Regulation**
   (the hooks enforce it). One file, three roles — **exactly the WS-4 mixed-doc
   problem.** Q1's language and WS-4's migration crux are the *same* problem.
5. **Content vs. process resolves the old edge.** `RELEASE_CHECKLIST` =
   **Distribution** content that the **Regulation** process writes/reads. An
   artifact can be content for one organ and input to another — not a conflict.
6. **Double home by hot-path discipline.** Runtime grounding/security/validation =
   **Core**; their eval-time cousins (L1/L2 NLI/MiniCheck) = **Workshop**.

### The reframe the sort forced: TWO ORGANISMS, one Charter (PROPOSED)
"Load-bearing" was ambiguous because it never said *for which subject*. The
language actually describes **two nested organisms** — which is literally Q5's "as
a product AND as a work":
- **The Product** (organism 1) — what the user runs. Load-bearing part = **Core**.
- **The Work** (organism 2, *contains the Product as an organ*) — everything that
  produces/evolves/maintains the Product: **Workshop** (measure/improve),
  **Distribution** (carry knowledge+rules), **Regulation** (gate/enforce/advance).
  Remove these and the *Product* still runs but the *Work* dies (no one can safely
  change it; the agent can't navigate). So they're load-bearing *for the Work*.
- **The Charter** governs the **Work**; the Work moves the Product from **as-is**
  toward the Charter's **as-becoming**. (Charter = prescriptive; Product+Work
  artifacts = descriptive. The bridge: **Distribution** *renders* both poles;
  **Regulation** *drags* as-is → as-becoming.)

This upgrades "Utility": its life is being the **distribution+regulation system of
the Work-organism**, not mere knowledge — answering "utility may have a life."

**Rudimentary set now:** 1 **Charter** + 1 **Core** (the Product) + the **Work** =
{ **Workshop**, **Distribution**, **Regulation** }; **actors** (user / maintainer /
AI agent) engage each (observer axis, orthogonal). The dead "scaffolding" is
cleanly replaced by **Regulation**; nothing is homeless.

**Open after the sort:** (a) Distribution⊕Regulation one organ or two; (b) user
data — now REQUIRED in-model (see ecology); (c) operators — now ACTIVE, not
observer-axis (see ecology); (d) labels — see register finding + ecology below.

### Naming register — function-nouns, not pictures (2026-06-07)
User flagged **"Workshop" is a different KIND of word** — and it is: the spine had
mixed registers (Distribution/Regulation = abstract **function-nouns**; Charter =
thing-instrument; Core = position; **Workshop = place-metaphor, the last
estate-skin survivor**). Decision-in-progress: **make the spine function-nouns**
(this *completes* the metaphor→analogue move — purge the last picture).
- **Workshop → Evaluation** *(recommended)* — internal analogue (the repo's own
  `evals/`), concrete, self-naming; "improve" is its gated consequence (tuning).
  Alts: **Assurance** (QA lineage, carries "+improve", but vaguer); **Feedback**
  (purest control-loop, breaks the -tion/-ance morphology).
- Estate/body metaphor **demoted to a disposable skin** for the layman-facing Q1
  narrative only — never the canonical category names.

### Ecological reframe (2026-06-07) — the third metaphor family, used as a DISCOVERY LENS
User's five steers pushed us off architecture/estate/body toward **ecology**, and
it cracked two things open:
1. **"Distribution" is wrong — nothing distributes.** Knowledge is *deposited and
   recalled* (pull, not push). Ecological role = **soil humus / mycorrhizal
   network** organisms *draw from*; the wiki-**ingest** is *decomposition*
   (code→knowledge-nutrients), query is *uptake*. Function-noun fix: **Memory /
   Reference** (the WS-4 wiki *is* a codebase memory; internal analogue).
2. **Regulation — KEEP** (user: "strong and clear"); ecology makes it *native*
   (homeostasis / population regulation / immune response).
3. **Operators + witnesses are ACTIVE, first-class.** Not an "observer axis." In
   ecology they're **fauna**: *ecosystem engineers* (agents/commands/human — beaver/
   earthworm: actively reshape the system) and *sensing-corrective fauna*
   (Evaluation — perceives fitness, triggers tuning). The witness role is *active*.
4. **User data is IN the model** (not out-of-scope furniture): `configs/`,
   `resumes/`, `output/`, `db/resume.sqlite` = the **substrate / soil / standing
   nutrient stock** (the corpus = accumulated career biomass; a JD = sunlight/
   external trigger; the generated résumé = fruit/exported product). Foundational —
   no soil, no ecosystem.

**Ecology-informed role set (function-noun spine; ecology = skin):**
| Function-noun | Ecological role | Was | Members |
|---|---|---|---|
| **Substrate / State** | soil + nutrient stock | (out of scope) | `configs/`, `resumes/`, `output/`, `db/resume.sqlite`, `context_*.json` |
| **Production** | primary producers (photosynthesis: compute × corpus × JD → résumé) | Core | the pipeline `app`/`analyzer`/deterministic core/`db`/`personas`/frontend |
| **Evaluation** | sensing-corrective fauna (active) | Workshop | `evals/`, `tests/`, `dashboard/`, perf/build `scripts/` |
| **Operation** | ecosystem engineers (active) | Operators (observer axis) | `.claude-plugin/commands/` + `agents/`, the human + AI agents |
| **Memory / Reference** | humus + mycorrhizal network + decomposers | Distribution | `docs/`, wiki, `llms.txt`, agent contract, `CHANGELOG`; ingest/lint = decomposers |
| **Regulation** | homeostasis / immune / population control | Regulation | `.claude-plugin/hooks/`, quality gate, branch/release discipline |
| **Governance** | **STRAIN POINT** — selective pressure / fitness target | Charter | `vision.md`, 10 Principles, product direction |

**The honest seam:** ecology has **no designer** — nature isn't *governed*, it's
*selected*. So **Governance/Charter is where the ecological model strains** (just as
"load-bearing for whom" was the estate model's strain). Best ecological reading:
the Charter is the **selective pressure / niche definition / climate** — it builds
nothing but determines what *survives*; drift from it = *maladaptation*; WS-4
vision-alignment auditing = *measuring fitness against the selective environment*.
Name the seam, don't paper it: **a designed system embedded in an evolutionary
frame.**

**Resolution (proposed):** ecology is the best **discovery lens** yet (the system
is genuinely alive — active agents, metabolism, regulation, evolution toward a
fitness target) AND a strong candidate **skin for Q1's actual layman output**. But
per the metaphor→analogue commitment, **the canonical spine stays function-nouns**;
we *harvest* ecology's insights (Substrate in-model; Memory not Distribution;
Operation/Evaluation as active fauna) rather than adopt "mycorrhizal network" as a
category name (that would re-make the "scaffolding" mistake at higher cost).
**Self-similarity payoff:** the *product* is a grounding/synthesis engine (raw →
synthesis, no invention); the *ecosystem* is a **metabolism** (nutrients → product).
The system is metabolic at both scales — same move, two altitudes.

---

## Q4 — WORKING (active thread, started 2026-06-07)

### Reference patterns (researched, not yet adopted)
- **Karpathy "LLM Wiki".** A knowledge base structured *for a model to query,
  not a human to browse*: `raw/` (immutable sources) → an LLM-compiled
  `wiki/` of interlinked `.md` pages (summaries, backlinks, concept articles)
  → a schema file (e.g. `CLAUDE.md`). Three operations: **ingest** (compile
  new sources into wiki pages), **query** (answer questions from wiki + source
  verification), **lint** (health checks: drift, contradictions, missing
  coverage, weak links). The **codebase variant** makes `git commit` the
  ingest trigger and grounds every claim in `path:line` citations a freshness
  check can verify.
- **`llms.txt`.** The lighter companion: a curated, root-level markdown
  "sitemap for LLMs" — H1 + grouped sections + links to key pages + short
  descriptions; optional `llms-full.txt` inlines the content. Reported ~10×
  token reductions vs. serving HTML. Still an evolving, informal spec.

### The convergence insight (the reason this is the first thread)
The **dev docs**, the upcoming **6.5 in-app education content**
(per-tab/per-panel plain-language summaries), and the **post-v1.1.0 Q&A
assistant** are *one knowledge base in three renderings*. The assistant's job
("how do I rename a job-experience title" ↔ "how does the grounding suite work,
set it up") is exactly the LLM-wiki **query** op over our repo+docs — and the
6.5 sweep is about to author content across that whole range. Decide the
authoring pattern *before* 6.5 writes it → assistant nearly free later. Decide
after → retrofit a mountain of docs. **Q4 has a clock; the others don't.**

### Current-state read (evidence; the "understand" half of Q4)
- **Too big per file?** A few are heavy: `RELEASE_CHECKLIST.md` 941,
  `CHANGELOG.md` 1,224, `architecture.md` 723, `PRODUCT_SHAPE.md` 681,
  `walkthrough.md` 538. Heavy isn't automatically wrong (CHANGELOG *should* be
  long; a checklist *should* be exhaustive) — but several mix multiple
  concerns in one file, which hurts both human scanning and LLM chunking.
- **Self-described?** Strong — every doc has a Purpose/Audience/
  Authoritative-for/Sibling-docs header. This is already half of an
  `llms.txt`-style discipline, done by hand.
- **Well-linked?** Hubs yes (architecture 44, README 40, PRODUCT_SHAPE 33);
  thin on some dev docs (RELEASE_ARC 6). Links are sibling-to-sibling, not
  hub-and-spoke through an index.
- **Discoverable (humans + LLMs)?** Gap: **no central `docs/README.md` index
  and no `llms.txt`.** Discovery relies on chasing sibling headers from
  README/AGENTS. An LLM (or me) has no single machine-readable map.
- **Context-management for the agent?** The hand-headers help, but there's no
  stable-anchor / per-section-front-matter convention, so I can't reliably
  load *just* the relevant slice — I tend to pull whole large files.

### The fork (being put to the user)
Given the assistant is post-v1.1.0 but the doc-heavy sprints run now —
**how ambitious, and when?**
1. **Conventions now, substrate later (recommended)** — define an
   "assistant-ready" authoring spec now (stable anchors, per-section
   front-matter, `path:line` citation habit, plain-language + technical
   layering) so 6.5 + every sprint doc is written once, correctly; add a light
   `docs/README.md` index + `llms.txt`. Defer the generated `wiki/` + the
   assistant build to post-v1.1.0.
2. **Full LLM-wiki adoption now** — stand up `raw/ → wiki/` + ingest/query/lint
   immediately. Highest forward leverage; real new machinery competing with
   the release work.
3. **Minimal now** — fix obvious gaps (index, split oversized files, `llms.txt`)
   only; revisit architecture after v1.1.0. Lowest effort; 6.5 gets written in
   the old shape → retrofit later.

*Sources:* [llms.txt spec](https://llmstxt.org/) ·
[Karpathy LLM-wiki gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) ·
[LLM-wiki for codebases (DEV)](https://dev.to/yysun/bringing-the-llm-wiki-idea-to-a-codebase-22go) ·
[wiki-skills (Claude Code impl)](https://github.com/kfchou/wiki-skills)

### Prior-art mechanics (researched 2026-06-07)
- **`wiki-skills` layout:** `SCHEMA.md` + `raw/` (immutable sources) +
  `wiki/{index.md, overview.md, log.md, pages/}` + `assets/`. Ops are **Claude
  Code skills, manually invoked**: `wiki-ingest` (source → page + backlink
  audit), `wiki-query` (read wiki, offer to file answers back w/ `[[citations]]`),
  `wiki-lint` (severity-tiered drift/coverage report), `wiki-audit` (fact-check
  a page vs. sources via parallel subagents), `wiki-update`, `wiki-init`. No git
  hooks in that impl. Grounding = bidirectional `[[links]]` + quote
  string-matching + `[synthesis]` citations judged against cited ranges.
- **Codebase variant:** the **repo at git HEAD is the source of truth**; first
  ingest scans HEAD, later runs **diff the saved last-ingest SHA → HEAD** (free
  rename/delete tracking, incremental). Git is "the maintenance engine," not an
  archive. Covers modules, concepts, entities (schemas/models/types), flows,
  architectural shifts, gaps/stale areas.

### WS-4 design sketch (v0 — for discussion, not built)
**Two source bodies, one wiki:** (1) **code** — source = git HEAD, diff-driven
ingest, no copies; (2) **curated docs + the 6.5 education content** — stay
living, get *cited*, not frozen.

**Proposed skeleton (committed in-repo so it's versioned + assistant-servable):**
```
docs/wiki/
├── SCHEMA.md          # conventions; points at AGENTS.md/CLAUDE.md as the contract
├── index.md           # one-line summary per page (doubles as the llms.txt map)
├── overview.md        # synthesized system summary
├── log.md             # append-only ingest/lint record
├── .last_ingest_sha   # codebase-variant checkpoint
└── pages/             # flat, slug-named, [[backlinked]], path:line-grounded
```
plus a root **`llms.txt`** pointing at `docs/wiki/index.md` + key living docs.

**Ops vehicle:** Claude Code skills under `.claude-plugin/`, adapted from
`kfchou/wiki-skills` (`/wiki-ingest`, `/wiki-query`, `/wiki-lint`,
`/wiki-audit`). Trigger = manual skill + a *lightweight* commit-time freshness
**reminder** hook (NOT auto-ingest — per-commit LLM cost). `wiki-lint` as a
periodic + pre-release gate (fits the existing RELEASE_CHECKLIST discipline).

**Coverage v1 (lands before Sprint 6.5):** stand up the skeleton + ingest the
**code architecture** (module map, the P1 deterministic/LLM boundary, the
`context_set` contract, pipeline flows, routes, the eval harness) — proves the
machinery and helps the agent's context-management *now*. Reserve a
**user-facing section** that the 6.5 education sweep authors into.

**Open design forks (agenda — walk one at a time):**
- **D1 · Source model** (LEAD — being asked now): hybrid git-as-engine vs.
  strict `raw/` vs. code-only.
- **D2 · Location + tracked-vs-generated** (`docs/wiki/` committed?).
- **D3 · Ops vehicle + trigger + token cost** (skills + reminder hook vs. more).
- **D4 · Coverage order** (code-first vs. user-education-first).
- **D5 · Schema reuse** (SCHEMA.md referencing AGENTS.md/CLAUDE.md, not duplicating).
- **D6 · Maintenance ownership** (who runs ingest/lint; per-branch closing agent? pre-release?).

### D1 analysis — source-model deep-dive (2026-06-07)
**Reframe:** A and B aren't mutually exclusive. Best fit = **A as the spine**
(git-as-engine over code + living docs) **+ a small B-style `raw/`** only for
genuinely-immutable external inputs (10-Principles notes, point-in-time design
rationale, the prior sprint-plan artifacts).

**A · Hybrid, git-as-engine**
- *Git mechanics:* `docs/wiki/.last_ingest_sha` = checkpoint. Ingest =
  `git diff --name-status <sha> HEAD` → only changed files (A/M/D/R, renames
  tracked) get re-read; update affected pages + backlinks; bump SHA; commit.
  Code is NEVER copied — HEAD is the source; docs stay living, cited not frozen.
- *Performance:* cold first ingest = whole-repo pass (one-time, chunk per
  module). Steady state = tiny per-branch diffs → cheap. Query reads the small
  curated wiki, not the repo → fast/low-token. Lint batchable.
- *Pros:* single source of truth (no code copy/drift); living docs stay live;
  incremental + cheap; wiki committed = versioned / reviewable / assistant-
  servable; staleness is *measurable* (sha→HEAD); slots into existing hooks +
  branch close-out + RELEASE_CHECKLIST; path:line grounding = verifiable answers.
- *Cons/constraints:* derived artifact can lag HEAD between ingests (mitigate:
  commit-time reminder hook + pre-release lint gate + measurable debt); needs an
  ownership rule (D6); path:line cites brittle to line shifts (mitigate: prefer
  symbol/anchor cites + freshness re-locate); cold ingest cost; two grounding
  modes (code path:line + doc anchors).
- *How it runs:* init → cold ingest (module-by-module) → steady-state ingest at
  branch close-out (diff-driven) → reminder hook nudges debt → periodic +
  pre-release lint/audit → query (me now; assistant post-v1.1.0).
- *Maintenance:* engine = git diff; cost scales with churn, not repo size;
  ownership = branch close-out + pre-release gate (D6).

**B · Strict raw/ wiki-skills**
- *Git side:* git is just storage; `raw/` is immutable input. No diff-driven
  code ingest — the "source" is raw/ docs, so code changes don't propagate
  unless you re-snapshot code into raw/ (→ you end up bolting on A anyway).
- *Pros:* least adaptation of the shipped skills; correct for genuinely
  immutable external reference; clear frozen-evidence provenance.
- *Cons:* freezing living docs (README/install/architecture) into raw/ =
  duplication + rot; doesn't natively handle a living codebase; manual
  re-snapshot burden; two copies of the truth (violates single-source ethos).
- *Right role:* the narrow class of immutable inputs — i.e., the small `raw/`
  *inside* option A, not the whole model.

**Recommendation:** A (git-as-engine) backbone + a small `raw/` for frozen
reference only. D2 (location/tracked), D3 (ops/trigger/cost), D6 (ownership)
then fall out of A.

### Why a `raw/` layer at all — the LLM lens (2026-06-07)
The wiki is *synthesis* (lossy, fast to query). `raw/` is *ground truth*
(immutable, full-fidelity). Keep both because an LLM needs both — and because an
LLM is an **unreliable narrator of its own synthesis**: with no source to
falsify against, synthesis errors silently become "facts." What `raw/` buys,
from the model's side:
- **Verification anchor** — `wiki-audit` fact-checks pages against raw/; a
  `[[citation]]` resolves to immutable text.
- **Fact vs. interpretation (provenance)** — raw/ = what was said; wiki = what we
  concluded. On conflict, raw/ wins.
- **Fidelity on demand** — read the wiki for the map; drop to raw/ for the detail
  the summary dropped.
- **Rebuildable** — wiki is a *compiled artifact*; raw/ is the *source* you
  re-ingest from if the schema/model improves or a page rots.
- **Stable citation** — an immutable target doesn't rot the citation under it.

This is the *same move as the product's own grounding check*:
**raw/ : wiki pages :: the source résumé : generated bullets** — synthesis may
not invent beyond its source.

**Why ours is small:** in a codebase **git already IS a raw/ layer** — every
commit is an immutable, diffable, rebuildable snapshot *with* provenance (blame,
history). Git absorbs the raw/ role for everything tracked; an explicit `raw/`
only needs the knowledge git *can't* see (external papers, point-in-time
rationale, transcripts). **Constraint:** raw/ earns its place ONLY for
immutable, externally-sourced, otherwise-homeless knowledge — copying a live
git-tracked doc into raw/ is pure duplication + rot. "Small" isn't a compromise,
it's exactly-sized; it could even **start at zero** and grow only when a
genuinely-homeless source appears.

### raw/ as the *constitutional* layer + vision-alignment auditing (2026-06-07)
The sharper definition of `raw/` from discussion: not "external homeless
knowledge" but the **prescriptive north-star sources everything downstream must
stay consistent with** — vision, product direction, the 10 Principles, durable
design rationale. These *prescribe* the project (upstream of the code);
README/architecture *describe* it (downstream). On the source-vs-derived axis,
**vision is the *most* raw thing in the repo — more raw than README**, because
the code is derived from the vision, not the reverse.
- **Qualifying trait = prescriptive/constitutional, NOT "low-churn."** Rarity of
  change is a *consequence* of being foundational, not the test. The test:
  *does it govern the others, or describe them?* Govern → constitutional;
  describe → living/synthesized. (Don't mis-sort a stable-but-descriptive doc.)
- **Friction must be mechanized.** A folder makes no friction. This repo's idiom
  is gates (`block-merge-to-main`, `CLAUDE_ALLOW_MAIN_EDITS`, `PROMPT_VERSION`
  must-bump). A constitutional edit deserves the same teeth — the "specialized
  intervention" should be a real guard. (= design item **D-friction**.)
- **Payoff — vision-alignment auditing (user: "yes!").** Lint/audit can then
  check drift of the *descriptive* layer (code, architecture, synthesized wiki)
  *away from* the *constitutional* layer — "does what we built still match what
  we said we'd build?" The product's own grounding contract, turned on itself.

---

## WS-4 — Integration & Migration design (NOT yet executed — captured 2026-06-07)

> Agreed: **we want to integrate this**, but it needs deliberate design +
> decisions first. The *migration* (moving files) is expected to be
> mechanically easy; the **prescriptive/descriptive classification is the hard,
> important part**. This section captures what/why/how so a future session
> resumes cleanly.

### What
Adopt the LLM-wiki knowledge architecture in-repo: a committed `docs/wiki/`
(codebase variant, git-as-engine) + a root `llms.txt` + a small **constitutional
`raw/`** (or registered constitutional sources) + `ingest/query/lint/audit` ops
as Claude Code skills, and migrate the existing documentation set into the model
(constitutional / living-descriptive / synthesized / frozen-reference).

### Why
- Context-management *now* (read a small curated wiki, not 19k lines) and the
  **post-v1.1.0 Q&A assistant** later.
- **Convergence:** the v1.0.6 **6.5 education sweep** authors *into* the wiki
  instead of throwaway prose → the assistant comes nearly free.
- **Vision-alignment auditing** becomes possible once the prescriptive layer is
  first-class.
- Verifiable, low-hallucination answers via `path:line` / `doc#anchor` citations
  — same grounding ethos the product enforces on résumé text.

### How (design, then build)
1. **Settle the design forks** (classification + D2–D6 + D-friction +
   move-vs-register) — see "Open migration questions."
2. **Bootstrap** `docs/wiki/` skeleton + `SCHEMA.md` (references AGENTS.md /
   CLAUDE.md / vision as the contract; doesn't duplicate them).
3. **Adapt the `wiki-skills` ops** into `.claude-plugin/` skills (`/wiki-ingest`,
   `/wiki-query`, `/wiki-lint`, `/wiki-audit`) — reuse, don't reinvent.
4. **Cold ingest** the code architecture, module-by-module, `path:line`-grounded
   → proves the machinery + helps the agent now.
5. **Classify + migrate** the existing docs per the agreed model (below).
6. **Wire maintenance:** ingest at branch close-out + a commit-time freshness
   reminder hook + a pre-release `wiki-lint` gate in RELEASE_CHECKLIST.
7. **Reserve the user-facing wiki section** so Sprint 6.5 authors into it.
8. **Integrate THIS capture doc** into `docs/dev/` (the deferred home/shape call).

### Candidate doc classification — first pass (THE important design work)
Four roles; the hard cases are the **mixed** docs (⚠️ = blends prescriptive +
descriptive):
- **Constitutional / prescriptive** (→ raw/ or registered + friction-gated):
  `vision.md`; the 10 Principles (external → freeze in raw/); ⚠️ `PRODUCT_SHAPE.md`
  (direction = prescriptive, but mixes descriptive); ⚠️ the *rules* portions of
  `AGENTS.md` / `CONTRIBUTING.md` / `SECURITY.md`.
- **Descriptive / living** (→ stay living human docs; wiki *cites* + ingests):
  `README.md`, `docs/install.md`, `docs/architecture.md`, `docs/walkthrough*.md`,
  `docs/template_authoring.md`, `docs/dev/GROUNDING_METRIC.md`, and the code.
- **Synthesized** (→ generated wiki pages): module / flow / concept pages; the
  6.5 user-facing education content authors here.
- **Frozen reference / historical** (→ raw/ or left as records): `CHANGELOG.md`
  (a ledger — likely stays), `docs/dev/perf/*` benchmarks, `V1_0_5_VERIFICATION.md`,
  point-in-time `docs/ux/*` audits, `*_LICENSE.md`.

### Open migration questions (resolve before executing)
1. **The mixed-doc problem (the crux).** AGENTS.md, CONTRIBUTING.md, SECURITY.md,
   PRODUCT_SHAPE.md, RELEASE_ARC.md each blend prescriptive *rules* with
   descriptive *content*. **Split** (prescriptive core → constitutional; rest →
   living/synthesized) or **classify whole-doc by dominant character**? Splitting
   is conceptually cleaner but fragments docs people already know.
2. **Agent-contract status.** AGENTS.md/CLAUDE.md are prescriptive *and* the LLM's
   operating instructions *and* the de-facto schema. Constitutional source, the
   wiki SCHEMA, or both?
3. **Move vs. register** (vision/principles): relocate into raw/ (canonical,
   breaks links) vs. keep in place + register in SCHEMA.md + friction-gate there.
   *Lean: register-in-place.*
4. **Does the wiki replace or cite `architecture.md`?** Synthesized wiki as the
   new primary dev entry (architecture.md folded in), or both coexist?
5. **CHANGELOG** — confirm it stays a standalone ledger, not wiki material.
6. **D2** wiki location + committed (lean: `docs/wiki/`, committed).
7. **D3** ops trigger + token cost (lean: manual skills + reminder hook, no
   auto-ingest).
8. **D-friction** — the constitutional-edit guard mechanism (hook design).
9. **D6** ownership (lean: branch close-out + pre-release lint gate).
10. **Sequencing vs. release plan** — WS-4 runs parallel; substrate **before
    Sprint 6.5**; reconcile **WS-2** strict typing with the prior plan's **PV-4**
    type scan.

### Sequencing vs. the live release plan (recommendation 2026-06-07)
**Continue the sprint schedule to the v1.0.5 tag — do NOT pause.** This work
doesn't gate or threaten v1.0.5:
- The wiki's only deadline is **Sprint 6.5** (in v1.0.6), comfortably *after* the
  v1.0.5 tag. Runway = 6.1–6.4.
- The only pre-tag docs branch (`docs/tuning-loop-discoverability`) just edits
  *living* docs → cited later by the wiki, no retrofit. No conflict.
- **WS-1 (blueprints) is the ONLY real collision** — it rewrites `app.py`/routes
  that nearly every sprint branch touches. Keep it **parked** until the release
  churn settles; never interleave it mid-stream.
**Recommended order:** tag v1.0.5 → (WS-4 *design* forks can be form-found in
parallel now — free, no code) → build the wiki substrate in the
v1.0.5-tag → 6.5 window → cold-ingest code after 6.4 (most churn done) → 6.5
authors *into* the wiki.

---

## WS-4 — mixed-doc crux RESOLVED: extract a canonical Governance core (2026-06-07)

> The seven-functions language (Q1) dissolved the resume point: docs = mostly
> **Memory** (3 strata: living-source / synthesized-wiki / frozen-archive); the
> constitutional layer = **Governance**; the crux = separating Governance from the
> Memory it's embedded in. **User chose EXTRACTION** over register-in-place
> (overrides the migration-Q3 lean).

**Decision:** prescriptive/**Governance** content is **lifted into one canonical
home** and stated once; the mixed docs keep their descriptive (**Memory**) content +
a pointer to it.

- **What extracts into Governance:** the `vision.md` core; the 10 Principles
  (external → frozen here); and the hard RULES scattered across `AGENTS.md`
  (security gate, `PROMPT_VERSION`-bump, deterministic/LLM boundary, what-NOT-to-do,
  branch conventions), `CONTRIBUTING.md` (the ruff+mypy+pytest bar, commit/branch
  conventions), `SECURITY.md` (API-key rules, `_safe_username`/`_within` mandate,
  threat-model rules), `PRODUCT_SHAPE.md` (the prescriptive v1→v2 ladder + Corpus-
  Item rules), `RELEASE_ARC.md` (the "hard constraints, all phases" + "do not edit
  without sign-off").
- **Single source of constitutional truth (DRY-for-governance):** each rule stated
  ONCE in Governance; `AGENTS`/`CONTRIBUTING`/`SECURITY`/the hooks all *reference*
  it.
- **Mixed docs → thin descriptive shells + pointers:** keep Memory content
  (architecture-at-a-glance, process prose), link to Governance for the rules.
  Bounded link-update done in the same migration.
- **⚠ CRITICAL CONSTRAINT — `AGENTS.md`/`CLAUDE.md` are harness-auto-loaded** (the
  agent's operating instructions). Extraction MUST preserve agent access to the
  rules — via `@import` (CLAUDE.md already does `@AGENTS.md`) or an explicit
  canonical pointer — or every future agent loses its guardrails at session start.
  `AGENTS.md` stays the entry point; it *imports/links* Governance, doesn't restate.
- **Payoffs:** vision-alignment auditing reads ONE canonical constitution; the
  D-friction **Regulation** hook guards the Governance home directly (one clean
  target); "consistency tracks enforcement" (Q2) now applies to the vision itself.
- **Open sub-decisions (for integration/implementation — NOT blocking the walk):**
  (i) **Governance home name/location** — `raw/` (WS-4 continuity) vs a self-
  describing `docs/governance/` or root `GOVERNANCE.md` (+ principles frozen
  alongside). *Lean: name it for its function (`docs/governance/`), reconcile the
  old `raw/` label into it.* (ii) per-doc extraction boundaries (exact spans).
  (iii) `AGENTS.md` = critical-rules-inline-with-pointer vs pure-shell-import.
- **Propagated updates:** migration-Q3 → **MOVE/extract** (was lean: register);
  migration-Q2 → `AGENTS`/`CLAUDE` become **Operation** entry-points that
  *reference* Governance (no longer the Governance source); D5 `SCHEMA.md`
  references the Governance core. Other D-forks (D2 `docs/wiki/` committed · D3
  manual skills + reminder hook · D4 code-first/reserve 6.5 · D6 close-out +
  pre-release lint gate) confirmed.

**WS-4 design walk = COMPLETE.** What remains is implementation (the three open
sub-decisions above + the build sequence already captured), sequenced into the
release arc (substrate before Sprint 6.5).

---

## Log
- **2026-06-07** — Round-1 assessment done; direction set (strict typing,
  blueprints, keep-improving tests, polished-production target). Capture
  created in `output/_dev-notes/` (untracked).
- **2026-06-07** — Other agent merged `feat/run-eval-from-console` → `main`
  (clean tree); moved our work to branch `docs/excellence-walk`. Decided pace
  (one-at-a-time, live doc), the AI-assistant goal (yes, post-v1.1.0), and the
  starting topic (Q4). Read the prior sprint-plan artifact; mapped WS-1/WS-2
  against it. Started the Q4 thread (research + current-state read + fork). No
  code touched.
- **2026-06-07 (close)** — Worked WS-4 design: **full LLM-wiki now**; D1 =
  **git-as-engine** backbone; reframed `raw/` as the **constitutional layer**
  (prescriptive vision/principles, friction-gated) + confirmed **vision-alignment
  auditing**. Captured the **Integration & Migration design** (what/why/how) +
  first-pass doc classification + open migration questions. Next session: the
  prescriptive/descriptive classification + remaining D-forks. No code touched.
- **2026-06-07 (session 2)** — Finished the **five-question spine**: Q1 (layman
  architecture → seven-functions overview draft), Q3 (downloads, verified), Q2
  (consistency = "tracks enforcement"). Settled the **seven-functions descriptive
  language** (Substrate / Production / Evaluation / Operation / Memory / Regulation
  / Governance + the one-way law) via an ecology *discovery lens* (omitted as the
  frame). Resumed WS-4: the seven functions reframed the doc model; **mixed-doc
  crux RESOLVED — user chose EXTRACT a canonical Governance core** (over register-
  in-place); D-forks confirmed; **WS-4 design walk complete.** Artifacts:
  `Q1_overview_draft.md`, `Q2_consistency_draft.md`, `Q3_downloads_draft.md` in
  `output/_dev-notes/`. No code touched. **Step 2 done:** handoff written →
  `output/_dev-notes/NEXT_AGENT_HANDOFF.md`. Session work (plan steps 1–2)
  complete; branch `docs/excellence-walk` has no commits (all deliverables are the
  gitignored temp docs) — next agent branches off `main` fresh.
