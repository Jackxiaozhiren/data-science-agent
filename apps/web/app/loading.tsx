import { CardsSkeleton, TableSkeleton } from "@/app/components/data/States";
import { serverLocale } from "@/lib/serverApi";
import { t } from "@/lib/locale";

export default async function Loading() {
  // A route-level `loading.tsx` is a server component, so the language comes from the request rather than from
  // context; the skeletons below are client components and read it through the provider. One sentence, two
  // routes to it, and both are answered before the browser paints, so nothing re-paints on hydration.
  const locale = await serverLocale();
  return (
    <div className="space-y-4" aria-label={t(locale, "state.loadingPage")} aria-busy="true">
      <div className="space-y-2">
        <div className="h-3 w-24 animate-pulse rounded bg-zinc-200" />
        <div className="h-6 w-64 animate-pulse rounded bg-zinc-200" />
        <div className="h-4 w-full max-w-xl animate-pulse rounded bg-zinc-100" />
      </div>
      <CardsSkeleton />
      <TableSkeleton rows={4} />
    </div>
  );
}
