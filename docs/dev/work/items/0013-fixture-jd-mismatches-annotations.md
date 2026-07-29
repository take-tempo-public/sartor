```toml
schema = 1
id = 13
kind = "item"
title = "Collate picks an anchor jd.txt that doesn't match its own fixture's annotations"
status = "open"
decision_owner = "agent"
depends_on = [11]
refs = ["evals/fixtures/real/robert-bootstrap/jd.txt", "evals/fixtures/real/robert-bootstrap/annotations.json"]
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
