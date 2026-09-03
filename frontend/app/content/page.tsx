"use client";

import { Suspense, useState } from "react";
import { AlertCircle, RefreshCw, ServerCrash } from "lucide-react";

import { ContentFilters } from "@/components/content/content-filters";
import { ContentSummaryCards } from "@/components/content/content-summary-cards";
import { ContentTable } from "@/components/content/content-table";
import { CurationPanel } from "@/components/content/curation-panel";
import { useContentItems } from "@/hooks/use-content-items";
import { useContentSummary } from "@/hooks/use-content-summary";
import { ContentItem } from "@/lib/types";
import { cn } from "@/lib/utils";

function ContentDashboardContent() {
  const { items, total, loading: loadingItems, error: errorItems, filters, setFilter, resetFilters, refresh: refreshItems } = useContentItems();
  const { summary, loading: loadingSummary, error: errorSummary, refresh: refreshSummary } = useContentSummary();
  const [selectedItem, setSelectedItem] = useState<ContentItem | null>(null);

  const refreshAll = () => {
    refreshItems();
    refreshSummary();
  };

  const hasOfflineError = errorItems?.includes("Não foi possível conectar ao backend") || errorSummary?.includes("Não foi possível conectar ao backend");

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 border-b border-slate-850 pb-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white sm:text-3xl">Radar</h2>
          <p className="mt-1 text-sm text-slate-400">Encontre sinais interessantes, abra a fonte original e guarde o que vale pesquisar depois.</p>
        </div>
        <button onClick={refreshAll} disabled={loadingItems || loadingSummary} className="flex items-center justify-center gap-2 rounded-lg border border-slate-800 bg-[#0b101c] px-4 py-2.5 text-sm font-semibold text-slate-300 transition-all hover:bg-slate-900 disabled:opacity-50">
          <RefreshCw className={cn("h-4 w-4", (loadingItems || loadingSummary) && "animate-spin")} />
          Atualizar
        </button>
      </div>

      {hasOfflineError ? (
        <div className="rounded-xl border border-rose-950 bg-rose-950/20 p-5 text-rose-200 shadow-md">
          <div className="flex items-start gap-3.5">
            <ServerCrash className="mt-0.5 h-6 w-6 shrink-0 text-rose-400" />
            <div className="space-y-1">
              <h3 className="font-bold text-white">Backend indisponível</h3>
              <p className="text-sm text-rose-300/95">Verifique a API FastAPI em <code className="rounded bg-rose-950/60 px-1 py-0.5 font-mono text-xs text-rose-100">{process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"}</code>.</p>
            </div>
          </div>
        </div>
      ) : (
        <>
          {(errorItems || errorSummary) && (
            <div className="rounded-xl border border-amber-950 bg-amber-950/20 p-4 text-amber-200">
              <div className="flex items-center gap-3"><AlertCircle className="h-5 w-5 shrink-0 text-amber-400" /><span className="text-sm font-medium">{errorItems || errorSummary}</span></div>
            </div>
          )}

          <ContentSummaryCards summary={summary} />

          <div className="flex flex-col items-start gap-6 lg:flex-row">
            <div className={cn("w-full transition-all duration-300", selectedItem && "lg:w-[58%] xl:w-[62%]")}>
              <div className="space-y-4">
                <ContentFilters filters={filters} setFilter={setFilter} resetFilters={resetFilters} />
                <ContentTable items={items} total={total} loading={loadingItems} filters={filters} setFilter={setFilter} onSelect={setSelectedItem} selectedId={selectedItem?.id} />
              </div>
            </div>

            {selectedItem && (
              <div className="h-[calc(100vh-7rem)] min-h-[500px] w-full lg:sticky lg:top-[84px] lg:w-[42%] xl:w-[38%]">
                <CurationPanel item={selectedItem} onClose={() => setSelectedItem(null)} onUpdateSuccess={(updated) => { refreshAll(); setSelectedItem(updated); }} />
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

export default function ContentDashboard() {
  return (
    <Suspense fallback={<div className="flex h-[80vh] items-center justify-center"><RefreshCw className="h-8 w-8 animate-spin text-indigo-500" /></div>}>
      <ContentDashboardContent />
    </Suspense>
  );
}
