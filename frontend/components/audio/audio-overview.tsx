"use client";

import { useEffect, useState } from "react";
import { Activity, CheckCircle2, Cpu, Database, Loader2, Mic2, Volume2, XCircle } from "lucide-react";
import { speechApi } from "@/lib/speech-api";
import type { SpeechDashboard, SpeechStatus } from "@/lib/speech-types";

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB", "TB"];
  let value = bytes / 1024;
  let index = 0;
  while (value >= 1024 && index < units.length - 1) {
    value /= 1024;
    index += 1;
  }
  return `${value.toFixed(value >= 10 ? 1 : 2)} ${units[index]}`;
}

export function AudioOverview() {
  const [status, setStatus] = useState<SpeechStatus | null>(null);
  const [dashboard, setDashboard] = useState<SpeechDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([speechApi.getStatus(), speechApi.getDashboard()])
      .then(([nextStatus, nextDashboard]) => {
        setStatus(nextStatus);
        setDashboard(nextDashboard);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="flex h-48 items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-indigo-400" /></div>;
  if (error) return <div className="rounded-xl border border-rose-900/50 bg-rose-950/20 p-4 text-sm text-rose-300">{error}</div>;
  if (!status || !dashboard) return null;

  const caps = status.worker.capabilities || {};
  const ttsReady = Array.isArray(caps.tts_engines) && caps.tts_engines.some((item: any) => typeof item === "string" || item?.available);
  const runtimeCards = [
    { label: "Worker", value: status.worker.online ? "Online" : "Offline", icon: Activity },
    { label: "STT", value: caps.stt_ready ? "Pronto" : "Indisponível", icon: Mic2 },
    { label: "TTS", value: ttsReady ? "Pronto" : "Indisponível", icon: Volume2 },
    { label: "Dispositivo", value: caps.cuda_available ? (caps.gpu_name || "CUDA") : "CPU", icon: Cpu },
  ];
  const metricCards = [
    { label: "Transcrições hoje", value: dashboard.transcriptions_today, icon: Mic2 },
    { label: "Vozes hoje", value: dashboard.tts_today, icon: Volume2 },
    { label: "Jobs totais", value: dashboard.total_jobs, icon: Activity },
    { label: "Taxa de sucesso", value: `${dashboard.success_rate.toFixed(1)}%`, icon: CheckCircle2 },
    { label: "Vozes disponíveis", value: dashboard.available_voices, icon: Volume2 },
    { label: "Armazenamento", value: formatBytes(dashboard.storage_used_bytes), icon: Database },
  ];

  return (
    <div className="space-y-5">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {runtimeCards.map(({ label, value, icon: Icon }) => (
          <div key={label} className="rounded-xl border border-slate-800 bg-[#0b101c]/60 p-4">
            <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-slate-500"><Icon className="h-4 w-4" />{label}</div>
            <div className="mt-2 text-lg font-semibold text-white">{value}</div>
          </div>
        ))}
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        {metricCards.map(({ label, value, icon: Icon }) => (
          <div key={label} className="rounded-xl border border-slate-800 bg-[#0b101c]/45 p-4">
            <div className="flex items-center gap-2 text-[10px] uppercase tracking-wide text-slate-500"><Icon className="h-3.5 w-3.5" />{label}</div>
            <div className="mt-2 text-xl font-semibold text-white">{value}</div>
          </div>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="rounded-xl border border-slate-800 bg-[#0b101c]/60 p-5">
          <h3 className="font-semibold text-white">Fila</h3>
          <div className="mt-4 grid grid-cols-2 gap-3">
            <div className="rounded-lg bg-slate-950 p-3"><div className="text-xs text-slate-500">Aguardando</div><div className="mt-1 text-2xl font-semibold text-white">{dashboard.queue.queued}</div></div>
            <div className="rounded-lg bg-slate-950 p-3"><div className="text-xs text-slate-500">Executando</div><div className="mt-1 text-2xl font-semibold text-white">{dashboard.queue.running}</div></div>
          </div>
          <div className="mt-3 text-xs text-slate-500">Concluídos: {dashboard.jobs_completed} · Falhas: {dashboard.jobs_failed}</div>
        </div>

        <div className="rounded-xl border border-slate-800 bg-[#0b101c]/60 p-5 text-sm text-slate-400">
          <h3 className="font-semibold text-white">Runtime</h3>
          <div className="mt-3 grid grid-cols-2 gap-2">
            {[
              ["FFmpeg", caps.ffmpeg_available],
              ["WhisperX", caps.whisperx_available],
              ["eSpeak", caps.espeak_available],
              ["Diarização", caps.diarization_ready],
              ["HF Token", dashboard.system_health.hf_token_configured],
              ["CUDA", caps.cuda_available],
            ].map(([label, ok]) => (
              <div key={String(label)} className="flex items-center gap-1.5 rounded-lg bg-slate-950 px-2.5 py-2">
                {ok ? <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" /> : <XCircle className="h-3.5 w-3.5 text-slate-600" />}
                <span>{label}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-xl border border-slate-800 bg-[#0b101c]/60 p-5">
          <h3 className="font-semibold text-white">Job ativo</h3>
          {dashboard.active_job ? (
            <div className="mt-3">
              <div className="text-sm font-medium text-slate-200">{dashboard.active_job.label}</div>
              <div className="mt-1 text-xs text-slate-500">{dashboard.active_job.stage} · {dashboard.active_job.progress_percent}%</div>
              <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-900"><div className="h-full bg-indigo-500" style={{ width: `${dashboard.active_job.progress_percent}%` }} /></div>
            </div>
          ) : <p className="mt-3 text-sm text-slate-500">Nenhum job em execução.</p>}
        </div>
      </div>

      <div className="rounded-xl border border-slate-800 bg-[#0b101c]/60 p-5">
        <div className="flex items-center justify-between gap-3"><h3 className="font-semibold text-white">Jobs recentes</h3><span className="text-xs text-slate-500">Últimos {dashboard.recent_jobs.length}</span></div>
        {dashboard.recent_jobs.length === 0 ? <p className="mt-4 text-sm text-slate-500">Nenhum job ainda.</p> : (
          <div className="mt-3 divide-y divide-slate-800">
            {dashboard.recent_jobs.map((job) => (
              <div key={job.id} className="flex flex-wrap items-center gap-3 py-3 text-sm">
                <span className="w-10 text-xs text-slate-600">#{job.id}</span>
                <span className="rounded-md bg-slate-900 px-2 py-1 text-[10px] font-semibold uppercase text-indigo-300">{job.operation}</span>
                <span className="min-w-0 flex-1 truncate text-slate-300">{job.label}</span>
                <span className={job.status === "completed" ? "text-emerald-300" : job.status === "failed" ? "text-rose-300" : "text-slate-400"}>{job.status}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
