"use client";

import * as React from "react";
import Link from "next/link";
import { FlaskConical, Menu, X } from "lucide-react";
import { Button } from "@/app/components/ui/button";
import { ApiStatusDot } from "@/app/components/layout/ApiStatusDot";
import { ProvenanceStatus } from "@/app/components/layout/ProvenanceStatus";

// Sticky top bar: logo + the analyst loop + GitHub + API dot + mobile menu.
//
// R-10 removed the flat "Analysis | Evaluation | Research" row: it put a measurement of the agent next to the
// thing a visitor came to do, at the same weight, and it named `/analysis` "Analysis" while the sidebar called
// the same route "Ask". The labels now come from the one navigation owner (Sidebar.NAV_GROUPS), and the
// benchmark/evaluation surfaces live in the sidebar group that says what they are. Structure reference:
// TailAdmin / next-shadcn-dashboard topbar pattern.
import { NAV_GROUPS } from "@/app/components/layout/Sidebar";
import { LanguageToggle } from "@/app/components/layout/LanguageToggle";
import { t, type Locale } from "@/lib/locale";

const [analystGroup, systemGroup] = NAV_GROUPS;

export function SiteHeader({ locale }: { locale: Locale }) {
  const [open, setOpen] = React.useState(false);
  return (
    <header className="sticky top-0 z-40 border-b border-zinc-200 bg-white/90 backdrop-blur">
      <nav aria-label={t(locale, "nav.primaryAria")} className="mx-auto flex h-14 max-w-6xl items-center justify-between gap-3 px-4 sm:px-6">
        <Link href="/" className="flex min-w-0 items-center gap-2 font-semibold tracking-tight">
          <span className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-zinc-900 text-white" aria-hidden>
            <FlaskConical className="size-4" />
          </span>
          <span className="truncate">{t(locale, "nav.brand")}</span>
        </Link>
        <div className="hidden items-center gap-1 text-sm md:flex">
          {analystGroup.items.slice(0, 2).map((l) => (
            <Link key={l.href} href={l.href} className="rounded-lg px-3 py-2 text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900">
              {t(locale, l.labelKey)}
            </Link>
          ))}
          <a
            href="https://github.com/Jackxiaozhiren/data-science-agent"
            target="_blank"
            rel="noreferrer"
            className="rounded-lg px-3 py-2 text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900"
          >
            GitHub ↗
          </a>
        </div>
        <div className="flex items-center gap-2">
          <LanguageToggle locale={locale} />
          <ApiStatusDot />
          <ProvenanceStatus />
          <Link href="/datasets" className="hidden md:inline-flex">
            <Button size="sm">{t(locale, "header.try")}</Button>
          </Link>
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
            aria-label={open ? "Close menu" : "Open menu"}
            className="rounded-lg border border-zinc-200 p-2 md:hidden"
          >
            {open ? <X className="size-4" /> : <Menu className="size-4" />}
          </button>
        </div>
      </nav>
      {open && (
        <div className="border-t border-zinc-200 bg-white px-4 py-3 md:hidden">
          <div className="flex flex-col gap-1 text-sm">
            <Link href="/datasets" onClick={() => setOpen(false)} className="rounded-lg bg-zinc-900 px-3 py-2 font-medium text-white">
              Try DSA
            </Link>
            {analystGroup.items.map((l) => (
              <Link key={l.href} href={l.href} onClick={() => setOpen(false)} className="rounded-lg px-3 py-2 text-zinc-700 hover:bg-zinc-100">
                {t(locale, l.labelKey)}
              </Link>
            ))}
            <p className="px-3 pb-1 pt-3 text-[11px] font-semibold uppercase tracking-wider text-zinc-400">
              {t(locale, systemGroup.labelKey)}
            </p>
            {systemGroup.items.map((l) => (
              <Link key={l.href} href={l.href} onClick={() => setOpen(false)} className="rounded-lg px-3 py-2 text-sm text-zinc-500 hover:bg-zinc-100">
                {t(locale, l.labelKey)}
              </Link>
            ))}
            <a href="https://github.com/Jackxiaozhiren/data-science-agent" target="_blank" rel="noreferrer" className="rounded-lg px-3 py-2 text-zinc-700 hover:bg-zinc-100">
              GitHub ↗
            </a>
          </div>
        </div>
      )}
    </header>
  );
}
