```toml
schema = 1
id = 177
kind = "item"
title = "Repo defects and gaps found while sweeping memory for item 7"
status = "open"
decision_owner = "agent"
refs = [
  "scripts/gate.py:39",
  "evals/README.md:97",
  "hardening.py:1992",
  "docs/dev/work/items/0025-apprun-threaded-governance-decision.md",
  "docs/dev/work/items/0174-model-pricing-disagrees-with-pricing-page.md:80",
  "tests/test_wiki_relevance_classification.py:248",
  "tests/conftest.py:234",
  "AGENTS.md:44",
]
summary = "Sweep found a threaded-server contradiction, a wrong gate.py item path, README min_* claims and stale counts."
```

Found by item 7's sweep and adversarial read (2026-10-18). **Each is an agent observation from reading code and running a
read-only command; none is fixed, and the first one needs a C-7 instrument before any change.** Split into branches as
you work them.

1. **Is the production server threaded? The repo says no; the installed Flask says yes.** `hardening.py:1992-1993` says
   `app.run(...)` has no `threaded=True` and "Werkzeug defaults to `threaded=False`", and item 25's premise ("single-threaded
   `app.run()` freezes the app during a diagnostics run") rests on it. On 2026-10-18 `inspect.getsource(flask.app.Flask.run)`
   on the installed Flask 3.1.3 contains `options.setdefault("threaded", True)`, and `app.py:494` calls
   `app.run(host=..., debug=..., port=...)` with no `threaded` argument. `docs/dev/diagnosis/context-write-lost-update-gap.md`
   (Observed 8 to 9) records the single-threaded behaviour as observed. **Both cannot be right. Reproduce first** (start the app,
   issue two overlapping requests, one of them slow, and record the result); then correct whichever of the docstring, item 25
   and the dossier is wrong. Not verified here beyond reading Flask's source.
2. `scripts/gate.py:39-40` cites `docs/dev/work/items/0108-gate-memory-preflight-refusal.md`; the file is
   `0108-gate-preflight-resource-check.md`.
3. `evals/README.md:97` and `:153` describe per-fixture `min_*_score` thresholds; `evals/runner.py` has no `min_` use, so the
   README describes a mechanism the runner does not implement. Either implement it or correct the README. Tracked nowhere else.
4. `docs/dev/work/items/0174-model-pricing-disagrees-with-pricing-page.md:80` still says `hardening.py` is a C-10 gated
   surface; it is not (`scripts/enforcement/blast_radius.py` lists it as acknowledged-not-gated). Item 173's record repeats the
   claim. `docs/dev/diagnosis/model-pricing-rates.md:65` already corrects it.
5. `tests/test_wiki_relevance_classification.py:248` says "13 of" the cited files were missing; `docs/dev/diagnosis/wiki-relevance-cited-scripts.md:55`
   measured 20 missing and 2 stale.
6. `tests/conftest.py:234` (docstring of the `app` fixture) says a factory-built app carries the assistant and dashboard
   blueprints but not the 93 module-level routes; `app.py` has no module-level routes now and registers ten blueprints
   (`app.py:52-84`).
7. `AGENTS.md:44` says the five load-bearing principles are frozen in `docs/governance/charter.md` ("The 10 Principles
   backbone"); `git grep -i "Principles backbone" docs/governance` finds nothing, and the section is at `vision.md:205`.
8. Tracked files still name the e2e instance directory (`docs/dev/RELEASE_ARC.md:1351`, `docs/dev/RELEASE_CHECKLIST.md:718`,
   `:2623`, `:2633`, `docs/dev/handoffs/chore-scrub-local-eval-paths.md:85`). These are history records describing the scrub that
   removed live references, so whether they break the owner's rule that nothing committed may reference it is the owner's call.
9. A C-11 guardrail is owed for the Workflow tool relaying the last user prompt as the triggering prompt (recorded in
   memory as "guardrail owed"); no work item exists for it.
10. `static/app.js:2581` says tab-level help is "a later branch"; the owner's decision recorded in memory is that
    only panel-level help icons were chosen. One of them is out of date; ask the owner.
11. `docs/dev/AGENT_HANDOFF_TEMPLATE.md:228` names `feedback_hook_discipline`, and `CLAUDE.local.md:30` points at
    `feedback-interrogative-is-not-a-work-order.md` by path. Both are memory files outside the repo. If either file is ever
    deleted or renamed, these pointers dangle.

## Updates

### 2026-10-18 - filed during `chore/memory-consolidation` (item 7)

Nothing is fixed here. Item 1 is the one with potential product impact (it bears on the lost-update lock's stated
rationale and on item 25); the rest are one-line corrections.
