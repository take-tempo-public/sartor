"""A duck-typed stand-in for the Anthropic client's streaming surface (item 181 tests).

Just enough of `client.messages.stream(...)` for the real `_call_llm_streaming` to run against:
a context manager with `text_stream`, `get_final_message()` and a `request_id`. Each queued
item is one call's stream; a stream built with ``fail=`` raises when its text is read, which is
how a test makes the send itself fail. Bodies are untyped like the rest of tests/.
"""

from __future__ import annotations


class FakeUsage:
    input_tokens = 10
    output_tokens = 5
    cache_creation_input_tokens = 0
    cache_read_input_tokens = 0


class FakeFinal:
    stop_reason = "end_turn"
    model = "claude-x"

    def __init__(self):
        self.usage = FakeUsage()


class FakeStream:
    def __init__(self, text, fail=None):
        self._text = text
        self._fail = fail
        self.request_id = "req_1"

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    @property
    def text_stream(self):
        if self._fail is not None:
            raise self._fail
        yield self._text

    def get_final_message(self):
        return FakeFinal()


class FakeMessages:
    def __init__(self, items):
        self._items = list(items)

    def stream(self, **kwargs):
        return self._items.pop(0)


class FakeClient:
    """Queue of streams; the Nth `messages.stream(...)` call returns the Nth item."""

    def __init__(self, *items):
        self.messages = FakeMessages(items)
