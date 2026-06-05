import { ContentStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

const statusConfig: Record<
  ContentStatus,
  { label: string; className: string }
> = {
  new: {
    label: "Novo",
    className: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  },
  reviewed: {
    label: "Revisado",
    className: "bg-violet-500/10 text-violet-400 border-violet-500/20",
  },
  selected: {
    label: "Selecionado",
    className: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  },
  rejected: {
    label: "Rejeitado",
    className: "bg-rose-500/10 text-rose-400 border-rose-500/20",
  },
  produced: {
    label: "Produzido",
    className: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  },
  archived: {
    label: "Arquivado",
    className: "bg-slate-500/10 text-slate-400 border-slate-500/20",
  },
};

export function ContentStatusBadge({
  status,
  className,
}: {
  status: ContentStatus;
  className?: string;
}) {
  const config = statusConfig[status] || {
    label: status,
    className: "bg-slate-500/10 text-slate-400 border-slate-500/20",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold tracking-wide shadow-sm select-none",
        config.className,
        className
      )}
    >
      {config.label}
    </span>
  );
}
