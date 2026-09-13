"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { FileText, Lightbulb, Loader2, Radar, Search, Video } from "lucide-react";

import { globalSearch } from "@/lib/api";
import type { GlobalSearchResponse } from "@/lib/types";

export function GlobalSearch() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<GlobalSearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const value = query.trim();
    if (value.length < 2) {
      setResult(null);
      setOpen(false);
      return;
    }
    const timer = setTimeout(async () => {
      try {
        setLoading(true);
        const data = await globalSearch(value, 5);
        setResult(data);
        setOpen(true);
      } catch {
        setResult(null);
      } finally {
        setLoading(false);
      }
    }, 250);
    return () => clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    const onMouseDown = (event: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onMouseDown);
    return () => document.removeEventListener("mousedown", onMouseDown);
  }, []);

  const hasResults = result && (
    result.content_items.length || result.references.length || result.transcript_matches.length || result.ideas.length
  );

  return (
    <div ref={rootRef} className="relative w-full max-w-xl">
      <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
      <input
        value={query}
        onFocus={() => result && setOpen(true)}
        onChange={(event) => setQuery(event.target.value)}
        placeholder="Buscar no Radar, Biblioteca, transcrições e Ideias..."
        className="h-9 w-full rounded-lg border border-slate-800 bg-slate-950/80 pl-9 pr-9 text-sm text-slate-200 outline-none placeholder:text-slate-600 focus:border-indigo-500"
      />
      {loading && <Loader2 className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 animate-spin text-indigo-400" />}

      {open && (
        <div className="absolute left-0 right-0 top-11 z-50 max-h-[70vh] overflow-y-auto rounded-xl border border-slate-800 bg-[#090d16] p-2 shadow-2xl">
          {!hasResults ? (
            <div className="px-3 py-6 text-center text-sm text-slate-500">Nenhum resultado.</div>
          ) : (
            <div className="space-y-3">
              {result!.content_items.length > 0 && (
                <ResultGroup title="Radar" icon={Radar}>
                  {result!.content_items.map((item) => (
                    <Link key={item.id} href={`/content/${item.id}`} onClick={() => setOpen(false)} className="block rounded-lg px-3 py-2 hover:bg-slate-800/70">
                      <div className="truncate text-sm font-semibold text-slate-200">{item.title}</div>
                      <div className="mt-0.5 text-xs text-slate-500">{item.channel_title || item.source}{item.performance_ratio ? ` · ${item.performance_ratio.toFixed(1)}x` : ""}</div>
                    </Link>
                  ))}
                </ResultGroup>
              )}

              {result!.references.length > 0 && (
                <ResultGroup title="Biblioteca" icon={Video}>
                  {result!.references.map((item) => (
                    <Link key={item.id} href={`/references/${item.id}`} onClick={() => setOpen(false)} className="block rounded-lg px-3 py-2 hover:bg-slate-800/70">
                      <div className="truncate text-sm font-semibold text-slate-200">{item.title}</div>
                      <div className="mt-0.5 text-xs text-slate-500">{item.channel_title || "Referência"}</div>
                    </Link>
                  ))}
                </ResultGroup>
              )}

              {result!.transcript_matches.length > 0 && (
                <ResultGroup title="Transcrições" icon={FileText}>
                  {result!.transcript_matches.map((item) => (
                    <Link key={item.segment_id} href={`/references/${item.reference_source_id}?segment=${item.segment_id}`} onClick={() => setOpen(false)} className="block rounded-lg px-3 py-2 hover:bg-slate-800/70">
                      <div className="truncate text-sm font-semibold text-slate-200">{item.video_title}</div>
                      <div className="mt-1 line-clamp-2 text-xs leading-relaxed text-slate-400">{item.matched_excerpt}</div>
                      <div className="mt-1 text-[11px] text-indigo-400">{formatTimestamp(item.start_time)}</div>
                    </Link>
                  ))}
                </ResultGroup>
              )}

              {result!.ideas.length > 0 && (
                <ResultGroup title="Ideias" icon={Lightbulb}>
                  {result!.ideas.map((item) => (
                    <Link key={item.id} href="/ideas" onClick={() => setOpen(false)} className="block rounded-lg px-3 py-2 hover:bg-slate-800/70">
                      <div className="truncate text-sm font-semibold text-slate-200">{item.title}</div>
                      <div className="mt-0.5 text-xs text-slate-500">{item.niche || item.status}</div>
                    </Link>
                  ))}
                </ResultGroup>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ResultGroup({ title, icon: Icon, children }: { title: string; icon: typeof Search; children: React.ReactNode }) {
  return (
    <section>
      <div className="flex items-center gap-2 px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-500">
        <Icon className="h-3.5 w-3.5" /> {title}
      </div>
      {children}
    </section>
  );
}

function formatTimestamp(seconds: number | null): string {
  if (seconds === null) return "Sem timestamp";
  const total = Math.max(0, Math.floor(seconds));
  const minutes = Math.floor(total / 60);
  const remaining = total % 60;
  return `${minutes}:${remaining.toString().padStart(2, "0")}`;
}
