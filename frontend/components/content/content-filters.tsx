"use client";

import { useEffect, useState } from "react";
import { Search, SlidersHorizontal, RotateCcw, ArrowUpDown } from "lucide-react";

import { DiscoveryAutocomplete } from "@/components/search/discovery-autocomplete";
import type { DiscoveryTerm } from "@/lib/types";
import { cn } from "@/lib/utils";

interface FiltersProps {
  filters: {
    search: string;
    source: string;
    content_type: string;
    status: string;
    topic_seed: string;
    topic_id: number;
    min_topic_confidence: number;
    min_score: number;
    min_views: number;
    min_performance_ratio: number;
    sort_by: string;
    sort_order: string;
  };
  setFilter: (key: any, value: any) => void;
  resetFilters: () => void;
}

export function ContentFilters({ filters, setFilter, resetFilters }: FiltersProps) {
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [selectedTopics, setSelectedTopics] = useState<DiscoveryTerm[]>([]);

  useEffect(() => {
    if (!filters.topic_id && selectedTopics.length > 0) setSelectedTopics([]);
  }, [filters.topic_id, selectedTopics.length]);

  const changeTopic = (terms: DiscoveryTerm[]) => {
    const last = terms.at(-1);
    const next = last && last.entity_id !== null ? [last] : [];
    setSelectedTopics(next);
    setFilter("topic_id", next[0]?.entity_id || 0);
  };

  const clearAll = () => {
    setSelectedTopics([]);
    resetFilters();
  };

  return (
    <div className="space-y-4 rounded-xl border border-slate-800/80 bg-[#0b101c]/30 p-5 backdrop-blur-sm">
      <div className="flex flex-col gap-4 md:flex-row md:items-center">
        <div className="relative flex-1">
          <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
          <input type="text" placeholder="Pesquisar por título ou descrição..." value={filters.search} onChange={(e) => setFilter("search", e.target.value)} className="w-full rounded-lg border border-slate-800 bg-slate-950/80 py-2.5 pl-10 pr-4 text-sm text-slate-200 placeholder-slate-500 outline-none transition-all focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20" />
        </div>

        <div className="w-full md:w-44">
          <select value={filters.status} onChange={(e) => setFilter("status", e.target.value)} className="w-full rounded-lg border border-slate-800 bg-slate-950/80 px-3 py-2.5 text-sm text-slate-300 outline-none focus:border-indigo-500">
            <option value="Todos">Status: Todos</option><option value="new">Novo</option><option value="reviewed">Revisado</option><option value="selected">Selecionado</option><option value="rejected">Rejeitado</option><option value="archived">Arquivado</option>
          </select>
        </div>

        <div className="w-full md:w-56">
          <select value={filters.sort_by} onChange={(e) => setFilter("sort_by", e.target.value)} className="w-full rounded-lg border border-slate-800 bg-slate-950/80 px-3 py-2.5 text-sm text-slate-300 outline-none focus:border-indigo-500">
            <option value="performance_ratio">Ordenar: Breakout do canal</option><option value="views_per_day">Ordenar: Views/dia</option><option value="views">Ordenar: Total views</option><option value="score">Ordenar: Score</option><option value="published_at">Ordenar: Publicação</option><option value="collected_at">Ordenar: Coleta</option>
          </select>
        </div>

        <button onClick={() => setFilter("sort_order", filters.sort_order === "asc" ? "desc" : "asc")} className="flex h-10 w-10 items-center justify-center rounded-lg border border-slate-800 bg-slate-950/50 text-slate-400 hover:bg-slate-900 hover:text-slate-200" title="Alternar ordenação"><ArrowUpDown className={cn("h-4 w-4 transition-transform", filters.sort_order === "asc" && "rotate-180")} /></button>
        <button onClick={() => setShowAdvanced(!showAdvanced)} className={cn("flex items-center justify-center gap-2 rounded-lg border px-4 py-2.5 text-sm font-medium", showAdvanced ? "border-indigo-500/30 bg-indigo-600/10 text-indigo-400" : "border-slate-800 bg-slate-950/50 text-slate-400 hover:bg-slate-900")}><SlidersHorizontal className="h-4 w-4" /> Filtros</button>
        <button onClick={clearAll} className="flex h-10 w-10 items-center justify-center rounded-lg border border-slate-800 bg-slate-950/30 text-slate-500 hover:bg-slate-900 hover:text-slate-300" title="Limpar filtros"><RotateCcw className="h-4 w-4" /></button>
      </div>

      <div className={cn("space-y-4 border-t border-slate-800/60 pt-4", showAdvanced ? "block" : "hidden")}>
        <div className="grid gap-4 md:grid-cols-5">
          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Fonte</label>
            <select value={filters.source} onChange={(e) => setFilter("source", e.target.value)} className="w-full rounded-lg border border-slate-800 bg-slate-950/80 px-3 py-2 text-sm text-slate-300 outline-none focus:border-indigo-500"><option value="Todos">Todas</option><option value="youtube">YouTube</option><option value="google_news">Google News</option></select>
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Tipo</label>
            <select value={filters.content_type} onChange={(e) => setFilter("content_type", e.target.value)} className="w-full rounded-lg border border-slate-800 bg-slate-950/80 px-3 py-2 text-sm text-slate-300 outline-none focus:border-indigo-500"><option value="Todos">Todos</option><option value="video">Vídeo</option><option value="article">Artigo</option></select>
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Nicho / semente</label>
            <input value={filters.topic_seed === "Todos" ? "" : filters.topic_seed} onChange={(e) => setFilter("topic_seed", e.target.value || "Todos")} placeholder="Ex: minecraft" className="w-full rounded-lg border border-slate-800 bg-slate-950/80 px-3 py-2 text-sm text-slate-300 outline-none focus:border-indigo-500" />
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Views mínimas</label>
            <input type="number" min="0" value={filters.min_views || ""} onChange={(e) => setFilter("min_views", e.target.value ? parseInt(e.target.value) : 0)} className="w-full rounded-lg border border-slate-800 bg-slate-950/80 px-3 py-2 text-sm text-slate-300 outline-none focus:border-indigo-500" />
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Breakout mínimo</label>
            <div className="relative"><input type="number" min="0" step="0.1" value={filters.min_performance_ratio || ""} onChange={(e) => setFilter("min_performance_ratio", e.target.value ? parseFloat(e.target.value) : 0)} placeholder="2.0" className="w-full rounded-lg border border-slate-800 bg-slate-950/80 px-3 py-2 pr-8 text-sm text-slate-300 outline-none focus:border-indigo-500" /><span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-slate-600">×</span></div>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-[1fr_220px]">
          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Tema detectado</label>
            <DiscoveryAutocomplete selected={selectedTopics} onChange={changeTopic} entityOnly placeholder="Minecraft, Analog Horror, SMP, série..." />
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Confiança mínima · {Math.round(filters.min_topic_confidence * 100)}%</label>
            <input type="range" min="0" max="1" step="0.05" value={filters.min_topic_confidence} onChange={(e) => setFilter("min_topic_confidence", Number(e.target.value))} className="mt-3 w-full" disabled={!filters.topic_id} />
          </div>
        </div>
      </div>
    </div>
  );
}
