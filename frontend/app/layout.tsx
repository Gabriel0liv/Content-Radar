import type { Metadata } from "next";
import { AppShell } from "@/components/layout/app-shell";
import { Toaster } from "sonner";
import "./globals.css";

export const metadata: Metadata = {
  title: "Content Radar",
  description: "Encontre conteúdos, guarde referências e transcrições e organize ideias de vídeo.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="pt-BR" className="dark">
      <body className="font-sans">
        <AppShell>{children}</AppShell>
        <Toaster theme="dark" position="bottom-right" closeButton richColors />
      </body>
    </html>
  );
}
