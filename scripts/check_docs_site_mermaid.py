#!/usr/bin/env python3
"""Check the built docs site in a real browser: every diagram renders, every local image loads.

**Why this exists.** The docs-site build can't catch a broken diagram. `remarkMdxMermaid`
turns each ```mermaid fence into a client component (`docs-site/src/components/mermaid.tsx`),
and mermaid parses it only in the browser. On a parse error the page quietly shows the
diagram's source as a code block, and the build stays green. The same goes for an image whose
path doesn't resolve after projection: the build succeeds and the page shows a broken image.

So this runs after `npm run build`, against `docs-site/out/`:
- serves the static export on a loopback port;
- loads every published page (`scripts/doc_registry.py`) in headless Chromium;
- waits until no diagram is still `data-mermaid="pending"`;
- **fails** if a page has a `failed` diagram, or fewer `ok` diagrams than its source doc has
  ```mermaid fences, or a same-origin `<img>` whose URL doesn't return 200.

External images (the README badges) aren't checked. Their hosts are not ours, and fetching
them would make the check flaky.

Run: `python scripts/check_docs_site_mermaid.py` (needs `docs-site/out/` and
`python -m playwright install chromium`). Wired into `.github/workflows/docs-deploy.yml`.
Exit 0 clean; 1 with a per-page listing; 2 when `docs-site/out/` is missing.
"""

from __future__ import annotations

import contextlib
import re
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from doc_registry import PUBLISHED
from project_docs_to_mdx import make_slug

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "docs-site" / "out"
_MERMAID_FENCE_RE = re.compile(r"^\s*```mermaid\s*$", re.M)
RENDER_TIMEOUT_MS = 30_000


def route_for(slug: str) -> str:
    """The static export's URL path for a projected page (`trailingSlash: true`)."""
    return "/docs/" if slug == "index" else f"/docs/{slug}/"


def expected_diagrams(root: Path = REPO_ROOT) -> dict[str, int]:
    """Route -> number of ```mermaid fences in its source doc, for every published page."""
    return {
        route_for(make_slug(e.path)): len(
            _MERMAID_FENCE_RE.findall((root / e.path).read_text(encoding="utf-8"))
        )
        for e in PUBLISHED
    }


_PAGE_STATE_JS = """() => {
  const by = (s) => document.querySelectorAll('[data-mermaid="' + s + '"]').length;
  // Images are lazy-loaded, so an off-screen one hasn't loaded yet. Collect the URLs and
  // fetch each one instead of reading its load state.
  const images = Array.from(document.images)
    .map((i) => new URL(i.getAttribute('src') || '', location.href))
    .filter((u) => u.origin === location.origin)
    .map((u) => u.href);
  return { ok: by('ok'), failed: by('failed'), pending: by('pending'), images };
}"""


class _QuietHandler(SimpleHTTPRequestHandler):
    """Serves `docs-site/out/` without a log line per request."""

    def __init__(self, *args: object, directory: str, **kwargs: object) -> None:
        super().__init__(*args, directory=directory, **kwargs)  # type: ignore[arg-type]

    def log_message(self, format: str, *args: object) -> None:
        return


class _QuietServer(ThreadingHTTPServer):
    """The browser aborts prefetch requests mid-response; that is not a finding."""

    def handle_error(self, request: object, client_address: object) -> None:
        return


def _serve(directory: Path) -> tuple[ThreadingHTTPServer, str]:
    def handler(*args: object, **kwargs: object) -> _QuietHandler:
        return _QuietHandler(*args, directory=str(directory), **kwargs)

    server = _QuietServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


def check(out_dir: Path = OUT_DIR) -> list[str]:
    # Imported here so the pure helpers above load without Playwright.
    from playwright.sync_api import TimeoutError as PWTimeout
    from playwright.sync_api import sync_playwright

    problems: list[str] = []
    expected = expected_diagrams()
    server, base = _serve(out_dir)
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page()
            for route, want in expected.items():
                resp = page.goto(base + route, wait_until="load")
                if resp is None or resp.status != 200:
                    problems.append(f"{route}: HTTP {resp.status if resp else 'no response'}")
                    continue
                if want:
                    # A timeout is reported below, with the counts that explain it.
                    with contextlib.suppress(PWTimeout):
                        page.wait_for_function(
                            "n => document.querySelectorAll('[data-mermaid=\"pending\"]').length === 0"
                            " && document.querySelectorAll('[data-mermaid]').length >= n",
                            arg=want,
                            timeout=RENDER_TIMEOUT_MS,
                        )
                state = page.evaluate(_PAGE_STATE_JS)
                if state["failed"] or state["pending"] or state["ok"] < want:
                    problems.append(
                        f"{route}: {state['ok']} of {want} diagram(s) rendered "
                        f"({state['failed']} failed, {state['pending']} still pending)"
                    )
                for url in state["images"]:
                    status = page.request.get(url).status
                    if status != 200:
                        problems.append(f"{route}: image {url.removeprefix(base)} -> HTTP {status}")
            browser.close()
    finally:
        server.shutdown()
    return problems


def main() -> int:
    if not (OUT_DIR / "index.html").is_file():
        print(f"check_docs_site_mermaid: no build at {OUT_DIR} — run `npm run build` in docs-site/")
        return 2
    expected = expected_diagrams()
    problems = check()
    total = sum(expected.values())
    if problems:
        print(f"check_docs_site_mermaid: FAILED — {len(problems)} problem(s):\n")
        print("\n".join(problems))
        return 1
    print(
        f"check_docs_site_mermaid: OK — {len(expected)} pages, {total} diagram(s) rendered, "
        "every local image returned 200."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
