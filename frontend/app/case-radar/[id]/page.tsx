"use client";

import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowLeft, Ban, RefreshCw } from "lucide-react";

import { CaseDossier } from "@/components/case-radar/case-dossier";
import { CaseList } from "@/components/case-radar/case-list";
import { RunStatus } from "@/components/case-radar/run-status";
import { cancelCaseResearchRun, getCaseResearchRun, getResearchCase, getResearchCases } from "@/lib/api";
import type { CaseResearchRun, ResearchCase } from "@/lib/types";

export default function CaseRadarRunPage() {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const runId = Number(params.id);
  const requestedCaseId = Number(searchParams.get("case") || 0) || null;
  const [run, setRun] = useState<CaseResearchRun | null>(null);
  const [cases, setCases] = useState<ResearchCase[]>([]);
  const [selectedCase, setSelectedCase] = useState<ResearchCase | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    if (!Number.isFinite(runId)) return;
    try {
      const [nextRun, nextCases] = await Promise.all([getCaseResearchRun(runId), getResearchCases(runId)]);
      setRun(nextRun);
      setCases(nextCases);
      if (requestedCaseId) {
        const existing = nextCases.find((item) => item.id === requestedCaseId);
        setSelectedCase(existing || (await getResearchCase(requestedCaseId)));
      } else if (selectedCase) {
        setSelectedCase(nextCases.find((item) => item.id === selectedCase.id) || null);
      }
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao carregar pesquisa.");
    } finally {
      setLoading(false);
    }
  }, [runId, requestedCaseId, selectedCase?.id]);

  useEffect(() => {
    refresh();
    const timer = window.setInterval(refresh, 4000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  const coverage = useMemo(() => Object.entries(run?.provider_coverage_json || {}), [run?.provider_coverage_json]);

  const cancel = async () => {
    if (!run || !["queued", "running"].includes(run.status)) return;
    try {
      setRun(await cancelCaseResearchRun(run.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao cancelar pesquisa.");
    }
  };

  if (loading && !run) return <div className="flex h-[70vh] items-center justify-center"><RefreshCw className="h-7 w-7 animate-spin text-indigo-400" /></div>;
  if (!run) return <div className="rounded-xl border border-rose-900 bg-rose-950/20 p-5 text-rose-300">{error || "Pesquisa não encontrada."}</div>;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 border-b border-slate-850 pb-5 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <Link href="/case-radar" className="mb-3 inline-flex items-center gap-1 text-xs font-medium text-slate-500 hover:text-slate-300"><ArrowLeft className="h-3.5 w-3.5" /> Case Radar</Link>
          <h2 className="max-w-4xl text-2xl font-bold text-white">{run.request_json.theme}</h2>
          <p className="mt-1 text-sm text-slate-500">Pesquisa #{run.id} · {run.request_json.research_depth} · alvo de {run.request_json.desired_usable_cases} casos</p>
        </div>
        <div className="flex gap-2">
          <button onClick={refresh} className="inline-flex items-center gap-2 rounded-lg border border-slate-800 px-3 py-2 text-xs font-semibold text-slate-300"><RefreshCw className="h-3.5 w-3.5" />Atualizar</button>
          {["queued", "running"].includes(run.status) && <button onClick={cancel} className="inline-flex items-center gap-2 rounded-lg border border-rose-900/70 px-3 py-2 text-xs font-semibold text-rose-300"><Ban className="h-3.5 w-3.5" />Cancelar</button>}
        </div>
      </div>

      {error && <div className="rounded-xl border border-rose-900/60 bg-rose-950/20 p-4 text-sm text-rose-300">{error}</div>}
      <RunStatus run={run} />

      {!!coverage.length && (
        <div className="flex flex-wrap gap-2">
          {coverage.map(([platform, value]: [string, any]) => (
            <span key={platform} className="rounded-full border border-slate-800 bg-slate-950/40 px-3 py-1.5 text-xs text-slate-400">
              {platform}: <strong className="text-slate-200">{value.results || 0}</strong> resultados{value.errors?.length ? ` · ${value.errors.length} aviso(s)` : ""}
            </span>
          ))}
        </div>
      )}

      <div className={`grid gap-6 ${selectedCase ? "xl:grid-cols-[340px_minmax(0,1fr)]" : ""}`}>
        <div>
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-lg font-semibold text-white">Casos encontrados</h3>
            <span className="text-xs text-slate-500">{cases.length}</span>
          </div>
          <CaseList cases={cases} runId={runId} />
        </div>

        {selectedCase && (
          <div className="min-w-0">
            <CaseDossier initialCase={selectedCase} onUpdated={(updated) => { setSelectedCase(updated); setCases((current) => current.map((item) => item.id === updated.id ? updated : item)); }} />
          </div>
        )}
      </div>
    </div>
  );
}
