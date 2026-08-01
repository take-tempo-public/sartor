```toml
schema = 1
id = 13
kind = "item"
title = "Collate picks an anchor jd.txt that doesn't match its own fixture's annotations"
status = "closed"
resolution = "Item's own filed mechanism (pick_anchor_jd's widest-cluster-span heuristic) falsified 2026-08-01 (fix/eval-fixture-jd-annotation-mismatch): the bootstrap doc it actually read was single-JD, Zoox-only (31 clusters, all zoox) -- there was no wrong choice to have made. The annotations (32 bullets, all Faros) were built from a different bootstrap that no longer existed under that name, most likely overwritten in place by item 11's pre-fix collision bug. Two real defects fixed instead, both capability-proven via new RED-then-GREEN tests: (1) item 11's bootstrap_source pin trusted path existence, never content -- now fingerprinted, fails closed on a mismatch; (2) nothing checked collate's anchor JD was represented in the annotation data it was collating alongside -- now a fail-closed guard (evals.annotation.ensure_anchor_covered_by_annotations) in both the CLI and the route (409 on mismatch). pick_anchor_jd itself is untouched -- proven not the defect; its own existing tests pass unmodified."
decision_owner = "agent"
depends_on = [11]
refs = [
  "evals/fixtures/real/robert-bootstrap/jd.txt",
  "evals/fixtures/real/robert-bootstrap/annotations.json",
  "docs/dev/diagnosis/eval-fixture-jd-annotation-mismatch.md",
  "evals/annotation.py:611-660",
  "blueprints/diagnostics.py:120-165",
]
summary = "Fixture's jd.txt (Zoox) has zero overlap with annotations.json's 32 bullets (100% Faros) - eval graded the wrong target."
```

Found 2026-07-28, downstream of item 11's overwrite bug. The
`robert-bootstrap` fixture's `jd.txt` (Collate's chosen anchor JD) is the
Zoox posting — confirmed by content and independently by the eval judge's
own reasoning, which extensively quotes Zoox-specific language. But every
one of the fixture's 32 annotated bullets in `annotations.json` is tagged
only `Faros`. So the eval that ran against this fixture graded the
pipeline's Zoox-targeted output using `expected.json`, while the
human-vetted ground truth underneath it is Faros-only data — the eval is
not testing what it claims to test. Collate's anchor-JD selection needs to
validate/derive from what's actually represented in the annotation data, not
pick independently from whatever's left in `jds/`.

## Updates

### 2026-07-28 — filed during chore/work-item-tracking

### 2026-07-29 — item 11 closed; this item is NOT resolved by that fix

Checked during item 11's fix on `fix/bootstrap-annotation-overwrite`:
`pick_anchor_jd`'s widest-cluster-span heuristic (`evals/annotation.py:587-606`)
is unchanged. Item 11 only guarantees collate reads the exact bootstrap
version an annotation was built from — it says nothing about whether that
bootstrap's anchor-JD choice matches what the annotation data actually
covers when a bootstrap run spans multiple JDs. Still needs its own fix:
validate/derive the anchor from JD coverage in the annotation data itself,
not independently from cluster span. `depends_on = [11]` no longer applies
mechanically (11 is closed) but the design dependency (11's provenance-pinning
was a precondition for reasoning about this correctly) is satisfied.

### 2026-08-01 — investigated, provenance corrected, fixed, closed (`fix/eval-fixture-jd-annotation-mismatch`)

**Provenance correction to this item's own description above:** the filed mechanism
— `pick_anchor_jd`'s widest-cluster-span heuristic choosing the wrong JD out of a
multi-JD bootstrap — is **falsified**. Direct measurement against the real
`robert-bootstrap` artifacts: the `bootstrap.json` `pick_anchor_jd` actually reads
is single-JD, Zoox-only (`jd_count: 1`, 31 bullet clusters, all tagged zoox). There
is no other JD in that document to have chosen instead — returning Zoox given that
input is correct behavior, not a heuristic failure. The `annotations.json` (32
bullets, all Faros) is structurally incompatible with that bootstrap (31 ≠ 32,
disjoint JD tags) — it was built from a *different* bootstrap that no longer exists
under that name, consistent with item 11's documented pre-fix overwrite bug. Same
drift shape items 30 and 31 each independently found — a filed item's mechanism
grew more specific than its evidence supports, and every downstream copy (the
board, this item's own original summary line) inherited it verbatim. Third
recurrence of this pattern; see `[[feedback-trace-stated-mechanism-to-original-citation]]`.
Full measurement trail: `docs/dev/diagnosis/eval-fixture-jd-annotation-mismatch.md`.

**What was actually still live**, both capability-proven via new tests that fail on
pre-fix `HEAD` and pass after: (1) `_resolve_bootstrap_path` (item 11's own fix)
trusted a pinned `bootstrap_source` path on existence alone, never content — a path
overwritten in place (the pre-item-11 collision shape) still resolved silently; (2)
nothing anywhere cross-checked that collate's anchor JD was represented in the
annotation data it was collating alongside, independent of *how* the wrong
bootstrap got read.

**Fix (two independent, fail-closed changes, `pick_anchor_jd` untouched by
design):** `build_annotation_template` now stamps a `bootstrap_fingerprint`
alongside `bootstrap_source`; `_resolve_bootstrap_path` (split into
`_resolve_bootstrap_pin`, `blueprints/diagnostics.py:120-165`) verifies content
against it and returns `None` on mismatch instead of substituting the newest
`bootstrap-*.json`. `evals.annotation.ensure_anchor_covered_by_annotations`
(`evals/annotation.py:611-636`) refuses to collate when the anchor isn't
represented in the annotation data, wired into both `_cmd_collate` (CLI,
non-zero exit) and `annotation_collate` (route, 409 + detail).

**Honest scope of the claim:** this closes two real, demonstrated gaps with the
same shape as the artifact that triggered this item — it does not claim certainty
about the artifact's exact history (offered only as `## Inferred`, not asserted as
fact), since no log survives from whichever run originally overwrote the Faros
bootstrap. `tests/test_annotation.py:539-558` (`pick_anchor_jd`'s existing unit
tests) pass unmodified — the proof that fixing the real defects required no change
to the function this item originally blamed. Full gate green, zero reruns.

**Filed forward:** item 14 (no JD-identifying metadata in eval artifacts) would
have made this specific mismatch visible at a glance — noted in its own file, kept
as a separate item per one-item-per-branch discipline.
