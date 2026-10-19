"""Item 137: `hardening.is_candidate_record` is the one definition of "not a baseline record".

A candidate run is one made under a prompt override (its `prompt_version` is `candidate:<hash>`) or a
model override (its records carry `model_overrides`). The eval runner's regression baseline and the
dashboard's baseline views all call this predicate; `analyzer.effective_prompt_version` builds the
prefix from the same constant, so the label and the filter cannot drift apart.
"""

from __future__ import annotations

import pytest

import analyzer
from hardening import CANDIDATE_VERSION_PREFIX, is_candidate_record


@pytest.mark.parametrize(
    ("record", "expected"),
    [
        ({"prompt_version": "2026-10-17.2"}, False),
        ({"prompt_version": ""}, False),
        ({}, False),
        ({"prompt_version": "candidate:0123456789ab"}, True),
        (
            {
                "prompt_version": "2026-10-17.2",
                "model_overrides": {"SONNET_MODEL": "claude-sonnet-5-5"},
            },
            True,
        ),
        ({"prompt_version": "2026-10-17.2", "model_overrides": {}}, False),
        ({"prompt_version": "2026-10-17.2", "model_overrides": None}, False),
        # A non-string version (a malformed record) is a baseline record, not a crash.
        ({"prompt_version": 7}, False),
        ({"prompt_version": None}, False),
    ],
)
def test_is_candidate_record(record, expected):
    assert is_candidate_record(record) is expected


def test_prompt_override_label_uses_the_shared_prefix():
    with analyzer.prompt_overrides({"SYSTEM_PROMPT": "a candidate persona"}):
        version = analyzer.effective_prompt_version()

    assert version.startswith(CANDIDATE_VERSION_PREFIX)
    assert is_candidate_record({"prompt_version": version})
    assert not is_candidate_record({"prompt_version": analyzer.effective_prompt_version()})


def test_a_model_override_does_not_change_the_prompt_version():
    """The two candidate kinds are told apart by different fields; the version stays the real one."""
    with analyzer.model_overrides({"SONNET_MODEL": "claude-sonnet-5-5"}):
        assert analyzer.effective_prompt_version() == analyzer.PROMPT_VERSION
