"use client";

import { useEffect, useRef, useState } from "react";
import { ChevronDown, ChevronUp, Loader2, Upload } from "lucide-react";
import { toast } from "sonner";
import { speechApi } from "@/lib/speech-api";
import type { SpeechJob, SttUploadOptions } from "@/lib/speech-types";
import { TranscriptionResult } from "@/components/audio/transcription-result";

const ACCEPT = ".mp3,.wav,.mp4,.mkv,.mov,.m4a,.webm";

export function TranscriptionPanel() {
  const [file, setFile] = useState<File | null>(null);
  const [job, setJob] = useState<SpeechJob | null>(null);
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
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current); }, []);

  const poll = (jobId: number) => {
    if (pollRef.current) clearInterval(pollRef.current);
    const run = async () => {
      try {
        const fresh = await speechApi.getJob(jobId);
        setJob(fresh);
        if (["completed", "failed", "cancelled"].includes(fresh.status) && pollRef.current) {
          clearInterval(pollRef.current);
          pollRef.current = null;
        }
      } catch {
        // transient API failures must not stop an active job
      }
    };
    void run();
    pollRef.current = setInterval(run, 2500);
  };

  const submit = async () => {
    if (!file) return;
    setSubmitting(true);
    try {
      const created = await speechApi.uploadStt(file, options);
      setJob(created);
      poll(created.id);
      toast.success("Transcrição adicionada à fila");
    } catch (e: any) {
      toast.error("Não foi possível iniciar a transcrição", { description: e.message });
    } finally {
      setSubmitting(false);
    }
  };

  const setNumber = (key: keyof SttUploadOptions, raw: string) => setOptions((old) => ({ ...old, [key]: raw === "" ? undefined : Number(raw) }));

  return (
    <div className="space-y-5">
      <div className="rounded-xl border border-slate-800 bg-[#0b101c]/60 p-5">
        <div className="grid gap-4 lg:grid-cols-[1.2fr_1fr]">
          <label className="flex min-h-32 cursor-pointer flex-col items-center justify-center rounded-xl border border-dashed border-slate-700 bg-slate-950/60 p-5 text-center hover:border-indigo-500">
            <Upload className="mb-2 h-6 w-6 text-indigo-400" />
            <span className="text-sm font-medium text-white">{file ? file.name : "Escolher áudio ou vídeo"}</span>
            <span className="mt-1 text-xs text-slate-500">MP3, WAV, MP4, MKV, MOV, M4A ou WEBM</span>
            <input type="file" accept={ACCEPT} className="hidden" onChange={(e) => setFile(e.target.files?.[0] || null)} />
          </label>

          <div className="grid gap-3 sm:grid-cols-2">
            <label className="text-xs text-slate-400">Preset<select value={options.preset} onChange={(e) => setOptions((o) => ({ ...o, preset: e.target.value }))} className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white"><option value="fast">Rápido</option><option value="balanced">Balanceado</option><option value="maximum_quality">Máxima qualidade</option></select></label>
            <label className="text-xs text-slate-400">Idioma<input value={options.language || ""} onChange={(e) => setOptions((o) => ({ ...o, language: e.target.value }))} placeholder="pt" className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white" /></label>
            <label className="flex items-center gap-2 text-sm text-slate-300"><input type="checkbox" checked={options.diarization} onChange={(e) => setOptions((o) => ({ ...o, diarization: e.target.checked }))} /> Identificar speakers</label>
            <label className="flex items-center gap-2 text-sm text-slate-300"><input type="checkbox" checked={options.quiet_speech} onChange={(e) => setOptions((o) => ({ ...o, quiet_speech: e.target.checked }))} /> Fala baixa/sensível</label>
          </div>
        </div>

        {options.diarization && (
          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            <label className="text-xs text-slate-400">Speakers exatos<input type="number" min={1} value={options.num_speakers ?? ""} onChange={(e) => setNumber("num_speakers", e.target.value)} className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white" /></label>
            <label className="text-xs text-slate-400">Mínimo<input type="number" min={1} value={options.min_speakers ?? ""} onChange={(e) => setNumber("min_speakers", e.target.value)} className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white" /></label>
            <label className="text-xs text-slate-400">Máximo<input type="number" min={1} value={options.max_speakers ?? ""} onChange={(e) => setNumber("max_speakers", e.target.value)} className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white" /></label>
          </div>
        )}

        <label className="mt-4 block text-xs text-slate-400">Prompt inicial<textarea value={options.initial_prompt || ""} onChange={(e) => setOptions((o) => ({ ...o, initial_prompt: e.target.value }))} rows={2} placeholder="Vocabulário, nomes próprios ou contexto opcional..." className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white" /></label>

        <button onClick={() => setAdvanced((v) => !v)} className="mt-4 flex items-center gap-2 text-xs font-medium text-indigo-300">{advanced ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />} Opções avançadas</button>
        {advanced && (
          <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <label className="text-xs text-slate-400">Modelo<input value={options.model || ""} onChange={(e) => setOptions((o) => ({ ...o, model: e.target.value || undefined }))} placeholder="medium" className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white" /></label>
            <label className="text-xs text-slate-400">Device<select value={options.device || "auto"} onChange={(e) => setOptions((o) => ({ ...o, device: e.target.value as any }))} className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white"><option value="auto">Auto</option><option value="cpu">CPU</option><option value="cuda">CUDA</option></select></label>
            <label className="text-xs text-slate-400">Compute<select value={options.compute_type || "int8"} onChange={(e) => setOptions((o) => ({ ...o, compute_type: e.target.value as any }))} className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white"><option value="int8">int8</option><option value="float16">float16</option><option value="float32">float32</option></select></label>
            <label className="text-xs text-slate-400">Batch<input type="number" min={1} value={options.batch_size ?? ""} onChange={(e) => setNumber("batch_size", e.target.value)} className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white" /></label>
            <label className="text-xs text-slate-400">VAD onset<input type="number" step="0.01" min={0} max={1} value={options.vad_onset ?? ""} onChange={(e) => setNumber("vad_onset", e.target.value)} className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white" /></label>
            <label className="text-xs text-slate-400">VAD offset<input type="number" step="0.01" min={0} max={1} value={options.vad_offset ?? ""} onChange={(e) => setNumber("vad_offset", e.target.value)} className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white" /></label>
            <label className="text-xs text-slate-400">Chunk (s)<input type="number" min={5} value={options.chunk_size ?? ""} onChange={(e) => setNumber("chunk_size", e.target.value)} className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white" /></label>
            <label className="flex items-end gap-2 pb-2 text-sm text-slate-300"><input type="checkbox" checked={options.offline || false} onChange={(e) => setOptions((o) => ({ ...o, offline: e.target.checked }))} /> Offline</label>
          </div>
        )}

        <div className="mt-5 flex items-center justify-between gap-4">
          <p className="text-xs text-slate-600">A extensão escolhida no navegador é apenas conveniência; o servidor valida o upload.</p>
          <button onClick={submit} disabled={!file || submitting || job?.status === "queued" || job?.status === "running"} className="flex items-center gap-2 rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-40">{submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : null} Transcrever</button>
        </div>
      </div>

      {job && (
        <div className="space-y-4 rounded-xl border border-slate-800 bg-[#0b101c]/40 p-5">
          <div className="flex items-center justify-between gap-3"><div><div className="text-xs text-slate-500">Job #{job.id}</div><div className="text-sm font-medium text-white">{job.stage}</div></div><div className="text-sm text-indigo-300">{job.progress_percent}%</div></div>
          <div className="h-2 overflow-hidden rounded-full bg-slate-900"><div className="h-full bg-indigo-500 transition-all" style={{ width: `${job.progress_percent}%` }} /></div>
          {job.progress_message && <p className="text-xs text-slate-400">{job.progress_message}</p>}
          {job.status === "failed" && <div className="rounded-lg border border-rose-900/50 bg-rose-950/20 p-3 text-sm text-rose-300">{job.error_message || job.error_code || "Falha na transcrição"}</div>}
          <TranscriptionResult job={job} />
        </div>
      )}
    </div>
  );
}
