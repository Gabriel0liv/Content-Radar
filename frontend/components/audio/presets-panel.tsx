"use client";

import { useEffect, useState } from "react";
import { Loader2, Plus, Save, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { speechApi } from "@/lib/speech-api";
import type { SpeechOperation, SpeechPreset } from "@/lib/speech-types";

export function PresetsPanel() {
  const [operation, setOperation] = useState<SpeechOperation>("stt");
  const [presets, setPresets] = useState<SpeechPreset[]>([]);
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [config, setConfig] = useState(operation === "stt" ? '{"model":"medium"}' : '{"engine":"kokoro","voice":"pt_br_dora"}');

  const load = async () => {
    setLoading(true);
    try { setPresets(await speechApi.listPresets(operation)); }
    catch (e: any) { toast.error("Falha ao carregar presets", { description: e.message }); }
    finally { setLoading(false); }
  };

  useEffect(() => {
    setConfig(operation === "stt" ? '{"model":"medium"}' : '{"engine":"kokoro","voice":"pt_br_dora"}');
    void load();
  }, [operation]);

  const create = async () => {
    if (!name.trim()) return;
    try {
      const parsed = JSON.parse(config);
      await speechApi.createPreset({ name: name.trim(), operation, config: parsed, description: description.trim() || undefined });
      setName(""); setDescription(""); await load(); toast.success("Preset criado");
    } catch (e: any) { toast.error("Não foi possível criar", { description: e.message }); }
  };

  const remove = async (preset: SpeechPreset) => {
    if (preset.is_builtin || typeof preset.id !== "number") return;
    if (!window.confirm(`Excluir o preset “${preset.name}”?`)) return;
    try { await speechApi.deletePreset(preset.id); await load(); }
    catch (e: any) { toast.error("Não foi possível excluir", { description: e.message }); }
  };

  return (
    <div className="space-y-5">
      <div className="flex gap-2">
        {(["stt", "tts"] as SpeechOperation[]).map((item) => <button key={item} onClick={() => setOperation(item)} className={`rounded-lg px-4 py-2 text-sm font-medium ${operation === item ? "bg-indigo-600 text-white" : "border border-slate-800 text-slate-400"}`}>{item.toUpperCase()}</button>)}
      </div>
      <div className="rounded-xl border border-slate-800 bg-[#0b101c]/55 p-5">
        <div className="grid gap-3 lg:grid-cols-[1fr_1fr_2fr_auto]">
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Nome do preset" className="rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white" />
          <input value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Descrição opcional" className="rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white" />
          <input value={config} onChange={(e) => setConfig(e.target.value)} className="font-mono rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-xs text-slate-300" />
          <button onClick={create} className="flex items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white"><Plus className="h-4 w-4" /> Criar</button>
        </div>
      </div>
      {loading ? <div className="flex h-32 items-center justify-center"><Loader2 className="h-5 w-5 animate-spin text-indigo-400" /></div> : (
        <div className="grid gap-3 lg:grid-cols-2">
          {presets.map((preset) => <div key={`${preset.id}-${preset.name}`} className="rounded-xl border border-slate-800 bg-[#0b101c]/55 p-4"><div className="flex items-start gap-3"><div className="min-w-0 flex-1"><div className="flex items-center gap-2"><h4 className="font-semibold text-white">{preset.name}</h4>{preset.is_builtin && <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-slate-400">built-in</span>}</div><p className="mt-1 text-xs text-slate-500">{preset.description || "Sem descrição"}</p><pre className="mt-3 overflow-auto rounded-lg bg-slate-950 p-2.5 text-[11px] text-slate-500">{JSON.stringify(preset.config_json || preset.config || {}, null, 2)}</pre></div>{!preset.is_builtin && typeof preset.id === "number" && <button onClick={() => remove(preset)} className="p-2 text-slate-600 hover:text-rose-400"><Trash2 className="h-4 w-4" /></button>}</div></div>)}
        </div>
      )}
    </div>
  );
}
