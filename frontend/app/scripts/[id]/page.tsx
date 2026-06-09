"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import ReactFlow, {
  addEdge,
  Background,
  Connection,
  Edge,
  MarkerType,
  Node,
  NodeProps,
  Panel,
  ReactFlowInstance,
  useEdgesState,
  useNodesState,
} from "reactflow";
import "reactflow/dist/style.css";

import {
  archiveVideoProject,
  createBoardNodeFromItem,
  createVideoProjectItem,
  createVideoProjectItemFromScriptExcerpt,
  deleteVideoProject,
  deleteVideoProjectItem,
  getVideoProject,
  getVideoProjectBoard,
  getVideoProjectItems,
  saveVideoProjectBoard,
  updateVideoProject,
  updateVideoProjectItem,
} from "@/lib/api";
import {
  VideoProject,
  VideoProjectBoardEdge,
  VideoProjectBoardNode,
  VideoProjectItem,
  VideoProjectItemType,
} from "@/lib/types";
import {
  ArrowLeft,
  Archive,
  BookOpen,
  CheckSquare,
  Copy,
  FileImage,
  Film,
  FolderKanban,
  Link2,
  Loader2,
  Music,
  Plus,
  Save,
  Sparkles,
  StickyNote,
  Trash2,
  Type,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

type PageTab = "roteiro" | "quadro" | "elementos";
type LibraryFilter = "all" | VideoProjectItemType;

type WorkshopNodeData = {
  itemId?: number | null;
  itemType: VideoProjectItemType;
  title: string;
  body: string;
  url?: string;
  status?: string;
  pinned?: boolean;
  color: string;
};

const statusConfig: Record<string, { label: string; className: string }> = {
  idea: { label: "Ideia", className: "border-indigo-500/25 bg-indigo-500/10 text-indigo-300" },
  researching: { label: "Pesquisa", className: "border-sky-500/25 bg-sky-500/10 text-sky-300" },
  scripting: { label: "Roteiro", className: "border-amber-500/25 bg-amber-500/10 text-amber-300" },
  reviewing: { label: "Revisao", className: "border-fuchsia-500/25 bg-fuchsia-500/10 text-fuchsia-300" },
  ready: { label: "Pronto", className: "border-emerald-500/25 bg-emerald-500/10 text-emerald-300" },
  produced: { label: "Produzido", className: "border-slate-500/25 bg-slate-500/10 text-slate-300" },
  archived: { label: "Arquivado", className: "border-rose-500/25 bg-rose-500/10 text-rose-300" },
};

const colorOptions = [
  { name: "slate", bg: "#0f172acc", border: "#334155", text: "#e2e8f0" },
  { name: "indigo", bg: "#312e81cc", border: "#6366f1", text: "#e0e7ff" },
  { name: "emerald", bg: "#064e3bcc", border: "#34d399", text: "#d1fae5" },
  { name: "amber", bg: "#78350fcc", border: "#f59e0b", text: "#fef3c7" },
  { name: "rose", bg: "#881337cc", border: "#fb7185", text: "#ffe4e6" },
  { name: "sky", bg: "#0c4a6ecc", border: "#38bdf8", text: "#e0f2fe" },
  { name: "zinc", bg: "#27272acc", border: "#71717a", text: "#f4f4f5" },
];

const itemTypeMeta: Record<
  VideoProjectItemType,
  {
    label: string;
    description: string;
    icon: typeof StickyNote;
    defaultColor: string;
  }
> = {
  note: { label: "Nota", description: "Ideias e observacoes", icon: StickyNote, defaultColor: "slate" },
  reference: { label: "Referencia", description: "Link, fonte ou citacao", icon: Link2, defaultColor: "sky" },
  script_excerpt: { label: "Trecho", description: "Recorte do roteiro", icon: Type, defaultColor: "indigo" },
  audio: { label: "Musica/SFX", description: "Faixa, trilha ou efeito", icon: Music, defaultColor: "amber" },
  thumbnail: { label: "Thumbnail", description: "Ideias visuais", icon: FileImage, defaultColor: "rose" },
  production: { label: "Producao", description: "Passos de execucao", icon: Film, defaultColor: "emerald" },
  todo: { label: "Tarefa", description: "Checklist acionavel", icon: CheckSquare, defaultColor: "emerald" },
  image: { label: "Imagem", description: "Imagem de apoio", icon: FileImage, defaultColor: "zinc" },
  group: { label: "Grupo", description: "Frame ou agrupamento", icon: FolderKanban, defaultColor: "zinc" },
  other: { label: "Outro", description: "Elemento generico", icon: Sparkles, defaultColor: "slate" },
};

const quickCanvasTypes: VideoProjectItemType[] = [
  "note",
  "reference",
  "script_excerpt",
  "audio",
  "thumbnail",
  "todo",
  "group",
];

function getColorDefinition(colorName?: string) {
  return colorOptions.find((option) => option.name === colorName) || colorOptions[0];
}

function getNodeDimensions(itemType: VideoProjectItemType) {
  if (itemType === "group") {
    return { width: 320, height: 200 };
  }
  if (itemType === "script_excerpt") {
    return { width: 260, height: 170 };
  }
  return { width: 220, height: 140 };
}

function WorkshopNode({ data, selected }: NodeProps<WorkshopNodeData>) {
  const itemType = data.itemType as VideoProjectItemType;
  const color = getColorDefinition(data.color);
  const typeMeta = itemTypeMeta[itemType];
  const Icon = typeMeta.icon;

  return (
    <div
      style={{
        background: color.bg,
        color: color.text,
        border: `1px solid ${color.border}`,
        boxShadow: selected ? `0 0 0 2px ${color.border}` : "0 12px 30px rgba(2, 6, 23, 0.25)",
      }}
      className={cn(
        "min-h-[110px] rounded-2xl px-4 py-3 backdrop-blur-sm transition-all",
        itemType === "group" && "border-dashed"
      )}
    >
      <div className="mb-2 flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="rounded-full border border-white/10 bg-white/10 p-1.5">
            <Icon className="h-3.5 w-3.5" />
          </span>
          <div>
            <div className="text-[10px] font-bold uppercase tracking-[0.18em] opacity-70">
              {typeMeta.label}
            </div>
            {data.pinned ? <div className="text-[10px] opacity-70">Fixado</div> : null}
          </div>
        </div>
        {data.status === "done" ? (
          <span className="rounded-full border border-emerald-400/30 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-semibold text-emerald-200">
            Done
          </span>
        ) : null}
      </div>
      <div className="space-y-2">
        <h4 className="text-sm font-semibold leading-tight">
          {data.title || typeMeta.label}
        </h4>
        {data.body ? (
          <p className="line-clamp-5 whitespace-pre-wrap text-xs leading-relaxed opacity-90">
            {data.body}
          </p>
        ) : null}
        {data.url ? (
          <div className="truncate text-[11px] font-medium opacity-80">{data.url}</div>
        ) : null}
      </div>
    </div>
  );
}

const nodeTypes = { workshopNode: WorkshopNode };

export default function VideoWorkspacePage() {
  const router = useRouter();
  const params = useParams();
  const projectId = Number(params.id);

  const [project, setProject] = useState<VideoProject | null>(null);
  const [items, setItems] = useState<VideoProjectItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [pageError, setPageError] = useState<string | null>(null);
  const [savingScript, setSavingScript] = useState(false);
  const [savingBoard, setSavingBoard] = useState(false);
  const [creatingQuickItem, setCreatingQuickItem] = useState<VideoProjectItemType | null>(null);
  const [activeTab, setActiveTab] = useState<PageTab>("roteiro");
  const [showImportPanel, setShowImportPanel] = useState(false);
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
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [nodeDraft, setNodeDraft] = useState({
    title: "",
    body: "",
    url: "",
    itemType: "note" as VideoProjectItemType,
    color: "slate",
  });
  const [flowInstance, setFlowInstance] = useState<ReactFlowInstance | null>(null);
  const [nodes, setNodes, onNodesChange] = useNodesState<WorkshopNodeData>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [scriptWordCount, setScriptWordCount] = useState(0);
  const [scriptDuration, setScriptDuration] = useState(0);

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

  const syncSelectedNodeDraft = useCallback((nodeId: string | null, currentNodes: Node<WorkshopNodeData>[]) => {
    setSelectedNodeId(nodeId);
    if (!nodeId) {
      return;
    }
    const node = currentNodes.find((entry) => entry.id === nodeId);
    if (!node) {
      return;
    }
    setNodeDraft({
      title: node.data.title || "",
      body: node.data.body || "",
      url: node.data.url || "",
      itemType: node.data.itemType,
      color: node.data.color,
    });
  }, []);

  const mapBoardToReactFlow = useCallback((boardNodes: VideoProjectBoardNode[], boardEdges: VideoProjectBoardEdge[]) => {
    const mappedNodes: Node<WorkshopNodeData>[] = boardNodes.map((boardNode) => {
      const itemType = (boardNode.node_type as VideoProjectItemType) || "note";
      const colorName = boardNode.color || itemTypeMeta[itemType]?.defaultColor || "slate";
      const dimensions = getNodeDimensions(itemType);
      return {
        id: boardNode.node_key,
        type: "workshopNode",
        position: { x: boardNode.x, y: boardNode.y },
        data: {
          itemId: boardNode.item_id ?? null,
          itemType,
          title: boardNode.title || "",
          body: boardNode.body || "",
          url: typeof boardNode.data_json?.url === "string" ? boardNode.data_json.url : "",
          status: typeof boardNode.data_json?.status === "string" ? boardNode.data_json.status : "open",
          pinned: Boolean(boardNode.data_json?.pinned),
          color: colorName,
        },
        style: {
          width: boardNode.width || dimensions.width,
          height: boardNode.height || dimensions.height,
        },
      };
    });

    const mappedEdges: Edge[] = boardEdges.map((boardEdge) => ({
      id: boardEdge.edge_key,
      source: boardEdge.source_node_key,
      target: boardEdge.target_node_key,
      label: boardEdge.label || undefined,
      animated: false,
      markerEnd: { type: MarkerType.ArrowClosed, color: "#94a3b8" },
      style: { stroke: "#94a3b8", strokeWidth: 1.5 },
    }));

    return { mappedNodes, mappedEdges };
  }, []);

  const loadProjectWorkspace = useCallback(async () => {
    setLoading(true);
    setPageError(null);

    let projectResponse: VideoProject;

    try {
      projectResponse = await getVideoProject(projectId);
      setProject(projectResponse);
      setScriptWordCount(projectResponse.word_count);
      setScriptDuration(projectResponse.estimated_duration_seconds || 0);
    } catch (error: any) {
      setProject(null);
      setPageError(error.message || "Nao foi possivel carregar este projeto de video.");
      setItems([]);
      setNodes([]);
      setEdges([]);
      syncSelectedNodeDraft(null, []);
      setLoading(false);
      return;
    }

    if (editor) {
      if (projectResponse.script_content_json) {
        editor.commands.setContent(projectResponse.script_content_json);
      } else {
        editor.commands.setContent(projectResponse.script_text || "<p>Comece a escrever seu roteiro aqui...</p>");
      }
    }

    try {
      const itemsResponse = await getVideoProjectItems(projectId);
      setItems(itemsResponse);
    } catch (error: any) {
      setItems([]);
      toast.error(error.message || "Nao foi possivel carregar os elementos da oficina.");
    }

    try {
      const boardResponse = await getVideoProjectBoard(projectId);
      const { mappedNodes, mappedEdges } = mapBoardToReactFlow(boardResponse.nodes, boardResponse.edges);
      setNodes(mappedNodes);
      setEdges(mappedEdges);
      syncSelectedNodeDraft(null, mappedNodes);
    } catch (error: any) {
      setNodes([]);
      setEdges([]);
      syncSelectedNodeDraft(null, []);
      toast.error(error.message || "Nao foi possivel carregar o quadro deste projeto.");
    } finally {
      setLoading(false);
    }
  }, [editor, mapBoardToReactFlow, projectId, setEdges, setNodes, syncSelectedNodeDraft]);

  useEffect(() => {
    loadProjectWorkspace();
  }, [loadProjectWorkspace]);

  const selectedNode = useMemo(
    () => nodes.find((node: Node<WorkshopNodeData>) => node.id === selectedNodeId) || null,
    [nodes, selectedNodeId]
  );

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

  const createLocalNodeFromItem = useCallback((item: VideoProjectItem, itemId?: number | null) => {
    const colorName = item.metadata_json?.color && typeof item.metadata_json.color === "string"
      ? item.metadata_json.color
      : itemTypeMeta[item.item_type].defaultColor;
    const dimensions = getNodeDimensions(item.item_type);
    return {
      itemId: itemId ?? item.id,
      itemType: item.item_type,
      title: item.title || "",
      body: item.body || "",
      url: item.url || "",
      status: item.status,
      pinned: item.pinned,
      color: colorName,
      width: dimensions.width,
      height: dimensions.height,
    };
  }, []);

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
      setNodes((current: Node<WorkshopNodeData>[]) =>
        current.map((node: Node<WorkshopNodeData>) =>
          node.data.itemId === editingItemId
            ? {
                ...node,
                data: {
                  ...node.data,
                  itemType: updated.item_type,
                  title: updated.title || "",
                  body: updated.body || "",
                  url: updated.url || "",
                  status: updated.status,
                  pinned: updated.pinned,
                },
              }
            : node
        )
      );
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

  const handleAddItemToBoard = async (item: VideoProjectItem) => {
    try {
      const position = flowInstance?.project({ x: 320 + Math.random() * 120, y: 220 + Math.random() * 120 }) || {
        x: 320 + Math.random() * 120,
        y: 220 + Math.random() * 120,
      };
      const createdNode = await createBoardNodeFromItem(projectId, {
        item_id: item.id,
        x: position.x,
        y: position.y,
        width: getNodeDimensions(item.item_type).width,
        height: getNodeDimensions(item.item_type).height,
      });

      const localNodeData = createLocalNodeFromItem(item, createdNode.item_id);
      setNodes((current: Node<WorkshopNodeData>[]) => [
        ...current,
        {
          id: createdNode.node_key,
          type: "workshopNode",
          position: { x: createdNode.x, y: createdNode.y },
          data: {
            itemId: localNodeData.itemId,
            itemType: localNodeData.itemType,
            title: localNodeData.title,
            body: localNodeData.body,
            url: localNodeData.url,
            status: localNodeData.status,
            pinned: localNodeData.pinned,
            color: createdNode.color || localNodeData.color,
          },
          style: {
            width: createdNode.width || localNodeData.width,
            height: createdNode.height || localNodeData.height,
          },
        },
      ]);
      setActiveTab("quadro");
      toast.success("Elemento adicionado ao quadro.");
    } catch (error: any) {
      toast.error(error.message || "Erro ao adicionar elemento ao quadro.");
    }
  };

  const handleCreateQuickCanvasItem = async (itemType: VideoProjectItemType) => {
    try {
      setCreatingQuickItem(itemType);
      const itemMeta = itemTypeMeta[itemType];
      const created = await createVideoProjectItem(projectId, {
        item_type: itemType,
        title: itemMeta.label,
        body: itemType === "todo" ? "Defina a proxima acao." : "",
        status: "open",
        pinned: false,
        metadata_json: { color: itemMeta.defaultColor },
      });
      setItems((current) => [created, ...current]);
      await handleAddItemToBoard(created);
    } catch (error: any) {
      toast.error(error.message || "Erro ao criar elemento no quadro.");
    } finally {
      setCreatingQuickItem(null);
    }
  };

  const handleSendScriptExcerptToBoard = async () => {
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
      await handleAddItemToBoard(created);
      toast.success("Trecho enviado para o quadro.");
    } catch (error: any) {
      toast.error(error.message || "Erro ao enviar trecho para o quadro.");
    }
  };

  const onConnect = useCallback((connection: Connection) => {
    if (!connection.source || !connection.target) return;
    setEdges((current: Edge[]) =>
      addEdge(
        {
          id: `edge-${Date.now()}`,
          source: connection.source,
          target: connection.target,
          markerEnd: { type: MarkerType.ArrowClosed, color: "#94a3b8" },
          style: { stroke: "#94a3b8", strokeWidth: 1.5 },
        },
        current
      )
    );
  }, [setEdges]);

  const handleSelectNode = (_event: unknown, node: Node<WorkshopNodeData>) => {
    syncSelectedNodeDraft(node.id, nodes);
  };

  const handleDuplicateSelectedNode = async () => {
    if (!selectedNode) return;
    try {
      const duplicatedItem = await createVideoProjectItem(projectId, {
        item_type: nodeDraft.itemType,
        title: nodeDraft.title || itemTypeMeta[nodeDraft.itemType].label,
        body: nodeDraft.body || "",
        url: nodeDraft.url || null,
        status: selectedNode.data.status || "open",
        pinned: selectedNode.data.pinned || false,
        metadata_json: { color: nodeDraft.color },
      });
      setItems((current) => [duplicatedItem, ...current]);
      await handleAddItemToBoard(duplicatedItem);
      toast.success("Elemento duplicado.");
    } catch (error: any) {
      toast.error(error.message || "Erro ao duplicar elemento.");
    }
  };

  const handleDeleteSelectedNode = () => {
    if (!selectedNodeId) return;
    setNodes((current: Node<WorkshopNodeData>[]) => current.filter((node: Node<WorkshopNodeData>) => node.id !== selectedNodeId));
    setEdges((current: Edge[]) => current.filter((edge: Edge) => edge.source !== selectedNodeId && edge.target !== selectedNodeId));
    syncSelectedNodeDraft(null, []);
    toast.success("Node removido do quadro. Salve para persistir.");
  };

  const handleApplySelectedNodeChanges = async () => {
    if (!selectedNode) return;
    const color = getColorDefinition(nodeDraft.color);
    setNodes((current: Node<WorkshopNodeData>[]) =>
      current.map((node: Node<WorkshopNodeData>) =>
        node.id === selectedNode.id
          ? {
              ...node,
              data: {
                ...node.data,
                itemType: nodeDraft.itemType,
                title: nodeDraft.title,
                body: nodeDraft.body,
                url: nodeDraft.url,
                color: color.name,
              },
              style: {
                ...node.style,
                ...getNodeDimensions(nodeDraft.itemType),
              },
            }
          : node
      )
    );

    if (selectedNode.data.itemId) {
      try {
        const updated = await updateVideoProjectItem(selectedNode.data.itemId, {
          item_type: nodeDraft.itemType,
          title: nodeDraft.title || null,
          body: nodeDraft.body || null,
          url: nodeDraft.url || null,
          metadata_json: { color: color.name },
        });
        setItems((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      } catch (error: any) {
        toast.error(error.message || "Erro ao sincronizar elemento da biblioteca.");
        return;
      }
    }

    toast.success("Node atualizado.");
  };

  const handleSaveBoard = async () => {
    try {
      setSavingBoard(true);
      const payload = {
        nodes: nodes.map((node: Node<WorkshopNodeData>) => ({
          item_id: node.data.itemId || null,
          node_key: node.id,
          node_type: node.data.itemType,
          title: node.data.title || null,
          body: node.data.body || null,
          x: node.position.x,
          y: node.position.y,
          width: Number(node.style?.width) || getNodeDimensions(node.data.itemType).width,
          height: Number(node.style?.height) || getNodeDimensions(node.data.itemType).height,
          color: node.data.color,
          data_json: {
            url: node.data.url || null,
            status: node.data.status || "open",
            pinned: node.data.pinned || false,
          },
        })),
        edges: edges.map((edge: Edge) => ({
          edge_key: edge.id,
          source_node_key: edge.source,
          target_node_key: edge.target,
          label: typeof edge.label === "string" ? edge.label : null,
          data_json: null,
        })),
      };

      const saved = await saveVideoProjectBoard(projectId, payload);
      const { mappedNodes, mappedEdges } = mapBoardToReactFlow(saved.nodes, saved.edges);
      setNodes(mappedNodes);
      setEdges(mappedEdges);
      syncSelectedNodeDraft(selectedNodeId, mappedNodes);
      toast.success("Quadro salvo.");
    } catch (error: any) {
      toast.error(error.message || "Erro ao salvar quadro.");
    } finally {
      setSavingBoard(false);
    }
  };

  const importPanelItems = filteredItems.filter((item) => !nodes.some((node: Node<WorkshopNodeData>) => node.data.itemId === item.id));

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
              onClick={loadProjectWorkspace}
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
                  <div>{nodes.length} cards no quadro</div>
                  <div>{scriptWordCount} palavras no roteiro</div>
                </div>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2 border-t border-slate-800/80 pt-4">
            {([
              { id: "roteiro", label: "Roteiro", icon: BookOpen },
              { id: "quadro", label: "Quadro", icon: Sparkles },
              { id: "elementos", label: "Biblioteca", icon: FolderKanban },
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
                    Selecione um trecho para criar um card de roteiro direto no quadro.
                  </div>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    onClick={handleSendScriptExcerptToBoard}
                    className="inline-flex items-center gap-2 rounded-full border border-sky-500/30 bg-sky-500/10 px-4 py-2 text-sm font-medium text-sky-200 transition-colors hover:bg-sky-500/15"
                  >
                    <Sparkles className="h-4 w-4" />
                    Enviar trecho para o quadro
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
                  <p>Use a biblioteca para criar referencias, musicas, tarefas e thumbnails como elementos unificados.</p>
                  <p>Use o quadro para conectar cards e organizar a narrativa visualmente.</p>
                </div>
              </div>
            </div>
          </div>
        ) : null}

        {activeTab === "quadro" ? (
          <div className="rounded-[32px] border border-slate-800/80 bg-slate-950/60 p-4 shadow-2xl shadow-slate-950/30">
            <div className="relative h-[78vh] overflow-hidden rounded-[28px] border border-slate-800 bg-[radial-gradient(circle_at_top_left,_rgba(56,189,248,0.12),_transparent_28%),radial-gradient(circle_at_bottom_right,_rgba(99,102,241,0.14),_transparent_25%),#030712]">
              <ReactFlow
                nodeTypes={nodeTypes}
                nodes={nodes}
                edges={edges}
                onInit={setFlowInstance}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onConnect={onConnect}
                onNodeClick={handleSelectNode}
                onPaneClick={() => syncSelectedNodeDraft(null, nodes)}
                fitView
              >
                <Background color="#1f2937" gap={20} size={1.2} />

                <Panel position="top-left">
                  <div className="flex items-center gap-2 rounded-2xl border border-slate-800/90 bg-slate-950/90 p-2 shadow-xl backdrop-blur">
                    <button
                      onClick={handleSaveBoard}
                      disabled={savingBoard}
                      className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-3 py-2 text-sm font-semibold text-white transition-colors hover:bg-indigo-500 disabled:opacity-50"
                    >
                      {savingBoard ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                      Salvar
                    </button>
                    <button
                      onClick={() => flowInstance?.fitView({ padding: 0.2 })}
                      className="rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200 transition-colors hover:bg-slate-800"
                    >
                      Fit view
                    </button>
                    <button
                      onClick={() => flowInstance?.zoomIn()}
                      className="rounded-xl border border-slate-700 bg-slate-900 p-2 text-slate-200 transition-colors hover:bg-slate-800"
                    >
                      <ZoomIn className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => flowInstance?.zoomOut()}
                      className="rounded-xl border border-slate-700 bg-slate-900 p-2 text-slate-200 transition-colors hover:bg-slate-800"
                    >
                      <ZoomOut className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => setShowImportPanel((current) => !current)}
                      className="rounded-xl border border-sky-500/30 bg-sky-500/10 px-3 py-2 text-sm text-sky-100 transition-colors hover:bg-sky-500/15"
                    >
                      Importar elemento
                    </button>
                  </div>
                </Panel>

                <Panel position="top-right">
                  {selectedNode ? (
                    <div className="w-[320px] rounded-3xl border border-slate-800/90 bg-slate-950/95 p-4 shadow-2xl backdrop-blur">
                      <div className="mb-3 flex items-center justify-between gap-3">
                        <div>
                          <div className="text-sm font-semibold text-white">Ferramentas do card</div>
                          <div className="text-xs text-slate-500">Edite o elemento dentro do quadro.</div>
                        </div>
                        <button
                          onClick={() => syncSelectedNodeDraft(null, nodes)}
                          className="rounded-full border border-slate-700 px-2 py-1 text-xs text-slate-400 hover:text-slate-200"
                        >
                          Fechar
                        </button>
                      </div>

                      <div className="space-y-3">
                        <input
                          value={nodeDraft.title}
                          onChange={(event) => setNodeDraft((current) => ({ ...current, title: event.target.value }))}
                          className="w-full rounded-2xl border border-slate-800 bg-slate-900/70 px-3 py-2 text-sm text-slate-100 outline-none focus:border-sky-500/40"
                          placeholder="Titulo"
                        />
                        <textarea
                          value={nodeDraft.body}
                          onChange={(event) => setNodeDraft((current) => ({ ...current, body: event.target.value }))}
                          rows={4}
                          className="w-full rounded-2xl border border-slate-800 bg-slate-900/70 px-3 py-2 text-sm text-slate-100 outline-none focus:border-sky-500/40"
                          placeholder="Texto do card"
                        />
                        <input
                          value={nodeDraft.url}
                          onChange={(event) => setNodeDraft((current) => ({ ...current, url: event.target.value }))}
                          className="w-full rounded-2xl border border-slate-800 bg-slate-900/70 px-3 py-2 text-sm text-slate-100 outline-none focus:border-sky-500/40"
                          placeholder="URL opcional"
                        />
                        <div className="grid gap-3 sm:grid-cols-2">
                          <select
                            value={nodeDraft.itemType}
                            onChange={(event) => setNodeDraft((current) => ({ ...current, itemType: event.target.value as VideoProjectItemType }))}
                            className="rounded-2xl border border-slate-800 bg-slate-900/70 px-3 py-2 text-sm text-slate-100 outline-none focus:border-sky-500/40"
                          >
                            {Object.entries(itemTypeMeta).map(([value, meta]) => (
                              <option key={value} value={value}>
                                {meta.label}
                              </option>
                            ))}
                          </select>
                          <div className="flex flex-wrap gap-2">
                            {colorOptions.map((color) => (
                              <button
                                key={color.name}
                                onClick={() => setNodeDraft((current) => ({ ...current, color: color.name }))}
                                style={{ background: color.bg, borderColor: color.border, color: color.text }}
                                className={cn(
                                  "rounded-xl border px-2.5 py-2 text-[11px] font-semibold transition-transform",
                                  nodeDraft.color === color.name ? "scale-105" : "opacity-80"
                                )}
                              >
                                {color.name}
                              </button>
                            ))}
                          </div>
                        </div>
                      </div>

                      <div className="mt-4 flex flex-wrap gap-2 border-t border-slate-800 pt-4">
                        <button
                          onClick={handleApplySelectedNodeChanges}
                          className="rounded-full bg-indigo-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-indigo-500"
                        >
                          Aplicar
                        </button>
                        <button
                          onClick={handleDuplicateSelectedNode}
                          className="inline-flex items-center gap-2 rounded-full border border-slate-700 bg-slate-900 px-4 py-2 text-sm text-slate-200 transition-colors hover:bg-slate-800"
                        >
                          <Copy className="h-4 w-4" />
                          Duplicar
                        </button>
                        <button
                          onClick={handleDeleteSelectedNode}
                          className="inline-flex items-center gap-2 rounded-full border border-rose-900/70 bg-rose-950/20 px-4 py-2 text-sm text-rose-200 transition-colors hover:bg-rose-950/35"
                        >
                          <Trash2 className="h-4 w-4" />
                          Deletar
                        </button>
                      </div>
                    </div>
                  ) : null}
                </Panel>

                <Panel position="bottom-left">
                  <div className="flex flex-col gap-2 rounded-3xl border border-slate-800/90 bg-slate-950/92 p-2 shadow-xl backdrop-blur">
                    {quickCanvasTypes.map((itemType) => {
                      const meta = itemTypeMeta[itemType];
                      const Icon = meta.icon;
                      return (
                        <button
                          key={itemType}
                          onClick={() => handleCreateQuickCanvasItem(itemType)}
                          className="flex items-center gap-3 rounded-2xl border border-slate-800 bg-slate-900/80 px-3 py-2 text-left text-sm text-slate-200 transition-colors hover:border-slate-700 hover:bg-slate-800/90"
                        >
                          {creatingQuickItem === itemType ? (
                            <Loader2 className="h-4 w-4 animate-spin text-sky-300" />
                          ) : (
                            <Icon className="h-4 w-4 text-sky-300" />
                          )}
                          <span>{meta.label}</span>
                        </button>
                      );
                    })}
                  </div>
                </Panel>

                {showImportPanel ? (
                  <Panel position="bottom-right">
                    <div className="w-[360px] rounded-3xl border border-slate-800/90 bg-slate-950/95 p-4 shadow-2xl backdrop-blur">
                      <div className="mb-3 flex items-center justify-between">
                        <div>
                          <div className="text-sm font-semibold text-white">Importar elementos</div>
                          <div className="text-xs text-slate-500">Biblioteca da oficina dentro do quadro.</div>
                        </div>
                        <button
                          onClick={() => setShowImportPanel(false)}
                          className="rounded-full border border-slate-700 px-2 py-1 text-xs text-slate-400 hover:text-slate-200"
                        >
                          Fechar
                        </button>
                      </div>

                      <div className="mb-3 flex flex-wrap gap-2">
                        <button
                          onClick={() => setLibraryFilter("all")}
                          className={cn(
                            "rounded-full border px-3 py-1.5 text-xs font-medium",
                            libraryFilter === "all"
                              ? "border-sky-500/30 bg-sky-500/10 text-sky-100"
                              : "border-slate-800 bg-slate-900 text-slate-400"
                          )}
                        >
                          Todos
                        </button>
                        {quickCanvasTypes.map((itemType) => (
                          <button
                            key={itemType}
                            onClick={() => setLibraryFilter(itemType)}
                            className={cn(
                              "rounded-full border px-3 py-1.5 text-xs font-medium",
                              libraryFilter === itemType
                                ? "border-sky-500/30 bg-sky-500/10 text-sky-100"
                                : "border-slate-800 bg-slate-900 text-slate-400"
                            )}
                          >
                            {itemTypeMeta[itemType].label}
                          </button>
                        ))}
                      </div>

                      <button
                        onClick={handleSendScriptExcerptToBoard}
                        className="mb-4 w-full rounded-2xl border border-indigo-500/30 bg-indigo-500/10 px-4 py-2 text-sm font-medium text-indigo-100 transition-colors hover:bg-indigo-500/15"
                      >
                        Importar trecho selecionado do roteiro
                      </button>

                      <div className="max-h-[340px] space-y-2 overflow-y-auto pr-1">
                        {importPanelItems.length === 0 ? (
                          <div className="rounded-2xl border border-dashed border-slate-800 px-4 py-8 text-center text-sm text-slate-500">
                            Nenhum elemento disponivel para importar neste filtro.
                          </div>
                        ) : (
                          importPanelItems.map((item) => (
                            <div
                              key={item.id}
                              className="rounded-2xl border border-slate-800 bg-slate-900/80 p-3"
                            >
                              <div className="mb-2 flex items-center justify-between gap-3">
                                <div>
                                  <div className="text-[11px] font-bold uppercase tracking-[0.18em] text-slate-500">
                                    {itemTypeMeta[item.item_type].label}
                                  </div>
                                  <div className="text-sm font-semibold text-slate-100">
                                    {item.title || "Sem titulo"}
                                  </div>
                                </div>
                                <button
                                  onClick={() => handleAddItemToBoard(item)}
                                  className="inline-flex items-center gap-2 rounded-full border border-sky-500/30 bg-sky-500/10 px-3 py-1.5 text-xs font-semibold text-sky-100 hover:bg-sky-500/15"
                                >
                                  <Plus className="h-3.5 w-3.5" />
                                  Adicionar ao quadro
                                </button>
                              </div>
                              {item.body ? (
                                <p className="line-clamp-3 whitespace-pre-wrap text-xs leading-relaxed text-slate-400">
                                  {item.body}
                                </p>
                              ) : null}
                            </div>
                          ))
                        )}
                      </div>
                    </div>
                  </Panel>
                ) : null}
              </ReactFlow>
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
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => handleAddItemToBoard(item)}
                            className="rounded-full border border-sky-500/30 bg-sky-500/10 px-3 py-1.5 text-xs font-semibold text-sky-100 hover:bg-sky-500/15"
                          >
                            Adicionar ao quadro
                          </button>
                          <button
                            onClick={() => handleDeleteItem(item.id)}
                            className="rounded-full border border-rose-900/70 bg-rose-950/20 p-2 text-rose-200 hover:bg-rose-950/35"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>
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
