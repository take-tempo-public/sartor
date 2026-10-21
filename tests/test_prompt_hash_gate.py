"""The system-prompt lock gate (item 181, charter C-11).

`evals/prompt_hashes.json` holds a hash per system prompt and the version it was locked under.
A prompt edit with no version bump used to pass every check (`PROMPT_VERSION` was convention
plus a reviewer); the live test below turns that into a failing gate. The unit tests pin the
two failure messages and the `--write` refusal on synthetic locks, so they cannot pass by
accident while the live prompts happen to match.

Declared limit: a hand-edited lock (hash and version both edited) passes, and user-prompt
templates are not covered. See `scripts/prompt_lock.py`.
"""

from __future__ import annotations

import json

import pytest

import analyzer
from scripts import prompt_lock


def _lock(**over):
    base = {
        "prompt_version": "v1",
        "avatar_prompt_version": "a1",
        "prompts": {"SYSTEM_PROMPT": "sha256:aa", "AVATAR_SYSTEM_PROMPT": "sha256:bb"},
    }
    base.update(over)
    return base


# ---------- the live gate -------------------------------------------------------------


def test_the_committed_lock_matches_the_code():
    issues = prompt_lock.problems(prompt_lock.load(), prompt_lock.current())
    assert issues == [], "\n".join(issues)


def test_every_module_level_system_prompt_is_locked():
    """Extends the registry drift guard in test_prompt_overrides: a new persona constant that
    nobody registered in the lock would be an unguarded prompt."""
    locked = set(prompt_lock.load()["prompts"])
    in_module = {
        name
        for name, value in vars(analyzer).items()
        if name.endswith("SYSTEM_PROMPT") and isinstance(value, str)
    }
    assert in_module <= locked, f"unlocked prompt constants: {sorted(in_module - locked)}"


def test_the_lock_file_is_lf_only_and_ends_with_a_newline():
    raw = prompt_lock.LOCK_PATH.read_bytes()
    assert b"\r" not in raw
    assert raw.endswith(b"\n")


# ---------- the failure modes ----------------------------------------------------------


def test_changed_hash_with_unchanged_version_fails_naming_the_prompt():
    cur = _lock(prompts={"SYSTEM_PROMPT": "sha256:CHANGED", "AVATAR_SYSTEM_PROMPT": "sha256:bb"})
    issues = prompt_lock.problems(_lock(), cur)
    assert len(issues) == 1
    assert "version did not" in issues[0]
    assert "SYSTEM_PROMPT" in issues[0]
    assert "AVATAR_SYSTEM_PROMPT" not in issues[0]


def test_a_new_prompt_without_a_bump_fails():
    cur = _lock(
        prompts={
            "SYSTEM_PROMPT": "sha256:aa",
            "AVATAR_SYSTEM_PROMPT": "sha256:bb",
            "NEW_SYSTEM_PROMPT": "sha256:cc",
        }
    )
    assert "NEW_SYSTEM_PROMPT" in prompt_lock.problems(_lock(), cur)[0]


def test_a_removed_prompt_without_a_bump_fails():
    cur = _lock(prompts={"SYSTEM_PROMPT": "sha256:aa"})
    assert "AVATAR_SYSTEM_PROMPT" in prompt_lock.problems(_lock(), cur)[0]


def test_bumping_the_wrong_version_does_not_excuse_the_avatar_prompt():
    cur = _lock(
        prompt_version="v2",
        prompts={"SYSTEM_PROMPT": "sha256:aa", "AVATAR_SYSTEM_PROMPT": "sha256:CHANGED"},
    )
    issues = prompt_lock.problems(_lock(), cur)
    assert "AVATAR_SYSTEM_PROMPT" in issues[0]
    assert "version did not" in issues[0]


def test_a_bump_with_a_changed_hash_asks_for_the_lock_to_be_refreshed_not_for_a_bump():
    cur = _lock(
        prompt_version="v2",
        prompts={"SYSTEM_PROMPT": "sha256:CHANGED", "AVATAR_SYSTEM_PROMPT": "sha256:bb"},
    )
    issues = prompt_lock.problems(_lock(), cur)
    assert len(issues) == 1
    assert "stale" in issues[0]
    assert "--write" in issues[0]


def test_a_version_bump_with_identical_hashes_is_a_stale_lock():
    """A user-template-only change legitimately bumps the version; the lock must follow it."""
    issues = prompt_lock.problems(_lock(), _lock(prompt_version="v2"))
    assert len(issues) == 1 and "stale" in issues[0]


def test_a_matching_lock_has_no_problems():
    assert prompt_lock.problems(_lock(), _lock()) == []


def test_a_missing_lock_is_a_problem():
    assert "missing" in prompt_lock.problems(None, _lock())[0]


# ---------- --write cannot be used to get around the rule ------------------------------


@pytest.fixture
def lock_path(tmp_path, monkeypatch):
    path = tmp_path / "evals" / "prompt_hashes.json"
    monkeypatch.setattr(prompt_lock, "LOCK_PATH", path)
    return path


def test_write_refuses_a_changed_hash_under_an_unchanged_version(lock_path, monkeypatch):
    lock_path.parent.mkdir(parents=True)
    lock_path.write_text(json.dumps(_lock()), encoding="utf-8")
    cur = _lock(prompts={"SYSTEM_PROMPT": "sha256:CHANGED", "AVATAR_SYSTEM_PROMPT": "sha256:bb"})
    monkeypatch.setattr(prompt_lock, "current", lambda: cur)

    refusal = prompt_lock.write()

    assert refusal and "SYSTEM_PROMPT" in refusal[0]
    assert json.loads(lock_path.read_text(encoding="utf-8")) == _lock()  # untouched


def test_write_accepts_the_change_once_the_version_moved(lock_path, monkeypatch):
    lock_path.parent.mkdir(parents=True)
    lock_path.write_text(json.dumps(_lock()), encoding="utf-8")
    cur = _lock(
        prompt_version="v2",
        prompts={"SYSTEM_PROMPT": "sha256:CHANGED", "AVATAR_SYSTEM_PROMPT": "sha256:bb"},
    )
    monkeypatch.setattr(prompt_lock, "current", lambda: cur)

    assert prompt_lock.write() == []
    assert json.loads(lock_path.read_text(encoding="utf-8")) == cur
    assert b"\r" not in lock_path.read_bytes()


def test_write_creates_the_lock_when_there_is_none(lock_path, monkeypatch):
    monkeypatch.setattr(prompt_lock, "current", lambda: _lock())
    assert prompt_lock.write() == []
    assert prompt_lock.load() == _lock()
