"use client";

import { FormEvent, useMemo, useState } from "react";
import { Loader2, Search } from "lucide-react";

import { createCaseResearchRun } from "@/lib/api";
import type { CaseRadarPlatform, CaseResearchRun } from "@/lib/types";

const PLATFORM_OPTIONS: Array<{ value: CaseRadarPlatform; label: string }> = [
  { value: "youtube", label: "YouTube" },
  { value: "x", label: "X" },
  { value: "tiktok", label: "TikTok" },
  { value: "instagram", label: "Instagram" },
  { value: "reddit", label: "Reddit" },
  { value: "web", label: "Web" },
];

function splitTerms(value: string): string[] {
  return value
    .split(/[,\n]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

export function ResearchForm({ onCreated }: { onCreated: (run: CaseResearchRun) => void }) {
  const [theme, setTheme] = useState("");
  const [target, setTarget] = useState(10);
  const [depth, setDepth] = useState<"quick" | "balanced" | "deep">("balanced");
  const [languages, setLanguages] = useState(["pt", "en", "es"]);
  const [platforms, setPlatforms] = useState<CaseRadarPlatform[]>(PLATFORM_OPTIONS.map((item) => item.value));
  const [includeTerms, setIncludeTerms] = useState("");
  const [excludeTerms, setExcludeTerms] = useState("");
  const [priorities, setPriorities] = useState("identificar fonte original\ncontexto verificável");
  const [exclusions, setExclusions] = useState("ARG conhecido\nconteúdo obviamente encenado");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSubmit = useMemo(() => theme.trim().length > 0 && platforms.length > 0 && languages.length > 0, [theme, platforms, languages]);

  const togglePlatform = (platform: CaseRadarPlatform) => {
    setPlatforms((current) => (current.includes(platform) ? current.filter((value) => value !== platform) : [...current, platform]));
  };

  const toggleLanguage = (language: string) => {
    setLanguages((current) => (current.includes(language) ? current.filter((value) => value !== language) : [...current, language]));
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!canSubmit || loading) return;
    setLoading(true);
    setError(null);
    try {
      const run = await createCaseResearchRun({
        theme: theme.trim(),
        desired_usable_cases: target,
        languages,
        platforms,
        include_terms: splitTerms(includeTerms),
        exclude_terms: splitTerms(excludeTerms),
        priorities: splitTerms(priorities),
        exclusions: splitTerms(exclusions),
        research_depth: depth,
        global_result_budget: depth === "quick" ? 180 : depth === "deep" ? 1000 : 500,
      });
      onCreated(run);
      setTheme("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao iniciar a pesquisa.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={submit} className="space-y-5 rounded-2xl border border-slate-800 bg-[#0b101c] p-5 shadow-xl shadow-black/10">
      <div>
        <label className="text-sm font-semibold text-slate-200">O que você quer pesquisar?</label>
        <textarea
          value={theme}
          onChange={(event) => setTheme(event.target.value)}
          rows={3}
          placeholder="Ex.: vídeos estranhos gravados em florestas, com contexto e possível fonte original"
          className="mt-2 w-full resize-none rounded-xl border border-slate-700 bg-[#070b12] px-3.5 py-3 text-sm text-white outline-none transition focus:border-indigo-500"
        />
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <label className="space-y-2 text-sm text-slate-300">
          <span className="font-medium">Casos utilizáveis desejados</span>
          <input type="number" min={1} max={50} value={target} onChange={(event) => setTarget(Number(event.target.value))} className="w-full rounded-lg border border-slate-700 bg-[#070b12] px-3 py-2.5 text-white" />
        </label>
        <label className="space-y-2 text-sm text-slate-300">
          <span className="font-medium">Profundidade</span>
          <select value={depth} onChange={(event) => setDepth(event.target.value as typeof depth)} className="w-full rounded-lg border border-slate-700 bg-[#070b12] px-3 py-2.5 text-white">
            <option value="quick">Rápida</option>
            <option value="balanced">Equilibrada</option>
            <option value="deep">Profunda</option>
          </select>
        </label>
        <div className="space-y-2 text-sm text-slate-300">
          <span className="font-medium">Idiomas</span>
          <div className="flex gap-2">
            {["pt", "en", "es"].map((language) => (
              <button key={language} type="button" onClick={() => toggleLanguage(language)} className={`rounded-lg border px-3 py-2 text-xs font-semibold uppercase ${languages.includes(language) ? "border-indigo-500 bg-indigo-500/15 text-indigo-200" : "border-slate-700 text-slate-400"}`}>
                {language}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div>
        <p className="mb-2 text-sm font-medium text-slate-300">Fontes</p>
        <div className="flex flex-wrap gap-2">
          {PLATFORM_OPTIONS.map((platform) => (
            <button key={platform.value} type="button" onClick={() => togglePlatform(platform.value)} className={`rounded-full border px-3 py-1.5 text-xs font-medium transition ${platforms.includes(platform.value) ? "border-indigo-500/60 bg-indigo-500/15 text-indigo-200" : "border-slate-700 text-slate-500 hover:text-slate-300"}`}>
              {platform.label}
            </button>
          ))}
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <label className="space-y-2 text-sm text-slate-300">
          <span className="font-medium">Termos que ajudam</span>
          <textarea value={includeTerms} onChange={(event) => setIncludeTerms(event.target.value)} rows={2} placeholder="trail camera, original upload" className="w-full rounded-lg border border-slate-700 bg-[#070b12] px-3 py-2.5 text-white" />
        </label>
        <label className="space-y-2 text-sm text-slate-300">
          <span className="font-medium">Termos a excluir</span>
          <textarea value={excludeTerms} onChange={(event) => setExcludeTerms(event.target.value)} rows={2} placeholder="filme, fan trailer" className="w-full rounded-lg border border-slate-700 bg-[#070b12] px-3 py-2.5 text-white" />
        </label>
        <label className="space-y-2 text-sm text-slate-300">
          <span className="font-medium">Priorizar</span>
          <textarea value={priorities} onChange={(event) => setPriorities(event.target.value)} rows={3} className="w-full rounded-lg border border-slate-700 bg-[#070b12] px-3 py-2.5 text-white" />
        </label>
        <label className="space-y-2 text-sm text-slate-300">
          <span className="font-medium">Excluir</span>
          <textarea value={exclusions} onChange={(event) => setExclusions(event.target.value)} rows={3} className="w-full rounded-lg border border-slate-700 bg-[#070b12] px-3 py-2.5 text-white" />
        </label>
      </div>

      {error && <p className="rounded-lg border border-rose-900/60 bg-rose-950/20 px-3 py-2 text-sm text-rose-300">{error}</p>}

      <button disabled={!canSubmit || loading} className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-indigo-950/30 transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-50">
        {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
        Iniciar pesquisa
      </button>
    </form>
  );
}
