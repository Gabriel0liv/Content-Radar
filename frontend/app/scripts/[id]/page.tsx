"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";

import {
  archiveVideoProject,
  createCanvaBoard,
  createVideoProjectItem,
  createVideoProjectItemFromScriptExcerpt,
  deleteVideoProject,
  deleteVideoProjectItem,
  getExternalBoards,
  getVideoProject,
  getVideoProjectItems,
  refreshCanvaBoardUrl,
  updateVideoProject,
  updateVideoProjectItem,
} from "@/lib/api";
import {
  ExternalBoard,
  VideoProject,
  VideoProjectItem,
  VideoProjectItemType,
} from "@/lib/types";
import {
  ArrowLeft,
  Archive,
  BookOpen,
  CheckSquare,
  ExternalLink,
  FileImage,
  Film,
  FolderKanban,
  Link2,
  Loader2,
  Music,
  Plus,
  RefreshCw,
  Save,
  Sparkles,
  StickyNote,
  Trash2,
  Type,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

type PageTab = "roteiro" | "elementos" | "quadro-externo";
type LibraryFilter = "all" | VideoProjectItemType;

const statusConfig: Record<string, { label: string; className: string }> = {
  idea: { label: "Ideia", className: "border-indigo-500/25 bg-indigo-500/10 text-indigo-300" },
  researching: { label: "Pesquisa", className: "border-sky-500/25 bg-sky-500/10 text-sky-300" },
  scripting: { label: "Roteiro", className: "border-amber-500/25 bg-amber-500/10 text-amber-300" },
  reviewing: { label: "Revisao", className: "border-fuchsia-500/25 bg-fuchsia-500/10 text-fuchsia-300" },
  ready: { label: "Pronto", className: "border-emerald-500/25 bg-emerald-500/10 text-emerald-300" },
  produced: { label: "Produzido", className: "border-slate-500/25 bg-slate-500/10 text-slate-300" },
  archived: { label: "Arquivado", className: "border-rose-500/25 bg-rose-500/10 text-rose-300" },
};

const itemTypeMeta: Record<
  VideoProjectItemType,
  {
    label: string;
    description: string;
    icon: typeof StickyNote;
  }
> = {
  note: { label: "Nota", description: "Ideias e observacoes", icon: StickyNote },
  reference: { label: "Referencia", description: "Link, fonte ou citacao", icon: Link2 },
  script_excerpt: { label: "Trecho", description: "Recorte do roteiro", icon: Type },
  audio: { label: "Musica/SFX", description: "Faixa, trilha ou efeito", icon: Music },
  thumbnail: { label: "Thumbnail", description: "Ideias visuais", icon: FileImage },
  production: { label: "Producao", description: "Passos de execucao", icon: Film },
  todo: { label: "Tarefa", description: "Checklist acionavel", icon: CheckSquare },
  image: { label: "Imagem", description: "Imagem de apoio", icon: FileImage },
  other: { label: "Outro", description: "Elemento generico", icon: Sparkles },
};

function formatBoardLinkExpiry(board: ExternalBoard) {
  const metadata = board.metadata_json;
  const possibleKeys = [
    "expires_at",
    "url_expires_at",
    "temporary_url_expires_at",
    "edit_url_expires_at",
    "view_url_expires_at",
  ];

  for (const key of possibleKeys) {
    const value = metadata?.[key];
    if (typeof value === "string" && value.trim()) {
      return value;
    }
  }

  return null;
}

function getBoardRefreshTimestamp(board: ExternalBoard) {
  const value = board.metadata_json?.canva_last_url_refresh_at;
  return typeof value === "string" && value.trim() ? value : null;
}

export default function VideoWorkspacePage() {
  const router = useRouter();
  const params = useParams();
  const projectId = Number(params.id);

  const [project, setProject] = useState<VideoProject | null>(null);
  const [items, setItems] = useState<VideoProjectItem[]>([]);
  const [externalBoards, setExternalBoards] = useState<ExternalBoard[]>([]);
  const [loading, setLoading] = useState(true);
  const [pageError, setPageError] = useState<string | null>(null);
  const [savingScript, setSavingScript] = useState(false);
  const [creatingExternalBoard, setCreatingExternalBoard] = useState(false);
  const [refreshingBoardId, setRefreshingBoardId] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<PageTab>("roteiro");
  const [libraryFilter, setLibraryFilter] = useState<LibraryFilter>("all");
  const [libraryForm, setLibraryForm] = useState({
    item_type: "note" as VideoProjectItemType,
    title: "",
    body: "",
    url: "",
    status: "open",
    pinned: false,
  });
  const [editingItemId, setEditingItemId] = useState<number | null>(null);
  const [editingItemDraft, setEditingItemDraft] = useState({
    item_type: "note" as VideoProjectItemType,
    title: "",
    body: "",
    url: "",
    status: "open",
    pinned: false,
  });
  const [scriptWordCount, setScriptWordCount] = useState(0);
  const [scriptDuration, setScriptDuration] = useState(0);

  const fetchProjectWorkspace = async (options?: { silentOptionalErrors?: boolean }) => {
    const { silentOptionalErrors = false } = options ?? {};
    const projectResponse = await getVideoProject(projectId);

    setProject(projectResponse);
    setScriptWordCount(projectResponse.word_count);
    setScriptDuration(projectResponse.estimated_duration_seconds || 0);

    try {
      const itemsResponse = await getVideoProjectItems(projectId);
      setItems(itemsResponse);
    } catch (error: any) {
      setItems([]);
      if (!silentOptionalErrors) {
        toast.error(error.message || "Nao foi possivel carregar a biblioteca.");
      }
    }

    try {
      const externalBoardsResponse = await getExternalBoards(projectId);
      setExternalBoards(externalBoardsResponse);
    } catch (error: any) {
      setExternalBoards([]);
      if (!silentOptionalErrors) {
        toast.error(error.message || "Nao foi possivel carregar os boards externos.");
      }
    }
  };

  const editor = useEditor({
    extensions: [StarterKit],
    content: "",
    onUpdate: ({ editor: tiptapEditor }: { editor: { getText(): string } }) => {
      const text = tiptapEditor.getText();
      const words = text.trim() ? text.trim().split(/\s+/).length : 0;
      setScriptWordCount(words);
      setScriptDuration(Math.round((words / 150) * 60));
    },
  });

  useEffect(() => {
    let cancelled = false;

    async function initializeProjectWorkspace() {
      setLoading(true);
      setPageError(null);

      try {
        if (cancelled) {
          return;
        }
        await fetchProjectWorkspace({ silentOptionalErrors: true });
      } catch (error: any) {
        if (cancelled) {
          return;
        }

        setProject(null);
        setItems([]);
        setExternalBoards([]);
        setPageError(error.message || "Nao foi possivel carregar este projeto de video.");
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    initializeProjectWorkspace();

    return () => {
      cancelled = true;
    };
  }, [projectId]);

  const scriptContentJson = project?.script_content_json;
  const scriptText = project?.script_text;

  useEffect(() => {
    if (!editor || !project) {
      return;
    }

    if (scriptContentJson) {
      editor.commands.setContent(scriptContentJson);
      return;
    }

    editor.commands.setContent(scriptText || "<p>Comece a escrever seu roteiro aqui...</p>");
  }, [editor, project?.id, scriptContentJson, scriptText]);

  const filteredItems = useMemo(() => {
    const list = libraryFilter === "all"
      ? items
      : items.filter((item) => item.item_type === libraryFilter);

    return [...list].sort((a, b) => {
      if (a.pinned && !b.pinned) return -1;
      if (!a.pinned && b.pinned) return 1;
      return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
    });
  }, [items, libraryFilter]);

  const canvaBoards = useMemo(
    () => externalBoards.filter((board) => board.provider === "canva"),
    [externalBoards]
  );

  const hiddenLegacyBoardsCount = externalBoards.length - canvaBoards.length;

  const handleReload = async () => {
    setLoading(true);
    setPageError(null);

    try {
      await fetchProjectWorkspace();
    } catch (error: any) {
      setPageError(error.message || "Nao foi possivel recarregar esta oficina.");
    } finally {
      setLoading(false);
    }
  };

  const handleSaveScript = async () => {
    if (!editor || !project) return;

    try {
      setSavingScript(true);
      const updated = await updateVideoProject(projectId, {
        script_text: editor.getText(),
        script_content_json: editor.getJSON(),
      });
      setProject(updated);
      setScriptWordCount(updated.word_count);
      setScriptDuration(updated.estimated_duration_seconds || 0);
      toast.success("Roteiro salvo.");
    } catch (error: any) {
      toast.error(error.message || "Erro ao salvar roteiro.");
    } finally {
      setSavingScript(false);
    }
  };

  const handleUpdateProjectMeta = async (payload: Partial<VideoProject>) => {
    try {
      const updated = await updateVideoProject(projectId, payload);
      setProject(updated);
      toast.success("Projeto atualizado.");
    } catch (error: any) {
      toast.error(error.message || "Erro ao atualizar projeto.");
    }
  };

  const handleArchiveProject = async () => {
    try {
      await archiveVideoProject(projectId);
      toast.success("Projeto arquivado.");
      router.push("/scripts");
    } catch (error: any) {
      toast.error(error.message || "Erro ao arquivar projeto.");
    }
  };

  const handleDeleteProject = async () => {
    if (!confirm("Excluir este projeto de video e toda a oficina?")) {
      return;
    }

    try {
      await deleteVideoProject(projectId);
      toast.success("Projeto excluido.");
      router.push("/scripts");
    } catch (error: any) {
      toast.error(error.message || "Erro ao excluir projeto.");
    }
  };

  const handleSendScriptExcerptToLibrary = async () => {
    if (!editor) return;

    const { from, to } = editor.state.selection;
    const text = editor.state.doc.textBetween(from, to, "\n").trim();

    if (!text) {
      toast.error("Selecione um trecho do roteiro primeiro.");
      return;
    }

    try {
      const created = await createVideoProjectItemFromScriptExcerpt(projectId, {
        text,
        title: text.slice(0, 42),
      });
      setItems((current) => [created, ...current]);
      setActiveTab("elementos");
      toast.success("Trecho enviado para a biblioteca.");
    } catch (error: any) {
      toast.error(error.message || "Erro ao enviar trecho para a biblioteca.");
    }
  };

  const handleCreateLibraryItem = async (event: React.FormEvent) => {
    event.preventDefault();

    try {
      const created = await createVideoProjectItem(projectId, libraryForm);
      setItems((current) => [created, ...current]);
      setLibraryForm({
        item_type: "note",
        title: "",
        body: "",
        url: "",
        status: "open",
        pinned: false,
      });
      toast.success("Elemento criado.");
    } catch (error: any) {
      toast.error(error.message || "Erro ao criar elemento.");
    }
  };

  const handleStartEditingItem = (item: VideoProjectItem) => {
    setEditingItemId(item.id);
    setEditingItemDraft({
      item_type: item.item_type,
      title: item.title || "",
      body: item.body || "",
      url: item.url || "",
      status: item.status,
      pinned: item.pinned,
    });
  };

  const handleSaveEditingItem = async () => {
    if (!editingItemId) return;

    try {
      const updated = await updateVideoProjectItem(editingItemId, editingItemDraft);
      setItems((current) => current.map((item) => (item.id === editingItemId ? updated : item)));
      setEditingItemId(null);
      toast.success("Elemento atualizado.");
    } catch (error: any) {
      toast.error(error.message || "Erro ao atualizar elemento.");
    }
  };

  const handleDeleteItem = async (itemId: number) => {
    try {
      await deleteVideoProjectItem(itemId);
      setItems((current) => current.filter((item) => item.id !== itemId));
      toast.success("Elemento removido.");
    } catch (error: any) {
      toast.error(error.message || "Erro ao remover elemento.");
    }
  };

  const handleCreateCanvaExternalBoard = async () => {
    try {
      setCreatingExternalBoard(true);
      const createdBoard = await createCanvaBoard(projectId);
      setExternalBoards((current) => [
        createdBoard,
        ...current.filter((board) => board.id !== createdBoard.id),
      ]);
      setActiveTab("quadro-externo");
      toast.success("Quadro externo criado no Canva.");
    } catch (error: any) {
      toast.error(error.message || "Erro ao criar quadro externo no Canva.");
    } finally {
      setCreatingExternalBoard(false);
    }
  };

  const handleRefreshBoardUrl = async (board: ExternalBoard) => {
    try {
      setRefreshingBoardId(board.id);
      const updatedBoard = await refreshCanvaBoardUrl(board.id);
      setExternalBoards((current) =>
        current.map((entry) => (entry.id === updatedBoard.id ? updatedBoard : entry))
      );
      toast.success("Link temporario do Canva atualizado.");
    } catch (error: any) {
      toast.error(error.message || "Erro ao atualizar link temporario do Canva.");
    } finally {
      setRefreshingBoardId(null);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-[70vh] items-center justify-center">
        <div className="flex items-center gap-3 rounded-2xl border border-slate-800 bg-slate-950/70 px-5 py-4 text-sm text-slate-300">
          <Loader2 className="h-4 w-4 animate-spin" />
          Carregando oficina...
        </div>
      </div>
    );
  }

  if (pageError || !project) {
    return (
      <div className="flex min-h-[70vh] items-center justify-center px-4">
        <div className="w-full max-w-xl rounded-3xl border border-rose-900/50 bg-slate-950/80 p-8 text-center shadow-2xl shadow-slate-950/30">
          <div className="text-lg font-semibold text-white">Nao foi possivel abrir a oficina</div>
          <p className="mt-3 text-sm leading-relaxed text-slate-400">
            {pageError || "Projeto de video nao encontrado."}
          </p>
          <div className="mt-6 flex items-center justify-center gap-3">
            <button
              onClick={handleReload}
              className="rounded-full border border-slate-700 bg-slate-900 px-4 py-2 text-sm text-slate-200 transition-colors hover:bg-slate-800"
            >
              Tentar novamente
            </button>
            <Link
              href="/scripts"
              className="rounded-full bg-indigo-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-indigo-500"
            >
              Voltar para scripts
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(56,189,248,0.10),_transparent_30%),radial-gradient(circle_at_right,_rgba(99,102,241,0.12),_transparent_28%),#020617] text-slate-100">
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <div className="mb-6 flex flex-col gap-4 rounded-3xl border border-slate-800/80 bg-slate-950/60 p-5 shadow-2xl shadow-slate-950/30 backdrop-blur">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div className="space-y-3">
              <Link
                href="/scripts"
                className="inline-flex items-center gap-2 text-sm font-medium text-slate-400 transition-colors hover:text-slate-200"
              >
                <ArrowLeft className="h-4 w-4" />
                Voltar para scripts
              </Link>
              <div className="space-y-2">
                <input
                  value={project.title}
                  onChange={(event) => setProject({ ...project, title: event.target.value })}
                  onBlur={() => handleUpdateProjectMeta({ title: project.title })}
                  className="w-full bg-transparent text-3xl font-semibold tracking-tight text-white outline-none"
                />
                <textarea
                  value={project.description || ""}
                  onChange={(event) => setProject({ ...project, description: event.target.value })}
                  onBlur={() => handleUpdateProjectMeta({ description: project.description || null })}
                  rows={2}
                  className="w-full resize-none rounded-2xl border border-slate-800/80 bg-slate-900/60 px-4 py-3 text-sm text-slate-300 outline-none transition-colors focus:border-sky-500/40"
                  placeholder="Resumo da proposta, angulo do video e objetivo da oficina."
                />
              </div>
            </div>

            <div className="grid min-w-[290px] gap-3 sm:grid-cols-2">
              <div className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-4">
                <div className="mb-2 text-[11px] font-bold uppercase tracking-[0.18em] text-slate-500">
                  Status
                </div>
                <select
                  value={project.status}
                  onChange={(event) => {
                    const nextStatus = event.target.value as VideoProject["status"];
                    setProject({ ...project, status: nextStatus });
                    handleUpdateProjectMeta({ status: nextStatus });
                  }}
                  className="w-full rounded-xl border border-slate-800 bg-slate-950/80 px-3 py-2 text-sm text-slate-200 outline-none focus:border-sky-500/40"
                >
                  {Object.entries(statusConfig).map(([value, config]) => (
                    <option key={value} value={value}>
                      {config.label}
                    </option>
                  ))}
                </select>
                <div className={cn("mt-3 inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold", statusConfig[project.status].className)}>
                  {statusConfig[project.status].label}
                </div>
              </div>

              <div className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-4">
                <div className="mb-2 text-[11px] font-bold uppercase tracking-[0.18em] text-slate-500">
                  Oficina
                </div>
                <div className="space-y-2 text-sm text-slate-300">
                  <div>{items.length} elementos</div>
                  <div>{canvaBoards.length} board(s) no Canva</div>
                  <div>{scriptWordCount} palavras no roteiro</div>
                </div>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2 border-t border-slate-800/80 pt-4">
            {([
              { id: "roteiro", label: "Roteiro", icon: BookOpen },
              { id: "elementos", label: "Biblioteca", icon: FolderKanban },
              { id: "quadro-externo", label: "Quadro externo", icon: ExternalLink },
            ] as const).map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={cn(
                    "inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-medium transition-all",
                    activeTab === tab.id
                      ? "border-sky-500/40 bg-sky-500/15 text-sky-100"
                      : "border-slate-800 bg-slate-900/70 text-slate-400 hover:border-slate-700 hover:text-slate-200"
                  )}
                >
                  <Icon className="h-4 w-4" />
                  {tab.label}
                </button>
              );
            })}

            <div className="ml-auto flex flex-wrap items-center gap-2">
              <button
                onClick={handleArchiveProject}
                className="inline-flex items-center gap-2 rounded-full border border-slate-700 bg-slate-900/70 px-4 py-2 text-sm text-slate-300 transition-colors hover:border-slate-600 hover:text-white"
              >
                <Archive className="h-4 w-4" />
                Arquivar
              </button>
              <button
                onClick={handleDeleteProject}
                className="inline-flex items-center gap-2 rounded-full border border-rose-900/60 bg-rose-950/20 px-4 py-2 text-sm text-rose-300 transition-colors hover:bg-rose-950/35"
              >
                <Trash2 className="h-4 w-4" />
                Excluir
              </button>
            </div>
          </div>
        </div>

        {activeTab === "roteiro" ? (
          <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
            <div className="rounded-3xl border border-slate-800/80 bg-slate-950/60 p-5 shadow-xl shadow-slate-950/20">
              <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                <div>
                  <div className="text-sm font-semibold text-white">Editor de roteiro</div>
                  <div className="text-xs text-slate-500">
                    Selecione um trecho para mandar o recorte para a biblioteca do projeto.
                  </div>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    onClick={handleSendScriptExcerptToLibrary}
                    className="inline-flex items-center gap-2 rounded-full border border-sky-500/30 bg-sky-500/10 px-4 py-2 text-sm font-medium text-sky-200 transition-colors hover:bg-sky-500/15"
                  >
                    <Sparkles className="h-4 w-4" />
                    Enviar trecho para biblioteca
                  </button>
                  <button
                    onClick={handleSaveScript}
                    disabled={savingScript}
                    className="inline-flex items-center gap-2 rounded-full bg-indigo-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-indigo-500 disabled:opacity-50"
                  >
                    {savingScript ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                    Salvar roteiro
                  </button>
                </div>
              </div>
              <div className="min-h-[580px] rounded-3xl border border-slate-800 bg-slate-950/80 p-4">
                <EditorContent editor={editor} className="prose prose-invert max-w-none [&_.ProseMirror]:min-h-[520px] [&_.ProseMirror]:outline-none" />
              </div>
            </div>

            <div className="space-y-4">
              <div className="rounded-3xl border border-slate-800/80 bg-slate-950/60 p-5">
                <div className="text-[11px] font-bold uppercase tracking-[0.18em] text-slate-500">Metricas</div>
                <div className="mt-4 grid gap-3">
                  <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                    <div className="text-2xl font-semibold text-white">{scriptWordCount}</div>
                    <div className="text-xs text-slate-500">Palavras</div>
                  </div>
                  <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                    <div className="text-2xl font-semibold text-white">{scriptDuration}s</div>
                    <div className="text-xs text-slate-500">Duracao estimada</div>
                  </div>
                </div>
              </div>

              <div className="rounded-3xl border border-slate-800/80 bg-slate-950/60 p-5">
                <div className="text-[11px] font-bold uppercase tracking-[0.18em] text-slate-500">Atalhos da oficina</div>
                <div className="mt-4 space-y-3 text-sm text-slate-300">
                  <p>Use a biblioteca como fonte unica para referencias, notas, musicas, tarefas e recortes do roteiro.</p>
                  <p>Use o quadro externo para abrir o Canva e organizar a composicao visual fora do app.</p>
                </div>
              </div>
            </div>
          </div>
        ) : null}

        {activeTab === "quadro-externo" ? (
          <div className="grid gap-6 lg:grid-cols-[360px_minmax(0,1fr)]">
            <div className="rounded-3xl border border-slate-800/80 bg-slate-950/60 p-5 shadow-xl shadow-slate-950/20">
              <div className="mb-4">
                <div className="text-sm font-semibold text-white">Quadro externo</div>
                <div className="text-xs text-slate-500">
                  O quadro visual agora vive fora do app. Use o Canva para montagem, espacamento e exploracao visual.
                </div>
              </div>

              <div className="space-y-4">
                <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
                  <div className="text-[11px] font-bold uppercase tracking-[0.18em] text-slate-500">Canva</div>
                  <p className="mt-3 text-sm leading-relaxed text-slate-300">
                    Crie um board externo do projeto e reabra o link quando precisar continuar a oficina visual.
                  </p>
                  <button
                    onClick={handleCreateCanvaExternalBoard}
                    disabled={creatingExternalBoard}
                    className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white transition-colors hover:bg-indigo-500 disabled:opacity-50"
                  >
                    {creatingExternalBoard ? <Loader2 className="h-4 w-4 animate-spin" /> : <ExternalLink className="h-4 w-4" />}
                    Criar board no Canva
                  </button>
                </div>

                <div className="rounded-2xl border border-amber-500/20 bg-amber-500/10 p-4 text-sm leading-relaxed text-amber-100">
                  Os links do Canva podem ser temporarios. Se um link expirar, use o refresh para gerar uma URL nova antes de abrir novamente.
                </div>

                <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4 text-sm text-slate-300">
                  <div className="font-semibold text-white">{items.length} elementos na biblioteca</div>
                  <div className="mt-2 text-slate-400">
                    O frontend nao sincroniza mais para um canvas interno. A biblioteca e o roteiro continuam como base do trabalho.
                  </div>
                </div>
              </div>
            </div>

            <div className="space-y-4">
              {hiddenLegacyBoardsCount > 0 ? (
                <div className="rounded-2xl border border-slate-800 bg-slate-950/40 px-4 py-3 text-sm text-slate-400">
                  {hiddenLegacyBoardsCount} board(s) legado(s) de outro provedor foram ocultados nesta tela. O frontend desta refatoracao mostra apenas boards Canva.
                </div>
              ) : null}

              {canvaBoards.length === 0 ? (
                <div className="rounded-3xl border border-dashed border-slate-800 bg-slate-950/40 px-6 py-16 text-center">
                  <div className="text-lg font-semibold text-white">Nenhum board Canva associado</div>
                  <p className="mt-2 text-sm text-slate-500">
                    Crie um board externo para continuar a oficina visual no Canva.
                  </p>
                </div>
              ) : (
                canvaBoards.map((board) => {
                  const expiresAt = formatBoardLinkExpiry(board);
                  const refreshedAt = getBoardRefreshTimestamp(board);
                  const boardUrl = board.edit_url || board.view_url || "#";

                  return (
                    <div
                      key={board.id}
                      className="rounded-3xl border border-slate-800/80 bg-slate-950/60 p-6 shadow-xl shadow-slate-950/20"
                    >
                      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                        <div className="space-y-2">
                          <div className="inline-flex rounded-full border border-sky-500/30 bg-sky-500/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-sky-100">
                            Canva
                          </div>
                          <div className="text-xl font-semibold text-white">
                            {board.title || `Board ${board.external_id}`}
                          </div>
                          <div className="text-sm text-slate-400">
                            Criado em {new Date(board.created_at).toLocaleString("pt-BR")}
                          </div>
                          <div className="text-sm text-slate-400">
                            Atualizado em {new Date(board.updated_at).toLocaleString("pt-BR")}
                          </div>
                          {refreshedAt ? (
                            <div className="text-sm text-slate-400">
                              URL renovada em {new Date(refreshedAt).toLocaleString("pt-BR")}
                            </div>
                          ) : null}
                          {expiresAt ? (
                            <div className="text-sm text-amber-200">
                              Link temporario ate {new Date(expiresAt).toLocaleString("pt-BR")}
                            </div>
                          ) : (
                            <div className="text-sm text-slate-500">
                              Este link pode ser temporario mesmo sem expiracao exposta pelo backend.
                            </div>
                          )}
                        </div>

                        <div className="flex flex-wrap items-center gap-2">
                          {(board.view_url || board.edit_url) ? (
                            <a
                              href={boardUrl}
                              target="_blank"
                              rel="noreferrer"
                              className="inline-flex items-center gap-2 rounded-full border border-sky-500/30 bg-sky-500/10 px-4 py-2 text-sm font-medium text-sky-100 transition-colors hover:bg-sky-500/15"
                            >
                              <ExternalLink className="h-4 w-4" />
                              Abrir no Canva
                            </a>
                          ) : null}
                          <button
                            onClick={() => handleRefreshBoardUrl(board)}
                            disabled={refreshingBoardId === board.id}
                            className="inline-flex items-center gap-2 rounded-full bg-indigo-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-indigo-500 disabled:opacity-50"
                          >
                            {refreshingBoardId === board.id ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <RefreshCw className="h-4 w-4" />
                            )}
                            Refresh de link
                          </button>
                        </div>
                      </div>

                      <div className="mt-5 grid gap-4 md:grid-cols-3">
                        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                          <div className="text-[11px] font-bold uppercase tracking-[0.18em] text-slate-500">Board ID</div>
                          <div className="mt-2 break-all text-sm text-slate-200">{board.external_id}</div>
                        </div>
                        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                          <div className="text-[11px] font-bold uppercase tracking-[0.18em] text-slate-500">Biblioteca atual</div>
                          <div className="mt-2 text-2xl font-semibold text-white">{items.length}</div>
                          <div className="text-xs text-slate-500">elementos disponiveis para usar no board</div>
                        </div>
                        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                          <div className="text-[11px] font-bold uppercase tracking-[0.18em] text-slate-500">Links</div>
                          <div className="mt-2 text-sm text-slate-200">
                            {board.edit_url || board.view_url ? "Disponivel" : "Aguardando URL"}
                          </div>
                          <div className="text-xs text-slate-500">use refresh se a URL expirar</div>
                        </div>
                      </div>

                      <div className="mt-5 rounded-2xl border border-amber-500/20 bg-amber-500/10 p-4 text-sm leading-relaxed text-amber-100">
                        O link salvo pode parar de funcionar com o tempo. Se isso acontecer, gere uma nova URL por aqui e reabra o Canva.
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        ) : null}

        {activeTab === "elementos" ? (
          <div className="grid gap-6 lg:grid-cols-[330px_minmax(0,1fr)]">
            <div className="rounded-3xl border border-slate-800/80 bg-slate-950/60 p-5 shadow-xl shadow-slate-950/20">
              <div className="mb-4">
                <div className="text-sm font-semibold text-white">Novo elemento</div>
                <div className="text-xs text-slate-500">Notas, referencias, musicas, tarefas e imagens entram pela mesma biblioteca.</div>
              </div>
              <form onSubmit={handleCreateLibraryItem} className="space-y-3">
                <select
                  value={libraryForm.item_type}
                  onChange={(event) => setLibraryForm((current) => ({ ...current, item_type: event.target.value as VideoProjectItemType }))}
                  className="w-full rounded-2xl border border-slate-800 bg-slate-900/80 px-3 py-2 text-sm text-slate-100 outline-none focus:border-sky-500/40"
                >
                  {Object.entries(itemTypeMeta).map(([value, meta]) => (
                    <option key={value} value={value}>
                      {meta.label}
                    </option>
                  ))}
                </select>
                <input
                  value={libraryForm.title}
                  onChange={(event) => setLibraryForm((current) => ({ ...current, title: event.target.value }))}
                  className="w-full rounded-2xl border border-slate-800 bg-slate-900/80 px-3 py-2 text-sm text-slate-100 outline-none focus:border-sky-500/40"
                  placeholder="Titulo"
                />
                <input
                  value={libraryForm.url}
                  onChange={(event) => setLibraryForm((current) => ({ ...current, url: event.target.value }))}
                  className="w-full rounded-2xl border border-slate-800 bg-slate-900/80 px-3 py-2 text-sm text-slate-100 outline-none focus:border-sky-500/40"
                  placeholder="URL opcional"
                />
                <textarea
                  value={libraryForm.body}
                  onChange={(event) => setLibraryForm((current) => ({ ...current, body: event.target.value }))}
                  rows={5}
                  className="w-full rounded-2xl border border-slate-800 bg-slate-900/80 px-3 py-2 text-sm text-slate-100 outline-none focus:border-sky-500/40"
                  placeholder="Observacoes, nota de uso, comentario ou contexto."
                />
                <div className="grid gap-3 sm:grid-cols-2">
                  <select
                    value={libraryForm.status}
                    onChange={(event) => setLibraryForm((current) => ({ ...current, status: event.target.value }))}
                    className="rounded-2xl border border-slate-800 bg-slate-900/80 px-3 py-2 text-sm text-slate-100 outline-none focus:border-sky-500/40"
                  >
                    <option value="open">Open</option>
                    <option value="done">Done</option>
                    <option value="archived">Archived</option>
                  </select>
                  <label className="flex items-center gap-2 rounded-2xl border border-slate-800 bg-slate-900/80 px-3 py-2 text-sm text-slate-200">
                    <input
                      type="checkbox"
                      checked={libraryForm.pinned}
                      onChange={(event) => setLibraryForm((current) => ({ ...current, pinned: event.target.checked }))}
                      className="rounded border-slate-700 bg-slate-950"
                    />
                    Fixado
                  </label>
                </div>
                <button
                  type="submit"
                  className="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white transition-colors hover:bg-indigo-500"
                >
                  <Plus className="h-4 w-4" />
                  Criar elemento
                </button>
              </form>
            </div>

            <div className="space-y-4">
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={() => setLibraryFilter("all")}
                  className={cn(
                    "rounded-full border px-3 py-2 text-sm font-medium",
                    libraryFilter === "all"
                      ? "border-sky-500/30 bg-sky-500/10 text-sky-100"
                      : "border-slate-800 bg-slate-900/70 text-slate-400"
                  )}
                >
                  Todos
                </button>
                {Object.entries(itemTypeMeta).map(([value, meta]) => (
                  <button
                    key={value}
                    onClick={() => setLibraryFilter(value as VideoProjectItemType)}
                    className={cn(
                      "rounded-full border px-3 py-2 text-sm font-medium",
                      libraryFilter === value
                        ? "border-sky-500/30 bg-sky-500/10 text-sky-100"
                        : "border-slate-800 bg-slate-900/70 text-slate-400"
                    )}
                  >
                    {meta.label}
                  </button>
                ))}
              </div>

              <div className="grid gap-4 xl:grid-cols-2">
                {filteredItems.map((item) => {
                  const meta = itemTypeMeta[item.item_type];
                  const Icon = meta.icon;
                  const isEditing = editingItemId === item.id;

                  return (
                    <div
                      key={item.id}
                      className="rounded-3xl border border-slate-800/80 bg-slate-950/60 p-5 shadow-lg shadow-slate-950/20"
                    >
                      <div className="mb-3 flex items-start justify-between gap-3">
                        <div className="flex items-start gap-3">
                          <span className="rounded-2xl border border-slate-800 bg-slate-900/80 p-2 text-sky-300">
                            <Icon className="h-4 w-4" />
                          </span>
                          <div>
                            <div className="text-[11px] font-bold uppercase tracking-[0.18em] text-slate-500">
                              {meta.label}
                            </div>
                            <div className="text-sm font-semibold text-white">
                              {item.title || "Sem titulo"}
                            </div>
                            <div className="text-xs text-slate-500">{meta.description}</div>
                          </div>
                        </div>
                        <button
                          onClick={() => handleDeleteItem(item.id)}
                          className="rounded-full border border-rose-900/70 bg-rose-950/20 p-2 text-rose-200 hover:bg-rose-950/35"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>

                      {isEditing ? (
                        <div className="space-y-3">
                          <select
                            value={editingItemDraft.item_type}
                            onChange={(event) => setEditingItemDraft((current) => ({ ...current, item_type: event.target.value as VideoProjectItemType }))}
                            className="w-full rounded-2xl border border-slate-800 bg-slate-900/80 px-3 py-2 text-sm text-slate-100 outline-none focus:border-sky-500/40"
                          >
                            {Object.entries(itemTypeMeta).map(([value, metaOption]) => (
                              <option key={value} value={value}>
                                {metaOption.label}
                              </option>
                            ))}
                          </select>
                          <input
                            value={editingItemDraft.title}
                            onChange={(event) => setEditingItemDraft((current) => ({ ...current, title: event.target.value }))}
                            className="w-full rounded-2xl border border-slate-800 bg-slate-900/80 px-3 py-2 text-sm text-slate-100 outline-none focus:border-sky-500/40"
                          />
                          <input
                            value={editingItemDraft.url}
                            onChange={(event) => setEditingItemDraft((current) => ({ ...current, url: event.target.value }))}
                            className="w-full rounded-2xl border border-slate-800 bg-slate-900/80 px-3 py-2 text-sm text-slate-100 outline-none focus:border-sky-500/40"
                            placeholder="URL"
                          />
                          <textarea
                            value={editingItemDraft.body}
                            onChange={(event) => setEditingItemDraft((current) => ({ ...current, body: event.target.value }))}
                            rows={4}
                            className="w-full rounded-2xl border border-slate-800 bg-slate-900/80 px-3 py-2 text-sm text-slate-100 outline-none focus:border-sky-500/40"
                          />
                          <div className="grid gap-3 sm:grid-cols-2">
                            <select
                              value={editingItemDraft.status}
                              onChange={(event) => setEditingItemDraft((current) => ({ ...current, status: event.target.value }))}
                              className="rounded-2xl border border-slate-800 bg-slate-900/80 px-3 py-2 text-sm text-slate-100 outline-none focus:border-sky-500/40"
                            >
                              <option value="open">Open</option>
                              <option value="done">Done</option>
                              <option value="archived">Archived</option>
                            </select>
                            <label className="flex items-center gap-2 rounded-2xl border border-slate-800 bg-slate-900/80 px-3 py-2 text-sm text-slate-200">
                              <input
                                type="checkbox"
                                checked={editingItemDraft.pinned}
                                onChange={(event) => setEditingItemDraft((current) => ({ ...current, pinned: event.target.checked }))}
                              />
                              Fixado
                            </label>
                          </div>
                          <div className="flex gap-2">
                            <button
                              onClick={handleSaveEditingItem}
                              className="rounded-full bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500"
                            >
                              Salvar
                            </button>
                            <button
                              onClick={() => setEditingItemId(null)}
                              className="rounded-full border border-slate-700 px-4 py-2 text-sm text-slate-300"
                            >
                              Cancelar
                            </button>
                          </div>
                        </div>
                      ) : (
                        <div className="space-y-3">
                          {item.url ? (
                            <a
                              href={item.url}
                              target="_blank"
                              rel="noreferrer"
                              className="inline-flex items-center gap-2 text-sm font-medium text-sky-300 hover:underline"
                            >
                              <Link2 className="h-4 w-4" />
                              {item.url}
                            </a>
                          ) : null}
                          {item.body ? (
                            <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-300">
                              {item.body}
                            </p>
                          ) : (
                            <p className="text-sm text-slate-500">Sem observacoes.</p>
                          )}
                          <div className="flex flex-wrap items-center gap-2 pt-2">
                            <span className="rounded-full border border-slate-800 bg-slate-900 px-2.5 py-1 text-xs text-slate-400">
                              {item.status}
                            </span>
                            {item.pinned ? (
                              <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-2.5 py-1 text-xs text-amber-200">
                                Fixado
                              </span>
                            ) : null}
                            <button
                              onClick={() => handleStartEditingItem(item)}
                              className="ml-auto rounded-full border border-slate-700 px-3 py-1.5 text-xs text-slate-300 hover:border-slate-600 hover:text-white"
                            >
                              Editar
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
