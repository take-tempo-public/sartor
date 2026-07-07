"""Packaging marker only — NOT application code.

`templates/` holds the single Jinja shell (`index.html`) `create_app()` loads.
This `__init__.py` turns the directory into a real (tiny, data-only) Python
package so `[tool.setuptools.package-data]` can ship `index.html` inside an
installed wheel, and so `importlib.import_module("templates").__file__`
resolves the directory correctly under BOTH `pip install -e .` (import
machinery points at this source tree — byte-identical to the pre-fix
`_PROJECT_ROOT`-relative lookup) and a real non-editable wheel install
(`site-packages/templates/`), where the old lookup 404'd (PyPI-wheel ledger
item, `docs/dev/RELEASE_CHECKLIST.md`). See `config.py:_package_dir`.
"""
