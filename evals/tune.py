"""Deterministic candidate-vs-baseline delta table for the eval tuning loop.

LLM-free. Reads eval result JSONL (the files ``evals/runner.py`` writes) and
computes a per-``(fixture, rubric)`` score delta between a baseline run and a
candidate run. This is the quantitative output the ``/tune-from-annotations``
skill surfaces after an A/B trial via the prompt-override primitive — extracted
here so the delta is reproducible and testable instead of eyeballed from two
JSONL files.

It deliberately does **not** import from ``runner.py`` (or ``annotation.py`` /
``bootstrap.py`` / ``seed_import.py``): it only consumes their output, so it can
never perturb the runner's ``--seed`` / ``--prompt-overrides`` / file paths. The
only thing mirrored is ``REGRESSION_DELTA`` (same default + env override as the
runner) so "what counts as a regression" stays consistent across the harness.

CLI:
    python -m evals.tune --baseline A.jsonl --candidate B.jsonl [--json]

Exit code: 0 if no rubric regressed, 2 if at least one regressed, 1 on a file
read error — so a script can gate a promote on a clean delta.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

# Mirror evals/runner.py: the same magnitude (and env override) decides what
# counts as a regression, so the tune delta and the runner agree.
REGRESSION_DELTA = float(os.environ.get("REGRESSION_DELTA", "0.5"))


@dataclass(frozen=True)
class DeltaRow:
    """One (fixture, rubric) baseline-vs-candidate comparison.

    ``baseline_mean`` / ``candidate_mean`` are ``None`` when that side has no
    graded (``status == "ok"``) record for the pair; ``delta`` is then ``None``
    too (one-sided pairs can't be compared, only flagged ``new`` / ``missing``).
    """

    fixture: str
    rubric: str
    baseline_mean: float | None
    candidate_mean: float | None
    delta: float | None
    regressed: bool


def _mean(values: list[float]) -> float | None:
    """Arithmetic mean, or ``None`` for an empty list."""
    return sum(values) / len(values) if values else None


def load_scores(path: Path | str) -> dict[tuple[str, str], list[float]]:
    """Read a result JSONL and group graded scores by ``(fixture, rubric)``.

    Only ``status == "ok"`` rows with a numeric ``score`` are counted — this
    drops ``judge_error`` (score 0) and ``pipeline_error`` rows that would
    otherwise drag a mean down and misattribute it to the prompt. Multiple rows
    for one pair (an n>1 run written to a single file) are kept so the caller
    gets the mean across them. Blank lines are skipped; a malformed line raises
    ``ValueError`` naming the file + line number.
    """
    path = Path(path)
    grouped: dict[tuple[str, str], list[float]] = {}
    text = path.read_text(encoding="utf-8")
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{lineno}: invalid JSON line: {exc}") from exc
        if record.get("status") != "ok":
            continue
        score = record.get("score")
        if not isinstance(score, (int, float)):
            continue
        key = (str(record.get("fixture", "")), str(record.get("rubric", "")))
        grouped.setdefault(key, []).append(float(score))
    return grouped


def build_delta_table(
    baseline: dict[tuple[str, str], list[float]],
    candidate: dict[tuple[str, str], list[float]],
) -> list[DeltaRow]:
    """Build the per-(fixture, rubric) delta rows, sorted for stable output.

    A pair present in only one side gets a ``None`` mean on the missing side and
    a ``None`` delta (it is not a regression — there is nothing to compare).
    ``regressed`` is true only when both means exist and the drop is at least
    ``REGRESSION_DELTA``.
    """
    rows: list[DeltaRow] = []
    for key in sorted(set(baseline) | set(candidate)):
        b_mean = _mean(baseline.get(key, []))
        c_mean = _mean(candidate.get(key, []))
        delta = c_mean - b_mean if b_mean is not None and c_mean is not None else None
        regressed = delta is not None and delta <= -REGRESSION_DELTA
        rows.append(DeltaRow(key[0], key[1], b_mean, c_mean, delta, regressed))
    return rows


def _fmt(value: float | None) -> str:
    """Two-decimal cell, or an ASCII ``n/a`` for a missing mean.

    ASCII deliberately: the table is printed to stdout and the command surfaces
    it on Windows, where a non-ASCII placeholder can mojibake or raise
    ``UnicodeEncodeError`` on a console code page that lacks the glyph.
    """
    return f"{value:.2f}" if value is not None else "n/a"


def format_delta_table(rows: list[DeltaRow]) -> str:
    """Render the delta rows as a readable fixed-width table.

    Regressions are tagged ``(REGRESSION)``; a pair seen on only one side is
    tagged ``(new)`` (candidate only) or ``(missing)`` (baseline only).
    """
    header = ("fixture", "rubric", "baseline", "candidate", "delta", "flag")
    body: list[tuple[str, str, str, str, str, str]] = []
    for r in rows:
        if r.delta is not None:
            delta_str = f"{r.delta:+.2f}"
            flag = "(REGRESSION)" if r.regressed else ""
        else:
            delta_str = "n/a"
            flag = "(new)" if r.baseline_mean is None else "(missing)"
        body.append(
            (r.fixture, r.rubric, _fmt(r.baseline_mean), _fmt(r.candidate_mean), delta_str, flag)
        )

    widths = [max(len(row[i]) for row in (header, *body)) for i in range(len(header))]
    sep = "  "

    def _line(cells: tuple[str, ...]) -> str:
        return sep.join(cell.ljust(widths[i]) for i, cell in enumerate(cells)).rstrip()

    lines = [_line(header), _line(tuple("-" * w for w in widths))]
    lines.extend(_line(row) for row in body)
    if not body:
        lines.append("(no (fixture, rubric) pairs in either run)")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m evals.tune",
        description="Candidate-vs-baseline eval delta table (LLM-free).",
    )
    ap.add_argument("--baseline", required=True, metavar="PATH", help="baseline result JSONL")
    ap.add_argument("--candidate", required=True, metavar="PATH", help="candidate result JSONL")
    ap.add_argument(
        "--json", action="store_true", help="emit the rows as JSON instead of a table"
    )
    args = ap.parse_args(argv)

    try:
        baseline = load_scores(args.baseline)
        candidate = load_scores(args.candidate)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}")
        return 1

    rows = build_delta_table(baseline, candidate)
    if args.json:
        print(json.dumps([asdict(r) for r in rows], indent=2))
    else:
        print(format_delta_table(rows))

    return 2 if any(r.regressed for r in rows) else 0


if __name__ == "__main__":
    raise SystemExit(main())
