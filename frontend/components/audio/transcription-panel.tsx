"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, ChevronDown, ChevronUp, Loader2, Upload } from "lucide-react";
import { toast } from "sonner";
import { speechApi } from "@/lib/speech-api";
import type { SpeechCapabilities, SpeechJob, SttUploadOptions } from "@/lib/speech-types";
import { TranscriptionResult } from "@/components/audio/transcription-result";

const ACCEPT = ".mp3,.wav,.mp4,.mkv,.mov,.m4a,.webm";
const EXPORT_FORMATS = ["txt", "json", "srt", "vtt"] as const;
const TERMINAL = new Set(["completed", "failed", "cancelled"]);

export function TranscriptionPanel() {
  const [files, setFiles] = useState<File[]>([]);
  const [jobs, setJobs] = useState<SpeechJob[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<number | null>(null);
  const [capabilities, setCapabilities] = useState<SpeechCapabilities | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [advanced, setAdvanced] = useState(false);
  const [options, setOptions] = useState<SttUploadOptions>({
    preset: "balanced",
    language: "pt",
    diarization: false,
    quiet_speech: false,
    export_formats: ["txt", "json", "srt", "vtt"],
    device: "auto",
    compute_type: "int8",
  });

  useEffect(() => {
    speechApi.getCapabilities().then(setCapabilities).catch(() => undefined);
  }, []);

  const hasActiveJobs = jobs.some((item) => !TERMINAL.has(item.status));
  useEffect(() => {
    if (!hasActiveJobs) return;
    let cancelled = false;
    const refresh = async () => {
      const current = await Promise.all(jobs.map(async (item) => {
        if (TERMINAL.has(item.status)) return item;
        try { return await speechApi.getJob(item.id); }
        catch { return item; }
      }));
      if (!cancelled) setJobs(current);
    };
    void refresh();
    const timer = setInterval(refresh, 2500);
    return () => { cancelled = true; clearInterval(timer); };
  }, [hasActiveJobs, jobs.map((item) => `${item.id}:${item.status}`).join("|")]);

  const selectedJob = useMemo(
    () => jobs.find((item) => item.id === selectedJobId) || jobs[0] || null,
    [jobs, selectedJobId],
  );

  const caps = capabilities?.capabilities || {};
  const cudaAvailable = Boolean(caps.cuda_available);
  const diarizationReady = Boolean(caps.diarization_ready);

  const submit = async () => {
    if (!files.length) return;
    setSubmitting(true);
    const created: SpeechJob[] = [];
    const failures: string[] = [];
    for (const file of files) {
      try {
        created.push(await speechApi.uploadStt(file, options));
      } catch (e: any) {
        failures.push(`${file.name}: ${e.message}`);
      }
    }
    if (created.length) {
      setJobs(created);
      setSelectedJobId(created[0].id);
      toast.success(created.length === 1 ? "Transcrição adicionada à fila" : `${created.length} transcrições adicionadas à fila`);
    }
    if (failures.length) {
      toast.error(`${failures.length} arquivo(s) não puderam ser enfileirados`, { description: failures.slice(0, 3).join(" · ") });
    }
    setSubmitting(false);
  };

  const setNumber = (key: keyof SttUploadOptions, raw: string) => setOptions((old) => ({ ...old, [key]: raw === "" ? undefined : Number(raw) }));
  const toggleFormat = (format: string) => setOptions((old) => {
    const current = old.export_formats || [];
    const next = current.includes(format) ? current.filter((item) => item !== format) : [...current, format];
    return { ...old, export_formats: next };
  });

  return (
    <div className="space-y-5">
      <div className="rounded-xl border border-slate-800 bg-[#0b101c]/60 p-5">
        {capabilities && !capabilities.worker_online && <div className="mb-4 flex gap-2 rounded-lg border border-amber-900/40 bg-amber-950/20 p-3 text-xs text-amber-300"><AlertTriangle className="h-4 w-4 shrink-0" />O speech worker está offline. Os jobs podem ser criados, mas ficarão na fila até um worker compatível voltar.</div>}
        <div className="grid gap-4 lg:grid-cols-[1.2fr_1fr]">
          <label className="flex min-h-32 cursor-pointer flex-col items-center justify-center rounded-xl border border-dashed border-slate-700 bg-slate-950/60 p-5 text-center hover:border-indigo-500">
            <Upload className="mb-2 h-6 w-6 text-indigo-400" />
            <span className="text-sm font-medium text-white">{files.length ? (files.length === 1 ? files[0].name : `${files.length} arquivos selecionados`) : "Escolher áudio ou vídeo"}</span>
            <span className="mt-1 text-xs text-slate-500">MP3, WAV, MP4, MKV, MOV, M4A ou WEBM · seleção múltipla suportada</span>
            <input type="file" multiple accept={ACCEPT} className="hidden" onChange={(e) => setFiles(Array.from(e.target.files || []))} />
          </label>

          <div className="grid gap-3 sm:grid-cols-2">
            <label className="text-xs text-slate-400">Preset<select value={options.preset} onChange={(e) => setOptions((o) => ({ ...o, preset: e.target.value }))} className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white"><option value="fast">Rápido</option><option value="balanced">Balanceado</option><option value="maximum_quality">Máxima qualidade</option></select></label>
            <label className="text-xs text-slate-400">Idioma<input value={options.language || ""} onChange={(e) => setOptions((o) => ({ ...o, language: e.target.value }))} placeholder="pt" className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white" /></label>
            <label className="flex items-center gap-2 text-sm text-slate-300"><input type="checkbox" checked={options.diarization} onChange={(e) => setOptions((o) => ({ ...o, diarization: e.target.checked }))} /> Identificar speakers</label>
            <label className="flex items-center gap-2 text-sm text-slate-300"><input type="checkbox" checked={options.quiet_speech} onChange={(e) => setOptions((o) => ({ ...o, quiet_speech: e.target.checked }))} /> Fala baixa/sensível</label>
          </div>
        </div>

        {files.length > 1 && <div className="mt-3 max-h-28 overflow-auto rounded-lg border border-slate-800 bg-slate-950/50 p-2 text-xs text-slate-400">{files.map((file) => <div key={`${file.name}:${file.size}`} className="truncate py-0.5">{file.name}</div>)}</div>}

        {options.diarization && !diarizationReady && capabilities?.worker_online && <div className="mt-3 rounded-lg border border-amber-900/40 bg-amber-950/20 p-3 text-xs text-amber-300">O worker atual não informa diarização pronta. Verifique WhisperX/pyannote e o acesso Hugging Face no Diagnóstico.</div>}

        {options.diarization && (
          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            <label className="text-xs text-slate-400">Speakers exatos<input type="number" min={1} value={options.num_speakers ?? ""} onChange={(e) => setNumber("num_speakers", e.target.value)} className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white" /></label>
            <label className="text-xs text-slate-400">Mínimo<input type="number" min={1} value={options.min_speakers ?? ""} onChange={(e) => setNumber("min_speakers", e.target.value)} className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white" /></label>
            <label className="text-xs text-slate-400">Máximo<input type="number" min={1} value={options.max_speakers ?? ""} onChange={(e) => setNumber("max_speakers", e.target.value)} className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white" /></label>
          </div>
        )}

        <div className="mt-4 grid gap-3 lg:grid-cols-[1fr_220px]">
          <label className="block text-xs text-slate-400">Prompt inicial<textarea value={options.initial_prompt || ""} onChange={(e) => setOptions((o) => ({ ...o, initial_prompt: e.target.value }))} rows={2} placeholder="Vocabulário, nomes próprios ou contexto opcional..." className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white" /></label>
          <label className="text-xs text-slate-400">Vincular à Biblioteca (ID)<input type="number" min={1} value={options.reference_source_id ?? ""} onChange={(e) => setNumber("reference_source_id", e.target.value)} placeholder="Opcional" className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white" /><span className="mt-1 block text-[10px] text-slate-600">Em lote, todos os arquivos usam a mesma referência quando este ID é informado.</span></label>
        </div>

        <div className="mt-4"><div className="text-xs text-slate-400">Arquivos de saída</div><div className="mt-2 flex flex-wrap gap-3">{EXPORT_FORMATS.map((format) => <label key={format} className="flex items-center gap-2 text-sm text-slate-300"><input type="checkbox" checked={(options.export_formats || []).includes(format)} onChange={() => toggleFormat(format)} /> {format.toUpperCase()}</label>)}</div>{(options.export_formats || []).length === 0 && <p className="mt-1 text-xs text-rose-300">Selecione pelo menos um formato.</p>}</div>

        <button onClick={() => setAdvanced((v) => !v)} className="mt-4 flex items-center gap-2 text-xs font-medium text-indigo-300">{advanced ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />} Opções avançadas</button>
        {advanced && (
          <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <label className="text-xs text-slate-400">Modelo<input value={options.model || ""} onChange={(e) => setOptions((o) => ({ ...o, model: e.target.value || undefined }))} placeholder="medium" className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white" /></label>
            <label className="text-xs text-slate-400">Device<select value={options.device || "auto"} onChange={(e) => setOptions((o) => ({ ...o, device: e.target.value as any }))} className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white"><option value="auto">Auto</option><option value="cpu">CPU</option><option value="cuda" disabled={capabilities?.worker_online && !cudaAvailable}>CUDA{capabilities?.worker_online && !cudaAvailable ? " (indisponível)" : ""}</option></select></label>
            <label className="text-xs text-slate-400">Compute<select value={options.compute_type || "int8"} onChange={(e) => setOptions((o) => ({ ...o, compute_type: e.target.value as any }))} className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white"><option value="int8">int8</option><option value="float16" disabled={capabilities?.worker_online && !cudaAvailable}>float16</option><option value="float32">float32</option></select></label>
            <label className="text-xs text-slate-400">Batch<input type="number" min={1} value={options.batch_size ?? ""} onChange={(e) => setNumber("batch_size", e.target.value)} className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white" /></label>
            <label className="text-xs text-slate-400">VAD onset<input type="number" step="0.01" min={0} max={1} value={options.vad_onset ?? ""} onChange={(e) => setNumber("vad_onset", e.target.value)} className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white" /></label>
            <label className="text-xs text-slate-400">VAD offset<input type="number" step="0.01" min={0} max={1} value={options.vad_offset ?? ""} onChange={(e) => setNumber("vad_offset", e.target.value)} className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white" /></label>
            <label className="text-xs text-slate-400">Chunk (s)<input type="number" min={5} value={options.chunk_size ?? ""} onChange={(e) => setNumber("chunk_size", e.target.value)} className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white" /></label>
            <label className="text-xs text-slate-400">Modelo diarização<input value={options.diarize_model || ""} onChange={(e) => setOptions((o) => ({ ...o, diarize_model: e.target.value || undefined }))} placeholder="pyannote/..." className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white" /></label>
            <label className="text-xs text-slate-400 lg:col-span-2">Cache de modelos<input value={options.cache_dir || ""} onChange={(e) => setOptions((o) => ({ ...o, cache_dir: e.target.value || undefined }))} placeholder="Opcional; caminho no worker" className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white" /></label>
            <label className="flex items-end gap-2 pb-2 text-sm text-slate-300"><input type="checkbox" checked={options.offline || false} onChange={(e) => setOptions((o) => ({ ...o, offline: e.target.checked }))} /> Offline</label>
          </div>
        )}

        <div className="mt-5 flex items-center justify-between gap-4">
          <p className="text-xs text-slate-600">Cada arquivo selecionado vira um job durável independente; a extensão no navegador é só conveniência e o servidor valida cada upload.</p>
          <button onClick={submit} disabled={!files.length || submitting || (options.export_formats || []).length === 0} className="flex items-center gap-2 rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-40">{submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : null} {files.length > 1 ? `Transcrever ${files.length} arquivos` : "Transcrever"}</button>
        </div>
      </div>

      {jobs.length > 1 && <div className="rounded-xl border border-slate-800 bg-[#0b101c]/40 p-4"><div className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-500">Lote atual</div><div className="flex flex-wrap gap-2">{jobs.map((item, index) => <button key={item.id} onClick={() => setSelectedJobId(item.id)} className={`rounded-lg border px-3 py-2 text-xs ${selectedJob?.id === item.id ? "border-indigo-500 bg-indigo-950/30 text-indigo-200" : "border-slate-800 text-slate-400"}`}>#{item.id} · {files[index]?.name || "arquivo"} · {item.status} {item.progress_percent}%</button>)}</div></div>}

      {selectedJob && (
        <div className="space-y-4 rounded-xl border border-slate-800 bg-[#0b101c]/40 p-5">
          <div className="flex items-center justify-between gap-3"><div><div className="text-xs text-slate-500">Job #{selectedJob.id}</div><div className="text-sm font-medium text-white">{selectedJob.stage}</div></div><div className="text-sm text-indigo-300">{selectedJob.progress_percent}%</div></div>
          <div className="h-2 overflow-hidden rounded-full bg-slate-900"><div className="h-full bg-indigo-500 transition-all" style={{ width: `${selectedJob.progress_percent}%` }} /></div>
          {selectedJob.progress_message && <p className="text-xs text-slate-400">{selectedJob.progress_message}</p>}
          {selectedJob.status === "failed" && <div className="rounded-lg border border-rose-900/50 bg-rose-950/20 p-3 text-sm text-rose-300">{selectedJob.error_message || selectedJob.error_code || "Falha na transcrição"}</div>}
          <TranscriptionResult job={selectedJob} />
        </div>
      )}
    </div>
  );
}
