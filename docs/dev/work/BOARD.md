# Work-item board

Generated from `docs/dev/work/items/` by `scripts/work_items.py` -- never hand-edited. Regenerate with `python -m scripts.work_items board --write`.

**Open 9 / 10 ceiling** | Blocked 4 | Deferred 2 | Watching 3 | Epics 0 | Closed 1

## Open

- **6** -- PX-39 real-corpus Sonnet-5 baseline (`agent`) -- Measure real-corpus Sonnet-5 latency/cost - 72 non-eval records already exist in E2E telemetry, zero new spend.
- **9** -- release/visual-assets refresh - stale screenshots (`agent`) -- 10 committed PNGs were ~7.5 weeks stale as of 2026-07-21 (predate the diagnostics redesign); README hero never wired in.
- **11** -- Bootstrap run overwrites prior annotation work with no merge or versioning (`agent`) -- Every /api/annotation/bootstrap call overwrites bootstrap.json wholesale - no merge, no versioning, no history.
- **12** -- Judge JSON-parse failure silently scores as 0, indistinguishable from a real failing grade (`agent`) -- _grade coerces a judge parse failure into score=0 instead of null/error - a crash reads as 'worst possible quality'.
- **13** -- Collate picks an anchor jd.txt that doesn't match its own fixture's annotations (`agent`) -- Fixture's jd.txt (Zoox) has zero overlap with annotations.json's 32 bullets (100% Faros) - eval graded the wrong target. [depends on: 11]
- **14** -- No JD-identifying metadata anywhere in bootstrap/eval artifacts (`agent`) -- Eval result records only fixture/fixture_hash, no JD name - had to open jd.txt prose to learn what a run graded. [depends on: 11]
- **15** -- Suggested skills split mid-parenthetical into separate entries (`agent`) -- e.g. 'Eval Framework Design (LLM-as-judge' and 'rubric-based)' saved as two separate skill entries - a comma-split bug.
- **17** -- PERFORMANCE_HISTORY.md and RELEASE_ARC.md contradict on eval-vs-live traffic source (`agent`) -- PERFORMANCE_HISTORY asks for non-eval:* runs; RELEASE_ARC step 12 prescribes the harness, which DOES carry that prefix. [depends on: 6]
- **19** -- UX-suite flakiness solution sprint - mode-C residual + newly observed instances (`agent`) -- Scheduled sprint: mode-C's own-flagged ~17% residual, plus 3 newly observed single-sample UX flakes from 2026-07-28.

## Blocked

- **3** -- [HUMAN] GitHub toggles: repo rename, PyPI Trusted Publisher, GHCR visibility, enforce_admins (`user`) -- Repo rename to take-tempo-public/sartor gates PyPI Trusted Publisher + GHCR visibility; enforce_admins still false. [blocked on: owner-only GitHub settings actions, no repo file changes; enforce_admins is a standing open decision]
- **5** -- Grounding-score persistence gap blocks calibrated L1/L2 metric layers (`agent`) -- First diagnosed 2026-07-09 on robert-bootstrap; independently re-found 2026-07-28 on the SAME fixture, still unfixed. [blocked on: the annotate-flow scorer never writes NLI/MiniCheck scores back into the fixture's annotations.json]
- **8** -- Compose-time rewrite latitude - the 'generate but don't invent' dial (`user`) -- Design doc landed (COMPOSE_REWRITE_DIAL.md); nothing built yet - read it before touching refinement/grounding code. [depends on: 6] [blocked on: evidence-gated on the PX-39 real-corpus run producing a comparison; owner has now excluded the Microsoft JD from that run]
- **10** -- chore/release-v1.1.0 - version bump, CHANGELOG cut, tag (`user`) -- Bump pyproject.toml to 1.1.0, cut CHANGELOG [Unreleased] to [1.1.0], tag - last step, on the owner's go. [depends on: 3, 6, 7, 9] [blocked on: everything else landing first, plus the owner's explicit go]

## Deferred

- **4** -- In-app rendered citation viewer (`user`) -- Avatar citations link out to GitHub; an in-app viewer needs a new route + sanitizer, deliberately not built yet. [blocked on: no friction signal yet; owner reaffirmed 2026-07-23, build only if friction warrants]
- **7** -- PX-46 selective memory consolidation (`user`) -- Selective, not wholesale, memory consolidation - present the list, act only after explicit approval. [blocked on: owner sign-off on the keep/consolidate/delete list required first - judged irreversible if botched]

## Watching

- **2** -- Wordmark sweep owed on docs/wiki/ and docs/dev/reviews/ (`agent`) -- ~107-file wiki + reviews-archive wordmark cleanup deliberately deferred to opportunistic fold-in, not a branch.
- **16** -- evals/runner.py --suite real is non-functional - no fixtures exist (`user`) -- No jd.txt/expected.json under evals/fixtures/real/ anywhere in this project - --suite real exits 1, zero LLM spend.
- **18** -- Large judge-score variance between back-to-back runs of the same fixture (`agent`) -- Same fixture, 68s apart: tone 3.2->2.1, clarification_quality 3.2->3.8, composite 4.06->3.89 - n=2, uncharacterized.

## Epics

None.

## Closed (1)

- 1 -- Quality gate unrunnable by an agent in one shot (2026-07-28, chore/work-item-tracking: root cause found (real ~30min runtime, no mystery kill); -n auto lands for the non-UX tier in scripts/gate.py, cutting it substantially; UX-tier flakiness confirmed as this project's pre-existing, CI-accepted (--reruns 2) characteristic, not a new problem, and deliberately left un-parallelized.)
