---
status: review-artifact
evidence_sha: 4196d0c
graduation: none
---

# Area C findings — docs & wiki processes

> Surfaces: canonical-doc overlap (README / vision / PRODUCT_SHAPE /
> architecture), CHANGELOG + RELEASE_ARC + RELEASE_CHECKLIST volume, wiki
> ingest lag, DOC-STATUS convention, docs/dev staleness, ledger hygiene.
> Finders: C1 doc-overlap, C2 wiki-mech.
>
> Area summary (C1): the ledger open-count drift is real and precisely
> locatable; a worse instance of the stale-embedded-number pattern exists
> (PRODUCT_SHAPE's app.py claim is already false at HEAD, not merely aging);
> CHANGELOG's oldest 5 releases are a clean archive split.
> Area summary (C2): wiki is 119 commits + 337 non-wiki files behind the
> 2026-06-20 ingest; the freshness hook has been escalating on every commit;
> DOC-STATUS is defined but ungated; the wiki's own D-5 discipline is holding.

## F-doc-01 — PRODUCT_SHAPE.md states app.py is "6,290-LOC / 75-route" — false at HEAD (241 lines, ~0 routes)

- **Disposition:** FIX · **Leverage:** P1 · **Simplification:** no
- **Metric:** >25× discrepancy on a headline number in the v1.0→v2 ladder table, phrased as current state; app.py measured 241 lines / 2 route-decorator hits (factory scaffolding).
- **Evidence:** `docs/PRODUCT_SHAPE.md:720` (WS-1 row) vs `app.py` (wc -l = 241; the 8.3a-h seams moved all routes to blueprints/).
- **Dedup:** fresh stale-number instance; distinct from PX-10 (a different doc/number, already landed) and from the ledger-header drift (different file/mechanism).

## F-doc-02 — Carry-forward ledger header "Open count: 7" contradicts the 8 open items it governs

- **Disposition:** WATCH · **Leverage:** P2 · **Simplification:** no
- **Metric:** every handoff reader trusting the header undercounts by 1 against the ~8–10 reduction-sprint threshold that same header defines.
- **Evidence:** `docs/dev/RELEASE_CHECKLIST.md:490` (header says 7; its own narrative ends "7 → 8" at the 2026-07-02 PyPI item, line ~507) vs the 8 `- [ ]` bullets at lines 492,511,525,537,569,582,596,811.
- **Dedup:** flagged report-only by the review brief; it is ABOUT the ledger's header accuracy, not any tracked item's content. (Corrected as normal ledger maintenance at this review's close-out.)

## F-doc-03 — app-blueprints-design.md still banners "Status: APPROVED design" though all 8 seams shipped

- **Disposition:** FIX · **Leverage:** P2 · **Simplification:** YES
- **Metric:** 527-line design doc reads as prospective; a SUPERSEDED/SHIPPED banner + pointer to the as-built blueprints/ tree lets readers skip to code.
- **Evidence:** `docs/dev/app-blueprints-design.md:3` (no later status update) vs `docs/dev/RELEASE_CHECKLIST.md:93-97` (8.3a-h all shipped through 2026-06-22, "app.py → zero routes").
- **Dedup:** stale STATUS banners on completed design docs not addressed by ledger 1-8 or PX-01..36.

## F-doc-04 — CHANGELOG.md's 5 oldest releases (~585 of 4,087 lines) are write-only history — archive-split candidate

- **Disposition:** FIX · **Leverage:** P2 · **Simplification:** YES
- **Metric:** ~585 lines (14%) moveable to CHANGELOG-v1.0.x-archive.md; no programmatic reader of old sections found (one dev/perf pointer to [1.0.1] survives an archive move).
- **Evidence:** `CHANGELOG.md:3502-4087` ([1.0.3]…[0.1.0]); `docs/dev/perf/PERFORMANCE_HISTORY.md:311` (sole old-entry cross-reference).
- **Dedup:** CHANGELOG file structure not covered by ledger/PX items.

## F-doc-05 — Corpus/pipeline mechanics restated as full paragraphs in 3 of 4 top-level docs (README already disciplined)

- **Disposition:** FIX · **Leverage:** P2 · **Simplification:** YES
- **Metric:** 33 "corpus" occurrences across README/vision/PRODUCT_SHAPE (PRODUCT_SHAPE alone: 20); architecture.md is the natural canonical home for corpus data-flow + pipeline mechanics; README's pointer+one-line pattern (e.g. README.md:144) is the model.
- **Evidence:** `docs/PRODUCT_SHAPE.md:73` ("The unifying pattern — Corpus Item" full section) vs `README.md:37,75,87,100,132,143,144` (one-sentence + pointer style).
- **Dedup:** cross-doc structural duplication; distinct from PX-09 (claims phrasing) and PX-11 (funnel accuracy).

## F-doc-06 — kit-adoption-design.md (605 lines): initiative fully COMPLETE but no top-of-file closure banner

- **Disposition:** WATCH · **Leverage:** P3 · **Simplification:** YES
- **Metric:** completion signals only appear at lines 155 and 499; cold readers process 605 lines as if live.
- **Evidence:** `docs/dev/kit-adoption-design.md:155` ("Phase 1 is now COMPLETE"), `:499` (Phase 2 final rung COMPLETE).
- **Dedup:** ledger #7 tracks the remaining OPEN commitments, not the doc's own closure banner.

## F-doc-07 — Wiki stale: 119 commits + 337 non-wiki files behind; blueprint split (8.3a-h) unrecorded

- **Disposition:** FIX · **Leverage:** P1 · **Simplification:** no
- **Metric:** `git log 3561657..HEAD` = 119 commits; 337 non-wiki files changed; route-surface.md cites "93 @app.route decorators" vs actual 2 in app.py + 99 in blueprints (101 total).
- **Evidence:** `docs/wiki/.last_ingest_sha` (3561657…, 2026-06-20); `docs/wiki/pages/route-surface.md:13`; `docs/wiki/pages/code-module-map.md` (pre-split topology); `docs/dev/RELEASE_CHECKLIST.md:376-380` (post-split re-ingest acknowledged as deferred).
- **Dedup:** wiki-code cite staleness, known deferral not yet filed as PX or ledger row; distinct from ledger #6 (link checker).

## F-doc-08 — wiki-freshness-reminder escalates on every commit: 337 files vs its 10-file threshold

- **Disposition:** WATCH · **Leverage:** P2 · **Simplification:** no
- **Metric:** threshold=10 files; actual drift=337 → the nudge has escalated to /wiki-self-update wording on every commit for ~119 commits (alarm fatigue defeats the design's bounded-checkpoint intent).
- **Evidence:** `.claude-plugin/hooks/wiki-freshness-reminder.sh:57` (THRESHOLD=10); `git diff --name-only 3561657 HEAD | grep -v '^docs/wiki/' | wc -l` = 337; `docs/dev/RELEASE_CHECKLIST.md:75` (design intent).
- **Dedup:** the staleness is F-doc-07; this is the hook's noise behavior — separate concern, same root.

## F-doc-09 — DOC-STATUS convention defined, 16 markers placed, zero enforcement

- **Disposition:** FIX · **Leverage:** P2 · **Simplification:** YES
- **Metric:** 16 DOC-STATUS markers in tree; the proposed grep gate ("fail when a marker's trigger sprint has tagged") remains unbuilt.
- **Evidence:** `docs/dev/documentation-architecture.md:105-119` (convention + "Hook point (proposed)"), `:162` (scheduled as v1.0.9 CI merge-gate item #4); `git grep -c DOC-STATUS` = 16.
- **Dedup:** property gate on one convention — distinct from ledger #6 (cross-doc [text](path) link graph). Coordinate already exists in the v1.0.9 epic; prescription affirms/schedules rather than invents.

## F-doc-10 — D-5 cite-don't-restate discipline is HOLDING across the 337-file drift

- **Disposition:** KEEP · **Leverage:** P1 · **Simplification:** no
- **Metric:** 2026-06-16 self-documenting-loop run: 47 changed sources → 1 affected page — the discipline is why 119 commits of lag has not corrupted the wiki's contract layer.
- **Evidence:** `docs/wiki/log.md:322-331`; `docs/wiki/SCHEMA.md:33-48`; `docs/wiki/pages/deterministic-llm-boundary.md:18-24` (exemplar).
- **Dedup:** affirmation (protect through the catch-up ingest), complements F-doc-07.

## F-doc-11 — Symbol-keyed cites survive drift; bare line-number cites don't — enforce universally

- **Disposition:** BOOST · **Leverage:** P2 · **Simplification:** no
- **Metric:** the 2026-06-16 grounding audit caught 3 fragile bare-line cites on the single audited page; symbol cites (analyzer.py:SYSTEM_PROMPT) survived the 119-commit drift.
- **Evidence:** `docs/wiki/log.md:345-349`; `docs/wiki/SCHEMA.md:68-69` (convention already prefers symbols); `docs/wiki/pages/route-surface.md:29-50` (mixed usage).
- **Dedup:** cite-mechanism durability improvement, not the staleness of cited facts (F-doc-07).
