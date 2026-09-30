"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, Loader2, RefreshCw, XCircle } from "lucide-react";
import { speechApi } from "@/lib/speech-api";
import type { DiagnosticCheck, SpeechDiagnostics } from "@/lib/speech-types";

function Icon({ status }: { status: string }) {
  if (status === "ok") return <CheckCircle2 className="h-4 w-4 text-emerald-400" />;
  if (status === "warning") return <AlertTriangle className="h-4 w-4 text-amber-400" />;
  return <XCircle className="h-4 w-4 text-rose-400" />;
}

export function DiagnosticsPanel() {
  const [data, setData] = useState<SpeechDiagnostics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true); setError(null);
    try { setData(await speechApi.getDiagnostics()); }
    catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  };

  useEffect(() => { void load(); }, []);

  if (loading) return <div className="flex h-48 items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-indigo-400" /></div>;
  if (error) return <div className="rounded-xl border border-rose-900/50 bg-rose-950/20 p-4 text-sm text-rose-300">{error}</div>;
  if (!data) return null;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3 rounded-xl border border-slate-800 bg-[#0b101c]/55 p-4"><div><div className="text-xs uppercase tracking-wide text-slate-500">Speech worker</div><div className="mt-1 text-sm font-medium text-white">{data.worker_online ? "Online" : "Offline"}{data.worker_id ? ` · ${data.worker_id}` : ""}</div></div><button onClick={load} className="flex items-center gap-2 rounded-lg border border-slate-800 px-3 py-2 text-sm text-slate-300"><RefreshCw className="h-4 w-4" /> Atualizar</button></div>
      <div className="space-y-3">
        {data.diagnostics.checks.map((check: DiagnosticCheck) => <div key={check.id} className="rounded-xl border border-slate-800 bg-[#0b101c]/55 p-4"><div className="flex items-start gap-3"><Icon status={check.status} /><div><div className="text-sm font-semibold text-white">{check.id}</div><p className="mt-1 text-sm text-slate-400">{check.reason}</p>{check.action && <p className="mt-2 text-xs text-indigo-300">Ação: {check.action}</p>}</div></div></div>)}
      </div>
    </div>
  );
}
