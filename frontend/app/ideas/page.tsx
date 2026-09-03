"use client";

import { useCallback, useEffect, useState } from "react";
import { Archive, Lightbulb, Loader2, Pencil, Plus, Search, Trash2, X } from "lucide-react";
import { toast } from "sonner";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const ACTIVE_STATUSES = ["idea", "researching", "ready", "archived"] as const;

type Idea = {
  id: number;
  title: string;
  description: string | null;
  niche: string | null;
  status: string;
  priority: number;
  created_at: string;
  updated_at: string;
};

type IdeaList = { items: Idea[]; total: number; limit: number; offset: number };

type IdeaDraft = {
  title: string;
  description: string;
  niche: string;
  status: string;
  priority: number;
};

const emptyDraft: IdeaDraft = { title: "", description: "", niche: "", status: "idea", priority: 0 };

const labels: Record<string, string> = {
  idea: "Ideia",
  researching: "Pesquisando",
  ready: "Pronta",
  archived: "Arquivada",
};

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail || `Erro HTTP ${response.status}`);
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}

export default function IdeasPage() {
  const [ideas, setIdeas] = useState<Idea[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [editing, setEditing] = useState<Idea | null>(null);
  const [creating, setCreating] = useState(false);
  const [draft, setDraft] = useState<IdeaDraft>(emptyDraft);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const query = new URLSearchParams({ limit: "200" });
      if (search.trim()) query.set("search", search.trim());
      const result = await api<IdeaList>(`/video-projects?${query}`);
      setIdeas(result.items);
    } catch (error: any) {
      toast.error("Erro ao carregar ideias", { description: error.message });
    } finally {
      setLoading(false);
    }
  }, [search]);

  useEffect(() => {
    const timer = setTimeout(load, 250);
    return () => clearTimeout(timer);
  }, [load]);

  const openCreate = () => {
    setEditing(null);
    setDraft(emptyDraft);
    setCreating(true);
  };

  const openEdit = (idea: Idea) => {
    setEditing(idea);
    setCreating(false);
    setDraft({
      title: idea.title,
      description: idea.description || "",
      niche: idea.niche || "",
      status: ACTIVE_STATUSES.includes(idea.status as any) ? idea.status : "idea",
      priority: idea.priority,
    });
  };

  const closeEditor = () => {
    setEditing(null);
    setCreating(false);
    setDraft(emptyDraft);
  };

  const save = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!draft.title.trim()) return;
    setSaving(true);
    try {
      const payload = {
        title: draft.title.trim(),
        description: draft.description.trim() || null,
        niche: draft.niche.trim() || null,
        status: draft.status,
        priority: Number(draft.priority) || 0,
      };
      if (editing) {
        await api(`/video-projects/${editing.id}`, { method: "PATCH", body: JSON.stringify(payload) });
        toast.success("Ideia atualizada");
      } else {
        await api("/video-projects", { method: "POST", body: JSON.stringify(payload) });
        toast.success("Ideia criada");
      }
      closeEditor();
      await load();
    } catch (error: any) {
      toast.error("Não foi possível salvar", { description: error.message });
    } finally {
      setSaving(false);
    }
  };

  const archive = async (idea: Idea) => {
    try {
      await api(`/video-projects/${idea.id}/archive`, { method: "POST" });
      await load();
    } catch (error: any) {
      toast.error("Não foi possível arquivar", { description: error.message });
    }
  };

  const remove = async (idea: Idea) => {
    if (!window.confirm(`Excluir a ideia "${idea.title}"?`)) return;
    try {
      await api(`/video-projects/${idea.id}`, { method: "DELETE" });
      toast.success("Ideia excluída");
      await load();
    } catch (error: any) {
      toast.error("Não foi possível excluir", { description: error.message });
    }
  };

  const editorOpen = creating || editing !== null;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 border-b border-slate-800 pb-5 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight text-white">Ideias</h2>
          <p className="mt-1 text-sm text-slate-400">Guarde ideias simples e volte às referências quando for montar o roteiro fora do Content Radar.</p>
        </div>
        <button onClick={openCreate} className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500">
          <Plus className="h-4 w-4" /> Nova ideia
        </button>
      </div>

      <div className="relative max-w-xl">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
        <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Pesquisar ideias..." className="w-full rounded-lg border border-slate-800 bg-slate-950 py-2.5 pl-10 pr-4 text-sm text-slate-200 outline-none focus:border-indigo-500" />
      </div>

      {loading ? (
        <div className="flex h-48 items-center justify-center"><Loader2 className="h-7 w-7 animate-spin text-indigo-400" /></div>
      ) : ideas.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-800 py-20 text-center text-slate-500">Nenhuma ideia encontrada.</div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {ideas.map((idea) => {
            const legacy = !ACTIVE_STATUSES.includes(idea.status as any);
            return (
              <article key={idea.id} className="rounded-xl border border-slate-800 bg-[#0b101c]/60 p-5">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="mb-2 flex flex-wrap items-center gap-2">
                      <span className="rounded-full border border-slate-700 px-2 py-0.5 text-[11px] font-semibold text-slate-300">{legacy ? `Legado: ${idea.status}` : labels[idea.status]}</span>
                      {idea.niche && <span className="text-xs text-indigo-400">{idea.niche}</span>}
                    </div>
                    <h3 className="font-semibold text-white">{idea.title}</h3>
                  </div>
                  <Lightbulb className="h-4 w-4 shrink-0 text-slate-600" />
                </div>
                {idea.description && <p className="mt-3 line-clamp-4 text-sm leading-relaxed text-slate-400">{idea.description}</p>}
                <div className="mt-5 flex items-center justify-between border-t border-slate-800 pt-4">
                  <span className="text-xs text-slate-600">Prioridade {idea.priority}</span>
                  <div className="flex gap-1">
                    <button onClick={() => openEdit(idea)} title="Editar" className="rounded p-2 text-slate-400 hover:bg-slate-800 hover:text-white"><Pencil className="h-4 w-4" /></button>
                    {idea.status !== "archived" && <button onClick={() => archive(idea)} title="Arquivar" className="rounded p-2 text-slate-400 hover:bg-slate-800 hover:text-white"><Archive className="h-4 w-4" /></button>}
                    <button onClick={() => remove(idea)} title="Excluir" className="rounded p-2 text-slate-500 hover:bg-rose-950/30 hover:text-rose-400"><Trash2 className="h-4 w-4" /></button>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      )}

      {editorOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/65 p-4">
          <form onSubmit={save} className="w-full max-w-lg space-y-4 rounded-xl border border-slate-800 bg-[#0b101c] p-6 shadow-2xl">
            <div className="flex items-center justify-between"><h3 className="text-lg font-bold text-white">{editing ? "Editar ideia" : "Nova ideia"}</h3><button type="button" onClick={closeEditor} className="text-slate-500 hover:text-white"><X className="h-5 w-5" /></button></div>
            <input required value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })} placeholder="Título da ideia" className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3.5 py-2.5 text-sm text-white outline-none focus:border-indigo-500" />
            <textarea rows={5} value={draft.description} onChange={(e) => setDraft({ ...draft, description: e.target.value })} placeholder="O que você pretende fazer nesse vídeo?" className="w-full resize-none rounded-lg border border-slate-800 bg-slate-950 px-3.5 py-2.5 text-sm text-white outline-none focus:border-indigo-500" />
            <div className="grid gap-3 sm:grid-cols-2">
              <input value={draft.niche} onChange={(e) => setDraft({ ...draft, niche: e.target.value })} placeholder="Nicho / assunto" className="rounded-lg border border-slate-800 bg-slate-950 px-3.5 py-2.5 text-sm text-white outline-none focus:border-indigo-500" />
              <select value={draft.status} onChange={(e) => setDraft({ ...draft, status: e.target.value })} className="rounded-lg border border-slate-800 bg-slate-950 px-3.5 py-2.5 text-sm text-white outline-none focus:border-indigo-500">
                <option value="idea">Ideia</option><option value="researching">Pesquisando</option><option value="ready">Pronta</option><option value="archived">Arquivada</option>
              </select>
            </div>
            <input type="number" value={draft.priority} onChange={(e) => setDraft({ ...draft, priority: Number(e.target.value) })} placeholder="Prioridade" className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3.5 py-2.5 text-sm text-white outline-none focus:border-indigo-500" />
            <button disabled={saving} className="flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-600 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-50">{saving && <Loader2 className="h-4 w-4 animate-spin" />}{editing ? "Salvar" : "Criar ideia"}</button>
          </form>
        </div>
      )}
    </div>
  );
}
