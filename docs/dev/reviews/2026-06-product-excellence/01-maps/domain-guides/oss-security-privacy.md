---
status: review-artifact
evidence_sha: c6e0437
graduation: none (rubric portions are v1.0.7 governance candidates)
---

# Domain Guide — Open-source readiness, security & privacy

> Severity anchor: the signed Product Charter. A gap matters here only if
> it blocks a charter clause. Charter anchors for this domain: **C-1**
> (local-and-yours), **C-2** (two-class egress + rulings PX-01..03),
> **S-1** (PII leak = top release fear), **D-4** (commitments hygiene),
> **P-3** (no-guarantees posture). Claims discipline **C-0** governs this
> guide too: no absolutes about LLM behavior; mechanisms + effort
> language; no marketing register.

## 1. What mastery means here

For *this* product, security and privacy excellence is not a generic
hardening checklist — it is **making C-1 and C-2 falsifiable, then
keeping the public-facing promises no larger than the machine can
enforce.**

- **C-2 is the load-bearing clause.** Its own text claims it is
  "machine-verifiable" because the egress destination set is enumerable
  (two classes: the configured LLM provider; the opt-in profile/website
  scrape). Mastery = that enumeration is asserted *by a committed test*,
  not just by audit-at-a-point-in-time. The charter says it "was verified
  at c6e0437" by hand; excellence converts that to continuous enforcement
  (E-2's "network-egress falsifiability test").
- **C-1 is enforced by construction or it is just a sentence.** The
  loopback bind and the per-route filesystem containment
  (`_safe_username` + `_within`) are the two mechanisms; mastery is full
  coverage across all 78 routes plus a test that *fails* if the bind or a
  guard regresses.
- **S-1 (PII leak, the #1 fear) sets the hostile-clone lens.** A fresh
  clone must contain zero real PII and zero secrets, and the gitignore +
  committed-fixture set must be auditable as synthetic-only.
- **P-3 / D-4 bound the public posture.** Best practice says "publish an
  SLA"; the charter outranks it — promises that tax the owner's life
  (response-time SLAs, recurring manual audits) are softened to
  best-effort, while *machine-run* gates may speak categorically (C-0,
  E-1). Mastery is choosing badges that keep themselves honest over
  badges that create obligations (E-2's machine-run set).

## 2. Current state pointers

**Strengths (name them):**
- Route containment is real and dense: `_safe_username` defined at
  `app.py:110`, `_within` at `app.py:124`; across the 78 routes the
  guards are called 66× / 48× respectively, with `secure_filename` 22×.
  Unit-tested at `tests/test_app_security.py` (traversal, unknown-user,
  containment).
- Build-time enforcement exists: `.claude-plugin/hooks/route-security-lint.sh`
  blocks app.py route edits that touch the FS without both guards;
  `block-secrets.sh` blocks `sk-ant-…` shapes and writes to
  `.api_key`/`.env`/`*.key`/`*.pem`.
- Gitignore is thorough on the PII surface (`.gitignore` L2, L13–24,
  L38–52): configs, resumes, output, logs, `db/*.sqlite`,
  `evals/fixtures/real/`. Committed fixtures are synthetic-only
  (`configs/testuser.config`, `resumes/testuser/casey_rivera_*`).
- Vendoring discipline is partly in place: `static/vendor/paged.polyfill.js`
  (MIT header preserved); axe vendored at
  `tests/ux/a11y/vendor/axe.min.js` with its **MPL-2.0** header intact.

**Gaps (evidence-cited @c6e0437):**
- **No egress-falsifiability test.** No committed test asserts the
  socket/route allowlist; `tests/test_app_security.py` is unit-only. C-2's
  "machine-verifiable" property is currently audit-by-hand, not enforced.
- **C-1 loopback bind is implicit.** `app.py:6988` is
  `app.run(debug=debug_mode, port=5000)` with no `host=` argument — it
  relies on Flask's `127.0.0.1` default; nothing asserts it.
- **License completeness lags the vendored reality.** `LICENSE` is MIT
  only; no SPDX headers / `.reuse` / `LICENSES/` tree, so the MPL-2.0
  axe asset and the to-be-vendored Chart.js are not machine-declared
  (REUSE lint would flag this — E-2).
- **C-2 ruling work pending (all v1.0.6):** Chart.js still loads from CDN
  (`dashboard/templates/dashboard.html:15`, PX-01); `fetch_profile_content`
  has no runtime caller (`scraper.py:71`, dead code, PX-02);
  SECURITY.md still enumerates **three** egress classes (L56–59, PX-03).
- **D-4 softening pending:** SECURITY.md L134–135 carries a 5-business-day
  response SLA + 30-day fix promise; CODE_OF_CONDUCT.md L15 repeats the
  5-day SLA. No `PRIVACY.md` exists yet (E-2 pairs the egress test with one).
- **Disclosure channel:** SECURITY.md routes to GitHub Security Advisories
  (L129) but GitHub **Private Vulnerability Reporting** is not yet enabled
  as a setup step (E-2 one-time item).

## 3. Rubric (BOOST / KEEP / FIX / DEBUFF / WATCH)

- **BOOST** — A committed egress-allowlist test that fails on any
  destination outside the two sanctioned classes; SPDX/REUSE lint green in
  CI declaring axe (MPL-2.0) + Chart.js; PVR live before day one. These
  convert charter promises into machine-kept facts (C-2, E-2, C-0).
- **KEEP** — The `_safe_username`/`_within` pattern + its lint hook; the
  thorough gitignore; synthetic-only committed fixtures; preserved
  upstream license headers. Do not regress these (C-1, S-1, D-5).
- **FIX** — Pin the loopback host explicitly and assert it (C-1); vendor
  Chart.js + drop the CDN (PX-01); re-wire the scrape (PX-02); align
  SECURITY/vision/README to the two-class enumeration (PX-03); soften the
  SLA wording (D-4).
- **DEBUFF** — Any new public promise of human response time or recurring
  manual audit (violates D-4/P-3); any categorical "never leaks" claim not
  backed by a deterministic test (violates C-0); a route added without the
  guard pair.
- **WATCH** — REUSE/Scorecard badges becoming obligations the solo owner
  must groom (E-1 tempering); the route-lint hook is heuristic + scans only
  the edit text, so coverage can silently drift; FLASK_DEBUG defaulting to
  1 if the app is ever fronted by a proxy (SECURITY.md accepted risk).

## 4. Sharpest questions

(See structured output for the question bank entries; each is decidable
against the pointers below.)
