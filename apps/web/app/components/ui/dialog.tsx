"use client";

import * as React from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

// shadcn/ui Dialog (minimal, dependency-free port) — https://ui.shadcn.com/docs/components/dialog
export function Dialog({
  open,
  onOpenChange,
  children,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  children: React.ReactNode;
}) {
  React.useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onOpenChange(false);
    };
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [open, onOpenChange]);

  if (!open) return null;
  return <>{children}</>;
}

export function DialogContent({ className, onClose, children }: { className?: string; onClose: () => void; children: React.ReactNode }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true">
      <button aria-label="Close dialog" onClick={onClose} className="absolute inset-0 bg-zinc-950/40" />
      <div className={cn("relative w-full max-w-lg rounded-xl border bg-white p-5 shadow-sm", className)}>
        <button
          onClick={onClose}
          aria-label="Close"
          className="absolute right-3 top-3 rounded-lg p-1 text-zinc-500 hover:bg-zinc-100"
        >
          <X className="size-4" />
        </button>
        {children}
      </div>
    </div>
  );
}

export function DialogHeader({ className, children }: { className?: string; children: React.ReactNode }) {
  return <div className={cn("mb-3 space-y-1", className)}>{children}</div>;
}

export function DialogTitle({ className, children }: { className?: string; children: React.ReactNode }) {
  return <h2 className={cn("font-semibold tracking-tight", className)}>{children}</h2>;
}

export function DialogDescription({ className, children }: { className?: string; children: React.ReactNode }) {
  return <p className={cn("text-sm leading-6 text-zinc-600", className)}>{children}</p>;
}

// shadcn/ui Tooltip (minimal, CSS-only) — https://ui.shadcn.com/docs/components/tooltip
export function Tooltip({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <span className="group relative inline-flex" title={label}>
      {children}
      <span
        role="tooltip"
        className="pointer-events-none absolute -top-8 left-1/2 hidden -translate-x-1/2 whitespace-nowrap rounded-lg border bg-zinc-900 px-2 py-1 text-xs text-white group-hover:block"
      >
        {label}
      </span>
    </span>
  );
}
