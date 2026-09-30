"use client";

import { useEffect, useState } from "react";
import { Loader2, Save } from "lucide-react";
import { toast } from "sonner";
import { speechApi } from "@/lib/speech-api";
import type { SpeechSettings } from "@/lib/speech-types";

export function SettingsPanel() {
  const [settings, setSettings] = useState<SpeechSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    speechApi.getSettings().then(setSettings).catch((e) => toast.error("Falha ao carregar configurações", { description: e.message })).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="flex h-48 items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-indigo-400" /></div>;
  if (!settings) return null;

  const save = async () => {
    setSaving(true);
    try {
      const { hf_token_configured: _secretState, ...changes } = settings;
      setSettings(await speechApi.updateSettings(changes));
      toast.success("Configurações salvas");
    } catch (e: any) {
      toast.error("Não foi possível salvar", { description: e.message });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-5">
      <div className="rounded-xl border border-slate-800 bg-[#0b101c]/55 p-5">
        <h3 className="font-semibold text-white">Padrões</h3>
        <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <label className="text-xs text-slate-400">Preset STT<select value={settings.default_stt_preset} onChange={(e) => setSettings({ ...settings, default_stt_preset: e.target.value })} className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white"><option value="fast">Rápido</option><option value="balanced">Balanceado</option><option value="maximum_quality">Máxima qualidade</option></select></label>
          <label className="text-xs text-slate-400">Idioma<input value={settings.default_language || ""} onChange={(e) => setSettings({ ...settings, default_language: e.target.value || null })} placeholder="pt" className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white" /></label>
          <label className="text-xs text-slate-400">Hardware<select value={settings.hardware_policy} onChange={(e) => setSettings({ ...settings, hardware_policy: e.target.value as any })} className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white"><option value="auto">Auto</option><option value="cpu">CPU</option><option value="cuda">CUDA</option></select></label>
          <label className="text-xs text-slate-400">Motor TTS<select value={settings.default_tts_engine} onChange={(e) => setSettings({ ...settings, default_tts_engine: e.target.value as any })} className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white"><option value="kokoro">Kokoro</option><option value="piper">Piper</option></select></label>
          <label className="text-xs text-slate-400">Voz padrão<input value={settings.default_voice || ""} onChange={(e) => setSettings({ ...settings, default_voice: e.target.value || null })} placeholder="pt_br_dora" className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white" /></label>
          <label className="text-xs text-slate-400">Formato TTS<select value={settings.default_output_format} onChange={(e) => setSettings({ ...settings, default_output_format: e.target.value as any })} className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white"><option value="wav">WAV</option><option value="mp3">MP3</option></select></label>
        </div>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <label className="flex items-center gap-2 text-sm text-slate-300"><input type="checkbox" checked={settings.default_diarization} onChange={(e) => setSettings({ ...settings, default_diarization: e.target.checked })} /> Diarização por padrão</label>
          <label className="flex items-center gap-2 text-sm text-slate-300"><input type="checkbox" checked={settings.default_ptbr_normalization} onChange={(e) => setSettings({ ...settings, default_ptbr_normalization: e.target.checked })} /> Normalização PT-BR por padrão</label>
          <label className="flex items-center gap-2 text-sm text-slate-300"><input type="checkbox" checked={settings.offline_mode} onChange={(e) => setSettings({ ...settings, offline_mode: e.target.checked })} /> Modo offline</label>
          <label className="flex items-center gap-2 text-sm text-slate-300"><input type="checkbox" checked={settings.retain_debug_artifacts} onChange={(e) => setSettings({ ...settings, retain_debug_artifacts: e.target.checked })} /> Manter artefatos de debug</label>
        </div>
      </div>

      <div className="rounded-xl border border-slate-800 bg-[#0b101c]/55 p-5">
        <h3 className="font-semibold text-white">Retenção e acesso</h3>
        <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <label className="text-xs text-slate-400">Artefatos (dias)<input type="number" min={0} max={3650} value={settings.artifact_retention_days} onChange={(e) => setSettings({ ...settings, artifact_retention_days: Number(e.target.value) })} className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white" /></label>
          <label className="text-xs text-slate-400">Inputs (dias)<input type="number" min={0} max={3650} value={settings.input_retention_days} onChange={(e) => setSettings({ ...settings, input_retention_days: Number(e.target.value) })} className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-white" /></label>
          <div className="rounded-lg border border-slate-800 bg-slate-950 px-3 py-2"><div className="text-xs text-slate-500">Hugging Face token</div><div className={`mt-1 text-sm font-medium ${settings.hf_token_configured ? "text-emerald-300" : "text-amber-300"}`}>{settings.hf_token_configured ? "Configurado" : "Não configurado"}</div><div className="mt-1 text-[10px] text-slate-600">O valor secreto nunca é exibido pela API.</div></div>
        </div>
      </div>

      <div className="flex justify-end"><button onClick={save} disabled={saving} className="flex items-center gap-2 rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-40">{saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />} Salvar configurações</button></div>
    </div>
  );
}
