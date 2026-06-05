import { ContentSummary } from "@/lib/types";
import { formatViews } from "@/lib/format";
import { Database, Sparkles, TrendingUp, Eye } from "lucide-react";

export function ContentSummaryCards({ summary }: { summary: ContentSummary | null }) {
  const stats = summary || {
    total_items: 0,
    new_items: 0,
    max_score: 0,
    max_views: 0,
  };

  const cards = [
    {
      name: "Total de Itens",
      value: stats.total_items.toLocaleString("pt-BR"),
      desc: "Conteúdos coletados no banco",
      icon: Database,
      color: "text-indigo-400 bg-indigo-500/10 border-indigo-500/20",
    },
    {
      name: "Novos Sinais",
      value: stats.new_items.toLocaleString("pt-BR"),
      desc: "Aguardando triagem de curadoria",
      icon: Sparkles,
      color: "text-blue-400 bg-blue-500/10 border-blue-500/20",
    },
    {
      name: "Score Máximo",
      value: stats.max_score.toFixed(1),
      desc: "Maior pontuação de oportunidade",
      icon: TrendingUp,
      color: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
    },
    {
      name: "Views Máximas",
      value: formatViews(stats.max_views),
      desc: "Maior tráfego viral detectado",
      icon: Eye,
      color: "text-amber-400 bg-amber-500/10 border-amber-500/20",
    },
  ];

  return (
    <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
      {cards.map((card) => {
        const Icon = card.icon;
        return (
          <div
            key={card.name}
            className="rounded-xl border border-slate-800/80 bg-[#0b101c]/40 p-6 backdrop-blur-sm transition-all hover:border-slate-700/80 hover:bg-[#0c1222]/60"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                {card.name}
              </span>
              <div className={`flex h-8 w-8 items-center justify-center rounded-lg border ${card.color}`}>
                <Icon className="h-4.5 w-4.5" />
              </div>
            </div>
            <div className="mt-3.5 flex items-baseline gap-2">
              <span className="text-3xl font-bold tracking-tight text-white">{card.value}</span>
            </div>
            <p className="mt-1 text-xs text-slate-400 font-medium">{card.desc}</p>
          </div>
        );
      })}
    </div>
  );
}
