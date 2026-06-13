---
status: review-artifact
evidence_sha: c6e0437
graduation: none
---

# Domain assessment - Documentation and wiki architecture

> Severity anchor: the SIGNED Product Charter. A finding matters only insofar
> as it bears on a charter clause. C-0 claims discipline honored here:
> mechanism/effort language, no absolutes about LLM behavior, no marketing
> register. Evidence pinned at c6e0437, cited via `git show c6e0437:<path>`
> (byte-identical to the worktree, which differs only under `review/`).

## Domain verdict

The wiki substrate is genuinely well-built: a sharp one-grounding-rule
contract that mirrors the product's own resume-grounding discipline, a
measurable-staleness design, a clean `llms.txt` front door whose 12 link
targets all resolve, and - most creditably - a documented refusal to falsely
advance `.last_ingest_sha` past what was actually ingested. That discipline is
the rot-detection most wikis lack; affirm it, do not churn it. The live
weakness is doc-vs-code drift in the canonical (non-wiki) docs: the egress
story is three-way-divergent across SECURITY/vision/README; SECURITY.md and
vision.md assert "no CDN" while `dashboard.html:15` still loads Chart.js from a
CDN at the pin; and `architecture.md`/`walkthrough.md` describe a live
profile-scrape that is dead code - with `architecture.md:197` citing a function
`scrape_url()` that exists nowhere. None of the v1.0.6 ruled fixes
(PX-01/02/03) have landed at c6e0437, so every drift is live. The wiki itself
also carries one internal staleness bug (SCHEMA.md still says "pages/ is empty
/ skeleton only" after 8 pages were ingested).

---

## Register (highest leverage first)

### F-docs-01 - Egress enumeration is three-way divergent across the public docs (the AL-7 drift, live at the pin)

- disposition: FIX
- leverage: P1
- charter-trace: C-2, C-0, S-1
- question_refs: QB-docs-01, QB-vision-07, QB-sec-04
- coordinate: v1.0.6 (PX-03)
- evidence: `SECURITY.md:57-59` enumerates THREE network classes - "(a) the Anthropic API, (b) the URL scraper for LinkedIn / portfolio URLs ... and (c) any URL you explicitly paste as a job description." `vision.md:89-90` enumerates TWO ("(a) the Anthropic API, (b) the optional LinkedIn / portfolio URL scrape"). `README.md:53-54, :127` enumerates TWO (Anthropic + opt-in scrape). The charter (C-2 (iv), PX-03) rules NO JD-URL fetch exists - `jd_url` is provenance metadata.
- finding: SECURITY.md asserts a third egress destination - a fetch of a pasted job-description URL - that the charter rules absent and the other two public docs do not list. The three public docs a security-minded stranger would triangulate disagree with each other, and the most authoritative (the threat model) overclaims a destination the code never produces. Under S-1 (PII-leak is the number-1 release fear) the security doc being the LEAST accurate of the three is the wrong failure direction. The ruled fix is to collapse all three to the two sanctioned classes; until then the drift is live at c6e0437.

### F-docs-02 - "No external CDN is loaded at runtime" is asserted by two docs while the dashboard still loads Chart.js from a CDN

- disposition: DEBUFF
- leverage: P1
- charter-trace: C-2, C-0, P-3
- question_refs: QB-docs-02, QB-sec-04
- coordinate: v1.0.6 (PX-01)
- evidence: `SECURITY.md:85` - "No external CDN is loaded at runtime. Every static asset ... ships from the local repo." `vision.md:92` - "no ... third-party CDN fetches at runtime." Yet `dashboard/templates/dashboard.html:15` loads https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js (SRI-pinned, crossorigin anonymous) on every /_dashboard open. `static/vendor/` contains only `paged.polyfill.js` - Chart.js is NOT vendored at the pin.
- finding: Two public docs make a categorical "no CDN at runtime" claim the diagnostics surface contradicts - the cardinal C-0 sin (categorical claim, no enforcer, falsified by code) on the exact text the charter audit flagged. SRI pins the bytes but does not eliminate the third-party egress the docs deny. Charter C-2 (i) ruled this a confirmed violation; the prescription (vendor `chart.umd.min.js` into `static/vendor/` like paged.js) is decided. Verify-the-fix: it has NOT landed at c6e0437, so the doc remains an over-claim against live code.

### F-docs-03 - architecture.md and walkthrough.md describe a live profile-scrape that is dead code, and architecture.md cites a non-existent function name

- disposition: FIX
- leverage: P1
- charter-trace: C-2, C-0, P-3
- question_refs: QB-docs-02, QB-docs-05, QB-sec-04
- coordinate: v1.0.6 (PX-02)
- evidence: `docs/architecture.md:197` describes `scraper.py` as "LinkedIn / portfolio URL fetch (best-effort)" with the function `scrape_url()` - but `git grep 'def scrape_url' c6e0437` returns nothing; the real functions are `fetch_url_content` / `fetch_profile_content` (`scraper.py:40,71`), and neither has a non-test caller (grep across all *.py excluding scraper.py/tests/ is empty; the only repo reference is a comment at `hardening.py:1007`). `docs/walkthrough.md:215` tells the user analyze "re-reads the JD + your full master resume + any LinkedIn / portfolio scrape ON EVERY ANALYZE CALL." So the docs describe a runtime path that does not run at the pin, and the canonical architecture cite points at a symbol that does not exist.
- finding: This extends the egress doc-drift class BEYOND the three public docs into the developer-facing canonical docs. A stranger following the A-2 user-to-power-user-to-dev path who opens architecture.md to verify the scrape finds a function name that resolves nowhere - the BOOST promise (QB-docs-05: "working path:line cites") fails on the canonical doc, not the wiki. The charter rules the scrape a regression to re-wire (C-2 (iii), PX-02); whichever way it resolves, the docs currently describe a capability the code lacks. The inaccurate-symbol cite in architecture.md is the higher-effort half (not auto-corrected by the PX-02 re-wire; needs a doc pass).

### F-docs-04 - KEEP: the one grounding rule + falsifiability convention is sharp and self-aware

- disposition: KEEP
- leverage: P2
- charter-trace: P-3, W-2, S-3
- question_refs: QB-docs-03
- coordinate:
- evidence: `docs/wiki/SCHEMA.md:74-81` - "A wiki page may not assert anything its cited sources do not support ... The wiki is lossy synthesis ... Grounding ([[links]] + path:line cites + quote-matching) is what keeps that from happening." SCHEMA.md frames this as "the project's own grounding contract turned on its documentation ... synthesis may not invent past its source," with [synthesis] tags and [[backlinks]] defined in the page conventions.
- finding: The wiki's grounding contract is genuinely excellent: it states the load-bearing invariant once, names the falsifiability mechanism (cites + quote-matching + synthesis tags), and consciously mirrors the product's own resume-grounding rule - a coherence between tool and self-description that serves P-3 ("describe every part of itself") and the v1.0.7 support agent (only as trustworthy as the sourceable docs beneath it). Affirm so it is not weakened under WS-4b refactor pressure.

### F-docs-05 - KEEP: sentinel-honesty - .last_ingest_sha deliberately left at the sentinel after the docs-only ingest

- disposition: KEEP
- leverage: P1
- charter-trace: P-3, W-2, C-0
- question_refs: QB-docs-03
- coordinate: WS-4b
- evidence: `docs/wiki/.last_ingest_sha` is literal text "# no code ingest yet - first /wiki-ingest performs a full cold pass (see SCHEM..." - no 40-char SHA. `docs/wiki/log.md:36-42` (2026-06-09 entry) records: ".last_ingest_sha deliberately LEFT at the sentinel. ... Advancing it would falsely assert the code was ingested and would prematurely silence the commit-time freshness reminder before WS-4b ever runs."
- finding: The team resisted the easy lie. A docs-only ingest populated 8 pages but the checkpoint that tracks the CODE ingest was deliberately not advanced, with the reasoning recorded in the log - so staleness stays measurable and the freshness reminder stays armed until WS-4b actually runs a code pass. This is the rot-detection discipline the domain's mastery bar demands; a charter-grade strength (C-0: do not assert what did not happen). Protect it through WS-4b - advancing the sentinel is correct ONLY when the cold code pass genuinely runs.

### F-docs-06 - SCHEMA.md is internally stale: "pages/ is empty / skeleton only" after 8 pages were ingested

- disposition: FIX
- leverage: P2
- charter-trace: P-3, W-2
- question_refs: QB-docs-03, QB-docs-05
- coordinate: WS-4b, Sprint 6.5
- evidence: `docs/wiki/SCHEMA.md:59` - "pages/ | Flat, slug-named synthesized pages. EMPTY UNTIL INGEST (steps 4 + WS-4b)." `SCHEMA.md:115-117` - "## Status ... SKELETON ONLY. pages/ is empty; overview.md is the one seeded entry." But `git ls-tree c6e0437 docs/wiki/pages/` shows 8 ingested pages, index.md lists them, and `log.md:24-34` records the 2026-06-09 ingest that created them (step 4 already ran).
- finding: The wiki's own rulebook describes a state the wiki left three days before the pin. The "skeleton only / pages empty" status was not updated when step 4 populated pages/. Low-harm (index and log are current) but it is precisely the doc-vs-state drift the wiki exists to detect - a wiki-lint that flagged this would justify itself. A stranger reading SCHEMA.md as the entry point is told the wiki is empty when it is not. Cheap fix; fold into the next wiki touch (Sprint 6.5 authors into the wiki, or WS-4b).

### F-docs-07 - KEEP: D5 cite-dont-restate + the governance-extraction @import safety condition are recorded before the extraction runs

- disposition: KEEP
- leverage: P2
- charter-trace: W-2, C-0
- question_refs: QB-docs-07, QB-gov-05
- coordinate: v1.0.7 (governance extraction)
- evidence: `docs/wiki/SCHEMA.md:34-48` (D5) - binding rules "are stated ONCE, in their canonical homes, and the wiki only CITES them ... The wiki does not restate these. On any conflict, the canonical docs win." `docs/wiki/pages/governance-extraction.md:45-52` - "Extraction MUST preserve agent rule-access via @import ... or every future agent loses its guardrails. ... This is the load-bearing safety condition on the whole extraction."
- finding: The one-job-per-rule-bearing-doc principle (precondition for a wiki-lint that checks "does what we built still match what we said") is already stated, and the single most dangerous failure mode of the v1.0.7 governance extraction - agents losing rule-access if @import is dropped - is named in advance as load-bearing. Design-before-code done right (matches map BOOST-1). Affirm so the v1.0.7 extraction owner does not rediscover the constraint; WATCH that extraction leaves exactly one home per rule (no second copy).

### F-docs-08 - BOOST: llms.txt front door is a clean agent entry point and all its targets resolve

- disposition: BOOST
- leverage: P2
- charter-trace: A-2, A-4, P-3
- question_refs: QB-docs-05
- coordinate:
- evidence: `llms.txt` points an agent at the wiki map first ("The committed knowledge wiki under docs/wiki/ is the best map ... start there"), states the precedence rule ("on any conflict the canonical docs below win"), and lists 12 targets. All 12 resolve at c6e0437 (git cat-file -e on index/overview/SCHEMA, system-model, architecture, PRODUCT_SHAPE, vision, README, AGENTS, CLAUDE, CONTRIBUTING, SECURITY - all OK).
- finding: A cold agent or dev-register stranger gets a single legible front door that names the wiki as the map, states the wiki-to-canonical precedence (so a stale wiki page cannot silently win), and routes per audience. No broken links. Real progress toward the legible public/internal boundary the A-2 continuum needs and the A-4 "whoa, robust" exhibit number-3. The remaining gap to a full BOOST is that the DESTINATIONS (architecture.md scrape cite, the egress trio) still carry the F-docs-01/03 drift - the front door is clean, some rooms are not.

### F-docs-09 - Install docs fold the Chromium ~150 MB download into the base-user prerequisite, against D-6 progressive disclosure

- disposition: FIX
- leverage: P2
- charter-trace: D-6, A-2, A-1
- question_refs: QB-docs-04, QB-sec-05
- coordinate: Sprint 6.5
- evidence: `docs/install.md:26-30` lists "~150 MB of free disk space for the Chromium binary Playwright downloads for PDF rendering" under Prerequisites, and `install.md:61-64` makes "Download the Chromium binary for PDF rendering (one-time, ~150 MB)" a numbered base step in the Windows (and parallel macOS/Linux) install flow. The eval-stack opt-in guide the charter expects (`docs/eval-stack-install-guide`, the ~3.2 GB HF download under D-6) DOES NOT EXIST at the pin (git ls-tree returns nothing for eval-stack/install-guide); its content lives only in `docs/wiki/pages/non-dependency-downloads.md:34-81`.
- finding: D-6 (per-system tool bundling, progressively disclosed: "things a user never needs to do, they should not have to see") wants the user path clean and heavier installs threaded as opt-ins. The Chromium step is genuinely needed for PDF render (the wiki provenance page itself classifies it under "(a) to run the basic tool," non-dependency-downloads.md:22-27), so this is a softer FIX than the eval-stack case - but presenting a 150 MB browser download as a flat base prerequisite still front-loads friction onto the cold user, and the M-2 "fresh-clone skip-clarify smoke under 5 min" bar makes that cost real. The eval-stack guide is the harder gap: the ~3.2 GB HF opt-in (the genuinely-hide-able power-user install) has no shipped install doc at all, only wiki provenance - a Sprint 6.5 deliverable not yet present.

### F-docs-10 - WATCH: WS-4b code cold-ingest is unrun; the grounding rule and sha-to-HEAD rot check are untested at module scale

- disposition: WATCH
- leverage: P2
- charter-trace: P-3, W-2
- question_refs: QB-docs-06
- coordinate: WS-4b
- evidence: `docs/wiki/index.md:39-45` - "The code architecture ... is NOT YET INGESTED - that is the whole-repo cold pass wiki/cold-ingest-code (WS-4b), which also advances .last_ingest_sha from its sentinel." The 8 ingested pages are all docs-grounded (excellence-walk source, log.md:24-34); none carry verified path:line CODE cites - they cite code by symbol/module in prose (e.g. `consistency-tracks-enforcement.md:38` "145 refs / 75 routes"; the actual route count at the pin is 78 per git grep on c6e0437:app.py, a minor snapshot drift).
- finding: The wiki's hardest promises - that the one grounding rule holds at code-pass scale and that .last_ingest_sha-to-HEAD rot-detection actually FIRES - have never been exercised; no code pass has run. The docs-only pages are clean but easy (committed docs are stable sources); the robustness question is whether per-module path:line cites stay grounded and drift-detectable once code is ingested. Not yet actionable (WS-4b is scheduled after Sprint 6.6), but it is the load-bearing unknown for the A-4 exhibit-number-3 claim - monitor that the first code ingest (a) advances the sentinel honestly and (b) produces cites that resolve and that lint can re-check.

---

## Appendix (beyond the register cap)

### A-docs-01 - SECURITY.md retains the 5-business-day / 30-day SLA (D-4 softening not landed)

`SECURITY.md:134-135` - "We aim to respond within 5 business days and to issue a fix within 30 days of confirmation." Charter D-4 / the posture directive softens human-promise SLAs to best-effort. Primarily a governance/qe-rel concern (QB-qe-rel-07), surfaced here only because it lives in a public egress/posture doc; cross-ref, not docs-register-grade.

### A-docs-02 - Synthesized-page count drift (75 vs 78 routes)

`docs/wiki/pages/consistency-tracks-enforcement.md:38` and project-self-assessment.md cite "75 routes" / "145 refs"; the actual route count at the pin is 78. These are docs-grounded pages citing the excellence-walk's 2026-06-07 snapshot, so the drift is expected staleness, not a grounding violation - but it is the same count/list-drift pattern the product map flags (DEBUFF-2). Low harm; auto-reconciled by a WS-4b code pass with a wiki-lint count check.

### A-docs-03 - README/vision egress phrasing is C-0-compliant (the inverse of F-docs-01/02)

Recorded as a positive: `README.md:52-54` ("nothing leaves your computer EXCEPT [the two classes]") and `vision.md:89-90` use the ENUMERATED form C-0 wants - the absolute is qualified by the destination list that makes it verifiable. `SECURITY.md:6` ("what never leaves the machine") is a Purpose-header topic descriptor immediately enumerated at L57-59, not a bare unqualified absolute. The C-0 problem in SECURITY.md is the OVER-enumeration (the phantom JD-URL class, F-docs-01), not an unqualified "ever" absolute. So the egress fix is a reconciliation-to-two-classes job, not a rewrite-to-add-qualifiers job.

### A-docs-04 - raw/ constitutional layer correctly deferred and kept at zero

`SCHEMA.md` ("The raw/ constitutional layer (not yet present)") and `log.md:44-50` document that nothing was copied into a raw/ folder because git already is the raw layer for tracked material. Correct restraint (avoids the duplicate-and-rot failure); supports the W-2 governance-extraction design. Minor KEEP, no action.
