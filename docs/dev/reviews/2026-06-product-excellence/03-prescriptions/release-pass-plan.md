---
status: review-artifact
evidence_sha: c6e0437
graduation: docs/dev/RELEASE_CHECKLIST.md additions (v1.0.7)
---

# Release-pass plan — gates that make the charter machine-true

> What gets verified before each tag (v1.0.6 → v1.1.0) and the enforcement
> infrastructure that converts charter prose into machine-kept fact.
> Severity anchor: the SIGNED Product Charter; evidence pinned at `c6e0437`.
> Findings are cited by F-id (see `02-assessment/findings-register.md`);
> WEAKENED findings use their revised claim from the verification log.
> Honors C-0 (no absolutes about LLM behavior; mechanism/effort language)
> and D-4/P-3 (machine-enforced gates over human-promise SLAs — no recurring
> human-labor obligation is proposed as a hard commitment).

## 1. The shape of a release pass

sartor. uses an **epic-per-patch-digit** model: v1.0.6 / v1.0.7 / v1.0.8
are internal epics; **v1.1.0 is the owner-owned public tag**. A "release
pass" here is not a manual audit — under E-1/D-4 the standing work is done
by gates that keep themselves honest; the human pass is **one-time, scoped
to a tag**. Mastery (QE guide §1) is that *every categorical charter claim
has a deterministic enforcer*: C-2 egress, the C-6 boundary, and C-5
template properties are exactly the claims a test holds by construction —
the gate inventory **is** the claims-discipline inventory. Where no test can
hold a claim, the charter forbids the absolute.

Two ordering rules govern the passes:

1. **Land the fix and the gate that would have caught it in the same epic.**
   The v1.0.6 CDN fix (PX-01) ships with the egress test (F-qe-rel-02) that
   makes the no-CDN promise falsifiable — otherwise C-2 returns to
   prose-only the moment a future asset reaches for a CDN.
2. **A gate is required only once it is green on the maintainer machine and
   in unattended CI.** Required-check status is the difference between
   "runs on the laptop" (the F-qe-rel-01 gap) and "machine-true."

## 2. The two P0 gates (v1.0.6–v1.0.7)

### G-1 · CI Chromium job + `pytest -m ux` as a required check (F-qe-rel-01, P0)

- **Enforces:** E-2's "machine-checked taxonomy in CI, free forever" — the
  axe a11y gate, the PDF/paged.js end-to-end path (C-5 ATS-safe output), and
  the keyboard/focus/live-region taxonomy that today run only on the
  maintainer's laptop. At the pin `ci.yml` has no `playwright install`, so
  `pytest -m ux` is collected-then-skipped and silently green (F-qe-rel-01,
  F-expa11y-01, both CONFIRMED).
- **Where it lives:** a new `ux` job in `.github/workflows/ci.yml` —
  `python -m playwright install --with-deps chromium`, then `pytest -m ux`,
  on the same `[dev]` extras. Keep it **separate from the py3.11–3.13
  `quality` matrix** so the fast gate is not slowed; mark it a **required
  status check** on branch protection.
- **Effort:** small (one CI job + branch-protection toggle). The suite
  already exists and is redesign-resilient (`ui_pages/` registry); this only
  removes the silent skip.
- **Gates a tag:** **yes — required check for v1.1.0**, wired in v1.0.7 so it
  is proven across real PRs before the public cut. (D-6 sanctions Chromium as
  a per-system/CI install, so the gap is a CI omission, not a charter conflict.)

### G-2 · Network-egress falsifiability test (F-qe-rel-02, P0; F-sec-01)

- **Enforces:** C-2 — that nothing opens a socket outside the **two**
  sanctioned classes (the configured LLM provider; the opt-in profile/website
  scrape). C-2's text calls itself "machine-verifiable" because the
  destination set is enumerable, but at the pin that was a one-time hand
  audit, not a committed gate; the only network test stubs `requests.get`
  (F-qe-rel-02, F-sec-01, both CONFIRMED). This test would have caught the
  PX-01 CDN fetch by construction.
- **Where it lives:** `tests/test_egress_allowlist.py` using `pytest-socket`
  (`disable_socket` + an `allow_hosts` fixture scoped to the configured
  provider host and the scrape path), plus a static assertion that no template
  references an off-box CDN host. New dep `pytest-socket` → `[dev]` extras +
  a `CHANGELOG.md` entry (D-1 mechanics). Runs in the fast `quality` job.
- **Effort:** small-medium (allowlist design + the template-host assertion).
- **Gates a tag:** **yes — v1.0.7** (charter-traced "v1.0.7 hardening"). It is
  the standing guarantor behind PX-01: once committed, C-2 stays honest after
  vendoring without a recurring human re-audit (D-4-clean).

## 3. The E-2 machine-badge set (v1.0.7 → v1.1.0)

None of the agreed E-2 machine gates exist at the pin (F-qe-rel-03,
F-sec-09, both CONFIRMED). Each below is **machine-run** (D-4-exempt — it
does not tax the owner's life); the one human item (PVR) is **one-time
setup, not a recurring SLA**. Per the QE guide §3 DEBUFF, coverage-% / SLSA /
"ATS-score" vanity badges are explicitly *out* — a badge earns its place
only where it enforces a stated claim.

| Gate | Enforces | Where it lives | Effort | Tag |
|---|---|---|---|---|
| **Lockfile + Dependabot** | E-2 reproducibility + supply-chain freshness | committed lockfile + `.github/dependabot.yml` (pip + actions) | small | v1.1.0 |
| **OpenSSF Scorecard** | E-2 supply-chain posture (surfaces the least-privilege `permissions: contents: read` already in `ci.yml`) | `.github/workflows/scorecard.yml` (read-only, scheduled); README badge | small | v1.1.0 |
| **REUSE / SPDX** | E-2 + D-5 license honesty — machine-declares vendored **axe-core MPL-2.0** + Chart.js alongside the MIT core (F-sec-08; axe today prose-only) | `REUSE.toml` + `LICENSES/` + SPDX headers; `reuse lint` in `quality` | small-med | v1.1.0 |
| **PVR** | E-2 one-time disclosure channel; pairs with the F-sec-11 wrong-repo fix so reports reach `amodal1/sartor` | GitHub repo setting + SECURITY.md pointer; **one-time, no SLA** (D-4) | trivial | v1.1.0 |

Sequencing note: REUSE should land in the **same pass that vendors Chart.js
(PX-01, v1.0.6)** so both vendored assets' licenses are declared together
(per `early-prescriptions.md` PX-06); the machine-readable `reuse lint`
**gate** can follow in v1.0.7/v1.1.0 once the headers exist. A standing
**PRIVACY.md** is the natural companion to G-2 (E-2 pairs the egress test
with one) — author it in v1.0.7 hardening.

## 4. The C-6 import-boundary gate (v1.0.8)

### G-3 · Deterministic↔LLM boundary, enforced by construction (F-arch-01 / F-qe-rel-04)

- **Enforces:** C-6 — the seven deterministic modules (`hardening.py`,
  `parser.py`, `generator.py`, `scraper.py`, `json_resume.py`,
  `corpus_to_json_resume.py`, `pdf_render.py`) make **no** LLM calls;
  `analyzer.py` is the sole caller. At the pin the boundary holds *by
  behavior* (AST: all seven clean — F-arch-04, KEEP) but **no gate fails on
  a regression** (F-arch-01, F-qe-rel-04, both CONFIRMED). C-0 names module
  boundary as a by-construction-enforceable category, so C-6's "Inviolable"
  is today a categorical without its prescribed backing.
- **Where it lives:** two cheap options, pick one — (a) an **import-linter**
  contract in `pyproject.toml` (a `forbidden` contract: the seven modules
  may not import `analyzer`/`anthropic`) run as a step in the `quality` job;
  or (b) a **~15-line AST test** (`tests/test_llm_boundary.py`) that parses
  each module and asserts zero `analyzer`/`anthropic` imports. Option (b)
  adds no dependency; option (a) is more declarative but adds `import-linter`
  (→ `[dev]` + CHANGELOG per D-1). A ruff `TID`/banned-API rule is a third,
  lighter variant (the existing `[tool.ruff.lint] select` makes it a one-line
  add) but is per-file rather than contract-shaped.
- **Effort:** small.
- **Gates a tag:** **yes — v1.0.8** (the blueprint-split epic, WS-1). It must
  land *with* the split: F-arch-03 (WEAKENED → P2/P3) and F-sec-05's WATCH
  rider both warn that the monolith→blueprint refactor is exactly when
  filesystem-touching routes migrate and convention-only coverage silently
  drifts. Pair with extending `route-security-lint` beyond its `app.py` +
  `@app.route` matcher (F-arch-03 action (i)) so the guard pair is enforced on
  blueprint route files too.

## 5. Proposed new hooks / CI steps (build-time, machine-enforced)

These are PreToolUse hooks (build-time) or CI steps; all are machine-run, so
D-4-exempt. They close convention-only governance seams flagged in the
register.

- **`block-merge-to-main` — close the common-path hole (F-gov-01, P1, CONFIRMED).**
  Today the routine feature-merge form *passes unblocked*; only the reverse
  direction/push blocks. Add a `git rev-parse --abbrev-ref HEAD == main`
  check (worktree-local per F-gov-02) so the dominant merge direction is
  actually guarded. Lives in `.claude-plugin/hooks/block-merge-to-main.sh`.
  Effort: trivial. **Witness/blocker, not a tag gate** — governance hygiene
  (v1.0.7 governance extraction).
- **Egress + boundary as required CI steps.** G-2 and G-3 above run inside
  the existing fast `quality` job (no new workflow); only G-1 (Chromium)
  warrants a separate job. This keeps the py3.11–3.13 matrix fast while making
  three charter claims (C-2, C-6, C-5-via-PDF) machine-checked.
- **`route-security-lint` matcher extension (F-arch-03, WEAKENED → P2/P3).**
  Extend the hook's file matcher beyond `app.py`+`@app.route` to blueprint
  files when they land in v1.0.8; scope `SECURITY.md:211` to app.py-resident
  routes (the one-line tightening the verification log specifies). Not a tag
  gate; lands *with* the blueprint split so coverage never goes dark.
- **`check-plan-approved` DEBUFF (F-gov-07, P2).** Remove the hand-create-the-
  marker hint that contradicts the never-hand-create rule. Trivial; v1.0.7.

## 6. D-4 posture — what is deliberately NOT a gate

Per D-4/P-3 and the QE guide DEBUFF row, the review proposes **no** recurring
human-labor obligation as a hard commitment:

- The two shipped human SLAs (`SECURITY.md:134-135`, `CODE_OF_CONDUCT.md:15`)
  are **softened to best-effort wording**, not re-armed as gates (F-qe-rel-08,
  F-sec-07, both CONFIRMED; `early-prescriptions.md` PX-07, v1.0.6).
- The pre-public **NVDA walkthrough** (E-2) and the **M-2 real-corpus pass**
  (≥10 real applications; F-eval-02, F-qe-rel-07 WEAKENED) are **one-time,
  tag-scoped human evidence**, not standing audits. The standing work — axe
  taxonomy (G-1), egress (G-2), eval-quality regression (F-qe-rel-05, KEEP:
  `REGRESSION_DELTA=0.5` → exit 2 already blocks eval-smoke) — is all machine-run.
- No conformance claim, no recurring manual-audit promise, no response-time
  SLA enters any public doc or tag criterion.

## 7. Tag-by-tag verification summary

- **v1.0.6** — PX-01 Chart.js vendor + PX-06 REUSE/axe-license note (assets
  declared together); PX-02 scrape re-wire; PX-03 two-class egress-doc
  alignment; PX-05 wrong-repo disclosure fix; PX-07 SLA softening. *Gate added:*
  begin G-2's allowlist (the test that keeps PX-01 honest).
- **v1.0.7** — **G-2 egress test required**; PRIVACY.md; ACCESSIBILITY.md
  honest-status page (F-expa11y-03); lay metrics legend (F-expa11y-04 /
  F-eval-03); F-gov-01 hook fix + F-gov-07 DEBUFF; G-1 wired and proven on
  real PRs (required-check toggle staged). PV-1/PV-2 real-loop calibration
  feeds the M-2 evidence (F-eval-02). **This file graduates here** into
  `docs/dev/RELEASE_CHECKLIST.md` additions.
- **v1.0.8** — **G-3 C-6 boundary gate required**; `route-security-lint`
  matcher extended to blueprints; F-sec-02 loopback bind pinned + asserted
  when `main()` moves in the split; F-arch-02 stale blast-radius numbers
  corrected (actuals 6992 LOC / 78 routes / 24 test files).
- **v1.1.0 (public)** — **G-1 required check** + full E-2 badge set
  (lockfile+Dependabot, Scorecard, REUSE lint, PVR) green; one-time NVDA pass
  and M-2 real-corpus evidence captured (closes T-D); fresh-clone first-run
  bars met (F-expa11y-10); every KEEP/BOOST surface protected through the tag.
