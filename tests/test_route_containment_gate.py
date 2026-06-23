"""Route-containment falsifiability gate — PX-29 (F-sec-05 KEEP) / v1.0.8 item 8.4.

The 2026-06 product-excellence review affirmed route containment as load-bearing
(`F-sec-05`, KEEP): every Flask route that touches the filesystem pairs the
``_safe_username`` + ``_within`` guards (charter **C-1** "local and yours" / S-1).
A ``route-security-lint`` PreToolUse hook enforces this in the dev loop — but the
hook only scans the proposed *Edit diff*, never the committed artifact, so coverage
can drift silently as routes move (the review's explicit WATCH rider on F-sec-05,
and exactly what happened in the 8.3 blueprint split: ``upload_resume`` /
``list_resumes`` lost ``_within`` in body-only move-edits, since restored).

This test commits the hook's intent as a do-not-regress gate over the *whole*
``blueprints/**.py`` tree, so a route added or weakened by any path — not just one
the hook saw — fails CI. It reuses the AST-walk + reviewed-allowlist shape of
``tests/test_egress_allowlist.py`` (the ``SANCTIONED_*`` registry) and
``tests/test_construction_boundary.py``.

The rule (mirrors ``.claude-plugin/hooks/route-security-lint.sh``, applied to the
final post-split layout):

* A route is **filesystem-touching** if its *code* (docstrings and comments
  stripped — see ``_scannable_body``) shows any FS indicator (``open(`` /
  ``send_file(`` / ``Path(`` / ``RESUMES_DIR`` / ``OUTPUT_DIR`` / …). ``CONFIGS_DIR``
  is deliberately NOT an indicator (post-8.3a a route reaches it only as
  ``_safe_username(configs_dir=...)``, which *is* the containment guard).
* Every FS-touching route must call ``_within`` (the resolved-path containment
  check) — unless it appears in ``WITHIN_NOT_REQUIRED`` (containment delegated to a
  sanitizing helper, or a fixed / sanitized-only path).
* Every FS-touching route must call ``_safe_username`` (the user-scoping guard) —
  unless it appears in ``SAFE_USERNAME_NOT_REQUIRED`` (no ``<username>`` to verify:
  a path-/id-keyed download, or the user-creation route).

Each exemption is a reviewed, reasoned entry. A NEW unguarded FS route fails until
it is fixed or deliberately added to the right registry. The two registries waive
exactly one guard each, so teeth are preserved: a no-username download that loses
``_within`` still fails (it is not in ``WITHIN_NOT_REQUIRED``), and an exemption
that later gains its guard is flagged stale.
"""

from __future__ import annotations

import ast
from pathlib import Path

# Repo root: tests/test_route_containment_gate.py -> parents[1].
REPO_ROOT = Path(__file__).resolve().parents[1]
BLUEPRINTS_DIR = REPO_ROOT / "blueprints"

# Flask route decorators: @<bp>.route / .get / .post / .put / .delete / .patch.
_ROUTE_METHODS = frozenset({"route", "get", "post", "put", "delete", "patch"})

# Filesystem-access indicators — the same set the route-security-lint hook uses,
# plus ANNOTATION_ROOT / PERSONAS_DIR (user-scoped dirs the diagnostics/templates
# seams write under). Substring checks over the docstring/comment-free code body:
# over-detecting FS access only ever *requires* a guard (the safe direction).
# CONFIGS_DIR is intentionally absent (see module docstring).
_FS_INDICATORS = (
    "open(",
    "send_file(",
    "send_from_directory(",
    "Path(",
    "read_text(",
    "write_text(",
    ".exists()",
    "os.path.",
    "RESUMES_DIR",
    "OUTPUT_DIR",
    "ANNOTATION_ROOT",
    "PERSONAS_DIR",  # also matches BUNDLED_PERSONAS_DIR (intended)
)

# --- Reviewed exemption registries (keyed "<module>.<funcname>", module relative
# to blueprints/, dotted). Each waives EXACTLY ONE guard, with a reason. ---------

# FS-touching routes that legitimately do NOT call _within directly: containment is
# delegated to a sanitizing helper, or the path is fixed / built only from sanitized
# parts. (They may or may not be user-scoped — that is the other registry's concern.)
WITHIN_NOT_REQUIRED: dict[str, str] = {
    "users.create_user": (
        "User-creation route: the path is RESUMES_DIR / secure_filename(username) "
        "with a refuse-if-empty check, and _save_config re-sanitizes — built only "
        "from sanitized parts, so there is no traversal vector to contain."
    ),
    "diagnostics.annotation_fixtures": (
        "Localhost-gated (_is_localhost_request) read of the FIXED ANNOTATION_ROOT "
        "tree (iterdir); no user-supplied path component, so no traversal vector. "
        "The diagnostics analog of the dashboard routes the hook excludes."
    ),
    "templates.preview_candidate_html": (
        "FS access is delegated: the user-influenced template path is resolved "
        "through _resolve_persona_template_path, which enforces _within(PERSONAS_DIR); "
        "the fallback is the fixed bundled classic.html. The route still scopes the "
        "candidate via _safe_username."
    ),
}

# FS-touching routes that legitimately do NOT call _safe_username: no <username> to
# verify. (They MUST still be contained — via _within, or via WITHIN_NOT_REQUIRED.)
SAFE_USERNAME_NOT_REQUIRED: dict[str, str] = {
    "generation.download_file": (
        "Path-keyed (/api/download/<path:filepath>): no <username>. "
        "Contained by _within(full_path, OUTPUT_DIR)."
    ),
    "templates.download_persona": (
        "Id-keyed (/api/personas/<int:persona_id>/download): no <username>. "
        "Contained by _within(disk_path, PERSONAS_DIR)."
    ),
    "templates.delete_persona": (
        "Id-keyed (DELETE /api/personas/<int:persona_id>): no <username>. "
        "Contained by _within before unlink."
    ),
    "users.create_user": (
        "User-creation route: the user does not yet exist, so _safe_username's "
        "existence check cannot apply; secure_filename(username) + refuse-if-empty "
        "is the scoping guard."
    ),
    "diagnostics.annotation_fixtures": (
        "Localhost-gated listing of the fixed ANNOTATION_ROOT tree: no <username> "
        "and no user-supplied path component."
    ),
}


class RouteInfo:
    """A route handler discovered in a blueprint module."""

    def __init__(self, key: str, url: str, body: str) -> None:
        self.key = key  # "<module>.<funcname>"
        self.url = url
        self.body = body  # docstring/comment-free code (see _scannable_body)

    @property
    def is_fs_touching(self) -> bool:
        return any(tok in self.body for tok in _FS_INDICATORS)

    @property
    def has_within(self) -> bool:
        return "_within(" in self.body

    @property
    def has_safe_username(self) -> bool:
        return "_safe_username(" in self.body


def _module_key(path: Path) -> str:
    """blueprints/corpus/curation.py -> 'corpus.curation'; generation.py -> 'generation'."""
    rel = path.relative_to(BLUEPRINTS_DIR).with_suffix("")
    return ".".join(rel.parts)


def _scannable_body(node: ast.FunctionDef) -> str:
    """Comment- and docstring-free code for a function.

    ``ast.unparse`` regenerates source from the AST, which carries no comments, so a
    guard/indicator named only in a comment never trips detection. The leading
    docstring node (an ``Expr`` wrapping a ``str`` constant) is dropped too, so a
    route that merely *mentions* OUTPUT_DIR / _safe_username in prose is not
    mis-classified (e.g. ``get_application_composition``, whose containment is
    delegated and named only in its docstring).
    """
    stmts = node.body
    if (
        stmts
        and isinstance(stmts[0], ast.Expr)
        and isinstance(stmts[0].value, ast.Constant)
        and isinstance(stmts[0].value.value, str)
    ):
        stmts = stmts[1:]
    return "\n".join(ast.unparse(s) for s in stmts)


def _route_decorator_url(node: ast.FunctionDef) -> str | None:
    """If the function carries a Flask route decorator, return its URL string
    (or "" when the URL is non-literal); else None (not a route handler)."""
    for dec in node.decorator_list:
        if not isinstance(dec, ast.Call):
            continue
        func = dec.func
        if isinstance(func, ast.Attribute) and func.attr in _ROUTE_METHODS:
            if dec.args and isinstance(dec.args[0], ast.Constant) and isinstance(dec.args[0].value, str):
                return dec.args[0].value
            return ""
    return None


def _blueprint_py_files() -> list[Path]:
    return [p for p in BLUEPRINTS_DIR.rglob("*.py") if "__pycache__" not in p.parts]


def _all_routes() -> list[RouteInfo]:
    routes: list[RouteInfo] = []
    for path in _blueprint_py_files():
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        module = _module_key(path)
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            url = _route_decorator_url(node)
            if url is None:
                continue
            routes.append(RouteInfo(f"{module}.{node.name}", url, _scannable_body(node)))
    return routes


# --------------------------------------------------------------------------- #
# 1. The walk has teeth — it actually finds the route surface.
# --------------------------------------------------------------------------- #
def test_route_walk_finds_the_surface() -> None:
    """No vacuous pass: the AST walk must find the bulk of the ~75-route surface and
    a healthy set of FS-touching routes. A broken walk (0 routes) would make every
    assertion below pass for the wrong reason."""
    routes = _all_routes()
    assert len(routes) >= 60, f"expected the full blueprint route surface, found {len(routes)}"
    fs = [r for r in routes if r.is_fs_touching]
    assert len(fs) >= 8, f"expected several FS-touching routes, found {len(fs)}"


# --------------------------------------------------------------------------- #
# 1b. The classifier has teeth — it flags an unguarded FS route.
# --------------------------------------------------------------------------- #
def test_classifier_flags_a_synthetic_unguarded_route() -> None:
    """A synthetic FS-touching route with neither guard must classify as
    FS-touching + missing both — so the offender arms below are not vacuously
    green. Mirrors test_egress_allowlist.test_disable_socket_has_teeth."""
    bad = RouteInfo("synthetic.evil", "/api/x/<username>", "p = OUTPUT_DIR / username\nopen(p)")
    assert bad.is_fs_touching
    assert not bad.has_within
    assert not bad.has_safe_username

    good = RouteInfo(
        "synthetic.ok",
        "/api/x/<username>",
        "_safe_username(username)\n_within(p, OUTPUT_DIR)\nsend_file(p)",
    )
    assert good.is_fs_touching and good.has_within and good.has_safe_username

    # A guard named only in a comment/docstring does not count (call-form detection).
    commentish = RouteInfo("synthetic.cmt", "/api/x", "x = 1  # _within and _safe_username")
    assert not commentish.has_within and not commentish.has_safe_username


# --------------------------------------------------------------------------- #
# 2. Every FS-touching route is contained (_within), or reviewed-exempt.
# --------------------------------------------------------------------------- #
def test_every_fs_route_has_within_containment() -> None:
    """The resolved-path containment check is required on every FS-touching route,
    except the reviewed WITHIN_NOT_REQUIRED set (delegated / fixed / sanitized-only).
    The 8.3 drift that dropped _within from upload_resume / list_resumes is what this
    asserts can never recur."""
    offenders = sorted(
        r.key
        for r in _all_routes()
        if r.is_fs_touching and not r.has_within and r.key not in WITHIN_NOT_REQUIRED
    )
    assert not offenders, (
        f"FS-touching blueprint route(s) missing the _within containment guard: {offenders}. "
        "Call _within(path, parent) (charter C-1 / F-sec-05) — or, if containment is "
        "genuinely delegated/fixed, add the route to WITHIN_NOT_REQUIRED with a reason."
    )


# --------------------------------------------------------------------------- #
# 3. Every FS-touching route is user-scoped (_safe_username), or reviewed-exempt.
# --------------------------------------------------------------------------- #
def test_every_fs_route_is_user_scoped() -> None:
    """An FS-touching route must call _safe_username, except the reviewed
    SAFE_USERNAME_NOT_REQUIRED set (no <username> to verify)."""
    offenders = sorted(
        r.key
        for r in _all_routes()
        if r.is_fs_touching
        and not r.has_safe_username
        and r.key not in SAFE_USERNAME_NOT_REQUIRED
    )
    assert not offenders, (
        f"FS-touching blueprint route(s) missing _safe_username: {offenders}. "
        "Scope the route to a sanitized, known user via _safe_username — or, if it "
        "genuinely has no <username>, add it to SAFE_USERNAME_NOT_REQUIRED with a reason."
    )


# --------------------------------------------------------------------------- #
# 4. The exemption registries stay tight (no rot).
# --------------------------------------------------------------------------- #
def test_no_stale_within_exemptions() -> None:
    """A WITHIN_NOT_REQUIRED entry is stale if its route is gone / no longer
    FS-touching, or now calls _within (the carve-out is no longer needed)."""
    by_key = {r.key: r for r in _all_routes()}
    stale: list[str] = []
    for key in WITHIN_NOT_REQUIRED:
        route = by_key.get(key)
        if route is None or not route.is_fs_touching:
            stale.append(f"{key} (no longer an FS-touching route)")
        elif route.has_within:
            stale.append(f"{key} (now calls _within — exemption unnecessary)")
    assert not stale, (
        f"Stale _within exemption(s): {stale}. Remove from WITHIN_NOT_REQUIRED."
    )


def test_no_stale_safe_username_exemptions() -> None:
    """A SAFE_USERNAME_NOT_REQUIRED entry is stale if its route is gone / no longer
    FS-touching, or now calls _safe_username (the carve-out is no longer needed)."""
    by_key = {r.key: r for r in _all_routes()}
    stale: list[str] = []
    for key in SAFE_USERNAME_NOT_REQUIRED:
        route = by_key.get(key)
        if route is None or not route.is_fs_touching:
            stale.append(f"{key} (no longer an FS-touching route)")
        elif route.has_safe_username:
            stale.append(f"{key} (now calls _safe_username — exemption unnecessary)")
    assert not stale, (
        f"Stale _safe_username exemption(s): {stale}. Remove from SAFE_USERNAME_NOT_REQUIRED."
    )
