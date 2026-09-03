"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Library, Lightbulb, Radar, Search } from "lucide-react";
import { cn } from "@/lib/utils";

const menuItems = [
  { name: "Radar", href: "/content", icon: Radar },
  { name: "Pesquisas", href: "/search-configs", icon: Search },
  { name: "Biblioteca", href: "/references", icon: Library },
  { name: "Ideias", href: "/ideas", icon: Lightbulb },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed inset-y-0 left-0 z-20 flex h-full w-64 flex-col border-r border-slate-800 bg-[#090d16] text-slate-200">
      <div className="flex h-16 items-center gap-2 border-b border-slate-800 bg-[#0b101c] px-6">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-white shadow-md shadow-indigo-600/20">
          <Radar className="h-5 w-5" />
        </div>
        <div>
          <h1 className="text-base font-semibold tracking-tight text-white">Content Radar</h1>
          <p className="text-[10px] font-mono uppercase tracking-wider text-indigo-400">Pesquisa de conteúdo</p>
        </div>
      </div>

      <nav className="flex-1 space-y-1.5 px-4 py-6">
        {menuItems.map((item) => {
          const isActive = pathname.startsWith(item.href);
          const Icon = item.icon;
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                "group flex items-center rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-150",
                isActive ? "bg-slate-800/80 text-white shadow-sm" : "text-slate-400 hover:bg-slate-800/30 hover:text-slate-200",
              )}
            >
              <Icon className={cn("mr-3 h-4 w-4", isActive ? "text-indigo-400" : "text-slate-500 group-hover:text-slate-300")} />
              <span>{item.name}</span>
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-slate-800 bg-[#070b12] p-4 text-xs text-slate-500">
        Encontrar → salvar → transcrever → anotar
      </div>
    </aside>
  );
}
