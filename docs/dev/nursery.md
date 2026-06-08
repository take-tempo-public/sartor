# Feature Nursery — callback.

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

---

## Retired (cut — kept as a one-line record)

- **Dockerfile / docker-compose** *(cut 2026-06-08)* — no Docker in use, no demand;
  `pip install -e .` + `python app.py` works. Re-introduce only if a real user asks.
- **Cross-candidate insights** *(non-goal, not nursery)* — impossible by design
  (local-first, single-tenant). Lives in `SECURITY.md` as a **privacy guarantee**,
  not a backlog item. Do not re-add as a feature.
