import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Data Science Agent — Verifiable AI Data Science",
  description: "The AI data scientist that shows its work. Ask questions about your data and inspect the evidence behind the answer.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-zinc-50 text-zinc-900">
        <header className="border-b bg-white">
          <nav className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
            <a href="/" className="font-semibold">Data Science Agent</a>
            <div className="flex flex-wrap items-center justify-end gap-4 text-sm">
              <a href="/datasets" className="font-medium hover:underline">Try DSA</a>
              <a href="/analysis" className="hover:underline">Analysis</a>
              <a href="/benchmarks" className="hover:underline">Evaluation</a>
              <a href="/research" className="hover:underline">Research</a>
              <a href="https://github.com/Jackxiaozhiren/data-science-agent" className="hover:underline" target="_blank" rel="noreferrer">GitHub ↗</a>
            </div>
          </nav>
        </header>
        <main className="mx-auto max-w-6xl px-6 py-6">{children}</main>
        <footer className="mx-auto max-w-6xl px-6 py-8 text-center text-xs text-zinc-500">
          Evidence before claim · Ask. Analyze. Verify. Reproduce.
        </footer>
      </body>
    </html>
  );
}
