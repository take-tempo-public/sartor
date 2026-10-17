"""The repo's files as git lists them: the one source for a whole-repo scan in a test.

A scan that walks the tree (`REPO_ROOT.rglob`, `os.walk`) reads every checkout nested inside the
clone as if it were this repo. The harness puts `EnterWorktree` checkouts at `.claude/worktrees/`,
so such a scan fails the main checkout's gate with a second copy of every module (item 172,
`docs/dev/diagnosis/gate-skips-linked-worktrees.md`). `git ls-files --cached --others
--exclude-standard` lists tracked files plus untracked-but-not-ignored ones (a new file is
scanned before it is `git add`ed) and does not descend into a nested checkout, whether or not
its path is ignored. It also skips `node_modules` and the other ignored trees without the test
keeping its own exclude list, ~65 ms against 1.3-2.3 s for the walk.

`tests/test_tree_walk_gate.py` fails any new recursive walk that is not listed there.
"""

from __future__ import annotations

import functools
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


@functools.cache
def _listed(root: Path) -> tuple[Path, ...]:
    """Every non-ignored file under `root` that exists on disk, one `git ls-files` call per root."""
    try:
        out = subprocess.run(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            cwd=root,
            check=True,
            capture_output=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        # An empty list would let every scan pass vacuously, so fail instead.
        raise RuntimeError(f"cannot list the repo's files with git under {root}: {exc}") from exc
    paths = (root / name.decode("utf-8") for name in out.split(b"\0") if name)
    # A nested checkout shows as "dir/", and a tracked file deleted from disk is still listed.
    return tuple(p for p in paths if p.is_file())


def repo_files(suffix: str | None = None, *, root: Path = REPO_ROOT) -> list[Path]:
    """Absolute paths of the repo's non-ignored files, optionally only those ending in `suffix`."""
    return [p for p in _listed(root) if suffix is None or p.name.endswith(suffix)]
