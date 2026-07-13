'use client';

// Client-side Mermaid renderer for the ```mermaid fences in the projected docs
// (the four architecture diagrams). `remarkMdxMermaid` (source.config.ts) turns
// each fence into <Mermaid chart="…" />; this renders it.
//
// Client-only by necessity: mermaid parses and lays out in the browser (it needs
// a DOM to measure text). Under `output: 'export'` the page HTML is generated at
// build time, so the diagram is drawn on mount — hence the `useEffect` + the
// `<pre>` fallback below, which is also what a reader with JS disabled sees.

import { useEffect, useId, useState } from 'react';
import { useTheme } from 'next-themes';

export function Mermaid({ chart }: { chart: string }) {
  const id = useId().replace(/:/g, '_'); // mermaid ids must be CSS-selector safe
  const { resolvedTheme } = useTheme();
  const [svg, setSvg] = useState<string>('');
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;

    void (async () => {
      const { default: mermaid } = await import('mermaid');

      mermaid.initialize({
        startOnLoad: false,
        securityLevel: 'strict', // no click-handler / script injection from diagram text
        theme: resolvedTheme === 'dark' ? 'dark' : 'default',
        fontFamily: 'inherit',
      });

      try {
        const { svg } = await mermaid.render(`mermaid-${id}`, chart.trim());
        if (!cancelled) setSvg(svg);
      } catch {
        // A malformed diagram must not take the page down — fall back to the
        // source text, which is strictly more useful than an empty box.
        if (!cancelled) setFailed(true);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [chart, id, resolvedTheme]);

  if (failed || !svg) {
    return (
      <pre className="fd-codeblock overflow-x-auto text-sm">
        <code>{chart.trim()}</code>
      </pre>
    );
  }

  // The SVG comes from mermaid's own renderer running under securityLevel:
  // 'strict' (it sanitizes the diagram text), and the input is our own committed
  // markdown — not user content.
  return (
    <div
      className="my-4 overflow-x-auto [&_svg]:mx-auto [&_svg]:h-auto [&_svg]:max-w-full"
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}
