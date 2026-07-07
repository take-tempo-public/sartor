"""Packaging marker only — NOT application code.

`docs/wiki/` is the committed LLM-wiki the doc-grounded assistant's S1 tier
reads (`blueprints/assistant.py:WikiSource`). This `__init__.py` turns the
directory into a real (tiny, data-only) Python package — an implicit
namespace package rooted at `docs/` (no `docs/__init__.py`; the rest of
`docs/` stays a plain, unpackaged directory) — so
`[tool.setuptools.package-data]` can ship the wiki pages inside an installed
wheel, and so `importlib.import_module("docs.wiki").__file__` resolves the
directory correctly under BOTH `pip install -e .` (byte-identical to the
pre-fix `PROJECT_ROOT`-relative lookup in `blueprints/assistant.py`) and a
real non-editable wheel install (`site-packages/docs/wiki/`), where the old
lookup 404'd (PyPI-wheel ledger item, `docs/dev/RELEASE_CHECKLIST.md`). See
`config.py:_package_dir`.
"""
