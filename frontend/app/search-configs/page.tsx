"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Edit, Loader2, Play, Plus, RefreshCw, Search, X } from "lucide-react";
import { toast } from "sonner";

import { DiscoveryAutocomplete } from "@/components/search/discovery-autocomplete";
import { createSearchConfig, getSearchConfigs, runSearchConfig, updateSearchConfig } from "@/lib/api";
import type { DiscoveryTerm, SearchConfig } from "@/lib/types";

const emptyForm = {
  name: "",
  description: "",
  language: "pt",
  country_code: "BR",
  days_back: 7,
  min_views: 30000,
  max_results_per_query: 50,
  keywords: "",
  negative_keywords: "",
  youtube_categories: "",
  minimum_topic_confidence: 0.7,
  minimum_performance_ratio: 0,
};

export default function SearchConfigsPage() {
  const [configs, setConfigs] = useState<SearchConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [editing, setEditing] = useState<SearchConfig | null>(null);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [includedTerms, setIncludedTerms] = useState<DiscoveryTerm[]>([]);
  const [excludedTerms, setExcludedTerms] = useState<DiscoveryTerm[]>([]);
  const [saving, setSaving] = useState(false);
  const [runningId, setRunningId] = useState<number | null>(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const response = await getSearchConfigs();
      setConfigs(response.configs);
    } catch (error: any) {
      toast.error("Erro ao carregar pesquisas", { description: error.message });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const visibleConfigs = useMemo(() => {
    const needle = search.trim().toLowerCase();
    if (!needle) return configs;
    return configs.filter((config) => `${config.name} ${config.description || ""}`.toLowerCase().includes(needle));
  }, [configs, search]);

  const resetEditor = () => {
    setEditing(null);
    setCreating(false);
    setForm(emptyForm);
    setIncludedTerms([]);
    setExcludedTerms([]);
  };

  const openCreate = () => {
    resetEditor();
    setCreating(true);
  };

  const topicPlaceholder = (id: number, name: string): DiscoveryTerm => ({
    id: -id,
    normalized_term: name.toLowerCase(),
    display_name: name,
    type: "topic",
    entity_id: id,
    usage_count: 0,
    video_count: 0,
    channel_count: 0,
    relevance_score: 0,
    last_seen_at: null,
  });

  const openEdit = (config: SearchConfig) => {
    setEditing(config);
    setCreating(false);
    setForm({
      name: config.name,
      description: config.description || "",
      language: config.language || "pt",
      country_code: config.country_code || "BR",
      days_back: config.days_back || 7,
      min_views: config.min_views || 0,
      max_results_per_query: config.max_results_per_query || 50,
      keywords: (config.keywords_json || []).join("\n"),
      negative_keywords: (config.negative_keywords_json || []).join("\n"),
      youtube_categories: (config.youtube_categories_json || []).join("\n"),
      minimum_topic_confidence: config.minimum_topic_confidence ?? 0.7,
      minimum_performance_ratio: config.minimum_performance_ratio ?? 0,
    });
    setIncludedTerms((config.included_topic_ids || []).map((id) => topicPlaceholder(id, `Tema #${id}`)));
    setExcludedTerms((config.excluded_topic_ids || []).map((id) => topicPlaceholder(id, `Tema #${id}`)));
  };

  const lines = (value: string) => value.split(/\n|,/).map((item) => item.trim()).filter(Boolean);

  const save = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!form.name.trim()) return;
    setSaving(true);
    try {
      const payload = {
        name: form.name.trim(),
        description: form.description.trim() || null,
        status: editing?.status || "active",
        language: form.language,
        country_code: form.country_code,
        days_back: Number(form.days_back),
        min_views: Number(form.min_views),
        max_results_per_query: Number(form.max_results_per_query),
        sources_json: ["youtube", "google_news"],
        keywords_json: lines(form.keywords),
        negative_keywords_json: lines(form.negative_keywords),
        youtube_categories_json: lines(form.youtube_categories),
        included_topic_ids: includedTerms.map((term) => term.entity_id).filter((id): id is number => id !== null),
        excluded_topic_ids: excludedTerms.map((term) => term.entity_id).filter((id): id is number => id !== null),
        minimum_topic_confidence: Number(form.minimum_topic_confidence),
        minimum_performance_ratio: form.minimum_performance_ratio > 0 ? Number(form.minimum_performance_ratio) : null,
      };
      if (editing) await updateSearchConfig(editing.id, payload);
      else await createSearchConfig(payload);
      toast.success(editing ? "Pesquisa atualizada" : "Pesquisa criada");
      resetEditor();
      await load();
    } catch (error: any) {
      toast.error("Não foi possível salvar", { description: error.message });
    } finally {
      setSaving(false);
    }
  };

  const run = async (config: SearchConfig) => {
    try {
      setRunningId(config.id);
      await runSearchConfig(config.id);
      toast.success(`Pesquisa “${config.name}” enviada para execução`);
    } catch (error: any) {
      toast.error("Não foi possível executar", { description: error.message });
    } finally {
      setRunningId(null);
    }
  };

  const editorOpen = creating || editing !== null;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 border-b border-slate-800 pb-5 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight text-white">Pesquisas</h2>
          <p className="mt-1 max-w-2xl text-sm text-slate-400">Combine palavras-chave com temas detectados, séries, categorias oficiais e filtros de breakout. A consulta de coleta não precisa ser igual à classificação final.</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => void load()} className="flex h-10 w-10 items-center justify-center rounded-lg border border-slate-800 bg-slate-950 text-slate-400 hover:text-white"><RefreshCw className="h-4 w-4" /></button>
          <button onClick={openCreate} className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500"><Plus className="h-4 w-4" /> Nova pesquisa</button>
        </div>
      </div>

      <div className="relative max-w-xl">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
        <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Filtrar pesquisas salvas..." className="w-full rounded-lg border border-slate-800 bg-slate-950 py-2.5 pl-9 pr-4 text-sm text-slate-200 outline-none focus:border-indigo-500" />
      </div>

      {loading ? (
        <div className="flex h-48 items-center justify-center"><Loader2 className="h-7 w-7 animate-spin text-indigo-400" /></div>
      ) : visibleConfigs.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-800 py-16 text-center text-sm text-slate-500">Nenhuma pesquisa encontrada.</div>
      ) : (
        <div className="grid gap-4 xl:grid-cols-2">
          {visibleConfigs.map((config) => (
            <article key={config.id} className="rounded-xl border border-slate-800 bg-[#0b101c]/45 p-5">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2"><h3 className="font-bold text-white">{config.name}</h3><span className="rounded border border-slate-800 px-2 py-0.5 text-[10px] uppercase text-slate-500">{config.status}</span></div>
                  {config.description && <p className="mt-2 text-sm text-slate-400">{config.description}</p>}
                </div>
                <div className="flex gap-1">
                  <button onClick={() => openEdit(config)} className="rounded p-2 text-slate-400 hover:bg-slate-800 hover:text-white" title="Editar"><Edit className="h-4 w-4" /></button>
                  <button onClick={() => void run(config)} disabled={runningId === config.id || config.status !== "active"} className="rounded p-2 text-indigo-400 hover:bg-indigo-500/10 disabled:opacity-30" title="Executar">{runningId === config.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}</button>
                </div>
              </div>
              <div className="mt-4 flex flex-wrap gap-2 text-xs">
                <span className="rounded bg-slate-900 px-2 py-1 text-slate-400">{config.days_back} dias</span>
                <span className="rounded bg-slate-900 px-2 py-1 text-slate-400">≥ {Number(config.min_views || 0).toLocaleString("pt-BR")} views</span>
                {(config.minimum_performance_ratio || 0) > 0 && <span className="rounded bg-emerald-500/10 px-2 py-1 text-emerald-400">≥ {config.minimum_performance_ratio}× canal</span>}
                {(config.included_topic_ids || []).length > 0 && <span className="rounded bg-indigo-500/10 px-2 py-1 text-indigo-400">{config.included_topic_ids.length} temas estruturados</span>}
              </div>
              {(config.keywords_json || []).length > 0 && <div className="mt-4 text-xs text-slate-500"><span className="font-semibold text-slate-400">Queries:</span> {config.keywords_json.join(" · ")}</div>}
            </article>
          ))}
        </div>
      )}

      {editorOpen && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-black/70 p-4">
          <form onSubmit={save} className="mx-auto my-8 w-full max-w-3xl space-y-5 rounded-2xl border border-slate-800 bg-[#090d16] p-6 shadow-2xl">
            <div className="flex items-center justify-between"><div><h3 className="text-xl font-bold text-white">{editing ? "Editar pesquisa" : "Nova pesquisa"}</h3><p className="mt-1 text-xs text-slate-500">Use keywords para coleta e temas estruturados para decidir o que realmente pertence à pesquisa.</p></div><button type="button" onClick={resetEditor} className="text-slate-500 hover:text-white"><X className="h-5 w-5" /></button></div>

            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Nome"><input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="input" placeholder="Minecraft breakout" /></Field>
              <Field label="Descrição"><input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className="input" placeholder="Vídeos fora da curva..." /></Field>
            </div>

            <div className="grid gap-3 md:grid-cols-3">
              <Field label="Últimos dias"><input type="number" min="1" value={form.days_back} onChange={(e) => setForm({ ...form, days_back: Number(e.target.value) })} className="input" /></Field>
              <Field label="Views mínimas"><input type="number" min="0" value={form.min_views} onChange={(e) => setForm({ ...form, min_views: Number(e.target.value) })} className="input" /></Field>
              <Field label="Breakout mínimo"><input type="number" min="0" step="0.1" value={form.minimum_performance_ratio || ""} onChange={(e) => setForm({ ...form, minimum_performance_ratio: Number(e.target.value) })} className="input" placeholder="2.0" /></Field>
            </div>

            <Field label="Temas / subtemas / formatos / séries incluídos">
              <DiscoveryAutocomplete selected={includedTerms} onChange={setIncludedTerms} entityOnly placeholder="Ex: Minecraft, Analog Horror, Roleplay..." />
            </Field>
            <Field label="Excluir temas">
              <DiscoveryAutocomplete selected={excludedTerms} onChange={setExcludedTerms} entityOnly placeholder="Temas que não devem entrar..." />
            </Field>

            <div className="grid gap-3 sm:grid-cols-2">
              <Field label={`Confiança temática mínima (${Math.round(form.minimum_topic_confidence * 100)}%)`}><input type="range" min="0" max="1" step="0.05" value={form.minimum_topic_confidence} onChange={(e) => setForm({ ...form, minimum_topic_confidence: Number(e.target.value) })} className="w-full" /></Field>
              <Field label="Máximo por query"><input type="number" min="1" max="200" value={form.max_results_per_query} onChange={(e) => setForm({ ...form, max_results_per_query: Number(e.target.value) })} className="input" /></Field>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Keywords de coleta (uma por linha)"><textarea rows={5} value={form.keywords} onChange={(e) => setForm({ ...form, keywords: e.target.value })} className="input resize-none" placeholder={"minecraft horror\nminecraft smp\nanalog horror"} /></Field>
              <Field label="Keywords negativas"><textarea rows={5} value={form.negative_keywords} onChange={(e) => setForm({ ...form, negative_keywords: e.target.value })} className="input resize-none" placeholder={"tutorial básico\ncompilação"} /></Field>
            </div>

            <div className="flex justify-end gap-3 border-t border-slate-800 pt-5"><button type="button" onClick={resetEditor} className="rounded-lg border border-slate-800 px-4 py-2.5 text-sm text-slate-400">Cancelar</button><button disabled={saving} className="flex items-center gap-2 rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-50">{saving && <Loader2 className="h-4 w-4 animate-spin" />}{editing ? "Salvar alterações" : "Criar pesquisa"}</button></div>
          </form>
        </div>
      )}

      <style jsx>{` .input { width: 100%; border-radius: .5rem; border: 1px solid rgb(30 41 59); background: rgb(2 6 23); padding: .625rem .75rem; font-size: .875rem; color: rgb(226 232 240); outline: none; } .input:focus { border-color: rgb(99 102 241); } `}</style>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="block space-y-2"><span className="text-xs font-bold uppercase tracking-wider text-slate-500">{label}</span>{children}</label>;
}
