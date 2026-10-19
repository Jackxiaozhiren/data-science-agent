"use client";

// R-13: how a client component learns which language to render.
//
// Reading `document.cookie` inside the component is the obvious version and it is wrong: the same component is
// rendered on the server first, where there is no cookie to read, so the server would emit English markup and
// the browser would immediately re-render in Chinese -- a hydration mismatch and a visible flash on every
// navigation. The root layout already reads the cookie on the server, so it hands the answer down through here
// and the value is part of the rendered tree on both sides of the boundary.
import { createContext, useContext } from "react";
import type { Locale } from "@/lib/locale";

const LocaleContext = createContext<Locale>("en");

export function LocaleProvider({ locale, children }: { locale: Locale; children: React.ReactNode }) {
  return <LocaleContext.Provider value={locale}>{children}</LocaleContext.Provider>;
}

/** The language this page was rendered in. Defaults to English when nothing provided it. */
export function useLocale(): Locale {
  return useContext(LocaleContext);
}
