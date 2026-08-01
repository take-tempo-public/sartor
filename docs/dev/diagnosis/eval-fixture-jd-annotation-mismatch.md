# Diagnosis — eval fixture's `jd.txt` describes a different JD than its `annotations.json` ground truth

> **Status:** root cause PROVEN — item 13's own filed mechanism is FALSIFIED; the real
> defect is a different, still-live gap in item 11's bootstrap-pinning fix.
> **Branch:** `fix/eval-fixture-jd-annotation-mismatch`

---

## Symptom

Item 13 (filed 2026-07-28, `docs/dev/work/items/0013-fixture-jd-mismatches-annotations.md`):
the `robert-bootstrap` real-suite eval fixture's `jd.txt` is a Zoox posting, but every
one of `annotations.json`'s 32 human-annotated bullets is tagged only `Faros`. The eval
judge's own reasoning extensively quotes Zoox-specific language while grading against
Faros-derived `expected.json` — the eval is not testing what it claims to test.

The filing attributes this to `pick_anchor_jd`'s widest-cluster-span heuristic
(`evals/annotation.py:587-606`) and prescribes: "Collate's anchor-JD selection needs to
validate/derive from what's actually represented in the annotation data, not pick
independently from whatever's left in `jds/`."

---

## Observed

The candidate's real bootstrap/annotation fixture data (kept out of this repo per
`.gitignore:57`, `evals/fixtures/real/*`) was inspected directly this session. All
values below are direct measurements, reproducible against those artifacts:

**O-1. `jd.txt`'s content is byte-identical to the Zoox JD file, not the Faros one.**

```
jd.txt sha256[:12]                          868307b31f94
jds/zoox-sr-mngr-exp-prod-dsn.txt sha256[:12] 868307b31f94   <- match
jds/Faros_-_Product_Manager_..._.txt sha256[:12] fc9927d5a5d6
```

Confirms the filing's premise: the anchor genuinely is Zoox.

**O-2. The bootstrap doc that `pick_anchor_jd` would run against today is a
single-JD, Zoox-only bootstrap — not a multi-JD bootstrap with a Zoox-majority span.**

```python
bootstrap.json:
  jd_count: 1
  per_jd: ['zoox-sr-mngr-exp-prod-dsn']
  bullet clusters: 31
  cluster jd_files span: {'zoox-sr-mngr-exp-prod-dsn': 31}   # every cluster, all zoox
  generated_at: 2026-07-28T14:36:45.447060+00:00
```

`pick_anchor_jd(bootstrap_doc)` on this document can only ever return
`'zoox-sr-mngr-exp-prod-dsn'` — there is no other JD in its cluster set to weigh
against it. Handed this bootstrap, the function's output is not a bug; it is the only
value the widest-cluster-span heuristic *can* produce.

**O-3. `annotations.json` does not match this bootstrap at all — different cluster
count, disjoint JD tags.**

```python
annotations.json:
  bullets: 32   (bootstrap has 31 clusters — 31 != 32)
  bullet jd_files distribution: {('Faros - Product Manager, AI Native Initiatives',): 32}
  bootstrap_source: <path to the fixture's own bootstrap.json>
```

Every one of the 32 annotated bullets is tagged only Faros — zero overlap with the
Zoox-only bootstrap `pick_anchor_jd` actually read. `build_annotation_template`
(`evals/annotation.py:443-492`) emits exactly one bullet entry per bootstrap cluster,
1:1, with `jd_files` copied verbatim from the cluster (`_bullet_item_template`,
`evals/annotation.py:409`). A 32-bullet, all-Faros annotations.json is therefore
structurally impossible to have been built from the 31-cluster, all-Zoox
`bootstrap.json` that exists today. It was built from a **different, Faros** bootstrap
that no longer exists under that name — consistent with item 11's documented overwrite
bug (`docs/dev/work/items/0011-bootstrap-overwrite-destroys-annotations.md`): a bootstrap
re-run for the same candidate silently replacing a prior run's `bootstrap.json` before
item 11's fix (merged `fix/bootstrap-annotation-overwrite`) introduced collision-free
`bootstrap-<timestamp>.json` naming.

**O-4. `annotations.json`'s `bootstrap_source` field currently resolves to a file that
still exists and still holds the wrong (Zoox) content — item 11's provenance pin does
not detect this.**

`_resolve_bootstrap_path` (`blueprints/diagnostics.py:120-143`) reads
`annotations.json`'s `bootstrap_source`, and returns that path unmodified as soon as
`pinned.exists()` is true (`:137`) — no check that the file's *content* still matches
what the annotation was built from. In this fixture, the pin's target is the legacy
mutable `bootstrap.json` mirror, which the Zoox bootstrap run overwrote in place
(pre-item-11 behavior). The path exists, so the pin is trusted, so re-resolving today
reads Zoox content for Faros-keyed annotations — reproducing the exact mismatch the
item complains about, on the current `main`, independent of `pick_anchor_jd`.

**O-5. No code anywhere cross-checks a fixture's `jd.txt` against its `expected.json`
or the annotation data it was collated from.** Confirmed by repo-wide search:
`validate_annotations` (`evals/annotation.py:234-266`) checks schema/verdict/regex
shape only, never JD identity; `collate_expected` (`:518-579`) never inspects the
anchor; `_cmd_collate` (`:820-874`) and the `annotation_collate` route
(`blueprints/diagnostics.py:344-420`) each check only that the anchor JD *file exists
on disk* (`anchor_src.is_file()` / `.exists()`), never that it's represented in the
annotation data being collated alongside it. `_load_fixture`
(`evals/runner.py:163-196`) performs no cross-validation either.

---

## Falsified

**Item 13's own filed mechanism: `pick_anchor_jd`'s widest-cluster-span heuristic
picked the wrong JD out of a multi-JD bootstrap.** Directly contradicted by O-2: the
bootstrap the function actually reads today is single-JD, Zoox-only — there is no
"wrong JD it picked over a right one" to have chosen instead. Given this input,
returning Zoox is correct behavior, not a heuristic failure. This is the same drift
shape items 30 and 31 each independently found and is now the **third** recurrence:
a filed item's mechanism grew more specific than its evidence supports, and every
downstream copy (the board, this item's own summary line) inherited the unsourced
claim verbatim. See `[[feedback-trace-stated-mechanism-to-original-citation]]`.

Also considered and ruled out: that the "100% Faros" summary in the filing was itself
imprecise. O-3's raw distribution (`{('Faros...',): 32}`, no other key) confirms it was
accurate — the annotation data really is 100% Faros. What was wrong was attributing
the mismatch to the anchor-picking *heuristic* rather than to *which bootstrap document
it was fed*.

---

## Inferred

The most likely history (not directly observed, offered for context only): an initial
Faros bootstrap run produced the `bootstrap.json` that `annotations.json` was built
against and fully hand-annotated; a later Zoox bootstrap run for the same candidate
slug overwrote that same `bootstrap.json` in place (item 11's pre-fix overwrite
behavior); collate then read the now-Zoox bootstrap, `pick_anchor_jd` correctly
reported Zoox as its sole JD, and `expected.json`/`jd.txt` were written from
mismatched sources with nothing to catch it. This history is not needed for the fix
below — the two defects that make it possible (O-4, O-5) are independently provable
without knowing exactly how this specific artifact arose.

---

## Falsification

**Experiment:** a regression test that collates an `annotations.json` whose bullets'
`jd_files` are entirely disjoint from the anchor `pick_anchor_jd` would select from the
paired `bootstrap.json` (mirroring O-2/O-3's measured shape: annotations covering JD
"A" only, bootstrap containing only JD "B" clusters). On current `main` this **must
pass** (collate succeeds silently, writing a mismatched fixture) — that passing-when-it
-should-fail result is itself the proof of O-5's gap, parallel to how O-4 is provable by
constructing an annotation pinned to a `bootstrap_source` file whose content is then
replaced and confirming resolution still returns it unchanged.

- **If collate succeeds silently on HEAD:** O-5 confirmed — build the fail-closed
  guard (Fix 2).
- **If content-swap-then-resolve still returns the stale-content path on HEAD:**
  O-4 confirmed — build the fingerprint check (Fix 1).

**Run against HEAD this session** (`tests/test_annotation_routes.py`,
`TestCollate::test_rejects_anchor_not_represented_in_annotations` and
`TestBootstrapPinIntegrity::test_stale_pin_content_is_not_silently_reused`):

```
FAILED ...test_rejects_anchor_not_represented_in_annotations - assert 200 == 409
FAILED ...test_stale_pin_content_is_not_silently_reused - AssertionError: pin
  target's content no longer matches the fingerprint ... assert WindowsPath(
  '.../alice-bootstrap/bootstrap.json') is None
```

Both RED, both for the documented mechanism: collate returned `200` and wrote a
mismatched fixture instead of rejecting it (O-5); `_resolve_bootstrap_path` returned
the swapped-content path unchanged instead of `None` (O-4). O-4 and O-5 are now
executable, not just read, observations.

---

## The fix

Two independent, fail-closed changes — `pick_anchor_jd` itself is untouched, since O-2
proves it is not the defect:

1. **Fingerprint the bootstrap pin** (closes O-4): `annotations.json` stamps a content
   fingerprint of the bootstrap doc it was built from; `_resolve_bootstrap_path`
   verifies the resolved file's current content against it and refuses to return a
   pin whose target has silently changed, instead of trusting path-existence alone.
2. **Fail-closed collate-time consistency guard** (closes O-5): collate refuses to
   write a fixture whose anchor JD is not represented in the annotation data it is
   collating, in both the CLI (`_cmd_collate`) and the route
   (`annotation_collate`) paths.

---

## Acceptance bar

- The falsification tests above are added, run RED against pre-fix code (captured in
  this same first commit's evidence, not asserted from memory), then pass after Fix 1
  + Fix 2 land — an A/B, not a single post-fix green run.
- `tests/test_annotation.py:539-558` (existing `pick_anchor_jd` unit tests) pass
  **unmodified** — the proof that fixing the real defects required no change to the
  function item 13 originally blamed.
- Full gate (`python -m scripts.gate`) green, no reruns.
- Item 13's own filing corrected in its `## Updates` section to name the actual
  mechanism (O-2 through O-5), then closed.
