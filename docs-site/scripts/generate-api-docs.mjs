#!/usr/bin/env node
/**
 * Deterministic OpenAPI -> Fumadocs MDX projection (spectree/OpenAPI Layer B,
 * Phase 2 — "render the spec").
 *
 * Companion to `scripts/generate_openapi_spec.py` (repo root): that script
 * emits `docs-site/openapi.json` from the 5 spectree-decorated Flask routes
 * (`web_infra/openapi.py`). THIS script reads that spec and projects it into
 * MDX reference pages under `content/docs/api-reference/` via
 * fumadocs-openapi's `createOpenAPI()` + `generateFiles()` — mirroring
 * `scripts/project_docs_to_mdx.py`'s L1 -> MDX projection pattern: a
 * deterministic build step, not synthesis. Must run AFTER
 * `scripts/generate_openapi_spec.py` (needs `openapi.json`) and AFTER `npm ci`
 * (needs `fumadocs-openapi` installed); see
 * `.github/workflows/docs-deploy.yml` for the ordering.
 *
 * This is a STANDALONE `createOpenAPI()` caller — it deliberately does NOT
 * import `docs-site/src/lib/openapi.ts` (that module uses the `@/*` path
 * alias, which only resolves inside Next's bundler / `next build`; this
 * script runs as a plain Node ESM script outside that pipeline, the same way
 * `scripts/generate_openapi_spec.py` builds its own throwaway `create_app()`
 * rather than importing anything route-specific).
 *
 * **Reference-only rendering.** The interactive "try it" playground is
 * disabled in `docs-site/src/components/api-page.tsx`
 * (`playground: { enabled: false }`) — a live playground would fire
 * cross-origin requests at each site visitor's own `localhost:5000`, which is
 * wrong for a static site documenting a local desktop app. This script only
 * arranges pages (schemas, parameters, response bodies, per-language code
 * samples); the actual UI toggle lives in that component factory, not here.
 *
 * **Nav wiring.** `generateFiles({ meta: true })` writes its OWN nested
 * `meta.json` tree under `content/docs/api-reference/` (one per tag: users,
 * applications, corpus) — no hand-authoring needed there. The single
 * remaining piece is making the `api-reference` folder show up in the
 * PARENT nav: `content/docs/meta.json` is fully regenerated on every CI run
 * by `scripts/project_docs_to_mdx.py` (which runs before this script — see
 * the workflow) and lists its `pages` explicitly, so an unlisted folder is
 * hidden from the sidebar (Fumadocs: pages not in an explicit `pages` array
 * don't appear unless a `...` rest entry is present). Rather than teach the
 * L1 projector about a docs-site-only reference section (out of scope, and
 * documentation-architecture.md prefers the nested/low-risk approach here),
 * this script appends exactly ONE entry — `"api-reference"` — to that
 * already-written file's `pages` array, idempotently.
 */

import { createOpenAPI } from 'fumadocs-openapi/server';
import { generateFiles } from 'fumadocs-openapi';
import { readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const DOCS_SITE_ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const OPENAPI_JSON = path.join(DOCS_SITE_ROOT, 'openapi.json');
const OUTPUT_DIR = path.join(DOCS_SITE_ROOT, 'content', 'docs', 'api-reference');
const OUTPUT_META_JSON = path.join(OUTPUT_DIR, 'meta.json');
const TOP_META_JSON = path.join(DOCS_SITE_ROOT, 'content', 'docs', 'meta.json');
const NAV_ENTRY = 'api-reference';
const NAV_TITLE = 'API Reference';

async function addNavEntry() {
  const raw = await readFile(TOP_META_JSON, 'utf-8');
  const meta = JSON.parse(raw);
  meta.pages ??= [];
  if (!meta.pages.includes(NAV_ENTRY)) {
    meta.pages.push(NAV_ENTRY);
    await writeFile(TOP_META_JSON, `${JSON.stringify(meta, null, 2)}\n`, 'utf-8');
  }
}

// generateFiles({ meta: true }) writes content/docs/api-reference/meta.json
// with no `title` (it only sets one when there's a parent folder — the
// top-level scan has none), which leaves Fumadocs to auto-title the folder
// from its slug ("Api reference"). Set a proper display title in the same
// already-generated file rather than hand-authoring a parallel one.
async function setFolderTitle() {
  const raw = await readFile(OUTPUT_META_JSON, 'utf-8');
  const meta = JSON.parse(raw);
  meta.title = NAV_TITLE;
  await writeFile(OUTPUT_META_JSON, `${JSON.stringify(meta, null, 2)}\n`, 'utf-8');
}

// The schema ID MUST be the literal string "api" — it has to match the key
// docs-site/src/lib/openapi.ts registers its own createOpenAPI() call under,
// because generateFiles() bakes this same ID into every generated page's
// `_openapi.preload` list and `document="api"` JSX prop, and
// `openapi.preloadOpenAPIPage(page)` (called at render time, in
// app/docs/[[...slug]]/page.tsx) looks up each `preload` entry by exact key
// against the RUNTIME instance's own input map. Passing the absolute path
// itself as the key (e.g. `input: [OPENAPI_JSON]`) would still "work" by
// accident (the fallback branch reads the path directly), but skips the
// instance's cache and desyncs from lib/openapi.ts's own key space — see the
// comment there.
const SCHEMA_ID = 'api';

async function main() {
  const openapi = createOpenAPI({ input: { [SCHEMA_ID]: OPENAPI_JSON } });

  await generateFiles({
    input: openapi,
    output: OUTPUT_DIR,
    per: 'operation',
    groupBy: 'tag',
    includeDescription: true,
    meta: true,
  });

  await setFolderTitle();
  await addNavEntry();

  const relOutput = path.relative(DOCS_SITE_ROOT, OUTPUT_DIR).replaceAll(path.sep, '/');
  console.log(
    `generate-api-docs: OK — projected ${path.basename(OPENAPI_JSON)} -> ${relOutput} ` +
      `(nav entry "${NAV_ENTRY}" ensured in content/docs/meta.json)`,
  );
}

main().catch((err) => {
  console.error('generate-api-docs: FAILED —', err);
  process.exitCode = 1;
});
