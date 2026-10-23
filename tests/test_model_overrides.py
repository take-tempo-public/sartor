"""Item 137 / 173 proposal 16: a candidate model runs without editing the pins.

`analyzer.model_overrides()` swaps what a pin resolves to for the duration of a `with` block, at
the one product send site (`_call_llm_streaming`). These tests pin the contract:

* the default path (no override) is byte-identical: same request, same row, no `pinned_model`;
* an override changes the request `model`, the `thinking` value (from `THINKING_POLICY`), the row's
  `model` (which `compute_call_cost` prices) and adds `pinned_model` to that row only;
* an override that could send an unchosen thinking mode or an unpriced model is refused BEFORE any
  request (charter C-11: fail closed);
* the eval judge never reaches `_call_llm_streaming`, so it stays on `JUDGE_MODEL`.

Offline: `_emit_call_log` is redirected, the client is a duck-typed stand-in, nothing is paid.
Bodies are untyped like the rest of tests/.
"""

from __future__ import annotations

import pytest

import analyzer
from analyzer import HAIKU_MODEL, SONNET_MODEL
from hardening import MODEL_PRICING, compute_call_cost

CANDIDATE_SONNET = "claude-sonnet-5-5"
CANDIDATE_HAIKU = "claude-haiku-5-5"


class _Usage:
    input_tokens = 10
    output_tokens = 5
    cache_creation_input_tokens = 0
    cache_read_input_tokens = 0


class _Final:
    stop_reason = "end_turn"
    usage = _Usage()


class _Stream:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    @property
    def text_stream(self):
        yield "ok"

    def get_final_message(self):
        return _Final()


class _Messages:
    def __init__(self, captured):
        self._captured = captured

    def stream(self, **kwargs):
        self._captured.append(kwargs)
        return _Stream()


class _Client:
    def __init__(self):
        self.captured: list[dict] = []
        self.messages = _Messages(self.captured)


@pytest.fixture(autouse=True)
def _rows(monkeypatch):
    rows: list[dict] = []
    monkeypatch.setattr(analyzer, "_emit_call_log", rows.append)
    return rows


def _call(client, model=None):
    return analyzer._call_llm(client, "p", call_kind="t", model=model)


class TestDefaultPathIsUnchanged:
    @pytest.mark.parametrize("model", [None, SONNET_MODEL, HAIKU_MODEL])
    def test_request_and_row_without_an_override(self, _rows, model):
        client = _Client()

        _call(client, model)

        requested = model or SONNET_MODEL
        assert client.captured[0]["model"] == requested
        assert _rows[0]["model"] == requested
        assert "pinned_model" not in _rows[0]

    def test_no_override_is_active_by_default(self):
        assert analyzer.active_model_overrides() == {}

    def test_none_and_empty_mapping_are_no_ops(self, _rows):
        client = _Client()
        for empty in (None, {}):
            with analyzer.model_overrides(empty):
                assert analyzer.active_model_overrides() == {}
                _call(client)
        assert [c["model"] for c in client.captured] == [SONNET_MODEL, SONNET_MODEL]
        assert all("pinned_model" not in r for r in _rows)


class TestOverrideSwapsTheModel:
    def test_sonnet_override_changes_request_thinking_and_row(self, _rows):
        client = _Client()

        with analyzer.model_overrides({"SONNET_MODEL": CANDIDATE_SONNET}):
            _call(client)  # model=None means "the Sonnet pin"

        sent = client.captured[0]
        assert sent["model"] == CANDIDATE_SONNET
        # `disabled` is a 400 on Sonnet 5.5: the candidate gets its own policy value.
        assert sent["thinking"] == analyzer.THINKING_POLICY[CANDIDATE_SONNET]
        assert sent["thinking"] == {"type": "between_tools"}
        row = _rows[0]
        assert row["model"] == CANDIDATE_SONNET
        assert row["pinned_model"] == SONNET_MODEL
        assert row["request_settings"]["model"] == CANDIDATE_SONNET

    def test_haiku_override_resolves_an_explicit_haiku_argument(self, _rows):
        client = _Client()

        with analyzer.model_overrides({"HAIKU_MODEL": CANDIDATE_HAIKU}):
            _call(client, HAIKU_MODEL)

        assert client.captured[0]["model"] == CANDIDATE_HAIKU
        assert client.captured[0]["thinking"] == {"type": "disabled"}
        assert _rows[0]["pinned_model"] == HAIKU_MODEL

    def test_override_matches_by_value_so_a_from_imported_pin_is_covered(self, _rows):
        """`onboarding/extract_experiences.py` holds its own copy of the HAIKU string."""
        copied = "".join([HAIKU_MODEL])  # a distinct str object with the same value
        client = _Client()

        with analyzer.model_overrides({"HAIKU_MODEL": CANDIDATE_HAIKU}):
            _call(client, copied)

        assert client.captured[0]["model"] == CANDIDATE_HAIKU

    def test_only_the_named_pin_moves(self, _rows):
        client = _Client()

        with analyzer.model_overrides({"SONNET_MODEL": CANDIDATE_SONNET}):
            _call(client, HAIKU_MODEL)
            _call(client, SONNET_MODEL)

        assert [c["model"] for c in client.captured] == [HAIKU_MODEL, CANDIDATE_SONNET]
        assert "pinned_model" not in _rows[0]
        assert _rows[1]["pinned_model"] == SONNET_MODEL

    def test_a_model_that_is_not_a_pin_is_not_swapped(self, _rows):
        client = _Client()

        with analyzer.model_overrides({"SONNET_MODEL": CANDIDATE_SONNET}):
            _call(client, CANDIDATE_HAIKU)  # priced and listed, but not a pin

        assert client.captured[0]["model"] == CANDIDATE_HAIKU
        assert "pinned_model" not in _rows[0]

    def test_the_overridden_row_is_priced_as_the_candidate(self, _rows):
        client = _Client()
        with analyzer.model_overrides({"SONNET_MODEL": CANDIDATE_SONNET}):
            _call(client)

        expected = compute_call_cost({**_rows[0], "model": CANDIDATE_SONNET})
        assert compute_call_cost(_rows[0]) == expected
        # ...which is not the pin's price, so the row cannot be mistaken for a baseline call.
        assert MODEL_PRICING[CANDIDATE_SONNET] != MODEL_PRICING[SONNET_MODEL]

    def test_the_context_resets_after_the_block_and_after_an_exception(self):
        with analyzer.model_overrides({"SONNET_MODEL": CANDIDATE_SONNET}):
            assert analyzer.active_model_overrides() == {"SONNET_MODEL": CANDIDATE_SONNET}
        assert analyzer.active_model_overrides() == {}

        with (
            pytest.raises(RuntimeError),
            analyzer.model_overrides({"HAIKU_MODEL": CANDIDATE_HAIKU}),
        ):
            raise RuntimeError("boom")
        assert analyzer.active_model_overrides() == {}

    def test_active_overrides_returns_a_copy(self):
        with analyzer.model_overrides({"SONNET_MODEL": CANDIDATE_SONNET}):
            analyzer.active_model_overrides()["SONNET_MODEL"] = "tampered"
            assert analyzer.active_model_overrides() == {"SONNET_MODEL": CANDIDATE_SONNET}


class TestRefusals:
    """Each refusal raises from the context manager, before any request exists (C-11)."""

    @pytest.mark.parametrize(
        ("overrides", "match"),
        [
            ({"OPUS_MODEL": CANDIDATE_SONNET}, "Unknown model override key"),
            ({"sonnet": CANDIDATE_SONNET}, "Unknown model override key"),
            ({"SONNET_MODEL": SONNET_MODEL}, "already the pin"),
            ({"HAIKU_MODEL": HAIKU_MODEL}, "already the pin"),
            ({"SONNET_MODEL": "claude-unlisted-9"}, "THINKING_POLICY"),
            # Priced + policy-listed targets only. Opus 5.5 is priced (it is the golden-set author's
            # model, evals/golden_author.py) but has no THINKING_POLICY row on purpose, so it stays refused.
            ({"SONNET_MODEL": "claude-opus-5-5"}, "THINKING_POLICY"),
            ({"SONNET_MODEL": ""}, "non-empty"),
            ({"SONNET_MODEL": 5}, "non-empty"),
        ],
    )
    def test_refused_overrides(self, overrides, match):
        client = _Client()

        with pytest.raises(ValueError, match=match), analyzer.model_overrides(overrides):
            _call(client)

        assert client.captured == []  # nothing left the process
        assert analyzer.active_model_overrides() == {}

    def test_a_listed_but_unpriced_target_is_refused(self, monkeypatch):
        monkeypatch.setitem(analyzer.THINKING_POLICY, "claude-test-unpriced", None)

        with (
            pytest.raises(ValueError, match="MODEL_PRICING"),
            analyzer.model_overrides({"SONNET_MODEL": "claude-test-unpriced"}),
        ):
            pass

    def test_a_bad_entry_activates_nothing_even_if_an_earlier_one_was_good(self):
        with (
            pytest.raises(ValueError, match="Unknown model override key"),
            analyzer.model_overrides(
                {"SONNET_MODEL": CANDIDATE_SONNET, "NOPE_MODEL": CANDIDATE_HAIKU}
            ),
        ):
            pass
        assert analyzer.active_model_overrides() == {}


def test_the_eval_judge_send_does_not_follow_a_model_override():
    """The judge calls `client.messages.create(model=JUDGE_MODEL)` directly, never `_call_llm`."""
    import evals.runner as runner

    sent: dict = {}

    class _JudgeMessages:
        def create(self, **kwargs):
            sent.update(kwargs)
            raise RuntimeError("stop after capturing the request")

    class _JudgeClient:
        messages = _JudgeMessages()

    # `JUDGE_MODEL` is the same string as the Haiku pin today, so a swap by value in the judge
    # path would show up here. The real call site is used so the model is not supplied by the test.
    assert runner.JUDGE_MODEL == HAIKU_MODEL
    with analyzer.model_overrides({"HAIKU_MODEL": CANDIDATE_HAIKU}):
        out = runner._score_distinctiveness(_JudgeClient(), "resume", "jd", "fx")

    assert out["summary"] == "judge_error"  # the stub raised; the judge swallows it by design
    assert sent["model"] == runner.JUDGE_MODEL
