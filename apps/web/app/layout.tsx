import type { Metadata } from "next";
import "./globals.css";
import { SiteHeader } from "@/app/components/layout/SiteHeader";
import { ArrivalBeacon } from "@/app/components/layout/ArrivalBeacon";
import { SiteFooter } from "@/app/components/layout/SiteFooter";
import { Sidebar } from "@/app/components/layout/Sidebar";
import { serverLocale } from "@/lib/serverApi";
import { t } from "@/lib/locale";
import { LocaleProvider } from "@/app/lib/LocaleProvider";

// R-13: the tab title and the document language follow the browser's choice, which means both are read per
// request. This layout therefore renders on every navigation -- a price worth paying, because a Chinese
// reader whose browser chrome and skip link stay English is being told the translation is a decoration.
export async function generateMetadata(): Promise<Metadata> {
  const locale = await serverLocale();
  return {
    title: t(locale, "meta.title"),
    description: t(locale, "meta.description"),
    icons: { icon: "/icon.svg" },
  };
}

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const locale = await serverLocale();
  return (
    <html lang={locale}>
      <body className="min-h-screen bg-zinc-50 text-zinc-900">
        {/* The route below may be a client component, and a client component cannot look the language up for
            itself without disagreeing with its own server render. So the answer the layout already paid for is
            handed down here, once -- and it wraps the whole shell, not just `<main>`: the sidebar is a client
            component reading this context, and while the provider sat inside `<main>` every navigation label
            rendered English on a 中文 page, which no source guard and no single-page browser test could see. */}
        <LocaleProvider locale={locale}>
          <ArrivalBeacon />
          <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:rounded-lg focus:bg-zinc-900 focus:px-3 focus:py-2 focus:text-sm focus:text-white">
            {t(locale, "a11y.skip")}
          </a>
          <SiteHeader locale={locale} />
          <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-6 sm:px-6 lg:flex-row">
            <Sidebar />
            <main id="main" className="min-w-0 flex-1">
              {children}
            </main>
          </div>
          <SiteFooter />
        </LocaleProvider>
      </body>
    </html>
  );
}
