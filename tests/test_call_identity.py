"""`call_identity`: the hash, producer-id and W3C-id helpers (item 181)."""

from __future__ import annotations

import re

import pytest

import call_identity as ci

_SHA = re.compile(r"sha256:[0-9a-f]{64}")


def test_text_sha256_is_prefixed_full_hex_of_utf8_bytes():
    assert _SHA.fullmatch(ci.text_sha256("abc"))
    # Known vector: sha256("abc").
    assert ci.text_sha256("abc") == (
        "sha256:ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )
    assert ci.text_sha256("é") != ci.text_sha256("e")


def test_canonical_json_sorts_keys_and_is_compact():
    assert ci.canonical_json({"b": 1, "a": [1, 2]}) == '{"a":[1,2],"b":1}'


@pytest.mark.parametrize("bad", [{"t": 0.7}, [1, 2.5], {"a": {"b": [1.0]}}])
def test_canonical_json_refuses_floats_anywhere(bad):
    with pytest.raises(TypeError, match="float"):
        ci.canonical_json(bad)


def test_canonical_json_accepts_bools_ints_none_and_strings():
    assert ci.canonical_json({"a": True, "b": None, "c": 3, "d": "x"})


def _pid(**over):
    base = {
        "call_kind": "clarify",
        "prompt_sha256": ci.text_sha256("p"),
        "model": "claude-haiku-4-5-20251001",
        "settings": {"max_tokens": 8000},
    }
    base.update(over)
    return ci.producer_id(**base)


def test_producer_id_is_stable_and_well_formed():
    assert _SHA.fullmatch(_pid())
    assert _pid() == _pid()


def test_producer_id_treats_a_retry_as_the_same_producer():
    assert _pid(call_kind="clarify_retry") == _pid(call_kind="clarify")


@pytest.mark.parametrize(
    "over",
    [
        {"call_kind": "recommend"},
        {"prompt_sha256": ci.text_sha256("other")},
        {"model": "claude-sonnet-5"},
        {"settings": {"max_tokens": 4000}},
        {"settings": None},
    ],
)
def test_producer_id_changes_when_any_input_changes(over):
    assert _pid(**over) != _pid()


def test_producer_id_refuses_a_float_setting():
    with pytest.raises(TypeError):
        _pid(settings={"temperature": 0.2})


def test_new_ids_have_w3c_sizes_and_validate():
    trace, span = ci.new_trace_id(), ci.new_span_id()
    assert re.fullmatch(r"[0-9a-f]{32}", trace) and ci.is_trace_id(trace)
    assert re.fullmatch(r"[0-9a-f]{16}", span) and ci.is_span_id(span)
    assert ci.new_trace_id() != trace


@pytest.mark.parametrize("value", ["", "0" * 32, "A" * 32, "a" * 31, "g" * 32, None, 5, "a" * 16])
def test_is_trace_id_rejects_malformed(value):
    assert not ci.is_trace_id(value)


@pytest.mark.parametrize("value", ["0" * 16, "A" * 16, "a" * 15, None, "a" * 32])
def test_is_span_id_rejects_malformed(value):
    assert not ci.is_span_id(value)
