# Feature Nursery — sartor.

> **Purpose:** a tracked holding bed for *possible future features* — "good idea,
> not now." Each entry is a 1–3 sentence what/why plus value/effort/risk tags and a
> status. We **review it together periodically** and watch for ideas that have
> **fallen out of favor** (retire) or **risen in value** as the project evolves
> (promote into a scheduled epic sprint). Nothing here is committed work; nothing
> orphaned is lost.
> **Audience:** humans + LLM agents planning future epics.
> **Authoritative for:** the deferred-but-alive idea set and its current scoring.
> **Siblings:** [`RELEASE_ARC.md`](RELEASE_ARC.md) (scheduled work),
> [`../PRODUCT_SHAPE.md`](../PRODUCT_SHAPE.md) (product shape),
> [`excellence-walk/`](excellence-walk/) (where several of these were first captured).

**Tag legend.** **Value / Effort / Risk** = H/M/L. **Status** = `idea` (ready to
weigh) · `blocked: <what>` (a precondition must clear first) · `needs-data` (waiting
on accumulated real usage). **Added** = date first parked.

**Lifecycle.** idea → (review raises value / clears block) → **promote** to a
scheduled sprint in an epic (move the entry to `RELEASE_ARC.md`, delete it here) ·
or → (review lowers value) → **retire** (cut, with a one-line why).

---

## Active nursery

### 1. Compose-overrides-compound — the corpus learns from your curation
*Value H · Effort M · Risk L · Status: needs-data · Added 2026-06-08*

If you pin the same bullet across several similar JDs, the corpus should *notice*
and propose making it a default-include for that JD class — so repeated manual
curation compounds into a standing signal instead of being re-done each time.
*Source: PRODUCT_SHAPE §2.6/§8. The flagship nursery idea (#1).* Naturally pairs
with outcome data (B.8 Part 2) once that lands.

### 2. Master-résumés surfacing
*Value M · Effort M · Risk L · Status: idea · Added 2026-06-08*

A "Masters" Library sub-tab + an `is_master` `ApplicationRun` + new-application
pre-seed, so a curated set per role tag ("Design IC", "PM") can be reused.
*Note: the `is_default` template **resolver is already wired** ([app.py:2082](../../app.py)) —
only the surfacing UX remains, which is why this is nursery, not a bug.*

### 3. `recommend_template` per JD class
*Value M · Effort M · Risk L · Status: blocked: outcome data (B.8 Part 2) · Added 2026-06-08*

A Haiku call that suggests which persona template fits a JD's inferred role class.
Low value without outcome data (it reduces to scoring template metadata); becomes
worthwhile once "this template + this JD class → interview" signal exists.
*Source: PRODUCT_SHAPE §8/§10.*

### 4. `CoverLetterChunkItem` — reusable cover-letter paragraphs
*Value L–M · Effort M · Risk L · Status: idea · Added 2026-06-08*

Cover letters are write-only today (asymmetry #2). This makes their parts
(intro / why-them / why-me / close) curatable Corpus Items so generation pulls from
reusable chunks. *Coherent extension of the Corpus-Item pattern, but low personal
priority — the primary user rarely uses cover letters (PRODUCT_SHAPE §5.1).*

### 5. Template field-filter chips (Step-4 chooser)
*Value L · Effort L · Risk L · Status: blocked: ≥3 owned templates across ≥2 role tags · Added 2026-06-08*

Chips above the source chips to filter templates by role tag. Pointless until the
template set has meaningful role-tag coverage — "chips with one template each is
worse UX than no chips." *Source: PRODUCT_SHAPE §10.*

### 6. Corpus-groomer LLM — dedup / tighten on demand
*Value H · Effort H · Risk M · Status: blocked: outcome data (B.8 Part 2) · Added 2026-07-08*

An on-demand LLM pass over the whole corpus that dedups and tightens bullets,
skills, titles, and summaries — proposing merges where two bullets say the same
thing at different quality levels, combining them into one stronger bullet rather
than leaving both. Leverages interview-outcome data (once B.8 Part 2 lands) to
find dedup targets: bullets that never contributed to a callback are the cheapest
candidates to fold into a stronger neighbor. Same human approve/deny gate as every
other corpus-mutating proposal (`is_pending_review`) — never auto-applies.
*Owner post-1.1.0 walkthrough idea.*

### 7. ATS-provider ingest research + optimization
*Value M · Effort H · Risk L · Status: blocked: owner's NVIDIA Workday sample artifacts analysis · Added 2026-07-08*

Research how the major ATS intake systems (Workday, SmartRecruiters/SAP,
Greenhouse) actually parse an uploaded résumé, and tune output structure/format
so it survives that pipeline intact — a real-world complement to the existing
`scrub_ats_unsafe()` character-level scrub. A concrete starting point already
exists: the owner has a real Workday-choke sample (their own NVIDIA application
artifacts) demonstrating a parse failure against a live provider, which should be
the first thing analyzed once this is picked up. *Owner post-1.1.0 walkthrough
idea.*

### 8. Job-title laddering agent
*Value M · Effort H · Risk L · Status: idea · Added 2026-07-08*

A specialized agent that suggests alternative title phrasings for a role, laddered
the way recruitment/ATS systems expect (jr → sr → staff, and adjacent lateral
titles), so a candidate's actual title can be reframed toward the JD's leveling
language without misrepresenting the role. Needs deep research into how ATS
title-matching / leveling actually works before the agent's rules can be trusted;
not a quick prompt-only addition. *Owner post-1.1.0 walkthrough idea.*

### 9. Owner's template as a bundled template + a clean ATS template set
*Value M · Effort M · Risk L · Status: idea · Added 2026-07-08*

Bundle the owner's own résumé template as a selectable persona template (it's
already proven through real use), and alongside it build a set of very clean,
tightly-spaced single-column ATS templates pitched at different experience
levels (junior / mid / senior+), each offered with and without a role-summary
block, so a candidate can pick the closest fit instead of one generic default.
*Owner post-1.1.0 walkthrough idea.*

### 10. STAR/CAR bullet-construction assistance
*Value M · Effort M · Risk L · Status: idea · Added 2026-07-08*

The Compose bullet editor already has a STAR/CAR **format picker**, but no
guided construction — the candidate still has to write the Situation/Task/
Action/Result (or Context/Action/Result) content themselves with no scaffolding.
An assisted mode would prompt for each component in turn (grounded in the
candidate's own corpus/clarifications, same no-invention discipline as every
other drafting call) and assemble the finished bullet. *Owner post-1.1.0
walkthrough idea.*

---

## Retired (cut — kept as a one-line record)

- **Dockerfile / docker-compose** *(cut 2026-06-08)* — no Docker in use, no demand;
  `pip install -e .` + `python app.py` works. Re-introduce only if a real user asks.
- **Cross-candidate insights** *(non-goal, not nursery)* — impossible by design
  (local-first, single-tenant). Lives in `SECURITY.md` as a **privacy guarantee**,
  not a backlog item. Do not re-add as a feature.
