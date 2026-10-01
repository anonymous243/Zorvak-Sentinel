"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { login } from "@/lib/api";
import Link from "next/link";
import Image from "next/image";
import { AlertTriangle, Eye } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      await login({ email, password });
      router.push("/"); // Redirect to dashboard
      router.refresh();
    } catch (err: any) {
      setError(err.message || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex bg-[#050505]">
      
      {/* BRAND PANEL - LEFT SIDE */}
      <div className="hidden lg:flex w-[60%] relative bg-[#050505] flex-col justify-center items-center overflow-hidden border-r border-zinc-900/50">
        
        {/* Background Effects (Planet + Stars) */}
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_bottom,_var(--tw-gradient-stops))] from-blue-900/10 via-[#050505] to-[#050505]" />
        
        {/* Simulated Planet Curve */}
        <div className="absolute -bottom-[40%] left-1/2 -translate-x-1/2 w-[150%] aspect-square rounded-full border-t border-blue-500/20 bg-gradient-to-t from-blue-900/10 to-transparent blur-[2px] opacity-60" />
        <div className="absolute -bottom-[40%] left-1/2 -translate-x-1/2 w-[150%] aspect-square rounded-full shadow-[0_-50px_100px_rgba(37,99,235,0.15)]" />

        {/* Branding Content */}
        <div className="relative z-20 flex flex-col items-center">
          {/* Guardian Logo */}
          <div className="relative w-72 h-72 mb-6">
            <div className="absolute inset-0 bg-blue-500/10 blur-[60px] rounded-full mix-blend-screen" />
            <Image 
              src="/hero.png" 
              alt="ZORVAK SENTINEL Guardian"
              fill
              className="object-contain drop-shadow-[0_0_40px_rgba(37,99,235,0.2)]"
              priority
            />
          </div>

          <div className="flex flex-col items-center text-center">
            <span className="font-outfit font-bold text-white tracking-[0.3em] text-sm">ZORVAK</span>
            <span className="font-outfit font-bold text-white tracking-[0.4em] text-2xl uppercase mt-1">SENTINEL</span>
            <span className="text-[10px] text-zinc-500 font-bold tracking-[0.2em] uppercase mt-2">SECURITY FOR AI AGENTS</span>
          </div>

          <p className="text-zinc-400 text-sm mt-8 tracking-wide">
            Build a safer future<br/>for autonomous systems.
          </p>
        </div>
      </div>

      {/* AUTH FORM - RIGHT SIDE */}
      <div className="w-full lg:w-[40%] flex flex-col justify-center items-center p-6 sm:p-12 relative">
        <div className="absolute inset-0 bg-[url('/grid.svg')] bg-center opacity-5" />
        
        <div className="w-full max-w-[420px] bg-[#0a0a0a]/80 backdrop-blur-xl border border-zinc-800/80 rounded-2xl p-8 relative z-10 shadow-2xl">
          <div className="mb-8 text-center sm:text-left">
            <h2 className="text-[10px] font-bold text-zinc-500 tracking-widest uppercase mb-2">WELCOME BACK</h2>
            <h1 className="font-outfit text-2xl font-bold text-white">Sign in to ZORVAK SENTINEL</h1>
            <p className="text-zinc-400 text-sm mt-2">Access your security control plane.</p>
          </div>
          
          {error && (
            <div className="bg-red-950/30 border border-red-900/50 rounded-lg p-3 mb-6 flex items-start">
              <AlertTriangle className="h-4 w-4 text-red-500 mt-0.5 mr-3 shrink-0" />
              <p className="text-sm text-red-400">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-xs font-medium text-zinc-400 mb-2">
                Work Email
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full bg-[#050505] border border-zinc-800 rounded-lg px-4 py-2.5 text-white text-sm focus:ring-1 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all placeholder:text-zinc-600"
                placeholder="admin@example.com"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-zinc-400 mb-2">
                Password
              </label>
              <div className="relative">
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-[#050505] border border-zinc-800 rounded-lg px-4 py-2.5 text-white text-sm focus:ring-1 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all placeholder:text-zinc-600"
                  placeholder="Enter your password"
                />
                <button type="button" className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-400">
                  <Eye className="w-4 h-4" />
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-[#3b82f6] hover:bg-blue-500 text-white font-medium rounded-lg px-4 py-2.5 transition-colors disabled:opacity-50 disabled:cursor-not-allowed mt-2 text-sm shadow-[0_0_15px_rgba(59,130,246,0.3)]"
            >
              {loading ? "Signing in..." : "Sign in"}
            </button>
          </form>

          <div className="mt-6 text-center text-xs text-zinc-500">
            Don't have an account?{" "}
            <Link href="/signup" className="text-blue-400 hover:text-blue-300 font-medium transition-colors">
              Sign up
            </Link>
          </div>
        </div>
      </div>

    </div>
  );
}
