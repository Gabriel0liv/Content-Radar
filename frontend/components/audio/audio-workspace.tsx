"use client";

import { useMemo, useState } from "react";
import { Activity, Clock3, Mic2, SlidersHorizontal, Stethoscope, Volume2, Waves, LibraryBig } from "lucide-react";
import { AudioOverview } from "@/components/audio/audio-overview";
import { TranscriptionPanel } from "@/components/audio/transcription-panel";
import { TtsPanel } from "@/components/audio/tts-panel";
import { HistoryPanel } from "@/components/audio/history-panel";
import { PresetsPanel } from "@/components/audio/presets-panel";
import { VoicesModelsPanel } from "@/components/audio/voices-models-panel";
import { DiagnosticsPanel } from "@/components/audio/diagnostics-panel";
import { SettingsPanel } from "@/components/audio/settings-panel";

type Section = "overview" | "stt" | "tts" | "history" | "presets" | "voices" | "diagnostics" | "settings";

const sections = [
  { id: "overview" as const, label: "Visão geral", icon: Activity },
  { id: "stt" as const, label: "Transcrever", icon: Mic2 },
  { id: "tts" as const, label: "Gerar voz", icon: Volume2 },
  { id: "history" as const, label: "Histórico", icon: Clock3 },
  { id: "presets" as const, label: "Presets", icon: SlidersHorizontal },
  { id: "voices" as const, label: "Vozes e modelos", icon: LibraryBig },
  { id: "diagnostics" as const, label: "Diagnóstico", icon: Stethoscope },
  { id: "settings" as const, label: "Configurações", icon: Waves },
];

export function AudioWorkspace() {
  const [section, setSection] = useState<Section>("overview");
  const title = useMemo(() => sections.find((item) => item.id === section)?.label || "Áudio", [section]);

  return (
    <div className="space-y-6">
      <div className="border-b border-slate-800 pb-5">
        <h2 className="text-3xl font-bold tracking-tight text-white">Áudio</h2>
        <p className="mt-1 text-sm text-slate-400">Transcrição, síntese de voz, histórico, vozes, diagnósticos e configurações no Speech Suite nativo.</p>
      </div>

      <div className="grid gap-6 xl:grid-cols-[220px_minmax(0,1fr)]">
        <aside className="h-fit rounded-xl border border-slate-800 bg-[#0b101c]/55 p-2">
          <nav className="space-y-1">
            {sections.map(({ id, label, icon: Icon }) => (
              <button key={id} onClick={() => setSection(id)} className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm transition ${section === id ? "bg-slate-800 text-white" : "text-slate-400 hover:bg-slate-900 hover:text-slate-200"}`}>
                <Icon className={`h-4 w-4 ${section === id ? "text-indigo-400" : "text-slate-600"}`} />
                {label}
              </button>
            ))}
          </nav>
        </aside>

        <section className="min-w-0">
          <div className="mb-4"><h3 className="text-xl font-semibold text-white">{title}</h3></div>
          {section === "overview" && <AudioOverview />}
          {section === "stt" && <TranscriptionPanel />}
          {section === "tts" && <TtsPanel />}
          {section === "history" && <HistoryPanel />}
          {section === "presets" && <PresetsPanel />}
          {section === "voices" && <VoicesModelsPanel />}
          {section === "diagnostics" && <DiagnosticsPanel />}
          {section === "settings" && <SettingsPanel />}
        </section>
      </div>
    </div>
  );
}
