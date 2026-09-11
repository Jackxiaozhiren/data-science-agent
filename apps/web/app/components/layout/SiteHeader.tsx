"use client";

import * as React from "react";
import Link from "next/link";
import { FlaskConical, Menu, X } from "lucide-react";
import { Button } from "@/app/components/ui/button";
import { ApiStatusDot } from "@/app/components/layout/ApiStatusDot";

// Sticky top bar: logo + Try DSA primary + Analysis/Evaluation/Research/GitHub + API dot + mobile menu.
// Structure reference: TailAdmin / next-shadcn-dashboard topbar pattern.
const links = [
  { href: "/analysis", label: "Analysis" },
  { href: "/benchmarks", label: "Evaluation" },
  { href: "/research", label: "Research" },
];

export function SiteHeader() {
  const [open, setOpen] = React.useState(false);
  return (
    <header className="sticky top-0 z-40 border-b border-zinc-200 bg-white/90 backdrop-blur">
      <nav aria-label="Primary" className="mx-auto flex h-14 max-w-6xl items-center justify-between gap-3 px-4 sm:px-6">
        <Link href="/" className="flex min-w-0 items-center gap-2 font-semibold tracking-tight">
          <span className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-zinc-900 text-white" aria-hidden>
            <FlaskConical className="size-4" />
          </span>
          <span className="truncate">Data Science Agent</span>
        </Link>
        <div className="hidden items-center gap-1 text-sm md:flex">
          {links.map((l) => (
            <Link key={l.href} href={l.href} className="rounded-lg px-3 py-2 text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900">
              {l.label}
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
          <ApiStatusDot />
          <Link href="/datasets" className="hidden md:inline-flex">
            <Button size="sm">Try DSA</Button>
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
            {links.map((l) => (
              <Link key={l.href} href={l.href} onClick={() => setOpen(false)} className="rounded-lg px-3 py-2 text-zinc-700 hover:bg-zinc-100">
                {l.label}
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
