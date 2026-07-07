"""Packaging marker only — NOT application code.

`personas/bundled/` holds the four shipped default persona templates (Classic
/ Modern / Spacious / Tech — `.docx` + companion `.html`/`.css`). This
`__init__.py` turns the directory into a real (tiny, data-only) Python package
so `[tool.setuptools.package-data]` can ship them inside an installed wheel,
and so `importlib.import_module("personas.bundled").__file__` resolves the
directory correctly under BOTH `pip install -e .` (byte-identical to the
pre-fix `_PROJECT_ROOT`-relative lookup) and a real non-editable wheel install
(`site-packages/personas/bundled/`), where the old lookup 404'd (PyPI-wheel
ledger item, `docs/dev/RELEASE_CHECKLIST.md`). Scoped to `bundled/` only —
`personas/` itself stays a plain (non-package) directory because it also
holds per-user, gitignored, runtime-written persona uploads
(`PERSONAS_DIR / <user>`); that mixed-use, user-writable path is unaffected
and still resolves off `Config.base_dir`. See `config.py:_package_dir`.
"""
