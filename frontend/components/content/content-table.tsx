"use client";

import { ContentItem } from "@/lib/types";
import { formatViews, formatDate, formatRelativeTime, formatScore } from "@/lib/format";
import { ContentStatusBadge } from "./content-status-badge";
import {
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  TrendingUp,
  Eye,
  Video,
  FileText,
  Clock,
  ExternalLink as LinkIcon
} from "lucide-react";
import { cn } from "@/lib/utils";

interface ContentTableProps {
  items: ContentItem[];
  total: number;
  loading: boolean;
  filters: {
    limit: number;
    offset: number;
  };
  setFilter: (key: string, value: any) => void;
  onSelect: (item: ContentItem) => void;
  selectedId?: number | null;
}

export function ContentTable({
  items,
  total,
  loading,
  filters,
  setFilter,
  onSelect,
  selectedId
}: ContentTableProps) {
  const currentPage = Math.floor(filters.offset / filters.limit) + 1;
  const totalPages = Math.ceil(total / filters.limit) || 1;

  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= totalPages) {
      setFilter("offset", (newPage - 1) * filters.limit);
    }
  };

  const handleLimitChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newLimit = parseInt(e.target.value);
    setFilter("limit", newLimit);
    setFilter("offset", 0);
  };

  // Render score meter helper
  const getScoreColor = (score: number | null | undefined) => {
    if (!score) return "text-slate-500 bg-slate-500/10 border-slate-500/20";
    if (score >= 70) return "text-emerald-400 bg-emerald-500/10 border-emerald-500/20";
    if (score >= 40) return "text-amber-400 bg-amber-500/10 border-amber-500/20";
    return "text-indigo-400 bg-indigo-500/10 border-indigo-500/20";
  };

  return (
    <div className="rounded-xl border border-slate-800/80 bg-[#0b101c]/25 backdrop-blur-sm overflow-hidden flex flex-col">
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-left text-sm text-slate-300">
          <thead className="border-b border-slate-800 bg-[#0c1223]/60 text-xs font-bold uppercase tracking-wider text-slate-400">
            <tr>
              <th className="px-6 py-4">Conteúdo</th>
              <th className="px-6 py-4 w-32">Origem</th>
              <th className="px-6 py-4 text-right w-28">Score</th>
              <th className="px-6 py-4 text-right w-28">Views</th>
              <th className="px-6 py-4 text-right w-32">Views / Dia</th>
              <th className="px-6 py-4 w-36">Publicado</th>
              <th className="px-6 py-4 w-32">Status</th>
              <th className="px-6 py-4 text-center w-24">Ações</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {loading ? (
              // Loading skeletons
              Array.from({ length: 8 }).map((_, idx) => (
                <tr key={idx} className="animate-pulse">
                  <td className="px-6 py-4">
                    <div className="h-4 w-3/4 rounded bg-slate-800/60 mb-2"></div>
                    <div className="h-3 w-1/2 rounded bg-slate-800/30"></div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="h-5 w-20 rounded bg-slate-800/60"></div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="h-6 w-12 rounded bg-slate-800/60 ml-auto"></div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="h-4 w-16 rounded bg-slate-800/60 ml-auto"></div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="h-4 w-16 rounded bg-slate-800/60 ml-auto"></div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="h-4 w-24 rounded bg-slate-800/60"></div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="h-5 w-20 rounded bg-slate-800/60"></div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="h-8 w-12 rounded bg-slate-800/60 mx-auto"></div>
                  </td>
                </tr>
              ))
            ) : items.length === 0 ? (
              <tr>
                <td colSpan={8} className="px-6 py-16 text-center text-slate-500 font-medium">
                  Nenhum conteúdo encontrado com os filtros selecionados.
                </td>
              </tr>
            ) : (
              items.map((item) => {
                const isSelected = selectedId === item.id;
                const isYoutube = item.source.toLowerCase() === "youtube";

                return (
                  <tr
                    key={item.id}
                    onClick={() => onSelect(item)}
                    className={cn(
                      "group cursor-pointer border-l-2 border-l-transparent transition-all duration-150",
                      isSelected
                        ? "border-l-indigo-500 bg-indigo-500/5 text-white"
                        : "hover:bg-slate-900/40 text-slate-300 hover:text-slate-100"
                    )}
                  >
                    {/* Content / Title */}
                    <td className="px-6 py-4">
                      <div className="flex flex-col gap-1 max-w-md md:max-w-lg lg:max-w-xl">
                        <span className="font-semibold text-slate-200 group-hover:text-white line-clamp-2 leading-tight">
                          {item.title}
                        </span>
                        <div className="flex items-center gap-2 text-xs text-slate-500 font-medium">
                          {item.channel_title && (
                            <span className="text-slate-400 font-medium truncate max-w-[150px]">
                              {item.channel_title}
                            </span>
                          )}
                          {item.topic_seed && (
                            <>
                              <span className="text-slate-700">•</span>
                              <span className="rounded bg-slate-950/80 px-1.5 py-0.5 text-[10px] text-indigo-400/90 border border-slate-800/60">
                                {item.topic_seed}
                              </span>
                            </>
                          )}
                        </div>
                      </div>
                    </td>

                    {/* Source / Type */}
                    <td className="px-6 py-4">
                      <div className="flex flex-col gap-1.5 justify-center">
                        <span
                          className={cn(
                            "inline-flex items-center gap-1.5 text-xs font-semibold px-2 py-0.5 rounded border w-fit",
                            isYoutube
                              ? "bg-rose-500/10 text-rose-400 border-rose-500/20"
                              : "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                          )}
                        >
                          <span
                            className={cn(
                              "h-1.5 w-1.5 rounded-full",
                              isYoutube ? "bg-rose-500" : "bg-emerald-500"
                            )}
                          ></span>
                          {isYoutube ? "YouTube" : "Google News"}
                        </span>
                        <span className="inline-flex items-center gap-1 text-[11px] text-slate-400 font-medium ml-1">
                          {item.content_type === "video" ? (
                            <Video className="h-3 w-3 text-slate-500" />
                          ) : (
                            <FileText className="h-3 w-3 text-slate-500" />
                          )}
                          {item.content_type === "video" ? "Vídeo" : "Artigo"}
                        </span>
                      </div>
                    </td>

                    {/* Score */}
                    <td className="px-6 py-4 text-right font-mono font-bold">
                      <span className={cn("inline-block rounded px-2 py-0.5 border text-xs shadow-sm", getScoreColor(item.score))}>
                        {formatScore(item.score)}
                      </span>
                    </td>

                    {/* Views */}
                    <td className="px-6 py-4 text-right font-mono text-slate-200 font-semibold">
                      {formatViews(item.views)}
                    </td>

                    {/* Views per Day */}
                    <td className="px-6 py-4 text-right font-mono text-slate-400 font-semibold">
                      {item.views_per_day ? `+${formatViews(item.views_per_day)}` : "-"}
                    </td>

                    {/* Published */}
                    <td className="px-6 py-4 text-slate-400 font-medium">
                      <div className="flex flex-col justify-center">
                        <span className="text-slate-300 font-medium">{formatRelativeTime(item.published_at)}</span>
                        <span className="text-[10px] text-slate-500 font-mono mt-0.5">
                          {formatDate(item.published_at)?.split(" ")[0]}
                        </span>
                      </div>
                    </td>

                    {/* Status */}
                    <td className="px-6 py-4">
                      <ContentStatusBadge status={item.status} />
                    </td>

                    {/* Actions */}
                    <td className="px-6 py-4 text-center">
                      <div className="flex items-center justify-center gap-2">
                        <a
                          href={item.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          className="flex h-8 w-8 items-center justify-center rounded-lg border border-slate-800 bg-slate-950/40 text-slate-400 hover:border-indigo-500/30 hover:bg-indigo-600/10 hover:text-indigo-400 transition-colors"
                          title="Abrir link original"
                        >
                          <ExternalLink className="h-3.5 w-3.5" />
                        </a>
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Controls */}
      {total > 0 && (
        <div className="flex flex-col gap-4 border-t border-slate-800/80 bg-[#0b101c]/50 px-6 py-4 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-4 text-xs text-slate-400 font-medium">
            <span>
              Mostrando <strong className="text-slate-200">{filters.offset + 1}</strong> a{" "}
              <strong className="text-slate-200">
                {Math.min(filters.offset + filters.limit, total)}
              </strong>{" "}
              de <strong className="text-slate-200">{total}</strong> itens
            </span>
            <div className="flex items-center gap-1.5">
              <span>Itens por página:</span>
              <select
                value={filters.limit}
                onChange={handleLimitChange}
                className="rounded border border-slate-800 bg-slate-950 px-2 py-1 text-xs text-slate-300 outline-none focus:border-indigo-500"
              >
                <option value={10}>10</option>
                <option value={25}>25</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
              </select>
            </div>
          </div>

          <div className="flex items-center gap-2 self-end md:self-auto">
            <button
              onClick={() => handlePageChange(currentPage - 1)}
              disabled={currentPage === 1 || loading}
              className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-800 bg-slate-950/40 text-slate-400 hover:bg-slate-900 hover:text-slate-200 disabled:opacity-30 disabled:hover:bg-transparent disabled:hover:text-slate-400 transition-colors"
              title="Página Anterior"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <span className="text-xs text-slate-400 px-2 font-medium">
              Pág <strong className="text-slate-200">{currentPage}</strong> de{" "}
              <strong className="text-slate-200">{totalPages}</strong>
            </span>
            <button
              onClick={() => handlePageChange(currentPage + 1)}
              disabled={currentPage === totalPages || loading}
              className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-800 bg-slate-950/40 text-slate-400 hover:bg-slate-900 hover:text-slate-200 disabled:opacity-30 disabled:hover:bg-transparent disabled:hover:text-slate-400 transition-colors"
              title="Próxima Página"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
