"""Blast-radius classification — the single source of truth for "is this path a schema,
a shared contract, or a widely-consumed helper."

**Why this exists.** Changing something many sites depend on, without first enumerating
those sites, is a recurring and expensive failure here — and every time, a *person*
caught it, never a mechanism:

- `docs/dev/diagnosis/compose-unawaited-reloads.md`: commit `be48fec` fixed the
  un-awaited `loadComposition()` contract at **5 call sites**; a later session's grep
  found **9 more** untouched (Fact 3), 3 further sites deliberately excluded (Fact 5),
  and `RELEASE_CHECKLIST.md`'s own enumeration of what remained was stale in *both*
  directions — naming a site already fixed, omitting 2 that were not (Fact 4).
- `docs/dev/diagnosis/extract-experiences-telemetry-pollution.md` (item 33): call sites
  that never redirected telemetry.
- `docs/dev/RELEASE_ARC.md` sprint A1's brief carries a hand-written instance of the
  rule ("audit every unfiltered `Experience` consumer ... decide-and-document each
  site") — added as an *adversarial-review amendment*, i.e. the standing guidance did
  not surface it; a reviewer did.

Charter **C-10**. Enforced by `guards/require_consumer_enumeration.py` over
`docs/dev/blast-radius/<branch-slug>.md`.

**Design, mirrored from `scripts/wiki_relevance.py`** (itself mirrored from
`tests/test_egress_allowlist.py`'s `SANCTIONED_EGRESS_FILES`) — the house pattern for a
maintained classification list that cannot silently rot. Three buckets, and the third is
the load-bearing one:

1. `GATED` — editing this is almost always a contract change, so the gate fires.
2. `ACKNOWLEDGED_NOT_GATED` — high fan-in, but **deliberately** not gated, each with a
   written reason. `analyzer.py` is the archetype: 13 first-party importers, but its
   edits are overwhelmingly prompt-text changes already governed by `PROMPT_VERSION`
   discipline and eval telemetry. Gating it would make the rule noise, and a rule that
   is noise gets worked around.
3. Everything else — must stay *below* the fan-in threshold. `tests/test_blast_radius_
   classification.py` fails the moment a module crosses it without appearing in bucket 1
   or 2, so a newly-widely-consumed helper forces a conscious decision instead of
   silently defaulting to ungated.

**A path-level classifier is deliberately coarse.** It cannot tell a signature change
from a comment fix inside the same file. That trade is intentional: the alternative —
inferring change-shape from an `Edit` payload — is fragile in the direction that
matters (it would fail *open*). Coarse-but-honest beats clever-but-silently-wrong, and
the escape is always the same and always available: write the enumeration down.

**Known limit (C-0, stated not papered over):** the computed offenders check covers
first-party **Python** imports only. JS (`static/app.js`), Jinja templates and CSS are
curation-only — a widely-consumed JS helper will not be auto-detected. The
`loadComposition()` incident that motivates this module is itself in that blind spot;
`static/app.js` is not gated because it is one 8000-line file whose every edit would
trip the gate. Narrowing that is future work, not a solved problem.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Minimum first-party **non-test** importers for a Python module to count as
#: "widely-consumed" for the offenders audit. Calibrated against the measured
#: distribution (see the dossier for this module's own branch): 8 puts the cut just
#: below `json_resume.py`/`db/build_context.py` and well above the long tail.
FAN_IN_THRESHOLD = 8


@dataclass(frozen=True)
class Surface:
    """One classified blast-radius surface."""

    path: str
    kind: str  # "schema" | "contract" | "helper"
    why: str


def _s(path: str, kind: str, why: str) -> tuple[str, Surface]:
    return path, Surface(path=path, kind=kind, why=why)


#: Exact repo-relative POSIX paths the gate fires on.
GATED: dict[str, Surface] = dict(
    (
        # --- schema: a shape other code and stored data depend on -------------------
        _s(
            "db/models.py",
            "schema",
            "ORM schema; 27 non-test importers. A column added or a default changed "
            "ripples into every query, every migration, and stored rows.",
        ),
        _s(
            "recall/models.py",
            "schema",
            "candidate-memory schema; 12 non-test importers.",
        ),
        _s(
            "evals/schemas/context_set.schema.json",
            "schema",
            "the JSON contract between every pipeline stage; validate-context enforces "
            "it on every output/**/context_*.json write.",
        ),
        _s(
            "docs/dev/prov/SPEC.md",
            "schema",
            "provenance stamp + ledger schema; every ledger shard and "
            "scripts/verify_doc_template.py are written against it.",
        ),
        _s(
            "docs/dev/work/SCHEMA.md",
            "schema",
            "work-item schema; docs/dev/work/BOARD.md is generated from items written to it.",
        ),
        _s(
            "docs/wiki/SCHEMA.md",
            "schema",
            "wiki page contract; the wiki-scribe and wiki-grounding-auditor subagents "
            "and /wiki-lint all validate against it.",
        ),
        # --- contract: a shape agents or suites reproduce ---------------------------
        _s(
            "docs/dev/AGENT_HANDOFF_TEMPLATE.md",
            "contract",
            "every handoff is re-validated against this file's structural headings and "
            "verbatim sections by scripts/verify_doc_template.py, including on "
            "--event consumed in the NEXT session. Editing a verbatim section's "
            "canonical text can block a handoff already in flight.",
        ),
        _s(
            "docs/dev/diagnosis/TEMPLATE.md",
            "contract",
            "the C-7 gate reads it to reject an untouched copy "
            "(enforcement/evidence.py:has_observed_evidence).",
        ),
        _s(
            "docs/dev/blast-radius/TEMPLATE.md",
            "contract",
            "this gate reads it for the same reason. Self-referential on purpose.",
        ),
        _s(
            "scripts/enforcement/guards/result.py",
            "contract",
            "GuardResult; every guard returns it and all three adapters consume it. "
            "10 non-test importers.",
        ),
        _s(
            "ui_pages/selectors.py",
            "contract",
            "the one selector registry; 14 non-test importers, consumed by the whole "
            "pytest -m ux tier AND scripts/capture_screenshots.py.",
        ),
        # --- helper: a function many sites call -------------------------------------
        _s(
            "scripts/enforcement/evidence.py",
            "helper",
            "the C-7/C-8 evidence primitive behind require-evidence-before-fix, "
            "restore-evidence and capture-before-compact.",
        ),
        _s(
            "scripts/enforcement/gitutil.py",
            "helper",
            "9 non-test importers; every guard's branch/repo detection.",
        ),
        _s(
            "scripts/wiki_relevance.py",
            "helper",
            "the classifier behind a merge-blocking freshness gate; a wrong answer "
            "here blocks merges or hides real drift.",
        ),
        _s(
            "scripts/enforcement/blast_radius.py",
            "helper",
            "this module. Changing what the gate fires on is itself a contract change.",
        ),
    )
)

#: Directory prefixes (repo-relative POSIX, trailing slash) the gate fires on.
GATED_PREFIXES: dict[str, Surface] = dict(
    (
        _s(
            "db/migrations/",
            "schema",
            "Alembic revisions; a migration is a schema change by definition, and this "
            "tree carries the batch_alter_table parent-FK cascade-delete trap "
            "(db/migrations/versions/0011_experience_title_is_active.py is the "
            "native-ADD-COLUMN precedent to follow instead).",
        ),
    )
)

#: Modules whose measured fan-in crosses `FAN_IN_THRESHOLD` but which are **deliberately
#: not gated**. Each entry is a decision with a reason, not an oversight — the audit test
#: treats this set as "reviewed", so adding to it is a conscious act.
ACKNOWLEDGED_NOT_GATED: dict[str, str] = {
    "analyzer.py": (
        "13 non-test importers, but its edits are overwhelmingly prompt-text changes "
        "already governed by PROMPT_VERSION discipline + eval telemetry. Gating every "
        "prompt tweak would make C-10 noise."
    ),
    "hardening.py": (
        "13 non-test importers. The context_set write helpers ARE a shared contract, but "
        "this module is also the ordinary home for per-branch pipeline work. Watched, "
        "not gated; revisit if a lost-update-class defect recurs "
        "(reference: context-write-lost-update-gap)."
    ),
    "db/session.py": (
        "20 non-test importers, but the surface is a stable engine/session factory that "
        "changes far less often than the models it serves."
    ),
    "web_infra/__init__.py": "15 non-test importers; a re-export shim, not a shape.",
    "ui_pages/base.py": (
        "12 non-test importers, but tests/** is exempt from the gate anyway, so gating "
        "the page-object base would block writes it can never usefully guard."
    ),
    "json_resume.py": (
        "8 non-test importers; deterministic renderer whose output shape is already "
        "pinned by tests/test_json_resume*.py."
    ),
    "db/build_context.py": (
        "8 non-test importers; assembles the context_set whose SHAPE is gated via "
        "evals/schemas/context_set.schema.json instead — the shape is the contract, "
        "not the builder."
    ),
    "blueprints/corpus/_bp.py": (
        "8 non-test importers; a Blueprint registration object, not a data or call shape."
    ),
}

# NOTE: `app.py` and `config.py` are deliberately ABSENT. Both look widely consumed at a
# glance -- 54 total importers each -- but that count is dominated by the test suite;
# their non-test fan-in is 2 and 4, below FAN_IN_THRESHOLD. They were in this dict on a
# first pass and `test_no_stale_acknowledgements` rejected them, which is the audit doing
# exactly its job: an acknowledgement for something not actually widely consumed is noise
# that hides a real one. Route-shaped changes to `app.py` are covered by
# route-security-lint + tests/test_route_containment_gate.py regardless.


def classify(path: str) -> Surface | None:
    """Classify a repo-relative POSIX path; `None` when the gate should not fire.

    O(1) on the exact-path table plus a short scan of `GATED_PREFIXES` (one entry
    today). This runs inside a PreToolUse hook on **every** Edit/Write, so it must not
    touch the filesystem or shell out — the expensive fan-in audit deliberately lives in
    `tests/test_blast_radius_classification.py` instead.
    """
    normalized = (path or "").replace("\\", "/").lstrip("./")
    if not normalized:
        return None
    exact = GATED.get(normalized)
    if exact is not None:
        return exact
    for prefix, surface in GATED_PREFIXES.items():
        if normalized.startswith(prefix):
            return Surface(path=normalized, kind=surface.kind, why=surface.why)
    return None


def is_gated(path: str) -> bool:
    """True if editing `path` requires a consumer enumeration first."""
    return classify(path) is not None
