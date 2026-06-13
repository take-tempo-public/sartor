"""Network-egress falsifiability gate — PX-08 (F-qe-rel-02 P0, F-sec-01) / G-2.

The 2026-06 product-excellence review (release-pass-plan.md §2 "G-2"; prescriptions.md
now-v1.0.6 band) makes charter claim **C-2** machine-falsifiable: callback. opens an
outbound socket to exactly TWO sanctioned destination classes —

  1. the configured LLM provider host ``api.anthropic.com`` (the ``anthropic`` SDK), and
  2. the opt-in profile/website scrape of ARBITRARY user-supplied URLs
     (``requests`` in ``scraper.py``).

The scrape "host" is not fixed — it's whatever URL the user pastes — so it is gated as a
code-path *class* (the sole ``requests`` importer), not a hostname allowlist. Before this
gate, C-2 was a one-time hand audit: the only network test
(``tests/test_scraper.py``) merely stubs ``requests.get``, so nothing failed if a new
module reached the network or a template re-added a CDN ``<script>`` (exactly the PX-01
regression this gate would have caught by construction).

This file fails if anything opens a socket outside those two classes, or if any Jinja
template references an off-box CDN host. Sockets are disabled for THIS FILE ONLY via the
autouse fixture below (no global ``--disable-socket``), so the rest of the suite and the
``-m ux`` live-server tier are untouched. pytest-socket is inert until explicitly invoked.
"""

from __future__ import annotations

import ast
import re
import socket
from pathlib import Path

import anthropic
import pytest
import pytest_socket
import requests

import scraper

# Repo root: tests/test_egress_allowlist.py -> parents[1].
REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _block_sockets():
    """Disable real sockets for every test in this file; re-enable on teardown.

    Function-scoped + autouse so the block never leaks into another file, even within
    the same process. The no-socket tests (static scans, base_url pin) are unaffected
    because they never touch a guarded primitive.
    """
    pytest_socket.disable_socket()
    try:
        yield
    finally:
        pytest_socket.enable_socket()


# --------------------------------------------------------------------------- #
# 1. The gate has teeth.
# --------------------------------------------------------------------------- #
def test_disable_socket_has_teeth():
    """If the fixture engaged, a raw socket construction is blocked.

    Guards against the "no error" tests below passing for the wrong reason (a silently
    inert block would make them green without proving anything).
    """
    with pytest.raises(pytest_socket.SocketBlockedError):
        socket.socket()


# --------------------------------------------------------------------------- #
# 2. The provider host is pinned to the single sanctioned destination.
# --------------------------------------------------------------------------- #
def test_provider_base_url_pinned():
    """The anthropic SDK targets ``api.anthropic.com`` with no base_url override.

    Constructing the client and reading ``base_url`` opens no socket (verified), so this
    runs cleanly under the block. Fails if a future ``base_url=`` points the LLM egress at
    a proxy or other host — i.e. it pins egress class (1) to its one sanctioned host.
    """
    client = anthropic.Anthropic(api_key="x")
    assert "api.anthropic.com" in str(client.base_url)


# --------------------------------------------------------------------------- #
# 3. The deterministic modules perform no egress at call time.
# --------------------------------------------------------------------------- #
def test_deterministic_modules_make_no_egress():
    """Calling a representative pure function from each deterministic module (the seven
    AGENTS.md guarantees never reach the network/LLM) opens no socket.

    ``pdf_render`` is import-only here: its render path drives a real Chromium subprocess
    (playwright is lazy-imported *inside* its functions), which belongs to the slow/ux
    tier, not this fast gate. The static allowlist (test 4) is what catches a *new*
    network import in any of these; this is the runtime complement.
    """
    import corpus_to_json_resume
    import generator
    import hardening
    import json_resume
    import parser
    import pdf_render  # noqa: F401  (import-only; see docstring)

    # None of these may open a socket; SocketBlockedError would surface if one did.
    assert generator._normalize_markdown("- alpha\n- beta") is not None
    assert isinstance(json_resume.md_to_json_resume("# Jane Doe\n"), dict)
    assert isinstance(corpus_to_json_resume._empty_document(), dict)
    assert isinstance(parser._infer_sections("Experience\nDid the thing"), list)
    assert 0.0 <= hardening.bullet_jaccard("a b c", "a b d") <= 1.0
    # scraper's pure normalizer (the network lives only in fetch_url_content; see test 5).
    assert scraper._ensure_scheme("github.com/you") == "https://github.com/you"


# --------------------------------------------------------------------------- #
# 4. The set of egress-importing modules equals the sanctioned allowlist.
# --------------------------------------------------------------------------- #

# Repo-relative POSIX paths permitted to import a network-egress library. Both sanctioned
# classes live here: anthropic (provider) + requests (scrape). A NEW egress site anywhere
# fails this test until it is reviewed and added here on purpose.
SANCTIONED_EGRESS_FILES = frozenset(
    {
        "analyzer.py",  # provider — all heavy/structured LLM calls
        "app.py",  # provider — _get_client() factory + anthropic error types
        "scraper.py",  # scrape — the sole requests importer (arbitrary user URLs)
        "evals/runner.py",  # provider — eval harness LLM calls
        "evals/bootstrap.py",  # provider — TYPE_CHECKING-only anthropic import
        "onboarding/extract_experiences.py",  # provider — corpus extraction
        "onboarding/corpus_import.py",  # provider — lazy in-function anthropic client
        "scripts/smoke_phase_b1.py",  # provider — manual smoke script
    }
)

# Importing any of these marks a module as network egress. ``urllib.parse`` is deliberately
# absent — it is pure string parsing (hardening.py uses ``urlparse``) and must stay clean.
_EGRESS_MODULES = frozenset(
    {
        "anthropic",
        "requests",
        "httpx",
        "aiohttp",
        "socket",
        "http.client",
        "ftplib",
        "smtplib",
        "telnetlib",
        "websocket",
        "websockets",
        "urllib.request",
        "urllib3",
    }
)

# Directory parts that take a .py file out of the production scan.
_SCAN_EXCLUDE_PARTS = frozenset(
    {"tests", ".venv", "venv", ".git", "build", "dist", "__pycache__", "versions"}
)


def _is_egress_name(dotted: str) -> bool:
    """True if a dotted import name is (or is a submodule of) a network-egress module."""
    return any(dotted == m or dotted.startswith(m + ".") for m in _EGRESS_MODULES)


def _module_imports_egress(tree: ast.AST) -> bool:
    """Walk a whole module AST (not just top-level) so lazy / TYPE_CHECKING / in-function
    imports are caught too — e.g. ``onboarding/corpus_import.py`` builds its client inside
    a function, and ``evals/bootstrap.py`` imports under ``if TYPE_CHECKING``.
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(_is_egress_name(alias.name) for alias in node.names):
                return True
        elif isinstance(node, ast.ImportFrom):
            # Reconstruct candidates: the module itself and module.name for each alias,
            # so ``from urllib import request`` resolves to ``urllib.request`` (egress)
            # while ``from urllib.parse import urlparse`` resolves to ``urllib.parse`` (ok).
            base = node.module or ""
            candidates = [base] if base else []
            for alias in node.names:
                candidates.append(f"{base}.{alias.name}" if base else alias.name)
            if any(_is_egress_name(c) for c in candidates):
                return True
    return False


def _production_py_files() -> list[Path]:
    out: list[Path] = []
    for path in REPO_ROOT.rglob("*.py"):
        rel_parts = path.relative_to(REPO_ROOT).parts
        if any(part in _SCAN_EXCLUDE_PARTS for part in rel_parts):
            continue
        out.append(path)
    return out


def test_static_egress_allowlist():
    """The set of production modules importing a network-egress library is EXACTLY the
    sanctioned allowlist — no more (a new egress site), no fewer (allowlist rot).
    """
    importers = set()
    for path in _production_py_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        if _module_imports_egress(tree):
            importers.add(path.relative_to(REPO_ROOT).as_posix())

    offenders = importers - SANCTIONED_EGRESS_FILES
    stale = SANCTIONED_EGRESS_FILES - importers
    assert not offenders, (
        f"Unsanctioned network-egress import site(s): {sorted(offenders)}. "
        "Every outbound socket must belong to one of the two sanctioned classes "
        "(LLM provider via anthropic; profile/website scrape via requests in scraper.py). "
        "If this is a deliberate new egress, add it to SANCTIONED_EGRESS_FILES on purpose."
    )
    assert not stale, (
        f"Allowlist rot — these no longer import an egress library: {sorted(stale)}. "
        "Remove them from SANCTIONED_EGRESS_FILES so the gate stays tight."
    )


# --------------------------------------------------------------------------- #
# 5. The scrape path is a real egress the gate actually catches.
# --------------------------------------------------------------------------- #
def test_scrape_path_is_real_egress_blocked():
    """The profile/website scrape (egress class 2) genuinely opens a socket the gate stops.

    Uses an IP literal (``127.0.0.1:9``) so ``socket`` is the first network op — a hostname
    URL would fail at DNS (getaddrinfo) and requests would wrap that as a RequestException
    that ``fetch_url_content`` swallows to ``""``, and the block would never prove anything.
    The IP-literal block raises before any byte leaves the box.
    """
    # The transport primitive the scrape path depends on is guarded.
    with pytest.raises(pytest_socket.SocketBlockedError):
        socket.create_connection(("127.0.0.1", 9))
    # The production path uses the real, guarded requests.get (not monkeypatched away).
    assert scraper.requests.get is requests.get
    # End-to-end: the block propagates out of fetch_url_content's RequestException swallow
    # (SocketBlockedError is a RuntimeError, which requests/urllib3 do not wrap), so the
    # scrape cannot silently succeed under the block.
    with pytest.raises(pytest_socket.SocketBlockedError):
        scraper.fetch_url_content("http://127.0.0.1:9/")


# --------------------------------------------------------------------------- #
# 6. No template loads an off-box resource (the browser-side egress class).
# --------------------------------------------------------------------------- #

# Generalizes the rendered-output assertion at tests/test_dashboard_routes.py:377-379 to a
# static scan of every template source (incl. the four personas + cover letter the dashboard
# route never renders). Hosts that must never appear anywhere in a template.
_BLOCKED_CDN_HOSTS = (
    "cdn.jsdelivr.net",
    "unpkg.com",
    "cdnjs.cloudflare.com",
    "ajax.googleapis.com",
    "fonts.googleapis.com",
    "fonts.gstatic.com",
    "code.jquery.com",
    "bootstrapcdn.com",
)

_TEMPLATE_ROOTS = ("templates", "dashboard/templates", "personas")

# Resource-loading contexts only — so legitimate <a href="https://..."> hyperlinks, comment
# URLs, Jinja replace("https://", "") filters, and placeholder/example text never match.
_SCRIPT_SRC_RE = re.compile(r"<script\b[^>]*\bsrc\s*=\s*[\"']([^\"']+)[\"']", re.IGNORECASE)
_LINK_HREF_RE = re.compile(r"<link\b[^>]*\bhref\s*=\s*[\"']([^\"']+)[\"']", re.IGNORECASE)
_MEDIA_SRC_RE = re.compile(
    r"<(?:img|source|video|audio)\b[^>]*\bsrc\s*=\s*[\"']([^\"']+)[\"']", re.IGNORECASE
)
_CSS_URL_RE = re.compile(r"url\(\s*[\"']?([^)\"']+)[\"']?\s*\)", re.IGNORECASE)
_ABSOLUTE_HTTP_RE = re.compile(r"^https?://", re.IGNORECASE)


def _template_files() -> list[Path]:
    out: list[Path] = []
    for root in _TEMPLATE_ROOTS:
        out.extend((REPO_ROOT / root).rglob("*.html"))
    return out


def test_templates_have_no_external_cdn():
    """No template loads a script/stylesheet/media/font from an off-box host."""
    files = _template_files()
    assert files, "Expected to find template .html files; the scan roots may have moved."

    resource_violations: list[str] = []
    host_violations: list[str] = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(REPO_ROOT).as_posix()

        for regex in (_SCRIPT_SRC_RE, _LINK_HREF_RE, _MEDIA_SRC_RE, _CSS_URL_RE):
            for url in regex.findall(text):
                if _ABSOLUTE_HTTP_RE.match(url.strip()):
                    resource_violations.append(f"{rel}: {url.strip()}")

        for host in _BLOCKED_CDN_HOSTS:
            if host in text:
                host_violations.append(f"{rel}: {host}")

    assert not resource_violations, (
        "Template(s) load an off-box resource (browser-side egress outside the two "
        f"sanctioned classes): {resource_violations}. Vendor the asset under static/ "
        "instead (see PX-01 / SECURITY.md bundled-assets)."
    )
    assert not host_violations, (
        f"Template(s) reference a known CDN host: {host_violations}. "
        "Vendor it locally; no runtime third-party fetch is allowed (C-2)."
    )
