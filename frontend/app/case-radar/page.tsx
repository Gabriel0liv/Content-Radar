"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ArrowRight, RefreshCw } from "lucide-react";

import { ResearchForm } from "@/components/case-radar/research-form";
import { RunStatus } from "@/components/case-radar/run-status";
import { getCaseResearchRuns } from "@/lib/api";
import type { CaseResearchRun } from "@/lib/types";

export default function CaseRadarPage() {
  const [runs, setRuns] = useState<CaseResearchRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const response = await getCaseResearchRuns({ limit: 30 });
      setRuns(response.items);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao carregar pesquisas.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const timer = window.setInterval(refresh, 4000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  const onCreated = (run: CaseResearchRun) => setRuns((current) => [run, ...current.filter((item) => item.id !== run.id)]);

  return (
    <div className="space-y-7">
      <div className="border-b border-slate-850 pb-5">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-indigo-400">Pesquisa investigativa</p>
        <h2 className="mt-1 text-3xl font-bold tracking-tight text-white">Case Radar</h2>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">Procure casos, encontre versões anteriores, comentários úteis, contexto externo e possíveis explicações sem tratar uma alegação como fato só porque ela viralizou.</p>
      </div>

      <ResearchForm onCreated={onCreated} />

      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-white">Pesquisas recentes</h3>
            <p className="text-xs text-slate-500">A execução continua no worker mesmo se esta página for fechada.</p>
          </div>
          <button onClick={refresh} disabled={loading} className="inline-flex items-center gap-2 rounded-lg border border-slate-800 px-3 py-2 text-xs font-semibold text-slate-300 hover:bg-slate-900 disabled:opacity-50">
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} /> Atualizar
          </button>
        </div>

        {error && <div className="rounded-xl border border-rose-900/60 bg-rose-950/20 p-4 text-sm text-rose-300">{error}</div>}
        {!loading && !runs.length && !error && <div className="rounded-xl border border-dashed border-slate-800 p-10 text-center text-sm text-slate-500">Nenhuma pesquisa iniciada ainda.</div>}

        <div className="grid gap-4 xl:grid-cols-2">
          {runs.map((run) => (
            <Link key={run.id} href={`/case-radar/${run.id}`} className="group block">
              <div className="relative">
                <RunStatus run={run} />
                <div className="mt-2 flex items-center justify-between px-1 text-xs text-slate-500">
                  <span className="max-w-[80%] truncate">{run.request_json.theme}</span>
                  <span className="inline-flex items-center gap-1 text-indigo-400 opacity-0 transition group-hover:opacity-100">Abrir <ArrowRight className="h-3 w-3" /></span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
