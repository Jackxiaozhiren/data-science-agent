import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

// shadcn/ui Badge — https://ui.shadcn.com/docs/components/badge
// Palette locked to zinc + emerald/amber/red per design language.
const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium transition-colors focus:outline-none",
  {
    variants: {
      variant: {
        default: "border-zinc-900 bg-zinc-900 text-white",
        secondary: "border-zinc-200 bg-zinc-100 text-zinc-700",
        outline: "border-zinc-200 bg-white text-zinc-700",
        success: "border-emerald-200 bg-emerald-50 text-emerald-700",
        warning: "border-amber-200 bg-amber-50 text-amber-800",
        destructive: "border-red-200 bg-red-50 text-red-700",
      },
    },
    defaultVariants: { variant: "secondary" },
  }
);

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
