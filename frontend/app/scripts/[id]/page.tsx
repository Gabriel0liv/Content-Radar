"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";

import {
  archiveVideoProject,
  createCanvaBoard,
  getCanvaOAuthStatus,
  createVideoProjectItem,
  createVideoProjectItemFromScriptExcerpt,
  deleteVideoProject,
  deleteVideoProjectItem,
  getExternalBoards,
  getVideoProject,
  getVideoProjectItems,
  refreshCanvaBoardUrl,
  refreshCanvaOAuthToken,
  updateVideoProject,
  updateVideoProjectItem,
} from "@/lib/api";
import {
  CanvaOAuthStatus,
  ExternalBoard,
  VideoProject,
  VideoProjectItem,
  VideoProjectItemType,
} from "@/lib/types";
import {
  ArrowLeft,
  Archive,
  CheckSquare,
  Copy,
  ExternalLink,
  FileImage,
  Film,
  FolderKanban,
  Link2,
  Loader2,
  MoreHorizontal,
  Music,
  Pin,
  PinOff,
  Plus,
  RefreshCw,
  Save,
  Search,
  Sparkles,
  StickyNote,
  Trash2,
  Type,
  X,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

type LibraryFilter = "all" | VideoProjectItemType;
type LibraryStatusFilter = "all" | VideoProjectItem["status"];
type LibraryGroupBy = "type" | "status";

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

const itemStatusMeta: Record<VideoProjectItem["status"], { label: string; className: string }> = {
  open: { label: "Aberto", className: "border-sky-500/30 bg-sky-500/10 text-sky-100" },
  done: { label: "Concluido", className: "border-emerald-500/30 bg-emerald-500/10 text-emerald-100" },
  archived: { label: "Arquivado", className: "border-slate-700 bg-slate-800/70 text-slate-300" },
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

function formatEstimatedDuration(seconds: number) {
  if (!seconds) {
    return "0s";
  }

  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  if (!minutes) {
    return `${remainingSeconds}s`;
  }
  if (!remainingSeconds) {
    return `${minutes}min`;
  }
  return `${minutes}min ${remainingSeconds}s`;
}

export default function VideoWorkspacePage() {
  const router = useRouter();
  const params = useParams();
  const projectId = Number(params.id);

  const [project, setProject] = useState<VideoProject | null>(null);
  const [items, setItems] = useState<VideoProjectItem[]>([]);
  const [externalBoards, setExternalBoards] = useState<ExternalBoard[]>([]);
  const [canvaOAuthStatus, setCanvaOAuthStatus] = useState<CanvaOAuthStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [pageError, setPageError] = useState<string | null>(null);
  const [savingScript, setSavingScript] = useState(false);
  const [creatingExternalBoard, setCreatingExternalBoard] = useState(false);
  const [refreshingBoardId, setRefreshingBoardId] = useState<number | null>(null);
  const [refreshingOAuthToken, setRefreshingOAuthToken] = useState(false);
  const [libraryFilter, setLibraryFilter] = useState<LibraryFilter>("all");
  const [libraryStatusFilter, setLibraryStatusFilter] = useState<LibraryStatusFilter>("all");
  const [librarySearch, setLibrarySearch] = useState("");
  const [libraryPinnedOnly, setLibraryPinnedOnly] = useState(false);
  const [libraryGroupBy, setLibraryGroupBy] = useState<LibraryGroupBy>("type");
  const [isLibraryOpen, setIsLibraryOpen] = useState(false);
  const [isLibraryComposerOpen, setIsLibraryComposerOpen] = useState(false);
  const [isCanvaMenuOpen, setIsCanvaMenuOpen] = useState(false);
  const [isProjectMenuOpen, setIsProjectMenuOpen] = useState(false);
  const [expandedItemId, setExpandedItemId] = useState<number | null>(null);
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
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
  const canvaConnectUrl = `${process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"}/canva/oauth/start`;

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

    try {
      const oauthStatus = await getCanvaOAuthStatus();
      setCanvaOAuthStatus(oauthStatus);
    } catch (error: any) {
      setCanvaOAuthStatus(null);
      if (!silentOptionalErrors) {
        toast.error(error.message || "Nao foi possivel carregar o status de conexao do Canva.");
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
    const search = librarySearch.trim().toLowerCase();
    const list = items.filter((item) => {
      if (libraryFilter !== "all" && item.item_type !== libraryFilter) {
        return false;
      }
      if (libraryStatusFilter !== "all" && item.status !== libraryStatusFilter) {
        return false;
      }
      if (libraryPinnedOnly && !item.pinned) {
        return false;
      }
      if (!search) {
        return true;
      }

      const haystack = [item.title, item.body, item.url]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return haystack.includes(search);
    });

    return [...list].sort((a, b) => {
      if (a.pinned && !b.pinned) return -1;
      if (!a.pinned && b.pinned) return 1;
      return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
    });
  }, [items, libraryFilter, libraryPinnedOnly, librarySearch, libraryStatusFilter]);

  const canvaBoards = useMemo(
    () => externalBoards.filter((board) => board.provider === "canva"),
    [externalBoards]
  );
  const primaryCanvaBoard = canvaBoards[0] || null;
  const hasCanvaBoard = Boolean(primaryCanvaBoard);
  const isCanvaOAuthConnected = Boolean(canvaOAuthStatus?.connected);

  const groupedItems = useMemo(() => {
    const groups = new Map<string, VideoProjectItem[]>();

    filteredItems.forEach((item) => {
      const key = libraryGroupBy === "status" ? item.status : item.item_type;
      const current = groups.get(key) || [];
      current.push(item);
      groups.set(key, current);
    });

    return Array.from(groups.entries()).map(([groupKey, groupItems]) => ({
      key: groupKey,
      label:
        libraryGroupBy === "status"
          ? itemStatusMeta[groupKey as VideoProjectItem["status"]].label
          : itemTypeMeta[groupKey as VideoProjectItemType].label,
      items: groupItems,
    }));
  }, [filteredItems, libraryGroupBy]);

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
      setIsLibraryComposerOpen(false);
      setExpandedItemId(created.id);
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
    setExpandedItemId(item.id);
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
      if (error.message?.includes("Elemento da oficina não encontrado")) {
        try {
          const refreshedItems = await getVideoProjectItems(projectId);
          setItems(refreshedItems);
        } catch {
          // Keep original state if reload fails.
        }
        setEditingItemId(null);
        toast.error("Este elemento nao existe mais. A biblioteca foi recarregada.");
        return;
      }
      toast.error(error.message || "Erro ao atualizar elemento.");
    }
  };

  const handleDeleteItem = async (itemId: number) => {
    try {
      await deleteVideoProjectItem(itemId);
      setItems((current) => current.filter((item) => item.id !== itemId));
      if (editingItemId === itemId) {
        setEditingItemId(null);
      }
      toast.success("Elemento removido.");
    } catch (error: any) {
      if (error.message?.includes("Elemento da oficina não encontrado")) {
        try {
          const refreshedItems = await getVideoProjectItems(projectId);
          setItems(refreshedItems);
        } catch {
          // Keep original state if reload fails.
        }
        toast.error("Este elemento nao existe mais. A biblioteca foi recarregada.");
        return;
      }
      toast.error(error.message || "Erro ao remover elemento.");
    }
  };

  const handleQuickUpdateItem = async (
    itemId: number,
    payload: Partial<Pick<VideoProjectItem, "status" | "pinned">>
  ) => {
    try {
      const updated = await updateVideoProjectItem(itemId, payload);
      setItems((current) => current.map((item) => (item.id === itemId ? updated : item)));
    } catch (error: any) {
      if (error.message?.includes("Elemento da oficina não encontrado")) {
        try {
          const refreshedItems = await getVideoProjectItems(projectId);
          setItems(refreshedItems);
        } catch {
          // Keep original state if reload fails.
        }
        toast.error("Este elemento nao existe mais. A biblioteca foi recarregada.");
        return;
      }
      toast.error(error.message || "Erro ao atualizar elemento.");
    }
  };

  const handleCreateCanvaExternalBoard = async () => {
    if (!isCanvaOAuthConnected) {
      toast.error("Conecte o Canva antes de criar boards externos.");
      return;
    }

    if (primaryCanvaBoard) {
      window.open(`${apiBaseUrl}/external-boards/${primaryCanvaBoard.id}/open-canva`, "_blank", "noopener,noreferrer");
      return;
    }

    try {
      setCreatingExternalBoard(true);
      const createdBoard = await createCanvaBoard(projectId);
      setExternalBoards((current) => [
        createdBoard,
        ...current.filter((board) => board.id !== createdBoard.id),
      ]);
      toast.success("Quadro externo criado no Canva.");
      window.open(`${apiBaseUrl}/external-boards/${createdBoard.id}/open-canva`, "_blank", "noopener,noreferrer");
    } catch (error: any) {
      toast.error(error.message || "Erro ao criar quadro externo no Canva.");
    } finally {
      setCreatingExternalBoard(false);
    }
  };

  const handleRefreshCanvaOAuth = async () => {
    try {
      setRefreshingOAuthToken(true);
      const refreshed = await refreshCanvaOAuthToken();
      const nextStatus = await getCanvaOAuthStatus();
      setCanvaOAuthStatus(nextStatus);
      toast.success(refreshed.message || "Token do Canva renovado.");
    } catch (error: any) {
      toast.error(error.message || "Erro ao renovar token OAuth do Canva.");
    } finally {
      setRefreshingOAuthToken(false);
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

  const handleOpenCanvaBoard = (board: ExternalBoard) => {
    window.open(`${apiBaseUrl}/external-boards/${board.id}/open-canva`, "_blank", "noopener,noreferrer");
    setIsCanvaMenuOpen(false);
  };

  const handleCopyCanvaPackage = async () => {
    if (!project) {
      return;
    }

    const sections = Object.entries(itemTypeMeta)
      .map(([type, meta]) => {
        const sectionItems = items.filter((item) => item.item_type === type);
        if (!sectionItems.length) {
          return null;
        }

        const lines = sectionItems.map((item) => {
          const parts = [
            item.title ? `- ${item.title}` : "- Sem titulo",
            item.body ? `  ${item.body}` : null,
            item.url ? `  URL: ${item.url}` : null,
            `  Status: ${itemStatusMeta[item.status].label}${item.pinned ? " | Fixado" : ""}`,
          ].filter(Boolean);
          return parts.join("\n");
        });

        return `${meta.label.toUpperCase()}\n${lines.join("\n")}`;
      })
      .filter(Boolean)
      .join("\n\n");

    const packageText = [
      `TITULO\n${project.title}`,
      project.description ? `DESCRICAO\n${project.description}` : null,
      `STATUS\n${statusConfig[project.status].label}`,
      `ROTEIRO\n${editor?.getText().trim() || project.script_text || "Sem roteiro."}`,
      sections ? `BIBLIOTECA\n${sections}` : "BIBLIOTECA\nSem itens.",
      "OBSERVACAO\nO Dark Content continua como fonte principal do roteiro e da biblioteca. Use o Canva para organizar visualmente.",
    ]
      .filter(Boolean)
      .join("\n\n");

    try {
      await navigator.clipboard.writeText(packageText);
      toast.success("Pacote do projeto copiado para colar no Canva.");
    } catch (error: any) {
      toast.error(error.message || "Nao foi possivel copiar o pacote para a area de transferencia.");
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
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(56,189,248,0.08),_transparent_24%),radial-gradient(circle_at_right,_rgba(99,102,241,0.10),_transparent_24%),#020617] text-slate-100">
      <div className="mx-auto max-w-[1500px] px-4 py-4 sm:px-6">
        <div className="sticky top-0 z-20 mb-4 rounded-3xl border border-slate-800/80 bg-slate-950/80 p-3 shadow-2xl shadow-slate-950/30 backdrop-blur">
          <div className="flex flex-col gap-3 xl:flex-row xl:items-center">
            <div className="flex min-w-0 flex-1 items-center gap-3">
              <Link
                href="/scripts"
                className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-slate-800 bg-slate-900/70 text-slate-300 transition-colors hover:border-slate-700 hover:text-white"
                title="Voltar para scripts"
              >
                <ArrowLeft className="h-4 w-4" />
              </Link>
              <input
                value={project.title}
                onChange={(event) => setProject({ ...project, title: event.target.value })}
                onBlur={() => handleUpdateProjectMeta({ title: project.title })}
                className="min-w-0 flex-1 bg-transparent text-xl font-semibold tracking-tight text-white outline-none md:text-2xl"
              />
              <select
                value={project.status}
                onChange={(event) => {
                  const nextStatus = event.target.value as VideoProject["status"];
                  setProject({ ...project, status: nextStatus });
                  handleUpdateProjectMeta({ status: nextStatus });
                }}
                className="h-10 rounded-full border border-slate-800 bg-slate-900/80 px-3 text-sm text-slate-200 outline-none focus:border-sky-500/40"
              >
                {Object.entries(statusConfig).map(([value, config]) => (
                  <option key={value} value={value}>
                    {config.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex flex-wrap items-center gap-2 text-sm text-slate-400">
              <span className="rounded-full border border-slate-800 bg-slate-900/70 px-3 py-2">
                {scriptWordCount} palavras
              </span>
              <span className="rounded-full border border-slate-800 bg-slate-900/70 px-3 py-2">
                {formatEstimatedDuration(scriptDuration)}
              </span>
              <button
                onClick={handleSaveScript}
                disabled={savingScript}
                className="inline-flex items-center gap-2 rounded-full bg-indigo-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-indigo-500 disabled:opacity-50"
              >
                {savingScript ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                Salvar
              </button>
              <button
                onClick={() => setIsLibraryOpen(true)}
                className="inline-flex items-center gap-2 rounded-full border border-slate-800 bg-slate-900/70 px-4 py-2 text-sm text-slate-200 transition-colors hover:border-slate-700 hover:text-white"
              >
                <FolderKanban className="h-4 w-4" />
                Biblioteca
              </button>
              <div className="relative">
                <button
                  onClick={() => {
                    setIsCanvaMenuOpen((current) => !current);
                    setIsProjectMenuOpen(false);
                  }}
                  className="inline-flex items-center gap-2 rounded-full border border-slate-800 bg-slate-900/70 px-4 py-2 text-sm text-slate-200 transition-colors hover:border-slate-700 hover:text-white"
                >
                  <ExternalLink className="h-4 w-4" />
                  Canva
                  <span className="rounded-full border border-slate-700 px-2 py-0.5 text-[11px] text-slate-400">
                    {!isCanvaOAuthConnected ? "Nao conectado" : hasCanvaBoard ? "Board criado" : "Pronto"}
                  </span>
                </button>
                {isCanvaMenuOpen ? (
                  <div className="absolute right-0 top-12 z-30 w-64 rounded-2xl border border-slate-800 bg-slate-950/95 p-2 shadow-2xl shadow-slate-950/40">
                    {!isCanvaOAuthConnected ? (
                      <a
                        href={canvaConnectUrl}
                        target="_blank"
                        rel="noreferrer"
                        className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-sm text-slate-200 transition-colors hover:bg-slate-900"
                      >
                        <ExternalLink className="h-4 w-4" />
                        Conectar Canva
                      </a>
                    ) : !hasCanvaBoard ? (
                      <button
                        onClick={handleCreateCanvaExternalBoard}
                        disabled={creatingExternalBoard}
                        className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm text-slate-200 transition-colors hover:bg-slate-900 disabled:opacity-50"
                      >
                        {creatingExternalBoard ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                        Criar board Canva
                      </button>
                    ) : (
                      <button
                        onClick={() => handleOpenCanvaBoard(primaryCanvaBoard)}
                        className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm text-slate-200 transition-colors hover:bg-slate-900"
                      >
                        <ExternalLink className="h-4 w-4" />
                        Abrir no Canva
                      </button>
                    )}
                    <button
                      onClick={handleCopyCanvaPackage}
                      className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm text-slate-200 transition-colors hover:bg-slate-900"
                    >
                      <Copy className="h-4 w-4" />
                      Copiar pacote
                    </button>
                    <button
                      onClick={() => primaryCanvaBoard && handleRefreshBoardUrl(primaryCanvaBoard)}
                      disabled={!primaryCanvaBoard || refreshingBoardId === primaryCanvaBoard.id}
                      className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm text-slate-200 transition-colors hover:bg-slate-900 disabled:opacity-50"
                    >
                      {refreshingBoardId === primaryCanvaBoard?.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
                      Atualizar acesso
                    </button>
                    <button
                      onClick={handleRefreshCanvaOAuth}
                      disabled={refreshingOAuthToken || !isCanvaOAuthConnected || Boolean(canvaOAuthStatus?.using_dev_token_fallback)}
                      className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm text-slate-200 transition-colors hover:bg-slate-900 disabled:opacity-50"
                    >
                      {refreshingOAuthToken ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
                      Renovar OAuth
                    </button>
                  </div>
                ) : null}
              </div>
              <div className="relative">
                <button
                  onClick={() => {
                    setIsProjectMenuOpen((current) => !current);
                    setIsCanvaMenuOpen(false);
                  }}
                  className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-slate-800 bg-slate-900/70 text-slate-300 transition-colors hover:border-slate-700 hover:text-white"
                >
                  <MoreHorizontal className="h-4 w-4" />
                </button>
                {isProjectMenuOpen ? (
                  <div className="absolute right-0 top-12 z-30 w-48 rounded-2xl border border-slate-800 bg-slate-950/95 p-2 shadow-2xl shadow-slate-950/40">
                    <button
                      onClick={handleArchiveProject}
                      className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm text-slate-200 transition-colors hover:bg-slate-900"
                    >
                      <Archive className="h-4 w-4" />
                      Arquivar
                    </button>
                    <button
                      onClick={handleDeleteProject}
                      className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm text-rose-300 transition-colors hover:bg-rose-950/20"
                    >
                      <Trash2 className="h-4 w-4" />
                      Excluir
                    </button>
                  </div>
                ) : null}
              </div>
            </div>
          </div>

          <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-slate-800/80 pt-3 text-xs text-slate-500">
            <span className={cn("rounded-full border px-2.5 py-1 font-medium", statusConfig[project.status].className)}>
              {statusConfig[project.status].label}
            </span>
            <span>{items.length} elementos</span>
            <span>{hasCanvaBoard ? "Canva pronto" : isCanvaOAuthConnected ? "Canva conectado" : "Canva nao conectado"}</span>
          </div>
        </div>

        <div className="rounded-[32px] border border-slate-800/80 bg-slate-950/55 p-4 shadow-2xl shadow-slate-950/20">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div className="min-w-0 flex-1">
              <textarea
                value={project.description || ""}
                onChange={(event) => setProject({ ...project, description: event.target.value })}
                onBlur={() => handleUpdateProjectMeta({ description: project.description || null })}
                rows={1}
                className="w-full resize-none bg-transparent text-sm text-slate-400 outline-none placeholder:text-slate-600"
                placeholder="Resumo curto, angulo e objetivo do roteiro."
              />
            </div>
            <button
              onClick={handleSendScriptExcerptToLibrary}
              className="inline-flex items-center gap-2 rounded-full border border-sky-500/30 bg-sky-500/10 px-4 py-2 text-sm font-medium text-sky-200 transition-colors hover:bg-sky-500/15"
            >
              <Sparkles className="h-4 w-4" />
              Enviar trecho para biblioteca
            </button>
          </div>
          <div className="min-h-[76vh] rounded-[28px] border border-slate-800 bg-slate-950/85 p-5">
            <EditorContent editor={editor} className="prose prose-invert max-w-none [&_.ProseMirror]:min-h-[70vh] [&_.ProseMirror]:outline-none" />
          </div>
        </div>
      </div>

      {isLibraryOpen ? (
        <div className="fixed inset-0 z-40 flex">
          <button
            aria-label="Fechar biblioteca"
            className="flex-1 bg-slate-950/70 backdrop-blur-sm"
            onClick={() => {
              setIsLibraryOpen(false);
              setIsLibraryComposerOpen(false);
            }}
          />
          <div className="relative h-full w-full max-w-[560px] overflow-y-auto border-l border-slate-800 bg-slate-950/95 p-4 shadow-2xl shadow-slate-950/40">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div>
                <div className="text-base font-semibold text-white">Biblioteca</div>
                <div className="text-xs text-slate-500">{filteredItems.length} itens visiveis</div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setIsLibraryComposerOpen((current) => !current)}
                  className="inline-flex items-center gap-2 rounded-full border border-slate-800 bg-slate-900/70 px-3 py-2 text-sm text-slate-200"
                >
                  <Plus className="h-4 w-4" />
                  Novo elemento
                </button>
                <button
                  onClick={() => {
                    setIsLibraryOpen(false);
                    setIsLibraryComposerOpen(false);
                  }}
                  className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-slate-800 bg-slate-900/70 text-slate-300"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>

            {isLibraryComposerOpen ? (
              <form onSubmit={handleCreateLibraryItem} className="mb-4 space-y-3 rounded-3xl border border-slate-800 bg-slate-900/50 p-4">
                <select
                  value={libraryForm.item_type}
                  onChange={(event) => setLibraryForm((current) => ({ ...current, item_type: event.target.value as VideoProjectItemType }))}
                  className="w-full rounded-2xl border border-slate-800 bg-slate-950/80 px-3 py-2 text-sm text-slate-100 outline-none"
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
                  className="w-full rounded-2xl border border-slate-800 bg-slate-950/80 px-3 py-2 text-sm text-slate-100 outline-none"
                  placeholder="Titulo"
                />
                <input
                  value={libraryForm.url}
                  onChange={(event) => setLibraryForm((current) => ({ ...current, url: event.target.value }))}
                  className="w-full rounded-2xl border border-slate-800 bg-slate-950/80 px-3 py-2 text-sm text-slate-100 outline-none"
                  placeholder="URL opcional"
                />
                <textarea
                  value={libraryForm.body}
                  onChange={(event) => setLibraryForm((current) => ({ ...current, body: event.target.value }))}
                  rows={4}
                  className="w-full rounded-2xl border border-slate-800 bg-slate-950/80 px-3 py-2 text-sm text-slate-100 outline-none"
                  placeholder="Resumo ou observacoes"
                />
                <div className="grid gap-3 sm:grid-cols-2">
                  <select
                    value={libraryForm.status}
                    onChange={(event) => setLibraryForm((current) => ({ ...current, status: event.target.value as VideoProjectItem["status"] }))}
                    className="rounded-2xl border border-slate-800 bg-slate-950/80 px-3 py-2 text-sm text-slate-100 outline-none"
                  >
                    <option value="open">Aberto</option>
                    <option value="done">Concluido</option>
                    <option value="archived">Arquivado</option>
                  </select>
                  <label className="flex items-center gap-2 rounded-2xl border border-slate-800 bg-slate-950/80 px-3 py-2 text-sm text-slate-200">
                    <input
                      type="checkbox"
                      checked={libraryForm.pinned}
                      onChange={(event) => setLibraryForm((current) => ({ ...current, pinned: event.target.checked }))}
                    />
                    Fixado
                  </label>
                </div>
                <button
                  type="submit"
                  className="inline-flex items-center gap-2 rounded-full bg-indigo-600 px-4 py-2 text-sm font-semibold text-white"
                >
                  <Plus className="h-4 w-4" />
                  Criar elemento
                </button>
              </form>
            ) : null}

            <div className="space-y-4">
              <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
                <input
                  value={librarySearch}
                  onChange={(event) => setLibrarySearch(event.target.value)}
                  placeholder="Buscar por titulo, corpo ou URL"
                  className="w-full rounded-2xl border border-slate-800 bg-slate-900/80 py-3 pl-10 pr-4 text-sm text-slate-100 outline-none"
                />
              </div>

              <div className="flex flex-wrap gap-2">
                <button
                  onClick={() => setLibraryFilter("all")}
                  className={cn(
                    "rounded-full border px-3 py-1.5 text-xs font-medium",
                    libraryFilter === "all" ? "border-sky-500/30 bg-sky-500/10 text-sky-100" : "border-slate-800 bg-slate-900/70 text-slate-400"
                  )}
                >
                  Todos
                </button>
                {Object.entries(itemTypeMeta).map(([value, meta]) => (
                  <button
                    key={value}
                    onClick={() => setLibraryFilter(value as VideoProjectItemType)}
                    className={cn(
                      "rounded-full border px-3 py-1.5 text-xs font-medium",
                      libraryFilter === value ? "border-sky-500/30 bg-sky-500/10 text-sky-100" : "border-slate-800 bg-slate-900/70 text-slate-400"
                    )}
                  >
                    {meta.label}
                  </button>
                ))}
              </div>

              <div className="flex flex-wrap gap-2">
                {(["all", "open", "done", "archived"] as const).map((value) => (
                  <button
                    key={value}
                    onClick={() => setLibraryStatusFilter(value)}
                    className={cn(
                      "rounded-full border px-3 py-1.5 text-xs font-medium",
                      libraryStatusFilter === value ? "border-sky-500/30 bg-sky-500/10 text-sky-100" : "border-slate-800 bg-slate-900/70 text-slate-400"
                    )}
                  >
                    {value === "all" ? "Status" : itemStatusMeta[value].label}
                  </button>
                ))}
                <button
                  onClick={() => setLibraryPinnedOnly((current) => !current)}
                  className={cn(
                    "rounded-full border px-3 py-1.5 text-xs font-medium",
                    libraryPinnedOnly ? "border-amber-500/30 bg-amber-500/10 text-amber-100" : "border-slate-800 bg-slate-900/70 text-slate-400"
                  )}
                >
                  So fixados
                </button>
                <button
                  onClick={() => setLibraryGroupBy((current) => (current === "type" ? "status" : "type"))}
                  className="rounded-full border border-slate-800 bg-slate-900/70 px-3 py-1.5 text-xs font-medium text-slate-300"
                >
                  Agrupar por {libraryGroupBy === "type" ? "status" : "tipo"}
                </button>
              </div>
            </div>

            <div className="mt-5 space-y-4">
              {groupedItems.length === 0 ? (
                <div className="rounded-3xl border border-dashed border-slate-800 bg-slate-950/40 px-6 py-12 text-center text-sm text-slate-500">
                  Nenhum item nesta combinacao de filtros.
                </div>
              ) : (
                groupedItems.map((group) => (
                  <section key={group.key} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">{group.label}</div>
                      <div className="text-xs text-slate-600">{group.items.length}</div>
                    </div>
                    <div className="space-y-2">
                      {group.items.map((item) => {
                        const meta = itemTypeMeta[item.item_type];
                        const Icon = meta.icon;
                        const isEditing = editingItemId === item.id;
                        const isExpanded = expandedItemId === item.id || isEditing;
                        const summary = item.body?.trim() ? item.body.trim().slice(0, 120) : item.url || "Sem detalhes.";

                        return (
                          <div key={item.id} className="rounded-2xl border border-slate-800 bg-slate-900/55 p-3">
                            <div className="flex items-start gap-3">
                              <button
                                onClick={() => setExpandedItemId((current) => (current === item.id ? null : item.id))}
                                className="flex min-w-0 flex-1 items-start gap-3 text-left"
                              >
                                <span className="rounded-2xl border border-slate-800 bg-slate-950/80 p-2 text-sky-300">
                                  <Icon className="h-4 w-4" />
                                </span>
                                <div className="min-w-0 flex-1">
                                  <div className="flex flex-wrap items-center gap-2">
                                    <div className="truncate text-sm font-semibold text-white">{item.title || "Sem titulo"}</div>
                                    <span className="rounded-full border border-slate-800 px-2 py-0.5 text-[11px] text-slate-400">{meta.label}</span>
                                    <span className={cn("rounded-full border px-2 py-0.5 text-[11px] font-medium", itemStatusMeta[item.status].className)}>
                                      {itemStatusMeta[item.status].label}
                                    </span>
                                  </div>
                                  <div className="mt-1 line-clamp-2 text-xs text-slate-400">{summary}</div>
                                </div>
                              </button>
                              <div className="flex items-center gap-1">
                                <button
                                  onClick={() => handleQuickUpdateItem(item.id, { pinned: !item.pinned })}
                                  className="rounded-full border border-slate-700 bg-slate-950/70 p-2 text-slate-300"
                                >
                                  {item.pinned ? <PinOff className="h-3.5 w-3.5" /> : <Pin className="h-3.5 w-3.5" />}
                                </button>
                                <button
                                  onClick={() => handleStartEditingItem(item)}
                                  className="rounded-full border border-slate-700 bg-slate-950/70 px-3 py-2 text-xs text-slate-300"
                                >
                                  Editar
                                </button>
                                <button
                                  onClick={() => handleDeleteItem(item.id)}
                                  className="rounded-full border border-rose-900/70 bg-rose-950/20 p-2 text-rose-200"
                                >
                                  <Trash2 className="h-3.5 w-3.5" />
                                </button>
                              </div>
                            </div>

                            {isExpanded ? (
                              <div className="mt-3 border-t border-slate-800 pt-3">
                                {isEditing ? (
                                  <div className="space-y-3">
                                    <select
                                      value={editingItemDraft.item_type}
                                      onChange={(event) => setEditingItemDraft((current) => ({ ...current, item_type: event.target.value as VideoProjectItemType }))}
                                      className="w-full rounded-2xl border border-slate-800 bg-slate-950/80 px-3 py-2 text-sm text-slate-100 outline-none"
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
                                      className="w-full rounded-2xl border border-slate-800 bg-slate-950/80 px-3 py-2 text-sm text-slate-100 outline-none"
                                    />
                                    <input
                                      value={editingItemDraft.url}
                                      onChange={(event) => setEditingItemDraft((current) => ({ ...current, url: event.target.value }))}
                                      className="w-full rounded-2xl border border-slate-800 bg-slate-950/80 px-3 py-2 text-sm text-slate-100 outline-none"
                                      placeholder="URL"
                                    />
                                    <textarea
                                      value={editingItemDraft.body}
                                      onChange={(event) => setEditingItemDraft((current) => ({ ...current, body: event.target.value }))}
                                      rows={4}
                                      className="w-full rounded-2xl border border-slate-800 bg-slate-950/80 px-3 py-2 text-sm text-slate-100 outline-none"
                                    />
                                    <div className="grid gap-3 sm:grid-cols-2">
                                      <select
                                        value={editingItemDraft.status}
                                        onChange={(event) => setEditingItemDraft((current) => ({ ...current, status: event.target.value as VideoProjectItem["status"] }))}
                                        className="rounded-2xl border border-slate-800 bg-slate-950/80 px-3 py-2 text-sm text-slate-100 outline-none"
                                      >
                                        <option value="open">Aberto</option>
                                        <option value="done">Concluido</option>
                                        <option value="archived">Arquivado</option>
                                      </select>
                                      <label className="flex items-center gap-2 rounded-2xl border border-slate-800 bg-slate-950/80 px-3 py-2 text-sm text-slate-200">
                                        <input
                                          type="checkbox"
                                          checked={editingItemDraft.pinned}
                                          onChange={(event) => setEditingItemDraft((current) => ({ ...current, pinned: event.target.checked }))}
                                        />
                                        Fixado
                                      </label>
                                    </div>
                                    <div className="flex gap-2">
                                      <button onClick={handleSaveEditingItem} className="rounded-full bg-indigo-600 px-4 py-2 text-sm font-semibold text-white">
                                        Salvar
                                      </button>
                                      <button onClick={() => setEditingItemId(null)} className="rounded-full border border-slate-700 px-4 py-2 text-sm text-slate-300">
                                        Cancelar
                                      </button>
                                    </div>
                                  </div>
                                ) : (
                                  <div className="space-y-3">
                                    {item.body ? <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-300">{item.body}</p> : null}
                                    {item.url ? (
                                      <a href={item.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 text-sm text-sky-300 hover:underline">
                                        <Link2 className="h-4 w-4" />
                                        {item.url}
                                      </a>
                                    ) : null}
                                    <div className="flex flex-wrap gap-2">
                                      {(["open", "done", "archived"] as const).map((statusValue) => (
                                        <button
                                          key={statusValue}
                                          onClick={() => handleQuickUpdateItem(item.id, { status: statusValue })}
                                          className={cn(
                                            "rounded-full border px-2.5 py-1 text-xs font-medium",
                                            item.status === statusValue ? itemStatusMeta[statusValue].className : "border-slate-800 bg-slate-950/70 text-slate-400"
                                          )}
                                        >
                                          {itemStatusMeta[statusValue].label}
                                        </button>
                                      ))}
                                    </div>
                                  </div>
                                )}
                              </div>
                            ) : null}
                          </div>
                        );
                      })}
                    </div>
                  </section>
                ))
              )}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
