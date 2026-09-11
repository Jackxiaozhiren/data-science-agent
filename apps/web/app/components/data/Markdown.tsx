"use client";

import * as React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/utils";

// Formatted Markdown renderer (zinc theme). Used for run report previews.
// Styling is scoped to this component via element overrides — no global CSS.
export function Markdown({ text, className }: { text: string; className?: string }) {
  return (
    <div className={cn("min-w-0 text-sm leading-6 text-zinc-700", className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => <h1 className="mt-4 text-lg font-semibold tracking-tight text-zinc-900 first:mt-0">{children}</h1>,
          h2: ({ children }) => <h2 className="mt-4 text-base font-semibold tracking-tight text-zinc-900 first:mt-0">{children}</h2>,
          h3: ({ children }) => <h3 className="mt-3 text-sm font-semibold text-zinc-900 first:mt-0">{children}</h3>,
          h4: ({ children }) => <h4 className="mt-2 text-sm font-semibold text-zinc-900 first:mt-0">{children}</h4>,
          p: ({ children }) => <p className="my-2">{children}</p>,
          ul: ({ children }) => <ul className="my-2 list-disc space-y-1 pl-5">{children}</ul>,
          ol: ({ children }) => <ol className="my-2 list-decimal space-y-1 pl-5">{children}</ol>,
          li: ({ children }) => <li className="leading-6">{children}</li>,
          a: ({ children, href }) => (
            <a href={href} target="_blank" rel="noreferrer" className="font-medium text-zinc-900 underline">
              {children}
            </a>
          ),
          code: ({ children, className: cls }) => {
            const block = (cls ?? "").includes("language-");
            return block ? (
              <code className="font-mono text-[12px]">{children}</code>
            ) : (
              <code className="rounded bg-zinc-100 px-1.5 py-0.5 font-mono text-xs text-zinc-800">{children}</code>
            );
          },
          pre: ({ children }) => (
            <pre className="my-2 max-h-96 overflow-auto rounded-lg bg-zinc-950 p-3 font-mono text-[12px] leading-6 text-zinc-200">{children}</pre>
          ),
          table: ({ children }) => (
            <div className="my-2 w-full overflow-x-auto rounded-lg border border-zinc-200">
              <table className="w-full min-w-[480px] text-xs">{children}</table>
            </div>
          ),
          thead: ({ children }) => <thead className="bg-zinc-50 text-left text-zinc-500">{children}</thead>,
          th: ({ children }) => <th className="whitespace-nowrap px-3 py-2 font-medium">{children}</th>,
          td: ({ children }) => <td className="border-t border-zinc-100 px-3 py-2 align-top">{children}</td>,
          blockquote: ({ children }) => (
            <blockquote className="my-2 border-l-2 border-amber-300 bg-amber-50/50 py-1 pl-3 text-zinc-600">{children}</blockquote>
          ),
          hr: () => <hr className="my-3 border-zinc-200" />,
          strong: ({ children }) => <strong className="font-semibold text-zinc-900">{children}</strong>,
        }}
      >
        {text}
      </ReactMarkdown>
    </div>
  );
}
