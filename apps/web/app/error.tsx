"use client";

import Link from "next/link";
import { ErrorState } from "@/app/components/data/States";
import { Button } from "@/app/components/ui/button";
import { useLocale } from "@/app/lib/LocaleProvider";
import { t } from "@/lib/locale";

export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  const locale = useLocale();
  return (
    <div className="space-y-4">
      <ErrorState
        message={error.message || t(locale, "error.pageBody")}
        retry={reset}
        diagnostics={
          <Link href="/analysis">
            <Button variant="secondary" size="sm">{t(locale, "error.back")}</Button>
          </Link>
        }
      />
    </div>
  );
}
