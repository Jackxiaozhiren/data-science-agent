"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

// shadcn/ui Tabs (lightweight controlled/uncontrolled port, Tailwind v3 safe)
// API: https://ui.shadcn.com/docs/components/tabs
type TabsContextValue = { value: string; setValue: (v: string) => void };

const TabsContext = React.createContext<TabsContextValue | null>(null);

export function Tabs({
  defaultValue,
  value,
  onValueChange,
  className,
  children,
}: {
  defaultValue?: string;
  value?: string;
  onValueChange?: (v: string) => void;
  className?: string;
  children: React.ReactNode;
}) {
  const [inner, setInner] = React.useState(defaultValue ?? "");
  const current = value ?? inner;
  const setValue = React.useCallback(
    (v: string) => {
      setInner(v);
      onValueChange?.(v);
    },
    [onValueChange]
  );
  return <TabsContext.Provider value={{ value: current, setValue }}><div className={cn("w-full", className)}>{children}</div></TabsContext.Provider>;
}

export function TabsList({ className, children }: { className?: string; children: React.ReactNode }) {
  return (
    <div
      role="tablist"
      aria-orientation="horizontal"
      className={cn("inline-flex h-9 w-full items-center justify-start gap-1 overflow-x-auto rounded-lg bg-zinc-100 p-1 text-zinc-600 sm:w-auto", className)}
    >
      {children}
    </div>
  );
}

export function TabsTrigger({ value, className, children }: { value: string; className?: string; children: React.ReactNode }) {
  const ctx = React.useContext(TabsContext);
  if (!ctx) throw new Error("TabsTrigger must be used within Tabs");
  const active = ctx.value === value;
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      data-state={active ? "active" : "inactive"}
      onClick={() => ctx.setValue(value)}
      className={cn(
        "inline-flex shrink-0 items-center justify-center whitespace-nowrap rounded-md px-3 py-1 text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-400 disabled:pointer-events-none disabled:opacity-50",
        active ? "bg-white text-zinc-900 shadow-sm" : "text-zinc-500 hover:text-zinc-900",
        className
      )}
    >
      {children}
    </button>
  );
}

export function TabsContent({ value, className, children }: { value: string; className?: string; children: React.ReactNode }) {
  const ctx = React.useContext(TabsContext);
  if (!ctx) throw new Error("TabsContent must be used within Tabs");
  if (ctx.value !== value) return null;
  return (
    <div role="tabpanel" className={cn("mt-4 focus-visible:outline-none", className)}>
      {children}
    </div>
  );
}
