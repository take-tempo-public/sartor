# docs-site

The hosted sartor. docs site — a Next.js app scaffolded with
[Create Fumadocs](https://github.com/fuma-nama/fumadocs), configured for
[Static Export](https://nextjs.org/docs/app/guides/static-exports)
(`npm run build` -> `out/`, no server process).

**This app renders content it does not author.** `content/docs/` is
generated — not hand-edited — by `../scripts/project_docs_to_mdx.py`, a
deterministic stdlib-only projection of the repo's L1 documentation set
(README + the `docs/**` pages that carry a `Purpose`/`Audience`/
`Authoritative-for` header; see
[`../docs/dev/documentation-architecture.md`](../docs/dev/documentation-architecture.md)).
Edit the cited `.md` source, not the generated `.mdx` — `content/docs/*.mdx`
and `meta.json` are gitignored for exactly this reason.

**Before `npm run dev` or `npm run build`, run the projector from the repo
root:**

```bash
python scripts/project_docs_to_mdx.py
```

Then:

```bash
npm run dev
```

Open http://localhost:3000 with your browser to see the result. CI
(`.github/workflows/docs-deploy.yml`) runs the projector automatically
before every build.

## Explore

In the project, you can see:

- `lib/source.ts`: Code for content source adapter, [`loader()`](https://fumadocs.dev/docs/headless/source-api) provides the interface to access your content.
- `lib/layout.shared.tsx`: Shared options for layouts, optional but preferred to keep.

| Route                     | Description                                            |
| ------------------------- | ------------------------------------------------------ |
| `app/(home)`              | The route group for your landing page and other pages. |
| `app/docs`                | The documentation layout and pages.                    |
| `app/api/search/route.ts` | The Route Handler for search.                          |

### Fumadocs MDX

A `source.config.ts` config file has been included, you can customise different options like frontmatter schema.

Read the [Introduction](https://fumadocs.dev/docs/mdx) for further details.

## Learn More

To learn more about Next.js and Fumadocs, take a look at the following
resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js
  features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.
- [Fumadocs](https://fumadocs.dev) - learn about Fumadocs
