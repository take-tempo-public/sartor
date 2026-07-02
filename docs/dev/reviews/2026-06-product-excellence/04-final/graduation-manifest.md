---
status: review-artifact
evidence_sha: c6e0437
drift_checked_against: a0a1cb2
graduation: self (the integration plan of record)
---

# Graduation manifest — making the review canonical

> How the 2026-06 product-excellence review becomes part of sartor.
> Two output classes, two fates: the **evidence archive** merges as-is to a
> permanent home; the **durable doctrine** graduates into canonical docs via
> normal one-branch-per-item dev sessions, with the review as the cited
> source (extract-don't-restate, charter W-2 / F-gov-05). Graduation happens
> in dev sessions, **never inside the review**. Evidence pinned at `c6e0437`;
> reconciled against current main `a0a1cb2` in
> [`drift-check.md`](drift-check.md).

## Class A — the evidence archive (relocate + merge)

**Move** `review/2026-06-product-excellence/` →
`docs/dev/reviews/2026-06-product-excellence/` via `git mv` at merge time
(history-preserving). Verified: `review/` exists only on this branch (never
on main); `docs/dev/reviews/` does not yet exist on main, so the move
**creates** the `reviews/` home — the same home the compliance agent and
future reviews append to (this review is the prototype entry).

The archive stays pinned at `c6e0437`; drift is recorded in
`drift-check.md`, not by mutating the findings. The archive is read-once,
reference-later: it is the record of how the doctrine was derived, not live
doctrine itself.

Contents that travel as the archive: `00-interview/` (record, charter,
verification brief), `01-maps/`, `02-assessment/` (findings, register,
verification log), `03-prescriptions/`, `04-final/`. The gitignored
`output/review-session-state.md` does **not** travel (working file).

## Class B — durable doctrine (graduate via dev branches)

Each row: artifact → canonical destination → carrying branch → arc position
→ status. Drift-honored (see notes): nothing below is marked already-landed
because **no PX item had landed on main at `a0a1cb2`**.

| # | Artifact | Canonical destination | Carrying branch | Arc | Status |
|---|---|---|---|---|---|
| 1 | governance-draft/constitution.md | `docs/governance/charter.md` (creates `docs/governance/`) | `feat/governance-extraction` | v1.0.7 | ready |
| 2 | governance-draft/metrics-and-rubrics.md | `docs/governance/metrics.md` | `feat/governance-extraction` | v1.0.7 | ready |
| 3 | governance-draft/enforcement-practices.md | `docs/governance/enforcement.md` | `feat/governance-extraction` | v1.0.7 | blocked-on #1 (charter home) |
| 4 | extraction-playbook.md | `docs/dev/EXTRACTION.md` | `docs/extraction-playbook` | v1.0.7 | ready |
| 5 | compliance-agent-design.md | `docs/governance/compliance-agent.md` + `.claude-plugin/` agent + command | `feat/compliance-agent-pilot` | v1.0.7 pilot | blocked-on #1 (needs docs/governance/ to witness) |
| 6 | wiki-architecture-proposal.md | `docs/wiki/SCHEMA.md` audience-lint + `index.md` reserved user slot + WS-4b follow-ups | `feat/wiki-audience-lint` | v1.0.7 / WS-4b | partly-landed (audience-tag convention shipped, F-docs-07; lint gate + slot remain) |
| 7 | timeline-overlay.md | `RELEASE_ARC.md` post-public §, 4-lane frame | `docs/release-arc-overlay` | v1.0.7 | ready (proposal-only) |
| 8 | release-pass-plan.md | `RELEASE_CHECKLIST.md` G-1/G-2/G-3 gate additions | `docs/release-pass-gates` | v1.0.7 | ready |
| 9 | early-prescriptions PX-01..07 | `RELEASE_ARC.md` Phase 4.5 rows + fix branches | (per PX, see early-prescriptions.md) | now-v1.0.6 | ready, none landed |
| 10 | prescriptions PX-08..36 | `RELEASE_ARC.md` rows, per-PX | (per PX, named in prescriptions.md) | v1.0.6 → post-public (+1 reject) | banded, ready |

### Drift-honored scoping notes
- **No PX-01..09 landed** at `a0a1cb2` — the egress/CDN/scraper/no-invention
  spine is fully live; graduate all of it.
- **PX-11 / PX-12** coordinate with Sprint 6.6, which only brushed the
  surface: `F-vision-03` (outcome funnel) is **still-valid** in vision.md;
  `F-vision-06` (corpus ladder) is **partly-addressed** in PRODUCT_SHAPE →
  PX-12 narrows to the residual `vision.md:222-229` Learnings drift only.
- **PX-33's sources discharged:** the WS-4b ingest advanced the sentinel
  honestly (`F-docs-08`) and fired rot-detection at scale (`F-docs-10`), so
  PX-33 graduates as a **completed-cycle affirmation**; its live remainder is
  seed-overview-from-system-model (`F-vision-08`).
- The WS-4b ingest's rot-detection is **code-vs-symbol scoped** — it did
  **not** surface the egress/CDN/scraper **cross-document** drift the review
  found. That distinction is load-bearing: the wiki and the review are
  complementary instruments, not redundant. The cross-doc drift stays the
  review's to carry (PX-01/03/09, F-docs-01/04, F-sec-03/04).

## Integration sequence (post-wiki-ingest)

1. **WS-4b done** (merged at `a0a1cb2`) — wiki grounds on code; sentinel
   advanced; rot-detection fired. Cross-doc egress drift NOT caught.
2. **Review merge** — relocate `review/` → `docs/dev/reviews/…`, merge to
   main (owner-confirmed). The archive lands; nothing canonical changes yet.
3. **v1.0.6 prescriptions** — fold PX-01..14 into live v1.0.6 work: the
   egress falsifiability test (PX-08), Chart.js vendor (PX-01), scraper
   re-wire (PX-02), egress + no-invention doc corrections (PX-03/09), the
   cheap batch (PX-05/06/07). These close the live charter contradictions.
4. **v1.0.7 governance extraction** — `governance-draft/` → `docs/governance/`
   (rows 1–3); extraction-playbook → `docs/dev/EXTRACTION.md` (row 4).
5. **Wiki re-ingest (diff-driven)** picks up the new `docs/governance/` →
   the support agent can answer governance questions ("a product that knows
   itself" closes its loop).
6. **Compliance-agent pilot (v1.0.7)** — now has `docs/governance/` + wiki
   provenance to witness against (row 5). Its design names this review as
   its prototype run.

Shape: **code-knowledge (wiki) → governance-knowledge (extraction) →
re-ingest → the agent that reads both (compliance).** The review feeds
steps 2–6.

## Graduation discipline

- One branch per item (house rule); the review is the **cited source**, not
  a parallel truth. Each carrying branch references the review artifact and
  marks every delta from the current doc.
- The governance-draft is the **first draft of the v1.0.7 extraction**, not
  a competing rulebook — there is never a moment with two governance truths.
- The prescriptions name their own landing spots; RELEASE_ARC integration is
  a copy-from-the-table, not a re-derivation.
