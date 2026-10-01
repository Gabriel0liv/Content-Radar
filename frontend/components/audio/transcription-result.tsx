"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Download, Library, Loader2, Save } from "lucide-react";
import { toast } from "sonner";
import { speechApi } from "@/lib/speech-api";
import type { SpeechArtifact, SpeechJob, SpeechSpeakerMapping } from "@/lib/speech-types";

export function TranscriptionResult({ job }: { job: SpeechJob }) {
  const [artifacts, setArtifacts] = useState<SpeechArtifact[]>([]);
  const [mappings, setMappings] = useState<SpeechSpeakerMapping[]>([]);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (job.status !== "completed") return;
    Promise.all([speechApi.listArtifacts(job.id), speechApi.listSpeakerMappings(job.id)])
      .then(([a, m]) => {
        setArtifacts(a);
        setMappings(m);
        setDrafts(Object.fromEntries(m.map((item) => [item.raw_speaker, item.display_name])));
      })
      .catch((e) => toast.error("Não foi possível carregar o resultado", { description: e.message }))
      .finally(() => setLoading(false));
  }, [job.id, job.status]);

  const normalized = (job.result_json as any)?.normalized || {};
  const segments = Array.isArray(normalized.segments) ? normalized.segments : [];
  const rawSpeakers = useMemo(
    () => Array.from(new Set(segments.map((s: any) => s?.speaker).filter(Boolean))) as string[],
    [segments],
  );

  if (job.status !== "completed") return null;
  if (loading) return <div className="flex justify-center py-8"><Loader2 className="h-5 w-5 animate-spin text-indigo-400" /></div>;

  const saveMapping = async (raw: string) => {
    const value = (drafts[raw] || "").trim();
    if (!value) return;
    try {
      const saved = await speechApi.setSpeakerMapping(job.id, raw, value);
      setMappings((items) => [...items.filter((item) => item.raw_speaker !== raw), saved]);
      toast.success("Nome do speaker salvo");
    } catch (e: any) {
      toast.error("Não foi possível salvar", { description: e.message });
    }
  };

  const display = (raw?: string | null) => {
    if (!raw) return null;
    return mappings.find((item) => item.raw_speaker === raw)?.display_name || raw;
  };

  return (
    <div className="space-y-5">
      {job.reference_source_id && job.transcript_id && (
        <div className="flex items-center justify-between gap-3 rounded-xl border border-emerald-900/40 bg-emerald-950/20 p-3 text-sm text-emerald-200">
          <div className="flex items-center gap-2"><Library className="h-4 w-4" /> Transcrição vinculada à Biblioteca.</div>
          <Link href={`/references/${job.reference_source_id}`} className="font-medium text-emerald-300 hover:text-emerald-200">Abrir referência</Link>
        </div>
      )}

      {rawSpeakers.length > 0 && (
        <div className="rounded-xl border border-slate-800 bg-[#0b101c]/60 p-4">
          <h4 className="mb-3 text-sm font-semibold text-white">Speakers</h4>
          <div className="grid gap-2 md:grid-cols-2">
            {rawSpeakers.map((raw) => (
              <div key={raw} className="flex items-center gap-2">
                <span className="w-24 shrink-0 text-xs font-mono text-slate-500">{raw}</span>
                <input value={drafts[raw] ?? display(raw) ?? ""} onChange={(e) => setDrafts((old) => ({ ...old, [raw]: e.target.value }))} placeholder="Nome de exibição" className="min-w-0 flex-1 rounded-md border border-slate-800 bg-slate-950 px-2.5 py-1.5 text-sm text-slate-200 outline-none focus:border-indigo-500" />
                <button onClick={() => saveMapping(raw)} className="rounded-md border border-slate-700 p-2 text-slate-300 hover:bg-slate-800"><Save className="h-3.5 w-3.5" /></button>
              </div>
            ))}
          </div>
          <p className="mt-2 text-[11px] text-slate-600">Os nomes alteram apenas a exibição; os labels crus permanecem preservados.</p>
        </div>
      )}

      <div className="rounded-xl border border-slate-800 bg-[#0b101c]/60 p-4">
        <div className="mb-3 flex items-center justify-between gap-3">
          <h4 className="text-sm font-semibold text-white">Transcrição</h4>
          <button onClick={() => navigator.clipboard.writeText(String(normalized.full_text || ""))} className="text-xs text-indigo-300 hover:text-indigo-200">Copiar texto</button>
        </div>
        {segments.length > 0 ? (
          <div className="max-h-[480px] space-y-2 overflow-y-auto pr-1">
            {segments.map((segment: any, index: number) => (
              <div key={index} className="rounded-lg bg-slate-950/70 px-3 py-2.5 text-sm text-slate-300">
                <div className="mb-1 flex gap-2 text-[11px] text-slate-600">
                  <span>{Number(segment.start || 0).toFixed(1)}s</span>
                  {segment.speaker && <span className="font-medium text-indigo-400">{display(segment.speaker)}</span>}
                </div>
                {segment.text}
              </div>
            ))}
          </div>
        ) : (
          <p className="whitespace-pre-wrap text-sm leading-6 text-slate-300">{String(normalized.full_text || "Sem texto retornado.")}</p>
        )}
      </div>

      {artifacts.length > 0 && (
        <div className="rounded-xl border border-slate-800 bg-[#0b101c]/60 p-4">
          <h4 className="mb-3 text-sm font-semibold text-white">Arquivos</h4>
          <div className="flex flex-wrap gap-2">
            {artifacts.map((artifact) => (
              <a key={artifact.id} href={speechApi.artifactDownloadUrl(job.id, artifact.id)} className="flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-xs text-slate-300 hover:bg-slate-800">
                <Download className="h-3.5 w-3.5" /> {artifact.filename}
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
