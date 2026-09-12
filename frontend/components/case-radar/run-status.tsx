"use client";

import { CheckCircle2, CircleDashed, Loader2, OctagonX } from "lucide-react";
import type { CaseResearchRun } from "@/lib/types";

const labels: Record<string, string> = {
  queued: "Na fila",
  generating_queries: "Gerando buscas",
  discovering: "Descobrindo fontes",
  enriching_sources: "Enriquecendo fontes",
  collecting_social_context: "Lendo contexto social",
  clustering_cases: "Agrupando casos",
  researching_cases: "Pesquisando casos",
  finalizing: "Montando dossiês",
  completed: "Concluída",
  partially_completed: "Concluída parcialmente",
  failed: "Falhou",
  cancelled: "Cancelada",
};

export function RunStatus({ run }: { run: CaseResearchRun }) {
  const terminal = ["completed", "partially_completed", "failed", "cancelled"].includes(run.status);
  const failed = ["failed", "cancelled"].includes(run.status);
  const Icon = failed ? OctagonX : terminal ? CheckCircle2 : run.status === "running" ? Loader2 : CircleDashed;

  return (
    <div className="rounded-xl border border-slate-800 bg-[#0b101c] p-4">
      <div className="flex items-center justify-between gap-4">
        <div className="flex min-w-0 items-center gap-3">
          <Icon className={`h-5 w-5 shrink-0 ${run.status === "running" ? "animate-spin text-indigo-400" : failed ? "text-rose-400" : "text-emerald-400"}`} />
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-white">{labels[run.stage] || labels[run.status] || run.stage}</p>
            <p className="truncate text-xs text-slate-500">{run.progress_message || `Pesquisa #${run.id}`}</p>
          </div>
        </div>
        <span className="text-sm font-mono text-slate-300">{run.progress_percent}%</span>
      </div>
      <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-800">
        <div className="h-full rounded-full bg-indigo-500 transition-all duration-500" style={{ width: `${Math.max(0, Math.min(100, run.progress_percent))}%` }} />
      </div>
      <div className="mt-3 grid grid-cols-4 gap-2 text-center text-xs text-slate-500">
        <div><strong className="block text-sm text-slate-200">{run.discovered_candidates}</strong>fontes</div>
        <div><strong className="block text-sm text-slate-200">{run.clustered_cases}</strong>casos</div>
        <div><strong className="block text-sm text-emerald-300">{run.usable_cases}</strong>utilizáveis</div>
        <div><strong className="block text-sm text-slate-300">{run.rejected_cases}</strong>rejeitados</div>
      </div>
    </div>
  );
}
