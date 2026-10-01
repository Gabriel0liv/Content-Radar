"use client";

import { useEffect, useState } from "react";
import { Archive, ArchiveX, Loader2, RefreshCw, RotateCcw, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { speechApi } from "@/lib/speech-api";
import type { SpeechArtifact, SpeechJob, SpeechOperation } from "@/lib/speech-types";

export function HistoryPanel() {
  const [jobs, setJobs] = useState<SpeechJob[]>([]);
  const [operation, setOperation] = useState<"all" | SpeechOperation>("all");
  const [status, setStatus] = useState("all");
  const [loading, setLoading] = useState(true);
  const [bulkArchiving, setBulkArchiving] = useState(false);
  const [artifacts, setArtifacts] = useState<Record<number, SpeechArtifact[]>>({});

  const load = async () => {
    setLoading(true);
    try {
      const data = await speechApi.listJobs({
        operation: operation === "all" ? undefined : operation,
        status: status === "all" ? undefined : status,
        limit: 100,
      });
      setJobs(data);
    } catch (e: any) {
      toast.error("Falha ao carregar histórico", { description: e.message });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, [operation, status]);

  const showArtifacts = async (jobId: number) => {
    try {
      const items = await speechApi.listArtifacts(jobId);
      setArtifacts((old) => ({ ...old, [jobId]: items }));
    } catch (e: any) {
      toast.error("Falha ao carregar artefatos", { description: e.message });
    }
  };

  const retry = async (jobId: number) => {
    try { await speechApi.retryJob(jobId); toast.success("Novo job criado"); await load(); } catch (e: any) { toast.error("Falha ao repetir", { description: e.message }); }
  };

  const archive = async (jobId: number) => {
    try { await speechApi.archiveJob(jobId); toast.success("Job arquivado"); await load(); } catch (e: any) { toast.error("Falha ao arquivar", { description: e.message }); }
  };

  const archiveVisible = async () => {
    const safeJobs = jobs.filter((job) => job.status !== "queued" && job.status !== "running");
    if (!safeJobs.length) return;
    if (!window.confirm(`Arquivar ${safeJobs.length} job(s) exibidos? Arquivar não apaga transcrições nem arquivos gerados.`)) return;
    setBulkArchiving(true);
    try {
      const results = await Promise.allSettled(safeJobs.map((job) => speechApi.archiveJob(job.id)));
      const failed = results.filter((item) => item.status === "rejected").length;
      if (failed) toast.error(`${failed} job(s) não puderam ser arquivados`);
      else toast.success(`${safeJobs.length} job(s) arquivados`);
      await load();
    } finally {
      setBulkArchiving(false);
    }
  };

  const removeArtifact = async (jobId: number, artifactId: number) => {
    if (!window.confirm("Excluir este arquivo gerado? Esta ação não apaga a transcrição da Biblioteca.")) return;
    try { await speechApi.deleteArtifact(jobId, artifactId); await showArtifacts(jobId); } catch (e: any) { toast.error("Falha ao excluir arquivo", { description: e.message }); }
  };

  const archivableCount = jobs.filter((job) => job.status !== "queued" && job.status !== "running").length;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <select value={operation} onChange={(e) => setOperation(e.target.value as any)} className="rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white"><option value="all">STT + TTS</option><option value="stt">STT</option><option value="tts">TTS</option></select>
        <select value={status} onChange={(e) => setStatus(e.target.value)} className="rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white"><option value="all">Todos os status</option><option value="queued">Na fila</option><option value="running">Executando</option><option value="completed">Concluído</option><option value="failed">Falhou</option><option value="cancelled">Cancelado</option></select>
        <button onClick={archiveVisible} disabled={!archivableCount || bulkArchiving} className="flex items-center gap-2 rounded-lg border border-slate-800 px-3 py-2 text-sm text-slate-400 hover:bg-slate-900 disabled:opacity-40"><ArchiveX className="h-4 w-4" /> {bulkArchiving ? "Arquivando..." : `Arquivar exibidos (${archivableCount})`}</button>
        <button onClick={load} className="ml-auto flex items-center gap-2 rounded-lg border border-slate-800 px-3 py-2 text-sm text-slate-300 hover:bg-slate-900"><RefreshCw className="h-4 w-4" /> Atualizar</button>
      </div>

      {loading ? <div className="flex h-40 items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-indigo-400" /></div> : jobs.length === 0 ? <div className="rounded-xl border border-dashed border-slate-800 py-16 text-center text-sm text-slate-500">Nenhum job encontrado.</div> : (
        <div className="space-y-3">
          {jobs.map((job) => (
            <div key={job.id} className="rounded-xl border border-slate-800 bg-[#0b101c]/55 p-4">
              <div className="flex flex-wrap items-center gap-3">
                <span className="rounded-md bg-slate-900 px-2 py-1 text-[11px] font-semibold uppercase text-indigo-300">{job.operation}</span>
                <div className="min-w-0 flex-1"><div className="text-sm font-medium text-white">Job #{job.id} · {job.stage}</div><div className="mt-0.5 text-xs text-slate-500">{new Date(job.created_at).toLocaleString("pt-BR")}</div></div>
                <span className="text-xs text-slate-400">{job.progress_percent}%</span>
                <button onClick={() => retry(job.id)} className="rounded-md border border-slate-700 p-2 text-slate-400 hover:bg-slate-800" title="Repetir"><RotateCcw className="h-3.5 w-3.5" /></button>
                <button onClick={() => archive(job.id)} disabled={job.status === "queued" || job.status === "running"} className="rounded-md border border-slate-700 p-2 text-slate-400 hover:bg-slate-800 disabled:opacity-30" title="Arquivar"><Archive className="h-3.5 w-3.5" /></button>
              </div>
              {job.error_message && <div className="mt-3 rounded-lg bg-rose-950/20 p-2.5 text-xs text-rose-300">{job.error_code ? `${job.error_code}: ` : ""}{job.error_message}</div>}
              <button onClick={() => showArtifacts(job.id)} className="mt-3 text-xs text-indigo-300 hover:text-indigo-200">Ver arquivos</button>
              {artifacts[job.id] && <div className="mt-3 flex flex-wrap gap-2">{artifacts[job.id].map((artifact) => <div key={artifact.id} className="flex items-center rounded-lg border border-slate-800 bg-slate-950"><a href={speechApi.artifactDownloadUrl(job.id, artifact.id)} className="px-3 py-2 text-xs text-slate-300 hover:text-white">{artifact.filename}</a><button onClick={() => removeArtifact(job.id, artifact.id)} className="border-l border-slate-800 p-2 text-slate-600 hover:text-rose-400"><Trash2 className="h-3.5 w-3.5" /></button></div>)}</div>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
