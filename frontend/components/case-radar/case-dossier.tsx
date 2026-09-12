"use client";

import { useState } from "react";
import { ExternalLink, Save, ShieldAlert, ShieldCheck } from "lucide-react";

import { updateResearchCase } from "@/lib/api";
import type { DossierClaim, ResearchCase, ResearchCaseStatus } from "@/lib/types";

function ClaimSection({ title, claims, tone }: { title: string; claims: DossierClaim[]; tone: "good" | "warn" | "bad" | "neutral" }) {
  if (!claims.length) return null;
  const toneClass = tone === "good" ? "border-emerald-900/60 bg-emerald-950/10" : tone === "bad" ? "border-rose-900/60 bg-rose-950/10" : tone === "warn" ? "border-amber-900/60 bg-amber-950/10" : "border-slate-800 bg-slate-950/20";
  return (
    <section className={`rounded-xl border p-4 ${toneClass}`}>
      <h3 className="mb-3 text-sm font-semibold text-white">{title}</h3>
      <div className="space-y-3">
        {claims.map((claim) => (
          <div key={claim.id} className="text-sm text-slate-300">
            <p>{claim.text}</p>
            <p className="mt-1 text-xs text-slate-500">Confiança {Math.round(claim.confidence * 100)}% · evidências {claim.evidence_ids.join(", ")}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

export function CaseDossier({ initialCase, onUpdated }: { initialCase: ResearchCase; onUpdated?: (item: ResearchCase) => void }) {
  const [item, setItem] = useState(initialCase);
  const [notes, setNotes] = useState(initialCase.manual_notes || "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const dossier = item.dossier_json;

  const save = async (patch: Partial<{ status: ResearchCaseStatus; manual_notes: string; already_used: boolean }>) => {
    setSaving(true);
    setError(null);
    try {
      const updated = await updateResearchCase(item.id, { ...patch, manual_notes: notes });
      setItem(updated);
      onUpdated?.(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao atualizar caso.");
    } finally {
      setSaving(false);
    }
  };

  if (!dossier) {
    return <div className="rounded-xl border border-slate-800 bg-[#0b101c] p-6 text-sm text-slate-400">O dossiê deste caso ainda está sendo montado.</div>;
  }

  return (
    <div className="space-y-5">
      <div className="rounded-2xl border border-slate-800 bg-[#0b101c] p-5">
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div>
            <div className="mb-2 flex flex-wrap items-center gap-2 text-xs">
              <span className="rounded-full border border-indigo-900/60 bg-indigo-950/30 px-2 py-1 text-indigo-300">{item.status}</span>
              <span className="inline-flex items-center gap-1 text-slate-400"><ShieldCheck className="h-3.5 w-3.5" /> pesquisa {Math.round(item.research_confidence * 100)}%</span>
              <span className="inline-flex items-center gap-1 text-slate-400"><ShieldAlert className="h-3.5 w-3.5" /> origem {Math.round(item.origin_confidence * 100)}% ({item.origin_status})</span>
            </div>
            <h2 className="text-xl font-bold text-white">{dossier.title}</h2>
            {dossier.summary && <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">{dossier.summary}</p>}
          </div>
          <div className="flex flex-wrap gap-2">
            <button onClick={() => save({ status: "approved" })} disabled={saving} className="rounded-lg bg-emerald-700 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50">Aprovar</button>
            <button onClick={() => save({ status: "rejected" })} disabled={saving} className="rounded-lg border border-rose-900 px-3 py-2 text-xs font-semibold text-rose-300 disabled:opacity-50">Rejeitar</button>
            <button onClick={() => save({ already_used: true })} disabled={saving} className="rounded-lg border border-slate-700 px-3 py-2 text-xs font-semibold text-slate-300 disabled:opacity-50">Já usado</button>
          </div>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        {[{ label: "Fonte principal", source: dossier.primary_source }, { label: "Mais antiga encontrada", source: dossier.earliest_known_source }, { label: "Provável original", source: dossier.likely_original_source }].map(({ label, source }) => (
          <div key={label} className="rounded-xl border border-slate-800 bg-[#0b101c] p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
            {source ? <><p className="mt-2 truncate text-sm font-medium text-slate-200">{source.title || source.author_handle || source.url}</p><a href={source.url} target="_blank" rel="noreferrer" className="mt-2 inline-flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300">Abrir fonte <ExternalLink className="h-3 w-3" /></a></> : <p className="mt-2 text-sm text-slate-600">Não resolvida</p>}
          </div>
        ))}
      </div>

      <ClaimSection title="Contexto corroborado" claims={dossier.verified_context || []} tone="good" />
      <ClaimSection title="Alegações não verificadas" claims={dossier.unverified_claims || []} tone="warn" />
      <ClaimSection title="Contradições encontradas" claims={dossier.contradictions || []} tone="bad" />
      <ClaimSection title="Explicações alternativas / debunks" claims={dossier.alternative_explanations || []} tone="neutral" />

      {!!dossier.useful_social_context?.length && (
        <section className="rounded-xl border border-slate-800 bg-[#0b101c] p-4">
          <h3 className="mb-3 text-sm font-semibold text-white">Comentários e contexto social úteis</h3>
          <div className="space-y-3">
            {dossier.useful_social_context.slice(0, 20).map((context: any) => (
              <div key={context.id} className="border-l-2 border-slate-700 pl-3 text-sm text-slate-300">
                <p>{context.body}</p>
                <p className="mt-1 text-xs text-slate-500">{context.author_handle || "autor desconhecido"} · utilidade {Number(context.usefulness_score || 0).toFixed(1)}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      {!!dossier.transcript_segments?.length && (
        <section className="rounded-xl border border-slate-800 bg-[#0b101c] p-4">
          <h3 className="mb-3 text-sm font-semibold text-white">Trechos transcritos</h3>
          <div className="max-h-80 space-y-2 overflow-y-auto pr-2">
            {dossier.transcript_segments.map((segment: any) => (
              <div key={segment.id} className="grid grid-cols-[72px_1fr] gap-3 text-sm">
                <span className="font-mono text-xs text-slate-500">{segment.start_time == null ? "—" : `${Number(segment.start_time).toFixed(1)}s`}</span>
                <span className="text-slate-300">{segment.text}</span>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="rounded-xl border border-slate-800 bg-[#0b101c] p-4">
        <label className="text-sm font-semibold text-white">Notas manuais</label>
        <textarea value={notes} onChange={(event) => setNotes(event.target.value)} rows={4} className="mt-2 w-full resize-none rounded-lg border border-slate-700 bg-[#070b12] px-3 py-2.5 text-sm text-white" />
        {error && <p className="mt-2 text-xs text-rose-400">{error}</p>}
        <button onClick={() => save({})} disabled={saving} className="mt-3 inline-flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-xs font-semibold text-slate-200 disabled:opacity-50"><Save className="h-3.5 w-3.5" />Salvar notas</button>
      </section>
    </div>
  );
}
