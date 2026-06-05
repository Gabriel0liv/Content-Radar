"use client";

import { useState, useEffect } from "react";
import { ContentItem, ContentStatus } from "@/lib/types";
import { updateContentItemCuration } from "@/lib/api";
import { ContentStatusBadge } from "./content-status-badge";
import { formatDate, formatViews, formatScore } from "@/lib/format";
import {
  X,
  Save,
  Loader2,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  FileCode,
  Youtube,
  Globe,
  CheckCircle,
  FileText
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

interface CurationPanelProps {
  item: ContentItem | null;
  onClose: () => void;
  onUpdateSuccess: (updatedItem: ContentItem) => void;
}

export function CurationPanel({ item, onClose, onUpdateSuccess }: CurationPanelProps) {
  const [status, setStatus] = useState<ContentStatus>("new");
  const [notes, setNotes] = useState("");
  const [productionNotes, setProductionNotes] = useState("");
  const [rejectedReason, setRejectedReason] = useState("");
  
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showRawJson, setShowRawJson] = useState(false);

  // Sync state with selected item
  useEffect(() => {
    if (item) {
      setStatus(item.status);
      setNotes(item.notes || "");
      setProductionNotes(item.production_notes || "");
      setRejectedReason(item.rejected_reason || "");
      setShowRawJson(false); // Reset JSON toggle
    }
  }, [item]);

  if (!item) return null;

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      const payload = {
        status,
        notes: notes.trim() || null,
        production_notes: productionNotes.trim() || null,
        rejected_reason: status === "rejected" ? rejectedReason.trim() || null : null,
      };

      const updated = await updateContentItemCuration(item.id, payload);
      toast.success("Conteúdo atualizado com sucesso!", {
        description: `Status alterado para "${status.toUpperCase()}"`,
      });
      onUpdateSuccess(updated);
    } catch (error: any) {
      toast.error("Erro ao atualizar o conteúdo", {
        description: error.message || "Erro desconhecido",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const isYoutube = item.source.toLowerCase() === "youtube";

  return (
    <div className="flex h-full flex-col border-l border-slate-800 bg-[#090d16] text-slate-200 shadow-2xl">
      {/* Panel Header */}
      <div className="flex h-16 items-center justify-between border-b border-slate-800 px-6 bg-[#0b101c]">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-white">Curadoria Editorial</span>
          <span className="text-xs text-slate-500 font-mono">ID: {item.id}</span>
        </div>
        <button
          onClick={onClose}
          className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-slate-200 transition-colors"
          aria-label="Fechar painel"
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      {/* Panel Scrollable Content */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* Read-Only Info Block */}
        <div className="space-y-4 rounded-xl border border-slate-800/80 bg-slate-950/40 p-4">
          <div className="flex items-start justify-between gap-3">
            <h3 className="font-bold text-white leading-snug line-clamp-3 select-text">{item.title}</h3>
            <a
              href={item.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-slate-800 bg-slate-950/60 text-slate-400 hover:border-indigo-500/30 hover:bg-indigo-600/10 hover:text-indigo-400 transition-all"
              title="Abrir conteúdo no navegador"
            >
              <ExternalLink className="h-4 w-4" />
            </a>
          </div>

          <div className="grid grid-cols-2 gap-3.5 pt-2 text-xs">
            <div className="flex flex-col gap-1 border-r border-slate-800/60 pr-2">
              <span className="text-[10px] uppercase font-bold tracking-wider text-slate-500">Canal / Autor</span>
              <span className="font-semibold text-slate-300 truncate">{item.channel_title || "-"}</span>
            </div>
            <div className="flex flex-col gap-1 pl-1">
              <span className="text-[10px] uppercase font-bold tracking-wider text-slate-500">Publicado Em</span>
              <span className="font-semibold text-slate-300 truncate">{formatDate(item.published_at)}</span>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-2 pt-2 border-t border-slate-800/40 text-center">
            <div className="rounded-lg bg-slate-900/40 py-2 border border-slate-900/80">
              <span className="block text-[9px] uppercase font-bold text-slate-500">Score</span>
              <span className="text-sm font-bold text-indigo-400 mt-0.5 block">{formatScore(item.score)}</span>
            </div>
            <div className="rounded-lg bg-slate-900/40 py-2 border border-slate-900/80">
              <span className="block text-[9px] uppercase font-bold text-slate-500">Views</span>
              <span className="text-sm font-bold text-white mt-0.5 block">{formatViews(item.views)}</span>
            </div>
            <div className="rounded-lg bg-slate-900/40 py-2 border border-slate-900/80">
              <span className="block text-[9px] uppercase font-bold text-slate-500">Views / Dia</span>
              <span className="text-sm font-bold text-slate-400 mt-0.5 block">
                {item.views_per_day ? `+${formatViews(item.views_per_day)}` : "-"}
              </span>
            </div>
          </div>
        </div>

        {/* Curation Form */}
        <form onSubmit={handleSave} className="space-y-5">
          {/* Status Dropdown */}
          <div className="space-y-2">
            <label htmlFor="curation-status" className="text-xs font-bold uppercase tracking-wider text-slate-400">
              Alterar Status
            </label>
            <select
              id="curation-status"
              value={status}
              onChange={(e) => setStatus(e.target.value as ContentStatus)}
              className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3.5 py-2.5 text-sm text-slate-200 outline-none ring-offset-slate-950 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 transition-all font-semibold"
            >
              <option value="new">Novo</option>
              <option value="reviewed">Revisado (Aprovado na triagem)</option>
              <option value="selected">Selecionado (Pronto para Roteiro)</option>
              <option value="rejected">Rejeitado</option>
              <option value="produced">Produzido</option>
              <option value="archived">Arquivado</option>
            </select>
          </div>

          {/* Rejected Reason - Only if status is rejected */}
          {status === "rejected" && (
            <div className="space-y-2 animate-fadeIn">
              <label htmlFor="rejected-reason" className="text-xs font-bold uppercase tracking-wider text-rose-400">
                Motivo da Rejeição
              </label>
              <input
                id="rejected-reason"
                type="text"
                value={rejectedReason}
                onChange={(e) => setRejectedReason(e.target.value)}
                placeholder="Ex: Tópico saturado, fora do escopo..."
                className="w-full rounded-lg border border-rose-950 bg-slate-950 px-3.5 py-2.5 text-sm text-slate-200 placeholder-slate-600 outline-none focus:border-rose-500 focus:ring-2 focus:ring-rose-500/10 transition-all"
                required
              />
            </div>
          )}

          {/* Production Notes - Only for selected/produced */}
          {(status === "selected" || status === "produced") && (
            <div className="space-y-2 animate-fadeIn">
              <label htmlFor="production-notes" className="text-xs font-bold uppercase tracking-wider text-emerald-400">
                Notas de Produção / Roteiro
              </label>
              <textarea
                id="production-notes"
                rows={3}
                value={productionNotes}
                onChange={(e) => setProductionNotes(e.target.value)}
                placeholder="Diretrizes para o roteiro, referências a abordar..."
                className="w-full rounded-lg border border-emerald-950 bg-slate-950 px-3.5 py-2.5 text-sm text-slate-200 placeholder-slate-600 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/10 transition-all resize-none"
              />
            </div>
          )}

          {/* General Curatorial Notes */}
          <div className="space-y-2">
            <label htmlFor="curation-notes" className="text-xs font-bold uppercase tracking-wider text-slate-400">
              Observações / Notas do Curador
            </label>
            <textarea
              id="curation-notes"
              rows={4}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="O que achou deste conteúdo? Adicione insights ou observações gerais..."
              className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3.5 py-2.5 text-sm text-slate-200 placeholder-slate-600 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 transition-all resize-none"
            />
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={isSubmitting}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-3 text-sm font-semibold text-white shadow-md shadow-indigo-600/15 hover:bg-indigo-500 active:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="h-4.5 w-4.5 animate-spin" />
                <span>Salvando...</span>
              </>
            ) : (
              <>
                <Save className="h-4.5 w-4.5" />
                <span>Salvar Alterações</span>
              </>
            )}
          </button>
        </form>

        {/* Collapsible Raw JSON Viewer */}
        <div className="border-t border-slate-800/80 pt-6">
          <button
            type="button"
            onClick={() => setShowRawJson(!showRawJson)}
            className="flex w-full items-center justify-between rounded-lg border border-slate-800 bg-slate-950/20 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-400 hover:bg-slate-950/40 hover:text-slate-200 transition-colors"
          >
            <span className="flex items-center gap-2">
              <FileCode className="h-4 w-4 text-slate-500" />
              Metadados Brutos (JSON)
            </span>
            {showRawJson ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </button>

          {showRawJson && (
            <div className="mt-3 overflow-x-auto rounded-lg border border-slate-900 bg-slate-950/90 p-4 font-mono text-[11px] text-slate-400 leading-relaxed max-h-[300px] select-text">
              {item.raw_json ? (
                <pre>{JSON.stringify(item.raw_json, null, 2)}</pre>
              ) : (
                <span className="text-slate-600 italic">Nenhum metadado bruto disponível.</span>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
