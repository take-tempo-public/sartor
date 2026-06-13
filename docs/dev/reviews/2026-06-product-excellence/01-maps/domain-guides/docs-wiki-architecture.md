---
status: review-artifact
evidence_sha: c6e0437
graduation: none (rubric portions are v1.0.7 governance candidates)
---

# Domain guide — Documentation & wiki architecture

> Severity anchor: the signed Product Charter. A gap matters here only if it
> blocks a charter clause. Claims discipline (C-0) applies to this guide too:
> mechanisms and effort, no absolutes about LLM behavior, no marketing register.
> Evidence pinned at `c6e0437` (a clean ancestor of the worktree HEAD; only
> `review/` artifacts differ, so every doc cited below is byte-identical here).

## 1. What mastery means here

callback. makes an unusual promise: P-3 says the project puts "effort into
sourcing and describing every part of itself," and ships a doc-grounded support
agent (v1.0.7) that can explain "how it works, what it's been, what it hopes to
be." That promise turns documentation from a courtesy into a **load-bearing
subsystem** — the *Memory* function of the system-model (overview.md:52). Mastery
in this domain is therefore not "good docs"; it is:

- **A legible public/internal boundary** (A-2's user→power-user→dev continuum):
  a stranger can tell what they're meant to read from the project's working
  notes, without a tour.
- **Provenance that survives scale** (P-3, W-2): the committed LLM-wiki may
  *select, condense, connect* its sources but never assert past them
  (SCHEMA.md:74 "one grounding rule"), and its staleness is *measurable*
  (`.last_ingest_sha` vs HEAD) so rot is detected, not discovered.
- **One job per rule-bearing doc** (W-2 governance extraction): each binding
  rule stated once, everything else pointing to it — the precondition for a
  `wiki-lint` that can check "does what we built still match what we said."
- **Groundable self-description** (P-3, S-3): the support agent's answers are
  only as trustworthy as the sourceable, *current* docs beneath it.

Generic best practice (a docs/ that onboards; a single source of truth) is
necessary but subordinate: the charter's "describe every part of itself" bar is
higher than most projects set, and C-0 forbids the confident overclaiming that
ordinary docs indulge.

## 2. Current state — strengths and pointers

**Strengths, named:**
- The wiki's grounding contract is genuinely sharp and self-aware:
  SCHEMA.md:74-81 frames synthesis-may-not-invent as the *same* rule the product
  enforces on résumés, with `path:line` cites, `[[backlinks]]`, and `[synthesis]`
  tags as the falsifiability mechanism.
- Staleness is designed to be *measurable*, and the team resisted the easy lie:
  the 2026-06-09 docs-ingest deliberately **left `.last_ingest_sha` at the
  sentinel** (log.md:36-42) rather than falsely assert a code pass had run — a
  rot-detection discipline most wikis lack.
- D5 ("the contract lives elsewhere," SCHEMA.md:34-48) already states the
  one-job-per-doc principle the v1.0.7 extraction will enforce; the
  `governance-extraction.md` page records the design and its load-bearing safety
  condition (agents must keep rule-access via `@import`, page lines 45-52).
- `llms.txt` (root) gives an agent a clean front door pointing at the wiki map.

**Gaps / pointers:**
- **Egress doc drift (lead AL-7) is live and three-way.** SECURITY.md:57-59
  enumerates **three** network classes including "(c) any URL you explicitly
  paste as a job description"; vision.md:89-90 and README.md:127 enumerate
  **two** (Anthropic + scrape, no JD fetch). The charter (C-2 (iv), PX-03) rules
  no JD-URL fetch exists — `jd_url` is provenance metadata. So SECURITY.md
  asserts a destination the charter says is absent, and the three public docs
  disagree with each other.
- **Doc-vs-code drift, same class:** SECURITY.md:85 asserts "No external CDN is
  loaded at runtime," but `dashboard/templates/dashboard.html:15` loads Chart.js
  from `cdn.jsdelivr.net` (SRI-pinned). Charter C-2 (i) rules this a confirmed
  violation (fix v1.0.6, vendor). The scrape the docs describe is also dead code
  at `c6e0437` (C-2 (iii), PX-02) — docs describe a path that does not run.
- **WS-4b code pass not yet run.** `pages/` covers only the excellence-walk
  (docs-grounded); the code architecture is explicitly **not ingested**
  (index.md:39-45). The robustness of the grounding rule *at code-pass scale* is
  untested, and the `sha→HEAD` rot check has never fired.
- **D-6 progressive install gap.** `docs/install.md` folds the Chromium (~150 MB)
  step inline as a base prerequisite (install.md:26-30, 61-64), mixing a
  dev/PDF-render need into the user path. The eval-stack guide
  (`docs/eval-stack-install-guide`, the ~3.2 GB HF opt-in) is a Sprint 6.5
  deliverable that **does not exist yet** — its content lives only in
  `non-dependency-downloads.md` (the verified provenance table, page lines 34-81).

## 3. Rubric

- **BOOST** — a stranger lands in `docs/`, follows `llms.txt`/README→wiki, and
  reaches an accurate self-description with working `path:line` cites; the egress
  story is identical across SECURITY/vision/README *and* matches code; install
  docs disclose progressively (user path clean, eval-stack opt-in threaded).
- **KEEP** — the one grounding rule + `[synthesis]`/`path:line`/`[[backlinks]]`
  convention; the sentinel-honesty discipline (don't advance `.last_ingest_sha`
  past what was actually ingested); D5 cite-don't-restate; `llms.txt` front door.
- **FIX** — reconcile the egress enumeration to the two sanctioned classes across
  all three public docs (PX-03); vendor Chart.js so SECURITY.md:85 stops
  overclaiming (PX-01); ship the Sprint 6.5 eval-stack install guide; lift the
  Chromium step out of the base-user prerequisite framing.
- **DEBUFF** — any doc that asserts a capability code doesn't have (JD-URL fetch,
  live scrape, "no CDN") survives to v1.1.0; an absolute the charter's C-0 would
  bar ("never leaves the machine, ever" stated without the enumerable-destination
  qualifier that makes it verifiable).
- **WATCH** — WS-4b cold code-ingest: whether the grounding rule holds at module
  scale and whether `.last_ingest_sha` rot-detection actually fires post-ingest;
  whether governance extraction leaves *exactly one* home per rule (not a second
  copy); whether the support agent surfaces stale pages with provenance.

## 4. Sharpest questions

(Below — feeds the assessment question bank.)
