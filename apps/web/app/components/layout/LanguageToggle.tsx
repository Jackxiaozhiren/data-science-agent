"use client";

// R-13: the control that chooses the interface language.
//
// The current value arrives as a prop from the server layout rather than being read from `document.cookie`
// here, because this component is server-rendered too: reading the cookie during render would produce English
// markup on the server and Chinese in the browser, which is a hydration mismatch and a visible flash.
//
// Switching reloads the route. That is deliberate: without it the pages that already rendered on the server --
// the landing page, the run list -- would keep their old language while only the client-rendered parts
// switched, and a half-translated screen is worse than a slower whole one.

import { useRouter } from "next/navigation";
import { LOCALES, LOCALE_LABELS, storeLocale, t, type Locale } from "@/lib/locale";

export function LanguageToggle({ locale, className }: { locale: Locale; className?: string }) {
  const router = useRouter();

  function choose(next: Locale) {
    if (next === locale) return;
    storeLocale(next);
    router.refresh();
    // `refresh` re-runs the server components; anything rendered purely in the browser picks the new value up
    // from the cookie on its next render, so a reload is what makes both halves agree immediately.
    window.location.reload();
  }

  return (
    <div
      role="group"
      aria-label={t(locale, "lang.aria")}
      className={`flex items-center gap-1 rounded-lg border border-zinc-200 p-0.5 ${className ?? ""}`}
    >
      {LOCALES.map((code) => (
        <button
          key={code}
          type="button"
          aria-pressed={code === locale}
          onClick={() => choose(code)}
          className={`rounded-md px-2 py-0.5 text-xs font-medium transition-colors hover:bg-zinc-100 ${
            code === locale ? "bg-zinc-900 text-white" : "text-zinc-600"
          }`}
        >
          {LOCALE_LABELS[code]}
        </button>
      ))}
    </div>
  );
}
