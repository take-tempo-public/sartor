# Vendored axe-core

`axe.min.js` is a **pinned, vendored** copy of [axe-core](https://github.com/dequelabs/axe-core)
— Deque's accessibility rules engine. It powers the a11y smoke gate at
[`../test_axe_smoke.py`](../test_axe_smoke.py).

- **Version:** axe-core `4.10.2`
- **Source:** `https://cdn.jsdelivr.net/npm/axe-core@4.10.2/axe.min.js`
- **License:** MPL-2.0 (the full notice is preserved at the top of the file).

## Why vendored (not a pip dependency)

The gate injects this file into the page itself via Playwright
(`page.add_script_tag(content=...)`), so it runs **wherever the UX-tier
Chromium already runs** — it can never silently skip from a missing pip
extra, and it adds no runtime/test dependency. This matches the repo's
existing JS vendoring (`static/vendor/paged.polyfill.js`).

## Bumping the version

This is a **manual** bump (no package manager tracks it):

```bash
curl -sS -L -o tests/ux/a11y/vendor/axe.min.js \
  https://cdn.jsdelivr.net/npm/axe-core@<new-version>/axe.min.js
```

Then update the version line above, re-run `pytest -m a11y`, and note the
bump in `CHANGELOG.md`.
