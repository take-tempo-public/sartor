"""Per-user config read/write helpers shared by `app.py` and the blueprints.

`_load_config` / `_save_config` read and write `configs/<user>.config`. Both
sanitize the username with `secure_filename` *at the helper* (PX-21) so the read /
write is contained to the configs directory even when a caller passes raw input —
the containment guarantee holds for any caller, not just pre-sanitized call sites.

They take an explicit `configs_dir` (keyword-only) instead of a module global so a
test can exercise them with a `tmp_path` and no Flask app context; blueprints pass
`current_app.config["CONFIGS_DIR"]`.

P1 Hardening boundary: deterministic, no LLM calls (charter C-6).
"""

from __future__ import annotations

import json
from pathlib import Path

from werkzeug.utils import secure_filename


def _load_config(username: str, *, configs_dir: Path) -> dict:
    # Sanitize here, not only at the call site: secure_filename strips ../ and
    # other traversal sequences, so the config read is contained to configs_dir
    # even when a caller passes raw input (PX-21). An unsafe-empty or missing
    # config resolves to {} (treated as "no such user" by callers).
    safe = secure_filename(username)
    if not safe:
        return {}
    path = configs_dir / f"{safe}.config"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _save_config(username: str, config: dict, *, configs_dir: Path) -> None:
    # Mirror _load_config: sanitize at the helper so the write is contained to
    # configs_dir regardless of the caller (PX-21). An all-stripped username
    # (e.g. "...") is rejected rather than written as a junk ".config" — every
    # real caller (create_user/update_config/upload_resume) pre-sanitizes, so
    # this raise is unreachable defense-in-depth in practice.
    safe = secure_filename(username)
    if not safe:
        raise ValueError(f"unsafe username for config write: {username!r}")
    path = configs_dir / f"{safe}.config"
    path.write_text(json.dumps(config, indent=2), encoding="utf-8")
