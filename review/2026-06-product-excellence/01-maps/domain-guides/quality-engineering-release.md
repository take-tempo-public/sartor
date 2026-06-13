---
status: review-artifact
evidence_sha: c6e0437
graduation: none (rubric portions are v1.0.7 governance candidates)
---

# Domain guide — Quality engineering & release discipline

> Lens, not survey. Anchored to the SIGNED charter
> (`00-interview/product-charter.md`); a gap matters only if it blocks a
> charter clause. C-0 discipline applies to this guide too: mechanisms and
> effort language, no absolutes about LLM behavior.

## 1. What mastery means here

For callback., "quality engineering" is not coverage theater — it is the set of
**machine-run gates that keep the project's claims honest without taxing the
owner's life** (E-1: "machine-run measures preferred — they keep themselves
honest"; D-4: no recurring human-labor promises). Mastery is three things:

- **Every categorical claim has a deterministic enforcer** (C-0): the no-egress
  promise (C-2), the deterministic↔LLM boundary (C-6), and the ATS-safe template
  properties (C-5) are exactly the claims a test can hold by construction. Where
  no test can hold a claim, the charter forbids the absolute — so the gate
  inventory *is* the claims-discipline inventory.
- **The right external badges, none of the cargo-cult ones** (E-2): the agreed
  set is lockfile+Dependabot, OpenSSF Scorecard, REUSE, the network-egress
  falsifiability test, and one-time Private Vulnerability Reporting (PVR). Round2
  brief Part C is explicit that coverage-% badges, SLSA, and "ATS-score" checkers
  are theater here and are correctly deferred or skipped.
- **The machinery is exercised on real data before the tag** (T-D, M-2): the
  admitted gap is that the pipeline + tuning loop have been measured on synthetic
  fixtures, not a real corpus. A v1.1.0 release pass closes that, under D-4 (no
  human SLAs) — gates do the standing work; the human pass is one-time.

Generic best practice (SHA-pinned actions, lockfiles, Scorecard) is welcome, but
the charter outranks it: a badge is worth pursuing only where it enforces a stated
claim. Solo bus-factor means **continuous machine enforcement beats any recurring
manual promise** every time.

## 2. Current state pointers

**Strengths — name them.**
- CI runs ruff + mypy + pytest across **py3.11/3.12/3.13** matrix
  (`.github/workflows/ci.yml:13-42`); `permissions: contents: read` is already
  least-privilege (`ci.yml:9-10`).
- **Deterministic-boundary (C-6) modules are genuinely tested**: `test_pdf_render`,
  `test_parser`, `test_scraper` (network stubbed — `tests/test_scraper.py:53`),
  `test_json_resume`, `test_ats_roundtrip`, `test_corpus_to_json_resume`. The ATS
  round-trip (C-5) and bundled-template count (`test_bundled_templates.py`) are
  pinned.
- **Migrations are exercised forward**: `init_db()` runs the real alembic
  `upgrade head` chain (`db/session.py:108-141`, 7 versions), and
  `test_db_session.py:54` (`test_creates_all_tables`) asserts the head schema (27
  tables) through that path — not `create_all`.
- A rich, provenance-traced **perf baseline** exists: `docs/dev/perf/` carries p50
  latency + cost per `prompt_version` sourced to `logs/llm_calls.jsonl` (1,824
  calls), with an eval gate that blocks any rubric drop > 0.5
  (`PERFORMANCE_HISTORY.md` §"How we measure").

**Gaps — all charter-traced.**
- **The UX/a11y/slow tier never runs in CI.** `ci.yml` has no
  `playwright install chromium` step, so `pytest -m ux` (which carries the axe
  a11y gate *and* the only PDF/paged.js end-to-end coverage) silently skips on CI
  and runs only on the maintainer's machine (round2 Part C, L52). This blocks E-2
  ("machine-checked taxonomy in CI, free forever").
- **None of the E-2 machine badges exist yet**: no lockfile/requirements pin, no
  `.github/dependabot.yml`, no Scorecard workflow, no REUSE config / `LICENSES/`
  dir, no committed egress test (all absent at c6e0437). The vendored
  `axe.min.js` (MPL-2.0, not MIT) is the concrete thing REUSE would force declared.
- **D-4 violation still shipped**: `SECURITY.md:134` promises "respond within 5
  business days … fix within 30 days" — a hard human SLA D-4 requires softened to
  best-effort.
- **No perf-regression gate** despite excellent baselines; and the two-pass split
  is **synthetic-only measured** (`PERFORMANCE_HISTORY.md` §Caveats) — the T-D gap
  in numeric form.

## 3. Rubric

- **BOOST** — a committed network-egress falsifiability test (socket/route
  allowlist: configured-provider + opt-in scrape only) that makes C-2
  machine-checkable; CI job that installs Chromium so the a11y/PDF tier becomes a
  required check; a migration test that asserts a *data-bearing* upgrade (e.g.
  0005 template curation) transforms rows, not just reaches head.
- **KEEP** — the py3.11–3.13 matrix; deterministic-module test set; the
  eval-gate-blocks-quality-regression discipline; perf provenance to
  `logs/llm_calls.jsonl`; least-privilege CI permissions.
- **FIX** — wire `pytest -m ux` into CI (Chromium install); add lockfile +
  Dependabot + Scorecard + REUSE + PVR (the E-2 set); soften `SECURITY.md:134`
  SLA to best-effort (D-4).
- **DEBUFF** — any badge with no enforcement behind it (coverage-% vanity,
  SLSA before artifacts ship, "ATS-score" checkers); gaming Scorecard's
  Code-Review heuristic on a solo repo instead of documenting bus-factor=1.
- **WATCH** — green-CI-but-real-data-untested (T-D): the suite is LLM-stubbed, so
  it cannot catch a regression that only manifests on a real corpus
  (PDF render at robert-scale, parser determinism on real docx, prompt drift). A
  release-pass on a real corpus is the only thing that closes this.

## 4. Sharpest questions

(Question bank entries — decidable, charter-traced.)

1. **Does any required CI check exercise the PDF-render / paged.js / a11y paths,
   or do they only run on the maintainer's laptop?** If `pytest -m ux` skips in
   CI, the regression cliffs the LLM-stubbed unit suite cannot catch (PDF, axe
   contrast/name, reflow) are unguarded on every PR.
2. **Which of the agreed E-2 machine gates — lockfile+Dependabot, Scorecard,
   REUSE, egress test, PVR — are committed at the candidate tag, and which claim
   does each enforce?** A gate present but enforcing nothing is cargo-cult; a
   claim (C-2 egress, vendored-license honesty) with no gate is an unenforced
   absolute (C-0 violation).
3. **Is C-2 (no egress beyond the two sanctioned classes) machine-falsifiable, or
   asserted in prose only?** The charter calls C-2 "machine-verifiable"; today the
   only network test stubs `requests.get` (`test_scraper.py:53`) — that proves the
   scraper's shape, not that nothing *else* opens a socket.
4. **Is there a perf-regression gate, or only a perf narrative?** `docs/dev/perf/`
   has strong baselines but no automated guard; the cheapest credible gate (anchor
   suite p50/cost vs a committed floor, off the existing telemetry) would catch a
   silent cache break — the exact `.2→.3` regression the team caught by hand.
5. **What does the v1.1.0 release pass look like under D-4, and does it close
   T-D?** M-2 names the criteria (≥10 real apps, tuning loop exercised, first-run
   bars); the question is whether the pass is one-time machine+human evidence (D-4
   compliant) or smuggles in a recurring human SLA.
6. **Do the deterministic-boundary tests prove C-6 by construction, or only by
   convention?** The modules are tested for behavior; is there a gate that fails
   if an LLM import appears in `hardening/parser/generator/scraper/pdf_render/
   json_resume/corpus_to_json_resume` — the boundary the charter calls inviolable?
