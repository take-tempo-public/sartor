---
status: review-artifact
evidence_sha: c6e0437
graduation: none (content flows into RELEASE_ARC.md via normal dev branches)
---

# Early Prescriptions (owner-directed, ahead of Phase 4)

> Phase 4 produces the full prescription set. These four were ruled on by
> the owner during Phase 1 (2026-06-12) with the directive "be sure those
> are scheduled in 1.0.6." The review is witness-only — it cannot edit
> RELEASE_ARC.md — so this file plus the paste-ready arc text below is the
> scheduling vehicle; a normal dev session applies it.

## PX-01 — Vendor Chart.js (kills the runtime CDN violation)

- **Finding:** AL-4 — `dashboard/templates/dashboard.html:15` loads
  `chart.umd.min.js` from cdn.jsdelivr.net at runtime on every
  `/_dashboard` open; violates the no-CDN promise (vision.md L89-93,
  SECURITY.md) and charter C-2.
- **Fix:** download `chart.umd.min.js@4.4.0` into `static/vendor/`
  (pattern: `paged.polyfill.js`); change the script tag to the local
  path; drop the integrity/crossorigin attrs; note the vendored asset +
  its MIT license in the bundled-assets section.
- **Size:** trivial (one session, minutes of work + license note).
- **Landing:** v1.0.6 — small fix branch (see arc text below).

## PX-02 — Re-wire the profile/website scrape (regression)

- **Finding:** AL-5 — `scraper.py:46 fetch_profile_content` has NO
  runtime caller at c6e0437 (imported only by tests); the corpus pipeline
  reads `candidate.profile_text` from SQLite
  (`db/build_context.py:149`). Owner ruling: "we should be scraping
  linkedin and website if provided … those are now broken and need to be
  fixed."
- **Fix:** re-wire `fetch_profile_content` into the runtime path. Hook
  point needs a small design decision first:
  - **(recommended)** on config save of profile/portfolio URLs —
    user-triggered, visible, cacheable into `candidate.profile_text`,
    refresh button possible; or
  - per-analyze fetch (fresher, slower, repeated egress).
  Stale comment to fix alongside: `app.js:230` ("server prepends https://
  at fetch time").
- **Constraints:** scrape stays opt-in + fails gracefully (existing
  behavior contract); `route-security-lint` will fire on app.py edits —
  scope narrowly.
- **Size:** small-medium (one branch; design decision + wiring + a test
  that the runtime path actually calls the scraper — the regression
  existed because nothing asserted the wiring).
- **Landing:** v1.0.6 — own fix branch (see arc text below).

## PX-03 — Correct the egress documentation to the two-class truth

- **Finding:** AL-7 — SECURITY.md claims a "pasted-JD URL fetch" egress
  class that has never existed in code (`jd_url` is provenance metadata,
  never fetched); vision.md/README count two classes, SECURITY.md three;
  none match code exactly.
- **Fix:** one canonical enumeration everywhere (charter C-2 wording):
  (a) the configured LLM provider; (b) the optional profile/website
  scrape when URLs are provided. State explicitly that JDs are always
  pasted text. SECURITY.md, vision.md, README.md aligned in one pass.
- **Size:** trivial docs-only; can ride PX-02's branch (the scrape
  re-wire makes class (b) true again — sequence the docs change with it).
- **Landing:** v1.0.6, same branch as PX-02 (or PX-01's if sequenced
  first — whichever session reaches it).

## PX-04 — Per-system tool bundling + progressive install docs

- **Finding:** AL-6 + owner ruling: the ~3.2GB HuggingFace scorer
  download is sanctioned power-user opt-in; "bundle the tools that must
  be installed for different systems (tuning → hugging face models, dev
  work → chromium). things a user never needs to do, they shouldn't have
  to see. then progressive documentation of tool install for various
  systems, threaded for completeness."
- **Fix (two parts):**
  1. **Docs (v1.0.6):** fold the per-system framing into Sprint 6.5's
     education sweep + the eval-stack install guide (#17): a base install
     (job-seeker path, no extras) and per-system extension threads
     (tuning system: `[eval-grounding]` extras + torch wheel + first-run
     model download with size warning; dev system: Chromium, dev extras).
     Diagnostics surfaces mention the install only at the moment a user
     steps into that system.
  2. **Packaging (v1.0.7 candidate):** extras hygiene so each system is
     one named install step (`pip install .[tuning]`-style), with the
     download moment made explicit and consentful in-UI.
- **Landing:** part 1 = Sprint 6.5 (existing item, reframed); part 2 =
  v1.0.7 pre-public hardening candidate (Phase 4 will propose formally).

---

## Paste-ready text for RELEASE_ARC.md §Phase 4.5 (v1.0.6)

Add to the v1.0.6 branch sequence (after Sprint 6.4, before/alongside
6.6 — small fixes, no dependencies):

```markdown
- `fix/vendor-chartjs` — vendor Chart.js 4.4.0 into static/vendor/
  (kills the only runtime CDN fetch; restores the no-CDN promise;
  found by the 2026-06 product review, PX-01).
- `fix/profile-scrape-rewire` — re-wire scraper.fetch_profile_content
  into the runtime path (regression: dead code since the corpus/db
  refactor; hook point: on config-save of profile URLs, cached to
  candidate.profile_text, opt-in + graceful failure) + align
  SECURITY.md/vision.md/README.md egress wording to the two-class
  enumeration (LLM provider; opt-in profile scrape; JDs always pasted)
  (review PX-02 + PX-03).
```

And one line to the Sprint 6.5 row's scope: *"install docs use the
per-system progressive model — base install vs tuning-system vs dev-system
threads (review PX-04 part 1)."*

v1.0.6 tag criteria addition: *"no runtime third-party egress beyond the
two sanctioned classes (Chart.js vendored; scrape re-wired or
consciously deferred)."*
