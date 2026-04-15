"""URL content fetcher — P1 Hardening.

Deterministic extraction of text from web pages.
Used to pull portfolio/LinkedIn content for LLM context.
"""

import logging

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "ResumeOptimizer/1.0 (personal use)",
    "Accept": "text/html,application/xhtml+xml",
}
TIMEOUT = 15
MAX_PROFILE_CHARS = 3_000  # per-URL cap — keeps total profile context manageable


def fetch_url_content(url: str) -> str:
    """Fetch a URL and extract meaningful text content."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.warning("Failed to fetch %s: %s", url, e)
        return ""

    soup = BeautifulSoup(resp.text, "html.parser")

    # Remove noise elements
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)

    # Collapse excessive whitespace
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    text = "\n".join(lines)

    # P2 Context Hygiene: cap per-URL content to prevent prompt bloat
    if len(text) > MAX_PROFILE_CHARS:
        text = text[:MAX_PROFILE_CHARS] + "\n[truncated]"

    return text


def fetch_profile_content(config: dict) -> str:
    """Fetch all profile URLs from a user config and combine content."""
    parts = []

    for field in ("linkedin_url", "website_url"):
        url = config.get(field, "")
        if url:
            content = fetch_url_content(url)
            if content:
                label = field.replace("_url", "").replace("_", " ").title()
                parts.append(f"--- {label} ---\n{content}")

    for url in config.get("portfolio_urls", []):
        content = fetch_url_content(url)
        if content:
            parts.append(f"--- Portfolio ---\n{content}")

    return "\n\n".join(parts)
