#!/usr/bin/env python3
"""Deterministic OpenAPI spec-emission script (spectree/OpenAPI Layer B, Phase 1).

**Why this exists.** Phase 1 of the kit-adoption spectree wiring
(`web_infra/openapi.py`) decorates exactly five read-only GET routes with
`@spec.validate(resp=..., skip_validation=True, ...)`. This script is the
standalone generator that turns that decoration into an actual OpenAPI JSON
artifact: it builds its OWN `create_app()` instance in-process (a throwaway
`Config` rooted at a temp directory — no real `configs/`/`resumes/`/`output/`
writes), calls `spec.register(app)` on THAT instance only, reads the cached
`spec.spec` dict (walks `app.url_map` — no HTTP server, no network), and
writes it as pretty JSON to `docs-site/openapi.json` (a build artifact,
gitignored — CI regenerates it; that wiring is a separate, later branch's job,
same division of labor as `scripts/project_docs_to_mdx.py`'s L1->MDX
projection).

**Scope note.** `mode="strict"` on the shared `spec` instance (see
`web_infra/openapi.py`) means only the 5 decorated routes appear here — the
other ~85 undecorated routes are deliberately NOT included (Phase 1 is
additive + scoped, not a dump of the whole route surface). Fumadocs RENDERING
this JSON into a hosted HTTP-API reference page is out of scope here.

Exit 0 on success, printing a one-line summary. Exit 1 on an unrecoverable
error, or if the generated spec is missing one of the 5 expected paths (a
self-check, not a hard dependency of the generation logic itself).
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = REPO_ROOT / "docs-site" / "openapi.json"

# Guarantee `app`/`config`/`web_infra` resolve to THIS checkout's repo root, not
# whatever `sartor` distribution (if any) happens to be on the interpreter's
# default path — e.g. run as `python scripts/generate_openapi_spec.py`, Python
# puts the script's OWN directory (`scripts/`) on sys.path[0], not the repo
# root, so an editable install pointing at a different clone would otherwise
# silently win. Mirrors tests/test_docs_projection.py's same repo-root insert.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# The 5 routes Phase 1 decorated — blueprints/users.py (list_users, get_config),
# blueprints/corpus/experiences.py (list_experiences), blueprints/applications.py
# (list_applications, get_application). Flask's `<username>`/`<int:...>` path
# converters are emitted by spectree as bare `{name}` OpenAPI path params.
_EXPECTED_PATHS = (
    "/api/users",
    "/api/users/{username}/config",
    "/api/users/{username}/experiences",
    "/api/users/{username}/applications",
    "/api/applications/{application_id}",
)


def build_spec() -> dict[str, Any]:
    """Build a throwaway app, register the shared spectree spec against it, return spec.spec.

    A fresh temp-dir `Config` keeps this side-effect-free against the real
    `configs/`/`resumes/`/`output/` trees — `create_app` only calls
    `Config.ensure_dirs()` (mkdir with `exist_ok=True`) on the temp root.
    """
    from app import create_app
    from config import Config
    from web_infra.openapi import spec

    with tempfile.TemporaryDirectory() as tmp:
        app = create_app(Config(base_dir=Path(tmp)))
        spec.register(app)
        with app.app_context():
            return dict(spec.spec)


def main() -> int:
    try:
        openapi_dict = build_spec()
    except Exception as exc:  # pragma: no cover - defensive top-level guard
        print(f"generate_openapi_spec: FAILED — {exc}", file=sys.stderr)
        return 1

    paths = openapi_dict.get("paths", {})
    missing = [p for p in _EXPECTED_PATHS if p not in paths]
    if missing:
        print(
            f"generate_openapi_spec: FAILED — spec is missing expected path(s): {missing}",
            file=sys.stderr,
        )
        return 1

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(openapi_dict, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    try:
        display_path = OUTPUT_PATH.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        # OUTPUT_PATH monkeypatched outside REPO_ROOT (e.g. a test pointing it at
        # tmp_path) — fall back to the absolute path rather than erroring on the
        # summary line, which carries no behavioral meaning either way.
        display_path = str(OUTPUT_PATH)
    print(f"generate_openapi_spec: OK — {len(paths)} path(s) written to {display_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
