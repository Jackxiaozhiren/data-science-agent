import "./globals.css";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-zinc-50 text-zinc-900">
        <header className="border-b bg-white">
          <nav className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
            <a href="/" className="font-semibold">Data Science Agent</a>
            <div className="flex gap-4 text-sm">
              <a href="/" className="hover:underline">Dashboard</a>
              <a href="/datasets" className="hover:underline">Datasets</a>
              <a href="/analysis" className="hover:underline">Analysis</a>
              <a href="/reports" className="hover:underline">Reports</a>
            </div>
          </nav>
        </header>
        <main className="mx-auto max-w-6xl px-6 py-6">{children}</main>
        <footer className="mx-auto max-w-6xl px-6 py-8 text-center text-xs text-zinc-500">Evidence Before Claim · Code Before Claim · API: http://localhost:8000</footer>
      </body>
    </html>
  );
}
