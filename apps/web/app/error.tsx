"use client";

import Link from "next/link";
import { ErrorState } from "@/app/components/data/States";
import { Button } from "@/app/components/ui/button";

export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div className="space-y-4">
      <ErrorState
        message={error.message || "This page could not be rendered. The API may be unavailable."}
        retry={reset}
        diagnostics={
          <Link href="/analysis">
            <Button variant="secondary" size="sm">Back to Analysis</Button>
          </Link>
        }
      />
    </div>
  );
}
