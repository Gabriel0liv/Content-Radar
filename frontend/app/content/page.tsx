"use client";

import { useState } from "react";
import { useContentItems } from "@/hooks/use-content-items";
import { useContentSummary } from "@/hooks/use-content-summary";
import { ContentSummaryCards } from "@/components/content/content-summary-cards";
import { ContentFilters } from "@/components/content/content-filters";
import { ContentTable } from "@/components/content/content-table";
import { CurationPanel } from "@/components/content/curation-panel";
import { ContentItem } from "@/lib/types";
import { RefreshCw, ServerCrash, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";

export default function ContentDashboard() {
  const {
    items,
    total,
    loading: loadingItems,
    error: errorItems,
    filters,
    setFilter,
    resetFilters,
    refresh: refreshItems,
  } = useContentItems();

  const {
    summary,
    loading: loadingSummary,
    error: errorSummary,
    refresh: refreshSummary,
  } = useContentSummary();

  const [selectedItem, setSelectedItem] = useState<ContentItem | null>(null);

  const handleRefreshAll = () => {
    refreshItems();
    refreshSummary();
  };

  const hasOfflineError =
    errorItems?.includes("Não foi possível conectar ao backend") ||
    errorSummary?.includes("Não foi possível conectar ao backend");

  return (
    <div className="space-y-6">
      {/* Top Header Section */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-slate-850 pb-5">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white sm:text-3xl">Painel de Curadoria</h2>
          <p className="mt-1 text-sm text-slate-400">
            Analise e selecione sinais qualificados recolhidos do YouTube e Google News.
          </p>
        </div>
        <button
          onClick={handleRefreshAll}
          disabled={loadingItems || loadingSummary}
          className="flex items-center justify-center gap-2 rounded-lg border border-slate-800 bg-[#0b101c] px-4 py-2.5 text-sm font-semibold text-slate-300 hover:bg-slate-900 active:bg-slate-950 transition-all select-none disabled:opacity-50"
        >
          <RefreshCw className={cn("h-4 w-4", (loadingItems || loadingSummary) && "animate-spin")} />
          <span>Atualizar Dados</span>
        </button>
      </div>

      {/* Offline Error Alert Banner */}
      {hasOfflineError ? (
        <div className="rounded-xl border border-rose-950 bg-rose-950/20 p-5 text-rose-200 shadow-md">
          <div className="flex items-start gap-3.5">
            <ServerCrash className="h-6 w-6 text-rose-400 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <h3 className="font-bold text-white">Servidor Backend Indisponível</h3>
              <p className="text-sm text-rose-300/95">
                Não conseguimos estabelecer conexão com a API FastAPI em{" "}
                <code className="rounded bg-rose-950/60 px-1 py-0.5 font-mono text-xs text-rose-100">
                  {process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"}
                </code>
                .
              </p>
              <p className="text-xs text-rose-400/90 pt-1.5">
                Por favor, verifique se o backend está rodando localmente (ex: executando{" "}
                <code className="rounded bg-rose-950/60 px-1 py-0.5 font-mono text-[10px] text-rose-100">
                  poetry run uvicorn src.api.main:app --reload
                </code>
                ).
              </p>
            </div>
          </div>
        </div>
      ) : (
        <>
          {/* General API error alerts */}
          {(errorItems || errorSummary) && (
            <div className="rounded-xl border border-amber-950 bg-amber-950/20 p-4 text-amber-200">
              <div className="flex items-center gap-3">
                <AlertCircle className="h-5 w-5 text-amber-400 shrink-0" />
                <span className="text-sm font-medium">
                  {errorItems || errorSummary || "Ocorreu um erro ao buscar atualizações do servidor."}
                </span>
              </div>
            </div>
          )}

          {/* Metric Summary Widgets */}
          <ContentSummaryCards summary={summary} />

          {/* Table list and curation editor panel */}
          <div className="flex flex-col lg:flex-row gap-6 items-start">
            <div className={cn("w-full transition-all duration-300", selectedItem && "lg:w-[58%] xl:w-[62%]")}>
              <div className="space-y-4">
                <ContentFilters filters={filters} setFilter={setFilter} resetFilters={resetFilters} />
                <ContentTable
                  items={items}
                  total={total}
                  loading={loadingItems}
                  filters={filters}
                  setFilter={setFilter}
                  onSelect={setSelectedItem}
                  selectedId={selectedItem?.id}
                />
              </div>
            </div>

            {selectedItem && (
              <div className="w-full lg:w-[42%] xl:w-[38%] lg:sticky lg:top-[84px] h-[calc(100vh-7rem)] min-h-[500px]">
                <CurationPanel
                  item={selectedItem}
                  onClose={() => setSelectedItem(null)}
                  onUpdateSuccess={(updatedItem) => {
                    // Refresh parent content state
                    refreshItems();
                    refreshSummary();
                    // Keep the side panel active with updated information
                    setSelectedItem(updatedItem);
                  }}
                />
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
