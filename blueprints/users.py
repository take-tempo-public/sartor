"""Users / config seam — the SPA shell + per-user config CRUD + profile fetch.

The sixth domain blueprint extracted from `app.py` (Sprint 8.3g, the app.py ->
blueprints decomposition). Owns the six routes that serve the single-page-app
shell, list/create users, read/write a user's `configs/<user>.config`, and run the
opt-in profile scrape:

    GET    /                                       index
    GET    /api/users                              list_users
    POST   /api/users                              create_user
    GET    /api/users/<u>/config                   get_config
    PUT    /api/users/<u>/config                   update_config
    POST   /api/users/<u>/profile/fetch            fetch_profile

Reads paths from `current_app.config[...]` at request time (never a module-global
import) and shares the security / config-io / provisioning helpers from
`web_infra` — so a test isolates the routes with
`create_app(Config(base_dir=tmp_path))`, no monkeypatching of module globals. The
blueprint never imports `app.py` (leaf-ward direction only); the DB-layer and
`scraper` imports stay lazy inside `fetch_profile`, as in the monolith.

None of these routes call an LLM. `fetch_profile`'s only network egress happens
inside `scraper.py` (already on the PX-08 egress allowlist) — this module imports
no network library, so it is NOT on the egress allowlist.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, cast

from flask import (
    Blueprint,
    current_app,
    jsonify,
    make_response,
    render_template,
    request,
)
from flask.typing import ResponseReturnValue
from werkzeug.utils import secure_filename

from hardening import validate_config
from web_infra import (
    _get_or_provision_candidate,
    _load_config,
    _safe_username,
    _save_config,
    _within,
)

if TYPE_CHECKING:
    from db.models import Candidate

logger = logging.getLogger(__name__)

users_bp = Blueprint("users", __name__)


@users_bp.route("/")
def index() -> ResponseReturnValue:
    """Serve the single-page app shell.

    Cache headers are set to `no-cache` so a freshly-deployed
    `templates/index.html` is always picked up on the next request —
    avoids the "I shipped a UI change but the user still sees the old
    button set" footgun. Static CSS/JS continue to use Flask's
    default caching; we cache-bust those by file path when needed.
    """
    resp = make_response(render_template("index.html"))
    resp.headers["Cache-Control"] = "no-cache, must-revalidate"
    return resp


@users_bp.route("/api/users", methods=["GET"])
def list_users() -> ResponseReturnValue:
    """List the usernames of all saved candidate configs."""
    configs_dir = current_app.config["CONFIGS_DIR"]
    users = [p.stem for p in configs_dir.glob("*.config")]
    return jsonify(users)


@users_bp.route("/api/users", methods=["POST"])
def create_user() -> ResponseReturnValue:
    """Create a user: write a default profile config and seed their resumes directory."""
    data = request.json
    username = data.get("username", "").strip()
    if not username:
        return jsonify({"error": "Username required"}), 400
    safe = secure_filename(username)
    if not safe:
        return jsonify({"error": "Invalid username"}), 400

    config = {
        "name": data.get("name", username),
        "email": data.get("email", ""),
        "phone": data.get("phone", ""),
        "linkedin_url": data.get("linkedin_url", ""),
        "website_url": data.get("website_url", ""),
        "portfolio_urls": [],
        "skills": [],
        "certifications": [],
        "education_summary": "",
        "notes": "",
    }
    _save_config(safe, config, configs_dir=current_app.config["CONFIGS_DIR"])
    (current_app.config["RESUMES_DIR"] / safe).mkdir(exist_ok=True)
    logger.info("Created user: %s", safe)
    return jsonify({"username": safe, "config": config})


@users_bp.route("/api/users/<username>/config", methods=["GET"])
def get_config(username: str) -> ResponseReturnValue:
    """Return one user's saved profile config (404 if the user is unknown)."""
    if not secure_filename(username):
        return jsonify({"error": "Invalid username"}), 400
    config = _load_config(username, configs_dir=current_app.config["CONFIGS_DIR"])
    if not config:
        return jsonify({"error": "User not found"}), 404
    return jsonify(config)


@users_bp.route("/api/users/<username>/config", methods=["PUT"])
def update_config(username: str) -> ResponseReturnValue:
    """Validate and persist one user's full profile config."""
    if not secure_filename(username):
        return jsonify({"error": "Invalid username"}), 400
    config = request.json
    errors = validate_config(config)
    if errors:
        return jsonify({"errors": errors}), 400
    _save_config(username, config, configs_dir=current_app.config["CONFIGS_DIR"])
    logger.info("Updated config for: %s", username)
    return jsonify({"ok": True})


@users_bp.route("/api/users/<username>/profile/fetch", methods=["POST"])
def fetch_profile(username: str) -> ResponseReturnValue:
    """PX-02: opt-in scrape of the user's saved profile URLs into the corpus.

    User-triggered by the Settings "Fetch profile content" button — that click
    IS the opt-in act. Reads the SAVED config (linkedin_url / website_url /
    portfolio_urls), runs the deterministic, best-effort
    `scraper.fetch_profile_content` (per-URL cap; `RequestException` swallowed →
    ""), and caches the combined text in `Candidate.online_profile_text`. From
    there `build_context_set_from_db` surfaces it to the LLM via the
    `<candidate_web_presence>` block.

    The network egress happens inside `scraper.py` (already on the PX-08 egress
    allowlist); this route imports no network library. Stored as a DISTINCT
    column from `profile_text` (the β.6 positioning summary) so the scrape can
    never clobber the résumé `basics.summary`.
    """
    from db.session import get_session, init_db
    from scraper import fetch_profile_content

    configs_dir = current_app.config["CONFIGS_DIR"]
    safe_user = _safe_username(username, configs_dir=configs_dir)
    if not safe_user:
        return jsonify({"error": "Invalid or unknown user"}), 400
    # Defensive containment: the config we read must resolve within CONFIGS_DIR.
    config_path = configs_dir / f"{safe_user}.config"
    if not _within(config_path, configs_dir):
        return jsonify({"error": "Invalid config path"}), 403

    config = _load_config(safe_user, configs_dir=configs_dir)
    url_count = sum(
        1
        for u in (
            config.get("linkedin_url", ""),
            config.get("website_url", ""),
            *config.get("portfolio_urls", []),
        )
        if u
    )
    scraped = fetch_profile_content(config)

    init_db()
    session = get_session()
    try:
        candidate = cast(
            "Candidate",
            _get_or_provision_candidate(
                session,
                safe_user,
                configs_dir=configs_dir,
            ),
        )
        candidate.online_profile_text = scraped or None
        session.commit()
    finally:
        session.close()

    logger.info(
        "PX-02 profile fetch for %s: %d chars from %d configured URL(s)",
        safe_user,
        len(scraped),
        url_count,
    )
    return jsonify({"ok": True, "chars": len(scraped), "urls": url_count})
