"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Boxes, Database, FlaskConical, GitCompare, History, FileText, Gauge, ScrollText, ServerCog, Bug } from "lucide-react";
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

export const NAV_GROUPS = [
  {
    label: "Your work",
    key: "analyst",
    items: [
      { href: "/analysis", label: "Ask", icon: FlaskConical },
      { href: "/runs", label: "Runs", icon: History },
      { href: "/reports", label: "Reports", icon: FileText },
      { href: "/datasets", label: "Datasets", icon: Database },
    ],
  },
  {
    label: "About this system",
    key: "system",
    hint: "Benchmarks, evaluations and audit surfaces -- measurements of the agent, not of your data.",
    items: [
      { href: "/benchmarks", label: "Benchmarks", icon: Gauge },
      { href: "/evaluations", label: "Evaluations", icon: Boxes },
      { href: "/failures", label: "Failures", icon: Bug },
      { href: "/research", label: "Research", icon: ScrollText },
      { href: "/runs/compare", label: "Compare runs", icon: GitCompare },
      { href: "/datasets/compare", label: "Compare datasets", icon: GitCompare },
      { href: "/mcp", label: "MCP", icon: ServerCog },
    ],
  },
] as const;

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside aria-label="Workspace" className="w-full shrink-0 lg:w-56">
      {NAV_GROUPS.map((group, index) => (
        <nav
          key={group.key}
          aria-label={group.label}
          data-nav-group={group.key}
          className={cn("flex gap-1 overflow-x-auto rounded-xl border bg-white p-1.5 shadow-sm lg:flex-col", index > 0 && "mt-3")}
        >
          {index > 0 && (
            <p className="hidden shrink-0 px-3 pb-1 pt-1 text-[11px] font-semibold uppercase tracking-wider text-zinc-400 lg:block">
              {group.label}
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
                {it.label}
              </Link>
            );
          })}
          {"hint" in group && group.hint ? (
            <p className="hidden px-3 pt-1 text-[11px] leading-4 text-zinc-400 lg:block" aria-hidden>
              {group.hint}
            </p>
          ) : null}
        </nav>
      ))}
    </aside>
  );
}
