"use client";

import { useEffect, useState } from "react";
import { Activity, Cpu, Loader2, Mic2, Volume2 } from "lucide-react";
import { speechApi } from "@/lib/speech-api";
import type { SpeechStatus } from "@/lib/speech-types";

export function AudioOverview() {
  const [status, setStatus] = useState<SpeechStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    speechApi.getStatus().then(setStatus).catch((e) => setError(e.message)).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="flex h-48 items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-indigo-400" /></div>;
  if (error) return <div className="rounded-xl border border-rose-900/50 bg-rose-950/20 p-4 text-sm text-rose-300">{error}</div>;
  if (!status) return null;

  const caps = status.worker.capabilities || {};
  const ttsReady = Array.isArray(caps.tts_engines) && caps.tts_engines.some((item: any) => item?.available);
  const cards = [
    { label: "Worker", value: status.worker.online ? "Online" : "Offline", icon: Activity },
    { label: "STT", value: caps.stt_ready ? "Pronto" : "Indisponível", icon: Mic2 },
    { label: "TTS", value: ttsReady ? "Pronto" : "Indisponível", icon: Volume2 },
    { label: "Dispositivo", value: caps.cuda_available ? (caps.gpu_name || "CUDA") : "CPU", icon: Cpu },
  ];

  return (
    <div className="space-y-5">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {cards.map(({ label, value, icon: Icon }) => (
          <div key={label} className="rounded-xl border border-slate-800 bg-[#0b101c]/60 p-4">
            <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-slate-500"><Icon className="h-4 w-4" />{label}</div>
            <div className="mt-2 text-lg font-semibold text-white">{value}</div>
          </div>
        ))}
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-xl border border-slate-800 bg-[#0b101c]/60 p-5">
          <h3 className="font-semibold text-white">Fila</h3>
          <div className="mt-4 grid grid-cols-2 gap-3">
            <div className="rounded-lg bg-slate-950 p-3"><div className="text-xs text-slate-500">Aguardando</div><div className="mt-1 text-2xl font-semibold text-white">{status.queue.queued}</div></div>
            <div className="rounded-lg bg-slate-950 p-3"><div className="text-xs text-slate-500">Executando</div><div className="mt-1 text-2xl font-semibold text-white">{status.queue.running}</div></div>
          </div>
        </div>
        <div className="rounded-xl border border-slate-800 bg-[#0b101c]/60 p-5 text-sm text-slate-400">
          <h3 className="font-semibold text-white">Runtime</h3>
          <div className="mt-3 space-y-1.5">
            <div>FFmpeg: <span className="text-slate-200">{caps.ffmpeg_available ? "sim" : "não"}</span></div>
            <div>WhisperX: <span className="text-slate-200">{caps.whisperx_available ? "sim" : "não"}</span></div>
            <div>eSpeak: <span className="text-slate-200">{caps.espeak_available ? "sim" : "não"}</span></div>
            <div>Diarização: <span className="text-slate-200">{caps.diarization_ready ? "pronta" : "indisponível"}</span></div>
          </div>
        </div>
      </div>
    </div>
  );
}
