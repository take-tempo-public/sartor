import { createMDX } from 'fumadocs-mdx/next';

const withMDX = createMDX();

/** @type {import('next').NextConfig} */
const config = {
  output: 'export',
  // Emit every route as `<route>/index.html` (e.g. out/docs/index.html) rather
  // than a sibling `<route>.html`. Without this, `output: 'export'` writes the
  // docs root as out/docs.html and leaves out/docs/ holding only child pages
  // with no index — so a traditional host (DreamHost/Apache) serving the bare
  // /docs/ directory falls through to mod_autoindex and shows the raw file
  // listing instead of the docs homepage. Trailing-slash routing gives every
  // directory URL its own index.html, which Apache serves natively.
  trailingSlash: true,
  // Serve the projected screenshots as plain static files. `next/image` (which
  // fumadocs-ui uses to render markdown images) defaults to emitting
  // `src="/_next/image?url=…"` — a request to Next's *server-side* image
  // optimizer. There is no server here: `output: 'export'` produces static HTML
  // for a traditional host, so every one of those requests 404s and each
  // screenshot renders as a broken-image glyph (most visibly at the head of each
  // walkthrough step, where the screenshots sit). `unoptimized` makes next/image
  // emit the real `/_next/static/media/*` path, which the host already serves
  // (verified 200). Same family as the `trailingSlash` fix above: a
  // server-rendering default that a static export can't honor.
  images: { unoptimized: true },
  reactStrictMode: true,
};

export default withMDX(config);
