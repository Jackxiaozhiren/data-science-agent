"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Boxes, Database, FlaskConical, GitCompare, History, FileText, Gauge, ScrollText, ServerCog, SlidersHorizontal, Bug } from "lucide-react";
import { useLocale } from "@/app/lib/LocaleProvider";
import { t } from "@/lib/locale";
import { cn } from "@/lib/utils";

// R-10: the analyst's loop first, the author's ledgers behind a label that says what they are.
//
// Measured before this file changed (2026-10-15): the top bar put `Analysis`, `Evaluation` and `Research` on one
// level, the sidebar appeared only on `/analysis`, `/datasets` and `/runs` (so on a report page there was no
// workspace navigation at all), and `/evaluations`, `/failures` and `/mcp` were reachable by typing a URL and
// by nothing else. The plan's B1 described the author surfaces as sitting at the same level as the task -- true
// of two of them, and the other three were worse than that: unlinked.
//
// So nothing is deleted or hidden here. The five diagnostic routes gain their first links, in a group whose
// label states that it describes the system rather than the visitor's work, and the analyst group is ordered by
// the loop the product teaches. `NAV_GROUPS` is the declaration the contract test compares against.
//
// The declaration carries *key names*, not sentences (R-13): a group label is rendered both as the landmark's
// accessible name and as the visible heading, so it would otherwise need two owners, and a hand-transcribed label
// in a module-level array is exactly the copy that keeps reading English after the switch.

export const NAV_GROUPS = [
  {
    labelKey: "nav.yourWork",
    key: "analyst",
    items: [
      { href: "/analysis", labelKey: "nav.ask", icon: FlaskConical },
      { href: "/runs", labelKey: "nav.runs", icon: History },
      { href: "/reports", labelKey: "nav.reports", icon: FileText },
      { href: "/datasets", labelKey: "nav.datasets", icon: Database },
    ],
  },
  {
    labelKey: "nav.about",
    key: "system",
    hintKey: "nav.aboutHint",
    items: [
      { href: "/benchmarks", labelKey: "nav.benchmarks", icon: Gauge },
      { href: "/evaluations", labelKey: "nav.evaluations", icon: Boxes },
      { href: "/failures", labelKey: "nav.failures", icon: Bug },
      { href: "/research", labelKey: "nav.research", icon: ScrollText },
      { href: "/runs/compare", labelKey: "nav.compareRuns", icon: GitCompare },
      { href: "/datasets/compare", labelKey: "nav.compareDatasets", icon: GitCompare },
      { href: "/mcp", labelKey: "nav.mcp", icon: ServerCog },
    ],
  },
  {
    labelKey: "nav.machine",
    key: "local",
    hintKey: "nav.machineHint",
    items: [{ href: "/settings", labelKey: "nav.settings", icon: SlidersHorizontal }],
  },
] as const;

export function Sidebar() {
  const locale = useLocale();
  const pathname = usePathname();
  return (
    <aside aria-label={t(locale, "nav.workspace")} className="w-full shrink-0 lg:w-56">
      {NAV_GROUPS.map((group, index) => (
        <nav
          key={group.key}
          aria-label={t(locale, group.labelKey)}
          data-nav-group={group.key}
          className={cn("flex gap-1 overflow-x-auto rounded-xl border bg-white p-1.5 shadow-sm lg:flex-col", index > 0 && "mt-3")}
        >
          {index > 0 && (
            <p className="hidden shrink-0 px-3 pb-1 pt-1 text-[11px] font-semibold uppercase tracking-wider text-zinc-400 lg:block">
              {t(locale, group.labelKey)}
            </p>
          )}
          {group.items.map((it) => {
            const active = pathname === it.href || pathname.startsWith(`${it.href}/`);
            const Icon = it.icon;
            return (
              <Link
                key={it.href}
                href={it.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex shrink-0 items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium",
                  active ? "bg-zinc-900 text-white" : index > 0 ? "text-zinc-500 hover:bg-zinc-100 hover:text-zinc-800" : "text-zinc-600 hover:bg-zinc-100"
                )}
              >
                <Icon className="size-4" aria-hidden />
                {t(locale, it.labelKey)}
              </Link>
            );
          })}
          {"hintKey" in group && group.hintKey ? (
            <p className="hidden px-3 pt-1 text-[11px] leading-4 text-zinc-400 lg:block" aria-hidden>
              {t(locale, group.hintKey)}
            </p>
          ) : null}
        </nav>
      ))}
    </aside>
  );
}
