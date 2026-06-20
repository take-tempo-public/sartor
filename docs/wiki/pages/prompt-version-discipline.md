# PROMPT_VERSION discipline + the prompt-override primitive

> **Audience:** `dev`
> **Concept:** why a single `PROMPT_VERSION` string must bump in the same commit as any prompt change, and how the eval prompt-override primitive A/Bs a *candidate* prompt without editing the persona constants — quarantining candidate runs as `candidate:<hash>` so they never pollute score-over-time.
> **Sources:** [`analyzer.py`](../../../analyzer.py), [`evals/runner.py`](../../../evals/runner.py), [`AGENTS.md`](../../../AGENTS.md).
> **Grounding:** per [`SCHEMA.md`](../SCHEMA.md); conclusions tagged `[synthesis]`.

---

## The bump rule (canonical elsewhere — cited, not restated)

[`AGENTS.md`](../../../AGENTS.md) states the binding rule under "LLM prompts" /
"Eval observability": **when any prompt (or per-call prompt template) changes,
bump `PROMPT_VERSION` in the same commit** so observability and eval can
attribute behavior to a revision. Per design fork D5 that contract lives there,
not here — this page documents the *machinery* that makes the rule enforceable
and tunable, and links back to the rule.

## What `PROMPT_VERSION` is

A single module-level string, [`analyzer.py:PROMPT_VERSION`](../../../analyzer.py)
(`"2026-06-13.1"` at this ingest). Its own comment says to bump it when
`SYSTEM_PROMPT`, `CLARIFY_SYSTEM_PROMPT`, **or any per-call prompt template**
changes, because it "labels every JSONL telemetry record so quality regressions
can be attributed to a revision."

The label is stamped on every LLM call's telemetry: the `_emit_call_log` record
in [`analyzer.py`](../../../analyzer.py) writes `"prompt_version":
effective_prompt_version()` alongside `call`, `model`, token counts, and latency.
So the version is not advisory bookkeeping — it is the join key the dashboard's
score-over-time chart groups on `[synthesis]`.

## Why "same commit", and what does *not* count

If a prompt edit shipped without a bump, telemetry would attribute the new
behavior to the *old* version label, silently blending two distinct prompts in
one score series — the exact regression-attribution failure the field exists to
prevent `[synthesis]`. The discipline is the inverse of the cache argument: an
unchanged prompt **must not** bump (a spurious bump fragments the series and can
miss a cache hit) `[synthesis]`.

The boundary is "prompt **template** vs **data**." A concrete worked example: the
Compose bullet-reorder path carries the inline note that it "reorders DATA, not
the prompt template → no `PROMPT_VERSION` bump" ([`analyzer.py`](../../../analyzer.py),
near the `bullet_order` handling). Reordering the facts fed *into* a prompt is
not a prompt change; rewriting the template around them is.

## The prompt-override primitive (eval tuning loop)

A/B-testing a candidate prompt by editing the persona constants would (a) ship an
untested prompt to production and (b) need a real `PROMPT_VERSION` bump — making
"try a variant" a committed change. The override primitive removes both costs.

It is a `ContextVar`-backed context manager,
[`analyzer.py:prompt_overrides`](../../../analyzer.py): you pass a mapping of
persona-constant **name** → replacement text; an unknown key raises `ValueError`
(fail loud — a typo'd name silently no-op'ing would mislabel a baseline run as a
candidate). An empty / `None` mapping is a no-op.

Resolution happens at every call site through
[`analyzer.py:_resolve_system_prompt`](../../../analyzer.py), which reads the
active override for `name` else falls back to the baseline in the
[`analyzer.py:_BASE_SYSTEM_PROMPTS`](../../../analyzer.py) registry. That registry
maps each overridable constant name (`SYSTEM_PROMPT`, `CLARIFY_SYSTEM_PROMPT`,
`RECOMMEND_SYSTEM_PROMPT`, … 11 keys) to its baseline value and is defined at
module end, after every constant exists. **Override scope is exactly those named
system-prompt constants** — not the dynamic user-prompt builders `[synthesis]`.

## Quarantine: `candidate:<hash>` never pollutes the baseline

[`analyzer.py:effective_prompt_version`](../../../analyzer.py) is the single
resolver for the stamp:

- **No active override** → returns `PROMPT_VERSION` verbatim.
- **Override active** → returns `candidate:<digest>`, where `<digest>` is the
  first 12 hex chars of a sha256 over the canonical (`sort_keys=True`) JSON of the
  override mapping — stable for a given candidate, so repeated runs of the same
  candidate share one label.

Because the stamp differs, candidate telemetry sorts into its own `candidate:*`
bucket and never lands in the `PROMPT_VERSION` score-over-time series — the
quarantine is a property of the label, not a separate filter `[synthesis]`.

## Default-path byte-identity (why production is untouched)

The primitive is designed so the no-override path is **byte-identical** to the
pre-primitive code: with no override active, `_resolve_system_prompt` returns the
*identical constant object* (so the bytes sent to the API — and thus the
analyze→generate prompt cache — are unchanged), and `effective_prompt_version()`
returns `PROMPT_VERSION` verbatim. The module comment is explicit that only the
eval harness / `/prompt-tune` skill enter the context manager; the production
request path in `app.py` never does, so `analyze()` / `generate()` stay on the
default path.

## How the eval harness drives it

[`evals/runner.py`](../../../evals/runner.py) exposes `--prompt-overrides PATH`, a
JSON file mapping a prompt-constant name to candidate text. The CLI does the
file read + shape-validation (object of string→string, else exit 1); the
prompt-**name** validation happens once inside `run_suite`, before any paid LLM
call. When overrides are present `run_suite` enters `prompt_overrides(...)`,
computes the `candidate:<hash>` it will run under, and logs a loud warning that
the run is "quarantined from score-over-time." Every result record then stamps
`effective_prompt_version()`. With no `--prompt-overrides`, `run_suite`'s default
invocation is byte-identical to the historical path (`prompt_overrides({})` is a
no-op). This is the substrate the `/prompt-tune` and v1.0.4 tuning loop build on
`[synthesis]`.

## A second version: AVATAR_PROMPT_VERSION

The doc-grounded assistant ("avatar", Sprint 7.5) is a **separate LLM subsystem** from the résumé pipeline — a different persona and **not an eval target** — so it carries its own [`analyzer.py:AVATAR_PROMPT_VERSION`](../../../analyzer.py) (`"2026-06-19.1"` at this ingest, per the inline comment at [`analyzer.py:283–289`](../../../analyzer.py)). When `AVATAR_SYSTEM_PROMPT` (the avatar's persona, defined at [`analyzer.py:519–540`](../../../analyzer.py)) changes, bump `AVATAR_PROMPT_VERSION` in the same commit; a tweak to the avatar's prompt should not force a bump to `PROMPT_VERSION`, which would muddy résumé score-over-time attribution on the dashboard `[synthesis]`. The avatar persona is intentionally **not** in the `_BASE_SYSTEM_PROMPTS` registry — the prompt-override machinery is résumé-scoped by construction, so the avatar is out of its reach.

It is a **source-level discipline marker, not a telemetry field.** The lone stamp site [`analyzer.py:effective_prompt_version`](../../../analyzer.py) writes `PROMPT_VERSION` (or a `candidate:<hash>`) onto *every* funnelled call's JSONL — including the avatar's `avatar_answer` ([`analyzer.py` `_emit_call_log`](../../../analyzer.py)); it has no `AVATAR_PROMPT_VERSION` branch. So bumping `AVATAR_PROMPT_VERSION` does **not** create a second telemetry series — its whole job is to record the avatar-prompt revision in source **without** bumping `PROMPT_VERSION`, keeping the résumé score-over-time join key stable. The avatar's calls are already separable in telemetry by `call_kind="avatar_answer"`, and the avatar is not an eval target `[synthesis]`.

## Related

- [[code-module-map]] — where `analyzer.py` sits in the module graph.
- [[llm-call-catalog]] — the call kinds whose telemetry the version stamps; the avatar's `avatar_answer` is one of them (stamped `PROMPT_VERSION`, not `AVATAR_PROMPT_VERSION`).
- [[eval-harness]] — `runner.py`, `--prompt-overrides`, and the result records.
- [[deterministic-llm-boundary]] — the deterministic modules that never bump it.
