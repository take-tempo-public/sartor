"""Flask server — application factory + WSGI handle + console entry point.

P8 Strategic Human Gate: workflow enforces two review points.
P7 Observability: structured logging throughout.

As of Sprint 8.3h every route lives on a domain blueprint (`blueprints/` +
the read-only `dashboard/`); this module is the thin composition root — the
`create_app` factory, the module-level WSGI / console handle, and `main()`. No
`@app.route` handlers, no path globals, no per-request helpers remain here (they
moved to the blueprints + the leaf `web_infra` package across Sprints 8.3a–h).
"""

import logging
import os
import threading
import webbrowser

from flask import Flask

from blueprints import (
    analysis_bp,
    applications_bp,
    assistant_bp,
    corpus_bp,
    diagnostics_bp,
    generation_bp,
    templates_bp,
    users_bp,
)
from config import Config
from dashboard import dashboard_bp

# P7 Observability: structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


def register_blueprints(app: Flask) -> None:
    """Register every blueprint in one place (called by the factory)."""
    app.register_blueprint(dashboard_bp, url_prefix="/_dashboard")
    app.register_blueprint(assistant_bp, url_prefix="/api/assistant")
    # No url_prefix: the analysis routes carry full paths (/api/analyze, /api/clarify,
    # …) and share no common sub-prefix, so the URLs stay byte-identical (Sprint 8.3b).
    app.register_blueprint(analysis_bp)
    # No url_prefix: same as analysis — the generation routes carry full paths
    # (/api/generate, /api/save-edits, /api/download/…, …) (Sprint 8.3c).
    app.register_blueprint(generation_bp)
    # No url_prefix: the corpus routes carry full paths (/api/users/<u>/experiences,
    # /api/bullets/<id>, /api/proposals/<id>/critique, …) and share no common
    # sub-prefix, so the URLs stay byte-identical (Sprint 8.3d).
    app.register_blueprint(corpus_bp)
    # No url_prefix: the templates/personas routes carry full paths
    # (/api/personas/<id>, /api/users/<u>/personas, /api/applications/<id>/preview,
    # …), so the URLs stay byte-identical (Sprint 8.3e).
    app.register_blueprint(templates_bp)
    # No url_prefix: the applications routes carry full paths
    # (/api/users/<u>/applications, /api/applications/<id>/composition, …), so the
    # URLs stay byte-identical (Sprint 8.3f).
    app.register_blueprint(applications_bp)
    # No url_prefix: the users/config routes carry full paths (/, /api/users,
    # /api/users/<u>/config, /api/users/<u>/profile/fetch), so the URLs stay
    # byte-identical (Sprint 8.3g).
    app.register_blueprint(users_bp)
    # No url_prefix: the diagnostics routes (annotation / bootstrap / eval / tune)
    # carry full paths (/api/annotation/…, /api/eval/run, /api/tune/run), so the URLs
    # stay byte-identical (Sprint 8.3h — the last seam; app.py now has zero routes).
    app.register_blueprint(diagnostics_bp)


def create_app(config: Config | None = None) -> Flask:
    """Application factory (Sprint 8.3a).

    The composition root: builds the Flask app from an injected `Config`
    (defaulting to production paths), pushes the config, ensures the runtime
    directories exist (the old import-time mkdir loop), and registers the
    blueprints. The side effects that importing this module used to trigger now
    happen here, when the factory is called.
    """
    app = Flask(__name__)
    config = config or Config()
    app.config.update(config.as_flask_config())
    # Disable browser caching of /static/* responses so UI edits land on
    # the next page reload without requiring a Flask restart or a manual
    # cache-bust query string. The `/` route also sets `Cache-Control:
    # no-cache` (see the `index` view) so the HTML shell is covered too.
    # Local-first single-tenant tool: cache-friendliness has no real
    # payoff here, and the alternative (cache-buster query strings,
    # process-start tokens, etc.) bites whenever the developer or user
    # forgets to restart.
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
    config.ensure_dirs()
    register_blueprints(app)
    return app


# Module-level WSGI / console-script (`callback = app:main`) / back-compat handle.
# Every route attaches via a blueprint inside `register_blueprints` (called by the
# factory), so a freshly-built `create_app(...)` in a test carries the full route
# map — there are no longer any module-level `@app.route` handlers to miss.
app = create_app()


def _should_open_browser(
    werkzeug_run_main: str | None, no_browser: str | None
) -> bool:
    """Decide whether THIS process should auto-open the default browser.

    Open exactly once at startup. In debug mode Flask's reloader runs ``main()``
    in BOTH a persistent supervisor (``WERKZEUG_RUN_MAIN`` unset) and a serving
    child that is RE-EXECUTED on every reload (``WERKZEUG_RUN_MAIN == "true"``).
    Opening in the child re-popped a browser window on every restart (the
    "stray windows" bug); open only when this is NOT the reload child. The
    non-debug single process (also unset) likewise opens once. Honors the
    ``CALLBACK_NO_BROWSER=1`` opt-out for headless / remote / CI runs.
    """
    if no_browser == "1":
        return False
    return werkzeug_run_main != "true"


def main() -> None:
    """Launch the Flask app on http://localhost:5000.

    Entry point for the `callback` console script registered in
    `pyproject.toml [project.scripts]`. Equivalent to `python app.py`
    for users who installed via `pip install -e .` or `pip install
    callback`.

    Set `FLASK_DEBUG=0` in the environment to disable Flask's
    reloader + verbose error pages (see SECURITY.md for rationale).
    Set `CALLBACK_NO_BROWSER=1` to skip the auto-open (headless / remote
    / CI runs where launching a browser is unwanted).
    """
    print("\n  callback. — http://localhost:5000\n")
    debug_mode = os.environ.get("FLASK_DEBUG", "1") == "1"

    # Auto-open the user's default browser so `python app.py` lands them
    # straight on the app. Under Flask's reloader (debug=True) main() runs in
    # BOTH a persistent supervisor (WERKZEUG_RUN_MAIN unset) and a serving child
    # that is re-executed on EVERY reload (WERKZEUG_RUN_MAIN == "true"). Opening
    # in the child re-popped a window per reload (the stray-windows bug), so we
    # open in the supervisor / single process — exactly once. A short Timer
    # delays the open until the server is listening; it runs as a daemon so it
    # never holds the interpreter open on shutdown.
    if _should_open_browser(
        os.environ.get("WERKZEUG_RUN_MAIN"), os.environ.get("CALLBACK_NO_BROWSER")
    ):
        def _open_browser() -> None:
            try:
                webbrowser.open("http://localhost:5000")
            except Exception as exc:  # best-effort; the URL is already printed
                logger.debug("Could not auto-open browser: %s", exc)

        opener = threading.Timer(1.0, _open_browser)
        opener.daemon = True
        opener.start()

    # PX-19: bind loopback only. The host comes from the injected Config
    # (Config.host default "127.0.0.1"), so the dev server is never reachable off
    # the local machine — matching the localhost-only posture SECURITY.md commits
    # to. (A third silent-flip vector is `SERVER_NAME`; leave it unset locally.)
    app.run(host=app.config.get("HOST", "127.0.0.1"), debug=debug_mode, port=5000)


if __name__ == "__main__":
    main()
