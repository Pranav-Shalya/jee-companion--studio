import React, { useMemo } from 'react';
import katex from 'katex';

/**
 * Parses a string containing LaTeX inline ($...$) and block ($$...$$) notations
 * and renders it safely into HTML elements using KaTeX.
 */
export default function LatexRenderer({ content = '', className = '' }) {
  const renderedHtml = useMemo(() => {
    if (!content) return '';

    // First replace block math $$...$$
    let text = content.replace(/\$\$(.*?)\$\$/gs, (match, formula) => {
      try {
        return `<div class="katex-display-wrapper my-2 overflow-x-auto py-1">${katex.renderToString(
          formula.trim(),
          { displayMode: true, throwOnError: false }
        )}</div>`;
      } catch (err) {
        return `<pre class="text-rose-400 bg-rose-950/40 p-2 rounded">${formula}</pre>`;
      }
    });

    // Then replace inline math $...$
    text = text.replace(/\$(.*?)\$/g, (match, formula) => {
      try {
        return katex.renderToString(formula.trim(), {
          displayMode: false,
          throwOnError: false,
        });
      } catch (err) {
        return `<code class="text-rose-400">${formula}</code>`;
      }
    });

    // Format newlines into paragraph breaks if not inside blocks
    text = text.replace(/\n\n/g, '<br/><br/>');

    return text;
  }, [content]);

  return (
    <div
      className={`prose prose-invert max-w-none text-slate-200 leading-relaxed ${className}`}
      dangerouslySetInnerHTML={{ __html: renderedHtml }}
    />
  );
}
