"use client";

import { ChevronLeft, ChevronRight, ExternalLink, FileText, Video } from "lucide-react";

import type { ContentItem } from "@/lib/types";
import { formatDate, formatRelativeTime, formatScore, formatViews } from "@/lib/format";
import { cn } from "@/lib/utils";
import { ContentStatusBadge } from "./content-status-badge";

interface ContentTableProps {
  items: ContentItem[];
  total: number;
  loading: boolean;
  filters: { limit: number; offset: number };
  setFilter: (key: any, value: any) => void;
  onSelect: (item: ContentItem) => void;
  selectedId?: number | null;
}

function breakoutLabel(item: ContentItem): { label: string; detail: string; className: string } {
  const samples = item.performance_baseline_samples || 0;
  if (item.performance_ratio === null || samples < 2) {
    return { label: "—", detail: "Histórico insuficiente", className: "text-slate-500 border-slate-800 bg-slate-900/30" };
  }
  const ratio = item.performance_ratio;
  const confidence = samples >= 5 ? `${samples} vídeos` : `estimativa · ${samples} vídeos`;
  if (ratio >= 7) return { label: `${ratio.toFixed(1)}×`, detail: confidence, className: "text-fuchsia-300 border-fuchsia-500/25 bg-fuchsia-500/10" };
  if (ratio >= 3) return { label: `${ratio.toFixed(1)}×`, detail: confidence, className: "text-emerald-300 border-emerald-500/25 bg-emerald-500/10" };
  if (ratio >= 1.5) return { label: `${ratio.toFixed(1)}×`, detail: confidence, className: "text-amber-300 border-amber-500/25 bg-amber-500/10" };
  return { label: `${ratio.toFixed(1)}×`, detail: confidence, className: "text-slate-300 border-slate-700 bg-slate-900/50" };
}

export function ContentTable({ items, total, loading, filters, setFilter, onSelect, selectedId }: ContentTableProps) {
  const currentPage = Math.floor(filters.offset / filters.limit) + 1;
  const totalPages = Math.ceil(total / filters.limit) || 1;

  return (
    <div className="flex flex-col overflow-hidden rounded-xl border border-slate-800/80 bg-[#0b101c]/25 backdrop-blur-sm">
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-left text-sm text-slate-300">
          <thead className="border-b border-slate-800 bg-[#0c1223]/60 text-[10px] font-bold uppercase tracking-wider text-slate-400">
            <tr>
              <th className="px-5 py-3">Conteúdo</th>
              <th className="px-5 py-3">Origem</th>
              <th className="px-5 py-3 text-right">Views</th>
              <th className="px-5 py-3 text-right">Views / dia</th>
              <th className="px-5 py-3 text-center">Breakout</th>
              <th className="px-5 py-3 text-right">Score</th>
              <th className="px-5 py-3">Publicado</th>
              <th className="px-5 py-3">Status</th>
              <th className="px-5 py-3 text-center">Link</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {loading ? (
              Array.from({ length: 6 }).map((_, index) => (
                <tr key={index} className="animate-pulse"><td colSpan={9} className="px-5 py-5"><div className="h-5 rounded bg-slate-800/50" /></td></tr>
              ))
            ) : items.length === 0 ? (
              <tr><td colSpan={9} className="px-5 py-16 text-center text-slate-500">Nenhum conteúdo encontrado.</td></tr>
            ) : items.map((item) => {
              const breakout = breakoutLabel(item);
              const isYoutube = item.source.toLowerCase() === "youtube";
              return (
                <tr key={item.id} onClick={() => onSelect(item)} className={cn("cursor-pointer border-l-2 border-l-transparent transition-colors hover:bg-slate-900/40", selectedId === item.id && "border-l-indigo-500 bg-indigo-500/5")}>
                  <td className="max-w-md px-5 py-4">
                    <div className="line-clamp-2 font-semibold leading-tight text-slate-200">{item.title}</div>
                    <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-500">
                      {item.channel_title && <span>{item.channel_title}</span>}
                      {item.youtube_category_name && <span className="rounded border border-slate-800 bg-slate-950 px-1.5 py-0.5 text-[10px] text-slate-400">YouTube: {item.youtube_category_name}</span>}
                    </div>
                    {item.detected_topics?.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1.5">
                        {item.detected_topics.slice(0, 4).map((topic) => (
                          <span key={`${topic.id}-${topic.type}`} className="rounded-full border border-indigo-500/20 bg-indigo-500/10 px-2 py-0.5 text-[10px] font-medium text-indigo-300" title={`${Math.round(topic.confidence * 100)}% · ${topic.source}`}>
                            {topic.name} <span className="text-indigo-500">{Math.round(topic.confidence * 100)}%</span>
                          </span>
                        ))}
                      </div>
                    )}
                  </td>
                  <td className="px-5 py-4">
                    <span className={cn("inline-flex items-center gap-1.5 rounded border px-2 py-1 text-xs", isYoutube ? "border-rose-500/20 bg-rose-500/10 text-rose-400" : "border-emerald-500/20 bg-emerald-500/10 text-emerald-400")}>
                      {item.content_type === "video" ? <Video className="h-3 w-3" /> : <FileText className="h-3 w-3" />}{isYoutube ? "YouTube" : item.source}
                    </span>
                  </td>
                  <td className="px-5 py-4 text-right font-mono font-semibold text-slate-200">{formatViews(item.views)}</td>
                  <td className="px-5 py-4 text-right font-mono text-slate-400">{item.views_per_day ? `+${formatViews(item.views_per_day)}` : "—"}</td>
                  <td className="px-5 py-4 text-center">
                    <div className={cn("inline-flex min-w-16 flex-col rounded-lg border px-2 py-1", breakout.className)} title={breakout.detail}>
                      <strong className="font-mono text-sm">{breakout.label}</strong>
                      {item.performance_baseline_samples >= 2 && <span className="text-[9px] opacity-70">n={item.performance_baseline_samples}</span>}
                    </div>
                  </td>
                  <td className="px-5 py-4 text-right font-mono text-xs text-slate-400">{formatScore(item.score)}</td>
                  <td className="px-5 py-4 text-xs text-slate-400"><div>{formatRelativeTime(item.published_at)}</div><div className="mt-0.5 text-[10px] text-slate-600">{formatDate(item.published_at)}</div></td>
                  <td className="px-5 py-4"><ContentStatusBadge status={item.status} /></td>
                  <td className="px-5 py-4 text-center"><a href={item.url} target="_blank" rel="noopener noreferrer" onClick={(event) => event.stopPropagation()} className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-slate-800 bg-slate-950 text-slate-400 hover:text-indigo-400"><ExternalLink className="h-3.5 w-3.5" /></a></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {total > 0 && (
        <div className="flex items-center justify-between border-t border-slate-800 px-5 py-4 text-xs text-slate-400">
          <span>{filters.offset + 1}–{Math.min(filters.offset + filters.limit, total)} de {total}</span>
          <div className="flex items-center gap-2">
            <button onClick={() => setFilter("offset", Math.max(0, filters.offset - filters.limit))} disabled={currentPage <= 1 || loading} className="rounded border border-slate-800 p-2 disabled:opacity-30"><ChevronLeft className="h-4 w-4" /></button>
            <span>{currentPage} / {totalPages}</span>
            <button onClick={() => setFilter("offset", filters.offset + filters.limit)} disabled={currentPage >= totalPages || loading} className="rounded border border-slate-800 p-2 disabled:opacity-30"><ChevronRight className="h-4 w-4" /></button>
          </div>
        </div>
      )}
    </div>
  );
}
