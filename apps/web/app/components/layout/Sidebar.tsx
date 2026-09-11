"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Database, FlaskConical, History, FileText } from "lucide-react";
import { cn } from "@/lib/utils";

const items = [
  { href: "/analysis", label: "Ask", icon: FlaskConical },
  { href: "/datasets", label: "Datasets", icon: Database },
  { href: "/runs", label: "Trace", icon: History },
  { href: "/reports", label: "Reports", icon: FileText },
];

// Secondary sidebar, only rendered for Analysis/Datasets/Trace-related routes.
export function Sidebar() {
  const pathname = usePathname();
  const show = pathname.startsWith("/analysis") || pathname.startsWith("/datasets") || pathname.startsWith("/runs");
  if (!show) return null;
  return (
    <aside aria-label="Workspace" className="w-full shrink-0 lg:w-52">
      <nav className="flex gap-1 overflow-x-auto rounded-xl border bg-white p-1.5 shadow-sm lg:flex-col">
        {items.map((it) => {
          const active = pathname === it.href || pathname.startsWith(`${it.href}/`);
          const Icon = it.icon;
          return (
            <Link
              key={it.href}
              href={it.href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "flex shrink-0 items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium",
                active ? "bg-zinc-900 text-white" : "text-zinc-600 hover:bg-zinc-100"
              )}
            >
              <Icon className="size-4" aria-hidden />
              {it.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
