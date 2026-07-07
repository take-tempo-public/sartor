"""Packaging marker only — NOT application code.

`static/` holds the app shell's JS/CSS (`app.js`, `style.css`, `vendor/…`).
This `__init__.py` turns the directory into a real (tiny, data-only) Python
package so `[tool.setuptools.package-data]` can ship those assets inside an
installed wheel, and so `importlib.import_module("static").__file__` resolves
the directory correctly under BOTH `pip install -e .` (byte-identical to the
pre-fix `_PROJECT_ROOT`-relative lookup) and a real non-editable wheel install
(`site-packages/static/`), where the old lookup 404'd (PyPI-wheel ledger item,
`docs/dev/RELEASE_CHECKLIST.md`). See `config.py:_package_dir`.
"""
