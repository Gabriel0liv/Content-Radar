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
        if (res.ok) {
          setOnline(true);
        } else {
          setOnline(false);
        }
      } catch {
        setOnline(false);
      }
    }
    checkHealth();
    // Check connection every 15 seconds
    const interval = setInterval(checkHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="fixed top-0 right-0 z-10 flex h-16 w-[calc(100%-16rem)] items-center justify-between border-b border-slate-800 bg-[#0b101c]/90 px-8 backdrop-blur-sm">
      <div className="flex flex-col">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500">Portal de Inteligência</h2>
      </div>
      <div className="flex items-center gap-4">
        {/* Connection status badge */}
        <div className="flex items-center gap-2 rounded-full bg-slate-900/50 border border-slate-800/80 px-3 py-1.5 text-xs">
          <Activity className="h-3.5 w-3.5 text-indigo-400" />
          <span className="text-slate-400 font-medium">FastAPI:</span>
          {online === null ? (
            <span className="text-slate-500 animate-pulse">Consultando...</span>
          ) : online ? (
            <span className="flex items-center gap-1.5 font-semibold text-emerald-400">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-ping"></span>
              Online
            </span>
          ) : (
            <span className="flex items-center gap-1.5 font-semibold text-rose-400">
              <span className="h-1.5 w-1.5 rounded-full bg-rose-500"></span>
              Offline
            </span>
          )}
        </div>
      </div>
    </header>
  );
}
