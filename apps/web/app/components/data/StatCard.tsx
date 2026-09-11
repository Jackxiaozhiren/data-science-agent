import type { LucideIcon } from "lucide-react";
import { Card, CardContent } from "@/app/components/ui/card";
import { cn } from "@/lib/utils";

const accentRing: Record<string, string> = {
  zinc: "text-zinc-500",
  emerald: "text-emerald-600",
  amber: "text-amber-600",
  red: "text-red-600",
};

// Unified StatCard: label + value + hint + optional icon.
export function StatCard({
  label,
  value,
  hint,
  icon: Icon,
  accent = "zinc",
  className,
}: {
  label: string;
  value: string;
  hint?: string;
  icon?: LucideIcon;
  accent?: "zinc" | "emerald" | "amber" | "red";
  className?: string;
}) {
  return (
    <Card className={cn(className)}>
      <CardContent className="p-4 pt-4">
        <div className="flex items-center justify-between gap-2">
          <p className="text-xs font-medium uppercase tracking-wider text-zinc-500">{label}</p>
          {Icon && <Icon className={cn("size-4", accentRing[accent])} aria-hidden />}
        </div>
        <p className="mt-1 truncate text-xl font-semibold tracking-tight" title={value}>
          {value}
        </p>
        {hint && <p className="mt-0.5 truncate text-xs text-zinc-500" title={hint}>{hint}</p>}
      </CardContent>
    </Card>
  );
}
