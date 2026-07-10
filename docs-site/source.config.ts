import { defineConfig, defineDocs } from 'fumadocs-mdx/config';
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
    // MDX options
  },
});
