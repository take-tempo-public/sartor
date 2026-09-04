"""Flask server — application factory + WSGI handle + console entry point.

P8 Strategic Human Gate: workflow enforces two review points.
P7 Observability: structured logging throughout.

As of Sprint 8.3h every route lives on a domain blueprint (`blueprints/` +
the read-only `dashboard/`); this module is the thin composition root — the
`create_app` factory, the module-level WSGI / console handle, and `main()`. No
`@app.route` handlers, no path globals, no per-request helpers remain here (they
moved to the blueprints + the leaf `web_infra` package across Sprints 8.3a–h).
"""

import argparse
import getpass
import logging
import os
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path

from flask import Flask

import preflight
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
from config import STATIC_DIR, TEMPLATES_DIR, Config
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

    `template_folder`/`static_folder` are passed EXPLICITLY (absolute paths,
    resolved via `config.TEMPLATES_DIR`/`STATIC_DIR`) rather than left to
    Flask's `Flask(__name__)` default, which resolves relative to `app.py`'s
    own directory — correct only when `templates/`/`static/` happen to be
    co-located with `app.py` on disk (a source checkout or editable install).
    A real (non-editable) wheel install puts `app.py` directly in
    `site-packages/` without those directories alongside it, which 500'd on
    first page load (PyPI-wheel ledger item, `docs/dev/RELEASE_CHECKLIST.md`).
    The resolved paths are byte-identical to the old default in the
    dev/editable case (see `config._package_dir`).
    """
    app = Flask(__name__, template_folder=str(TEMPLATES_DIR), static_folder=str(STATIC_DIR))
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


# Module-level WSGI / console-script (`sartor = app:main`) / back-compat handle.
# Every route attaches via a blueprint inside `register_blueprints` (called by the
# factory), so a freshly-built `create_app(...)` in a test carries the full route
# map — there are no longer any module-level `@app.route` handlers to miss.
app = create_app()


def _should_open_browser(werkzeug_run_main: str | None, no_browser: str | None) -> bool:
    """Decide whether THIS process should auto-open the default browser.

    Open exactly once at startup. In debug mode Flask's reloader runs ``main()``
    in BOTH a persistent supervisor (``WERKZEUG_RUN_MAIN`` unset) and a serving
    child that is RE-EXECUTED on every reload (``WERKZEUG_RUN_MAIN == "true"``).
    Opening in the child re-popped a browser window on every restart (the
    "stray windows" bug); open only when this is NOT the reload child. The
    non-debug single process (also unset) likewise opens once. Honors the
    ``SARTOR_NO_BROWSER=1`` opt-out for headless / remote / CI runs.
    """
    if no_browser == "1":
        return False
    return werkzeug_run_main != "true"


def _is_ci_or_container() -> bool:
    """Best-effort signal for "this is not an interactive local desktop" (F-18).

    A CI runner or a container, where an auto-opened browser hangs/errors and
    Flask's debug reloader + verbose error pages are an unwanted surprise
    rather than a convenience.

    Two independent, widely-honored signals, either sufficient: ``CI`` (set
    truthy by GitHub Actions, GitLab CI, CircleCI, Travis, and effectively
    every other CI provider) and the presence of ``/.dockerenv`` (written by
    the Docker runtime into every container's filesystem). This is only ever
    consulted as a *default* — an explicit ``SARTOR_NO_BROWSER`` or
    ``FLASK_DEBUG`` always wins (see ``main()``), so it can never override a
    deliberate choice, only fill in a sane one when neither is set. The
    shipped ``Dockerfile`` already sets both explicitly for its own image;
    this covers the ad-hoc case (a bare ``python app.py`` run inside a
    devcontainer, Codespace, or CI smoke step, outside that image).
    """
    ci_env = os.environ.get("CI", "").strip().lower()
    if ci_env not in ("", "0", "false"):
        return True
    return os.path.exists("/.dockerenv")


def _write_api_key(key: str, base_dir: Path | None = None) -> Path:
    """Write `key` to the `.api_key` file with owner-only permissions. Returns the path.

    Created via `os.open` with mode 0o600 rather than `Path.write_text` so the file is
    never, even briefly, world-readable: `write_text` creates at 0o666-minus-umask and a
    follow-up `chmod` leaves a window in between. On Windows the POSIX mode is largely
    inert — stated, not papered over (C-0); the ACL is the real control there, and this
    does not attempt to set one.
    """
    path = preflight.api_key_path(base_dir)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(key.strip() + "\n")
    return path


def _prompt_for_api_key(base_dir: Path | None = None) -> None:
    """Offer a non-echoing key prompt during `--setup` when no key is resolvable (item 104).

    Every documented way to supply the key put it in plaintext shell history —
    `docker run -e ANTHROPIC_API_KEY=…`, `export ANTHROPIC_API_KEY=…`, and
    `echo … > .api_key` alike. A live install (2026-09-02) ended with a test key in
    `~/.zsh_history` on hardware the key's owner did not control, and the user had to be
    walked through scrubbing it — including the non-obvious ordering trap that closing
    the terminal re-flushes in-memory history over the scrubbed file. `getpass` removes
    the exposure and a manual step at once.

    Three deliberate refusals:
      * **Never prompts when a key already resolves** — `--setup` is documented as
        idempotent, and silently re-writing a working key is not that.
      * **Never prompts on a non-interactive stdin.** A container build, a CI step, or a
        piped `--setup` would block forever on a tty read that can never be answered.
      * **Never echoes, logs, or prints the key**, and an empty answer is a valid one:
        the user may be heading for demo mode or setting the key later.
    """
    if preflight.api_key_capability(base_dir).ok:
        return
    if not sys.stdin.isatty():
        print(
            "  No API key found. Set ANTHROPIC_API_KEY, or run `sartor --setup` from a "
            "terminal to be prompted for one without it reaching your shell history.",
            file=sys.stderr,
        )
        return
    print(
        "\n  No Anthropic API key found. Paste one to save it to .api_key "
        "(owner-only, never echoed,\n  and never in your shell history). "
        "Press Enter to skip — `SARTOR_DEMO=1` runs with no key at all."
    )
    try:
        key = getpass.getpass("  API key: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n  Skipped.", file=sys.stderr)
        return
    if not key:
        print("  Skipped. Set ANTHROPIC_API_KEY or create .api_key later.")
        return
    try:
        path = _write_api_key(key, base_dir)
    except OSError as exc:
        print(f"  ! could not write the key file: {exc}", file=sys.stderr)
        return
    print(f"  Key saved to {path} (owner-only).")


def _run_setup(base_dir: Path | None = None) -> int:
    """One-time post-install bootstrap: Chromium (PDF) + the vector index (recall).

    `pip install sartor` fetches neither — they are large runtime downloads (the
    Chromium binary ~150 MB into the OS user cache; the model2vec model ~30 MB
    into a local sidecar) — so a fresh install would hit a cryptic error the first
    time it renders a PDF or the assistant does semantic recall. `sartor --setup`
    does both up front. Idempotent; safe to re-run. Returns a process exit code.
    Both steps run as subprocesses of THIS interpreter so the right venv is used.

    The key prompt (item 104) runs FIRST, before either download: a user with no key
    should learn that in the first second, not after waiting out ~180 MB of transfers.
    It is a no-op when a key already resolves or stdin is not a tty.
    """
    _prompt_for_api_key(base_dir)
    # (install label, the FEATURE the step delivers, argv). The feature name is
    # carried separately because the closing summary names the features that
    # actually failed — see the `degraded` list below (item 102).
    steps: list[tuple[str, str, list[str]]] = [
        (
            "Chromium for PDF output (~150 MB, one-time)",
            "PDF export",
            [sys.executable, "-m", "playwright", "install"]
            + (["--with-deps"] if sys.platform.startswith("linux") else [])
            + ["chromium"],
        ),
        (
            "the semantic-recall vector index (~30 MB model, one-time)",
            "semantic recall",
            [sys.executable, "-m", "scripts.build_vector_index"],
        ),
    ]
    # Item 102: this used to be a single `ok` boolean, so the summary named BOTH
    # features whenever EITHER step failed — observed 2026-09-02 on macOS 12.7.4,
    # where Chromium failed, the index succeeded, and the user still had to be told
    # to `ls db/vector_index/` to find out whether their search was broken. The loop
    # already had the information; it was being discarded into a boolean.
    degraded: list[str] = []
    for i, (label, feature, cmd) in enumerate(steps, start=1):
        print(f"  [{i}/{len(steps)}] Installing {label}…")
        try:
            subprocess.run(cmd, check=True)  # noqa: S603 — fixed, trusted argv (sys.executable + literals)
        except (subprocess.CalledProcessError, OSError) as exc:
            degraded.append(feature)
            print(
                f"      ! failed: {exc}\n        retry manually: {' '.join(cmd)}",
                file=sys.stderr,
            )
    if not degraded:
        print("\n  Setup complete. Run `sartor` to start.\n")
        return 0
    working = [feature for _, feature, _ in steps if feature not in degraded]
    summary = f"\n  Setup finished with warnings (above). `sartor` still runs.\n  Degraded: {' and '.join(degraded)}."
    if working:
        summary += f" Working: {' and '.join(working)}."
    print(summary + "\n", file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> None:
    """Console entry point for `sartor` (and `python app.py`).

    Default (no flags) is unchanged for a local desktop run: serve the app on
    http://localhost:5000, auto-open a browser, and run with Flask's debug
    reloader on. Flags:
      `--doctor`      report this machine's capabilities, then exit (item 100)
      `--setup`       one-time bootstrap (Chromium + vector index), then exit
      `--host`/`--port`  bind override (the container passes `--host 0.0.0.0`)
      `--no-browser`  skip the auto-open (alias for `SARTOR_NO_BROWSER=1`)

    Set `FLASK_DEBUG=0` to disable Flask's reloader + verbose error pages (see
    SECURITY.md). The default host stays loopback-only (127.0.0.1) per PX-19.

    F-18: an explicit `SARTOR_NO_BROWSER` / `FLASK_DEBUG` always wins, but when
    NEITHER is set, `_is_ci_or_container()` fills in the off default (no
    browser open, debug off) instead of the local-desktop default — a bare
    `python app.py` in a CI job or an ad-hoc container/devcontainer no longer
    hangs on a browser open or prints a debug traceback by surprise. The
    shipped `Dockerfile` already sets both env vars explicitly; this only
    covers runs outside that image. See docs/install.md's "Local development"
    section for the full flag/env reference.
    """
    parser = argparse.ArgumentParser(
        prog="sartor",
        description="Local-first résumé + cover-letter tailor — runs a local web app.",
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help="one-time bootstrap: install Chromium (PDF) + build the recall index, then exit",
    )
    parser.add_argument(
        "--doctor",
        action="store_true",
        help="report what this machine can do (Python, OS, key, Chromium, recall), then exit",
    )
    parser.add_argument(
        "--host",
        default=app.config.get("HOST", "127.0.0.1"),
        help="bind host (default 127.0.0.1, loopback only; a container passes 0.0.0.0 and "
        "maps -p 127.0.0.1:5000:5000)",
    )
    parser.add_argument("--port", type=int, default=5000, help="bind port (default 5000)")
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="do not auto-open a browser (same as SARTOR_NO_BROWSER=1)",
    )
    args = parser.parse_args(argv)

    # --doctor before --setup: it is the read-only one, and the whole point of item 100
    # is that a user can find out what will work BEFORE downloading several GB.
    if args.doctor:
        raise SystemExit(preflight.run_doctor())

    if args.setup:
        raise SystemExit(_run_setup())

    print(f"\n  sartor. — http://localhost:{args.port}\n")
    # F-18: FLASK_DEBUG explicit wins; unset defaults to debug-on locally, but
    # debug-off when a CI/container signal is detected (verbose error pages +
    # the reloader are a dev-hostile surprise there, not a convenience).
    flask_debug_env = os.environ.get("FLASK_DEBUG")
    debug_mode = not _is_ci_or_container() if flask_debug_env is None else flask_debug_env == "1"

    # Auto-open the user's default browser so `python app.py` lands them
    # straight on the app. Under Flask's reloader (debug=True) main() runs in
    # BOTH a persistent supervisor (WERKZEUG_RUN_MAIN unset) and a serving child
    # that is re-executed on EVERY reload (WERKZEUG_RUN_MAIN == "true"). Opening
    # in the child re-popped a window per reload (the stray-windows bug), so we
    # open in the supervisor / single process — exactly once. A short Timer
    # delays the open until the server is listening; it runs as a daemon so it
    # never holds the interpreter open on shutdown.
    # F-18: SARTOR_NO_BROWSER (or --no-browser) explicit wins; unset defaults to
    # "open" locally, but "skip" when a CI/container signal is detected — see
    # _is_ci_or_container(). _should_open_browser's own (tested) 2-arg contract
    # is untouched; this only changes what gets passed in as `no_browser`.
    no_browser = "1" if args.no_browser else os.environ.get("SARTOR_NO_BROWSER")
    if no_browser is None and _is_ci_or_container():
        no_browser = "1"
    if _should_open_browser(os.environ.get("WERKZEUG_RUN_MAIN"), no_browser):

        def _open_browser() -> None:
            """Best-effort open the app URL in a browser (logs and ignores any failure)."""
            try:
                webbrowser.open(f"http://localhost:{args.port}")
            except Exception as exc:  # best-effort; the URL is already printed
                logger.debug("Could not auto-open browser: %s", exc)

        opener = threading.Timer(1.0, _open_browser)
        opener.daemon = True
        opener.start()

    # PX-19: default host is loopback only (Config.host = "127.0.0.1"), so the dev
    # server is never reachable off the local machine — matching the localhost-only
    # posture SECURITY.md commits to. `--host 0.0.0.0` (used only by the container,
    # which then maps -p 127.0.0.1:5000:5000 on the host) is the sole exception.
    # (A third silent-flip vector is `SERVER_NAME`; leave it unset locally.)
    app.run(host=args.host, debug=debug_mode, port=args.port)


if __name__ == "__main__":
    main()
