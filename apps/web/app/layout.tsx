import type { Metadata } from "next";
import "./globals.css";
import { SiteHeader } from "@/app/components/layout/SiteHeader";
import { SiteFooter } from "@/app/components/layout/SiteFooter";
import { Sidebar } from "@/app/components/layout/Sidebar";

export const metadata: Metadata = {
  title: "Data Science Agent — Verifiable AI Data Science",
  description: "The AI data scientist that shows its work. Ask questions about your data and inspect the evidence behind the answer.",
  icons: { icon: "/icon.svg" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-zinc-50 text-zinc-900">
        <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:rounded-lg focus:bg-zinc-900 focus:px-3 focus:py-2 focus:text-sm focus:text-white">
          Skip to content
        </a>
        <SiteHeader />
        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-6 sm:px-6 lg:flex-row">
          <Sidebar />
          <main id="main" className="min-w-0 flex-1">
            {children}
          </main>
        </div>
        <SiteFooter />
      </body>
    </html>
  );
}
