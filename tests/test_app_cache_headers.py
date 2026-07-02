"""Cache-header contract for the Flask shell.

sartor. is a local-first dev tool. Browsers must always revalidate
the HTML shell and never reuse stale `/static/*` JS/CSS — otherwise
a UI change ships but the user still sees the previous build until
they manually hard-reload. We've hit this footgun twice; these tests
pin the headers in place so the next regression is caught
automatically.

Pins three things:
  - GET /                    → Cache-Control includes "no-cache"
  - GET /static/app.js       → Cache-Control includes "max-age=0"
  - GET /static/style.css    → Cache-Control includes "max-age=0"

Underlying mechanisms:
  - The `/` route sets the no-cache header explicitly in the view.
  - The static-asset behavior comes from
    `app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0`, which Flask
    converts into `Cache-Control: max-age=0, no-cache` on every
    static response.
"""

from __future__ import annotations


def test_index_route_sets_no_cache_header():
    """The HTML shell at `/` must never be cached. If a browser
    reuses it without revalidating, the user sees stale UI even
    after a deploy."""
    import app as app_module

    client = app_module.app.test_client()
    r = client.get("/")
    assert r.status_code == 200
    cc = r.headers.get("Cache-Control", "").lower()
    assert "no-cache" in cc, f"Expected 'no-cache' in Cache-Control, got {cc!r}"


def test_static_js_has_zero_max_age():
    """`/static/app.js` must not be browser-cached. UI edits should
    land on the next reload without manual cache-bust query strings
    or process-start tokens."""
    import app as app_module

    client = app_module.app.test_client()
    r = client.get("/static/app.js")
    assert r.status_code == 200
    cc = r.headers.get("Cache-Control", "").lower()
    assert "max-age=0" in cc, f"Expected 'max-age=0' in Cache-Control, got {cc!r}"


def test_static_css_has_zero_max_age():
    """Mirror of the JS check for CSS — same caching policy applies."""
    import app as app_module

    client = app_module.app.test_client()
    r = client.get("/static/style.css")
    assert r.status_code == 200
    cc = r.headers.get("Cache-Control", "").lower()
    assert "max-age=0" in cc, f"Expected 'max-age=0' in Cache-Control, got {cc!r}"


def test_send_file_max_age_default_is_zero():
    """Direct read of the Flask app config — pins the constant in
    place so a refactor that flips it back to None (= default
    "12 hours") is caught."""
    import app as app_module

    assert app_module.app.config.get("SEND_FILE_MAX_AGE_DEFAULT") == 0
