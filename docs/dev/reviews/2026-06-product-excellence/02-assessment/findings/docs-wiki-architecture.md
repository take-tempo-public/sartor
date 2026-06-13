---
status: review-artifact
evidence_sha: c6e0437
graduation: none
---

# Findings — Documentation & wiki architecture

**Domain verdict.** The committed LLM-wiki is the standout: its grounding contract
(one rule, `path:line`/`[[backlink]]`/`[synthesis]` mechanics), its honest
sentinel discipline (`.last_ingest_sha` left at sentinel because the code pass has
not run), D5 cite-don't-restate, and the `llms.txt`→wiki front door are all
genuinely strong and should be affirmed, not churned. The defects all live in the
**public-facing** docs and are the same class: docs that describe behavior the code
does not have at the pin (a JD-URL egress class that does not exist; "no external
CDN" while Chart.js loads from jsdelivr; a live scrape that is dead code) and
absolutes about LLM behavior that C-0 bars ("the LLM cannot invent facts"). The
egress story is three-way-divergent across SECURITY/vision/README and contradicts
code — directly into the owner's #1 fear (PII / amateurish-planning) and the P-3
"describe every part of itself" promise. Three of the four FIX items are already
charter-ruled (PX-01/PX-03, fix v1.0.6); this review verifies they are still
**unlanded at c6e0437**.

Dynamic checks run: wiki backlink-slug resolution (all 8 resolve), `[synthesis]`
tag + anchor-cite presence across all pages, scraper runtime-caller grep
(confirmed dead), egress-enumeration diff across the three public docs, install.md
prerequisite framing, eval-stack-install-guide existence check (absent). No app
boot or paid/LLM calls — all static inspection on the read-only pin.

---

## Register findings (highest leverage first)

### F-docs-01 — SECURITY.md asserts a JD-URL egress class the code does not have; the three public docs disagree
- **disposition:** FIX
- **leverage:** P1
- **charter-trace:** C-2, C-2(iv), C-0, P-3, S-1
- **question_refs:** QB-docs-01, QB-docs-02
- **evidence:** `SECURITY.md:56-59@c6e0437` lists THREE network classes incl. "(c) any
  URL you explicitly paste as a job description"; `vision.md:89-90@c6e0437` and
  `README.md:127@c6e0437` list TWO (Anthropic + optional scrape). Charter C-2(iv)/PX-03
  rules `jd_url` is provenance metadata, never fetched (interview-record AL-7,
  post-charter ruling 2026-06-12). The fix is ruled for v1.0.6 and is **not landed at
  the pin** — SECURITY.md still enumerates three classes.
- **finding:** The single most-consequential doc defect in this domain. SECURITY.md —
  the doc a security-minded stranger reads first — asserts a network destination that
  does not exist in code, and the three public docs do not even agree with each other on
  how many egress classes there are. This is the charter's cardinal C-0 sin (a
  destination claim with no code behind it) landing in the doc that most needs to be
  literally true, and it sits squarely in the owner's S-1 fear (PII / "amateurish
  planning revealed"). Prescription is ruled (PX-03): collapse all three docs to the two
  sanctioned classes (configured LLM provider; optional profile/website scrape).
- **coordinate:** v1.0.6 (PX-03)

### F-docs-02 — SECURITY.md:85 "No external CDN is loaded at runtime" is false at the pin
- **disposition:** FIX
- **leverage:** P1
- **charter-trace:** C-2, C-2(i), C-0, P-3, S-1
- **question_refs:** QB-docs-02
- **evidence:** `SECURITY.md:85@c6e0437` "No external CDN is loaded at runtime. Every
  static asset in the preview / generated output ships from the local repo." vs.
  `dashboard/templates/dashboard.html:15@c6e0437` `<script src="https://cdn.jsdelivr.net/
  npm/chart.js@4.4.0/...">` (SRI-pinned, `crossorigin="anonymous"`) loaded on every
  `/_dashboard` open. Charter C-2(i)/PX-01 rules this a confirmed violation; vendor fix
  ruled for v1.0.6, **not landed at the pin**.
- **finding:** A doc-vs-code contradiction of the same class as F-docs-01: a categorical
  promise ("No external CDN") that the runtime breaks. SECURITY.md hedges the claim in
  multiple places (line 60 "No background updates / phone-home"; line 144 "no third-party
  content is loaded") so the overclaim is load-bearing more than once. The dashboard is a
  power-user surface (E-2, A-2) so a careful reader will hit it. PX-01's vendoring removes
  the CDN load and makes SECURITY.md:85 true; until then the doc overclaims.
- **coordinate:** v1.0.6 (PX-01)

### F-docs-03 — "The LLM cannot invent facts" — a flat C-0-barred absolute the owner already flagged as overstated
- **disposition:** FIX
- **leverage:** P1
- **charter-trace:** C-0, C-3, A-4, P-3
- **question_refs:** QB-docs-02 (relates QB-vision-05/07)
- **evidence:** `vision.md:50@c6e0437` "**Honest tailoring.** The LLM cannot invent
  facts." — a bare categorical with no mechanism/effort qualifier. The same absolute
  propagates to the wiki front door: `docs/wiki/overview.md:19@c6e0437` and
  `llms.txt:6@c6e0437` "**without inventing anything about you**"; `overview.md:27` "it
  may not **fabricate**". Owner's own words: "'LLM cannot invent' is a bold claim"
  (R2-4.2) and "no invention ever is over-stated" (R2-4.4).
- **finding:** C-0 is explicit: categorical claims only where a deterministic test
  enforces them by construction; anywhere a claim depends on LLM behavior, describe
  mechanisms and effort. "The LLM cannot invent facts" is the precise antithesis, stated
  as a flat fact at the top of the vision and echoed through the wiki's front door and
  `llms.txt` (the agent entry point). The owner twice called it overstated in the
  interview. For the A-4 "whoa, this is robust" audience the overclaim does the opposite
  of its intent — a careful reader who knows LLMs distrusts the rest of the doc. Reframe
  to mechanism+effort ("does its best to keep the LLM grounded; here is exactly how"),
  matching the charter C-3 register, in all four places (vision, overview, llms.txt, and
  README's lead framing). Note `overview.md:87` already lists "lead with 'without
  inventing'" as an open revision point — this finding decides it.
- **coordinate:** (touches the v1.0.7 governance/wiki extraction surface; no sprint owns
  the public-doc copy edit yet)

### F-docs-04 — Docs describe a live profile/website scrape that is dead code at the pin
- **disposition:** FIX
- **leverage:** P1
- **charter-trace:** C-2, C-2(iii), P-3, C-0
- **question_refs:** QB-docs-02 (relates QB-sec-04)
- **evidence:** `scraper.py:46/71@c6e0437` `fetch_url_content`/`fetch_profile_content`
  have no runtime caller — grep across `app.py`/`analyzer.py`/all `*.py` (excluding
  tests) returns only a `hardening.py:1007` mirror-comment reference, no invocation. Yet
  `SECURITY.md:57-59`, `vision.md:89-90`, `README.md:127`, `README.md:25/53`,
  `install.md` (via the downloads page), and
  `docs/wiki/pages/non-dependency-downloads.md:31` all describe the scrape as a live,
  opt-in capability. Charter C-2(iii)/PX-02 rules this a regression; re-wire ruled for
  v1.0.6, **not landed at the pin**.
- **finding:** Every public doc that enumerates egress lists the scrape as class (b) — a
  capability that does not run at c6e0437. This is the "dead code shipped as working"
  pattern (map DEBUFF-5) in documentation form: the docs are not wrong about intent but
  are wrong about the assessed state. The ruled fix is to re-wire the scrape (PX-02), at
  which point the docs become true; if the wiring slips past v1.0.6 the docs must say so.
  Either way, doc and code must be reconciled before the public tag — a stranger who
  provides a LinkedIn URL and sees nothing fetched hits exactly the "amateurish execution"
  fear (S-1).
- **coordinate:** v1.0.6 (PX-02)

### F-docs-05 — Install docs fold the Chromium ~150 MB step into the base-user prerequisite, contradicting D-6
- **disposition:** FIX
- **leverage:** P1
- **charter-trace:** D-6, A-2, A-1, M-2 (first-run <5 min)
- **question_refs:** QB-docs-04 (relates QB-sec-05)
- **evidence:** `docs/install.md:26-30@c6e0437` lists "~150 MB ... for the Chromium
  binary" under **Prerequisites**; the Windows/macOS/Linux paths each make
  `playwright install chromium` a mandatory numbered step (`install.md:61-64, 111-114,
  164-167`). `docs/wiki/pages/non-dependency-downloads.md:22-23` correctly classes
  Chromium as "the single biggest non-pip download for normal use," but normal use there
  conflates PDF render with the whole product. Charter D-6 (post-charter ruling
  2026-06-12) classes Chromium as a *dev/PDF-render* per-system bundle that users who
  never enter that system "shouldn't have to see."
- **finding:** D-6 says capabilities requiring extra installs are bundled per system and
  progressively disclosed; the install doc instead front-loads a ~150 MB binary as a flat
  prerequisite for everyone. A fresh-clone, skip-clarify, DOCX-output smoke user (the
  M-2 "<5 min" bar) does not need Chromium — it renders PDF and the live preview only.
  The fix is framing, not deletion: present Chromium as the PDF/preview step a user
  reaches when they want PDF, lifted out of the base prerequisite block, with the user
  path to a first DOCX clean. This is the lowest-cost half of the D-6 progressive-
  disclosure work and directly serves the first-run-time bar.
- **coordinate:** Sprint 6.5 (in-app education / install-guide sweep)

### F-docs-06 — The Sprint 6.5 eval-stack install guide does not exist; the ~3.2 GB HF opt-in is documented only in a wiki provenance page
- **disposition:** FIX
- **leverage:** P2
- **charter-trace:** D-6, C-2(ii), A-2, M-2 (v1.0.7 explainability)
- **question_refs:** QB-docs-04 (relates QB-sec-05)
- **evidence:** `find docs -iname "*eval-stack*"` returns nothing at c6e0437 (absent).
  `docs/wiki/pages/non-dependency-downloads.md:9-11,44-52@c6e0437` names
  `docs/eval-stack-install-guide` as a Sprint 6.5 deliverable (finding #17) and carries
  the verified provenance table (torch ~200 MB, DeBERTa ~180 MB, MiniCheck flan-t5-large
  ~3 GB, "~3.2 GB total"). No `README`/`SECURITY`/`install.md` mention of the HF download
  exists (grep for `huggingface`/`3.2GB`/`grounding-scorer` across `docs/ README.md
  SECURITY.md vision.md` hits only `docs/dev/` and the one wiki page).
- **finding:** The charter's D-6 (C-2(ii) carve-out) requires the ~3.2 GB HF
  grounding-scorer download to be an explicitly disclosed power-user opt-in with threaded
  install docs. At the pin that disclosure lives **only** in a wiki provenance page; the
  user-/power-user-facing install guide it is meant to feed does not exist. The provenance
  groundwork is excellent (see F-docs-08) — the gap is the missing surfaced guide. This is
  P2 (the download is power-user-only and degrades gracefully) but it is a named v1.0.6/6.5
  deliverable and a charter D-6 obligation, so it must ship before the public tag closes.
- **coordinate:** Sprint 6.5

### F-docs-07 — KEEP: the wiki's one grounding rule + cite/backlink/synthesis convention is genuinely practiced
- **disposition:** KEEP
- **leverage:** P2
- **charter-trace:** P-3, W-2, S-3, A-4 (exhibit #3)
- **question_refs:** QB-docs-03, QB-docs-05
- **evidence:** `docs/wiki/SCHEMA.md:73-81@c6e0437` states the one grounding rule and
  frames it as the same rule the product enforces on résumés. The convention is *used*,
  not just declared: all 8 backlink slugs in `pages/` resolve (verified by slug-existence
  check); `[synthesis]` tags appear in every page (1-5 each); cites use symbol/anchor form
  (`analyzer.py:SYSTEM_PROMPT`, `pyproject.toml`) per `SCHEMA.md:69`'s "prefer a symbol
  over a bare line number" guidance; `index.md`/`llms.txt`/`overview.md` form a working
  front door (`llms.txt:9-17`).
- **finding:** This is the charter's A-4 exhibit #3 (wiki/memory + documentation-with-git)
  and it earns the claim. The grounding contract is sharp and self-aware, the conventions
  are honored in the actual pages, and a stranger landing on `llms.txt` reaches an accurate
  map. Affirm so it is not churned by the v1.0.7 extraction or WS-4b ingest. The one caveat
  rides on F-docs-03: the wiki front door (overview.md, llms.txt) inherits the "without
  inventing" absolute from the vision and should be reframed in lockstep.
- **coordinate:** (protect through v1.0.7 governance extraction + WS-4b)

### F-docs-08 — KEEP: sentinel-honesty discipline — `.last_ingest_sha` left at sentinel rather than falsely advanced
- **disposition:** KEEP
- **leverage:** P2
- **charter-trace:** P-3, W-2, C-0
- **question_refs:** QB-docs-03
- **evidence:** `docs/wiki/.last_ingest_sha@c6e0437` carries no 40-char SHA (sentinel
  comment only). `docs/wiki/log.md:36-42@c6e0437` records the deliberate decision: the
  2026-06-09 ingest was docs-scoped, "Advancing it would falsely assert the code was
  ingested and would prematurely silence the commit-time freshness reminder before WS-4b
  ever runs." `index.md:39-45` honestly marks the code architecture as "not yet ingested."
  The verified provenance table in `non-dependency-downloads.md:65-81` (sizes/licenses
  dated 2026-06-07) is the same honesty discipline applied to downloads.
- **finding:** A rot-detection discipline most wikis lack: the team resisted the easy lie
  of advancing the checkpoint to silence the staleness signal, and documented exactly why.
  This is the mechanism that makes the wiki's staleness *measurable* (sha vs HEAD) rather
  than discovered. It is the precondition for the WATCH item (F-docs-10) — affirm it so the
  WS-4b ingest preserves it.
- **coordinate:** (protect through WS-4b)

### F-docs-09 — KEEP: governance-extraction design records the load-bearing `@import` safety condition for one-home-per-rule
- **disposition:** KEEP
- **leverage:** P2
- **charter-trace:** W-2, C-0
- **question_refs:** QB-docs-07 (relates QB-gov-05)
- **evidence:** `docs/wiki/SCHEMA.md:33-48@c6e0437` (D5: "The contract lives elsewhere" —
  binding rules stated once in canonical homes, wiki cites). `docs/wiki/pages/
  governance-extraction.md:27-52@c6e0437` records "extract, don't register-in-place" (one
  canonical home per rule) AND the ⚠ critical constraint (lines 45-52): extraction "MUST
  preserve agent rule-access via `@import` ... or every future agent loses its guardrails."
- **finding:** The v1.0.7 governance extraction is the charter's own graduation vehicle
  (W-2), and the design doc for it already names both the goal (exactly one home per rule,
  cite-don't-restate) and the safety condition that makes it non-destructive (`@import`
  preserves harness-auto-loaded rule access). This is the QB-docs-07 / QB-gov-05 concern
  pre-answered in design. Affirm; the WATCH is whether the *build* honors it (F-docs-10).
- **coordinate:** v1.0.7 (governance extraction)

### F-docs-10 — WATCH: WS-4b code cold-ingest untested — grounding rule at module scale, and whether `.last_ingest_sha` rot-detection ever fires
- **disposition:** WATCH
- **leverage:** P2
- **charter-trace:** P-3, W-2, A-4
- **question_refs:** QB-docs-06 (relates QB-docs-07)
- **evidence:** `docs/wiki/index.md:39-45@c6e0437` — the code architecture is explicitly
  "not yet ingested"; that is the `wiki/cold-ingest-code` pass (WS-4b), which "also
  advances `.last_ingest_sha` from its sentinel." `pages/` currently covers only the
  docs-grounded excellence walk. The `sha → HEAD` rot check has therefore never fired.
- **finding:** The wiki's grounding rule and its rot-detection are proven only at
  docs-pass scale. WS-4b is where both get their real test: whether the one grounding rule
  holds across ~7k LOC of `app.py` + the deterministic modules without synthesis errors
  becoming "facts," and whether advancing `.last_ingest_sha` actually arms the
  staleness/freshness machinery as designed. Also watch (per F-docs-09) that the parallel
  v1.0.7 governance extraction leaves exactly one home per rule, not a second copy. Not yet
  actionable — monitor at WS-4b execution (sequenced after Sprint 6.6).
- **coordinate:** WS-4b

---

## Appendix (beyond the register cap)

### A-docs-01 — README lead frames the product without the grounding mechanism/effort qualifier (minor C-0 register)
- **disposition:** WATCH · **leverage:** P3 · **charter-trace:** C-0, A-4
- `README.md:3@c6e0437` leads with capability framing ("tailors résumés ... the LLM
  handles analysis and writing") without the no-invention overclaim, which is fine — but
  if the F-docs-03 reframe propagates a mechanism sentence into the README it should match
  the charter C-3 register, not re-import an absolute. Bundle with F-docs-03 when edited.

### A-docs-02 — SECURITY.md 5-business-day response + 30-day fix SLA not yet softened to best-effort
- **disposition:** FIX · **leverage:** P2 · **charter-trace:** D-4, P-3
- `SECURITY.md:134@c6e0437` "We aim to respond within 5 business days and to issue a fix
  within 30 days of confirmation." Charter D-4 (posture directive, R2-1 continued)
  requires human-promise SLAs softened to best-effort wording. Owned primarily by
  QB-qe-rel-07 / QB-sec-05 (the same 5-day promise also at `CODE_OF_CONDUCT.md:15`);
  flagged here only as a docs-surface instance, not double-counted in the register.

### A-docs-03 — `non-dependency-downloads.md` "for normal use" framing pre-stages the F-docs-05 conflation
- **disposition:** WATCH · **leverage:** P3 · **charter-trace:** D-6
- `docs/wiki/pages/non-dependency-downloads.md:17-23@c6e0437` groups Chromium under "(a)
  To run the basic tool," accurate for PDF output but inheriting the same
  base-prerequisite conflation as install.md (F-docs-05). When the install guide is
  re-tiered per D-6, this wiki page's "(a)" grouping should note that PDF/preview is the
  trigger, not the whole tool. Low priority — the page is provenance, not the user path.

### A-docs-04 — install.md verification step cites a test count that may be stale
- **disposition:** WATCH · **leverage:** P3 · **charter-trace:** P-3 (self-description accuracy)
- `docs/install.md:295@c6e0437` "Should report `637+ passed`"; the map notes test counts
  drifting (632 → 1072 → ~955, product-map §5). The "+" hedge makes it non-binding, but a
  cold stranger who sees a very different number may distrust the doc. Same count-drift
  class as map DEBUFF-2. Low priority; verify against the live suite when WS-3 runs.
