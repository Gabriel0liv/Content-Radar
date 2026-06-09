"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  getVideoProjects,
  createVideoProject
} from "@/lib/api";
import { VideoProject } from "@/lib/types";
import {
  Search,
  Plus,
  Loader2,
  AlertCircle,
  FileText,
  Clock,
  Tag,
  Monitor,
  FolderClosed,
  ChevronRight,
  TrendingUp,
  X
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { formatDate } from "@/lib/format";

// Status configuration for visual badges
const statusConfig: Record<string, { label: string; class: string }> = {
  idea: { label: "Ideia", class: "bg-indigo-500/10 text-indigo-400 border-indigo-500/20" },
  researching: { label: "Pesquisando", class: "bg-blue-500/10 text-blue-400 border-blue-500/20" },
  scripting: { label: "Roteirizando", class: "bg-amber-500/10 text-amber-400 border-amber-500/20" },
  reviewing: { label: "Revisando", class: "bg-purple-500/10 text-purple-400 border-purple-500/20" },
  ready: { label: "Pronto", class: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" },
  produced: { label: "Produzido", class: "bg-slate-500/10 text-slate-355 border-slate-500/20" },
  archived: { label: "Arquivado", class: "bg-rose-500/10 text-rose-450 border-rose-500/20" }
};

export default function ScriptsPage() {
  const [projects, setProjects] = useState<VideoProject[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filter states
  const [searchText, setSearchText] = useState("");
  const [statusFilter, setStatusFilter] = useState("Todos");
  const [nicheFilter, setNicheFilter] = useState("Todos");
  const [formatFilter, setFormatFilter] = useState("Todos");
  const [limit, setLimit] = useState(24);
  const [offset, setOffset] = useState(0);

  // Create Modal State
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newNiche, setNewNiche] = useState("");
  const [newPlatform, setNewPlatform] = useState("YouTube");
  const [newFormat, setNewFormat] = useState("Video Normal");
  const [newPriority, setNewPriority] = useState(1);
  const [newDescription, setNewDescription] = useState("");
  const [creating, setCreating] = useState(false);

  // Available niches from projects for filtering list
  const [availableNiches, setAvailableNiches] = useState<string[]>([]);

  const loadProjects = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await getVideoProjects({
        limit,
        offset,
        search: searchText,
        status: statusFilter,
        niche: nicheFilter,
        video_format: formatFilter
      });
      setProjects(res.items);
      setTotal(res.total);

      // Extract unique niches for filter helper
      if (nicheFilter === "Todos") {
        const niches = Array.from(new Set(res.items.map(p => p.niche).filter(Boolean))) as string[];
        setAvailableNiches(niches);
      }
    } catch (err: any) {
      setError(err.message || "Erro ao carregar projetos de vídeo.");
    } finally {
      setLoading(false);
    }
  }, [limit, offset, searchText, statusFilter, nicheFilter, formatFilter]);

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  // Reset offset when filter criteria changes
  useEffect(() => {
    setOffset(0);
  }, [searchText, statusFilter, nicheFilter, formatFilter]);

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim()) {
      toast.error("Por favor, preencha o título do projeto.");
      return;
    }

    try {
      setCreating(true);
      await createVideoProject({
        title: newTitle.trim(),
        niche: newNiche.trim() || null,
        target_platform: newPlatform || null,
        video_format: newFormat || null,
        priority: Number(newPriority),
        description: newDescription.trim() || null,
        status: "idea"
      });

      toast.success("Ideia de vídeo criada com sucesso!");
      setIsCreateModalOpen(false);
      setNewTitle("");
      setNewNiche("");
      setNewDescription("");
      loadProjects();
    } catch (err: any) {
      toast.error(`Erro ao criar projeto: ${err.message}`);
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header section */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-slate-850 pb-5">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white sm:text-3xl font-sans">
            Oficina de Vídeos (Workshop)
          </h2>
          <p className="mt-1 text-sm text-slate-400">
            Gerencie ideias, planeje e escreva roteiros, organize referências e esboce conceitos no quadro criativo.
          </p>
        </div>
        <div>
          <button
            onClick={() => setIsCreateModalOpen(true)}
            className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white shadow-md shadow-indigo-600/15 hover:bg-indigo-500 transition-all select-none"
          >
            <Plus className="h-4.5 w-4.5" />
            <span>Nova Ideia</span>
          </button>
        </div>
      </div>

      {/* Filters Bar */}
      <div className="flex flex-col gap-4 bg-[#0b101c]/35 p-5 rounded-xl border border-slate-800 backdrop-blur-sm shadow-md">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-4">
          {/* General Search */}
          <div className="relative col-span-1 sm:col-span-2">
            <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              placeholder="Pesquisar por título ou descrição..."
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              className="w-full rounded-lg border border-slate-800 bg-slate-950 pl-10 pr-4 py-2 text-sm text-slate-200 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/10 transition-all font-medium placeholder:text-slate-500"
            />
          </div>

          {/* Status filter */}
          <div>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-300 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/10 transition-all font-semibold"
            >
              <option value="Todos">Todos os Status</option>
              <option value="idea">Ideia</option>
              <option value="researching">Pesquisando</option>
              <option value="scripting">Roteirizando</option>
              <option value="reviewing">Revisando</option>
              <option value="ready">Pronto</option>
              <option value="produced">Produzido</option>
              <option value="archived">Arquivado</option>
            </select>
          </div>

          {/* Niche filter */}
          <div>
            <select
              value={nicheFilter}
              onChange={(e) => setNicheFilter(e.target.value)}
              className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-300 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/10 transition-all font-semibold"
            >
              <option value="Todos">Todos os Nichos</option>
              {availableNiches.map(niche => (
                <option key={niche} value={niche}>{niche}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Grid List */}
      {loading && projects.length === 0 ? (
        <div className="flex h-[40vh] flex-col items-center justify-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
          <span className="text-sm text-slate-400 font-medium">Carregando oficina de roteiros...</span>
        </div>
      ) : error ? (
        <div className="rounded-xl border border-rose-950 bg-rose-950/20 p-5 text-rose-250 flex items-center gap-3">
          <AlertCircle className="h-5 w-5 text-rose-450 shrink-0" />
          <span className="text-sm">{error}</span>
        </div>
      ) : projects.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-800 bg-slate-950/10 py-24 text-center text-slate-500 font-medium">
          Nenhuma ideia de vídeo encontrada. Comece criando um novo projeto no botão acima!
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((project) => {
            const status = statusConfig[project.status] || { label: project.status, class: "bg-slate-850 text-slate-400" };
            return (
              <Link
                key={project.id}
                href={`/scripts/${project.id}`}
                className="group relative flex flex-col justify-between rounded-xl border border-slate-800/80 bg-[#0b101c]/25 backdrop-blur-sm p-5 hover:border-slate-700/80 hover:bg-[#0c1324]/35 transition-all duration-300 shadow shadow-indigo-950/5 cursor-pointer select-none"
              >
                <div>
                  {/* Title & Status Row */}
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <span className={cn("inline-flex items-center rounded px-2 py-0.5 text-[10px] font-bold border tracking-wide uppercase shadow-sm", status.class)}>
                      {status.label}
                    </span>
                    {project.priority > 0 && (
                      <span className="flex items-center gap-0.5 text-[10px] font-bold text-amber-400 bg-amber-500/5 px-2 py-0.5 rounded border border-amber-500/10 uppercase tracking-wider">
                        <TrendingUp className="h-3 w-3" />
                        P{project.priority}
                      </span>
                    )}
                  </div>

                  {/* Title */}
                  <h4 className="text-base font-bold text-slate-100 group-hover:text-white line-clamp-1 leading-snug transition-colors">
                    {project.title}
                  </h4>
                  {project.working_title && (
                    <span className="block text-xs text-slate-500 font-medium line-clamp-1 italic mb-2.5">
                      Título provisório: {project.working_title}
                    </span>
                  )}

                  {/* Description */}
                  <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed mb-4">
                    {project.description || "Sem descrição disponível."}
                  </p>
                </div>

                {/* Footer specs */}
                <div className="border-t border-slate-850/60 pt-3 mt-1 flex items-center justify-between text-[11px] text-slate-500 font-semibold">
                  <div className="flex items-center gap-3">
                    {project.niche && (
                      <span className="flex items-center gap-1">
                        <Tag className="h-3.5 w-3.5 text-slate-600" />
                        {project.niche}
                      </span>
                    )}
                    {project.video_format && (
                      <span className="flex items-center gap-1">
                        <Monitor className="h-3.5 w-3.5 text-slate-600" />
                        {project.video_format}
                      </span>
                    )}
                  </div>
                  <span className="text-[10px] text-slate-600 font-medium uppercase font-mono">
                    At. {formatDate(project.updated_at)?.split(" ")[0]}
                  </span>
                </div>

                {/* Interactive corner indicator */}
                <ChevronRight className="absolute right-3.5 top-1/2 -translate-y-1/2 h-5 w-5 text-slate-700 opacity-0 group-hover:opacity-100 group-hover:translate-x-1 transition-all" />
              </Link>
            );
          })}
        </div>
      )}

      {/* Create Modal Dialog */}
      {isCreateModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-250">
          <div className="relative w-full max-w-lg rounded-xl border border-slate-800 bg-[#0b101c] p-6 shadow-2xl animate-in zoom-in-95 duration-250">
            {/* Header */}
            <div className="flex items-center justify-between border-b border-slate-850 pb-4 mb-4">
              <h3 className="text-lg font-bold text-white flex items-center gap-2 font-sans">
                <FolderClosed className="h-4.5 w-4.5 text-indigo-400" />
                Nova Ideia de Vídeo
              </h3>
              <button
                type="button"
                onClick={() => setIsCreateModalOpen(false)}
                className="rounded-lg p-1.5 hover:bg-slate-900 text-slate-450 hover:text-slate-200 transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleCreateSubmit} className="space-y-4">
              {/* Title */}
              <div className="space-y-1.5">
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 select-none">Título da Ideia *</label>
                <input
                  type="text"
                  placeholder="Ex: Como programar em Rust do Zero"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3.5 py-2 text-sm text-slate-200 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/10 transition-all font-medium placeholder:text-slate-600"
                  required
                />
              </div>

              {/* Niche & Priority */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 select-none">Nicho / Tema</label>
                  <input
                    type="text"
                    placeholder="Ex: Programação"
                    value={newNiche}
                    onChange={(e) => setNewNiche(e.target.value)}
                    className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3.5 py-2 text-sm text-slate-200 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/10 transition-all font-medium placeholder:text-slate-600"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 select-none">Prioridade</label>
                  <select
                    value={newPriority}
                    onChange={(e) => setNewPriority(Number(e.target.value))}
                    className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3.5 py-2 text-sm text-slate-350 outline-none focus:border-indigo-500 font-semibold"
                  >
                    <option value={0}>Baixa (0)</option>
                    <option value={1}>Média (1)</option>
                    <option value={2}>Alta (2)</option>
                    <option value={3}>Urgente (3)</option>
                  </select>
                </div>
              </div>

              {/* Platform & Format */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 select-none">Plataforma Destino</label>
                  <select
                    value={newPlatform}
                    onChange={(e) => setNewPlatform(e.target.value)}
                    className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3.5 py-2 text-sm text-slate-350 outline-none focus:border-indigo-500 font-semibold"
                  >
                    <option value="YouTube">YouTube</option>
                    <option value="TikTok">TikTok</option>
                    <option value="Instagram">Instagram Reels</option>
                    <option value="Outro">Outro</option>
                  </select>
                </div>

                <div className="space-y-1.5">
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 select-none">Formato do Vídeo</label>
                  <select
                    value={newFormat}
                    onChange={(e) => setNewFormat(e.target.value)}
                    className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3.5 py-2 text-sm text-slate-350 outline-none focus:border-indigo-500 font-semibold"
                  >
                    <option value="Video Normal">Vídeo Normal (Landscape)</option>
                    <option value="Shorts / Reels">Shorts / Reels (Vertical)</option>
                    <option value="Live / Stream">Live / Stream</option>
                  </select>
                </div>
              </div>

              {/* Description */}
              <div className="space-y-1.5">
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-400 select-none">Descrição / Objetivo</label>
                <textarea
                  placeholder="Escreva brevemente qual o objetivo principal deste vídeo..."
                  value={newDescription}
                  onChange={(e) => setNewDescription(e.target.value)}
                  rows={3}
                  className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3.5 py-2 text-sm text-slate-200 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/10 transition-all font-medium placeholder:text-slate-600 resize-none"
                />
              </div>

              {/* Submit Buttons */}
              <div className="flex items-center justify-end gap-3 border-t border-slate-850 pt-4 mt-6">
                <button
                  type="button"
                  onClick={() => setIsCreateModalOpen(false)}
                  className="px-4 py-2 rounded-lg text-xs font-bold text-slate-500 hover:text-slate-300 transition-colors"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={creating || !newTitle.trim()}
                  className="flex items-center justify-center gap-2 rounded-lg bg-indigo-600 px-5 py-2 text-xs font-bold text-white shadow-md shadow-indigo-600/15 hover:bg-indigo-500 disabled:opacity-45 transition-all select-none"
                >
                  {creating ? (
                    <>
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      <span>Criando...</span>
                    </>
                  ) : (
                    <span>Criar Ideia</span>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
