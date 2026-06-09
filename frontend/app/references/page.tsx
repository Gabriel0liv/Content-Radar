"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
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
  Volume2,
  ChevronDown,
  SlidersHorizontal,
  X
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

const availableLanguages = [
  { code: "pt", name: "Português" },
  { code: "pt-BR", name: "Português (Brasil)" },
  { code: "en", name: "Inglês" },
  { code: "es", name: "Espanhol" },
  { code: "fr", name: "Francês" },
  { code: "de", name: "Alemão" },
  { code: "it", name: "Italiano" }
];

export default function ReferencesPage() {
  const router = useRouter();
  const [sources, setSources] = useState<ReferenceSource[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [limit, setLimit] = useState(10);
  const [offset, setOffset] = useState(0);
  const [searchText, setSearchText] = useState("");
  const [statusFilter, setStatusFilter] = useState("Todos");
  const [sourceTypeFilter, setSourceTypeFilter] = useState("Todos");
  const [channelTitleFilter, setChannelTitleFilter] = useState("");
  const [sortField, setSortField] = useState<"created_at" | "view_count" | "like_count" | "duration_seconds" | "published_at">("created_at");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const [isFilterModalOpen, setIsFilterModalOpen] = useState(false);

  const getActiveFiltersCount = () => {
    let count = 0;
    if (searchText.trim()) count++;
    if (channelTitleFilter.trim()) count++;
    if (statusFilter !== "Todos") count++;
    if (sourceTypeFilter !== "Todos") count++;
    return count;
  };

  // Import form states
  const [importUrl, setImportUrl] = useState("");
  const [selectedLangs, setSelectedLangs] = useState<string[]>(["pt", "pt-BR", "en"]);
  const [showLangDropdown, setShowLangDropdown] = useState(false);
  const [allowAutoCaptions, setAllowAutoCaptions] = useState(true);
  const [importing, setImporting] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const [activeJobId, setActiveJobId] = useState<number | null>(null);
  const [pollingJob, setPollingJob] = useState<ReferenceImportJob | null>(null);
  const pollCountRef = useRef(0);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Close dropdown on click outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowLangDropdown(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const toggleLanguage = (langCode: string) => {
    if (selectedLangs.includes(langCode)) {
      if (selectedLangs.length > 1) {
        setSelectedLangs(selectedLangs.filter(l => l !== langCode));
      } else {
        toast.warning("Selecione pelo menos um idioma.");
      }
    } else {
      setSelectedLangs([...selectedLangs, langCode]);
    }
  };

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
        source_type: sourceTypeFilter,
        channel_title: channelTitleFilter,
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
  }, [limit, offset, searchText, statusFilter, sourceTypeFilter, channelTitleFilter, sortField, sortOrder]);

  // Reset offset to 0 when filters change
  useEffect(() => {
    setOffset(0);
  }, [searchText, statusFilter, sourceTypeFilter, channelTitleFilter, sortField, sortOrder]);

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

    const langs = selectedLangs.length > 0 ? selectedLangs : ["pt", "pt-BR", "en"];

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
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setIsFilterModalOpen(true)}
            className={cn(
              "relative flex h-10 px-3.5 items-center justify-center gap-2 rounded-lg border transition-colors font-semibold text-xs select-none",
              getActiveFiltersCount() > 0
                ? "border-indigo-500 bg-indigo-600/10 text-indigo-400 hover:bg-indigo-650/20"
                : "border-slate-800 bg-[#0b101c] text-slate-400 hover:text-slate-205 hover:bg-slate-900"
            )}
            title="Filtrar e Ordenar"
          >
            <SlidersHorizontal className="h-4 w-4" />
            <span>Filtros</span>
            {getActiveFiltersCount() > 0 && (
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-indigo-600 text-[10px] font-bold text-white leading-none">
                {getActiveFiltersCount()}
              </span>
            )}
          </button>

          <button
            type="button"
            onClick={loadSources}
            className="flex h-10 w-10 items-center justify-center rounded-lg border border-slate-800 bg-[#0b101c] hover:bg-slate-900 text-slate-400 hover:text-slate-200 transition-colors"
            title="Atualizar lista"
          >
            <RefreshCw className="h-4.5 w-4.5" />
          </button>
        </div>
      </div>

      {/* YouTube Import Form Card */}
      <div className="rounded-xl border border-slate-800 bg-[#0b101c]/35 p-6 backdrop-blur-sm shadow-md">
        <h3 className="text-base font-bold text-white mb-4 flex items-center gap-2">
          <Plus className="h-4.5 w-4.5 text-indigo-400" />
          Importar do YouTube
        </h3>
        <form onSubmit={handleImportSubmit} className="space-y-3">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <div className="flex-1 relative">
              <input
                type="text"
                value={importUrl}
                onChange={(e) => setImportUrl(e.target.value)}
                placeholder="Cole o link do YouTube (Vídeo ou Shorts) aqui..."
                className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3.5 py-2.5 text-sm text-slate-200 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/10 transition-all font-semibold"
                disabled={importing || activeJobId !== null}
                required
              />
            </div>

            {/* Custom Multi-Select Dropdown */}
            <div className="relative shrink-0" ref={dropdownRef}>
              <button
                type="button"
                onClick={() => setShowLangDropdown(!showLangDropdown)}
                disabled={importing || activeJobId !== null}
                className="h-10 px-3.5 flex items-center justify-between gap-2 rounded-lg border border-slate-800 bg-slate-950 text-xs font-semibold text-slate-350 hover:border-slate-700 transition-colors w-full sm:w-44 select-none"
              >
                <span className="truncate">
                  Idiomas ({selectedLangs.join(", ")})
                </span>
                <ChevronDown className="h-4 w-4 text-slate-500 shrink-0" />
              </button>

              {showLangDropdown && (
                <div className="absolute right-0 mt-2 w-48 rounded-lg border border-slate-850 bg-slate-950 p-2 shadow-xl z-20 space-y-1">
                  <span className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 px-2.5 py-1">Idiomas Preferidos</span>
                  <div className="max-h-48 overflow-y-auto space-y-0.5">
                    {availableLanguages.map((lang) => {
                      const isChecked = selectedLangs.includes(lang.code);
                      return (
                        <label
                          key={lang.code}
                          className={cn(
                            "flex items-center gap-2.5 px-2.5 py-1.5 rounded text-xs font-medium cursor-pointer transition-colors select-none",
                            isChecked ? "text-white bg-indigo-600/10 hover:bg-indigo-600/15" : "text-slate-400 hover:bg-slate-900/60"
                          )}
                        >
                          <input
                            type="checkbox"
                            checked={isChecked}
                            onChange={() => toggleLanguage(lang.code)}
                            className="h-3.5 w-3.5 rounded border-slate-800 bg-slate-950 text-indigo-600 outline-none focus:ring-0"
                          />
                          <span>{lang.name}</span>
                        </label>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>

            {/* Import Button */}
            <button
              type="submit"
              disabled={importing || activeJobId !== null || !importUrl.trim()}
              className="shrink-0 flex items-center justify-center gap-2 rounded-lg bg-indigo-600 px-5 h-10 text-sm font-semibold text-white shadow-md shadow-indigo-600/15 hover:bg-indigo-500 transition-all disabled:opacity-40 select-none"
            >
              {importing ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin shrink-0" />
                  <span>Importando...</span>
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 fill-current shrink-0" />
                  <span>Importar</span>
                </>
              )}
            </button>
          </div>

          <div className="flex items-center gap-2 select-none text-[11px] font-semibold text-slate-450 mt-1.5 pl-1">
            <label className="flex items-center gap-2 cursor-pointer hover:text-slate-350 transition-colors">
              <input
                type="checkbox"
                checked={allowAutoCaptions}
                onChange={(e) => setAllowAutoCaptions(e.target.checked)}
                className="h-4 w-4 rounded border-slate-800 bg-slate-950 text-indigo-600 outline-none focus:ring-0"
                disabled={importing || activeJobId !== null}
              />
              <span>Habilitar legendas automáticas geradas por IA</span>
            </label>
          </div>
        </form>

        {/* Active Job Status Banner */}
        {activeJobId && (
          <div className="mt-4 rounded-xl border border-indigo-900/40 bg-indigo-950/15 p-4 shadow-inner flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 animate-pulse">
            <div className="flex items-center gap-3">
              <Loader2 className="h-5 w-5 text-indigo-450 animate-spin shrink-0" />
              <div className="space-y-0.5">
                <span className="block text-xs font-bold text-slate-200">Importação em Andamento</span>
                <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[11px] text-slate-500 font-medium">
                  <span>Job ID: #{activeJobId}</span>
                  <span>•</span>
                  <span className="text-indigo-400 font-semibold">{pollingJob ? getJobStatusLabel(pollingJob.status) : "Na fila..."}</span>
                  {pollingJob?.selected_language && (
                    <>
                      <span>•</span>
                      <span className="uppercase font-mono font-bold text-slate-450">{pollingJob.selected_language}</span>
                    </>
                  )}
                </div>
              </div>
            </div>
            {pollingJob?.reference_source_id && (
              <Link
                href={`/references/${pollingJob.reference_source_id}`}
                className="shrink-0 inline-flex items-center justify-center gap-1.5 rounded-lg border border-indigo-500/20 bg-indigo-600/10 hover:bg-indigo-600/20 hover:text-white px-3 py-1.5 text-xs font-bold text-indigo-400 transition-colors"
              >
                <span>Ver transcrição</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            )}
          </div>
        )}
      </div>

      {/* Main List Section */}
      <div className="space-y-4">

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
                    <tr
                      key={item.id}
                      onDoubleClick={() => router.push(`/references/${item.id}`)}
                      className="hover:bg-slate-900/25 transition-colors cursor-pointer select-none"
                      title="Duplo clique para visualizar detalhes"
                    >
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

      {/* Filters Modal */}
      {isFilterModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="relative w-full max-w-lg rounded-xl border border-slate-800 bg-[#0b101c] p-6 shadow-2xl animate-in zoom-in-95 duration-200">
            {/* Header */}
            <div className="flex items-center justify-between border-b border-slate-850 pb-4 mb-4">
              <h3 className="text-lg font-bold text-white flex items-center gap-2 font-sans">
                <SlidersHorizontal className="h-4.5 w-4.5 text-indigo-400" />
                Filtros e Ordenação
              </h3>
              <button
                type="button"
                onClick={() => setIsFilterModalOpen(false)}
                className="rounded-lg p-1.5 hover:bg-slate-900 text-slate-450 hover:text-slate-200 transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Body */}
            <div className="space-y-4">
              {/* Search Inputs */}
              <div className="space-y-3">
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-450 select-none">Busca por Texto</label>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
                  <input
                    type="text"
                    placeholder="Pesquisar por título ou conteúdo..."
                    value={searchText}
                    onChange={(e) => setSearchText(e.target.value)}
                    className="w-full rounded-lg border border-slate-800 bg-slate-950 pl-9 pr-3 py-2 text-sm text-slate-200 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/10 transition-all placeholder:text-slate-500 font-medium"
                  />
                </div>
                
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
                  <input
                    type="text"
                    placeholder="Filtrar por nome do canal..."
                    value={channelTitleFilter}
                    onChange={(e) => setChannelTitleFilter(e.target.value)}
                    className="w-full rounded-lg border border-slate-800 bg-slate-950 pl-9 pr-3 py-2 text-sm text-slate-200 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/10 transition-all placeholder:text-slate-500 font-medium"
                  />
                </div>
              </div>

              {/* Status and Type Selects */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-450 select-none">Status</label>
                  <select
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value)}
                    className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-300 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/10 transition-all font-semibold"
                  >
                    <option value="Todos">Todos</option>
                    <option value="transcribed">Transcrito</option>
                    <option value="needs_audio_transcription">Pendente de Áudio</option>
                    <option value="importing">Importando</option>
                    <option value="failed">Falhou</option>
                    <option value="archived">Arquivado</option>
                  </select>
                </div>

                <div className="space-y-1.5">
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-450 select-none">Tipo</label>
                  <select
                    value={sourceTypeFilter}
                    onChange={(e) => setSourceTypeFilter(e.target.value)}
                    className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-300 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/10 transition-all font-semibold"
                  >
                    <option value="Todos">Todos</option>
                    <option value="youtube_video">YouTube</option>
                    <option value="manual">Manual</option>
                  </select>
                </div>
              </div>

              {/* Sorting */}
              <div className="space-y-1.5">
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-450 select-none">Ordenar por</label>
                <div className="flex gap-2">
                  <select
                    value={sortField}
                    onChange={(e) => setSortField(e.target.value as any)}
                    className="flex-1 rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-300 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/10 transition-all font-semibold"
                  >
                    <option value="created_at">Data Cadastro</option>
                    <option value="published_at">Data Publicação</option>
                    <option value="view_count">Visualizações</option>
                    <option value="like_count">Likes</option>
                    <option value="duration_seconds">Duração</option>
                  </select>
                  <button
                    type="button"
                    onClick={() => setSortOrder(sortOrder === "asc" ? "desc" : "asc")}
                    className="h-9 px-3.5 rounded-lg border border-slate-800 bg-slate-950 text-xs font-bold text-slate-450 hover:text-slate-205 transition-colors uppercase font-mono select-none"
                  >
                    {sortOrder === "asc" ? "ASC" : "DESC"}
                  </button>
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="flex items-center justify-between border-t border-slate-850 pt-4 mt-6">
              <button
                type="button"
                onClick={() => {
                  setSearchText("");
                  setChannelTitleFilter("");
                  setStatusFilter("Todos");
                  setSourceTypeFilter("Todos");
                  setSortField("created_at");
                  setSortOrder("desc");
                }}
                className="text-xs font-bold text-slate-500 hover:text-slate-300 transition-colors py-2 px-1 select-none"
              >
                Limpar Filtros
              </button>
              
              <button
                type="button"
                onClick={() => setIsFilterModalOpen(false)}
                className="rounded-lg bg-indigo-600 px-4 py-2 text-xs font-bold text-white shadow-md shadow-indigo-600/15 hover:bg-indigo-500 transition-all select-none"
              >
                Aplicar ({total} {total === 1 ? "fonte" : "fontes"})
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
