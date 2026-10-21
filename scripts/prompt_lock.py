"""The system-prompt lock: a committed hash per prompt, and the rule that a changed hash needs
a bumped version (item 181, charter C-11).

``PROMPT_VERSION`` is a hand-bumped label, so a prompt edit that forgets the bump used to pass
every gate (`docs/governance/enforcement.md`). `evals/prompt_hashes.json` records the hash of
every system prompt the product sends, as `analyzer.py` sends it, beside the version it was
locked under. `tests/test_prompt_hash_gate.py` recomputes the hashes on every gate run:

* a hash differs and its version is unchanged -> fail: the prompt changed, bump the version;
* anything else differs from the lock -> fail: the lock is stale, run ``--write``.

``--write`` refuses to record a changed hash while the version is unchanged, so the lock
cannot be regenerated around the rule. Declared limit (C-0): a hand-edited lock (hash and
version both edited) passes, and only system prompts are covered -- the user-prompt templates
are inline f-strings with dynamic content and stay under the convention.

    python -m scripts.prompt_lock --check   # exit 1 on any problem
    python -m scripts.prompt_lock --write   # refresh after bumping the version
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import call_identity

LOCK_PATH = Path(__file__).resolve().parent.parent / "evals" / "prompt_hashes.json"

# Which version string governs which prompt names. Everything else is under PROMPT_VERSION.
_AVATAR_PROMPTS = frozenset({"AVATAR_SYSTEM_PROMPT"})


def current() -> dict[str, Any]:
    """The lock as the code on disk would write it now."""
    import analyzer
    from onboarding import extract_experiences

    texts = dict(analyzer._BASE_SYSTEM_PROMPTS)
    texts["AVATAR_SYSTEM_PROMPT"] = analyzer.AVATAR_SYSTEM_PROMPT
    texts["EXTRACT_EXPERIENCES_SYSTEM_PROMPT"] = (
        extract_experiences.EXTRACT_EXPERIENCES_SYSTEM_PROMPT
    )
    return {
        "prompt_version": analyzer.PROMPT_VERSION,
        "avatar_prompt_version": analyzer.AVATAR_PROMPT_VERSION,
        "prompts": {name: call_identity.text_sha256(texts[name]) for name in sorted(texts)},
    }


def load() -> dict[str, Any] | None:
    """The committed lock, or ``None`` if it does not exist yet."""
    if not LOCK_PATH.exists():
        return None
    data = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else None


def _group(name: str) -> str:
    return "avatar_prompt_version" if name in _AVATAR_PROMPTS else "prompt_version"


def unbumped_changes(lock: dict[str, Any], cur: dict[str, Any]) -> list[str]:
    """Prompts whose hash differs from (or is absent in) the lock while their version is unchanged."""
    locked = lock.get("prompts", {})
    now = cur["prompts"]
    changed = []
    for name in sorted(set(locked) | set(now)):
        if locked.get(name) == now.get(name):
            continue
        version_key = _group(name)
        if lock.get(version_key) == cur[version_key]:
            changed.append(name)
    return changed


def problems(lock: dict[str, Any] | None, cur: dict[str, Any]) -> list[str]:
    """Why the lock fails the gate; empty when it matches the code exactly."""
    if lock is None:
        return [f"{LOCK_PATH.name} is missing: run `python -m scripts.prompt_lock --write`."]
    out = []
    unbumped = unbumped_changes(lock, cur)
    if unbumped:
        out.append(
            "prompt text changed but its version did not: "
            + ", ".join(unbumped)
            + ". Bump PROMPT_VERSION (AVATAR_PROMPT_VERSION for the avatar prompt) in analyzer.py,"
            " then run `python -m scripts.prompt_lock --write`."
        )
    elif lock != cur:
        out.append(
            f"{LOCK_PATH.name} is stale (a version or a hash differs from the code): run"
            " `python -m scripts.prompt_lock --write`."
        )
    return out


def write() -> list[str]:
    """Write the lock; refuse (return the reasons) if a hash changed under an unchanged version."""
    cur = current()
    lock = load()
    if lock is not None:
        unbumped = unbumped_changes(lock, cur)
        if unbumped:
            return [
                "refusing to lock a changed prompt under an unchanged version: "
                + ", ".join(unbumped)
                + ". Bump the version in analyzer.py first."
            ]
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    # newline="\n": the lock is byte-stable across platforms (a CRLF rewrite is a spurious diff).
    with LOCK_PATH.open("w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(cur, indent=2, sort_keys=True) + "\n")
    return []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="fail if the lock does not match")
    mode.add_argument("--write", action="store_true", help="refresh the lock")
    args = parser.parse_args(argv)
    issues = write() if args.write else problems(load(), current())
    for issue in issues:
        print(f"prompt_lock: {issue}", file=sys.stderr)
    if not issues:
        print(f"prompt_lock: OK ({LOCK_PATH.name})")
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
