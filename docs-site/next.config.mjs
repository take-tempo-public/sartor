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
  reactStrictMode: true,
};

export default withMDX(config);
