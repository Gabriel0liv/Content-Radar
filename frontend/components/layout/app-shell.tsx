import { Sidebar } from "./sidebar";
import { Topbar } from "./topbar";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-[#060913] text-slate-100 antialiased font-sans">
      <Sidebar />
      <div className="pl-64">
        <Topbar />
        <main className="min-h-[calc(100vh-4rem)] pt-16">
          <div className="px-8 py-8">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
