"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import Link from "next/link";
import {
  importYouTubeReferenceUrl,
  getReferenceSources,
  getReferenceImportJob
} from "@/lib/api";
import {
  ReferenceSource,
  ReferenceSourceStatus,
  ReferenceImportJob
} from "@/lib/types";
import {
  Search,
  Plus,
  Play,
  Loader2,
  AlertCircle,
  ExternalLink,
  FileText,
  CheckCircle,
  XCircle,
  RefreshCw,
  Clock,
  ArrowRight,
  Eye,
  ThumbsUp,
  Volume2
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { formatDate, formatRelativeTime, formatViews } from "@/lib/format";

// Inline helper for formatting duration
function formatDuration(seconds: number | null | undefined): string {
  if (!seconds) return "-";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) {
    return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  }
  return `${m}:${s.toString().padStart(2, '0')}`;
}

export default function ReferencesPage() {
  const [sources, setSources] = useState<ReferenceSource[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [limit, setLimit] = useState(10);
  const [offset, setOffset] = useState(0);
  const [searchText, setSearchText] = useState("");
  const [statusFilter, setStatusFilter] = useState("Todos");
  const [sortField, setSortField] = useState<"created_at" | "view_count" | "like_count" | "duration_seconds" | "published_at">("created_at");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");

  // Import form states
  const [importUrl, setImportUrl] = useState("");
  const [preferredLanguagesStr, setPreferredLanguagesStr] = useState("pt, pt-BR, en");
  const [allowAutoCaptions, setAllowAutoCaptions] = useState(true);
  const [importing, setImporting] = useState(false);

  // Polling state
  const [activeJobId, setActiveJobId] = useState<number | null>(null);
  const [pollingJob, setPollingJob] = useState<ReferenceImportJob | null>(null);
  const pollCountRef = useRef(0);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Fetch reference sources
  const loadSources = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await getReferenceSources({
        limit,
        offset,
        search: searchText,
        status: statusFilter,
        sort_by: sortField,
        sort_order: sortOrder
      });
      setSources(res.items);
      setTotal(res.total);
    } catch (err: any) {
      setError(err.message || "Erro ao carregar fontes de referência.");
    } finally {
      setLoading(false);
    }
  }, [limit, offset, searchText, statusFilter, sortField, sortOrder]);

  useEffect(() => {
    loadSources();
  }, [loadSources]);

  // Clean polling interval on unmount
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, []);

  // Poll active import job
  const startPollingJob = (jobId: number) => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
    }
    
    pollCountRef.current = 0;
    setActiveJobId(jobId);

    const poll = async () => {
      pollCountRef.current += 1;
      
      // Stop polling after 3 minutes (e.g. 60 attempts every 3s)
      if (pollCountRef.current > 60) {
        if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
        toast.info("Processamento prolongado", {
          description: "O vídeo continua sendo importado em segundo plano. Por favor, atualize em instantes.",
          duration: 8000
        });
        setActiveJobId(null);
        setPollingJob(null);
        loadSources();
        return;
      }

      try {
        const job = await getReferenceImportJob(jobId);
        setPollingJob(job);

        if (job.status === "completed") {
          if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
          toast.success("Vídeo importado com sucesso!", {
            description: `A transcrição de "${job.source_url.substring(0, 40)}..." está pronta.`
          });
          setActiveJobId(null);
          setPollingJob(null);
          loadSources();
        } else if (job.status === "needs_audio_transcription") {
          if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
          toast.warning("Importado sem legendas", {
            description: "Vídeo salvo, mas não possui legendas disponíveis. Status alterado para pendente de áudio.",
            duration: 8000
          });
          setActiveJobId(null);
          setPollingJob(null);
          loadSources();
        } else if (job.status === "failed") {
          if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
          toast.error("Falha ao importar vídeo", {
            description: job.error_message || "Erro desconhecido durante o processo.",
            duration: 8000
          });
          setActiveJobId(null);
          setPollingJob(null);
          loadSources();
        }
      } catch (err: any) {
        // Silently catch polling errors and retry
      }
    };

    // Run first poll immediately, then every 3 seconds
    poll();
    pollIntervalRef.current = setInterval(poll, 3000);
  };

  // Submit YouTube import
  const handleImportSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!importUrl.trim()) {
      toast.error("Por favor, informe a URL do YouTube.");
      return;
    }

    const langs = preferredLanguagesStr
      .split(",")
      .map(lang => lang.trim())
      .filter(Boolean);

    setImporting(true);
    toast.info("Iniciando importação de vídeo...", {
      description: "Conectando ao YouTube para extração de metadados..."
    });

    try {
      const payload = {
        url: importUrl.trim(),
        preferred_languages: langs,
        allow_auto_captions: allowAutoCaptions
      };
      const response = await importYouTubeReferenceUrl(payload);
      
      toast.info("Importação enfileirada", {
        description: "Aguardando processamento em segundo plano..."
      });

      // Clear input
      setImportUrl("");
      // Start polling status
      startPollingJob(response.import_job_id);

    } catch (err: any) {
      toast.error("Erro ao iniciar importação", {
        description: err.message || "Verifique se a URL informada está correta."
      });
    } finally {
      setImporting(false);
    }
  };

  // Get visual badge config
  const getStatusBadge = (status: ReferenceSourceStatus) => {
    switch (status) {
      case "transcribed":
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
      case "importing":
        return "bg-blue-500/10 text-blue-400 border-blue-500/20";
      case "needs_audio_transcription":
        return "bg-amber-500/10 text-amber-400 border-amber-500/20";
      case "failed":
        return "bg-rose-500/10 text-rose-400 border-rose-500/20";
      case "archived":
        return "bg-slate-500/10 text-slate-400 border-slate-500/20";
      case "new":
      default:
        return "bg-indigo-500/10 text-indigo-400 border-indigo-500/20";
    }
  };

  const getStatusLabel = (status: ReferenceSourceStatus) => {
    switch (status) {
      case "transcribed": return "Transcrito";
      case "importing": return "Importando...";
      case "needs_audio_transcription": return "Pendente de Áudio";
      case "failed": return "Falhou";
      case "archived": return "Arquivado";
      case "new": return "Novo";
      default: return status;
    }
  };

  const getJobStatusLabel = (status: string) => {
    switch (status) {
      case "queued": return "Fila de Espera";
      case "running": return "Extraindo Metadados/Legendas...";
      case "completed": return "Concluído!";
      case "needs_audio_transcription": return "Concluído sem legendas (Pendente de Áudio)";
      case "failed": return "Falhou";
      default: return status;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header section */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-slate-850 pb-5">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white sm:text-3xl font-sans">
            Referências e Transcrições
          </h2>
          <p className="mt-1 text-sm text-slate-400">
            Cole links do YouTube para extrair metadados e transcrições automaticamente como referências criativas.
          </p>
        </div>
        <div>
          <button
            onClick={loadSources}
            className="flex h-10 w-10 items-center justify-center rounded-lg border border-slate-800 bg-[#0b101c] hover:bg-slate-900 text-slate-400 hover:text-slate-200 transition-colors"
            title="Atualizar lista"
          >
            <RefreshCw className="h-4.5 w-4.5" />
          </button>
        </div>
      </div>

      {/* Top Section: Form and Active Polling Job Info */}
      <div className="grid gap-6 md:grid-cols-3">
        {/* Import Form Card */}
        <div className="md:col-span-2 rounded-xl border border-slate-800 bg-[#0b101c]/35 p-6 backdrop-blur-sm shadow-md">
          <h3 className="text-base font-bold text-white mb-4 flex items-center gap-2">
            <Plus className="h-4.5 w-4.5 text-indigo-400" />
            Importar do YouTube
          </h3>
          <form onSubmit={handleImportSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-xs font-bold uppercase tracking-wider text-slate-400">URL do Vídeo ou Shorts</label>
              <input
                type="text"
                value={importUrl}
                onChange={(e) => setImportUrl(e.target.value)}
                placeholder="Ex: https://www.youtube.com/watch?v=VIDEO_ID ou https://youtu.be/... ou shorts/..."
                className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3.5 py-2.5 text-sm text-slate-200 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/10 transition-all font-semibold"
                disabled={importing || activeJobId !== null}
                required
              />
            </div>
            
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <label className="text-xs font-bold uppercase tracking-wider text-slate-400">Idiomas Preferidos (Ordem)</label>
                <input
                  type="text"
                  value={preferredLanguagesStr}
                  onChange={(e) => setPreferredLanguagesStr(e.target.value)}
                  placeholder="pt, pt-BR, en"
                  className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3.5 py-2 text-sm text-slate-200 outline-none focus:border-indigo-500 font-semibold"
                  disabled={importing || activeJobId !== null}
                />
              </div>

              <div className="flex items-center h-full pt-6 select-none">
                <label className="flex items-center gap-2.5 cursor-pointer text-sm text-slate-350 font-medium">
                  <input
                    type="checkbox"
                    checked={allowAutoCaptions}
                    onChange={(e) => setAllowAutoCaptions(e.target.checked)}
                    className="h-4.5 w-4.5 rounded border-slate-800 bg-slate-950 text-indigo-600 outline-none focus:ring-offset-0 focus:ring-0"
                    disabled={importing || activeJobId !== null}
                  />
                  <span>Permitir Legendas Automáticas</span>
                </label>
              </div>
            </div>

            <button
              type="submit"
              disabled={importing || activeJobId !== null || !importUrl.trim()}
              className="w-full sm:w-auto flex items-center justify-center gap-2 rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-md shadow-indigo-600/15 hover:bg-indigo-500 transition-all disabled:opacity-40 select-none"
            >
              {importing ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Conectando...</span>
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 fill-current" />
                  <span>Importar Vídeo</span>
                </>
              )}
            </button>
          </form>
        </div>

        {/* Polling/Active job card */}
        <div className="rounded-xl border border-slate-800 bg-[#0b101c]/25 p-6 backdrop-blur-sm flex flex-col justify-between">
          <div>
            <h3 className="text-base font-bold text-white mb-4">Tarefa Ativa</h3>
            {activeJobId ? (
              <div className="space-y-4">
                <div className="flex items-start gap-3">
                  <Loader2 className="h-5 w-5 text-indigo-400 animate-spin shrink-0 mt-0.5" />
                  <div className="space-y-1">
                    <span className="block text-xs font-semibold text-slate-300">Processando Importação</span>
                    <span className="block text-[11px] font-mono text-slate-500">ID do Job: #{activeJobId}</span>
                  </div>
                </div>

                <div className="space-y-2.5 bg-slate-950/40 rounded-lg p-3.5 border border-slate-900 text-xs">
                  <div className="flex justify-between">
                    <span className="text-slate-500 font-bold uppercase tracking-wider text-[9px]">Status</span>
                    <span className="text-indigo-400 font-semibold">{pollingJob ? getJobStatusLabel(pollingJob.status) : "Na fila..."}</span>
                  </div>
                  {pollingJob?.selected_language && (
                    <div className="flex justify-between">
                      <span className="text-slate-500 font-bold uppercase tracking-wider text-[9px]">Idioma Escolhido</span>
                      <span className="text-slate-300 font-semibold uppercase font-mono">{pollingJob.selected_language}</span>
                    </div>
                  )}
                  {pollingJob?.reference_source_id && (
                    <div className="flex justify-between items-center pt-1.5 border-t border-slate-900/60 mt-1">
                      <span className="text-slate-500 font-bold uppercase tracking-wider text-[9px]">Ação</span>
                      <Link
                        href={`/references/${pollingJob.reference_source_id}`}
                        className="text-[11px] font-bold text-indigo-400 hover:text-indigo-300 flex items-center gap-1 group"
                      >
                        Ver detalhes
                        <ArrowRight className="h-3 w-3 group-hover:translate-x-0.5 transition-transform" />
                      </Link>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="text-center py-8 text-slate-500 text-sm font-medium">
                Nenhuma importação ativa em progresso neste navegador.
              </div>
            )}
          </div>

          {activeJobId && (
            <div className="text-[10px] text-slate-500 font-medium italic border-t border-slate-800/40 pt-4 mt-2">
              Polling automático ativo (atualiza a cada 3s)
            </div>
          )}
        </div>
      </div>

      {/* Main List Section */}
      <div className="space-y-4">
        {/* Filter bar */}
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between bg-slate-950/20 p-4 rounded-xl border border-slate-850">
          <div className="flex flex-1 flex-col gap-3 sm:flex-row sm:items-center">
            {/* Search Input */}
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
              <input
                type="text"
                placeholder="Pesquisar por título, canal ou conteúdo..."
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
                className="w-full rounded-lg border border-slate-800 bg-slate-950 pl-10 pr-4 py-2 text-sm text-slate-200 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/10 transition-all"
              />
            </div>

            {/* Status Select */}
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500 font-bold uppercase tracking-wider">Status:</span>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="rounded-lg border border-slate-800 bg-slate-950 px-3 py-1.5 text-xs text-slate-350 outline-none focus:border-indigo-500 font-medium"
              >
                <option value="Todos">Todos</option>
                <option value="transcribed">Transcrito</option>
                <option value="needs_audio_transcription">Pendente de Áudio</option>
                <option value="importing">Importando</option>
                <option value="failed">Falhou</option>
                <option value="archived">Arquivado</option>
              </select>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500 font-bold uppercase tracking-wider">Ordenar:</span>
            <select
              value={sortField}
              onChange={(e) => setSortField(e.target.value as any)}
              className="rounded-lg border border-slate-800 bg-slate-950 px-3 py-1.5 text-xs text-slate-350 outline-none focus:border-indigo-500 font-medium"
            >
              <option value="created_at">Data Cadastro</option>
              <option value="published_at">Data Publicação</option>
              <option value="view_count">Visualizações</option>
              <option value="like_count">Likes</option>
              <option value="duration_seconds">Duração</option>
            </select>
            <button
              onClick={() => setSortOrder(sortOrder === "asc" ? "desc" : "asc")}
              className="h-8.5 px-3 rounded-lg border border-slate-800 bg-slate-950 text-xs font-semibold text-slate-400 hover:text-slate-200 transition-colors uppercase font-mono"
            >
              {sortOrder === "asc" ? "ASC" : "DESC"}
            </button>
          </div>
        </div>

        {/* References Table */}
        {loading && sources.length === 0 ? (
          <div className="flex h-[30vh] flex-col items-center justify-center gap-3">
            <Loader2 className="h-7 w-7 animate-spin text-indigo-500" />
            <span className="text-xs text-slate-400 font-medium">Carregando referências...</span>
          </div>
        ) : error ? (
          <div className="rounded-xl border border-rose-950 bg-rose-950/20 p-5 text-rose-250 flex items-center gap-3">
            <AlertCircle className="h-5 w-5 text-rose-450 shrink-0" />
            <span className="text-sm">{error}</span>
          </div>
        ) : sources.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-800 bg-slate-950/10 py-16 text-center text-slate-500 font-medium">
            Nenhuma fonte de referência encontrada. Comece colando um link do YouTube acima.
          </div>
        ) : (
          <div className="rounded-xl border border-slate-800/80 bg-[#0b101c]/25 backdrop-blur-sm overflow-hidden flex flex-col">
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-left text-sm text-slate-300">
                <thead className="border-b border-slate-800 bg-[#0c1223]/60 text-xs font-bold uppercase tracking-wider text-slate-400">
                  <tr>
                    <th className="px-6 py-4">Vídeo</th>
                    <th className="px-6 py-4 w-32">Duração</th>
                    <th className="px-6 py-4 text-right w-28">Views</th>
                    <th className="px-6 py-4 text-right w-28">Likes</th>
                    <th className="px-6 py-4 w-36">Publicado</th>
                    <th className="px-6 py-4 w-24 text-center">Idioma</th>
                    <th className="px-6 py-4 w-32">Status</th>
                    <th className="px-6 py-4 text-center w-24">Ações</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {sources.map((item) => (
                    <tr key={item.id} className="hover:bg-slate-900/25 transition-colors">
                      {/* Video Title and Thumbnail */}
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3 max-w-sm sm:max-w-md md:max-w-lg lg:max-w-xl">
                          {item.thumbnail_url ? (
                            <img
                              src={item.thumbnail_url}
                              alt=""
                              className="h-10 w-16 rounded object-cover border border-slate-800/60 shrink-0 bg-slate-950"
                            />
                          ) : (
                            <div className="h-10 w-16 rounded border border-slate-800 bg-slate-950 shrink-0 flex items-center justify-center text-slate-600">
                              <FileText className="h-4 w-4" />
                            </div>
                          )}
                          <div className="flex flex-col gap-0.5 truncate">
                            <span className="font-semibold text-slate-200 line-clamp-1 leading-tight select-text">
                              {item.title}
                            </span>
                            <span className="text-xs text-slate-450 font-medium truncate">
                              {item.channel_title || "Canal desconhecido"}
                            </span>
                          </div>
                        </div>
                      </td>

                      {/* Duration */}
                      <td className="px-6 py-4 text-slate-350 font-medium font-mono text-xs">
                        <div className="flex items-center gap-1.5">
                          <Clock className="h-3 w-3 text-slate-500" />
                          {formatDuration(item.duration_seconds)}
                        </div>
                      </td>

                      {/* Views */}
                      <td className="px-6 py-4 text-right font-mono font-semibold text-slate-300 text-xs">
                        {formatViews(item.view_count)}
                      </td>

                      {/* Likes */}
                      <td className="px-6 py-4 text-right font-mono font-medium text-slate-400 text-xs">
                        {formatViews(item.like_count)}
                      </td>

                      {/* Published */}
                      <td className="px-6 py-4 text-slate-450 font-medium text-xs">
                        <div className="flex flex-col">
                          <span className="text-slate-300">{formatRelativeTime(item.published_at)}</span>
                          <span className="text-[9px] text-slate-500 font-mono mt-0.5">
                            {formatDate(item.published_at)?.split(" ")[0]}
                          </span>
                        </div>
                      </td>

                      {/* Language */}
                      <td className="px-6 py-4 text-center font-mono text-[11px] font-bold text-slate-400 uppercase">
                        {item.language || "-"}
                      </td>

                      {/* Status */}
                      <td className="px-6 py-4">
                        <span className={cn("inline-flex items-center rounded px-2 py-0.5 text-[10px] font-bold border tracking-wide uppercase shrink-0 shadow-sm", getStatusBadge(item.status))}>
                          {getStatusLabel(item.status)}
                        </span>
                      </td>

                      {/* Actions */}
                      <td className="px-6 py-4 text-center">
                        <div className="flex items-center justify-center gap-2">
                          <a
                            href={item.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex h-8 w-8 items-center justify-center rounded-lg border border-slate-800 bg-slate-950/40 text-slate-450 hover:border-indigo-500/30 hover:bg-indigo-600/10 hover:text-indigo-400 transition-colors"
                            title="Abrir no YouTube"
                          >
                            <ExternalLink className="h-3.5 w-3.5" />
                          </a>
                          
                          <Link
                            href={`/references/${item.id}`}
                            className="flex h-8 w-8 items-center justify-center rounded-lg border border-slate-850 bg-indigo-600/5 text-indigo-400 hover:bg-indigo-600 hover:text-white transition-all shadow shadow-indigo-950/20"
                            title="Ver Transcrição"
                          >
                            <Eye className="h-3.5 w-3.5" />
                          </Link>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination Controls */}
            {total > 0 && (
              <div className="flex flex-col gap-4 border-t border-slate-850 bg-[#0b101c]/50 px-6 py-4 md:flex-row md:items-center md:justify-between">
                <span className="text-xs text-slate-450 font-medium">
                  Mostrando <strong className="text-slate-200">{offset + 1}</strong> a{" "}
                  <strong className="text-slate-200">{Math.min(offset + limit, total)}</strong> de{" "}
                  <strong className="text-slate-200">{total}</strong> fontes
                </span>
                
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setOffset(Math.max(0, offset - limit))}
                    disabled={offset === 0}
                    className="h-8.5 px-3 rounded-lg border border-slate-800 bg-slate-950 text-xs font-semibold text-slate-450 hover:bg-slate-900 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                  >
                    Anterior
                  </button>
                  <button
                    onClick={() => {
                      if (offset + limit < total) setOffset(offset + limit);
                    }}
                    disabled={offset + limit >= total}
                    className="h-8.5 px-3 rounded-lg border border-slate-800 bg-slate-950 text-xs font-semibold text-slate-450 hover:bg-slate-900 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                  >
                    Próxima
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
