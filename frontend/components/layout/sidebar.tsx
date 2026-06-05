"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Radar, ListChecks, FileText, Video, Settings, Play } from "lucide-react";
import { cn } from "@/lib/utils";

const menuItems = [
  {
    name: "Conteúdos",
    href: "/content",
    icon: ListChecks,
    active: true,
  },
  {
    name: "Roteiros",
    href: "#",
    icon: FileText,
    active: false,
    badge: "Futuro",
  },
  {
    name: "Produção",
    href: "#",
    icon: Video,
    active: false,
    badge: "Futuro",
  },
  {
    name: "Configurações",
    href: "#",
    icon: Settings,
    active: false,
  },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed inset-y-0 left-0 z-20 flex h-full w-64 flex-col border-r border-slate-800 bg-[#090d16] text-slate-200">
      {/* Brand logo */}
      <div className="flex h-16 items-center border-b border-slate-800 px-6 gap-2 bg-[#0b101c]">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-white shadow-md shadow-indigo-600/20">
          <Radar className="h-5 w-5 animate-pulse" />
        </div>
        <div>
          <h1 className="text-base font-semibold tracking-tight text-white">Content Radar</h1>
          <p className="text-[10px] text-indigo-400 font-mono tracking-wider uppercase">Editorial AI</p>
        </div>
      </div>

      {/* Menu Navigation */}
      <nav className="flex-1 space-y-1.5 px-4 py-6">
        {menuItems.map((item) => {
          const isActive = pathname.startsWith(item.href) && item.active;
          const Icon = item.icon;

          return (
            <div key={item.name} className="relative">
              {item.active ? (
                <Link
                  href={item.href}
                  className={cn(
                    "group flex items-center rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-150 ease-in-out",
                    isActive
                      ? "bg-slate-800/80 text-white shadow-sm"
                      : "text-slate-400 hover:bg-slate-800/30 hover:text-slate-200"
                  )}
                >
                  <Icon
                    className={cn(
                      "mr-3 h-4 w-4 transition-colors",
                      isActive ? "text-indigo-400" : "text-slate-500 group-hover:text-slate-300"
                    )}
                  />
                  <span>{item.name}</span>
                </Link>
              ) : (
                <div
                  className="flex items-center rounded-lg px-3 py-2.5 text-sm font-medium text-slate-600 cursor-not-allowed select-none"
                  title="Funcionalidade planejada para a próxima etapa"
                >
                  <Icon className="mr-3 h-4 w-4 text-slate-700" />
                  <span>{item.name}</span>
                  {item.badge && (
                    <span className="ml-auto rounded-full bg-slate-900 px-1.5 py-0.5 text-[9px] font-semibold text-slate-500 border border-slate-800">
                      {item.badge}
                    </span>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </nav>

      {/* Footer Info */}
      <div className="border-t border-slate-800 p-4 bg-[#070b12] text-xs text-slate-500">
        <div className="flex items-center justify-between">
          <span>Versão MVP v1.0.0</span>
          <span className="flex h-2 w-2 rounded-full bg-emerald-500 shadow-sm shadow-emerald-500/50"></span>
        </div>
      </div>
    </aside>
  );
}
