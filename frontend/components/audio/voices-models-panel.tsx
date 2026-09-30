"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Download, Loader2, Play, RefreshCw, Scale } from "lucide-react";
import { toast } from "sonner";
import { speechApi } from "@/lib/speech-api";
import type { SpeechArtifact, SpeechJob, SpeechVoice } from "@/lib/speech-types";

export function VoicesModelsPanel() {
  const [voices, setVoices] = useState<SpeechVoice[]>([]);
  const [engine, setEngine] = useState<"all" | "kokoro" | "piper">("all");
  const [loading, setLoading] = useState(true);
  const [compareText, setCompareText] = useState("Olá! Esta frase serve para comparar ritmo, clareza, naturalidade e entonação das vozes em português do Brasil.");
  const [compareJob, setCompareJob] = useState<SpeechJob | null>(null);
  const [compareArtifacts, setCompareArtifacts] = useState<SpeechArtifact[]>([]);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = async () => {
    setLoading(true);
    try { setVoices(await speechApi.listVoices()); }
    catch (e: any) { toast.error("Falha ao carregar vozes", { description: e.message }); }
    finally { setLoading(false); }
  };

  useEffect(() => {
    void load();
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, []);

  const filtered = useMemo(() => voices.filter((voice) => engine === "all" || voice.engine === engine), [voices, engine]);

  const createSample = async (voice: SpeechVoice) => {
    try { await speechApi.createVoiceSample(voice.id); toast.success(`Amostra de ${voice.display_name} adicionada à fila`); }
    catch (e: any) { toast.error("Não foi possível gerar amostra", { description: e.message }); }
  };

  const watchCompare = (id: number) => {
    if (pollRef.current) clearInterval(pollRef.current);
    const run = async () => {
      try {
        const fresh = await speechApi.getJob(id);
        setCompareJob(fresh);
        if (["completed", "failed", "cancelled"].includes(fresh.status)) {
          if (pollRef.current) clearInterval(pollRef.current);
          pollRef.current = null;
          if (fresh.status === "completed") setCompareArtifacts(await speechApi.listArtifacts(id));
        }
      } catch {
        // transient API failure should not stop comparison polling
      }
    };
    void run();
    pollRef.current = setInterval(run, 2000);
  };

  const compare = async () => {
    try {
      setCompareArtifacts([]);
      const available = voices.filter((voice) => voice.available && voice.locale.toLowerCase() === "pt-br").map((voice) => voice.id);
      const job = await speechApi.createVoiceCompare(compareText, available.length ? available : undefined);
      setCompareJob(job);
      watchCompare(job.id);
      toast.success("Comparação adicionada à fila");
    } catch (e: any) { toast.error("Não foi possível iniciar comparação", { description: e.message }); }
  };

  const compareResults = Array.isArray((compareJob?.result_json as any)?.results) ? (compareJob?.result_json as any).results : [];
  const audioForVoice = (voiceId: string) => compareArtifacts.find((artifact) => artifact.artifact_type === "voice_compare_audio" && artifact.filename === `compare_${voiceId}.wav`);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-3">
        <select value={engine} onChange={(e) => setEngine(e.target.value as any)} className="rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white"><option value="all">Todos os motores</option><option value="kokoro">Kokoro</option><option value="piper">Piper</option></select>
        <button onClick={load} className="flex items-center gap-2 rounded-lg border border-slate-800 px-3 py-2 text-sm text-slate-300 hover:bg-slate-900"><RefreshCw className="h-4 w-4" /> Atualizar</button>
      </div>

      {loading ? <div className="flex h-40 items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-indigo-400" /></div> : (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {filtered.map((voice) => <div key={voice.id} className="rounded-xl border border-slate-800 bg-[#0b101c]/55 p-4"><div className="flex items-start justify-between gap-3"><div><h4 className="font-semibold text-white">{voice.display_name}</h4><p className="mt-0.5 text-xs text-slate-500">{voice.engine} · {voice.locale} · {voice.style || "sem estilo"}</p></div><span className={`rounded-full px-2 py-1 text-[10px] font-semibold ${voice.available ? "bg-emerald-950 text-emerald-300" : "bg-rose-950 text-rose-300"}`}>{voice.available ? "Disponível" : "Indisponível"}</span></div>{voice.unavailable_reason && <p className="mt-3 text-xs text-amber-300">{voice.unavailable_reason}</p>}<div className="mt-4 flex gap-2">{voice.sample_state === "ready" ? <audio controls preload="none" className="h-8 min-w-0 flex-1" src={speechApi.voiceSampleUrl(voice.id)} /> : <button onClick={() => createSample(voice)} disabled={!voice.available} className="flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-xs text-slate-300 disabled:opacity-40"><Play className="h-3.5 w-3.5" /> Gerar amostra</button>}</div></div>)}
        </div>
      )}

      <div className="rounded-xl border border-slate-800 bg-[#0b101c]/55 p-5">
        <div className="flex items-center gap-2"><Scale className="h-4 w-4 text-indigo-400" /><h3 className="font-semibold text-white">Comparar vozes PT-BR</h3></div>
        <textarea value={compareText} onChange={(e) => setCompareText(e.target.value)} rows={3} className="mt-3 w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white" />
        <div className="mt-3 flex items-center justify-between gap-3"><p className="text-xs text-slate-500">A comparação usa as vozes disponíveis no worker e continua mesmo se uma voz individual falhar.</p><button onClick={compare} disabled={compareJob?.status === "queued" || compareJob?.status === "running"} className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-40">Comparar</button></div>
        {compareJob && <div className="mt-4 space-y-3"><div className="flex items-center justify-between text-xs"><span className="text-slate-400">Job #{compareJob.id} · {compareJob.stage}</span><span className="text-indigo-300">{compareJob.progress_percent}%</span></div><div className="h-1.5 overflow-hidden rounded-full bg-slate-900"><div className="h-full bg-indigo-500" style={{ width: `${compareJob.progress_percent}%` }} /></div>{compareJob.error_message && <div className="rounded-lg bg-rose-950/20 p-3 text-xs text-rose-300">{compareJob.error_message}</div>}</div>}

        {compareResults.length > 0 && <div className="mt-4 grid gap-3 md:grid-cols-2">{compareResults.map((result: any) => {
          const artifact = audioForVoice(result.voice_id);
          return <div key={result.voice_id} className="rounded-lg border border-slate-800 bg-slate-950/60 p-3"><div className="flex items-center justify-between gap-2"><div><div className="text-sm font-medium text-white">{result.voice_id}</div><div className="text-xs text-slate-500">{result.engine}</div></div><span className={`text-xs font-medium ${result.status === "success" ? "text-emerald-300" : "text-rose-300"}`}>{result.status}</span></div>{result.error && <p className="mt-2 text-xs text-rose-300">{result.error}</p>}{artifact && <audio controls className="mt-3 h-8 w-full" src={speechApi.artifactDownloadUrl(compareJob!.id, artifact.id)} />}</div>;
        })}</div>}

        {compareArtifacts.filter((item) => item.artifact_type !== "voice_compare_audio").length > 0 && <div className="mt-4 flex flex-wrap gap-2">{compareArtifacts.filter((item) => item.artifact_type !== "voice_compare_audio").map((artifact) => <a key={artifact.id} href={speechApi.artifactDownloadUrl(compareJob!.id, artifact.id)} className="flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-xs text-slate-300"><Download className="h-3.5 w-3.5" /> {artifact.filename}</a>)}</div>}
      </div>
    </div>
  );
}
