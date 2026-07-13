import { defineConfig, defineDocs } from 'fumadocs-mdx/config';
import { remarkMdxMermaid } from 'fumadocs-core/mdx-plugins';
import { metaSchema, pageSchema } from 'fumadocs-core/source/schema';
import { z } from 'zod';

// Frontmatter schema extended with the two fields
// scripts/project_docs_to_mdx.py projects from each L1 doc's Purpose/Audience/
// Authoritative-for header (see docs/dev/documentation-architecture.md
// "Fumadocs sourcing"): `audience` gates which ICP front door a page belongs
// to (mirrors docs/wiki/SCHEMA.md's user/dev tag), `authoritativeFor` is the
// canonical-home marker. Both are additive metadata on top of the stock
// fumadocs pageSchema, not a replacement for it.
const projectedPageSchema = pageSchema.extend({
  audience: z.array(z.enum(['user', 'dev'])).optional(),
  authoritativeFor: z.string().optional(),
});

export const docs = defineDocs({
  dir: 'content/docs',
  docs: {
    schema: projectedPageSchema,
    postprocess: {
      includeProcessedMarkdown: true,
    },
  },
  meta: {
    schema: metaSchema,
  },
});

export default defineConfig({
  mdxOptions: {
    // The four architecture diagrams are authored as ```mermaid fences in
    // docs/architecture.md (the single source — the standalone docs/diagrams/*.mmd
    // copies were retired). Fumadocs ships no Mermaid renderer by default, so
    // those fences were shipping to the public site as raw code blocks. This
    // plugin rewrites a ```mermaid fence into <Mermaid chart="…" />, which
    // src/components/mermaid.tsx renders client-side (registered in
    // src/components/mdx.tsx).
    remarkPlugins: [remarkMdxMermaid],
  },
});
