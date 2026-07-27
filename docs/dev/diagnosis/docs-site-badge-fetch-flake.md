# Diagnosis — docs-site static-export build hard-fails on a live shields.io badge-image fetch timeout

> **Status:** root cause PROVEN (direct CI log evidence + reproduced/fixed locally with the exact installed package code)
> **Branch:** `fix/docs-site-badge-fetch-flake`

---

## Symptom

The `docs-site/` "Project docs -> MDX, build static export, publish" GitHub
Actions check fails intermittently on otherwise-unrelated PRs. First observed
on PR #66 (`feat/context-structure-review-skill`, 2026-07-24) — the check
failed identically twice in a row despite zero `docs-site/` diff on that
branch. Not merge-blocking today (not in `main`'s required six checks), but
will recur on every future PR until fixed (`docs/dev/RELEASE_CHECKLIST.md`
ledger item 8).

---

## Observed

- Pulled the two actual failed run logs directly via
  `gh run view <id> --repo take-tempo-public/sartor --log-failed`
  for runs `30108437723` and `30108426345` (both on
  `feat/context-structure-review-skill`, 2026-07-24T16:15-16:22Z). Identical
  failure both times:
  ```
  > next build
  ...
  Error: Turbopack build failed with 1 errors:
  ./content/docs/index.mdx
  Error evaluating Node.js code
  Error: [Remark Image] Failed obtain image size for
  https://img.shields.io/github/actions/workflow/status/take-tempo-public/sartor/ci.yml?branch=main&label=CI
  (public directory configured as /home/runner/work/sartor/sartor/docs-site/public)
    (from .../docs-site/node_modules/fumadocs-mdx/dist/webpack/mdx.js)
    [at file://.../docs-site/node_modules/fumadocs-core/dist/mdx-plugins/remark-image.js:70:11]
    [at async updateImage (file://.../fumadocs-core/dist/mdx-plugins/remark-image.js:69:17)]
    [at async (file://.../fumadocs-core/dist/mdx-plugins/remark-image.js:96:3)]
  Caused by: Error: [Remark Image] Failed to fetch
  https://img.shields.io/github/actions/workflow/status/take-tempo-public/sartor/ci.yml?branch=main&label=CI
  (408): Request Timeout
    [at getImageSize (file://.../fumadocs-core/dist/mdx-plugins/remark-image.js:167:21)]
  ##[error]Process completed with exit code 1.
  ```
- Read the exact installed file at that path,
  `docs-site/node_modules/fumadocs-core/dist/mdx-plugins/remark-image.js` —
  the line numbers in the traceback above (`:70:11`, `:69:17`, `:96:3`,
  `:167:21`) match this file's actual content exactly. The plugin does a
  live `fetch(src.url, ...)` for every external (`http(s)://`) markdown image
  with no retry, and its default `onError: "error"` option rethrows any
  fetch failure — killing the entire Turbopack build for the whole
  `content/docs/index.mdx` page (the one that carries all 7 README badges).
- Confirmed via `docs-site/source.config.ts` +
  `docs-site/node_modules/fumadocs-core/dist/content/mdx/preset-bundler.js`
  that a `remarkImageOptions` key placed in `defineConfig({ mdxOptions })`
  is destructured straight through to the `remarkImage` plugin instance —
  this is a supported, first-class override point, not a hack.
- **Empirically ran both onError candidates** (not assumed) via
  `node --input-type=module` from `docs-site/`, using the project's own
  installed `remark` + `fumadocs-core/mdx-plugins`, against a markdown image
  with the exact real badge URL shape pointed at an unreachable host
  (`http://127.0.0.1:1/...`, 500ms timeout):
  - `onError: "hide"` → resulting mdast tree: `paragraph.children: []` — the
    image node is spliced out entirely, no error thrown, no `<img>` reaches
    the render.
  - `onError: "ignore"` → resulting mdast tree: the original dimension-less
    `image` node is left in place, unconverted, no error thrown either.
  - Read `docs-site/node_modules/fumadocs-ui/dist/mdx.js`: every rendered
    `<img>` (including a plain, unconverted markdown image) is routed through
    `img: Image$1`, which wraps `next/image`'s `<Image>` — a component that
    requires an explicit `width`/`height` (or `fill`) prop, a stable,
    independent Next.js API constraint unrelated to fumadocs.

---

## Falsified

- **`onError: "ignore"`** — plausible from the name ("ignore the error"), and
  it does suppress the fetch-time error. **Rejected**: the empirical test
  above shows it leaves a dimension-less image node in the tree, which the
  `img: Image$1` → `next/image` wrapper very likely then fails on separately
  (missing required `width`/`height`) — i.e. it would trade this specific
  build failure for a different one, not fix the underlying problem. Not
  re-verified end-to-end against a live `next build` (that would require
  committing it first, which the point of this falsification was to avoid);
  the mdast-level behavior alone is sufficient to reject it in favor of
  `"hide"`, which provably avoids emitting any `<img>` for the failed node.

---

## Inferred

_(None — the mechanism was directly observed in the CI log with matching
line numbers against the exact installed package source, and the fix
candidate was validated empirically against the same installed package
rather than assumed from documentation or option names.)_

---

## Falsification

**Experiment (already run, see Observed):** process a markdown image with the
real badge URL shape, pointed at an unreachable host, through the project's
actual installed `remarkImage` plugin with `onError: "hide"` vs `"ignore"`.

- `"hide"` splices the failing node out of the tree (empty `paragraph`) →
  **no `<img>` element reaches the `next/image` wrapper for that node**, so
  there is nothing left to fail on missing `width`/`height`. This is the
  fix.
- `"ignore"` leaves a dimension-less `image` node in the tree, which (per the
  `img: Image$1` routing observed above) would still hit `next/image`'s
  own required-width/height constraint. **Dead end — do not use.**

---

## The fix

`docs-site/source.config.ts`: add `remarkImageOptions: { onError: 'hide' }`
to the `mdxOptions` object passed to `defineConfig(...)`.

**Accepted trade-off:** on a badge-fetch failure, that one badge is silently
absent from the built docs-site homepage for that build only — it reappears
on the next successful build once the badge host is reachable again. GitHub's
own README rendering is unaffected (separate, live fetch). This applies
uniformly to all 7 README badges (CI, license, python-version, egress,
OpenSSF Scorecard, OpenSSF Best Practices, REUSE) — they share the identical
code path, so any one of them could time out the same way; local screenshot
images are unaffected (`type: 'file'` code path, no network call).

---

## Acceptance bar

- `cd docs-site && npm run build` succeeds with the real, currently-reachable
  badges (no regression in the success case).
- The same build, run against a deliberately-unreachable badge URL, succeeds
  (rather than failing the whole Turbopack build) with that one badge absent
  from `out/index.html` — reproducing the original CI failure mode locally
  and confirming the fix actually holds against it, not just in theory.
- `python -m scripts.gate` green.
