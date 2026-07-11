'use client';
import { createOpenAPIPage } from 'fumadocs-openapi/ui';

// Reference-only rendering — schemas, parameters, response bodies, and
// per-language code-usage samples, but NO interactive "try it" playground.
// A live playground would fire cross-origin requests at each site visitor's
// own `localhost:5000` (this static site documents a local desktop app, it
// doesn't front a public API) — see this branch's mission note in
// docs-site/scripts/generate-api-docs.mjs. `playground: { enabled: false }`
// (see packages/openapi/src/ui/operation/index.tsx upstream — `ctx.playground
// ?.enabled ?? true` gates whether `PlaygroundClient` or a static method+path
// badge renders) replaces the live request builder with that static badge;
// everything else (parameters, request/response schemas, TypeScript
// definitions, and the multi-language usage tabs) is unaffected and still
// renders statically from the bundled OpenAPI document.
export const OpenAPIPage = createOpenAPIPage({
  playground: { enabled: false },
});
