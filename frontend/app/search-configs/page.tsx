"use client";

import { useEffect, useState, useCallback } from "react";
import {
  getSearchConfigs,
  createSearchConfig,
  updateSearchConfig,
  runSearchConfig,
  getSearchConfigRuns
} from "@/lib/api";
import {
  Search,
  Plus,
  Play,
  Edit,
  History,
  Loader2,
  CheckCircle,
  XCircle,
  AlertCircle,
  Save,
  Trash2,
  FolderOpen,
  ChevronRight,
  RefreshCw,
  Info
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { formatDate } from "@/lib/format";

interface SearchConfigData {
  id: number;
  name: string;
  description: string | null;
  status: "active" | "paused" | "archived";
  language: string;
  country_code: string;
  region_code: string | null;
  days_back: number;
  min_views: number;
  max_results_per_query: number;
  sources_json: string[];
  keywords_json: string[];
  negative_keywords_json: string[];
  youtube_categories_json: string[];
  created_at: string;
  updated_at: string;
}

interface SearchRunData {
  id: number;
  search_config_id: number;
  status: "queued" | "running" | "completed" | "failed";
  trigger_source: string;
  started_at: string | null;
  finished_at: string | null;
  items_found: number;
  items_inserted: number;
  items_updated: number;
  error_message: string | null;
  created_at: string;
}

export default function SearchConfigsPage() {
  const [configs, setConfigs] = useState<SearchConfigData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Active / Selected state
  const [selectedConfig, setSelectedConfig] = useState<SearchConfigData | null>(null);
  const [runs, setRuns] = useState<SearchRunData[]>([]);
  const [loadingRuns, setLoadingRuns] = useState(false);
  const [lastRuns, setLastRuns] = useState<Record<number, SearchRunData>>({});

  // View state: 'details' | 'form'
  const [rightView, setRightView] = useState<'details' | 'form'>('details');
  const [isEditing, setIsEditing] = useState(false); // false for Create, true for Update

  // Form states
  const [formName, setFormName] = useState("");
  const [formDescription, setFormDescription] = useState("");
  const [formStatus, setFormStatus] = useState<"active" | "paused" | "archived">("active");
  const [formLanguage, setFormLanguage] = useState("pt");
  const [formCountryCode, setFormCountryCode] = useState("BR");
  const [formRegionCode, setFormRegionCode] = useState("");
  const [formDaysBack, setFormDaysBack] = useState(5);
  const [formMinViews, setFormMinViews] = useState(30000);
  const [formMaxResults, setFormMaxResults] = useState(50);
  const [formSources, setFormSources] = useState<string[]>(["youtube", "google_news"]);
  const [formKeywordsText, setFormKeywordsText] = useState("");
  const [formNegKeywordsText, setFormNegKeywordsText] = useState("");
  const [formCategoriesText, setFormCategoriesText] = useState("");

  const [formSubmitting, setFormSubmitting] = useState(false);
  const [triggeringId, setTriggeringId] = useState<number | null>(null);

  // Fetch configs list
  const loadConfigs = useCallback(async (autoSelectId?: number) => {
    try {
      setLoading(true);
      setError(null);
      const res = await getSearchConfigs();
      setConfigs(res.configs);

      // Load runs statistics for each config to show the last execution status
      const lastRunsMap: Record<number, SearchRunData> = {};
      await Promise.all(
        res.configs.map(async (c: SearchConfigData) => {
          try {
            const configRuns = await getSearchConfigRuns(c.id);
            if (configRuns && configRuns.length > 0) {
              lastRunsMap[c.id] = configRuns[0]; // Most recent run
            }
          } catch {
            // Silently skip if one config fails to fetch runs
          }
        })
      );
      setLastRuns(lastRunsMap);

      // Restore active configuration selection
      if (autoSelectId) {
        const found = res.configs.find((c: SearchConfigData) => c.id === autoSelectId);
        if (found) {
          setSelectedConfig(found);
          loadRuns(found.id);
        }
      } else if (res.configs.length > 0) {
        setSelectedConfig(res.configs[0]);
        loadRuns(res.configs[0].id);
      } else {
        setSelectedConfig(null);
        setRuns([]);
      }
    } catch (err: any) {
      setError(err.message || "Erro ao carregar nichos de pesquisa.");
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch runs list for a config
  const loadRuns = async (configId: number) => {
    try {
      setLoadingRuns(true);
      const runsList = await getSearchConfigRuns(configId);
      setRuns(runsList);
    } catch {
      toast.error("Não foi possível carregar o histórico de buscas");
    } finally {
      setLoadingRuns(false);
    }
  };

  useEffect(() => {
    loadConfigs();
  }, [loadConfigs]);

  const handleSelectConfig = (config: SearchConfigData) => {
    setSelectedConfig(config);
    setRightView('details');
    loadRuns(config.id);
  };

  // Trigger manual search execution
  const handleTriggerRun = async (e: React.MouseEvent, config: SearchConfigData) => {
    e.stopPropagation();
    if (config.status !== "active") {
      toast.error("Só é possível rodar buscas para nichos com status 'ATIVO'");
      return;
    }

    setTriggeringId(config.id);
    toast.info("Enfileirando busca...", {
      description: `Iniciando varredura para "${config.name}"`,
    });

    try {
      const run = await runSearchConfig(config.id);
      
      toast.success("Busca enfileirada com sucesso!", {
        description: run.error_message || "O workflow do n8n foi acionado para execução em background.",
      });

      // Reload config runs history
      loadConfigs(config.id);
    } catch (err: any) {
      toast.error("Falha ao iniciar busca", {
        description: err.message || "Erro de conexão com o servidor",
      });
    } finally {
      setTriggeringId(null);
    }
  };

  // Toggle Source Checkbox
  const handleSourceToggle = (source: string) => {
    if (formSources.includes(source)) {
      setFormSources(formSources.filter(s => s !== source));
    } else {
      setFormSources([...formSources, source]);
    }
  };

  // Open Create Form
  const handleOpenCreate = () => {
    setIsEditing(false);
    setFormName("");
    setFormDescription("");
    setFormStatus("active");
    setFormLanguage("pt");
    setFormCountryCode("BR");
    setFormRegionCode("");
    setFormDaysBack(5);
    setFormMinViews(30000);
    setFormMaxResults(50);
    setFormSources(["youtube", "google_news"]);
    setFormKeywordsText("");
    setFormNegKeywordsText("");
    setFormCategoriesText("");

    setRightView('form');
  };

  // Open Edit Form
  const handleOpenEdit = (e: React.MouseEvent, config: SearchConfigData) => {
    e.stopPropagation();
    setIsEditing(true);
    setFormName(config.name);
    setFormDescription(config.description || "");
    setFormStatus(config.status);
    setFormLanguage(config.language);
    setFormCountryCode(config.country_code);
    setFormRegionCode(config.region_code || "");
    setFormDaysBack(config.days_back);
    setFormMinViews(config.min_views);
    setFormMaxResults(config.max_results_per_query);
    setFormSources(config.sources_json || []);
    setFormKeywordsText(config.keywords_json ? config.keywords_json.join("\n") : "");
    setFormNegKeywordsText(config.negative_keywords_json ? config.negative_keywords_json.join("\n") : "");
    setFormCategoriesText(config.youtube_categories_json ? config.youtube_categories_json.join("\n") : "");

    setRightView('form');
  };

  // Form Submit Handler
  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formName.trim()) {
      toast.error("O nome do nicho é obrigatório");
      return;
    }

    const keywords = formKeywordsText
      .split("\n")
      .map(k => k.trim())
      .filter(Boolean);

    if (keywords.length === 0) {
      toast.error("É necessário informar ao menos uma palavra-chave para a pesquisa");
      return;
    }

    const negativeKeywords = formNegKeywordsText
      .split("\n")
      .map(k => k.trim())
      .filter(Boolean);

    const categories = formCategoriesText
      .split("\n")
      .map(c => c.trim())
      .filter(Boolean);

    if (formSources.length === 0) {
      toast.error("Selecione ao menos uma fonte de busca (YouTube ou Google News)");
      return;
    }

    const payload = {
      name: formName.trim(),
      description: formDescription.trim() || null,
      status: formStatus,
      language: formLanguage.trim(),
      country_code: formCountryCode.trim(),
      region_code: formRegionCode.trim() || null,
      days_back: formDaysBack,
      min_views: formMinViews,
      max_results_per_query: formMaxResults,
      sources_json: formSources,
      keywords_json: keywords,
      negative_keywords_json: negativeKeywords,
      youtube_categories_json: categories,
    };

    setFormSubmitting(true);
    try {
      if (isEditing && selectedConfig) {
        const updated = await updateSearchConfig(selectedConfig.id, payload);
        toast.success("Nicho atualizado com sucesso!");
        loadConfigs(updated.id);
      } else {
        const created = await createSearchConfig(payload);
        toast.success("Nicho de pesquisa criado com sucesso!");
        loadConfigs(created.id);
      }
    } catch (err: any) {
      toast.error("Erro ao salvar configuração", {
        description: err.message || "Erro desconhecido",
      });
    } finally {
      setFormSubmitting(false);
    }
  };

  // Status visual badge configs
  const getStatusBadge = (status: string) => {
    switch (status) {
      case "active":
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
      case "paused":
        return "bg-amber-500/10 text-amber-400 border-amber-500/20";
      case "archived":
        return "bg-slate-500/10 text-slate-450 border-slate-500/20";
      default:
        return "bg-slate-500/10 text-slate-400 border-slate-500/20";
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case "active": return "Ativo";
      case "paused": return "Pausado";
      case "archived": return "Arquivado";
      default: return status;
    }
  };

  const getRunStatusIcon = (status: string) => {
    switch (status) {
      case "queued":
        return <Loader2 className="h-3.5 w-3.5 text-slate-400 animate-pulse" />;
      case "running":
        return <Loader2 className="h-3.5 w-3.5 text-blue-400 animate-spin" />;
      case "completed":
        return <CheckCircle className="h-3.5 w-3.5 text-emerald-400" />;
      case "failed":
        return <XCircle className="h-3.5 w-3.5 text-rose-400" />;
    }
  };

  const getRunStatusText = (status: string) => {
    switch (status) {
      case "queued": return "Fila (Aguardando)";
      case "running": return "Executando...";
      case "completed": return "Sucesso";
      case "failed": return "Falhou";
      default: return status;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header section */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-slate-850 pb-5">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white sm:text-3xl font-sans">
            Nichos e Fontes de Pesquisa
          </h2>
          <p className="mt-1 text-sm text-slate-400">
            Configure as palavras-chave e parâmetros de raspagem utilizados pelos workflows de inteligência.
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => loadConfigs(selectedConfig?.id)}
            className="flex h-10 w-10 items-center justify-center rounded-lg border border-slate-800 bg-[#0b101c] hover:bg-slate-900 text-slate-400 hover:text-slate-200 transition-colors"
            title="Atualizar lista"
          >
            <RefreshCw className="h-4.5 w-4.5" />
          </button>
          <button
            onClick={handleOpenCreate}
            className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-md shadow-indigo-600/15 hover:bg-indigo-500 transition-all select-none"
          >
            <Plus className="h-4.5 w-4.5" />
            <span>Novo Nicho</span>
          </button>
        </div>
      </div>

      {loading && configs.length === 0 ? (
        <div className="flex h-[50vh] flex-col items-center justify-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
          <span className="text-sm text-slate-400 font-medium">Carregando configurações de busca...</span>
        </div>
      ) : error ? (
        <div className="rounded-xl border border-rose-950 bg-rose-950/20 p-5 text-rose-200 shadow-md">
          <div className="flex items-center gap-3">
            <AlertCircle className="h-6 w-6 text-rose-400" />
            <div>
              <h3 className="font-bold text-white">Erro ao conectar à API</h3>
              <p className="text-xs text-rose-350">{error}</p>
            </div>
          </div>
        </div>
      ) : (
        <div className="grid gap-6 lg:grid-cols-3 items-start">
          {/* Left Column: Configurations list */}
          <div className="space-y-4 lg:col-span-1 max-h-[calc(100vh-12rem)] overflow-y-auto pr-1">
            {configs.length === 0 ? (
              <div className="rounded-xl border border-dashed border-slate-800 bg-slate-950/20 p-8 text-center text-slate-500 font-medium">
                Nenhum nicho cadastrado. Clique em "Novo Nicho" para começar.
              </div>
            ) : (
              configs.map((config) => {
                const isSelected = selectedConfig?.id === config.id;
                const lastRun = lastRuns[config.id];
                const isTriggering = triggeringId === config.id;

                return (
                  <div
                    key={config.id}
                    onClick={() => handleSelectConfig(config)}
                    className={cn(
                      "group relative cursor-pointer rounded-xl border p-4.5 transition-all select-none flex flex-col gap-3",
                      isSelected
                        ? "border-indigo-500 bg-indigo-500/5 shadow-md shadow-indigo-950/10"
                        : "border-slate-800/80 bg-[#0b101c]/30 hover:border-slate-700/80 hover:bg-[#0c1222]/50"
                    )}
                  >
                    {/* Primary top row */}
                    <div className="flex items-start justify-between gap-2">
                      <div className="space-y-1">
                        <h3 className="font-bold text-slate-200 group-hover:text-white transition-colors leading-tight">
                          {config.name}
                        </h3>
                        <p className="text-xs text-slate-450 line-clamp-2 pr-2">
                          {config.description || "Sem descrição cadastrada"}
                        </p>
                      </div>
                      <span className={cn("inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-bold tracking-wide uppercase shrink-0", getStatusBadge(config.status))}>
                        {getStatusLabel(config.status)}
                      </span>
                    </div>

                    {/* Metadata tags */}
                    <div className="flex flex-wrap gap-1.5 pt-1 text-[10px] font-mono text-slate-400 font-medium">
                      <span className="rounded bg-slate-900 px-1.5 py-0.5 border border-slate-800/40">
                        Fontes: {config.sources_json?.join(", ")}
                      </span>
                      <span className="rounded bg-slate-900 px-1.5 py-0.5 border border-slate-800/40">
                        {config.keywords_json?.length || 0} Kw
                      </span>
                    </div>

                    {/* Footer Execution Status */}
                    <div className="flex items-center justify-between border-t border-slate-800/40 pt-3 mt-1">
                      {lastRun ? (
                        <div className="flex items-center gap-1.5 text-xs text-slate-400 font-medium">
                          {getRunStatusIcon(lastRun.status)}
                          <span className="text-[11px] truncate max-w-[120px]">
                            {getRunStatusText(lastRun.status)} ({formatDate(lastRun.created_at).split(" ")[0]})
                          </span>
                        </div>
                      ) : (
                        <span className="text-[10px] text-slate-500 italic">Nunca executado</span>
                      )}

                      {/* Quick Action buttons */}
                      <div className="flex gap-2 shrink-0">
                        <button
                          onClick={(e) => handleOpenEdit(e, config)}
                          className="flex h-7.5 w-7.5 items-center justify-center rounded-lg border border-slate-800 bg-slate-950/30 text-slate-400 hover:border-slate-600 hover:text-slate-200 hover:bg-slate-900 transition-colors"
                          title="Editar Nicho"
                          aria-label="Editar"
                        >
                          <Edit className="h-3.5 w-3.5" />
                        </button>
                        <button
                          onClick={(e) => handleTriggerRun(e, config)}
                          disabled={config.status !== "active" || isTriggering}
                          className="flex h-7.5 w-7.5 items-center justify-center rounded-lg border border-slate-800 bg-slate-950/40 text-emerald-400 hover:border-emerald-500/30 hover:bg-emerald-600/10 hover:text-emerald-300 transition-colors disabled:opacity-35 disabled:hover:bg-transparent disabled:hover:text-emerald-400 disabled:cursor-not-allowed"
                          title="Buscar Agora"
                          aria-label="Disparar varredura"
                        >
                          {isTriggering ? (
                            <Loader2 className="h-3.5 w-3.5 animate-spin" />
                          ) : (
                            <Play className="h-3.5 w-3.5 fill-current" />
                          )}
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* Right Column: Dynamic config form or active runs history details */}
          <div className="lg:col-span-2">
            {rightView === 'details' && selectedConfig ? (
              <div className="rounded-xl border border-slate-800 bg-[#0b101c]/30 p-6 backdrop-blur-sm space-y-6">
                {/* Header detail */}
                <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between border-b border-slate-800/60 pb-5">
                  <div>
                    <h3 className="text-xl font-bold text-white leading-tight">{selectedConfig.name}</h3>
                    <p className="mt-1 text-sm text-slate-400">{selectedConfig.description || "Sem descrição"}</p>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={(e) => handleOpenEdit(e, selectedConfig)}
                      className="flex items-center gap-1.5 rounded-lg border border-slate-800 bg-slate-950 px-3.5 py-2 text-xs font-semibold text-slate-300 hover:bg-slate-900 hover:text-white transition-colors"
                    >
                      <Edit className="h-3.5 w-3.5" />
                      <span>Editar</span>
                    </button>
                    <button
                      onClick={(e) => handleTriggerRun(e, selectedConfig)}
                      disabled={selectedConfig.status !== "active" || triggeringId === selectedConfig.id}
                      className="flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3.5 py-2 text-xs font-semibold text-white shadow hover:bg-emerald-500 disabled:opacity-40 transition-colors"
                    >
                      {triggeringId === selectedConfig.id ? (
                        <>
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                          <span>Enfileirando...</span>
                        </>
                      ) : (
                        <>
                          <Play className="h-3.5 w-3.5 fill-current" />
                          <span>Buscar agora</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>

                {/* Configuration Metadata Table Grid */}
                <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-3 bg-slate-950/40 rounded-xl border border-slate-900 p-5 text-xs">
                  <div className="space-y-1">
                    <span className="block font-bold text-slate-500 uppercase tracking-wider text-[9px]">Linguagem / Região</span>
                    <span className="font-semibold text-slate-350 text-xs">
                      {selectedConfig.language} / {selectedConfig.country_code} {selectedConfig.region_code ? `(${selectedConfig.region_code})` : ""}
                    </span>
                  </div>
                  <div className="space-y-1">
                    <span className="block font-bold text-slate-500 uppercase tracking-wider text-[9px]">Histórico de Busca</span>
                    <span className="font-semibold text-slate-350 text-xs">{selectedConfig.days_back} dias atrás</span>
                  </div>
                  <div className="space-y-1">
                    <span className="block font-bold text-slate-500 uppercase tracking-wider text-[9px]">Visualizações Mínimas</span>
                    <span className="font-semibold text-slate-350 text-xs">
                      {selectedConfig.min_views.toLocaleString("pt-BR")} views
                    </span>
                  </div>
                  <div className="space-y-1">
                    <span className="block font-bold text-slate-500 uppercase tracking-wider text-[9px]">Resultados Máximos / Query</span>
                    <span className="font-semibold text-slate-350 text-xs">{selectedConfig.max_results_per_query} resultados</span>
                  </div>
                  <div className="space-y-1 sm:col-span-2">
                    <span className="block font-bold text-slate-500 uppercase tracking-wider text-[9px]">Fontes</span>
                    <span className="font-semibold text-slate-350 text-xs uppercase font-mono">
                      {selectedConfig.sources_json?.join(" + ")}
                    </span>
                  </div>
                </div>

                {/* Keywords List */}
                <div className="space-y-3">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">Palavras-chave Pesquisadas</h4>
                  <div className="flex flex-wrap gap-1.5 bg-slate-950/20 rounded-xl border border-slate-900/60 p-4 max-h-[150px] overflow-y-auto">
                    {selectedConfig.keywords_json?.map((kw, idx) => (
                      <span
                        key={idx}
                        className="rounded bg-[#0c1223] border border-slate-800/80 px-2.5 py-1 text-xs font-medium text-indigo-400 select-text"
                      >
                        {kw}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Negative Keywords List if present */}
                {selectedConfig.negative_keywords_json?.length > 0 && (
                  <div className="space-y-3">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-rose-400/90">Termos Excluídos (Filtro Negativo)</h4>
                    <div className="flex flex-wrap gap-1.5 bg-slate-950/10 rounded-xl border border-rose-950/10 p-4 max-h-[120px] overflow-y-auto">
                      {selectedConfig.negative_keywords_json.map((nkw, idx) => (
                        <span
                          key={idx}
                          className="rounded bg-slate-950/60 border border-rose-950/20 px-2 py-0.5 text-xs text-rose-450 select-text"
                        >
                          {nkw}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Runs execution history */}
                <div className="space-y-4 border-t border-slate-800/60 pt-6">
                  <div className="flex items-center justify-between">
                    <h4 className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-400">
                      <History className="h-4 w-4 text-slate-500" />
                      Histórico Recente de Execuções
                    </h4>
                    <span className="text-[10px] text-slate-500 font-mono">Máx 50 registros</span>
                  </div>

                  {loadingRuns ? (
                    <div className="flex justify-center py-8">
                      <Loader2 className="h-6 w-6 animate-spin text-slate-500" />
                    </div>
                  ) : runs.length === 0 ? (
                    <div className="rounded-xl border border-slate-900 bg-slate-950/20 py-8 text-center text-xs text-slate-500 font-medium">
                      Este nicho ainda não possui histórico de execuções. Clique em "Buscar agora" para iniciar.
                    </div>
                  ) : (
                    <div className="overflow-hidden rounded-xl border border-slate-850 bg-slate-950/30">
                      <div className="max-h-[300px] overflow-y-auto">
                        <table className="w-full text-left text-xs text-slate-300">
                          <thead className="sticky top-0 bg-[#0c1223] text-[10px] font-bold uppercase tracking-wider text-slate-400 border-b border-slate-800">
                            <tr>
                              <th className="px-4 py-3">Iniciado Em</th>
                              <th className="px-4 py-3">Status</th>
                              <th className="px-4 py-3 text-right">Itens Encontrados</th>
                              <th className="px-4 py-3 text-right">Salvos / Atualizados</th>
                              <th className="px-4 py-3">Erro</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-900/50">
                            {runs.map((run) => (
                              <tr key={run.id} className="hover:bg-slate-900/40">
                                <td className="px-4 py-3 font-mono text-[11px] text-slate-400">
                                  {formatDate(run.created_at)}
                                </td>
                                <td className="px-4 py-3">
                                  <span className="inline-flex items-center gap-1 font-semibold text-slate-350">
                                    {getRunStatusIcon(run.status)}
                                    <span className="ml-1 text-[11px]">{getRunStatusText(run.status)}</span>
                                  </span>
                                </td>
                                <td className="px-4 py-3 text-right font-mono font-semibold text-slate-200">
                                  {run.items_found || 0}
                                </td>
                                <td className="px-4 py-3 text-right font-mono font-medium text-slate-400">
                                  {run.items_inserted || 0} / {run.items_updated || 0}
                                </td>
                                <td className="px-4 py-3 text-rose-400 truncate max-w-[150px] font-medium" title={run.error_message || ""}>
                                  {run.error_message || "-"}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ) : rightView === 'form' ? (
              /* Create or Edit config Form */
              <div className="rounded-xl border border-slate-800 bg-[#0b101c]/40 p-6 backdrop-blur-sm space-y-6">
                <div className="flex items-center justify-between border-b border-slate-800/60 pb-5">
                  <h3 className="text-lg font-bold text-white">
                    {isEditing ? "Editar Nicho de Pesquisa" : "Cadastrar Novo Nicho"}
                  </h3>
                  <button
                    onClick={() => {
                      if (selectedConfig) {
                        setRightView('details');
                        loadRuns(selectedConfig.id);
                      } else {
                        setRightView('details');
                      }
                    }}
                    className="text-xs text-slate-450 hover:text-slate-200 font-semibold"
                  >
                    Cancelar
                  </button>
                </div>

                <form onSubmit={handleFormSubmit} className="space-y-5">
                  {/* Name field */}
                  <div className="space-y-2">
                    <label className="text-xs font-bold uppercase tracking-wider text-slate-400">Nome do Nicho</label>
                    <input
                      type="text"
                      value={formName}
                      onChange={(e) => setFormName(e.target.value)}
                      placeholder="Ex: Inteligência Artificial, Astronomia Amadora..."
                      className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3.5 py-2.5 text-sm text-slate-200 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/10 transition-all font-semibold"
                      required
                    />
                  </div>

                  {/* Description field */}
                  <div className="space-y-2">
                    <label className="text-xs font-bold uppercase tracking-wider text-slate-400">Descrição</label>
                    <input
                      type="text"
                      value={formDescription}
                      onChange={(e) => setFormDescription(e.target.value)}
                      placeholder="Breve sumário dos objetivos desse mapeamento..."
                      className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3.5 py-2.5 text-sm text-slate-350 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/10 transition-all"
                    />
                  </div>

                  <div className="grid gap-4 sm:grid-cols-3">
                    {/* Status field */}
                    <div className="space-y-2">
                      <label className="text-xs font-bold uppercase tracking-wider text-slate-400">Status</label>
                      <select
                        value={formStatus}
                        onChange={(e) => setFormStatus(e.target.value as any)}
                        className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2.5 text-sm text-slate-200 outline-none focus:border-indigo-500"
                      >
                        <option value="active">Ativo</option>
                        <option value="paused">Pausado</option>
                        <option value="archived">Arquivado</option>
                      </select>
                    </div>

                    {/* Language field */}
                    <div className="space-y-2">
                      <label className="text-xs font-bold uppercase tracking-wider text-slate-400">Idioma</label>
                      <input
                        type="text"
                        value={formLanguage}
                        onChange={(e) => setFormLanguage(e.target.value)}
                        placeholder="pt"
                        className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-200 outline-none focus:border-indigo-500 text-center font-semibold"
                      />
                    </div>

                    {/* Country code field */}
                    <div className="space-y-2">
                      <label className="text-xs font-bold uppercase tracking-wider text-slate-400">Cód País</label>
                      <input
                        type="text"
                        value={formCountryCode}
                        onChange={(e) => setFormCountryCode(e.target.value)}
                        placeholder="BR"
                        className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-200 outline-none focus:border-indigo-500 text-center font-semibold"
                      />
                    </div>
                  </div>

                  <div className="grid gap-4 sm:grid-cols-3">
                    {/* Days back field */}
                    <div className="space-y-2">
                      <label className="text-xs font-bold uppercase tracking-wider text-slate-400">Varredura (Dias)</label>
                      <input
                        type="number"
                        min="1"
                        max="90"
                        value={formDaysBack}
                        onChange={(e) => setFormDaysBack(parseInt(e.target.value) || 5)}
                        className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-200 outline-none focus:border-indigo-500 text-center"
                      />
                    </div>

                    {/* Min views field */}
                    <div className="space-y-2">
                      <label className="text-xs font-bold uppercase tracking-wider text-slate-400">Views Mínimas</label>
                      <input
                        type="number"
                        min="0"
                        value={formMinViews}
                        onChange={(e) => setFormMinViews(parseInt(e.target.value) || 0)}
                        className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-200 outline-none focus:border-indigo-500 text-center"
                      />
                    </div>

                    {/* Max results field */}
                    <div className="space-y-2">
                      <label className="text-xs font-bold uppercase tracking-wider text-slate-400">Max Results / Query</label>
                      <input
                        type="number"
                        min="5"
                        max="200"
                        value={formMaxResults}
                        onChange={(e) => setFormMaxResults(parseInt(e.target.value) || 50)}
                        className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-200 outline-none focus:border-indigo-500 text-center"
                      />
                    </div>
                  </div>

                  {/* Sources field checkboxes */}
                  <div className="space-y-2">
                    <label className="text-xs font-bold uppercase tracking-wider text-slate-400 block mb-1">
                      Fontes de Busca
                    </label>
                    <div className="flex gap-4">
                      <label className="flex items-center gap-2 cursor-pointer text-sm text-slate-350 select-none">
                        <input
                          type="checkbox"
                          checked={formSources.includes("youtube")}
                          onChange={() => handleSourceToggle("youtube")}
                          className="h-4 w-4 rounded border-slate-800 bg-slate-950 text-indigo-600 focus:ring-indigo-500/20"
                        />
                        <span>YouTube (Vídeos / Shorts)</span>
                      </label>
                      <label className="flex items-center gap-2 cursor-pointer text-sm text-slate-350 select-none">
                        <input
                          type="checkbox"
                          checked={formSources.includes("google_news")}
                          onChange={() => handleSourceToggle("google_news")}
                          className="h-4 w-4 rounded border-slate-800 bg-slate-950 text-indigo-600 focus:ring-indigo-500/20"
                        />
                        <span>Google News (Artigos / Notícias)</span>
                      </label>
                    </div>
                  </div>

                  {/* Keywords text area */}
                  <div className="space-y-2">
                    <div className="flex justify-between items-baseline">
                      <label className="text-xs font-bold uppercase tracking-wider text-slate-400">
                        Palavras-chave (Mapeamento Positivo)
                      </label>
                      <span className="text-[10px] text-slate-500">Uma por linha. Obrigatório.</span>
                    </div>
                    <textarea
                      rows={5}
                      value={formKeywordsText}
                      onChange={(e) => setFormKeywordsText(e.target.value)}
                      placeholder="inteligencia artificial&#10;ia no marketing&#10;openai artificial intelligence"
                      className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3.5 py-2.5 text-sm text-slate-250 placeholder-slate-700 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/10 transition-all font-mono resize-none"
                      required
                    />
                  </div>

                  {/* Negative keywords text area */}
                  <div className="space-y-2">
                    <div className="flex justify-between items-baseline">
                      <label className="text-xs font-bold uppercase tracking-wider text-rose-450/90">
                        Termos Excluídos (Filtro Negativo)
                      </label>
                      <span className="text-[10px] text-slate-500">Uma por linha. Opcional.</span>
                    </div>
                    <textarea
                      rows={3}
                      value={formNegKeywordsText}
                      onChange={(e) => setFormNegKeywordsText(e.target.value)}
                      placeholder="curso gratis&#10;vagas de emprego&#10;empresa contrata"
                      className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3.5 py-2.5 text-sm text-slate-250 placeholder-slate-700 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/10 transition-all font-mono resize-none"
                    />
                  </div>

                  {/* Youtube categories text area */}
                  <div className="space-y-2">
                    <div className="flex justify-between items-baseline">
                      <label className="text-xs font-bold uppercase tracking-wider text-slate-400">
                        Categorias do YouTube (IDs de Busca)
                      </label>
                      <span className="text-[10px] text-slate-500">Uma por linha. Opcional (Ex: 28 = Tech, 27 = Educação).</span>
                    </div>
                    <textarea
                      rows={2}
                      value={formCategoriesText}
                      onChange={(e) => setFormCategoriesText(e.target.value)}
                      placeholder="28&#10;27"
                      className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3.5 py-2.5 text-sm text-slate-250 placeholder-slate-700 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/10 transition-all font-mono resize-none"
                    />
                  </div>

                  {/* Submit button */}
                  <button
                    type="submit"
                    disabled={formSubmitting}
                    className="flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-3 text-sm font-semibold text-white shadow-md shadow-indigo-600/15 hover:bg-indigo-500 active:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                  >
                    {formSubmitting ? (
                      <>
                        <Loader2 className="h-4.5 w-4.5 animate-spin" />
                        <span>Salvando Configurações...</span>
                      </>
                    ) : (
                      <>
                        <Save className="h-4.5 w-4.5" />
                        <span>Salvar Nicho</span>
                      </>
                    )}
                  </button>
                </form>
              </div>
            ) : (
              <div className="h-[40vh] rounded-xl border border-dashed border-slate-850 flex flex-col items-center justify-center text-center text-slate-500 p-8">
                <FolderOpen className="h-8 w-8 text-slate-700 mb-2.5" />
                <span className="font-semibold text-sm">Selecione um Nicho de Pesquisa</span>
                <p className="text-xs text-slate-550 mt-1.5 max-w-[300px]">
                  Escolha um nicho na lista lateral para visualizar suas configurações estruturadas e histórico de raspagem.
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
