"use client";

import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowLeft, Ban, ExternalLink, RefreshCw } from "lucide-react";

import { CaseDossier } from "@/components/case-radar/case-dossier";
import { CaseList } from "@/components/case-radar/case-list";
import { RunStatus } from "@/components/case-radar/run-status";
import {
  cancelCaseResearchRun,
  getCaseResearchQueries,
  getCaseResearchRun,
  getCaseResearchSources,
  getResearchCase,
  getResearchCases,
} from "@/lib/api";
import type { CaseResearchQuery, CaseResearchRun, ResearchCase, ResearchSource } from "@/lib/types";

export default function CaseRadarRunPage() {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const runId = Number(params.id);
  const requestedCaseId = Number(searchParams.get("case") || 0) || null;
  const [run, setRun] = useState<CaseResearchRun | null>(null);
  const [cases, setCases] = useState<ResearchCase[]>([]);
  const [queries, setQueries] = useState<CaseResearchQuery[]>([]);
  const [sources, setSources] = useState<ResearchSource[]>([]);
  const [selectedCase, setSelectedCase] = useState<ResearchCase | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    if (!Number.isFinite(runId)) return;
    try {
      const [nextRun, nextCases, nextQueries, nextSources] = await Promise.all([
        getCaseResearchRun(runId),
        getResearchCases(runId),
        getCaseResearchQueries(runId),
        getCaseResearchSources(runId),
      ]);
      setRun(nextRun);
      setCases(nextCases);
      setQueries(nextQueries);
      setSources(nextSources);
      if (requestedCaseId) {
        const existing = nextCases.find((item) => item.id === requestedCaseId);
        setSelectedCase(existing || (await getResearchCase(requestedCaseId)));
      } else {
        setSelectedCase((current) => current ? nextCases.find((item) => item.id === current.id) || null : null);
      }
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao carregar pesquisa.");
    } finally {
      setLoading(false);
    }
  }, [runId, requestedCaseId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const isActive = run?.status === "queued" || run?.status === "running";

  useEffect(() => {
    if (!isActive) return;
    const timer = window.setInterval(() => void refresh(), 4000);
    return () => window.clearInterval(timer);
  }, [isActive, refresh]);

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
          <button onClick={() => void refresh()} className="inline-flex items-center gap-2 rounded-lg border border-slate-800 px-3 py-2 text-xs font-semibold text-slate-300"><RefreshCw className="h-3.5 w-3.5" />Atualizar</button>
          {["queued", "running"].includes(run.status) && <button onClick={() => void cancel()} className="inline-flex items-center gap-2 rounded-lg border border-rose-900/70 px-3 py-2 text-xs font-semibold text-rose-300"><Ban className="h-3.5 w-3.5" />Cancelar</button>}
        </div>
      </div>

      {error && <div className="rounded-xl border border-rose-900/60 bg-rose-950/20 p-4 text-sm text-rose-300">{error}</div>}
      <RunStatus run={run} />

      {!!coverage.length && (
        <div className="flex flex-wrap gap-2">
          {coverage.map(([platform, value]) => (
            <span key={platform} className="rounded-full border border-slate-800 bg-slate-950/40 px-3 py-1.5 text-xs text-slate-400">
              {platform}: <strong className="text-slate-200">{value.results || 0}</strong> resultados{value.errors?.length ? ` · ${value.errors.length} aviso(s)` : ""}
            </span>
          ))}
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="rounded-xl border border-slate-800 bg-[#0b101c] p-4">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white">Queries geradas</h3>
            <span className="text-xs text-slate-500">{queries.length}</span>
          </div>
          <div className="max-h-64 space-y-2 overflow-auto pr-1">
            {queries.length ? queries.map((query) => (
              <div key={query.id} className="rounded-lg border border-slate-850 bg-slate-950/35 p-3">
                <div className="flex flex-wrap items-center gap-2 text-[10px] uppercase tracking-wide text-slate-500">
                  <span>{query.language}</span><span>·</span><span>{query.intent}</span>{query.target_platform && <><span>·</span><span>{query.target_platform}</span></>}
                </div>
                <p className="mt-1 text-xs leading-5 text-slate-300">{query.query_text}</p>
                <p className="mt-1 text-[11px] text-slate-600">{query.result_count} resultado(s) · {query.status}</p>
              </div>
            )) : <p className="text-xs text-slate-500">As queries aparecerão quando o worker iniciar a pesquisa.</p>}
          </div>
        </section>

        <section className="rounded-xl border border-slate-800 bg-[#0b101c] p-4">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white">Fontes descobertas</h3>
            <span className="text-xs text-slate-500">{sources.length}</span>
          </div>
          <div className="max-h-64 space-y-2 overflow-auto pr-1">
            {sources.length ? sources.slice(0, 50).map((source) => (
              <a key={source.id} href={source.canonical_url} target="_blank" rel="noreferrer" className="block rounded-lg border border-slate-850 bg-slate-950/35 p-3 transition hover:border-slate-700">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate text-xs font-medium text-slate-200">{source.title_or_caption || source.text || source.canonical_url}</p>
                    <p className="mt-1 text-[11px] text-slate-500">{source.platform} · {source.discovery_method}{source.author_handle ? ` · ${source.author_handle}` : ""}</p>
                  </div>
                  <ExternalLink className="mt-0.5 h-3.5 w-3.5 shrink-0 text-slate-600" />
                </div>
              </a>
            )) : <p className="text-xs text-slate-500">As fontes aparecerão durante a etapa de descoberta.</p>}
          </div>
        </section>
      </div>

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
