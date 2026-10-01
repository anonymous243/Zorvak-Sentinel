import type { Metadata } from "next";
import { Inter, Outfit } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const outfit = Outfit({ subsets: ["latin"], variable: "--font-outfit" });

export const metadata: Metadata = {
  title: "ZORVAK SENTINEL — Security for Autonomous AI Agents",
  description: "ZORVAK SENTINEL provides identity, authorization, risk, runtime enforcement, monitoring, and response controls for autonomous AI agents.",
  icons: {
    icon: "/hero.png",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark scroll-smooth">
      <body className={`${inter.variable} ${outfit.variable} font-sans antialiased bg-zinc-950 text-zinc-100 min-h-screen overflow-x-hidden selection:bg-indigo-500/30`}>
        {children}
      </body>
    </html>
  );
}
