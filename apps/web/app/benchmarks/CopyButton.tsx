"use client";

import * as React from "react";
import { Check, Copy } from "lucide-react";
import { Button } from "@/app/components/ui/button";
import { useLocale } from "@/app/lib/LocaleProvider";
import { t } from "@/lib/locale";

export function CopyButton({ text, label }: { text: string; label: string }) {
  const locale = useLocale();
  const [copied, setCopied] = React.useState(false);
  return (
    <Button
      variant="secondary"
      size="sm"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text);
          setCopied(true);
          setTimeout(() => setCopied(false), 1600);
        } catch {
          setCopied(false);
        }
      }}
      aria-label={label}
    >
      {copied ? <><Check className="size-3.5" aria-hidden /> {t(locale, "copy.copied")}</> : <><Copy className="size-3.5" aria-hidden /> {label}</>}
    </Button>
  );
}
