"use client";

import { useEffect, useState } from "react";
import { ExternalLink, FileCode, Loader2, Save, X } from "lucide-react";
import { toast } from "sonner";

import { ContentItem, ContentStatus } from "@/lib/types";
import { updateContentItemCuration } from "@/lib/api";
import { formatDate, formatScore, formatViews } from "@/lib/format";

interface CurationPanelProps {
  item: ContentItem | null;
  onClose: () => void;
  onUpdateSuccess: (updatedItem: ContentItem) => void;
}

const statusOptions: Array<{ value: ContentStatus; label: string }> = [
  { value: "new", label: "Novo" },
  { value: "reviewed", label: "Revisado" },
  { value: "selected", label: "Salvo / Selecionado" },
  { value: "rejected", label: "Ignorado / Rejeitado" },
  { value: "archived", label: "Arquivado" },
];

export function CurationPanel({ item, onClose, onUpdateSuccess }: CurationPanelProps) {
  const [status, setStatus] = useState<ContentStatus>("new");
  const [notes, setNotes] = useState("");
  const [rejectedReason, setRejectedReason] = useState("");
  const [showRawJson, setShowRawJson] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!item) return;
    setStatus(item.status);
    setNotes(item.notes || "");
    setRejectedReason(item.rejected_reason || "");
    setShowRawJson(false);
  }, [item]);

  if (!item) return null;

  const isLegacyProduced = status === "produced";

  const save = async (event: React.FormEvent) => {
    event.preventDefault();
    setSaving(true);
    try {
      const updated = await updateContentItemCuration(item.id, {
        status,
        notes: notes.trim() || null,
        rejected_reason: status === "rejected" ? rejectedReason.trim() || null : null,
      });
      toast.success("Conteúdo atualizado");
      onUpdateSuccess(updated);
    } catch (error: any) {
      toast.error("Erro ao atualizar conteúdo", { description: error.message || "Erro desconhecido" });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex h-full flex-col border-l border-slate-800 bg-[#090d16] text-slate-200 shadow-2xl">
      <div className="flex h-16 items-center justify-between border-b border-slate-800 bg-[#0b101c] px-6">
        <div>
          <span className="font-semibold text-white">Detalhes do Radar</span>
          <span className="ml-2 text-xs font-mono text-slate-500">ID {item.id}</span>
        </div>
        <button onClick={onClose} className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white" aria-label="Fechar painel">
          <X className="h-5 w-5" />
        </button>
      </div>

      <div className="flex-1 space-y-6 overflow-y-auto p-6">
        <section className="space-y-4 rounded-xl border border-slate-800/80 bg-slate-950/40 p-4">
          <div className="flex items-start justify-between gap-3">
            <h3 className="font-bold leading-snug text-white">{item.title}</h3>
            <a href={item.url} target="_blank" rel="noopener noreferrer" title="Abrir fonte original" className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-slate-800 bg-slate-950 text-slate-400 hover:border-indigo-500/40 hover:text-indigo-400">
              <ExternalLink className="h-4 w-4" />
            </a>
          </div>

          <div className="grid grid-cols-2 gap-3 text-xs text-slate-400">
            <div><span className="block text-[10px] font-bold uppercase tracking-wider text-slate-600">Canal / Autor</span><span className="font-semibold text-slate-300">{item.channel_title || "-"}</span></div>
            <div><span className="block text-[10px] font-bold uppercase tracking-wider text-slate-600">Publicado</span><span className="font-semibold text-slate-300">{formatDate(item.published_at)}</span></div>
          </div>

          <div className="grid grid-cols-3 gap-2 border-t border-slate-800/50 pt-3 text-center">
            <div className="rounded-lg bg-slate-900/40 py-2"><span className="block text-[9px] font-bold uppercase text-slate-600">Score</span><strong className="text-indigo-400">{formatScore(item.score)}</strong></div>
            <div className="rounded-lg bg-slate-900/40 py-2"><span className="block text-[9px] font-bold uppercase text-slate-600">Views</span><strong className="text-white">{formatViews(item.views)}</strong></div>
            <div className="rounded-lg bg-slate-900/40 py-2"><span className="block text-[9px] font-bold uppercase text-slate-600">Views / dia</span><strong className="text-slate-300">{item.views_per_day ? formatViews(item.views_per_day) : "-"}</strong></div>
          </div>
        </section>

        <form onSubmit={save} className="space-y-5">
          <div className="space-y-2">
            <label className="text-xs font-bold uppercase tracking-wider text-slate-400">Status</label>
            <select value={status} onChange={(e) => setStatus(e.target.value as ContentStatus)} className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3.5 py-2.5 text-sm font-semibold text-slate-200 outline-none focus:border-indigo-500">
              {isLegacyProduced && <option value="produced">Legado: Produzido</option>}
              {statusOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
            </select>
          </div>

          {status === "rejected" && (
            <div className="space-y-2">
              <label className="text-xs font-bold uppercase tracking-wider text-rose-400">Motivo</label>
              <input value={rejectedReason} onChange={(e) => setRejectedReason(e.target.value)} placeholder="Ex.: fora do tema, repetido, pouco interessante..." className="w-full rounded-lg border border-rose-950 bg-slate-950 px-3.5 py-2.5 text-sm text-slate-200 outline-none focus:border-rose-500" />
            </div>
          )}

          <div className="space-y-2">
            <label className="text-xs font-bold uppercase tracking-wider text-slate-400">Notas</label>
            <textarea rows={5} value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Por que isso chamou atenção? O que vale lembrar depois?" className="w-full resize-none rounded-lg border border-slate-800 bg-slate-950 px-3.5 py-2.5 text-sm text-slate-200 outline-none focus:border-indigo-500" />
          </div>

          <button disabled={saving} className="flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-3 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-50">
            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
            Salvar
          </button>
        </form>

        <section className="border-t border-slate-800 pt-5">
          <button type="button" onClick={() => setShowRawJson(!showRawJson)} className="flex w-full items-center gap-2 rounded-lg border border-slate-800 bg-slate-950/20 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500 hover:text-slate-300">
            <FileCode className="h-4 w-4" /> Metadados brutos
          </button>
          {showRawJson && <pre className="mt-3 max-h-72 overflow-auto rounded-lg border border-slate-900 bg-slate-950 p-4 text-[11px] text-slate-400">{JSON.stringify(item.raw_json || {}, null, 2)}</pre>}
        </section>
      </div>
    </div>
  );
}
