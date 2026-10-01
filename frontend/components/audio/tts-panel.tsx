"use client";

import { useEffect, useRef, useState } from "react";
import { Download, Loader2, Play, Search } from "lucide-react";
import { toast } from "sonner";
import { speechApi } from "@/lib/speech-api";
import type { SpeechArtifact, SpeechJob, SpeechVoice, TtsRequest } from "@/lib/speech-types";

export function TtsPanel() {
  const [voices, setVoices] = useState<SpeechVoice[]>([]);
  const [text, setText] = useState("Olá! Este é um teste de síntese de voz em português do Brasil.");
  const [engine, setEngine] = useState<"kokoro" | "piper">("kokoro");
  const [voice, setVoice] = useState("pt_br_dora");
  const [format, setFormat] = useState<"wav" | "mp3">("wav");
  const [speed, setSpeed] = useState(1);
  const [normalize, setNormalize] = useState(false);
  const [analysis, setAnalysis] = useState<Record<string, any> | null>(null);
  const [job, setJob] = useState<SpeechJob | null>(null);
  const [artifacts, setArtifacts] = useState<SpeechArtifact[]>([]);
  const [busy, setBusy] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    speechApi.listVoices().then((items) => {
      setVoices(items);
      const first = items.find((item) => item.engine === engine && item.available) || items.find((item) => item.engine === engine);
      if (first) setVoice(first.id);
    }).catch(() => undefined);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, []);

  useEffect(() => {
    const candidates = voices.filter((item) => item.engine === engine);
    if (!candidates.some((item) => item.id === voice)) {
      const first = candidates.find((item) => item.available) || candidates[0];
      if (first) setVoice(first.id);
    }
  }, [engine, voices, voice]);

  const watch = (id: number) => {
    if (pollRef.current) clearInterval(pollRef.current);
    const run = async () => {
      try {
        const fresh = await speechApi.getJob(id);
        setJob(fresh);
        if (["completed", "failed", "cancelled"].includes(fresh.status)) {
          if (pollRef.current) clearInterval(pollRef.current);
          pollRef.current = null;
          if (fresh.status === "completed") setArtifacts(await speechApi.listArtifacts(id));
        }
      } catch {
        // transient API failure
      }
    };
    void run();
    pollRef.current = setInterval(run, 2000);
  };

  const payload = (): TtsRequest => ({
    text,
    engine,
    voice,
    output_format: format,
    speed,
    language: "pt-br",
    normalize_ptbr: normalize,
    analyze_ptbr: true,
    preview_chars: 300,
  });

  const generate = async (preview: boolean) => {
    if (!text.trim()) return;
    setBusy(true);
    setArtifacts([]);
    try {
      const created = await speechApi.createTts(payload(), preview);
      setJob(created);
      watch(created.id);
      toast.success(preview ? "Preview adicionado à fila" : "Geração adicionada à fila");
    } catch (e: any) {
      toast.error("Não foi possível gerar a voz", { description: e.message });
    } finally {
      setBusy(false);
    }
  };

  const analyze = async () => {
    if (!text.trim()) return;
    try {
      const result = await speechApi.analyzeText(text);
      setAnalysis(result.analysis);
    } catch (e: any) {
      toast.error("Falha na análise", { description: e.message });
    }
  };

  const engineVoices = voices.filter((item) => item.engine === engine);
  const selected = voices.find((item) => item.id === voice);

  return (
    <div className="space-y-5">
      <div className="rounded-xl border border-slate-800 bg-[#0b101c]/60 p-5">
        <label className="text-xs text-slate-400">Texto<textarea value={text} onChange={(e) => setText(e.target.value)} rows={9} className="mt-1 w-full resize-y rounded-lg border border-slate-800 bg-slate-950 px-3.5 py-3 text-sm leading-6 text-white outline-none focus:border-indigo-500" /></label>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <label className="text-xs text-slate-400">Motor<select value={engine} onChange={(e) => setEngine(e.target.value as any)} className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white"><option value="kokoro">Kokoro</option><option value="piper">Piper</option></select></label>
          <label className="text-xs text-slate-400">Voz<select value={voice} onChange={(e) => setVoice(e.target.value)} className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white">{engineVoices.map((item) => <option key={item.id} value={item.id}>{item.display_name}{item.available ? "" : " — indisponível"}</option>)}</select></label>
          <label className="text-xs text-slate-400">Formato<select value={format} onChange={(e) => setFormat(e.target.value as any)} className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white"><option value="wav">WAV</option><option value="mp3">MP3</option></select></label>
          <label className="text-xs text-slate-400">Velocidade<input type="number" min={0.25} max={3} step={0.05} value={speed} onChange={(e) => setSpeed(Number(e.target.value))} className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white" /></label>
        </div>
        {selected && !selected.available && <div className="mt-3 rounded-lg border border-amber-900/50 bg-amber-950/20 p-3 text-xs text-amber-300">{selected.unavailable_reason || "Este motor/voz não está disponível no worker atual."}</div>}
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-slate-300"><input type="checkbox" checked={normalize} onChange={(e) => setNormalize(e.target.checked)} /> Normalizar PT-BR antes da síntese</label>
          <button onClick={analyze} className="flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-xs text-slate-300 hover:bg-slate-800"><Search className="h-3.5 w-3.5" /> Analisar texto</button>
          <div className="ml-auto flex gap-2">
            <button onClick={() => generate(true)} disabled={busy || !text.trim() || selected?.available === false} className="flex items-center gap-2 rounded-lg border border-indigo-700 px-4 py-2 text-sm font-medium text-indigo-300 hover:bg-indigo-950/40 disabled:opacity-40"><Play className="h-4 w-4" /> Preview</button>
            <button onClick={() => generate(false)} disabled={busy || !text.trim() || selected?.available === false} className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-40">{busy ? <Loader2 className="h-4 w-4 animate-spin" /> : null} Gerar voz</button>
          </div>
        </div>
        {analysis && <pre className="mt-4 max-h-48 overflow-auto rounded-lg bg-slate-950 p-3 text-xs text-slate-400">{JSON.stringify(analysis, null, 2)}</pre>}
      </div>

      {job && (
        <div className="rounded-xl border border-slate-800 bg-[#0b101c]/50 p-5">
          <div className="flex items-center justify-between"><div><div className="text-xs text-slate-500">Job #{job.id}</div><div className="text-sm font-medium text-white">{job.stage}</div></div><span className="text-sm text-indigo-300">{job.progress_percent}%</span></div>
          <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-900"><div className="h-full bg-indigo-500" style={{ width: `${job.progress_percent}%` }} /></div>
          {job.error_message && <div className="mt-3 rounded-lg border border-rose-900/50 bg-rose-950/20 p-3 text-sm text-rose-300">{job.error_message}</div>}
          {artifacts.length > 0 && <div className="mt-4 flex flex-wrap gap-3">{artifacts.map((artifact) => <a key={artifact.id} href={speechApi.artifactDownloadUrl(job.id, artifact.id)} className="flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-xs text-slate-300 hover:bg-slate-800"><Download className="h-3.5 w-3.5" />{artifact.filename}</a>)}</div>}
          {artifacts.some((item) => item.mime_type?.startsWith("audio/")) && <audio controls className="mt-4 w-full" src={speechApi.artifactDownloadUrl(job.id, artifacts.find((item) => item.mime_type?.startsWith("audio/"))!.id)} />}
        </div>
      )}
    </div>
  );
}
