# Blast radius — llm-call-error-capture

> **Branch:** `feat/llm-call-error-capture`
> **Status:** complete

---

## Surface

`analyzer.py`'s `_call_llm_streaming` (`analyzer.py:1289-1469`): the `except TypeError` /
`except Exception` branches (status-setting) and the `finally` block's record
construction plus `_emit_call_log(...)` call (`analyzer.py:1427-1448`), which builds the
one JSON record per call written to `logs/llm_calls.jsonl` (`LOG_PATH`, `analyzer.py:567`).
This sprint adds two keys — `error_type`, `error_message` — to that record, **only** on
rows where `status == "error"`. No existing key changes name, type, or meaning;
`status == "ok"` rows are byte-identical to today.

A new pure helper, `_redact_error_message(message: str) -> str`, is added at
`analyzer.py:604` (its module-level redaction constants at `analyzer.py:598`) implementing
the redaction/size policy. It has no consumers yet (new code), so it does not itself need
enumeration — it is listed here only because it is new.

**Correction (F2, closer re-verification):** the citations above were re-checked
line-by-line against the staged tree rather than reused from the sprint brief. The prior
draft of this section cited `analyzer.py:1245-1408` and `:1371-1387`, both pre-edit line
numbers — the diff's `_redact_error_message` block shifts everything below it by +44 lines
(`@@ -1316,6 +1360,8 @@`), which is why a stale citation drifts silently rather than
failing loudly.

---

## Enumeration

Commands run from the repo root, verbatim, with counts. "Grep-complete" here means every
name the `llm_calls.jsonl` record shape goes by: the file name, `LOG_PATH`,
`_emit_call_log`, and the field names a reader could depend on.

```
$ grep -rniE "LOG_PATH|_emit_call_log" --include=*.py . | wc -l
92
$ grep -rli "llm_calls\.jsonl" --include=*.py . | wc -l
22 files (analyzer.py, blueprints/analysis.py, dashboard/__init__.py,
          dashboard/routes.py, evals/corpus_drafting_probe.py, evals/runner.py,
          hardening.py, scripts/perf_baseline.py, scripts/smoke_phase_b1.py,
          tests/conftest.py, tests/test_call_kind_route_telemetry.py,
          tests/test_call_kind_telemetry.py, tests/test_demo_mode.py,
          tests/test_extract_experiences.py, tests/test_hardening.py,
          tests/test_llm_call_error_capture.py, tests/test_llm_credential_gate.py,
          tests/test_refinement_scope.py, tests/ux/flows/test_dashboard_console.py,
          tests/ux/regression/test_20260611_diagnostics_chart_corrections.py,
          tests/ux/regression/test_20260809_wizard_rail_frozen_gate.py,
          tests/ux/stubs.py)
```
**Correction, re-derived (fixes F2):** the prior count/list on this branch (19 claimed,
21 actually listed) was wrong on two counts — miscounted, and missing
`tests/test_hardening.py` (a `llm_calls.jsonl`-referencing comment at `:747`, `TestCallCost`
class — see row 11a below). The 22-file list above also now includes this sprint's own new
`tests/test_llm_call_error_capture.py`, which did not exist when the grep was first run.
Re-derived without any `git stash` command, per the C1c re-run instructions.

**Correction (F1, closer re-verification):** an earlier draft of this dossier (row 11b)
claimed `tests/test_analyzer_model_selection.py` was not a consumer, reasoning that the
literal `llm_calls\.jsonl` grep above does not match it. That is true but insufficient —
the file depends on the telemetry record shape via `LOG_PATH`, which the literal-string
grep misses and the `LOG_PATH|_emit_call_log` grep (line 32 above) correctly catches. It
is independently reproduced below in row 11b, restored.

```
$ grep -rli "llm_calls" --include=*.md . | wc -l
~20 files — commands/bench.md, commands/replay.md, docs/architecture.md,
docs/install.md, docs/governance/metrics.md, docs/wiki/pages/diagnostics-console.md,
plus historical handoffs/diagnoses/work-items that only narrate past incidents
(item 21, item 22, item 33) and are not live consumers.
$ grep -n "scripts.enforcement.blast_radius" scripts/enforcement/blast_radius.py
  — confirms analyzer.py's registry entry: ACKNOWLEDGED_NOT_GATED (`:191`), NOT
    GATED. `classify("analyzer.py")` returns None (only `GATED` + `GATED_PREFIXES`
    are checked by `classify()`), so `require-consumer-enumeration` does not
    actually fire on this edit. **Correction to the sprint brief**, which cited
    `:191` as evidence the guard "is expected to fire" — `:191` is inside
    `ACKNOWLEDGED_NOT_GATED`, a dict `classify()` never reads. This dossier is
    written anyway, on the brief's explicit in-scope instruction and because
    `llm_calls.jsonl`'s record shape is a real shared contract regardless of
    whether the hook enforces it mechanically.
```

Zero hits for `error_type` or `error_message` anywhere in the repo before this branch
(both are new field names) — confirmed by
`grep -rn "error_type\|error_message" --include=*.py .` returning nothing under
`analyzer.py`, `dashboard/`, `hardening.py`, `evals/`, `scripts/`. No existing reader can
already depend on them; there is nothing to break by adding them.

---

## Consumers

| # | Site (`path:line`) | Decision | Rationale |
|---|---|---|---|
| 1 | `analyzer.py:1427-1448` (`finally` block: record construction + `_emit_call_log` call site) | **update** | The actual edit: build `error_type`/`error_message` in the except branches, pass them into the record dict conditionally on `status == "error"`. |
| 2 | `dashboard/routes.py:53` (`LLM_LOG`) + `:63-68` (`json.loads(line)` into `records`) | no change | Every downstream read goes through `r.get("status")` / dict access (`:184`, `:792`, `:872`), never a fixed-key unpack or strict schema. New keys pass through inert until C2's UX-8 reads them — that read is explicitly out of scope for this sprint. |
| 3 | `dashboard/__init__.py:3` (docstring: "Reads logs/llm_calls.jsonl") | no change | Prose description of the file, not a parser. Still accurate. |
| 4 | `hardening.py:1497` (`compute_call_cost`) | no change | Reads `model`/`input_tokens`/`output_tokens`/`cache_*_tokens` via `.get()`; the two new keys are never referenced, so cost computation is unaffected. |
| 5 | `blueprints/analysis.py:466` | no change | A code comment referencing the log for run-id provenance, not a parser. |
| 6 | `evals/corpus_drafting_probe.py:110-119` (`LOG_PATH` import, tail-200 read) | no change | Reads the last 200 lines via `json.loads`; no fixed-key assumption found. |
| 7 | `evals/runner.py:94,393-409` (`LLM_LOG_PATH`, per-fixture cost sum) | no change | `rec.get("run_id")`, `rec.get("cache_read_input_tokens", 0)` — tolerant `.get()` access throughout. |
| 8 | `scripts/perf_baseline.py:30-86` (CLI over an arbitrary log path) | no change | `r.get("call", "?")`, `r.get("latency_ms")`, `r.get("output_tokens", 0)` — tolerant. Percentile output is unaffected by two new string keys on error rows. |
| 9 | `scripts/smoke_phase_b1.py:205` (`log_path`) | no change | Same tolerant `.get()` pattern reading `run_id`/`cache_read_input_tokens`. |
| 10 | `tests/conftest.py:16-33` (`_default_llm_log_path` autouse fixture) | no change | Redirects `analyzer.LOG_PATH` to `tmp_path`; agnostic to record shape. New error-path tests this sprint adds get this redirect for free. |
| 11 | `tests/test_call_kind_telemetry.py`, `tests/test_call_kind_route_telemetry.py`, `tests/test_demo_mode.py`, `tests/test_extract_experiences.py`, `tests/test_llm_credential_gate.py`, `tests/test_refinement_scope.py` | no change | All assert specific keys they care about (`status`, `call`, `model`, `latency_ms`, `prompt_version`) via membership/equality, never an exact-keys/length assertion on the record dict. Verified by reading each assertion site; none breaks when two new keys appear only on `status == "error"` rows, which none of these tests currently produce except `test_llm_credential_gate.py`'s `test_the_failure_still_emits_its_telemetry_row` (asserts `rows[0]["status"] == "error"` and `rows[0]["call"]`, not an exact key set — unaffected). |
| 11a | `tests/test_hardening.py:747` (`TestCallCost`, comment referencing `llm_calls.jsonl`) | no change | The class builds `record` dicts by hand (`model`/`input_tokens`/`output_tokens`/`cache_*_tokens`) to exercise `compute_call_cost`, which reads via `.get()` (row 4). Neither test constructs `error_type`/`error_message`, and `compute_call_cost` never references them, so the rows are unaffected either way. Previously omitted from this dossier's enumeration — F2. |
| 11b | `tests/test_analyzer_model_selection.py` | no change | Monkeypatches `analyzer.LOG_PATH` to a temp file (`:46`, `:58`, `:69`) and, after each `_call_llm` call, reads the emitted JSONL record back and asserts `rec["model"] == <expected>` by key lookup (`:54-55`, and the equivalent pair in the other two test methods) — never an exact-keyset or positional-unpack check on the record dict. The additive `error_type`/`error_message` fields ride only on `status == "error"` rows, and every row this test produces is `status == "ok"` (a stubbed successful `client.messages.stream` call), so they never appear here and the assertion is unaffected. Restored per F1 — the literal `llm_calls\.jsonl` string grep misses this file (it writes to `tmp_path / "calls.jsonl"`, never the literal filename), but the `LOG_PATH|_emit_call_log` grep (line 32 above) catches it correctly; the prior "removed from this table" entry rested on the narrower grep alone. |
| 11c | `tests/test_llm_call_error_capture.py` (this sprint's own new test) | n/a | Not a pre-existing consumer; it is the positive-assertion test this sprint adds (see "Verification" below). Listed only because the re-derived grep now matches it. |
| 12 | `tests/ux/stubs.py:431,482` | no change | Comments/prose about `status="error"` rows appearing during stubbed UX runs; no field-level parsing. |
| 13 | `tests/ux/flows/test_dashboard_console.py:122`, `tests/ux/regression/test_20260611_diagnostics_chart_corrections.py:106` | no change | Write synthetic fixture rows for dashboard UX tests; they construct dicts by hand and don't assert against `analyzer`'s live shape, so adding fields there is optional and out of scope (no dashboard UI work this sprint). |
| 14 | `commands/bench.md:11-27` | no change | Agent-prompt slash command; already instructs summarizing "Any `status: \"error\"` rows" generically. It will surface the new fields once populated without an edit; enhancing its instructions to explicitly ask for `error_message` is a nice-to-have, filed as a work item, not required for this sprint's scope. |
| 15 | `commands/replay.md:18` | no change | Prints `latency_ms`/`cache_read_input_tokens` from the most recent line; doesn't touch `status` or error fields. |
| 16 | `docs/architecture.md`, `docs/install.md`, `docs/governance/metrics.md`, `docs/wiki/pages/diagnostics-console.md` | deferred | Prose descriptions of the telemetry log's shape/purpose. None currently documents the per-field schema in enough detail to go stale from an additive change. Full documentation of the new fields (plus the UI that will display them) belongs with C2's UX-8 work and the epic-close wiki pass (`epic-c-design-brief.md` §"Close-out intervals" — wiki pass deferred to epic close unless drift crosses 60). |

---

## Deferred

- **Dashboard UI surfacing of `error_message`/`error_type`** (C2's UX-8) — explicitly out
  of scope per `docs/dev/handoffs/epic-c-c1c-brief.md` ("Out of scope, deliberately: Any
  dashboard/UI change"). Tracked as the reason C1c exists at all.
- **`commands/bench.md` copy update** to explicitly call out `error_message` — low value
  until the field has real data; filed as a work item rather than folded in here.
- **Wiki page `docs/wiki/pages/diagnostics-console.md`** — deferred to the epic-close wiki
  pass per the design brief's declared cadence; this sprint's wiki-freshness backstop
  check happens at gate time, not per-file here.

---

## Verification

A missed consumer would surface as: a reader that unpacks the record via fixed positional
keys or an `assert set(record.keys()) == {...}` style exact-membership check breaking when
two new keys appear on error rows. Grep for `set(.*\.keys\(\))` and `\.keys\(\)\s*==` against
`tests/**/*llm*` and `dashboard/**`, `hardening.py`, `evals/**`, `scripts/perf_baseline.py`,
`scripts/smoke_phase_b1.py` found zero such assertions — every reader found above uses
`.get()` or equality/membership checks on named keys it already expects, which is exactly the
tolerant-reader shape that makes an additive change safe. The new unit tests added this
sprint (`tests/test_llm_call_error_capture.py`) assert directly on the record `_emit_call_log`
receives (via the existing `LOG_PATH`-redirect fixture idiom), proving the two fields land on
an error row and are absent on an ok row — the positive half of this claim. The full test
suite (`python -m scripts.gate`) is the negative half: any reader that did break would fail
loudly rather than silently, per the tolerant-access pattern confirmed above.
