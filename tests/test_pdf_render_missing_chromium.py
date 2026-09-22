"""What `render_pdf` actually raises when Chromium is absent (item 103, O-1).

`pdf_render.render_pdf` and `render_cover_letter_pdf` both documented
"RuntimeError if Playwright fails to launch (Chromium not installed)". Item 103
inherited that claim from `_run_setup`'s docstring and filed itself as
explicitly un-observed. Running it settled the question the other way:

    playwright Error MRO: ['Error', 'Exception', 'BaseException', 'object']
    isinstance(exc, RuntimeError): False

`except RuntimeError` around a PDF render would therefore NOT catch the
missing-Chromium case. Nothing in-tree does that today
(`blueprints/generation.py` catches broad `Exception`), so the false docstring
had not yet produced a live bug -- but it was a docstring contradicting the
code it describes, which is exactly the drift a future graceful-degradation
handler would be written against.

These tests pin the corrected claim. They do not launch a browser and do not
need Chromium absent on the machine running them: the exception class is a
property of the `playwright` package, and the launch-failure path is exercised
by monkeypatching, not by uninstalling anything.

Full evidence: `docs/dev/diagnosis/install-onboarding-preflight.md`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import pdf_render


class TestPlaywrightErrorIsNotARuntimeError:
    def test_the_documented_exception_class_is_what_playwright_actually_raises(self):
        """The claim the two docstrings now make, asserted against the real class."""
        from playwright.sync_api import Error as PlaywrightError

        assert issubclass(PlaywrightError, Exception)
        assert not issubclass(PlaywrightError, RuntimeError), (
            "playwright.sync_api.Error became a RuntimeError subclass; the docstrings in "
            "pdf_render.py and docs/dev/diagnosis/install-onboarding-preflight.md O-1 both "
            "need revisiting"
        )

    def test_sync_api_error_is_the_impl_error(self):
        """The public alias and the class raised from `_impl` are the same object.

        The observed traceback named `playwright._impl._errors.Error`; the docstrings
        cite the public `playwright.sync_api.Error`. If those ever diverged, the
        docstring would be technically wrong again.
        """
        from playwright._impl._errors import Error as ImplError
        from playwright.sync_api import Error as PublicError

        assert PublicError is ImplError


class TestRenderPdfPropagatesTheLaunchFailure:
    """`render_pdf` must not swallow or re-wrap the launch failure.

    The route above it catches broad `Exception` and surfaces a message; a
    re-wrap into RuntimeError here would make the docstring true again by
    accident and hide the real cause from the log.
    """

    def _launch_raising_playwright_error(self, monkeypatch):
        from playwright.sync_api import Error as PlaywrightError

        class _FakeChromium:
            def launch(self, *args, **kwargs):
                raise PlaywrightError(
                    "BrowserType.launch: Executable doesn't exist at "
                    "/nowhere/chromium_headless_shell-1223/chrome-headless-shell"
                )

        class _FakePlaywright:
            chromium = _FakeChromium()

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

        # `render_pdf` does `from playwright.sync_api import sync_playwright` INSIDE the
        # function, so the name is re-bound on every call and patching `pdf_render`'s
        # own attribute does nothing -- the first draft of this test did that and
        # silently launched a real browser instead of exercising the failure path.
        # Patch the source module.
        import playwright.sync_api

        monkeypatch.setattr(playwright.sync_api, "sync_playwright", lambda: _FakePlaywright())
        return PlaywrightError

    def test_launch_failure_reaches_the_caller_unwrapped(self, monkeypatch, tmp_path):
        pytest.importorskip("playwright")
        error_cls = self._launch_raising_playwright_error(monkeypatch)
        html = tmp_path / "persona.html"
        html.write_text("<html><body>{{ basics.name }}</body></html>", encoding="utf-8")
        with pytest.raises(error_cls) as excinfo:
            pdf_render.render_pdf(
                {"basics": {"name": "Test"}},
                html_template_path=html,
                output_pdf_path=tmp_path / "out.pdf",
            )
        assert not isinstance(excinfo.value, RuntimeError)
        assert "Executable doesn't exist" in str(excinfo.value)


class TestMissingTemplateStillRaisesFileNotFound:
    """The other documented exception, unchanged -- guards against an over-broad edit."""

    def test_missing_html_template(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            pdf_render.render_pdf(
                {"basics": {"name": "Test"}},
                html_template_path=Path(tmp_path / "does-not-exist.html"),
                output_pdf_path=tmp_path / "out.pdf",
            )
