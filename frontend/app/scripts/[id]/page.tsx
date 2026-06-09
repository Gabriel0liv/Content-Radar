"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import Link from "next/link";
import { useRouter, useParams } from "next/navigation";
import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import ReactFlow, {
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  Edge,
  Node,
  MarkerType
} from "reactflow";
import "reactflow/dist/style.css";

import {
  getVideoProject,
  updateVideoProject,
  archiveVideoProject,
  deleteVideoProject,
  getVideoProjectNotes,
  createVideoProjectNote,
  updateVideoProjectNote,
  deleteVideoProjectNote,
  getVideoProjectReferences,
  createVideoProjectReference,
  deleteVideoProjectReference,
  getVideoProjectAudioIdeas,
  createVideoProjectAudioIdea,
  deleteVideoProjectAudioIdea,
  getVideoProjectBoard,
  saveVideoProjectBoard,
  getContentItems,
  getReferenceSources
} from "@/lib/api";
import {
  VideoProject,
  VideoProjectNote,
  VideoProjectNoteType,
  VideoProjectReference,
  VideoProjectAudioIdea,
  VideoProjectBoardNode,
  VideoProjectBoardEdge,
  ContentItem,
  ReferenceSource
} from "@/lib/types";
import {
  ArrowLeft,
  Save,
  Loader2,
  Trash2,
  Plus,
  BookOpen,
  Pin,
  Tag,
  Link2,
  Music,
  Maximize2,
  Layout,
  Clock,
  Bold,
  Italic,
  Heading1,
  Heading2,
  List,
  Archive,
  Volume2,
  Disc,
  Play,
  Sliders,
  AlertCircle
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

// Status configuration for visual badges
const statusConfig: Record<string, { label: string; class: string }> = {
  idea: { label: "Ideia", class: "bg-indigo-500/10 text-indigo-400 border-indigo-500/20" },
  researching: { label: "Pesquisando", class: "bg-blue-500/10 text-blue-400 border-blue-500/20" },
  scripting: { label: "Roteirizando", class: "bg-amber-500/10 text-amber-400 border-amber-500/20" },
  reviewing: { label: "Revisando", class: "bg-purple-500/10 text-purple-400 border-purple-500/20" },
  ready: { label: "Pronto", class: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" },
  produced: { label: "Produzido", class: "bg-slate-500/10 text-slate-300 border-slate-500/20" },
  archived: { label: "Arquivado", class: "bg-rose-500/10 text-rose-400 border-rose-500/20" }
};

// Available colors for board nodes — stores real CSS values, NOT Tailwind classes
const colors: { name: string; bg: string; border: string; text: string }[] = [
  { name: "Gray",    bg: "rgba(15,23,42,0.8)",   border: "#334155", text: "#cbd5e1" },
  { name: "Blue",    bg: "rgba(23,37,84,0.6)",   border: "#1e40af", text: "#bfdbfe" },
  { name: "Emerald", bg: "rgba(6,46,37,0.6)",    border: "#065f46", text: "#a7f3d0" },
  { name: "Indigo",  bg: "rgba(30,27,75,0.6)",   border: "#3730a3", text: "#c7d2fe" },
  { name: "Purple",  bg: "rgba(46,16,101,0.6)",  border: "#6b21a8", text: "#e9d5ff" },
  { name: "Orange",  bg: "rgba(67,20,7,0.6)",    border: "#9a3412", text: "#fed7aa" },
  { name: "Rose",    bg: "rgba(62,9,26,0.6)",    border: "#9f1239", text: "#fecdd3" }
];

export default function VideoWorkspacePage() {
  const router = useRouter();
  const params = useParams();
  const projectId = Number(params.id);

  // States
  const [project, setProject] = useState<VideoProject | null>(null);
  const [loading, setLoading] = useState(true);
  const [savingScript, setSavingScript] = useState(false);
  const [activeTab, setActiveTab] = useState<"roteiro" | "quadro" | "notas" | "referencias" | "musica">("roteiro");
  const [editorInitialized, setEditorInitialized] = useState(false);

  // Notes state
  const [notes, setNotes] = useState<VideoProjectNote[]>([]);
  const [newNoteBody, setNewNoteBody] = useState("");
  const [newNoteType, setNewNoteType] = useState<VideoProjectNoteType>("idea");
  const [newNoteTitle, setNewNoteTitle] = useState("");
  const [noteFilter, setNoteFilter] = useState<string>("all");

  // Note editing state (Fix 6)
  const [editingNoteId, setEditingNoteId] = useState<number | null>(null);
  const [editNoteTitle, setEditNoteTitle] = useState("");
  const [editNoteBody, setEditNoteBody] = useState("");

  // References state
  const [references, setReferences] = useState<VideoProjectReference[]>([]);
  const [refTitle, setRefTitle] = useState("");
  const [refUrl, setRefUrl] = useState("");
  const [selectedContentItemId, setSelectedContentItemId] = useState<string>("");
  const [selectedRefSourceId, setSelectedRefSourceId] = useState<string>("");
  const [selectedTranscriptId, setSelectedTranscriptId] = useState<string>("");
  
  const [allContentItems, setAllContentItems] = useState<ContentItem[]>([]);
  const [allRefSources, setAllRefSources] = useState<ReferenceSource[]>([]);

  // Audio Ideas state
  const [audios, setAudios] = useState<VideoProjectAudioIdea[]>([]);
  const [audioTitle, setAudioTitle] = useState("");
  const [audioUrl, setAudioUrl] = useState("");
  const [audioType, setAudioType] = useState("background_music");
  const [audioMood, setAudioMood] = useState("");
  const [audioLicense, setAudioLicense] = useState("");
  const [audioUsage, setAudioUsage] = useState("");

  // Canvas Board state
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [nodeTitleInput, setNodeTitleInput] = useState("");
  const [nodeBodyInput, setNodeBodyInput] = useState("");
  const [nodeColorInput, setNodeColorInput] = useState("Gray");
  const [savingBoard, setSavingBoard] = useState(false);

  // Text script values (live stats)
  const [scriptWordCount, setScriptWordCount] = useState(0);
  const [scriptDuration, setScriptDuration] = useState(0);

  // Tiptap setup
  const editor = useEditor({
    extensions: [StarterKit],
    content: "",
    onUpdate: ({ editor }) => {
      const text = editor.getText();
      const words = text.trim() ? text.trim().split(/\s+/).length : 0;
      setScriptWordCount(words);
      setScriptDuration(Math.round((words / 150) * 60));
    }
  });

  // Initialize editor content when both project and editor are ready
  useEffect(() => {
    if (project && editor && !editorInitialized) {
      if (project.script_content_json) {
        editor.commands.setContent(project.script_content_json);
      } else {
        editor.commands.setContent(project.script_text || "<p>Comece a escrever seu roteiro aqui...</p>");
      }
      setEditorInitialized(true);
    }
  }, [project, editor, editorInitialized]);

  // Load project details and other tabs elements
  const loadProjectData = useCallback(async () => {
    try {
      setLoading(true);
      const proj = await getVideoProject(projectId);
      setProject(proj);
      setScriptWordCount(proj.word_count);
      setScriptDuration(proj.estimated_duration_seconds || 0);

      // Load sub-modules
      const [projNotes, projRefs, projAudios, projBoard] = await Promise.all([
        getVideoProjectNotes(projectId),
        getVideoProjectReferences(projectId),
        getVideoProjectAudioIdeas(projectId),
        getVideoProjectBoard(projectId)
      ]);

      setNotes(projNotes);
      setReferences(projRefs);
      setAudios(projAudios);

      // Board React Flow mapping
      const mappedNodes: Node[] = projBoard.nodes.map(n => ({
        id: n.node_key,
        position: { x: n.x, y: n.y },
        data: { label: n.title || n.body || "Nó do Quadro", title: n.title, body: n.body, color: n.color },
        style: {
          background: colors.find(c => c.name === n.color)?.bg || "rgba(15,23,42,0.8)",
          color: colors.find(c => c.name === n.color)?.text || "#cbd5e1",
          border: `1px solid ${colors.find(c => c.name === n.color)?.border || "#334155"}`,
          borderRadius: "8px",
          padding: "10px",
          width: n.width || 160,
          height: n.height || 80
        }
      }));

      const mappedEdges: Edge[] = projBoard.edges.map(e => ({
        id: e.edge_key,
        source: e.source_node_key,
        target: e.target_node_key,
        label: typeof e.label === "string" ? e.label : null,
        animated: true,
        markerEnd: { type: MarkerType.ArrowClosed, color: "#6366f1" },
        style: { stroke: "#6366f1" }
      }));

      setNodes(mappedNodes);
      setEdges(mappedEdges);

    } catch (err: any) {
      toast.error("Erro ao carregar dados do projeto.");
    } finally {
      setLoading(false);
    }
  }, [projectId, setNodes, setEdges]);

  // Load static references options
  useEffect(() => {
    loadProjectData();

    // Load sources for linking references dropdowns
    getContentItems({ limit: 100 }).then(res => setAllContentItems(res.items)).catch(() => {});
    getReferenceSources({ limit: 100 }).then(res => setAllRefSources(res.items)).catch(() => {});
  }, [loadProjectData]);

  // Save script data
  const handleSaveScript = async () => {
    if (!project || !editor) return;
    try {
      setSavingScript(true);
      const textContent = editor.getText();
      const jsonContent = editor.getJSON();

      const updated = await updateVideoProject(projectId, {
        script_text: textContent,
        script_content_json: jsonContent
      });

      setProject(updated);
      setScriptWordCount(updated.word_count);
      setScriptDuration(updated.estimated_duration_seconds || 0);
      toast.success("Roteiro salvo com sucesso!");
    } catch (err: any) {
      toast.error(`Erro ao salvar roteiro: ${err.message}`);
    } finally {
      setSavingScript(false);
    }
  };

  // Update metadata fields directly
  const handleUpdateMeta = async (fields: Partial<VideoProject>) => {
    if (!project) return;
    try {
      const updated = await updateVideoProject(projectId, fields);
      setProject(updated);
      toast.success("Metadados atualizados!");
    } catch (err: any) {
      toast.error("Erro ao salvar metadados.");
    }
  };

  // Archive project
  const handleArchive = async () => {
    try {
      await archiveVideoProject(projectId);
      toast.success("Projeto arquivado!");
      router.push("/scripts");
    } catch (err: any) {
      toast.error("Erro ao arquivar projeto.");
    }
  };

  // Delete project
  const handleDeleteProject = async () => {
    if (!confirm("Tem certeza que deseja excluir permanentemente este projeto de vídeo? Todas as notas e quadro associados serão apagados.")) return;
    try {
      await deleteVideoProject(projectId);
      toast.success("Projeto excluído com sucesso!");
      router.push("/scripts");
    } catch (err: any) {
      toast.error("Erro ao excluir projeto.");
    }
  };

  // Notes operations
  const handleCreateNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newNoteBody.trim()) return;

    try {
      const payload = {
        title: newNoteTitle.trim() || null,
        body: newNoteBody.trim(),
        note_type: newNoteType,
        status: "open",
        pinned: false
      };
      const note = await createVideoProjectNote(projectId, payload);
      setNotes([note, ...notes]);
      setNewNoteTitle("");
      setNewNoteBody("");
      toast.success("Nota adicionada!");
    } catch (err: any) {
      toast.error("Erro ao adicionar nota.");
    }
  };

  const handleTogglePinNote = async (note: VideoProjectNote) => {
    try {
      const updated = await updateVideoProjectNote(note.id, { pinned: !note.pinned });
      setNotes(notes.map(n => n.id === note.id ? updated : n));
      toast.success(updated.pinned ? "Nota fixada!" : "Nota desafixada.");
    } catch (err: any) {
      toast.error("Erro ao atualizar nota.");
    }
  };

  const handleToggleNoteStatus = async (note: VideoProjectNote) => {
    try {
      const newStatus = note.status === "open" ? "done" : "open";
      const updated = await updateVideoProjectNote(note.id, { status: newStatus });
      setNotes(notes.map(n => n.id === note.id ? updated : n));
      toast.success(newStatus === "done" ? "Tarefa concluída!" : "Tarefa reaberta.");
    } catch (err: any) {
      toast.error("Erro ao atualizar status da tarefa.");
    }
  };

  const handleDeleteNote = async (noteId: number) => {
    try {
      await deleteVideoProjectNote(noteId);
      setNotes(notes.filter(n => n.id !== noteId));
      toast.success("Nota excluída.");
    } catch (err: any) {
      toast.error("Erro ao excluir nota.");
    }
  };

  // Note editing handlers (Fix 6)
  const handleStartEditNote = (note: VideoProjectNote) => {
    setEditingNoteId(note.id);
    setEditNoteTitle(note.title || "");
    setEditNoteBody(note.body);
  };

  const handleCancelEditNote = () => {
    setEditingNoteId(null);
    setEditNoteTitle("");
    setEditNoteBody("");
  };

  const handleSaveEditNote = async (noteId: number) => {
    if (!editNoteBody.trim()) return;
    try {
      const updated = await updateVideoProjectNote(noteId, {
        title: editNoteTitle.trim() || null,
        body: editNoteBody.trim()
      });
      setNotes(notes.map(n => n.id === noteId ? updated : n));
      setEditingNoteId(null);
      toast.success("Nota atualizada!");
    } catch (err: any) {
      toast.error("Erro ao atualizar nota.");
    }
  };

  const filteredNotes = useMemo(() => {
    let result = notes;
    if (noteFilter !== "all") {
      result = result.filter(n => n.note_type === noteFilter);
    }
    // Sort: pinned first, then newest
    return [...result].sort((a, b) => {
      if (a.pinned && !b.pinned) return -1;
      if (!a.pinned && b.pinned) return 1;
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    });
  }, [notes, noteFilter]);


  // References operations
  const handleAddReference = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!refTitle.trim() && !selectedContentItemId && !selectedRefSourceId && !selectedTranscriptId && !refUrl.trim()) {
      toast.error("Preencha pelo menos um campo para vincular a referência.");
      return;
    }

    try {
      const payload = {
        title: refTitle.trim() || null,
        external_url: refUrl.trim() || null,
        content_item_id: selectedContentItemId ? Number(selectedContentItemId) : null,
        reference_source_id: selectedRefSourceId ? Number(selectedRefSourceId) : null,
        transcript_id: selectedTranscriptId ? Number(selectedTranscriptId) : null,
      };

      const ref = await createVideoProjectReference(projectId, payload);
      setReferences([ref, ...references]);
      setRefTitle("");
      setRefUrl("");
      setSelectedContentItemId("");
      setSelectedRefSourceId("");
      setSelectedTranscriptId("");
      toast.success("Referência vinculada!");
    } catch (err: any) {
      toast.error("Erro ao vincular referência.");
    }
  };

  const handleDeleteReference = async (refId: number) => {
    try {
      await deleteVideoProjectReference(refId);
      setReferences(references.filter(r => r.id !== refId));
      toast.success("Referência desvinculada.");
    } catch (err: any) {
      toast.error("Erro ao excluir referência.");
    }
  };


  // Audio ideas operations
  const handleAddAudio = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!audioTitle.trim()) {
      toast.error("Título do áudio obrigatório.");
      return;
    }

    try {
      const payload = {
        audio_title: audioTitle.trim(),
        audio_url: audioUrl.trim() || null,
        audio_type: audioType,
        mood: audioMood.trim() || null,
        license_notes: audioLicense.trim() || null,
        usage_notes: audioUsage.trim() || null
      };

      const audio = await createVideoProjectAudioIdea(projectId, payload);
      setAudios([audio, ...audios]);
      setAudioTitle("");
      setAudioUrl("");
      setAudioMood("");
      setAudioLicense("");
      setAudioUsage("");
      toast.success("Ideia de áudio vinculada!");
    } catch (err: any) {
      toast.error("Erro ao adicionar áudio.");
    }
  };

  const handleDeleteAudio = async (audioId: number) => {
    try {
      await deleteVideoProjectAudioIdea(audioId);
      setAudios(audios.filter(a => a.id !== audioId));
      toast.success("Áudio desvinculado.");
    } catch (err: any) {
      toast.error("Erro ao excluir áudio.");
    }
  };


  // Board Canvas operations
  const onConnect = useCallback((connection: Connection) => {
    const newEdge: Edge = {
      id: `edge-${Date.now()}`,
      source: connection.source!,
      target: connection.target!,
      animated: true,
      markerEnd: { type: MarkerType.ArrowClosed, color: "#6366f1" },
      style: { stroke: "#6366f1" }
    };
    setEdges((eds) => addEdge(newEdge, eds));
  }, [setEdges]);

  const handleAddBoardNode = () => {
    const nodeKey = `node-${Date.now()}`;
    const newNode: Node = {
      id: nodeKey,
      position: { x: 150 + Math.random() * 50, y: 150 + Math.random() * 50 },
      data: { label: "Nova Nota", title: "Nova Nota", body: "Escreva algo...", color: "Gray" },
      style: {
        background: "rgba(15, 23, 42, 0.8)",
        color: "#fff",
        border: "1px solid #334155",
        borderRadius: "8px",
        padding: "10px",
        width: 160,
        height: 80
      }
    };
    setNodes((nds) => [...nds, newNode]);
  };

  const handleNodeClick = (_e: any, node: Node) => {
    setSelectedNodeId(node.id);
    setNodeTitleInput(node.data.title || "");
    setNodeBodyInput(node.data.body || "");
    setNodeColorInput(node.data.color || "Gray");
  };

  const handleUpdateNodeProperties = () => {
    if (!selectedNodeId) return;

    setNodes((nds) =>
      nds.map((node) => {
        if (node.id === selectedNodeId) {
          const colorDef = colors.find(c => c.name === nodeColorInput) || colors[0];
          return {
            ...node,
            data: {
              ...node.data,
              label: nodeTitleInput || nodeBodyInput || "Nota",
              title: nodeTitleInput,
              body: nodeBodyInput,
              color: nodeColorInput
            },
            style: {
              ...node.style,
              background: colorDef.bg,
              color: colorDef.text,
              border: `1px solid ${colorDef.border}`
            }
          };
        }
        return node;
      })
    );
    toast.success("Elemento do quadro atualizado localmente!");
  };

  const handleDeleteNodeFromBoard = () => {
    if (!selectedNodeId) return;
    setNodes((nds) => nds.filter((node) => node.id !== selectedNodeId));
    setEdges((eds) => eds.filter((edge) => edge.source !== selectedNodeId && edge.target !== selectedNodeId));
    setSelectedNodeId(null);
    toast.success("Elemento removido do quadro!");
  };

  const handleSaveBoard = async () => {
    try {
      setSavingBoard(true);
      const boardNodes: VideoProjectBoardNode[] = nodes.map(n => ({
        node_key: n.id,
        node_type: "note",
        title: n.data.title || null,
        body: n.data.body || null,
        x: n.position.x,
        y: n.position.y,
        width: Number(n.style?.width) || 160,
        height: Number(n.style?.height) || 80,
        color: n.data.color || "Gray"
      }));

      const boardEdges: VideoProjectBoardEdge[] = edges.map(e => ({
        edge_key: e.id,
        source_node_key: e.source,
        target_node_key: e.target,
        label: typeof e.label === "string" ? e.label : null
      }));

      await saveVideoProjectBoard(projectId, {
        nodes: boardNodes,
        edges: boardEdges
      });

      toast.success("Estrutura do quadro salva com sucesso!");
    } catch (err: any) {
      toast.error("Erro ao salvar quadro criativo.");
    } finally {
      setSavingBoard(false);
    }
  };


  if (loading && !project) {
    return (
      <div className="flex h-[80vh] flex-col items-center justify-center gap-3">
        <Loader2 className="h-9 w-9 animate-spin text-indigo-500" />
        <span className="text-sm text-slate-400 font-medium">Carregando painel criativo...</span>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="rounded-xl border border-rose-950 bg-rose-950/20 p-5 text-rose-250 flex items-center gap-3">
        <AlertCircle className="h-5 w-5 text-rose-450 shrink-0" />
        <span className="text-sm">Projeto de vídeo não encontrado.</span>
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-12">
      {/* Back & Actions Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-slate-850 pb-5">
        <div className="flex items-center gap-3">
          <Link
            href="/scripts"
            className="flex h-9 w-9 items-center justify-center rounded-lg border border-slate-800 bg-[#0b101c] hover:bg-slate-900 text-slate-400 hover:text-slate-205 transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div>
            <h2 className="text-2xl font-bold tracking-tight text-white font-sans flex items-center gap-2">
              {project.title}
              <span className={cn("inline-flex items-center rounded px-2 py-0.5 text-[9px] font-bold border tracking-wider uppercase", statusConfig[project.status]?.class)}>
                {statusConfig[project.status]?.label}
              </span>
            </h2>
            <div className="flex items-center gap-2 mt-0.5 text-xs text-slate-450">
              {project.niche && <span>Nicho: <strong className="text-slate-300">{project.niche}</strong></span>}
              {project.niche && <span>•</span>}
              <span>Prioridade: <strong className="text-slate-300">P{project.priority}</strong></span>
            </div>
          </div>
        </div>

        {/* Action button controls */}
        <div className="flex items-center gap-2">
          {/* Status select dropdown */}
          <select
            value={project.status}
            onChange={(e) => handleUpdateMeta({ status: e.target.value as any })}
            className="rounded-lg border border-slate-800 bg-slate-950 px-3 h-10 text-xs font-bold text-slate-300 outline-none focus:border-indigo-500 transition-all cursor-pointer"
          >
            <option value="idea">Mudar para: Ideia</option>
            <option value="researching">Mudar para: Pesquisando</option>
            <option value="scripting">Mudar para: Roteirizando</option>
            <option value="reviewing">Mudar para: Revisando</option>
            <option value="ready">Mudar para: Pronto</option>
            <option value="produced">Mudar para: Produzido</option>
          </select>

          {/* Archive Project */}
          <button
            onClick={handleArchive}
            className="flex h-10 px-3.5 items-center gap-2 rounded-lg border border-slate-800 bg-[#0b101c] hover:bg-slate-900 text-slate-400 hover:text-indigo-400 hover:border-indigo-950/20 transition-all font-semibold text-xs"
            title="Arquivar Projeto"
          >
            <Archive className="h-4 w-4" />
            <span className="hidden sm:inline">Arquivar</span>
          </button>

          {/* Delete Project */}
          <button
            onClick={handleDeleteProject}
            className="flex h-10 w-10 items-center justify-center rounded-lg border border-rose-950 bg-rose-950/5 hover:bg-rose-900 text-rose-450 hover:text-white transition-colors"
            title="Excluir Projeto"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Tabs list navigation */}
      <div className="flex border-b border-slate-850 gap-1.5 overflow-x-auto select-none">
        {(["roteiro", "quadro", "notas", "referencias", "musica"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={cn(
              "px-4 py-2 text-xs font-bold border-b-2 capitalize transition-all shrink-0",
              activeTab === tab
                ? "border-indigo-500 text-white"
                : "border-transparent text-slate-500 hover:text-slate-300 hover:border-slate-800"
            )}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Tab Panels */}
      <div className="mt-4">
        {/* TAB 1: ROTEIRO (SCRIPT) */}
        {activeTab === "roteiro" && (
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
            <div className="lg:col-span-3 space-y-4">
              {/* Rich text Editor container */}
              <div className="rounded-xl border border-slate-800 bg-[#0b101c]/15 overflow-hidden flex flex-col min-h-[500px]">
                {/* Formatting Toolbar */}
                {editor && (
                  <div className="border-b border-slate-800 bg-slate-950/80 px-4 py-2.5 flex flex-wrap gap-1 items-center select-none">
                    <button
                      onClick={() => editor.chain().focus().toggleBold().run()}
                      className={cn("p-1.5 rounded hover:bg-slate-900 transition-colors text-slate-400 hover:text-slate-205", editor.isActive("bold") && "bg-slate-800 text-white")}
                      title="Negrito"
                    >
                      <Bold className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => editor.chain().focus().toggleItalic().run()}
                      className={cn("p-1.5 rounded hover:bg-slate-900 transition-colors text-slate-400 hover:text-slate-205", editor.isActive("italic") && "bg-slate-800 text-white")}
                      title="Itálico"
                    >
                      <Italic className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
                      className={cn("p-1.5 rounded hover:bg-slate-900 transition-colors text-slate-400 hover:text-slate-205", editor.isActive("heading", { level: 1 }) && "bg-slate-800 text-white")}
                      title="Título 1"
                    >
                      <Heading1 className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
                      className={cn("p-1.5 rounded hover:bg-slate-900 transition-colors text-slate-400 hover:text-slate-205", editor.isActive("heading", { level: 2 }) && "bg-slate-800 text-white")}
                      title="Título 2"
                    >
                      <Heading2 className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => editor.chain().focus().toggleBulletList().run()}
                      className={cn("p-1.5 rounded hover:bg-slate-900 transition-colors text-slate-400 hover:text-slate-205", editor.isActive("bulletList") && "bg-slate-800 text-white")}
                      title="Lista de marcadores"
                    >
                      <List className="h-4 w-4" />
                    </button>
                  </div>
                )}
                
                {/* Editor Content Area */}
                <div className="flex-1 p-5 prose prose-invert max-w-none text-slate-200 focus:outline-none min-h-[400px]">
                  <EditorContent editor={editor} className="outline-none" />
                </div>
              </div>

              {/* Word Count Display & Actions */}
              <div className="flex items-center justify-between bg-slate-950/20 p-4 rounded-xl border border-slate-850">
                <div className="flex items-center gap-4 text-xs font-semibold text-slate-500">
                  <span className="flex items-center gap-1">
                    <BookOpen className="h-4 w-4 text-slate-600" />
                    {scriptWordCount} palavras
                  </span>
                  <span className="flex items-center gap-1">
                    <Clock className="h-4 w-4 text-slate-600" />
                    Leitura: ~{scriptDuration}s (150ppm)
                  </span>
                </div>

                <button
                  onClick={handleSaveScript}
                  disabled={savingScript}
                  className="flex items-center gap-1.5 rounded-lg bg-indigo-600 px-4 py-2 text-xs font-bold text-white shadow hover:bg-indigo-500 transition-all select-none disabled:opacity-40"
                >
                  {savingScript ? (
                    <>
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      <span>Salvando Roteiro...</span>
                    </>
                  ) : (
                    <>
                      <Save className="h-3.5 w-3.5" />
                      <span>Salvar Roteiro</span>
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Script Sidebar metadata form */}
            <div className="rounded-xl border border-slate-800 bg-[#0b101c]/35 p-5 shadow-sm space-y-4">
              <h3 className="text-sm font-bold text-white uppercase tracking-wider select-none">Propriedades do Roteiro</h3>
              
              {/* Working Title */}
              <div className="space-y-1">
                <span className="block text-[10px] font-bold text-slate-500 uppercase tracking-wider">Título de Trabalho</span>
                <input
                  type="text"
                  value={project.working_title || ""}
                  onChange={(e) => setProject({ ...project, working_title: e.target.value })}
                  onBlur={() => handleUpdateMeta({ working_title: project.working_title })}
                  className="w-full rounded bg-slate-950 border border-slate-850 px-2.5 py-1.5 text-xs text-slate-200 outline-none focus:border-indigo-500 transition-colors font-medium"
                  placeholder="Ex: Roteiro v1 - Rust"
                />
              </div>

              {/* Niche Theme */}
              <div className="space-y-1">
                <span className="block text-[10px] font-bold text-slate-500 uppercase tracking-wider">Nicho / Assunto</span>
                <input
                  type="text"
                  value={project.niche || ""}
                  onChange={(e) => setProject({ ...project, niche: e.target.value })}
                  onBlur={() => handleUpdateMeta({ niche: project.niche })}
                  className="w-full rounded bg-slate-950 border border-slate-850 px-2.5 py-1.5 text-xs text-slate-200 outline-none focus:border-indigo-500 transition-colors font-medium"
                  placeholder="Ex: Finanças"
                />
              </div>

              {/* Target Duration */}
              <div className="space-y-1">
                <span className="block text-[10px] font-bold text-slate-500 uppercase tracking-wider">Duração Alvo (segundos)</span>
                <input
                  type="number"
                  value={project.target_duration_seconds || ""}
                  onChange={(e) => setProject({ ...project, target_duration_seconds: Number(e.target.value) })}
                  onBlur={() => handleUpdateMeta({ target_duration_seconds: project.target_duration_seconds })}
                  className="w-full rounded bg-slate-950 border border-slate-850 px-2.5 py-1.5 text-xs text-slate-200 outline-none focus:border-indigo-500 transition-colors font-mono font-bold"
                  placeholder="Ex: 600"
                />
              </div>

              {/* Platform */}
              <div className="space-y-1">
                <span className="block text-[10px] font-bold text-slate-500 uppercase tracking-wider">Plataforma</span>
                <input
                  type="text"
                  value={project.target_platform || ""}
                  onChange={(e) => setProject({ ...project, target_platform: e.target.value })}
                  onBlur={() => handleUpdateMeta({ target_platform: project.target_platform })}
                  className="w-full rounded bg-slate-950 border border-slate-850 px-2.5 py-1.5 text-xs text-slate-200 outline-none focus:border-indigo-500 transition-colors font-medium"
                  placeholder="Ex: Instagram"
                />
              </div>

              {/* Format */}
              <div className="space-y-1">
                <span className="block text-[10px] font-bold text-slate-500 uppercase tracking-wider">Formato do Vídeo</span>
                <input
                  type="text"
                  value={project.video_format || ""}
                  onChange={(e) => setProject({ ...project, video_format: e.target.value })}
                  onBlur={() => handleUpdateMeta({ video_format: project.video_format })}
                  className="w-full rounded bg-slate-950 border border-slate-850 px-2.5 py-1.5 text-xs text-slate-200 outline-none focus:border-indigo-500 transition-colors font-medium"
                  placeholder="Ex: Shorts (Vertical)"
                />
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: QUADRO CRIATIVO (CANVAS BOARD) */}
        {activeTab === "quadro" && (
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
            <div className="lg:col-span-3 space-y-4">
              <div className="h-[550px] w-full border border-slate-800 rounded-xl bg-slate-950/40 relative overflow-hidden">
                <ReactFlow
                  nodes={nodes}
                  edges={edges}
                  onNodesChange={onNodesChange}
                  onEdgesChange={onEdgesChange}
                  onConnect={onConnect}
                  onNodeClick={handleNodeClick}
                  fitView
                >
                  <Background color="#334155" gap={16} />
                  <Controls className="bg-slate-900 border-slate-800 text-white fill-current fill-white rounded shadow-lg overflow-hidden [&>button]:border-slate-800" />
                </ReactFlow>
              </div>

              {/* Board controls */}
              <div className="flex items-center justify-between bg-slate-950/20 p-4 rounded-xl border border-slate-850">
                <button
                  onClick={handleAddBoardNode}
                  className="flex items-center gap-1.5 rounded-lg border border-slate-800 bg-[#0b101c] hover:bg-slate-900 px-4 py-2 text-xs font-bold text-indigo-400 transition-colors"
                >
                  <Plus className="h-4 w-4" />
                  <span>Adicionar Nota</span>
                </button>

                <button
                  onClick={handleSaveBoard}
                  disabled={savingBoard}
                  className="flex items-center gap-1.5 rounded-lg bg-indigo-600 px-4 py-2 text-xs font-bold text-white shadow hover:bg-indigo-500 transition-all select-none disabled:opacity-40"
                >
                  {savingBoard ? (
                    <>
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      <span>Salvando Quadro...</span>
                    </>
                  ) : (
                    <>
                      <Save className="h-3.5 w-3.5" />
                      <span>Salvar Quadro</span>
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Visual Board node properties editor panel */}
            <div className="rounded-xl border border-slate-800 bg-[#0b101c]/35 p-5 shadow-sm space-y-4">
              <h3 className="text-sm font-bold text-white uppercase tracking-wider select-none">Propriedades do Elemento</h3>
              {selectedNodeId ? (
                <div className="space-y-4">
                  {/* Title */}
                  <div className="space-y-1">
                    <span className="block text-[10px] font-bold text-slate-500 uppercase tracking-wider">Título da Nota</span>
                    <input
                      type="text"
                      value={nodeTitleInput}
                      onChange={(e) => setNodeTitleInput(e.target.value)}
                      className="w-full rounded bg-slate-950 border border-slate-850 px-2.5 py-1.5 text-xs text-slate-200 outline-none focus:border-indigo-500 transition-colors font-semibold"
                    />
                  </div>

                  {/* Body */}
                  <div className="space-y-1">
                    <span className="block text-[10px] font-bold text-slate-500 uppercase tracking-wider">Conteúdo</span>
                    <textarea
                      value={nodeBodyInput}
                      onChange={(e) => setNodeBodyInput(e.target.value)}
                      rows={4}
                      className="w-full rounded bg-slate-950 border border-slate-850 px-2.5 py-1.5 text-xs text-slate-200 outline-none focus:border-indigo-500 transition-colors font-medium resize-none"
                    />
                  </div>

                  {/* Color Selector */}
                  <div className="space-y-1.5">
                    <span className="block text-[10px] font-bold text-slate-500 uppercase tracking-wider">Cor do Card</span>
                    <div className="grid grid-cols-4 gap-1.5">
                      {colors.map((c) => (
                        <button
                          key={c.name}
                          type="button"
                          onClick={() => setNodeColorInput(c.name)}
                          style={{ background: c.bg, borderColor: c.border, color: c.text }}
                          className={cn(
                            "h-6 rounded border text-[9px] font-bold transition-all truncate px-0.5",
                            nodeColorInput === c.name ? "ring-2 ring-indigo-500 scale-105" : "opacity-80"
                          )}
                        >
                          {c.name}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Action buttons */}
                  <div className="flex items-center gap-2 pt-2 border-t border-slate-800/60">
                    <button
                      onClick={handleUpdateNodeProperties}
                      className="flex-1 flex items-center justify-center gap-1 rounded bg-indigo-600/15 hover:bg-indigo-600/25 border border-indigo-500/20 text-indigo-400 py-1.5 text-xs font-bold transition-colors"
                    >
                      Atualizar
                    </button>
                    <button
                      onClick={handleDeleteNodeFromBoard}
                      className="h-8 w-8 flex items-center justify-center rounded bg-rose-950/15 hover:bg-rose-950/25 border border-rose-900/20 text-rose-400 transition-colors"
                      title="Deletar nó"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ) : (
                <div className="text-center text-xs text-slate-500 py-12">
                  Selecione um card no quadro para editar suas propriedades.
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 3: NOTAS AVULSAS (LOOSE NOTES) */}
        {activeTab === "notas" && (
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
            {/* Create note sidebar form */}
            <div className="rounded-xl border border-slate-800 bg-[#0b101c]/35 p-5 shadow-sm self-start">
              <h3 className="text-sm font-bold text-white mb-4 uppercase tracking-wider select-none">Adicionar Nota</h3>
              <form onSubmit={handleCreateNote} className="space-y-4">
                <div className="space-y-1">
                  <span className="block text-[10px] font-bold text-slate-500 uppercase tracking-wider">Título</span>
                  <input
                    type="text"
                    placeholder="Título da nota (opcional)"
                    value={newNoteTitle}
                    onChange={(e) => setNewNoteTitle(e.target.value)}
                    className="w-full rounded bg-slate-950 border border-slate-850 px-2.5 py-1.5 text-xs text-slate-200 outline-none focus:border-indigo-500 transition-colors font-semibold"
                  />
                </div>

                <div className="space-y-1">
                  <span className="block text-[10px] font-bold text-slate-500 uppercase tracking-wider">Tipo da Nota</span>
                  <select
                    value={newNoteType}
                    onChange={(e) => setNewNoteType(e.target.value as any)}
                    className="w-full rounded bg-slate-950 border border-slate-850 px-2.5 py-1.5 text-xs text-slate-350 outline-none focus:border-indigo-500 font-semibold"
                  >
                    <option value="idea">Ideia</option>
                    <option value="research">Pesquisa</option>
                    <option value="script_note">Nota do Roteiro</option>
                    <option value="production_note">Produção</option>
                    <option value="music_idea">Ideia Musical</option>
                    <option value="thumbnail_idea">Capa / Thumbnail</option>
                    <option value="todo">Tarefa (To Do)</option>
                    <option value="other">Outro</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <span className="block text-[10px] font-bold text-slate-500 uppercase tracking-wider">Conteúdo *</span>
                  <textarea
                    placeholder="Escreva sua nota aqui..."
                    value={newNoteBody}
                    onChange={(e) => setNewNoteBody(e.target.value)}
                    rows={4}
                    className="w-full rounded bg-slate-950 border border-slate-850 px-2.5 py-1.5 text-xs text-slate-200 outline-none focus:border-indigo-500 transition-colors font-medium resize-none"
                    required
                  />
                </div>

                <button
                  type="submit"
                  disabled={!newNoteBody.trim()}
                  className="w-full flex items-center justify-center gap-1.5 rounded-lg bg-indigo-600 px-4 py-2 text-xs font-bold text-white hover:bg-indigo-500 transition-all select-none disabled:opacity-40"
                >
                  <Plus className="h-4 w-4" />
                  <span>Adicionar</span>
                </button>
              </form>
            </div>

            {/* Note Board Display List */}
            <div className="lg:col-span-3 space-y-4">
              {/* Type Filters Bar */}
              <div className="flex flex-wrap gap-1.5 border-b border-slate-850/60 pb-3 select-none">
                {[
                  { value: "all", label: "Todas" },
                  { value: "idea", label: "Ideias" },
                  { value: "research", label: "Pesquisa" },
                  { value: "script_note", label: "Nota Roteiro" },
                  { value: "production_note", label: "Produção" },
                  { value: "thumbnail_idea", label: "Thumbnails" },
                  { value: "todo", label: "Tarefas" }
                ].map((f) => (
                  <button
                    key={f.value}
                    onClick={() => setNoteFilter(f.value)}
                    className={cn(
                      "px-3 py-1 rounded text-[10px] font-bold uppercase border tracking-wider transition-colors",
                      noteFilter === f.value
                        ? "bg-indigo-650/15 border-indigo-500/25 text-indigo-400"
                        : "bg-slate-950/20 border-slate-850 text-slate-500 hover:text-slate-300"
                    )}
                  >
                    {f.label}
                  </button>
                ))}
              </div>

              {/* Note card grid layout */}
              {filteredNotes.length === 0 ? (
                <div className="text-center text-xs text-slate-500 py-16 border border-dashed border-slate-800 rounded-xl bg-slate-950/10">
                  Nenhuma nota salva para este filtro. Escreva uma no painel ao lado!
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {filteredNotes.map((note) => (
                    <div
                      key={note.id}
                      className={cn(
                        "relative flex flex-col justify-between rounded-xl border p-4 backdrop-blur-sm transition-all shadow-md group",
                        note.pinned ? "border-indigo-500/40 bg-indigo-950/5" : "border-slate-800 bg-[#0b101c]/15"
                      )}
                    >
                      {editingNoteId === note.id ? (
                        /* Inline edit mode */
                        <div className="space-y-3">
                          <input
                            type="text"
                            value={editNoteTitle}
                            onChange={(e) => setEditNoteTitle(e.target.value)}
                            placeholder="Título (opcional)"
                            className="w-full rounded bg-slate-950 border border-slate-700 px-2.5 py-1.5 text-xs text-slate-200 outline-none focus:border-indigo-500 font-semibold"
                          />
                          <textarea
                            value={editNoteBody}
                            onChange={(e) => setEditNoteBody(e.target.value)}
                            rows={4}
                            className="w-full rounded bg-slate-950 border border-slate-700 px-2.5 py-1.5 text-xs text-slate-200 outline-none focus:border-indigo-500 font-medium resize-none"
                          />
                          <div className="flex gap-2">
                            <button
                              onClick={() => handleSaveEditNote(note.id)}
                              className="flex-1 rounded bg-indigo-600 hover:bg-indigo-500 px-3 py-1.5 text-xs font-bold text-white transition-colors"
                            >
                              Salvar
                            </button>
                            <button
                              onClick={handleCancelEditNote}
                              className="flex-1 rounded border border-slate-700 bg-slate-950 hover:bg-slate-900 px-3 py-1.5 text-xs font-bold text-slate-400 transition-colors"
                            >
                              Cancelar
                            </button>
                          </div>
                        </div>
                      ) : (
                        /* View mode */
                        <div>
                          {/* Note Header Info */}
                          <div className="flex items-center justify-between gap-2 mb-2">
                            <span className="text-[9px] font-bold uppercase tracking-wider text-indigo-400 bg-indigo-500/5 px-2 py-0.5 rounded border border-indigo-500/10">
                              {note.note_type}
                            </span>
                            
                            <div className="flex items-center gap-1">
                              {/* Edit note button */}
                              <button
                                onClick={() => handleStartEditNote(note)}
                                className="p-1 rounded hover:bg-slate-900 transition-colors text-slate-600 hover:text-slate-300 opacity-0 group-hover:opacity-100"
                                title="Editar nota"
                              >
                                <svg xmlns="http://www.w3.org/2000/svg" className="h-3 w-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                  <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                                  <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                                </svg>
                              </button>

                              {/* Pin note button */}
                              <button
                                onClick={() => handleTogglePinNote(note)}
                                className={cn("p-1 rounded hover:bg-slate-900 transition-colors text-slate-500 hover:text-slate-300", note.pinned && "text-indigo-400")}
                              >
                                <Pin className="h-3 w-3" />
                              </button>

                              {/* To Do Checkbox if todo type */}
                              {note.note_type === "todo" && (
                                <button
                                  onClick={() => handleToggleNoteStatus(note)}
                                  className={cn("p-1 rounded hover:bg-slate-900 transition-colors text-slate-500 hover:text-slate-300", note.status === "done" && "text-emerald-400")}
                                >
                                  <Sliders className="h-3 w-3" />
                                </button>
                              )}

                              {/* Delete Note button */}
                              <button
                                onClick={() => handleDeleteNote(note.id)}
                                className="p-1 rounded hover:bg-rose-950/20 text-slate-600 hover:text-rose-400 opacity-0 group-hover:opacity-100 transition-opacity"
                              >
                                <Trash2 className="h-3 w-3" />
                              </button>
                            </div>
                          </div>

                          {/* Note Title */}
                          {note.title && (
                            <h5 className="text-xs font-bold text-slate-200 mb-1 leading-snug">
                              {note.title}
                            </h5>
                          )}

                          {/* Note Body */}
                          <p className={cn(
                            "text-xs leading-relaxed text-slate-400 whitespace-pre-wrap",
                            note.status === "done" && "line-through text-slate-500"
                          )}>
                            {note.body}
                          </p>

                          {/* Created date footer */}
                          <div className="mt-3 pt-2.5 border-t border-slate-800/30 text-[10px] text-slate-500 font-mono font-medium">
                            Adicionado em: {new Date(note.created_at).toLocaleString("pt-BR")}
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 4: REFERÊNCIAS VINCULADAS (REFERENCES) */}
        {activeTab === "referencias" && (
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
            {/* Create/Link reference form panel */}
            <div className="rounded-xl border border-slate-800 bg-[#0b101c]/35 p-5 shadow-sm self-start">
              <h3 className="text-sm font-bold text-white mb-4 uppercase tracking-wider select-none">Vincular Referência</h3>
              <form onSubmit={handleAddReference} className="space-y-4">
                <div className="space-y-1">
                  <span className="block text-[10px] font-bold text-slate-500 uppercase tracking-wider">Título da Referência</span>
                  <input
                    type="text"
                    placeholder="Título amigável (opcional)"
                    value={refTitle}
                    onChange={(e) => setRefTitle(e.target.value)}
                    className="w-full rounded bg-slate-950 border border-slate-850 px-2.5 py-1.5 text-xs text-slate-200 outline-none focus:border-indigo-500 transition-colors font-semibold"
                  />
                </div>

                <div className="space-y-1">
                  <span className="block text-[10px] font-bold text-slate-500 uppercase tracking-wider">Link / URL Externa</span>
                  <input
                    type="url"
                    placeholder="URL externa (opcional)"
                    value={refUrl}
                    onChange={(e) => setRefUrl(e.target.value)}
                    className="w-full rounded bg-slate-950 border border-slate-850 px-2.5 py-1.5 text-xs text-slate-200 outline-none focus:border-indigo-500 transition-colors font-medium"
                  />
                </div>

                <div className="space-y-1">
                  <span className="block text-[10px] font-bold text-slate-500 uppercase tracking-wider">Ligar a Item de Curadoria</span>
                  <select
                    value={selectedContentItemId}
                    onChange={(e) => setSelectedContentItemId(e.target.value)}
                    className="w-full rounded bg-slate-950 border border-slate-850 px-2.5 py-1.5 text-xs text-slate-350 outline-none focus:border-indigo-500 font-semibold"
                  >
                    <option value="">Nenhum</option>
                    {allContentItems.map(item => (
                      <option key={item.id} value={item.id}>{item.title.substring(0, 40)}...</option>
                    ))}
                  </select>
                </div>

                <div className="space-y-1">
                  <span className="block text-[10px] font-bold text-slate-500 uppercase tracking-wider">Ligar a Fonte Importada (YouTube)</span>
                  <select
                    value={selectedRefSourceId}
                    onChange={(e) => setSelectedRefSourceId(e.target.value)}
                    className="w-full rounded bg-slate-950 border border-slate-800 px-2.5 py-1.5 text-xs text-slate-300 outline-none focus:border-indigo-500 font-semibold"
                  >
                    <option value="">Nenhum</option>
                    {allRefSources.map(src => (
                      <option key={src.id} value={src.id}>{src.title.substring(0, 40)}...</option>
                    ))}
                  </select>
                </div>

                <button
                  type="submit"
                  className="w-full flex items-center justify-center gap-1.5 rounded-lg bg-indigo-600 px-4 py-2 text-xs font-bold text-white hover:bg-indigo-500 transition-all select-none"
                >
                  <Link2 className="h-4 w-4" />
                  <span>Vincular</span>
                </button>
              </form>
            </div>

            {/* References list table */}
            <div className="lg:col-span-3 space-y-4">
              {references.length === 0 ? (
                <div className="text-center text-xs text-slate-500 py-16 border border-dashed border-slate-800 rounded-xl bg-slate-950/10">
                  Nenhuma referência vinculada a este projeto de vídeo ainda. Use o painel lateral para associar itens.
                </div>
              ) : (
                <div className="rounded-xl border border-slate-800 bg-[#0b101c]/25 overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="w-full border-collapse text-left text-sm text-slate-300">
                      <thead className="border-b border-slate-800 bg-[#0c1223]/60 text-xs font-bold uppercase tracking-wider text-slate-400">
                        <tr>
                          <th className="px-5 py-3.5">Título / Tipo</th>
                          <th className="px-5 py-3.5">Link / Origem</th>
                          <th className="px-5 py-3.5 text-center w-20">Ações</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/50">
                        {references.map((ref) => (
                          <tr key={ref.id} className="hover:bg-slate-900/10 transition-colors">
                            {/* Title & Badge */}
                            <td className="px-5 py-3.5">
                              <div className="flex flex-col gap-0.5">
                                <span className="font-semibold text-slate-200">
                                  {ref.title || "Referência Sem Nome"}
                                </span>
                                <div className="flex gap-1">
                                  {ref.content_item_id && (
                                    <span className="inline-flex text-[9px] font-bold bg-amber-500/10 text-amber-400 border border-amber-550/15 rounded px-1.5 py-0.5">Curadoria</span>
                                  )}
                                  {ref.reference_source_id && (
                                    <span className="inline-flex text-[9px] font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-550/15 rounded px-1.5 py-0.5">Transição YT</span>
                                  )}
                                  {ref.external_url && !ref.content_item_id && !ref.reference_source_id && (
                                    <span className="inline-flex text-[9px] font-bold bg-slate-500/10 text-slate-400 border border-slate-550/15 rounded px-1.5 py-0.5">Link Externo</span>
                                  )}
                                </div>
                              </div>
                            </td>

                            {/* Linked target URLs */}
                            <td className="px-5 py-3.5">
                              {ref.external_url ? (
                                <a
                                  href={ref.external_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-xs font-semibold text-indigo-450 hover:underline flex items-center gap-1"
                                >
                                  <span>{ref.external_url.substring(0, 45)}...</span>
                                </a>
                              ) : ref.content_item_id ? (
                                <Link
                                  href={`/content/${ref.content_item_id}`}
                                  className="text-xs font-semibold text-indigo-450 hover:underline"
                                >
                                  Ver Item Curado #{ref.content_item_id}
                                </Link>
                              ) : ref.reference_source_id ? (
                                <Link
                                  href={`/references/${ref.reference_source_id}`}
                                  className="text-xs font-semibold text-indigo-450 hover:underline"
                                >
                                  Ver Fonte Transcrita #{ref.reference_source_id}
                                </Link>
                              ) : (
                                <span className="text-slate-500 text-xs font-medium">-</span>
                              )}
                            </td>

                            {/* Actions */}
                            <td className="px-5 py-3.5 text-center">
                              <button
                                onClick={() => handleDeleteReference(ref.id)}
                                className="h-7 w-7 rounded flex items-center justify-center hover:bg-rose-950/20 text-slate-500 hover:text-rose-400 transition-colors mx-auto"
                                title="Remover Referência"
                              >
                                <Trash2 className="h-4 w-4" />
                              </button>
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
        )}

        {/* TAB 5: MÚSICA / AMBIÊNCIA (AUDIO IDEAS) */}
        {activeTab === "musica" && (
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
            {/* Create Audio form */}
            <div className="rounded-xl border border-slate-800 bg-[#0b101c]/35 p-5 shadow-sm self-start">
              <h3 className="text-sm font-bold text-white mb-4 uppercase tracking-wider select-none">Nova Ideia de Áudio</h3>
              <form onSubmit={handleAddAudio} className="space-y-4">
                <div className="space-y-1">
                  <span className="block text-[10px] font-bold text-slate-500 uppercase tracking-wider">Título da Música / Faixa *</span>
                  <input
                    type="text"
                    placeholder="Ex: Synthwave Beat 120bpm"
                    value={audioTitle}
                    onChange={(e) => setAudioTitle(e.target.value)}
                    className="w-full rounded bg-slate-950 border border-slate-850 px-2.5 py-1.5 text-xs text-slate-200 outline-none focus:border-indigo-500 transition-colors font-semibold"
                    required
                  />
                </div>

                <div className="space-y-1">
                  <span className="block text-[10px] font-bold text-slate-500 uppercase tracking-wider">URL do Áudio / Arquivo</span>
                  <input
                    type="url"
                    placeholder="Link direto para áudio (.mp3, etc.)"
                    value={audioUrl}
                    onChange={(e) => setAudioUrl(e.target.value)}
                    className="w-full rounded bg-slate-950 border border-slate-850 px-2.5 py-1.5 text-xs text-slate-200 outline-none focus:border-indigo-500 transition-colors font-medium"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <span className="block text-[10px] font-bold text-slate-500 uppercase tracking-wider">Tipo</span>
                    <select
                      value={audioType}
                      onChange={(e) => setAudioType(e.target.value)}
                      className="w-full rounded bg-slate-950 border border-slate-850 px-2 py-1 text-xs text-slate-355 outline-none focus:border-indigo-500 font-semibold"
                    >
                      <option value="background_music">Música Fundo</option>
                      <option value="sound_effect">Efeito Sonoro</option>
                      <option value="voiceover">Locução</option>
                      <option value="other">Outro</option>
                    </select>
                  </div>

                  <div className="space-y-1">
                    <span className="block text-[10px] font-bold text-slate-500 uppercase tracking-wider">Vibe / Mood</span>
                    <input
                      type="text"
                      placeholder="Ex: Tenso"
                      value={audioMood}
                      onChange={(e) => setAudioMood(e.target.value)}
                      className="w-full rounded bg-slate-950 border border-slate-850 px-2 py-1 text-xs text-slate-200 outline-none focus:border-indigo-500 transition-colors font-medium"
                    />
                  </div>
                </div>

                <div className="space-y-1">
                  <span className="block text-[10px] font-bold text-slate-500 uppercase tracking-wider">Licença / Autor</span>
                  <input
                    type="text"
                    placeholder="Ex: Royalty Free (Envato)"
                    value={audioLicense}
                    onChange={(e) => setAudioLicense(e.target.value)}
                    className="w-full rounded bg-slate-950 border border-slate-850 px-2.5 py-1.5 text-xs text-slate-200 outline-none focus:border-indigo-500 transition-colors font-medium"
                  />
                </div>

                <div className="space-y-1">
                  <span className="block text-[10px] font-bold text-slate-500 uppercase tracking-wider">Instruções de Uso</span>
                  <textarea
                    placeholder="Ex: Tocar baixo a partir de 01:20..."
                    value={audioUsage}
                    onChange={(e) => setAudioUsage(e.target.value)}
                    rows={2.5}
                    className="w-full rounded bg-slate-950 border border-slate-850 px-2.5 py-1.5 text-xs text-slate-200 outline-none focus:border-indigo-500 transition-colors font-medium resize-none"
                  />
                </div>

                <button
                  type="submit"
                  disabled={!audioTitle.trim()}
                  className="w-full flex items-center justify-center gap-1.5 rounded-lg bg-indigo-600 px-4 py-2 text-xs font-bold text-white hover:bg-indigo-500 transition-all select-none disabled:opacity-40"
                >
                  <Music className="h-4 w-4" />
                  <span>Vincular Áudio</span>
                </button>
              </form>
            </div>

            {/* Audio cards list grid */}
            <div className="lg:col-span-3 space-y-4">
              {audios.length === 0 ? (
                <div className="text-center text-xs text-slate-500 py-16 border border-dashed border-slate-800 rounded-xl bg-slate-950/10">
                  Nenhuma ideia musical vinculada a este projeto de vídeo. Escreva uma no painel ao lado!
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {audios.map((audio) => (
                    <div
                      key={audio.id}
                      className="rounded-xl border border-slate-800 bg-[#0b101c]/15 p-4 flex flex-col justify-between backdrop-blur-sm group"
                    >
                      <div>
                        {/* Audio Card Header */}
                        <div className="flex items-center justify-between gap-2 mb-2 select-none">
                          <span className="text-[9px] font-bold uppercase tracking-wider text-amber-400 bg-amber-500/5 px-2 py-0.5 rounded border border-amber-500/10">
                            {audio.audio_type === "background_music" ? "Música de Fundo" : audio.audio_type === "sound_effect" ? "SFX / Efeito" : "Voz / Locução"}
                          </span>
                          
                          <button
                            onClick={() => handleDeleteAudio(audio.id)}
                            className="p-1 rounded hover:bg-rose-950/20 text-slate-600 hover:text-rose-400 opacity-0 group-hover:opacity-100 transition-opacity"
                            title="Deletar áudio"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>

                        {/* Title */}
                        <h5 className="text-sm font-bold text-slate-200 flex items-center gap-2 mb-1.5">
                          <Disc className="h-4 w-4 text-indigo-400 shrink-0" />
                          {audio.audio_title}
                        </h5>

                        {/* Mood / License */}
                        <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-[10px] text-slate-500 font-semibold mb-3">
                          {audio.mood && <span>Mood: <strong className="text-slate-400">{audio.mood}</strong></span>}
                          {audio.license_notes && <span>Licença: <strong className="text-slate-400">{audio.license_notes}</strong></span>}
                        </div>

                        {/* Usage notes */}
                        {audio.usage_notes && (
                          <p className="text-xs text-slate-400 leading-relaxed italic bg-slate-950/40 p-2.5 rounded border border-slate-850/40 mb-3">
                            {audio.usage_notes}
                          </p>
                        )}
                      </div>

                      {/* HTML Audio Player if URL is set */}
                      {audio.audio_url ? (
                        <div className="mt-2 bg-slate-950 p-2 rounded-lg border border-slate-850">
                          <audio
                            src={audio.audio_url}
                            controls
                            className="w-full h-8 outline-none"
                          />
                        </div>
                      ) : (
                        <div className="text-[10px] text-slate-600 font-medium italic mt-2">
                          Nenhum player de áudio disponível (URL ausente).
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
