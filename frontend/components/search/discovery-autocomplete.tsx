"use client";

import { useEffect, useRef, useState } from "react";
import { Loader2, Search, X } from "lucide-react";

import { getDiscoveryTerms } from "@/lib/api";
import type { DiscoveryTerm } from "@/lib/types";

interface DiscoveryAutocompleteProps {
  selected: DiscoveryTerm[];
  onChange: (terms: DiscoveryTerm[]) => void;
  placeholder?: string;
  entityOnly?: boolean;
}

const typeLabels: Record<string, string> = {
  topic: "Tema",
  subtopic: "Subtema",
  format: "Formato",
  series: "Série",
  tag: "Tag encontrada",
  youtube_category: "Categoria YouTube",
};

export function DiscoveryAutocomplete({ selected, onChange, placeholder = "Buscar tema, série, tag ou categoria...", entityOnly = false }: DiscoveryAutocompleteProps) {
  const [query, setQuery] = useState("");
  const [options, setOptions] = useState<DiscoveryTerm[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const value = query.trim();
    if (value.length < 2) {
      setOptions([]);
      setOpen(false);
      return;
    }
    const timer = setTimeout(async () => {
      try {
        setLoading(true);
        const terms = await getDiscoveryTerms(value, 20);
        setOptions(terms.filter((term) => !entityOnly || term.entity_id !== null));
        setOpen(true);
      } catch {
        setOptions([]);
      } finally {
        setLoading(false);
      }
    }, 220);
    return () => clearTimeout(timer);
  }, [query, entityOnly]);

  useEffect(() => {
    const close = (event: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  const add = (term: DiscoveryTerm) => {
    if (!selected.some((item) => item.type === term.type && item.entity_id === term.entity_id && item.normalized_term === term.normalized_term)) {
      onChange([...selected, term]);
    }
    setQuery("");
    setOpen(false);
  };

  const remove = (index: number) => onChange(selected.filter((_, current) => current !== index));

  return (
    <div ref={rootRef} className="space-y-2">
      {selected.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {selected.map((term, index) => (
            <span key={`${term.type}-${term.entity_id}-${term.normalized_term}`} className="inline-flex items-center gap-1.5 rounded-full border border-indigo-500/25 bg-indigo-500/10 px-2.5 py-1 text-xs text-indigo-300">
              <span className="text-[9px] font-bold uppercase text-indigo-500">{typeLabels[term.type] || term.type}</span>
              {term.display_name}
              <button type="button" onClick={() => remove(index)} className="text-indigo-500 hover:text-white"><X className="h-3 w-3" /></button>
            </span>
          ))}
        </div>
      )}

      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
        <input value={query} onChange={(event) => setQuery(event.target.value)} onFocus={() => options.length > 0 && setOpen(true)} placeholder={placeholder} className="w-full rounded-lg border border-slate-800 bg-slate-950 py-2.5 pl-9 pr-9 text-sm text-slate-200 outline-none focus:border-indigo-500" />
        {loading && <Loader2 className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 animate-spin text-indigo-400" />}

        {open && (
          <div className="absolute z-40 mt-2 max-h-72 w-full overflow-y-auto rounded-xl border border-slate-800 bg-[#090d16] p-1.5 shadow-2xl">
            {options.length === 0 ? (
              <div className="px-3 py-5 text-center text-xs text-slate-500">Nenhuma sugestão.</div>
            ) : options.map((term) => (
              <button key={`${term.type}-${term.entity_id}-${term.normalized_term}`} type="button" onClick={() => add(term)} className="flex w-full items-center justify-between gap-4 rounded-lg px-3 py-2 text-left hover:bg-slate-800/70">
                <div className="min-w-0">
                  <div className="truncate text-sm font-semibold text-slate-200">{term.display_name}</div>
                  <div className="text-[10px] uppercase tracking-wider text-slate-500">{typeLabels[term.type] || term.type}</div>
                </div>
                {(term.video_count > 0 || term.channel_count > 0) && <div className="shrink-0 text-[10px] text-slate-600">{term.video_count} vídeos · {term.channel_count} canais</div>}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
