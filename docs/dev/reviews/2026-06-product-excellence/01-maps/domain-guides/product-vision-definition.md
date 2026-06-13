---
status: review-artifact
evidence_sha: c6e0437
graduation: none (rubric portions are v1.0.7 governance candidates)
---

# Domain Guide — Product vision & definition

> The lens for whether callback. *knows what it is*, states it
> falsifiably, and holds that statement consistently across the docs a
> reader meets. The charter ([product-charter.md](../../00-interview/product-charter.md))
> is the severity anchor; this guide reads the public vision docs against
> it. The verification brief's [C1–C11](../../00-interview/round2-verification-brief.md)
> already maps most doc-vs-charter drift — this guide builds on that map
> rather than re-deriving it.

## 1. What mastery means here

For *this* product, a mastered vision is not a marketing pitch — it is a
**falsifiable identity** that a skeptical engineer (A-4's "whoa, this is
robust") can check against the code and find true. Mastery has four
shapes, each charter-anchored:

- **Identity is stated, bounded, and load-bearing (P-1, P-2, C-1).**
  "Local and yours" is the spine; the docs name it plainly, without
  marketing register, and every constraint traces to it. Best practice
  (a product "north star") asks only that the statement exist; the
  charter asks more — that it be *enforced by construction* where it
  can be (C-0): categorical claims only where a deterministic test backs
  them (egress, module boundary, template properties), and
  mechanism-and-effort language everywhere LLM behavior is involved.
- **Claims are tiered by enforceability, not flattened (C-0, C-8 via
  brief C8).** The owner holds only two constraints truly inviolable
  (the egress enumeration C-2, the deterministic boundary C-6); a
  mastered vision doc must not present all ~12 self-imposed constraints
  as one uniform "won't-cross" tier.
- **Success is named where it can be measured (P-4, M-1).** Interviews
  are the reward and the measure — and the product's literal name. A
  mastered definition says so *as a success criterion*, honestly scoped
  to what C-2/T-A let the project observe (the user's instance, never
  the aggregate).
- **The thesis is still the thesis (PRODUCT_SHAPE Corpus-Item ladder).**
  Mastery means the load-bearing architectural pattern is either still
  converging or consciously re-dispositioned — not silently stalled.

The charter outranks generic best practice wherever they differ (e.g.
best practice tolerates aspirational absolutes; C-0 forbids them).

## 2. Current state pointers

**Strengths — name them first.** The identity is genuinely crisp and
non-marketing: vision.md states "one person, one machine, one job at a
time" (`vision.md:42@c6e0437`) and the three priority goals are ordered
and concrete (`vision.md:48-71`). The `system-model.md` self-model is a
real asset — the seven-functions + one-law framing
(`docs/system-model.md:60-126`) gives the "whoa, robust" reader (A-4) an
unusually legible map, and it already flags its own honesty seams
(`docs/system-model.md:148-164`). The no-invention thesis is consistent
and load-bearing across vision, system-model, and the charter (C-3).
The Corpus-Item ladder is documented with rare discipline — the
asymmetry matrix (`docs/PRODUCT_SHAPE.md:31-42`) is a falsifiable
diagnosis, not a slogan.

**Gaps (building on C1–C11, not repeating).**
- **Claims-tier flatness (brief C8).** vision.md's "Self-imposed
  constraints" (`vision.md:76-175`) reads as one uniform won't-cross
  tier; C-0/C-8 want explicit tiering (machine-enforced-inviolable vs
  default-negotiable). This is the single largest vision-doc divergence
  from the signed charter.
- **Success-metric absence (brief C6).** Interviews (P-4/M-1) appear in
  vision as Goal framing only via "callback." the name; the
  outcome loop is documented as a *deferred v2 feature*
  (`docs/PRODUCT_SHAPE.md:133-139`, "Mark sent"), never as a stated
  success criterion. The charter elevates it; the public docs do not yet.
- **ATS escape-hatch wording (brief C4).** C-5 grants a real escape
  hatch ("users who want non-ATS output edit the document they
  produced"); vision.md frames ATS-safety categorically — heading
  "ATS-safety is the product" (`vision.md:250-259`) and a flat
  retirement rule (`vision.md:57-63`) — with no hatch named.
- **Corpus-Item ladder post-Phase-4.5 staleness.** The ladder's stage
  labels are explicitly superseded (`docs/PRODUCT_SHAPE.md:410-417`) and
  re-dispositioned (§10), but vision.md's Learnings still describe the
  v1.1/v1.2 extension as forward-looking (`vision.md:222-229`) — a
  vision/shape drift worth a decidable check (Q4 below).

## 3. Rubric (BOOST / KEEP / FIX / DEBUFF / WATCH)

- **BOOST** — A vision change that makes the identity *more falsifiable*:
  tiers constraints by enforceability (C-0/C-8), or ties a stated success
  criterion to a mechanism the user's own instance can observe (M-1).
  Adding the egress two-class enumeration verbatim everywhere counts.
- **KEEP** — The crisp non-marketing identity sentence; the ordered
  three goals; the `system-model.md` seven-functions self-model with its
  visible honesty seams; the Corpus-Item asymmetry matrix as the
  diagnosis of record. Do not "improve" these into pitch copy (C-0).
- **FIX** — A doc that overstates the constitution (flat won't-cross
  tier, brief C8) or under-states success (interviews absent as a
  criterion, brief C6) or contradicts a granted escape hatch (ATS, brief
  C4). These are doc-vs-signed-charter conflicts with a known landing.
- **DEBUFF** — Any new vision claim in absolute register that rests on
  LLM behavior ("never invents", "always grounded" as guarantees rather
  than mechanism+effort). C-0 is explicit; the charter signed it.
- **WATCH** — Audiences the charter admits but docs omit (A-5
  wanted-but-blocked ATS integration; the power-user→dev continuum A-2;
  builders A-3). Not yet a conflict if scoped as future, but drift-prone
  as the public release nears (brief C5).

## 4. Sharpest questions

These feed the assessment question bank; each is decidable against named
evidence.

1. Does any public-facing vision doc tier its self-imposed constraints by
   enforceability (machine-inviolable vs negotiable-default), or are they
   presented as one uniform "won't-cross" set?
2. Is "an interview from a callback-written resume" stated anywhere as a
   *success criterion* (not only as a deferred v2 "Mark sent" feature)?
3. Does the ATS framing carry the charter's escape hatch (edit the
   produced document for non-ATS needs), or is it stated categorically
   with no hatch?
4. Is the Corpus-Item ladder still the load-bearing thesis after Phase
   4.5 — converging on schedule, or re-dispositioned — and does
   vision.md's Learnings agree with PRODUCT_SHAPE's current disposition?
5. Where would portfolio polish (A-4 "whoa, robust") tempt a vision claim
   that conflicts with function or with C-0 — e.g. an absolute
   no-invention guarantee instead of mechanism+effort?
6. Do the charter-admitted audiences (A-5 blocked-ATS integration, A-2
   continuum, A-3 builders) appear in the public identity, or does "one
   person, one machine, one job at a time" structurally exclude them?
