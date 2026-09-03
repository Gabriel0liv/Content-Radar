"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { ExternalLink, FileText, Loader2, Play, RefreshCw, Search } from "lucide-react";
import { toast } from "sonner";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

type Source = {
  id: number;
  source_url: string;
  title: string;
  channel_title: string | null;
  thumbnail_url: string | null;
  view_count: number | null;
  duration_seconds: number | null;
  published_at: string | null;
  status: string;
  language: string | null;
  created_at: string;
};

type SourceList = { items: Source[]; total: number; limit: number; offset: number };
type ImportJob = { id: number; status: string; error_message?: string | null; reference_source_id?: number | null };

type TranscriptionMode = "auto" | "max_fidelity";

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail || `Erro HTTP ${response.status}`);
  }
  return response.json();
}

function formatDuration(value: number | null) {
  if (!value) return "-";
  const h = Math.floor(value / 3600);
  const m = Math.floor((value % 3600) / 60);
  const s = value % 60;
  return h ? `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}` : `${m}:${String(s).padStart(2, "0")}`;
}

function formatViews(value: number | null) {
  if (!value) return "-";
  return new Intl.NumberFormat("pt-BR", { notation: "compact", maximumFractionDigits: 1 }).format(value);
}

export default function ReferencesPage() {
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [url, setUrl] = useState("");
  const [mode, setMode] = useState<TranscriptionMode>("auto");
  const [allowAutoCaptions, setAllowAutoCaptions] = useState(true);
  const [importing, setImporting] = useState(false);
  const [activeJob, setActiveJob] = useState<ImportJob | null>(null);
  const pollRef = useRef<NodeJS.Timeout | null>(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams({ limit: "100", sort_by: "created_at", sort_order: "desc" });
      if (search.trim()) params.set("search", search.trim());
      const result = await api<SourceList>(`/reference-sources?${params}`);
      setSources(result.items);
    } catch (error: any) {
      toast.error("Erro ao carregar biblioteca", { description: error.message });
    } finally {
      setLoading(false);
    }
  }, [search]);

  useEffect(() => {
    const timer = setTimeout(load, 250);
    return () => clearTimeout(timer);
  }, [load]);

  useEffect(() => () => {
    if (pollRef.current) clearInterval(pollRef.current);
  }, []);

  const watchJob = (jobId: number) => {
    if (pollRef.current) clearInterval(pollRef.current);
    const poll = async () => {
      try {
        const job = await api<ImportJob>(`/reference-import-jobs/${jobId}`);
        setActiveJob(job);
        if (job.status === "completed") {
          if (pollRef.current) clearInterval(pollRef.current);
          toast.success("Transcrição pronta");
          setActiveJob(null);
          await load();
        } else if (job.status === "failed" || job.status === "needs_audio_transcription") {
          if (pollRef.current) clearInterval(pollRef.current);
          toast.error("Não foi possível concluir a transcrição", {
            description: job.error_message || "A transcrição por áudio não pôde ser concluída. Você pode tentar novamente.",
          });
          setActiveJob(null);
          await load();
        }
      } catch {
        // Mantém o polling: uma falha transitória da API não deve cancelar o job.
      }
    };
    void poll();
    pollRef.current = setInterval(poll, 3000);
  };

  const importVideo = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!url.trim()) return;
    setImporting(true);
    try {
      const result = await api<{ import_job_id: number }>("/reference-sources/import-youtube-url", {
        method: "POST",
        body: JSON.stringify({
          url: url.trim(),
          preferred_languages: ["pt", "pt-BR", "en"],
          allow_auto_captions: allowAutoCaptions,
          transcription_mode: mode,
        }),
      });
      setUrl("");
      toast.info(mode === "max_fidelity" ? "Transcrição de alta fidelidade iniciada" : "Importação iniciada");
      watchJob(result.import_job_id);
    } catch (error: any) {
      toast.error("Não foi possível importar", { description: error.message });
    } finally {
      setImporting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 border-b border-slate-800 pb-5 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight text-white">Biblioteca</h2>
          <p className="mt-1 text-sm text-slate-400">Guarde vídeos de referência e tenha o que foi dito neles com transcrição e timestamps.</p>
        </div>
        <button onClick={load} className="flex items-center gap-2 rounded-lg border border-slate-800 bg-[#0b101c] px-3 py-2 text-sm text-slate-300 hover:bg-slate-900"><RefreshCw className="h-4 w-4" /> Atualizar</button>
      </div>

      <form onSubmit={importVideo} className="space-y-4 rounded-xl border border-slate-800 bg-[#0b101c]/50 p-5">
        <div className="flex flex-col gap-3 lg:flex-row">
          <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="Cole o link de um vídeo ou Short do YouTube..." className="min-w-0 flex-1 rounded-lg border border-slate-800 bg-slate-950 px-3.5 py-2.5 text-sm text-white outline-none focus:border-indigo-500" />
          <select value={mode} onChange={(e) => setMode(e.target.value as TranscriptionMode)} className="rounded-lg border border-slate-800 bg-slate-950 px-3.5 py-2.5 text-sm text-slate-200 outline-none focus:border-indigo-500">
            <option value="auto">Rápido: legendas primeiro</option>
            <option value="max_fidelity">Máxima fidelidade: transcrever áudio</option>
          </select>
          <button disabled={importing || !!activeJob || !url.trim()} className="flex items-center justify-center gap-2 rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-40">
            {importing || activeJob ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />} Transcrever
          </button>
        </div>
        <label className="flex items-center gap-2 text-xs text-slate-400">
          <input type="checkbox" checked={allowAutoCaptions} onChange={(e) => setAllowAutoCaptions(e.target.checked)} className="h-4 w-4" />
          Permitir legenda automática do YouTube no modo rápido
        </label>
        <p className="text-xs text-slate-600">No modo rápido: legenda manual → legenda automática → áudio como fallback. Em máxima fidelidade, o áudio é transcrito diretamente.</p>
        {activeJob && <div className="flex items-center gap-2 rounded-lg border border-indigo-900/50 bg-indigo-950/20 px-3 py-2 text-xs text-indigo-300"><Loader2 className="h-3.5 w-3.5 animate-spin" /> Processando transcrição…</div>}
      </form>

      <div className="relative max-w-xl">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
        <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Pesquisar na biblioteca..." className="w-full rounded-lg border border-slate-800 bg-slate-950 py-2.5 pl-10 pr-4 text-sm text-slate-200 outline-none focus:border-indigo-500" />
      </div>

      {loading ? (
        <div className="flex h-48 items-center justify-center"><Loader2 className="h-7 w-7 animate-spin text-indigo-400" /></div>
      ) : sources.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-800 py-20 text-center text-slate-500">Sua biblioteca ainda está vazia.</div>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {sources.map((source) => (
            <article key={source.id} className="flex gap-4 rounded-xl border border-slate-800 bg-[#0b101c]/55 p-4">
              {source.thumbnail_url ? <img src={source.thumbnail_url} alt="" className="h-24 w-40 shrink-0 rounded-lg object-cover" /> : <div className="flex h-24 w-40 shrink-0 items-center justify-center rounded-lg bg-slate-900"><FileText className="h-6 w-6 text-slate-700" /></div>}
              <div className="min-w-0 flex-1">
                <div className="mb-1 flex items-center gap-2"><span className="rounded-full border border-slate-700 px-2 py-0.5 text-[10px] font-semibold text-slate-400">{source.status === "transcribed" ? "Transcrito" : source.status}</span>{source.language && <span className="text-[10px] text-slate-600">{source.language}</span>}</div>
                <Link href={`/references/${source.id}`} className="line-clamp-2 font-semibold text-white hover:text-indigo-300">{source.title}</Link>
                <p className="mt-1 truncate text-xs text-slate-500">{source.channel_title || "Canal desconhecido"}</p>
                <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-slate-600"><span>{formatViews(source.view_count)} views</span><span>{formatDuration(source.duration_seconds)}</span><a href={source.source_url} target="_blank" rel="noopener noreferrer" className="ml-auto flex items-center gap-1 text-slate-400 hover:text-white"><ExternalLink className="h-3.5 w-3.5" /> YouTube</a></div>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
