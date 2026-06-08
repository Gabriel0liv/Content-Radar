"use client";

import { useState } from "react";
import { Search, SlidersHorizontal, RotateCcw, ArrowUpDown } from "lucide-react";
import { cn } from "@/lib/utils";

interface FiltersProps {
  filters: {
    search: string;
    source: string;
    content_type: string;
    status: string;
    topic_seed: string;
    min_score: number;
    min_views: number;
    sort_by: string;
    sort_order: string;
  };
  setFilter: (key: any, value: any) => void;
  resetFilters: () => void;
}

export function ContentFilters({ filters, setFilter, resetFilters }: FiltersProps) {
  const [showAdvanced, setShowAdvanced] = useState(false);

  return (
    <div className="rounded-xl border border-slate-800/80 bg-[#0b101c]/30 p-5 backdrop-blur-sm space-y-4">
      {/* Primary Row: Search and Quick Controls */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center">
        {/* Search Input */}
        <div className="relative flex-1">
          <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            placeholder="Pesquisar por título ou descrição..."
            value={filters.search}
            onChange={(e) => setFilter("search", e.target.value)}
            className="w-full rounded-lg border border-slate-800 bg-slate-950/80 py-2.5 pl-10 pr-4 text-sm text-slate-200 placeholder-slate-500 outline-none ring-offset-slate-950 transition-all focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20"
            aria-label="Pesquisar conteúdos"
          />
        </div>

        {/* Status Filter */}
        <div className="w-full md:w-48">
          <select
            value={filters.status}
            onChange={(e) => setFilter("status", e.target.value)}
            className="w-full rounded-lg border border-slate-800 bg-slate-950/80 px-3 py-2.5 text-sm text-slate-300 outline-none transition-all focus:border-indigo-500"
            aria-label="Filtrar por Status"
          >
            <option value="Todos">Status: Todos</option>
            <option value="new">Novo</option>
            <option value="reviewed">Revisado</option>
            <option value="selected">Selecionado</option>
            <option value="rejected">Rejeitado</option>
            <option value="produced">Produzido</option>
            <option value="archived">Arquivado</option>
          </select>
        </div>

        {/* Sort By Filter */}
        <div className="w-full md:w-56">
          <select
            value={filters.sort_by}
            onChange={(e) => setFilter("sort_by", e.target.value)}
            className="w-full rounded-lg border border-slate-800 bg-slate-950/80 px-3 py-2.5 text-sm text-slate-300 outline-none transition-all focus:border-indigo-500"
            aria-label="Ordenar por"
          >
            <option value="score">Ordenar por: Score Oportunidade</option>
            <option value="views">Ordenar por: Total Views</option>
            <option value="views_per_day">Ordenar por: Views/Dia</option>
            <option value="published_at">Ordenar por: Data Publicação</option>
            <option value="collected_at">Ordenar por: Data Coleta</option>
            <option value="last_seen_at">Ordenar por: Última Atualização</option>
          </select>
        </div>

        {/* Sort Order Toggle */}
        <button
          onClick={() => setFilter("sort_order", filters.sort_order === "asc" ? "desc" : "asc")}
          className="flex h-10 w-10 items-center justify-center rounded-lg border border-slate-800 bg-slate-950/50 hover:bg-slate-900 transition-colors text-slate-400 hover:text-slate-200"
          title={filters.sort_order === "asc" ? "Ordem Crescente" : "Ordem Decrescente"}
          aria-label="Alternar direção de ordenação"
        >
          <ArrowUpDown className={cn("h-4 w-4 transition-transform", filters.sort_order === "asc" && "rotate-180")} />
        </button>

        {/* Advanced Filters Button */}
        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          className={cn(
            "flex items-center gap-2 rounded-lg border px-4 py-2.5 text-sm font-medium transition-colors md:w-auto justify-center",
            showAdvanced
              ? "border-indigo-500/30 bg-indigo-600/10 text-indigo-400"
              : "border-slate-800 bg-slate-950/50 text-slate-400 hover:bg-slate-900 hover:text-slate-200"
          )}
        >
          <SlidersHorizontal className="h-4 w-4" />
          <span>Filtros</span>
        </button>

        {/* Reset Button */}
        <button
          onClick={resetFilters}
          className="flex h-10 w-10 items-center justify-center rounded-lg border border-slate-800 bg-slate-950/30 hover:bg-slate-900 transition-colors text-slate-500 hover:text-slate-300"
          title="Limpar todos os filtros"
          aria-label="Limpar filtros"
        >
          <RotateCcw className="h-4 w-4" />
        </button>
      </div>

      {/* Advanced Row (Collapsible) */}
      <div
        className={cn(
          "grid gap-4 border-t border-slate-800/60 pt-4 md:grid-cols-4 transition-all duration-200 ease-in-out",
          showAdvanced ? "grid" : "hidden"
        )}
      >
        {/* Source Filter */}
        <div className="space-y-1.5">
          <label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Fonte</label>
          <select
            value={filters.source}
            onChange={(e) => setFilter("source", e.target.value)}
            className="w-full rounded-lg border border-slate-800 bg-slate-950/80 px-3 py-2 text-sm text-slate-300 outline-none focus:border-indigo-500"
          >
            <option value="Todos">Todas</option>
            <option value="youtube">YouTube</option>
            <option value="google_news">Google News</option>
          </select>
        </div>

        {/* Content Type Filter */}
        <div className="space-y-1.5">
          <label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Tipo de Conteúdo</label>
          <select
            value={filters.content_type}
            onChange={(e) => setFilter("content_type", e.target.value)}
            className="w-full rounded-lg border border-slate-800 bg-slate-950/80 px-3 py-2 text-sm text-slate-300 outline-none focus:border-indigo-500"
          >
            <option value="Todos">Todos</option>
            <option value="video">Vídeo</option>
            <option value="article">Artigo</option>
          </select>
        </div>

        {/* Topic Seed Filter */}
        <div className="space-y-1.5">
          <label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Nicho / Semente</label>
          <input
            type="text"
            placeholder="Ex: astronomia, ia..."
            value={filters.topic_seed === "Todos" ? "" : filters.topic_seed}
            onChange={(e) => setFilter("topic_seed", e.target.value || "Todos")}
            className="w-full rounded-lg border border-slate-800 bg-slate-950/80 px-3 py-2 text-sm text-slate-300 placeholder-slate-600 outline-none focus:border-indigo-500"
          />
        </div>

        {/* Min Score & Views Inputs */}
        <div className="grid grid-cols-2 gap-2">
          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Score Mínimo</label>
            <input
              type="number"
              min="0"
              max="100"
              placeholder="0"
              value={filters.min_score || ""}
              onChange={(e) => setFilter("min_score", e.target.value ? parseFloat(e.target.value) : 0)}
              className="w-full rounded-lg border border-slate-800 bg-slate-950/80 px-3 py-2 text-sm text-slate-300 outline-none focus:border-indigo-500"
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-500">Views Mínimas</label>
            <input
              type="number"
              min="0"
              placeholder="0"
              value={filters.min_views || ""}
              onChange={(e) => setFilter("min_views", e.target.value ? parseInt(e.target.value) : 0)}
              className="w-full rounded-lg border border-slate-800 bg-slate-950/80 px-3 py-2 text-sm text-slate-300 outline-none focus:border-indigo-500"
            />
          </div>
        </div>
      </div>
    </div>
  );
}
