```toml
schema = 1
id = 14
kind = "item"
title = "No JD-identifying metadata anywhere in bootstrap/eval artifacts"
status = "closed"
resolution = "Fixed on feat/jd-provenance-metadata: hardening.extract_jd_label() deterministically derives a (title, company) label from a JD's own header text (sibling to extract_company_terms, which stays byte-identical to protect its baselined eval-scoring behavior). Stamped once per JD in evals/bootstrap.py (per_jd[].jd_label + a top-level jd_labels index), carried through evals/annotation.py's annotation template and expected.json (resolved for the anchor JD), and threaded onto all 7 eval-result record sites in evals/runner.py -- explicitly excluded from the 2 judge-input payloads (would change graded prompts, silently invalidating baseline_v1.json) and from fixture_hash (must stay a pure function of file bytes). Also surfaced in the bootstrap SSE done event/log line and the collate route's response/log, naming the anchor JD's label at exactly the moment item 13's mismatch would have been visible on sight. No schema-version bumps (additive field, mirroring item 13's own bootstrap_fingerprint precedent)."
decision_owner = "agent"
depends_on = [11]
refs = [
  "evals/results/20260728_164119Z.jsonl",
  "hardening.py:extract_jd_label",
  "evals/bootstrap.py:jd_labels",
  "evals/annotation.py:collate_expected",
  "evals/runner.py:_load_fixture",
]
summary = "Eval result records only fixture/fixture_hash, no JD name - had to open jd.txt prose to learn what a run graded."
```

Found 2026-07-28 (owner's own observation mid-session: "there is no
identifying information in the bootstraps, so I have no idea what JDs they
were run against"). `evals/results/*.jsonl` records `fixture`,
`fixture_hash`, `eval_mode`, `prompt_version`, etc. — no field names the JD
by title/company. Same gap in the bootstrap artifacts themselves: nothing
short of opening `jd.txt`'s raw prose tells you what job posting a given run
was against. Likely the same underlying fix as item 11 (a provenance-bearing
manifest/naming scheme for bootstrap runs) — a manifest field naming the
JD(s) per run would close both gaps together.

## Updates

### 2026-07-28 — filed during chore/work-item-tracking

### 2026-07-29 — item 11 closed; only partially overlaps with this item

Item 11's fix (`fix/bootstrap-annotation-overwrite`) adds RUN provenance — a
timestamped `bootstrap-<ts>.json` filename, surfaced as `bootstrap_file` in
the bootstrap SSE `done` event and the server log line. That answers "which
generation," not "which job posting": this item's actual gap (JD name/company
by title, in `evals/results/*.jsonl` and the bootstrap artifacts themselves)
is untouched. `depends_on = [11]` no longer applies mechanically (11 is
closed) — this item still needs its own manifest/naming work naming the JD(s)
per run.

### 2026-08-01 — item 13 closed; concrete motivating case for this item

Item 13 (`fix/eval-fixture-jd-annotation-mismatch`) closed a real fixture whose
`jd.txt` (Zoox) and `annotations.json` (100% Faros) described two different JDs —
undetectable without opening the raw JD prose, exactly this item's gap. That fix
added `bootstrap_fingerprint` to `annotations.json` (content-verification, not
identification) and a collate-time guard that rejects an unrepresented anchor, but
neither writes a human-readable JD name/company anywhere a person or a dashboard
could glance at. This item's own fix (a manifest field naming the JD(s) per run)
would have surfaced the original mismatch immediately, before any guard was needed
— worth weighing when this item is picked up. Not resolved by item 13; still open.

### 2026-08-01 — fixed and closed (`feat/jd-provenance-metadata`)

Added `hardening.extract_jd_label(jd_text) -> {"title": str, "company": str}`:
deterministic, bounded to the JD's first ~6 non-blank lines, reusing
`extract_company_terms`'s constants but scanning separately so that function's
eval-scoring behavior (baselined in `baseline_v1.json`) stays byte-identical.
Fail-open by design — a label is descriptive metadata, never a correctness
signal, and must never feed a fail-closed check (`ensure_anchor_covered_by_annotations`
stays keyed on `jd_file`, unchanged).

Wired through the whole chain: `evals/bootstrap.py` stamps `jd_label` on every
`per_jd` record plus a top-level `jd_labels` glanceable index;
`evals/annotation.py`'s `build_annotation_template` carries `jd_labels` straight
through (no re-derivation), and `collate_expected` resolves the anchor's own
label into `expected.json`; `evals/runner.py` computes the label once per
fixture in `_load_fixture` and stamps it onto exactly the 7 result-record write
sites — verified by direct inspection that the 2 judge-input-payload sites
(`_iteration_payload`, the main grading `payload`) do NOT carry it, with a
dedicated regression test capturing the actual payload sent to `_grade`.
`fixture_hash` is unaffected (bytes-only, unchanged). Surfaced in the bootstrap
SSE `done` event/log and the collate route's response/log (`anchor_jd_label`) —
the collate log is exactly the moment item 13's Zoox/Faros mismatch would have
been visible on sight, before any guard was needed.

No schema-version bumps anywhere: additive optional field, and `evals/runner.py`'s
`SCHEMA_VERSION` is used as an equality gate for baseline seeding — bumping it
would have silently disabled baseline comparison. New coverage across
`tests/test_hardening.py`, `tests/test_bootstrap.py`, `tests/test_annotation.py`,
`tests/test_eval_runner.py`, `tests/test_annotation_routes.py`. Full gate green.
