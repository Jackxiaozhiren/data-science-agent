import { apiUrl } from "@/lib/api";
import { serverLocale } from "@/lib/serverApi";
import { t } from "@/lib/locale";
import { ProvenanceStatus } from "@/app/components/layout/ProvenanceStatus";

// Footer: slogan + which build this is (R-09) + GitHub/Docs/API /health links.
export async function SiteFooter() {
  const locale = await serverLocale();
  return (
    <footer className="border-t border-zinc-200 bg-white">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-3 px-4 py-6 text-xs text-zinc-500 sm:flex-row sm:px-6">
        <p className="flex flex-wrap items-center justify-center gap-2 sm:justify-start">
          <span>{t(locale, "footer.tagline")}</span>
          <ProvenanceStatus showVersion />
        </p>
        <nav aria-label={t(locale, "nav.footerAria")} className="flex flex-wrap items-center justify-center gap-4">
          <a href="https://github.com/Jackxiaozhiren/data-science-agent" target="_blank" rel="noreferrer" className="hover:underline">
            GitHub
          </a>
          <a href="https://github.com/Jackxiaozhiren/data-science-agent/tree/main/docs" target="_blank" rel="noreferrer" className="hover:underline">
            Docs
          </a>
          <a href={apiUrl("/health")} target="_blank" rel="noreferrer" className="hover:underline">
            API /health
          </a>
          <a href={apiUrl("/version")} target="_blank" rel="noreferrer" className="hover:underline">
            /version
          </a>
        </nav>
      </div>
    </footer>
  );
}
