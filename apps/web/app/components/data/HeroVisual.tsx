"use client";

import { motion } from "framer-motion";
import { FileCheck2, Database, Wrench, ScrollText } from "lucide-react";
import { useLocale } from "@/app/lib/LocaleProvider";
import { t } from "@/lib/locale";

// Home Hero visual: Claim → Evidence → Tool → Dataset hash chain.
// Single permitted decorative block (gradient + grid + beam live in the parent).
export function HeroVisual() {
  const locale = useLocale();
  const nodes = [
    { icon: ScrollText, labelKey: "hero.nodeClaim", subKey: "hero.nodeSubFinding" },
    { icon: FileCheck2, labelKey: "hero.nodeEvidence", sub: "confidence 0.92" },
    { icon: Wrench, labelKey: "hero.nodeToolCall", sub: "sql · stats · ml" },
    { icon: Database, labelKey: "hero.nodeDatasetHash", sub: "sha256 pinned" },
  ];
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="rounded-xl border border-zinc-200 bg-zinc-950 p-4 text-zinc-100 shadow-sm"
      aria-label={t(locale, "hero.evidenceAria")}
    >
      <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-zinc-400">
        {t(locale, "hero.chainTitle")}
      </p>
      <ol className="mt-3 space-y-0">
        {nodes.map((n, i) => {
          const Icon = n.icon;
          return (
            <li key={n.labelKey} className="relative flex gap-3 pb-4 last:pb-0">
              {i < nodes.length - 1 && <span aria-hidden className="absolute left-[15px] top-8 h-full w-px bg-zinc-800" />}
              <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-zinc-900 ring-1 ring-zinc-800" aria-hidden>
                <Icon className="size-4 text-emerald-400" />
              </span>
              <span>
                <span className="block text-sm font-medium">{t(locale, n.labelKey)}</span>
                <span className="block font-mono text-xs text-zinc-400">{"subKey" in n ? t(locale, n.subKey as string) : n.sub}</span>
              </span>
            </li>
          );
        })}
      </ol>
    </motion.div>
  );
}
