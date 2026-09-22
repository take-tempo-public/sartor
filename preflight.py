"""Capability preflight — what can THIS machine actually do, asked before it matters.

Items 100/102/103/104 are four symptoms of one absence: nothing in the codebase
could answer "is this capability actually available here?" Each surfaced instead
as a *runtime* failure, one at a time, after the user had already committed to a
path. The worst case is item 100's: five consecutive failures on macOS 12.7.4
before a `--log-level=debug` run finally printed **unsupported macOS version**.

This module answers each question up front, cheaply, and — where it cannot — says
so rather than guessing. `sartor --doctor` prints the whole set; `--setup` and the
generate UI consume individual probes.

Deterministic by construction: no LLM call, no network, no browser launch, no new
dependency (D-1). Every probe is filesystem/stdlib only.

**Three-state, deliberately.** A probe returns `True`, `False`, or `None`, and
`None` ("could not determine") is a first-class answer, not an error. Collapsing
unknown into either boolean is how a preflight starts lying: unknown-as-False
hides a feature that works, unknown-as-True reproduces the bug the probe exists
to prevent. Consumers decide which way to lean *at the call site*, where the cost
of being wrong is actually known — see `pdf_available()` for the one case where
that decision is made and why it leans the way it does.

**Cost.** Measured on this machine, 2026-09-03, both arms (real browsers path and
an empty `PLAYWRIGHT_BROWSERS_PATH`) —
`docs/dev/diagnosis/install-onboarding-preflight.md` O-5:

    browsers.json + 2 stats, driver never started      8.4 / 8.5 ms
    sync_playwright() + chromium.executable_path   2912.0 / 3099.0 ms
    playwright install --dry-run chromium          4071.0 / 3559.0 ms
    real launch() + close()                       14369.0 /  324.0 ms

The Playwright API path costs ~3 s because entering `sync_playwright()` spawns
the Node driver process. That is why `chromium_capability()` reads the driver's
`browsers.json` and stats two marker files instead of asking Playwright — ~350x
cheaper, and it checks *more* (see the function's own note). Anything here that
reaches for the Playwright API in future is a regression, not a cleanup.
"""

from __future__ import annotations

import importlib.util
import json
import os
import platform
import shutil
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

#: Minimum Python, mirroring `pyproject.toml`'s `requires-python = ">=3.11"`.
#: Duplicated deliberately: reading pyproject at runtime would fail on a non-editable
#: wheel install, where no pyproject sits beside the package (see `config._is_dev_checkout`).
PYTHON_FLOOR = (3, 11)

#: macOS floor for the CONTAINER path only. Podman's `applehv` VM backend requires
#: macOS 13+; on 12.x `podman machine start` dies with a generic
#: "vfkit exited unexpectedly with exit code 1" and only reveals the real cause under
#: `--log-level=debug`. Observed on macOS 12.7.4 build 21H1123, 2026-09-02
#: (`docs/dev/work/items/0100-install-prereqs-no-version-floors.md`).
MACOS_CONTAINER_FLOOR = (13, 0)

#: macOS floor for PDF output. Current Playwright releases ship no Chromium build
#: supporting macOS 12, and `pyproject.toml` pins `playwright>=1.40,<2.0` so pip
#: resolves the newest 1.x — precisely the build that dropped macOS 12. Same session,
#: same machine (`docs/dev/work/items/0103-pdf-output-no-graceful-degradation.md`).
MACOS_CHROMIUM_FLOOR = (13, 0)

#: Playwright's own per-artifact completeness sentinel. Every artifact directory under
#: the browsers root carries one; its presence distinguishes a *complete* install from
#: an interrupted one, which plain directory existence cannot
#: (diagnosis O-4). Stated limit (C-0): this is an internal Playwright layout detail,
#: not a documented API — `chromium_capability()` degrades to `None` if it stops holding.
_INSTALL_MARKER = "INSTALLATION_COMPLETE"


@dataclass(frozen=True)
class Capability:
    """One answered question about this machine.

    `ok` is tri-state: `True` available, `False` unavailable, `None` could not be
    determined. `detail` is always safe to print — no probe ever puts a secret in it
    (see `api_key_capability`, which reports presence and never the value).
    """

    key: str
    label: str
    ok: bool | None
    detail: str
    remedy: str = ""

    @property
    def mark(self) -> str:
        """A stable ASCII status glyph. ASCII on purpose — a Windows console is cp1252.

        Printing a non-ASCII glyph here would crash `--doctor` on the exact console the
        install docs tell a Windows user to open (diagnosis O-7 is the same class of
        crash, hit live in this session's own instrument).
        """
        if self.ok is True:
            return "ok "
        if self.ok is False:
            return "MISSING"
        return "unknown"


# --- OS / runtime ------------------------------------------------------------------


def python_capability() -> Capability:
    """Is this interpreter at or above the project's floor?"""
    current = sys.version_info[:2]
    ok = current >= PYTHON_FLOOR
    floor = ".".join(str(part) for part in PYTHON_FLOOR)
    return Capability(
        key="python",
        label="Python runtime",
        ok=ok,
        detail=f"{platform.python_version()} (floor {floor})",
        remedy="" if ok else f"Install Python {floor} or newer from python.org.",
    )


def _macos_version() -> tuple[int, int] | None:
    """`(major, minor)` from `platform.mac_ver()`, or None when unreadable.

    `mac_ver()` returns `('', ('', '', ''), '')` off macOS and can return an empty
    release string even on macOS under some packaging, so every branch is guarded.
    """
    release = platform.mac_ver()[0]
    if not release:
        return None
    parts = release.split(".")
    try:
        major = int(parts[0])
        minor = int(parts[1]) if len(parts) > 1 else 0
    except ValueError:
        return None
    return major, minor


def os_capability() -> Capability:
    """Report the OS, and flag only the floors this project has actually MEASURED.

    Deliberately narrow (C-0). The macOS 13 floor is recorded because a real install
    hit it and the cause was traced. **No Windows or Linux floor is asserted**, because
    none has been measured — inventing a plausible one here would put an unsourced
    claim in front of every user, which is exactly the failure `--doctor` exists to
    prevent. An unmeasured floor is reported as "no measured floor", not as "supported".
    """
    system = platform.system()
    if system == "Darwin":
        version = _macos_version()
        if version is None:
            return Capability(
                key="os",
                label="Operating system",
                ok=None,
                detail="macOS, version unreadable",
                remedy="Check `sw_vers`; the container path needs macOS 13+.",
            )
        major, minor = version
        below = (major, minor) < MACOS_CONTAINER_FLOOR
        floor = ".".join(str(part) for part in MACOS_CONTAINER_FLOOR)
        return Capability(
            key="os",
            label="Operating system",
            ok=not below,
            detail=(
                f"macOS {major}.{minor}" + (f" (below the measured {floor} floor)" if below else "")
            ),
            remedy=(
                f"macOS {floor}+ is required for the container path (Podman's applehv "
                "backend) and for Playwright's current Chromium builds. Use the source "
                "install, and expect PDF output to be unavailable."
                if below
                else ""
            ),
        )
    detail = f"{system} {platform.release()}".strip() or "unknown"
    return Capability(
        key="os",
        label="Operating system",
        ok=True,
        detail=f"{detail} (no measured version floor)",
    )


# --- Chromium / PDF ----------------------------------------------------------------


def _browsers_root() -> Path | None:
    """Playwright's browsers root, or None when it cannot be resolved confidently.

    `PLAYWRIGHT_BROWSERS_PATH=0` is Playwright's documented "install beside the package"
    mode rather than a path; it is reported as unresolvable instead of being treated as
    a directory named "0".
    """
    env = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if env == "0":
        return None
    if env:
        return Path(env)
    system = platform.system()
    if system == "Windows":
        local = os.environ.get("LOCALAPPDATA")
        return Path(local) / "ms-playwright" if local else None
    if system == "Darwin":
        return Path.home() / "Library" / "Caches" / "ms-playwright"
    return Path.home() / ".cache" / "ms-playwright"


def _parse_browsers_json(text: str) -> tuple[str, str] | None:
    """`(chromium_rev, headless_shell_rev)` from `browsers.json` text, or None.

    Pure — no filesystem, no imports — so the regression suite can exercise it against
    real captured manifest text on any platform, the way `scripts/gate.py`'s meminfo and
    vm_stat parsers are tested.

    Names are matched **exactly**, not by prefix: the real manifest also carries
    `chromium-tip-of-tree` and `chromium-tip-of-tree-headless-shell`, which a
    `startswith("chromium-")` match would confuse for the shipping build.
    """
    try:
        data = json.loads(text)
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    entries = data.get("browsers")
    if not isinstance(entries, list):
        return None
    revisions: dict[str, str] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        name, revision = entry.get("name"), entry.get("revision")
        if isinstance(name, str) and isinstance(revision, (str, int)):
            revisions[name] = str(revision)
    chromium = revisions.get("chromium")
    shell = revisions.get("chromium-headless-shell")
    if chromium is None or shell is None:
        return None
    return chromium, shell


def _chromium_revisions() -> tuple[str, str] | None:
    """`(chromium_rev, headless_shell_rev)` from the driver's own `browsers.json`.

    Uses `importlib.util.find_spec` rather than `import playwright` so a missing
    Playwright is a clean `None` instead of an ImportError, and so the package is
    never executed just to locate a JSON file.
    """
    try:
        spec = importlib.util.find_spec("playwright")
    except (ImportError, ValueError):
        return None
    if spec is None or spec.origin is None:
        return None
    manifest = Path(spec.origin).parent / "driver" / "package" / "browsers.json"
    try:
        return _parse_browsers_json(manifest.read_text(encoding="utf-8"))
    except OSError:
        return None


def _artifact_complete(root: Path, directory: str) -> bool:
    """True when Playwright's completeness sentinel is present in `<root>/<directory>`."""
    try:
        return (root / directory / _INSTALL_MARKER).is_file()
    except OSError:
        return False


def chromium_capability() -> Capability:
    """Can this machine render a PDF?

    Checks **both** chromium artifacts, because they are genuinely different files and
    the PDF path needs the one you would not guess. `render_pdf` calls
    `p.chromium.launch()` with no `headless` argument, so it takes the headless default
    and needs `chromium_headless_shell-<rev>` — while `chromium.executable_path` names
    `chromium-<rev>/chrome-*/chrome`. Measured directly (diagnosis O-2): with an empty
    browsers root, `launch(headless=True)` failed on the *headless shell* path and
    `launch(headless=False)` on the *headed* path. A probe that stats only
    `executable_path` therefore reports "available" for a partial install that cannot
    render a PDF — and a chromium install is five artifacts, so partial is a real state
    (O-3).

    Returns `None` (unknown) rather than guessing when Playwright is absent, the browsers
    root is unresolvable, or `browsers.json` does not parse — see `pdf_available()` for
    how unknown is resolved and why.
    """
    revisions = _chromium_revisions()
    root = _browsers_root()
    if revisions is None or root is None:
        return Capability(
            key="chromium",
            label="Chromium (PDF output)",
            ok=None,
            detail="could not resolve Playwright's browser layout",
            remedy="PDF may still work. `sartor --setup` installs Chromium if it does not.",
        )
    chromium_rev, shell_rev = revisions
    headed = _artifact_complete(root, f"chromium-{chromium_rev}")
    shell = _artifact_complete(root, f"chromium_headless_shell-{shell_rev}")
    if headed and shell:
        return Capability(
            key="chromium",
            label="Chromium (PDF output)",
            ok=True,
            detail=f"chromium + headless shell r{chromium_rev} installed",
        )
    missing = ", ".join(
        name for name, present in (("chromium", headed), ("headless shell", shell)) if not present
    )
    return Capability(
        key="chromium",
        label="Chromium (PDF output)",
        ok=False,
        detail=f"missing: {missing}",
        remedy=_chromium_remedy(),
    )


def _chromium_remedy() -> str:
    """What to tell someone whose Chromium is missing — which is not the same everywhere.

    On macOS below `MACOS_CHROMIUM_FLOOR` the usual advice is actively wrong: current
    Playwright releases ship no Chromium build for macOS 12, so
    `python -m playwright install chromium` cannot succeed no matter how many times it
    is run. That is exactly the machine item 103 was filed from — telling that user to
    re-run the command that already failed is the misdirection this preflight exists to
    remove, so the floor gets its own branch instead of one generic string.
    """
    version = _macos_version()
    if version is not None and version < MACOS_CHROMIUM_FLOOR:
        floor = ".".join(str(part) for part in MACOS_CHROMIUM_FLOOR)
        return (
            f"PDF output is not available on macOS {version[0]}.{version[1]}: current "
            f"Playwright releases ship no Chromium build below macOS {floor}, so "
            "`playwright install chromium` cannot succeed here. Use DOCX or Markdown "
            "output, or the live in-browser preview, which need no Chromium."
        )
    return (
        "Run `sartor --setup` (or `python -m playwright install chromium`). "
        "DOCX, Markdown and the live preview do not need it."
    )


@lru_cache(maxsize=1)
def pdf_available() -> bool:
    """Should the UI offer PDF? Resolved once per process.

    **Unknown leans available.** The two ways to be wrong are not symmetric: a false
    "unavailable" hides a working feature from every user with no way to discover the
    button should be there, while a false "available" merely restores today's behavior —
    the PDF attempt fails with an error the route already surfaces. The unknown branch
    exists precisely because `chromium_capability()` reads an *internal* Playwright
    layout (diagnosis "Inferred"), so a future Playwright reshuffle must degrade to
    today's behavior, not to a silent blackout of PDF for everyone.

    Cached because the answer cannot change while the process lives and the alternative
    is a filesystem probe in the request path. Call `pdf_available.cache_clear()` in a
    test that manipulates the environment.
    """
    return chromium_capability().ok is not False


# --- Recall index, API key, container backend ---------------------------------------


def vector_index_capability(base_dir: Path | None = None) -> Capability:
    """Is the assistant's semantic-recall tier built?

    Mirrors `blueprints/assistant.py`'s activation condition (both the model and the
    index must be present) rather than restating a looser one — the assistant runs on
    its wiki/git/session tiers without this, so absence is a degraded tier, not an error.
    """
    root = base_dir if base_dir is not None else Path(__file__).resolve().parent
    index_dir = root / "db" / "vector_index"
    embeddings = index_dir / "embeddings.npy"
    chunks = index_dir / "chunks.json"
    model = index_dir / "model"
    try:
        ok = embeddings.is_file() and chunks.is_file() and model.is_dir()
    except OSError:
        return Capability(
            key="recall",
            label="Semantic recall index",
            ok=None,
            detail=f"could not read {index_dir}",
        )
    return Capability(
        key="recall",
        label="Semantic recall index",
        ok=ok,
        detail="built" if ok else "not built",
        remedy=(
            "" if ok else "Run `sartor --setup`. Without it the assistant uses its lexical tiers."
        ),
    )


def api_key_path(base_dir: Path | None = None) -> Path:
    """The `.api_key` file's location — the ONE resolution both readers and writers use.

    `web_infra.clients._get_client` falls back to `_REPO_ROOT / ".api_key"`, where
    `_REPO_ROOT` is `web_infra/`'s parent — the same directory this module lives in.
    `--setup`'s key prompt (item 104) writes here and `api_key_capability` reports on
    here, so a preflight cannot tell a user their key is missing while the app happily
    reads it (or the reverse). `tests/test_setup_api_key.py` asserts the agreement
    directly rather than trusting this comment to stay true.
    """
    root = base_dir if base_dir is not None else Path(__file__).resolve().parent
    return root / ".api_key"


def api_key_capability(base_dir: Path | None = None) -> Capability:
    """Is an Anthropic key resolvable? The value is read to test it, and never reported.

    Precise on purpose: the value *is* read — testing "is there a non-blank key here"
    cannot be done without looking at it. What is guaranteed is narrower and is the part
    that matters: the value never reaches `detail`, `remedy`, a log, or a return value,
    so nothing a caller can print carries it. `tests/test_preflight.py::
    TestApiKeyCapability::test_the_key_value_is_never_reported` asserts exactly that.

    Mirrors `web_infra.clients._get_client`'s resolution order (env var, then the
    `.api_key` file) so `--doctor` cannot disagree with what the app will actually do.
    """
    if os.environ.get("ANTHROPIC_API_KEY", "").strip():
        return Capability(
            key="api_key",
            label="Anthropic API key",
            ok=True,
            detail="found in ANTHROPIC_API_KEY",
        )
    key_file = api_key_path(base_dir)
    try:
        present = key_file.is_file() and bool(key_file.read_text(encoding="utf-8").strip())
    except OSError:
        present = False
    if present:
        return Capability(
            key="api_key", label="Anthropic API key", ok=True, detail="found in .api_key"
        )
    return Capability(
        key="api_key",
        label="Anthropic API key",
        ok=False,
        detail="not found",
        remedy=(
            "Run `sartor --setup`: it prompts without echoing, so the key never reaches "
            "your shell history. Or set SARTOR_DEMO=1 to try the app with no key at all."
        ),
    )


def container_capability() -> Capability:
    """Is a container engine on PATH? Best-effort, PATH lookup only — nothing is executed.

    Deliberately does not run `podman info` to check the machine is *started*: that shells
    out, can hang on a broken VM, and the failure it would catch (item 100's step 2) is
    better reported by Podman itself than guessed at here.
    """
    found = [name for name in ("podman", "docker") if shutil.which(name)]
    if found:
        return Capability(
            key="container",
            label="Container engine",
            ok=True,
            detail=", ".join(found) + " on PATH",
        )
    return Capability(
        key="container",
        label="Container engine",
        ok=False,
        detail="neither podman nor docker on PATH",
        remedy=(
            "Only needed for the container path. Podman Desktop installs the GUI but not "
            "the engine; `brew install podman` (macOS) installs the CLI itself."
        ),
    )


# --- Aggregate + report --------------------------------------------------------------


def probe_all(base_dir: Path | None = None) -> list[Capability]:
    """Every probe, in the order `--doctor` prints them. Uncached — see `pdf_available`."""
    return [
        python_capability(),
        os_capability(),
        api_key_capability(base_dir),
        chromium_capability(),
        vector_index_capability(base_dir),
        container_capability(),
    ]


def format_report(capabilities: list[Capability]) -> str:
    """Render the capability set as an ASCII block. Pure — takes probes, returns text."""
    width = max((len(cap.label) for cap in capabilities), default=0)
    lines = ["", "  sartor. preflight", ""]
    for cap in capabilities:
        lines.append(f"  [{cap.mark:^7}] {cap.label:<{width}}  {cap.detail}")
    remedies = [cap for cap in capabilities if cap.remedy]
    if remedies:
        lines.extend(["", "  What to do:"])
        for cap in remedies:
            lines.append(f"    - {cap.label}: {cap.remedy}")
    blocking = [cap for cap in capabilities if cap.ok is False and cap.key in ("python",)]
    lines.append("")
    if blocking:
        lines.append("  Sartor cannot run until the items above are resolved.")
    else:
        lines.append("  Sartor can run. Anything MISSING above is an optional feature.")
    lines.append("")
    return "\n".join(lines)


def run_doctor(base_dir: Path | None = None) -> int:
    """`sartor --doctor` — print the whole capability set. Exit 1 only if Python is too old.

    Optional features being absent is not a failure exit: a user on macOS 12 with no
    Chromium has a working Sartor minus PDF, and exiting nonzero there would tell them
    the opposite of what the docs promise.
    """
    capabilities = probe_all(base_dir)
    print(format_report(capabilities))
    fatal = any(cap.ok is False and cap.key == "python" for cap in capabilities)
    return 1 if fatal else 0
