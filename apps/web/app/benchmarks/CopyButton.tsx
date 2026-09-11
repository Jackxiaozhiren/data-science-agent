"use client";

import * as React from "react";
import { Check, Copy } from "lucide-react";
import { Button } from "@/app/components/ui/button";

export function CopyButton({ text, label = "Copy" }: { text: string; label?: string }) {
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
      aria-label={`${label} runner command`}
    >
      {copied ? <><Check className="size-3.5" aria-hidden /> Copied</> : <><Copy className="size-3.5" aria-hidden /> {label}</>}
    </Button>
  );
}
