"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  getReferenceSource,
  getReferenceTranscripts,
  getTranscriptSegments,
  getReferenceImportJobs
} from "@/lib/api";
import {
  ReferenceSource,
  Transcript,
  TranscriptSegment,
  ReferenceImportJob
} from "@/lib/types";
import {
  ArrowLeft,
  Calendar,
  Clock,
  Eye,
  ThumbsUp,
  ExternalLink,
  Loader2,
  FileText,
  Clock as ClockIcon,
  Copy,
  ChevronDown,
  ChevronUp,
  AlertCircle,
  HelpCircle,
  CheckCircle,
  ListRestart
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

// Inline helper for formatting timestamps
function formatTimestamp(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined) return "00:00";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (h > 0) {
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  }
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
}

export default function ReferenceDetailPage() {
  const { id } = useParams();
  const sourceId = parseInt(Array.isArray(id) ? id[0] : id || "0");

  const [source, setSource] = useState<ReferenceSource | null>(null);
  const [transcripts, setTranscripts] = useState<Transcript[]>([]);
  const [selectedTranscript, setSelectedTranscript] = useState<Transcript | null>(null);
  const [segments, setSegments] = useState<TranscriptSegment[]>([]);
  const [jobs, setJobs] = useState<ReferenceImportJob[]>([]);

  // UI state
  const [loading, setLoading] = useState(true);
  const [loadingSegments, setLoadingSegments] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showRawMetadata, setShowRawMetadata] = useState(false);
  const [activeTab, setActiveTab] = useState<"text" | "segments" | "jobs">("text");

  // Load data
  useEffect(() => {
    if (!sourceId) return;

    const loadAllData = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // Fetch reference source
        const srcData = await getReferenceSource(sourceId);
        setSource(srcData);

        // Fetch transcripts
        const transList = await getReferenceTranscripts(sourceId);
        setTranscripts(transList);
        
        if (transList.length > 0) {
          setSelectedTranscript(transList[0]);
          loadSegments(transList[0].id);
        }

        // Fetch jobs history
        const jobsList = await getReferenceImportJobs(sourceId);
        setJobs(jobsList);

      } catch (err: any) {
        setError(err.message || "Erro ao carregar detalhes da referência.");
      } finally {
        setLoading(false);
      }
    };

    loadAllData();
  }, [sourceId]);

  // Load segments for a transcript
  const loadSegments = async (transcriptId: number) => {
    try {
      setLoadingSegments(true);
      const segs = await getTranscriptSegments(transcriptId);
      setSegments(segs);
    } catch {
      toast.error("Não foi possível carregar os segmentos com timestamps.");
    } finally {
      setLoadingSegments(false);
    }
  };

  // Copy helpers
  const handleCopyCleanText = () => {
    if (!selectedTranscript) return;
    navigator.clipboard.writeText(selectedTranscript.full_text);
    toast.success("Texto limpo copiado com sucesso!");
  };

  const handleCopyTimestampsText = () => {
    if (segments.length === 0) {
      toast.error("Nenhum segmento disponível para copiar.");
      return;
    }

    const formatted = segments
      .map(
        seg =>
          `[${formatTimestamp(seg.start_time)} - ${formatTimestamp(seg.end_time)}] ${
            seg.speaker ? `${seg.speaker}: ` : ""
          }${seg.text}`
      )
      .join("\n");

    navigator.clipboard.writeText(formatted);
    toast.success("Transcrição com timestamps copiada com sucesso!");
  };

  const getStatusBadge = (status: string) => {
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
        return "bg-slate-500/10 text-slate-450 border-slate-500/20";
      default:
        return "bg-indigo-500/10 text-indigo-400 border-indigo-500/20";
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case "transcribed": return "Transcrito";
      case "importing": return "Importando...";
      case "needs_audio_transcription": return "Pendente de Áudio";
      case "failed": return "Falhou";
      case "archived": return "Arquivado";
      default: return status;
    }
  };

  if (loading) {
    return (
      <div className="flex h-[80vh] flex-col items-center justify-center gap-3">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
        <span className="text-sm text-slate-400 font-medium">Carregando detalhes da referência...</span>
      </div>
    );
  }

  if (error || !source) {
    return (
      <div className="space-y-6">
        <Link
          href="/references"
          className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-slate-200 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>Voltar para Referências</span>
        </Link>
        <div className="rounded-xl border border-rose-950 bg-rose-950/20 p-5 text-rose-250 flex items-center gap-3">
          <AlertCircle className="h-5 w-5 text-rose-450 shrink-0" />
          <span className="text-sm">{error || "Referência não encontrada."}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Back button */}
      <div>
        <Link
          href="/references"
          className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-slate-200 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>Voltar para Referências</span>
        </Link>
      </div>

      {/* Main Metadata Grid Card */}
      <div className="rounded-xl border border-slate-800 bg-[#0b101c]/35 p-6 backdrop-blur-sm shadow-md">
        <div className="flex flex-col gap-6 md:flex-row md:items-start">
          {/* Thumbnail */}
          {source.thumbnail_url ? (
            <div className="relative h-40 w-full md:w-64 rounded-lg overflow-hidden border border-slate-800 shrink-0 bg-slate-950 shadow-inner">
              <img
                src={source.thumbnail_url}
                alt=""
                className="h-full w-full object-cover"
              />
              <span className="absolute bottom-2 right-2 rounded bg-slate-950/80 px-1.5 py-0.5 text-[10px] font-mono text-slate-350 font-bold border border-slate-900">
                {formatDuration(source.duration_seconds)}
              </span>
            </div>
          ) : (
            <div className="h-40 w-full md:w-64 rounded-lg border border-slate-800 bg-slate-950 shrink-0 flex items-center justify-center text-slate-600">
              <FileText className="h-8 w-8" />
            </div>
          )}

          {/* Details */}
          <div className="flex-1 space-y-4">
            <div className="space-y-2">
              <div className="flex flex-wrap items-center gap-3">
                <span className={cn("inline-flex items-center rounded px-2.5 py-0.5 text-[10px] font-bold border tracking-wide uppercase shadow-sm", getStatusBadge(source.status))}>
                  {getStatusLabel(source.status)}
                </span>
                {source.language && (
                  <span className="rounded bg-slate-900 border border-slate-800/80 px-2 py-0.5 text-[10px] font-mono font-bold text-slate-400 uppercase">
                    Idioma: {source.language}
                  </span>
                )}
              </div>
              
              <h2 className="text-xl font-bold text-white md:text-2xl select-text leading-tight">{source.title}</h2>
              <p className="text-sm font-semibold text-indigo-400">{source.channel_title || "Canal desconhecido"}</p>
            </div>

            {/* Video Stats */}
            <div className="flex flex-wrap gap-x-6 gap-y-2 text-xs text-slate-400 pt-1 border-t border-slate-800/50">
              <div className="flex items-center gap-1.5">
                <Eye className="h-4 w-4 text-slate-500" />
                <span><strong className="text-slate-300">{formatViews(source.view_count)}</strong> visualizações</span>
              </div>
              <div className="flex items-center gap-1.5">
                <ThumbsUp className="h-4 w-4 text-slate-500" />
                <span><strong className="text-slate-300">{formatViews(source.like_count)}</strong> likes</span>
              </div>
              <div className="flex items-center gap-1.5">
                <Calendar className="h-4 w-4 text-slate-500" />
                <span>Publicado {formatRelativeTime(source.published_at)}</span>
              </div>
            </div>

            <div className="pt-2">
              <a
                href={source.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 rounded-lg border border-slate-800 bg-slate-950/50 px-3 py-1.5 text-xs font-semibold text-slate-300 hover:bg-slate-900 hover:text-white transition-colors"
              >
                <span>Abrir vídeo original</span>
                <ExternalLink className="h-3.5 w-3.5" />
              </a>
            </div>
          </div>
        </div>

        {/* Collapsible raw metadata */}
        {source.raw_json && (
          <div className="mt-6 pt-5 border-t border-slate-800/50">
            <button
              onClick={() => setShowRawMetadata(!showRawMetadata)}
              className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-slate-400 hover:text-slate-200 transition-colors"
            >
              {showRawMetadata ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              <span>Metadados Brutos (raw JSON)</span>
            </button>
            
            {showRawMetadata && (
              <div className="mt-3 rounded-lg border border-slate-900 bg-slate-950 p-4 overflow-x-auto">
                <pre className="text-[11px] font-mono text-slate-450 leading-relaxed max-h-60 overflow-y-auto select-text">
                  {JSON.stringify(source.raw_json, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Warning/Info Banners based on status */}
      {source.status === "needs_audio_transcription" && (
        <div className="rounded-xl border border-amber-950 bg-amber-950/20 p-5 text-amber-200/90 shadow">
          <div className="flex items-start gap-3">
            <HelpCircle className="h-5.5 w-5.5 text-amber-400 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <h4 className="font-bold text-white">Pendente de transcrição por áudio</h4>
              <p className="text-xs text-amber-350 max-w-2xl leading-relaxed">
                Este vídeo não possui legendas manuais ou automáticas disponíveis nos idiomas preferidos. 
                Nas etapas futuras do projeto, o áudio deste vídeo poderá ser extraído e transcrito automaticamente via inteligência artificial (Whisper/Audio-to-Text).
              </p>
            </div>
          </div>
        </div>
      )}

      {source.status === "failed" && (
        <div className="rounded-xl border border-rose-950 bg-rose-950/20 p-5 text-rose-250 shadow">
          <div className="flex items-start gap-3">
            <AlertCircle className="h-5.5 w-5.5 text-rose-450 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <h4 className="font-bold text-white font-sans">Falha crítica no processamento</h4>
              <p className="text-xs text-rose-350 max-w-2xl leading-relaxed">
                Não foi possível processar este vídeo. Verifique se o vídeo não é privado, restrito para menores ou se foi excluído pelo uploader.
                Consulte o histórico de jobs abaixo para obter mais detalhes.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Description card */}
      {source.description && (
        <div className="rounded-xl border border-slate-800 bg-[#0b101c]/15 p-6 space-y-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">Descrição do YouTube</h3>
          <p className="text-xs text-slate-350 whitespace-pre-wrap leading-relaxed select-text max-h-48 overflow-y-auto pr-1">
            {source.description}
          </p>
        </div>
      )}

      {/* Transcript Visualizer section */}
      <div className="space-y-4">
        {/* Navigation Tabs */}
        <div className="flex border-b border-slate-800">
          <button
            onClick={() => setActiveTab("text")}
            className={cn(
              "px-5 py-3 text-xs font-bold uppercase tracking-wider border-b-2 transition-all",
              activeTab === "text"
                ? "border-indigo-500 text-white"
                : "border-transparent text-slate-400 hover:text-slate-200"
            )}
          >
            Texto Completo
          </button>
          <button
            onClick={() => setActiveTab("segments")}
            className={cn(
              "px-5 py-3 text-xs font-bold uppercase tracking-wider border-b-2 transition-all",
              activeTab === "segments"
                ? "border-indigo-500 text-white"
                : "border-transparent text-slate-400 hover:text-slate-200"
            )}
          >
            Segmentos / Timestamps
          </button>
          <button
            onClick={() => setActiveTab("jobs")}
            className={cn(
              "px-5 py-3 text-xs font-bold uppercase tracking-wider border-b-2 transition-all",
              activeTab === "jobs"
                ? "border-indigo-500 text-white"
                : "border-transparent text-slate-400 hover:text-slate-200"
            )}
          >
            Histórico de Jobs ({jobs.length})
          </button>
        </div>

        {/* Tab contents */}
        {activeTab === "text" && (
          <div className="space-y-4">
            {selectedTranscript ? (
              <div className="rounded-xl border border-slate-800 bg-[#0b101c]/25 p-6 backdrop-blur-sm space-y-4">
                {/* Copy actions */}
                <div className="flex justify-end gap-2.5">
                  <button
                    onClick={handleCopyCleanText}
                    className="flex items-center gap-1.5 rounded bg-indigo-600 hover:bg-indigo-500 px-3 py-1.5 text-xs font-semibold text-white shadow transition-colors"
                  >
                    <Copy className="h-3.5 w-3.5" />
                    <span>Copiar Texto Limpo</span>
                  </button>
                </div>

                <div className="text-sm text-slate-300 leading-relaxed whitespace-pre-wrap select-text max-h-[60vh] overflow-y-auto bg-slate-950/20 border border-slate-900 rounded-lg p-5">
                  {selectedTranscript.full_text}
                </div>
              </div>
            ) : (
              <div className="rounded-xl border border-dashed border-slate-800 bg-slate-950/10 py-12 text-center text-slate-500 font-medium">
                Nenhuma transcrição disponível para esta fonte.
              </div>
            )}
          </div>
        )}

        {activeTab === "segments" && (
          <div className="space-y-4">
            {selectedTranscript && segments.length > 0 ? (
              <div className="rounded-xl border border-slate-800 bg-[#0b101c]/25 p-6 backdrop-blur-sm space-y-4">
                <div className="flex justify-end gap-2.5">
                  <button
                    onClick={handleCopyTimestampsText}
                    className="flex items-center gap-1.5 rounded bg-indigo-600 hover:bg-indigo-500 px-3 py-1.5 text-xs font-semibold text-white shadow transition-colors"
                  >
                    <Copy className="h-3.5 w-3.5" />
                    <span>Copiar com Timestamps</span>
                  </button>
                </div>

                {loadingSegments ? (
                  <div className="flex justify-center py-12">
                    <Loader2 className="h-6 w-6 animate-spin text-slate-500" />
                  </div>
                ) : (
                  <div className="max-h-[60vh] overflow-y-auto space-y-3 border border-slate-900 rounded-lg p-4 bg-slate-950/20">
                    {segments.map((seg) => (
                      <div
                        key={seg.id}
                        className="group flex flex-col sm:flex-row sm:items-start gap-2 sm:gap-4 p-2.5 rounded border border-transparent hover:border-slate-850 hover:bg-slate-900/30 transition-all text-xs"
                      >
                        {/* Timestamp */}
                        <div className="flex items-center gap-1 shrink-0 font-mono font-bold text-indigo-400 bg-indigo-500/5 px-2 py-0.5 rounded border border-indigo-500/10 h-fit w-fit select-none">
                          <ClockIcon className="h-3 w-3 text-indigo-500" />
                          <span>{formatTimestamp(seg.start_time)}</span>
                        </div>

                        {/* Segment Text */}
                        <div className="flex-1 space-y-1 select-text">
                          {seg.speaker && (
                            <span className="block font-bold text-slate-400">{seg.speaker}:</span>
                          )}
                          <p className="text-slate-350 leading-relaxed font-medium">{seg.text}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <div className="rounded-xl border border-dashed border-slate-800 bg-slate-950/10 py-12 text-center text-slate-500 font-medium">
                Nenhum segmento com timestamp disponível.
              </div>
            )}
          </div>
        )}

        {activeTab === "jobs" && (
          <div className="space-y-4">
            {jobs.length === 0 ? (
              <div className="rounded-xl border border-slate-900 bg-slate-950/20 py-12 text-center text-xs text-slate-500 font-medium">
                Nenhum log de job registrado para esta fonte.
              </div>
            ) : (
              <div className="rounded-xl border border-slate-800 bg-[#0b101c]/25 backdrop-blur-sm overflow-hidden flex flex-col">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs text-slate-300">
                    <thead className="bg-[#0c1223] text-[10px] font-bold uppercase tracking-wider text-slate-400 border-b border-slate-800">
                      <tr>
                        <th className="px-5 py-3">Iniciado Em</th>
                        <th className="px-5 py-3">Finalizado Em</th>
                        <th className="px-5 py-3">Status</th>
                        <th className="px-5 py-3">Método</th>
                        <th className="px-5 py-3">Idioma</th>
                        <th className="px-5 py-3">Legenda</th>
                        <th className="px-5 py-3">Logs de Erro</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-900/50">
                      {jobs.map((job) => {
                        const statusColors: Record<string, string> = {
                          completed: "text-emerald-400",
                          failed: "text-rose-450",
                          needs_audio_transcription: "text-amber-400",
                          running: "text-blue-400",
                          queued: "text-slate-400"
                        };

                        const jobStatusLabels: Record<string, string> = {
                          completed: "Sucesso",
                          failed: "Falhou",
                          needs_audio_transcription: "Pendente de Áudio",
                          running: "Executando...",
                          queued: "Na Fila"
                        };

                        return (
                          <tr key={job.id} className="hover:bg-slate-900/30">
                            <td className="px-5 py-3 font-mono text-[11px] text-slate-400">
                              {formatDate(job.created_at)}
                            </td>
                            <td className="px-5 py-3 font-mono text-[11px] text-slate-500">
                              {job.finished_at ? formatDate(job.finished_at) : "-"}
                            </td>
                            <td className="px-5 py-3">
                              <span className={cn("font-bold", statusColors[job.status] || "text-slate-400")}>
                                {jobStatusLabels[job.status] || job.status}
                              </span>
                            </td>
                            <td className="px-5 py-3 font-mono text-[10px] text-slate-400 uppercase">
                              {job.method}
                            </td>
                            <td className="px-5 py-3 font-mono text-slate-300 font-semibold uppercase">
                              {job.selected_language || "-"}
                            </td>
                            <td className="px-5 py-3 text-slate-450 capitalize">
                              {job.selected_caption_type?.replace("_", " ") || "-"}
                            </td>
                            <td className="px-5 py-3 text-rose-400 max-w-[200px] truncate" title={job.error_message || ""}>
                              {job.error_message || "-"}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
