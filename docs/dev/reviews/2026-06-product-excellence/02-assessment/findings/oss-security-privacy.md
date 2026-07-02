---
status: review-artifact
evidence_sha: c6e0437
graduation: none
---

# Findings - Open-source readiness, security & privacy

## Domain verdict

The privacy/security substance at c6e0437 is strong and largely matches the charter promises: route containment (_safe_username + _within) is dense and unit-tested, the gitignore PII surface is thorough, committed fixtures are auditably synthetic (RFC-2606 domains), and a cold pip install -e . + import app succeeds with no key, no Chromium, and no LLM call (verified in a sandbox). The gap is not the mechanisms - it is that the two load-bearing inviolable clauses (C-1 loopback bind, C-2 two-class egress) are kept by hand / by implicit default, not by a committed test, so the charter's own "machine-verifiable" claim for C-2 is not yet true at the pin; and the public docs over-promise relative to the code in two ways C-0 bars (a false "no external CDN loaded at runtime" line, a third egress class that does not exist, two human-response SLAs D-4 softens). License declaration also lags the vendored MPL-2.0 reality. None of these are PII leaks (S-1 holds); they are the difference between "verified once" and "enforced forever," which is exactly this domain's mastery bar.

---

## Register findings (highest leverage first)

### F-sec-01 - C-2 egress is asserted in prose, not by a committed falsifiability test
- disposition: FIX
- leverage: P1
- charter-trace: C-2, E-2 (network-egress falsifiability test), C-0
- question_refs: QB-sec-01, QB-qe-rel-03
- evidence: No egress/allowlist test exists in the tree at c6e0437 (full test listing: tests/test_*.py + tests/ux/**; none assert a socket bind or an LLM-destination allowlist). The only network-touching test stubs requests.get (tests/test_scraper.py:53-58). tests/test_app_security.py is unit-only (traversal/containment).
- finding: C-2's text claims it is "machine-verifiable ... and was verified at c6e0437" - but that verification is audit-by-hand, not a gate. The destination set is enumerable (configured LLM provider; the opt-in scrape), so a committed test that fails on any outbound connection outside that set would convert the charter's strongest promise into a continuously-kept fact. Highest-leverage move for this domain and the named E-2 badge.
- coordinate: (none - net-new gate; could ride v1.0.7 hardening)

### F-sec-02 - C-1 loopback bind is implicit (Flask default), neither pinned nor asserted
- disposition: FIX
- leverage: P1
- charter-trace: C-1, S-1, C-0
- question_refs: QB-sec-02
- evidence: app.py:6988 is app.run(debug=debug_mode, port=5000) with no host= argument. Sandbox-verified: Flask.run's host default is None, which Flask maps to 127.0.0.1; booting the exact call shape bound 127.0.0.1 only - the LAN address (10.0.0.19) refused/timed out. No test pins this.
- finding: C-1 ("the server binds to 127.0.0.1 only") holds today, but only by Flask's internal None->127.0.0.1 default. A dependency bump or a copy-paste that adds host= could silently flip the load-bearing mechanism with nothing to catch it. The cheap, correct fix is an explicit host="127.0.0.1" plus a one-line regression test - pairs naturally with F-sec-01's egress test.
- coordinate: v1.0.8 (the blueprint split moves main()/bind; pin it before the move so it cannot regress in transit)

### F-sec-03 - SECURITY.md asserts "No external CDN is loaded at runtime" - false at the pin
- disposition: FIX
- leverage: P1
- charter-trace: C-0, C-2(i), P-3
- question_refs: QB-sec-04, QB-docs-02
- evidence: SECURITY.md:85 "No external CDN is loaded at runtime. Every static asset ... ships from the local repo." Contradicted by dashboard/templates/dashboard.html:15 which loads cdn.jsdelivr.net/npm/chart.js@4.4.0/... on every /_dashboard open (SRI-pinned, but real third-party egress - the only CDN ref in the tree). The accepted-risk table repeats the false premise: SECURITY.md:160 ("no third-party content is loaded (all assets are local)") under "No CSP header."
- finding: A categorical claim contradicted by code - the C-0 cardinal sin. PX-01 (vendor Chart.js) is ruled for v1.0.6 and fixes the underlying load; this finding flags that the doc claim must land in the same change, and that two SECURITY.md lines (not just the CDN tag) carry the false premise. Verify-the-fix: at c6e0437 neither the load nor the claim is corrected.
- coordinate: v1.0.6 (PX-01 - bundle the doc correction with the vendor)

### F-sec-04 - Egress enumeration is three-way divergent across SECURITY/README (+ HF undisclosed in security docs)
- disposition: FIX
- leverage: P1
- charter-trace: C-2, C-0
- question_refs: QB-sec-04, QB-docs-01
- evidence: SECURITY.md:56-59 enumerates three egress classes including "(c) any URL you explicitly paste as a job description" - a JD-URL fetch that does not exist in code (jd_url is provenance-only; no fetch call anywhere). README.md:127 correctly enumerates two classes ("nothing else leaves your machine"). Neither security doc mentions the huggingface.co weight download; only the wiki (docs/wiki/pages/non-dependency-downloads.md:44-52,76-81) discloses it.
- finding: PX-03 (correct jd_url docs to the two-class enumeration) is ruled for v1.0.6; at the pin SECURITY.md still carries the phantom third class while README is already right - a live cross-doc drift. The fix should also thread the HF opt-in download into the security narrative as a sanctioned-under-D-6 carve-out so SECURITY.md and the wiki agree. Verify-the-fix: not landed at c6e0437.
- coordinate: v1.0.6 (PX-03)

### F-sec-05 - Route containment is dense, unit-tested, and build-time-guarded (KEEP)
- disposition: KEEP
- leverage: P1
- charter-trace: C-1, S-1, D-5
- question_refs: QB-sec-02, QB-sec-03
- evidence: _safe_username at app.py:110, _within at app.py:124; across 78 routes the guards appear 82x / 59x (incl. defs), secure_filename 25x. Unit-tested for traversal / unknown-user / containment (tests/test_app_security.py:27-80). Build-time enforcer: .claude-plugin/hooks/route-security-lint.sh; .claude-plugin/hooks/block-secrets.sh:29,39 blocks sk-ant-... shapes and writes to .api_key/.env*/*.key/*.pem/*.p12.
- finding: This is the C-1/S-1 mechanism done right and must not be churned. One WATCH rider (appendix A-1): the route-lint hook scans only the Edit new_string, so coverage can drift silently as routes move into blueprints (v1.0.8) - affirm the pattern now, guard the hook scope at the split.
- coordinate: v1.0.8 (keep the guard pair + hook firing on blueprint files)

### F-sec-06 - Fresh hostile clone carries zero real PII and zero secrets (KEEP)
- disposition: KEEP
- leverage: P1
- charter-trace: S-1, C-1, D-5
- question_refs: QB-sec-03
- evidence: .gitignore ignores configs/*.config, resumes/*, output/*, logs/, db/*.sqlite*, evals/fixtures/real/* (.gitignore:2-6,13-24,38-52), allow-listing only the synthetic fixtures. Committed fixtures are auditably synthetic: configs/testuser.config (Casey Rivera, example.com email, 555-0142, RFC-2606 domains, self-documented as fictional), resumes/testuser/casey_rivera_*.md, evals/fixtures/synthetic/*. Tree scan for sk-ant-... key shapes: zero hits.
- finding: S-1 (the #1 release fear, PII leak) is satisfied at the hostile-clone lens. Affirm so the allow-list lines are not "tidied" away in a future gitignore refactor.
- coordinate: (none)

### F-sec-07 - Two human-response SLAs survive at the pin (D-4 softening pending)
- disposition: FIX
- leverage: P1
- charter-trace: D-4, P-3
- question_refs: QB-sec-07, QB-qe-rel-07
- evidence: SECURITY.md:134-135 "We aim to respond within 5 business days and to issue a fix within 30 days of confirmation." CODE_OF_CONDUCT.md:15 "The maintainer will respond within 5 business days ..." Both are response-time/fix-time promises.
- finding: D-4 ("public docs make no response-time SLAs ... existing promises ... softened to best-effort") and the posture directive explicitly name the SECURITY.md 5-day SLA for softening. Two docs carry the promise; both need best-effort wording before public. Low effort, but a charter-named obligation, and an unsoftened SLA is the DEBUFF pattern (a public human-time commitment) the charter is trying to retire.
- coordinate: v1.0.7 (pre-public hardening) or earlier

### F-sec-08 - License declaration is MIT-only; the vendored axe asset is MPL-2.0 (under-declared)
- disposition: FIX
- leverage: P2
- charter-trace: E-2 (REUSE lint), D-5
- question_refs: QB-sec-06
- evidence: LICENSE is MIT only ("Copyright (c) 2026 sartor. contributors"). tests/ux/a11y/vendor/axe.min.js header is MPL-2.0 (Deque Systems, axe v4.10.2). No LICENSES/ tree, no .reuse/REUSE.toml, no SPDX headers (tree scan: none). static/vendor/paged.polyfill.js is MIT (header preserved).
- finding: Upstream headers are preserved (good, D-5), but the repo does not machine-declare the mixed-license reality - a REUSE lint (the named E-2 badge) would flag the MPL-2.0 asset under an MIT-only declaration, and PX-01's vendored Chart.js will add a third license to declare. Mastery here is an SPDX/REUSE manifest, not just preserved headers. P2 because it blocks a badge, not the tag, and harms no user.
- coordinate: v1.0.6 (declare Chart.js's license in the same vendor change)

### F-sec-09 - None of the agreed E-2 machine gates (lockfile/Dependabot, Scorecard, REUSE, egress test, PVR) are committed
- disposition: WATCH
- leverage: P2
- charter-trace: E-2, C-0, P-3
- question_refs: QB-sec-01, QB-sec-06, QB-sec-07, QB-qe-rel-02
- evidence: .github/ contains only workflows/ci.yml (ruff + mypy + pytest on py3.11/3.12/3.13) and templates - no dependabot.yml, no Scorecard workflow, no REUSE lint, no egress test; no lockfile/requirements*.txt/poetry.lock in the tree. SECURITY.md:129 routes to GitHub Security Advisories but PVR is a GitHub repo setting (not assessable in-repo) and no setup note exists. No PRIVACY.md.
- finding: The E-2 "machine-run badge set" is the charter's chosen way to keep promises honest without taxing the owner (E-1/D-4). At the pin the set is essentially un-wired. WATCH, not FIX, because E-1 tempers this against owner grooming-burden - but F-sec-01 (egress test) and F-sec-08 (REUSE) are the two from this set that directly enforce a charter clause and graduate to FIX; the rest (Scorecard, Dependabot, PVR, PRIVACY.md) are the honest-by-machine bundle to land before the public tag, watched for badge-as-obligation creep.
- coordinate: v1.1.0 public-tag readiness

### F-sec-10 - HF eval-grounding download honors D-6 (opt-in, lazy, graceful) - KEEP, with an unpinned VCS dep WATCH
- disposition: KEEP
- leverage: P2
- charter-trace: D-6, C-2(ii), A-2
- question_refs: QB-sec-05
- evidence: HF weights (DeBERTa ~180 MB Apache-2.0; MiniCheck flan-t5-large ~3 GB) load behind the [eval-grounding] extra (pyproject.toml:59-62), lazy-imported inside the scorer (evals/grounding_signals.py:45-69), gated on the same extra in the routes with graceful degradation (app.py:6582-6618 "a missing dep never wastes the LLM spend"). Disclosed in the wiki (docs/wiki/pages/non-dependency-downloads.md:44-52).
- finding: This is the sanctioned power-user opt-in the AL-6 ruling describes, implemented to the D-6 bar: invisible to the base user path (the cold pip install -e . sandbox pulled none of it), threaded install docs, graceful degradation. Affirm. One WATCH rider: minicheck @ git+https://github.com/Liyan06/MiniCheck.git (pyproject.toml:61) is an unpinned VCS dependency (no @<sha/tag>) - a supply-chain consideration; scoped to the opt-in extra so it never touches the base user, but a pin would harden the power-user path.
- coordinate: (none - base path unaffected)

---

## Appendix (beyond the register cap)

### A-1 - route-security-lint hook scans only the Edit text (coverage can drift silently)
- disposition: WATCH | leverage: P2 | charter-trace: C-0, S-1
- evidence/finding: .claude-plugin/hooks/route-security-lint.sh is a heuristic that inspects the proposed Edit new_string, not the whole app.py/blueprint. A route added by a tool path the hook does not see, or a guard removed in an unrelated edit, will not be caught. Today coverage is excellent (F-sec-05), but the enforcer is build-time agent-tooling, not a CI test - so it protects the dev loop, not the shipped artifact. Pairs with F-sec-02's "assert it in a test" theme. (Already flagged in the domain guide WATCH list; recorded here for completeness.) Coordinate: v1.0.8 blueprint split.

### A-2 - Flask debug mode defaults ON (FLASK_DEBUG defaults to "1")
- disposition: WATCH | leverage: P3 | charter-trace: C-1, S-1
- evidence/finding: app.py:6970 debug_mode = os.environ.get("FLASK_DEBUG", "1") == "1". SECURITY.md:141 lists this as a knowingly accepted risk ("Low - local-only tool"). Consistent with the local-and-yours posture and already documented; included only because the domain-guide WATCH list names it for the "if ever fronted by a proxy" scenario. No action at the pin.

### A-3 - pyproject version string lags the in-flight epic (cosmetic)
- disposition: WATCH | leverage: P3 | charter-trace: D-5
- evidence/finding: pyproject.toml:7 version = "1.0.5" while the tree is mid-v1.0.6 (CHANGELOG.md [Unreleased] + v1.0.6 sprint entries). The cold-install sandbox reported sartor 1.0.5. Harmless for a not-yet-public tool; flag only so the v1.1.0 tag pass bumps it deliberately rather than discovering staleness at release.

### A-4 - Cold-setup smoke result (provenance for the verdict)
- disposition: KEEP | leverage: P2 | charter-trace: M-2 (fresh-clone first-run), A-1
- evidence/finding: In a temp venv outside the repo, git archive c6e0437 -> pip install -e . resolved all 8 base runtime deps with no conflict (no Chromium, no extras), and import app succeeded (app.url_map = 80 rules). A cold stranger reaches an importable app without an API key or Chromium. This is the positive half of the domain: the friction a stranger hits is Chromium-for-PDF and API-key setup (both acknowledged in A-1/M-2), not a broken base install. Dynamic evidence, sandbox-only; nothing written inside the repo.
