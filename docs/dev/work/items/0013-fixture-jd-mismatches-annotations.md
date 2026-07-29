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
