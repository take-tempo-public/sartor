# Keyless client refusal — refusing an LLM call before any network I/O

> **Audience:** `dev`
> **Concept:** the credential gate that detects a missing Anthropic API key at the
> single `client.messages.stream()` call site in `analyzer.py`, refusing before any
> network I/O and converting an unhandled SDK `TypeError` into a catchable
> `LLMConfigurationError` that every existing LLM route handler already catches.
> **Sources:** [`analyzer.py`](../../../analyzer.py),
> [`web_infra/clients.py`](../../../web_infra/clients.py),
> [`tests/test_llm_credential_gate.py`](../../../tests/test_llm_credential_gate.py).
> **Grounding:** per [`SCHEMA.md`](../SCHEMA.md); conclusions tagged `[synthesis]`.

---

## The defect

When no Anthropic API key is configured (neither `ANTHROPIC_API_KEY` env var nor `.api_key`
file at the repo root), [`web_infra/clients.py:_get_client`](../../../web_infra/clients.py)
returns `anthropic.Anthropic(api_key="")` — the SDK accepts it at construction time. The SDK
only refuses at request-build time, raising a bare `TypeError` from
`anthropic/_client.py::_validate_headers` **before any network I/O**, so
`anthropic.APIConnectionError` never fires. Every LLM route in `blueprints/` pairs exactly
two handlers (`APIConnectionError` + `LLMResponseError`) — neither matches a `TypeError`, so
it escaped to Flask as an unhandled **500** `[synthesis]`. Observed live on PR #117's
required check, 3/3 in CI, from `POST /api/applications/<id>/draft-summary` (cited in
[`analyzer.py:LLMConfigurationError`](../../../analyzer.py)).

## The gate — check before the network call

[`analyzer.py:_assert_client_has_credential`](../../../analyzer.py) runs at the top of
every LLM call, inside `_call_llm_streaming`'s try block but **before**
`client.messages.stream(...)` is opened at [`analyzer.py:_call_llm_streaming`](../../../analyzer.py).
It performs a **positive determination only** — when both credential slots are present AND
falsy (the keyless case), it raises [`analyzer.py:LLMConfigurationError`](../../../analyzer.py)
`[synthesis]`. The message it carries is [`analyzer.py:_NO_CREDENTIAL_DETAIL`](../../../analyzer.py),
which names both remediation paths: `ANTHROPIC_API_KEY` environment variable or `.api_key`
file `[synthesis]`.

**Why `LLMConfigurationError` subclasses `LLMResponseError`.** This is a deliberate taxonomy
choice (not sloppy inheritance). [`analyzer.py:LLMConfigurationError`](../../../analyzer.py)
inherits from [`analyzer.py:LLMResponseError`](../../../analyzer.py) so that all 19
`except LLMResponseError` sites across five blueprint modules catch it **without a single edit**
— the alternative, a standalone class, would have left every one of them returning 500, which
is the original defect (fully explained at [`analyzer.py:LLMConfigurationError`](../../../analyzer.py)).

## The backstop — catch a future SDK drift

If the SDK changes and a new authentication refusal path exists that the pre-check cannot
see, [`analyzer.py:_call_llm_streaming`](../../../analyzer.py) has a backstop:
catch any `TypeError` at request-build time and check if it contains the substring
[`analyzer.py:_SDK_NO_AUTH_MARKER`](../../../analyzer.py) (`"Could not resolve authentication method"`).
If it matches, re-raise as `LLMConfigurationError` instead of letting the bare `TypeError`
escape `[synthesis]`. The comment at [`analyzer.py:_call_llm_streaming`](../../../analyzer.py)
notes this is "for SDK drift only" and is narrow by construction — the message match means
no ordinary `TypeError` (a real programming error) can be swallowed.

## Telemetry and observability

The failure still emits its telemetry row exactly as every failed call has always done.
Inside the `finally` block of [`analyzer.py:_call_llm_streaming`](../../../analyzer.py), a
single JSONL record is written with `status="error"`, `call=<call_kind>`, `error_type` set
to the exception class name, and `error_message` (redacted) — so observability is a
property of the funnel, not of each caller `[synthesis]`. Pinned in
[`tests/test_llm_credential_gate.py:test_the_failure_still_emits_its_telemetry_row`](../../../tests/test_llm_credential_gate.py).

## Known limit — HTTP status stays 502

[`analyzer.py:LLMConfigurationError`](../../../analyzer.py) notes that the resulting
HTTP status stays 502 (since all 19 handlers emit that status for `LLMResponseError`), and
their copy still says "malformed" instead of naming the configuration cause. The cause
travels verbatim in `validation_error`, which every handler already puts in the response
`detail` and in its own `logger.error` line — so the *information* about why the call
failed reaches the client and the log, even if the status code is not perfectly named.
Correcting status + copy across 19 sites is deferred.

## What the gate does NOT do

The gate deliberately does **not** blanket-catch all `TypeError` at the SDK call — that would
swallow genuine programming errors (a wrong argument, a `None` where a dict belongs) and
turn real bugs into polite messages. It checks **only** when both credential slots exist AND
are falsy, leaving any other `TypeError` shape to re-raise untouched and hit the developer
as a traceback. Pinned in [`tests/test_llm_credential_gate.py:test_an_ordinary_typeerror_is_not_relabeled`](../../../tests/test_llm_credential_gate.py).

It also passes through objects that expose neither credential slot —
`MagicMock(spec=anthropic.Anthropic)` and `None` (from stubbed tests) — untouched, so
they keep their original failure modes (missing `AttributeError` for the mock, loud
`AttributeError` for the None stub) rather than being relabeled as configuration errors
`[synthesis]`. Pinned in [`tests/test_llm_credential_gate.py:test_a_client_exposing_neither_slot_is_passed_straight_through`](../../../tests/test_llm_credential_gate.py).

## Related

- [[llm-call-catalog]] — the full inventory of LLM call kinds that all route through this gate.
- [[deterministic-llm-boundary]] — the single `client.messages` call site and its telemetry
  funnel, of which credential checking is the first step.
- [[troubleshooting]] — user-facing error guidance (API-key setup is one common failure case).
