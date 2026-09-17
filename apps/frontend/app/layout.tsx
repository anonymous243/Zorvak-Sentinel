import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "ZORVAK SENTINEL — AI Security Control Plane",
  description: "Enterprise security control plane for autonomous AI agents. Verify identity, enforce policies, evaluate risk, monitor behavior.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.variable} font-sans antialiased bg-zinc-950 text-zinc-100 min-h-screen`}>
        {children}
      </body>
    </html>
  );
}
