# Diagnosis — the wiki-freshness gate counts non-wiki-tracked churn as drift

> **Status:** root cause PROVEN (read the measurement code directly; confirmed by
> categorizing a real 79-file diff that tripped the gate).
> **Branch:** `fix/wiki-freshness-relevance-classification`

---

## Symptom

The merge-blocking wiki-freshness gate (`scripts/wiki_freshness.py`, `BLOCK_THRESHOLD = 75`)
tripped on `fix/extract-experiences-telemetry-pollution` (PR #96): "STALE — 79 file(s)
changed since the last ingest." That branch's own actual diff was 8 files, none of them
wiki-relevant (a test-only fix). The user asked why non-wiki-tracked documents (session
handoffs, provenance ledgers, work-item filings) would trip a *wiki* freshness gate at all,
suspecting the measurement itself, not the branch, was the defect.

---

## Observed

- Read `scripts/wiki_freshness.py:83-106` (`drift_count()`) in full: it computes
  `git diff --name-only <last_ingest_sha> HEAD`, excluding only lines starting with
  `docs/wiki/` or `docs-site/`. No other exclusion exists.
- Read `hooks/wiki-freshness-reminder.sh:48` (the non-blocking post-commit nudge): a
  SEPARATE, independently-maintained bash reimplementation of the same count
  (`git diff --name-only "$SHA" HEAD | grep -vE '^docs/wiki/' | grep -c .`) — this one
  doesn't even exclude `docs-site/`, an existing small inconsistency between the two
  implementations of "the same" measurement.
- Ran `git diff --name-status 65b0f88f5c2469484a3ed2ad8edbe28991f56df1 HEAD -- . ':!docs/wiki/' ':!docs/dev/reviews/'`
  against `fix/never-logged-call-kinds`'s merge commit (`c8eb74d`, the tip at the time):
  79 files, spanning 10 merged branches since the last real ingest. Categorized all 79
  by hand: **60+ are `docs/dev/{handoffs,ledger,work/items,diagnosis}/*` or `tests/`/
  `ui_pages/*`** — session handoffs, provenance-ledger JSONL rows, per-item work
  filings, evidence dossiers, and test files. None of these is ever cited by a
  `docs/wiki/pages/*.md` file (confirmed: the wiki's own module map in
  `docs/architecture.md` documents production modules only; a `Grep` across
  `docs/wiki/pages/` for these path shapes returns zero matches).
- Checked `docs/wiki/log.md` for prior occurrences of this exact shape: **two
  independent, prior instances** — `chore/wiki-refresh-v109` (2026-07-30, 75 files/5
  branches, cap raised 8→18, only 3/15 candidate pages actually needed edits) and
  `feat/context-structure-review-skill` (2026-07-24, 78 files, "initially-requested
  full cold pass... scoped down after flagging the cost/scope tradeoff... of the 78
  changed files, the large majority were non-wiki artifacts"). Both prior fixes were
  one-off manual triages, not a structural correction to the measurement itself — the
  same false-positive shape was therefore guaranteed to recur, and did (this branch is
  the third instance in under two weeks).
- Cross-checked the inverse risk before assuming a blanket directory exclusion is safe:
  `Grep`'d `docs/wiki/pages/` for `scripts/` and `docs/dev/perf/` citations. Found real,
  specific hits — `scripts/generate_openapi_spec.py` and
  `scripts/enforcement/guards/route_security_lint.py` (cited by `route-surface.md` /
  `openapi-api-reference.md`), and `docs/dev/perf/PERFORMANCE_HISTORY.md` (cited by
  `llm-call-catalog.md`). **These two directories are genuinely mixed** — mostly dev
  tooling / one-off investigation docs, but containing specific files a wiki page
  actually depends on. A naive blanket-prefix exclusion of `scripts/` or
  `docs/dev/perf/` would have silently hidden real future drift on exactly those files.

---

## Falsified

- **Hypothesis considered and rejected: "the branch itself was too large."** The
  branch that tripped the gate (`fix/extract-experiences-telemetry-pollution`) had an
   8-file diff of its own; the 79-file count is accumulated drift across 10 merged
  branches since the last real ingest, not this branch's size. Confirmed via
  `git log --merges 65b0f88..HEAD` (10 merge commits).
- **Hypothesis considered and rejected: "a full cold `/wiki-ingest` pass is the right
  fix."** Initially proposed as one option; rejected once `docs/wiki/log.md` surfaced
  that this exact tradeoff (full re-verify vs. targeted fix) was already flagged and
  reversed twice in this project's own history, for the same stated reason (the wiki
  already covers most of the codebase; a whole-repo re-verify is materially more
  expensive than the actual gap).

---

## Inferred

_(Nothing — the mechanism is directly observed above: a raw, unfiltered `git diff
--name-only` count with a 2-item exclusion list, no classification of what's actually
a wiki source.)_

---

## Falsification

Not an intermittent-bug scenario — the miscount is reproducible on demand: running
`python scripts/wiki_freshness.py` against any real multi-branch window shows the raw
count includes `docs/dev/handoffs/`, `docs/dev/ledger/`, `docs/dev/work/items/`,
`docs/dev/diagnosis/`, `tests/`, `ui_pages/` files that are never wiki-cited. Post-fix
acceptance: re-running the classification-filtered `drift_count()` against the exact
same 65b0f88→HEAD window must show only genuinely wiki-relevant files counted, and the
count must drop enough that `fix/extract-experiences-telemetry-pollution`'s own PR
gate (currently blocked at 79) passes once this fix merges to `main` and that PR is
re-evaluated, without any wiki content edits on that branch.

---

## The fix

A new `scripts/wiki_relevance.py` module — the single source of truth both
`wiki_freshness.py`'s `drift_count()` and `hooks/wiki-freshness-reminder.sh`'s nudge
now call into — classifies every changed path as wiki-relevant or not:

- `IRRELEVANT_PREFIXES` — directories that are wholesale, by-construction never a
  wiki source (`docs/dev/handoffs/`, `docs/dev/ledger/`, `docs/dev/diagnosis/`,
  `docs/dev/reviews/`, `docs/dev/prov/`, `docs/dev/work/items/`, `docs/screenshots/`,
  `docs/ux/`, `tests/`, `ui_pages/`, the Claude-Code-plugin/tooling directories,
  gitignored user-data directories).
- `IRRELEVANT_FILES` — specific always-irrelevant files that don't fall under a listed
  prefix (`docs/dev/work/BOARD.md`, `CHANGELOG.md`, `CHANGELOG-archive.md`,
  `docs/bundled_templates_LICENSE.md`).
- `MIXED_PREFIXES` (`scripts/`, `docs/dev/perf/`) — default irrelevant, **except** the
  specific files in `RELEVANT_OVERRIDES` that a wiki page genuinely cites
  (`scripts/generate_openapi_spec.py`,
  `scripts/enforcement/guards/route_security_lint.py`, `scripts/perf_baseline.py`,
  `scripts/export_corpus_seed.py`, `docs/dev/perf/PERFORMANCE_HISTORY.md`).
- Everything else defaults to relevant (production code, canonical docs, the
  excellence-walk source directory, user-facing content).
- An audit test (`tests/test_wiki_relevance_classification.py`) enumerates the CURRENT
  top-level repo entries + `docs/`'s + `docs/dev/`'s immediate children, and fails if
  any of them is not accounted for by the classification (new-and-unclassified) or if
  a classified prefix/file no longer exists (stale) — mirrors
  `tests/test_egress_allowlist.py`'s `offenders`/`stale` dual check, the only existing
  precedent in this repo for "maintained classification list that can't silently rot."

---

## Acceptance bar

- `test_wiki_relevance_classification.py` passes against the CURRENT repo tree.
- Re-running the (now-filtered) drift count against the `65b0f88 → HEAD` window shows
  a materially lower count than the raw 79, with only genuinely wiki-cited files
  contributing.
- `tests/test_wiki_freshness_gate.py`'s existing unit tests (threshold behavior,
  `docs/wiki/`/`docs-site/` exclusion) still pass unmodified — this is an additive
  filter, not a rewrite of the threshold logic.
- Full `python -m scripts.gate` green.
