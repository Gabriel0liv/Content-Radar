"use client";

import { Activity } from "lucide-react";
import { useEffect, useState } from "react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export function Topbar() {
  const [online, setOnline] = useState<boolean | null>(null);

  useEffect(() => {
    async function checkHealth() {
      try {
        const res = await fetch(`${API_BASE_URL}/health`);
        setOnline(res.ok);
      } catch {
        setOnline(false);
      }
    }
    void checkHealth();
    const interval = setInterval(checkHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="fixed right-0 top-0 z-10 flex h-16 w-[calc(100%-16rem)] items-center justify-between border-b border-slate-800 bg-[#0b101c]/90 px-8 backdrop-blur-sm">
      <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">Pesquisa e referências</span>
      <div className="flex items-center gap-2 rounded-full border border-slate-800/80 bg-slate-900/50 px-3 py-1.5 text-xs">
        <Activity className="h-3.5 w-3.5 text-indigo-400" />
        <span className="font-medium text-slate-400">API</span>
        {online === null ? <span className="text-slate-500">…</span> : online ? <span className="font-semibold text-emerald-400">Online</span> : <span className="font-semibold text-rose-400">Offline</span>}
      </div>
    </header>
  );
}
