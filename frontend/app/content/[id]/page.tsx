"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { getContentItem, updateContentItemCuration } from "@/lib/api";
import { ContentItem, ContentStatus } from "@/lib/types";
import { ContentStatusBadge } from "@/components/content/content-status-badge";
import { formatDate, formatViews, formatScore } from "@/lib/format";
import {
  ArrowLeft,
  Save,
  Loader2,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  FileCode,
  Calendar,
  Eye,
  TrendingUp,
  Youtube,
  Globe,
  Video,
  FileText
} from "lucide-react";
import { toast } from "sonner";

export default function ContentItemDetail() {
  const params = useParams();
  const router = useRouter();
  const idStr = params.id as string;
  const itemId = parseInt(idStr);

  const [item, setItem] = useState<ContentItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Form states
  const [status, setStatus] = useState<ContentStatus>("new");
  const [notes, setNotes] = useState("");
  const [productionNotes, setProductionNotes] = useState("");
  const [rejectedReason, setRejectedReason] = useState("");

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showRawJson, setShowRawJson] = useState(false);

  useEffect(() => {
    async function loadItem() {
      if (isNaN(itemId)) {
        setError("ID de conteúdo inválido.");
        setLoading(false);
        return;
      }
      try {
        setLoading(true);
        setError(null);
        const data = await getContentItem(itemId);
        setItem(data);
        setStatus(data.status);
        setNotes(data.notes || "");
        setProductionNotes(data.production_notes || "");
        setRejectedReason(data.rejected_reason || "");
      } catch (err: any) {
        setError(err.message || "Não foi possível carregar o conteúdo.");
      } finally {
        setLoading(false);
      }
    }
    loadItem();
  }, [itemId]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!item) return;

    setIsSubmitting(true);
    try {
      const payload = {
        status,
        notes: notes.trim() || null,
        production_notes: productionNotes.trim() || null,
        rejected_reason: status === "rejected" ? rejectedReason.trim() || null : null,
      };

      const updated = await updateContentItemCuration(item.id, payload);
      setItem(updated);
      toast.success("Conteúdo atualizado com sucesso!");
    } catch (err: any) {
      toast.error("Erro ao atualizar o conteúdo", {
        description: err.message || "Erro desconhecido",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex h-[50vh] flex-col items-center justify-center gap-3">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
        <span className="text-sm text-slate-400 font-medium">Carregando detalhes do conteúdo...</span>
      </div>
    );
  }

  if (error || !item) {
    return (
      <div className="mx-auto max-w-2xl rounded-xl border border-rose-950 bg-rose-950/10 p-6 text-center shadow-lg my-12">
        <h3 className="text-lg font-bold text-white">Erro ao Carregar Detalhes</h3>
        <p className="mt-2 text-sm text-rose-300">{error || "Conteúdo não encontrado."}</p>
        <div className="mt-6">
          <Link
            href="/content"
            className="inline-flex items-center gap-2 rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-slate-200 border border-slate-800 hover:bg-slate-800 transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>Voltar para Conteúdos</span>
          </Link>
        </div>
      </div>
    );
  }

  const isYoutube = item.source.toLowerCase() === "youtube";

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      {/* Navigation & Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <Link
          href="/content"
          className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-400 hover:text-slate-200 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>Voltar para Lista</span>
        </Link>
        <div className="flex items-center gap-3">
          <span className="text-xs text-slate-500 font-mono">Última atualização: {formatDate(item.last_seen_at)}</span>
          <ContentStatusBadge status={item.status} />
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Left Column: Content Information */}
        <div className="space-y-6 lg:col-span-2">
          <div className="rounded-xl border border-slate-800 bg-[#0b101c]/30 p-6 backdrop-blur-sm space-y-6">
            <div>
              <div className="flex items-center gap-2 text-xs text-slate-500 font-medium mb-3">
                <span
                  className={`inline-flex items-center gap-1 px-2 py-0.5 rounded border text-[11px] font-bold ${
                    isYoutube
                      ? "bg-rose-500/10 text-rose-400 border-rose-500/20"
                      : "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                  }`}
                >
                  {isYoutube ? "YouTube" : "Google News"}
                </span>
                <span>•</span>
                <span className="inline-flex items-center gap-1">
                  {item.content_type === "video" ? <Video className="h-3 w-3" /> : <FileText className="h-3 w-3" />}
                  {item.content_type === "video" ? "Vídeo" : "Artigo"}
                </span>
                <span>•</span>
                <span className="font-mono">ID Ext: {item.external_id}</span>
              </div>
              <h1 className="text-xl font-bold text-white sm:text-2xl leading-snug leading-tight select-text">
                {item.title}
              </h1>
            </div>

            {/* Metrics Row */}
            <div className="grid grid-cols-2 gap-4 border-y border-slate-800/60 py-5 sm:grid-cols-4">
              <div className="space-y-1">
                <span className="block text-[10px] uppercase font-bold tracking-wider text-slate-500">Score Oportunidade</span>
                <div className="flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-indigo-400" />
                  <span className="text-lg font-bold text-white">{formatScore(item.score)}</span>
                </div>
              </div>
              <div className="space-y-1">
                <span className="block text-[10px] uppercase font-bold tracking-wider text-slate-500">Total de Views</span>
                <div className="flex items-center gap-2">
                  <Eye className="h-4 w-4 text-slate-400" />
                  <span className="text-lg font-bold text-white">{formatViews(item.views)}</span>
                </div>
              </div>
              <div className="space-y-1">
                <span className="block text-[10px] uppercase font-bold tracking-wider text-slate-500">Views por Dia</span>
                <div className="flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-emerald-400" />
                  <span className="text-lg font-bold text-white">
                    {item.views_per_day ? `+${formatViews(item.views_per_day)}` : "-"}
                  </span>
                </div>
              </div>
              <div className="space-y-1">
                <span className="block text-[10px] uppercase font-bold tracking-wider text-slate-500">Publicado Em</span>
                <div className="flex items-center gap-2">
                  <Calendar className="h-4 w-4 text-slate-400" />
                  <span className="text-sm font-semibold text-slate-300 truncate">{formatDate(item.published_at)?.split(" ")[0]}</span>
                </div>
              </div>
            </div>

            {/* Description */}
            <div className="space-y-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">Descrição / Sumário</h3>
              {item.description ? (
                <p className="text-sm text-slate-300 leading-relaxed whitespace-pre-wrap select-text bg-slate-950/20 rounded-lg p-4 border border-slate-900/60">
                  {item.description}
                </p>
              ) : (
                <p className="text-sm text-slate-500 italic">Nenhuma descrição ou sumário disponível.</p>
              )}
            </div>

            {/* Link to Source */}
            <div className="pt-2">
              <a
                href={item.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-md shadow-indigo-600/20 hover:bg-indigo-500 transition-colors"
              >
                <span>Visualizar Conteúdo Original</span>
                <ExternalLink className="h-4 w-4" />
              </a>
            </div>
          </div>

          {/* Raw JSON Accordion */}
          <div className="rounded-xl border border-slate-800 bg-[#0b101c]/30 p-6 backdrop-blur-sm space-y-4">
            <button
              onClick={() => setShowRawJson(!showRawJson)}
              className="flex w-full items-center justify-between text-left outline-none"
            >
              <h3 className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-400">
                <FileCode className="h-4 w-4 text-slate-500" />
                Metadados Brutos (JSON de Extração)
              </h3>
              {showRawJson ? <ChevronUp className="h-4 w-4 text-slate-400" /> : <ChevronDown className="h-4 w-4 text-slate-400" />}
            </button>

            {showRawJson && (
              <div className="overflow-x-auto rounded-lg border border-slate-900 bg-slate-950 p-4 font-mono text-[11px] text-slate-400 leading-relaxed select-text">
                {item.raw_json ? (
                  <pre>{JSON.stringify(item.raw_json, null, 2)}</pre>
                ) : (
                  <span className="text-slate-600 italic">Nenhum metadado bruto disponível.</span>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Curation Panel */}
        <div className="space-y-6">
          <div className="rounded-xl border border-slate-800 bg-[#0b101c]/50 p-6 backdrop-blur-sm space-y-6">
            <h2 className="text-lg font-bold text-white">Curadoria Editorial</h2>

            <form onSubmit={handleSave} className="space-y-5">
              {/* Status Select */}
              <div className="space-y-2">
                <label htmlFor="curation-status" className="text-xs font-bold uppercase tracking-wider text-slate-400">
                  Definir Status
                </label>
                <select
                  id="curation-status"
                  value={status}
                  onChange={(e) => setStatus(e.target.value as ContentStatus)}
                  className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3.5 py-2.5 text-sm text-slate-200 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 transition-all font-semibold"
                >
                  <option value="new">Novo</option>
                  <option value="reviewed">Revisado (Aprovado na triagem)</option>
                  <option value="selected">Selecionado (Pronto para Roteiro)</option>
                  <option value="rejected">Rejeitado</option>
                  <option value="produced">Produzido</option>
                  <option value="archived">Arquivado</option>
                </select>
              </div>

              {/* Rejected Reason */}
              {status === "rejected" && (
                <div className="space-y-2">
                  <label htmlFor="rejected-reason" className="text-xs font-bold uppercase tracking-wider text-rose-400">
                    Motivo da Rejeição
                  </label>
                  <input
                    id="rejected-reason"
                    type="text"
                    value={rejectedReason}
                    onChange={(e) => setRejectedReason(e.target.value)}
                    placeholder="Ex: Assunto repetitivo, desatualizado..."
                    className="w-full rounded-lg border border-rose-950 bg-slate-950 px-3.5 py-2.5 text-sm text-slate-200 outline-none focus:border-rose-500 focus:ring-2 focus:ring-rose-500/10 transition-all"
                    required
                  />
                </div>
              )}

              {/* Production Notes */}
              {(status === "selected" || status === "produced") && (
                <div className="space-y-2">
                  <label htmlFor="production-notes" className="text-xs font-bold uppercase tracking-wider text-emerald-400">
                    Notas de Produção / Roteiro
                  </label>
                  <textarea
                    id="production-notes"
                    rows={4}
                    value={productionNotes}
                    onChange={(e) => setProductionNotes(e.target.value)}
                    placeholder="Orientações e pautas para desenvolvimento..."
                    className="w-full rounded-lg border border-emerald-950 bg-slate-950 px-3.5 py-2.5 text-sm text-slate-200 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/10 transition-all resize-none"
                  />
                </div>
              )}

              {/* Curatorial Notes */}
              <div className="space-y-2">
                <label htmlFor="curation-notes" className="text-xs font-bold uppercase tracking-wider text-slate-400">
                  Notas de Observação (Curador)
                </label>
                <textarea
                  id="curation-notes"
                  rows={5}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Seus insights sobre a oportunidade, ideias para o gancho de abertura..."
                  className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3.5 py-2.5 text-sm text-slate-200 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 transition-all resize-none"
                />
              </div>

              {/* Save Button */}
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
          </div>

          {/* Curatorial Log / Timestamps */}
          <div className="rounded-xl border border-slate-800 bg-[#0b101c]/30 p-6 backdrop-blur-sm text-xs space-y-3">
            <h4 className="font-bold text-white uppercase tracking-wider text-[10px] text-slate-500">Histórico de Triagem</h4>
            <div className="space-y-2 text-slate-400 font-medium">
              <div className="flex justify-between">
                <span>Coletado em:</span>
                <span className="font-mono">{formatDate(item.collected_at)}</span>
              </div>
              <div className="flex justify-between">
                <span>Revisado em:</span>
                <span className="font-mono">{item.reviewed_at ? formatDate(item.reviewed_at) : "Pendente"}</span>
              </div>
              <div className="flex justify-between">
                <span>Selecionado em:</span>
                <span className="font-mono">{item.selected_at ? formatDate(item.selected_at) : "Pendente"}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
