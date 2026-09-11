import { CheckCircle2, Circle, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

export type TraceStep = {
  id: string;
  name: string;
  tool: string;
  description?: string;
  status?: "done" | "active" | "todo";
};

// Unified TraceTimeline: vertical Plan timeline used by run/trace pages.
export function TraceTimeline({ steps }: { steps: TraceStep[] }) {
  if (steps.length === 0) return <p className="text-sm text-zinc-500">No plan steps.</p>;
  return (
    <ol className="relative space-y-4 border-l border-zinc-200 pl-5">
      {steps.map((s) => (
        <li key={s.id} className="relative">
          <span
            aria-hidden
            className={cn(
              "absolute -left-[27px] flex size-4 items-center justify-center rounded-full bg-white",
              s.status === "done" ? "text-emerald-600" : s.status === "active" ? "text-amber-600" : "text-zinc-300"
            )}
          >
            {s.status === "done" ? (
              <CheckCircle2 className="size-4" />
            ) : s.status === "active" ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <Circle className="size-4" />
            )}
          </span>
          <p className="text-sm font-medium">
            {s.name} <code className="ml-1 rounded bg-zinc-100 px-1.5 py-0.5 font-mono text-xs text-zinc-600">{s.tool}</code>
          </p>
          {s.description && <p className="mt-0.5 text-xs leading-5 text-zinc-500">{s.description}</p>}
        </li>
      ))}
    </ol>
  );
}
