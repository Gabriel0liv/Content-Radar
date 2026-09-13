"use client";

import Link from "next/link";
import { ExternalLink, MapPin, ShieldCheck } from "lucide-react";

import type { ResearchCase } from "@/lib/types";

const statusLabels: Record<string, string> = {
  researching: "Pesquisando",
  ready: "Pronto",
  approved: "Aprovado",
  rejected: "Rejeitado",
  duplicate: "Duplicado",
  already_used: "Já usado",
};

export function CaseList({ cases, runId }: { cases: ResearchCase[]; runId: number }) {
  if (!cases.length) {
    return <div className="rounded-xl border border-dashed border-slate-800 px-5 py-10 text-center text-sm text-slate-500">Nenhum caso agrupado ainda.</div>;
  }

  return (
    <div className="space-y-3">
      {cases.map((item) => (
        <Link key={item.id} href={`/case-radar/${runId}?case=${item.id}`} className="group block rounded-xl border border-slate-800 bg-[#0b101c] p-4 transition hover:border-slate-700 hover:bg-slate-900/60">
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <div className="mb-2 flex flex-wrap items-center gap-2">
                <span className="rounded-full border border-slate-700 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-slate-400">{statusLabels[item.status] || item.status}</span>
                <span className="inline-flex items-center gap-1 text-xs text-slate-500"><ShieldCheck className="h-3.5 w-3.5" /> confiança {Math.round(item.research_confidence * 100)}%</span>
              </div>
              <h3 className="truncate font-semibold text-white">{item.provisional_title}</h3>
              {item.normalized_summary && <p className="mt-1 line-clamp-2 text-sm leading-relaxed text-slate-400">{item.normalized_summary}</p>}
              {item.alleged_location && <p className="mt-2 inline-flex items-center gap-1 text-xs text-slate-500"><MapPin className="h-3.5 w-3.5" />{item.alleged_location}</p>}
            </div>
            <ExternalLink className="mt-1 h-4 w-4 shrink-0 text-slate-600 transition group-hover:text-indigo-400" />
          </div>
        </Link>
      ))}
    </div>
  );
}
