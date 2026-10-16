"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";
import { recordArrival } from "@/app/lib/productEvents";

/** Renders nothing. Its only job is to report the page view the browser is the one place that knows about. */
export function ArrivalBeacon() {
  const pathname = usePathname();
  useEffect(() => {
    recordArrival(pathname);
  }, [pathname]);
  return null;
}
