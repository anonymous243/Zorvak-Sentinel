import Image from "next/image";
import Link from "next/link";
import {
  ShieldCheck, ArrowRight, Lock, Activity, Server, FileText,
  Terminal, Shield, Layers, Database, Code, Key, ChevronRight, Zap,
  Code2, Briefcase, MessageSquare, Video, Check
} from "lucide-react";
import { ProblemSection } from "@/components/landing/ProblemSection";
import { SentinelAnswerSection } from "@/components/landing/SentinelAnswerSection";
export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[#050505] text-zinc-300 font-sans selection:bg-indigo-500/30 overflow-hidden">

      {/* Background Ambient Lighting */}
      <div className="fixed inset-0 z-0 pointer-events-none">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-[1200px] h-[600px] bg-indigo-900/10 blur-[120px] rounded-full opacity-50" />
      </div>

      {/* NAVBAR */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-[#050505]/80 backdrop-blur-md border-b border-zinc-800/50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3">
            <div className="w-8 h-8 rounded relative overflow-hidden bg-zinc-950 flex items-center justify-center">
              <Image src="/hero.png" alt="Logo" width={32} height={32} className="object-contain scale-[2] translate-y-[2px]" />
            </div>
            <span className="font-outfit font-bold text-white tracking-widest text-sm">ZORVAK SENTINEL</span>
          </Link>

          <div className="hidden md:flex items-center gap-8 text-sm font-medium text-zinc-400">
            <Link href="#platform" className="hover:text-white transition-colors">Platform</Link>
            <Link href="#security" className="hover:text-white transition-colors">Security</Link>
            <Link href="#developers" className="hover:text-white transition-colors">Developers</Link>
            <Link href="#documentation" className="hover:text-white transition-colors">Documentation</Link>
            <Link href="/pricing" className="hover:text-white transition-colors">Pricing</Link>
          </div>

          <div className="flex items-center gap-4">
            <Link href="/login" className="text-sm font-medium text-zinc-300 hover:text-white transition-colors hidden sm:block">
              Sign In
            </Link>
            <Link href="/signup" className="bg-white text-black px-4 py-2 rounded text-sm font-semibold hover:bg-zinc-200 transition-colors">
              Get Started
            </Link>
          </div>
        </div>
      </nav>

      <main className="relative z-10 pt-16 pb-20">

        {/* HERO SECTION - CENTERED WITH BACKGROUND IMAGE */}
        <section className="relative pt-32 pb-32 border-b border-zinc-900 overflow-hidden flex flex-col items-center justify-center min-h-[85vh]">
          {/* Background Image & Gradient Overlays */}
          <div className="absolute inset-0 bg-[#050505] z-0" />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] lg:w-[1200px] lg:h-[1200px] bg-[url('/hero.png')] bg-center bg-no-repeat bg-contain opacity-[0.15] z-0 mix-blend-screen" />
          <div className="absolute inset-0 bg-gradient-to-t from-[#050505] via-transparent to-[#050505] z-0 pointer-events-none" />
          <div className="absolute inset-0 bg-gradient-to-r from-[#050505] via-transparent to-[#050505] z-0 pointer-events-none" />

          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-4xl h-[500px] bg-blue-500/10 blur-[120px] rounded-full z-0 pointer-events-none" />

          <div className="relative z-20 max-w-[1000px] mx-auto px-6 w-full flex flex-col items-center text-center space-y-8 mt-12">



            <h1 className="font-outfit text-5xl lg:text-7xl font-bold text-white leading-[1.05] tracking-tight uppercase max-w-4xl drop-shadow-2xl">
              SECURITY SCALED <br /> TO YOUR <span className="text-blue-500">AUTONOMOUS</span> <br /> AGENTS.
            </h1>

            <p className="text-base text-zinc-400 max-w-xl leading-relaxed">
              Start free. Upgrade as your fleet of AI agents expands and takes on more critical operations.
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-6 w-full">
              <Link href="/signup" className="w-full sm:w-auto flex items-center justify-center gap-2 bg-[#2563eb] hover:bg-blue-600 text-white px-8 py-4 rounded font-bold transition-all shadow-[0_0_20px_rgba(37,99,235,0.4)] tracking-wider">
                GET STARTED <ChevronRight className="w-4 h-4" />
              </Link>
              <Link href="/pricing" className="w-full sm:w-auto flex items-center justify-center gap-2 bg-zinc-900/50 hover:bg-zinc-800 border border-zinc-700 text-white px-8 py-4 rounded font-bold transition-all tracking-wider backdrop-blur-sm">
                VIEW PRICING
              </Link>
            </div>
          </div>

          {/* Bottom Feature Bar */}
          <div className="relative z-20 max-w-4xl mx-auto px-6 mt-20 flex flex-wrap items-center justify-center gap-4 sm:gap-8 text-[11px] font-medium text-zinc-400 tracking-wider">
            <div className="flex items-center gap-2"><Shield className="w-3 h-3" /> Identity</div>
            <div className="hidden sm:block w-[1px] h-3 bg-zinc-800" />
            <div className="flex items-center gap-2"><Layers className="w-3 h-3" /> Control</div>
            <div className="hidden sm:block w-[1px] h-3 bg-zinc-800" />
            <div className="flex items-center gap-2"><Activity className="w-3 h-3" /> Monitor</div>
            <div className="hidden sm:block w-[1px] h-3 bg-zinc-800" />
            <div className="flex items-center gap-2"><Lock className="w-3 h-3" /> Protect</div>
          </div>
        </section>
        <ProblemSection />
        <SentinelAnswerSection />

        {/* FEATURE GRID */}
        <section id="security" className="max-w-7xl mx-auto px-6 py-24 border-t border-zinc-900">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">

            {/* Identity */}
            <div className="bg-zinc-900/20 border border-zinc-800/50 rounded-2xl p-8 hover:bg-zinc-900/40 transition-colors">
              <Key className="w-8 h-8 text-indigo-400 mb-6" />
              <h3 className="font-outfit text-2xl font-bold text-white mb-4 uppercase">Know Which Agent Is Acting.</h3>
              <p className="text-zinc-400 text-sm leading-relaxed mb-6">
                SENTINEL establishes machine identity and verifies signed requests before security decisions are made using agent credentials, Ed25519 request signing, and strict tenant binding.
              </p>
              <Link href="/docs" className="text-xs font-bold tracking-wider text-indigo-400 hover:text-indigo-300 uppercase flex items-center gap-1">
                Explore Agent Identity <ChevronRight className="w-3 h-3" />
              </Link>
            </div>

            {/* Capability */}
            <div className="bg-zinc-900/20 border border-zinc-800/50 rounded-2xl p-8 hover:bg-zinc-900/40 transition-colors">
              <Layers className="w-8 h-8 text-indigo-400 mb-6" />
              <h3 className="font-outfit text-2xl font-bold text-white mb-4 uppercase">Control What An Agent Can Touch.</h3>
              <p className="text-zinc-400 text-sm leading-relaxed mb-6">
                Capabilities constrain what an agent can use. Restrict a support agent to `CRM.read` and `Email.send` while explicitly denying access to `Customer.delete` or `Payment.refund`.
              </p>
            </div>

            {/* Policy Engine */}
            <div className="bg-zinc-900/20 border border-zinc-800/50 rounded-2xl p-8 hover:bg-zinc-900/40 transition-colors md:col-span-2 flex flex-col lg:flex-row gap-8 items-center">
              <div className="flex-1">
                <ShieldCheck className="w-8 h-8 text-indigo-400 mb-6" />
                <h3 className="font-outfit text-2xl font-bold text-white mb-4 uppercase">Policies That Actually Enforce.</h3>
                <p className="text-zinc-400 text-sm leading-relaxed">
                  Deterministic authorization policies map specific agents to specific actions and resources. Unambiguous ALLOW or DENY decisions driven by structured capabilities.
                </p>
              </div>
              <div className="w-full lg:w-96 bg-zinc-950 border border-zinc-800 rounded-lg p-4 font-mono text-xs text-zinc-300 shadow-2xl">
                <div className="flex justify-between border-b border-zinc-800 pb-2 mb-2 text-zinc-500">
                  <span>ACTION</span><span>POLICY</span>
                </div>
                <div className="flex justify-between py-1">
                  <span>refund.create</span><span className="text-emerald-400">ALLOW (Quorum)</span>
                </div>
                <div className="flex justify-between py-1">
                  <span>customer.delete</span><span className="text-red-400">DENY</span>
                </div>
              </div>
            </div>

          </div>
        </section>

        {/* RISK & ENFORCEMENT */}
        <section className="max-w-7xl mx-auto px-6 py-24 border-t border-zinc-900 grid grid-cols-1 md:grid-cols-2 gap-12">
          <div>
            <h2 className="font-outfit text-3xl font-bold text-white mb-6 uppercase">
              Permission isn't <br /> the same as safety.
            </h2>
            <p className="text-zinc-400 text-lg mb-8">
              An action may be permitted by policy but still require additional security controls based on risk. CRITICAL actions can enforce human-in-the-loop approval, while UNKNOWN states fail closed.
            </p>
          </div>
          <div>
            <h2 className="font-outfit text-3xl font-bold text-white mb-6 uppercase">
              Decide before <br /> the action executes.
            </h2>
            <div className="bg-zinc-900/50 border border-zinc-800 p-6 rounded-xl flex items-center justify-between text-sm font-medium">
              <span className="text-zinc-300">AI AGENT</span>
              <div className="flex flex-col items-center gap-2">
                <ArrowRight className="text-zinc-600" />
                <span className="bg-indigo-900/50 text-indigo-400 px-2 py-0.5 rounded text-[10px]">SENTINEL</span>
              </div>
              <div className="flex flex-col gap-2 text-[11px]">
                <div className="flex items-center gap-2 text-emerald-400">
                  <ArrowRight className="w-3 h-3" /> ALLOW → API
                </div>
                <div className="flex items-center gap-2 text-red-400">
                  <ArrowRight className="w-3 h-3" /> DENY → BLOCKED
                </div>
              </div>
            </div>
            <p className="text-zinc-500 text-sm mt-4 italic">
              "A denied action never reaches the protected execution path."
            </p>
          </div>
        </section>

        {/* ARCHITECTURE */}
        <section className="max-w-7xl mx-auto px-6 py-24 border-t border-zinc-900">
          <div className="text-center mb-16">
            <h2 className="font-outfit text-3xl lg:text-4xl font-bold text-white mb-4 uppercase tracking-wide">
              A SECURITY CONTROL PLANE <br /> FOR AGENTIC SYSTEMS.
            </h2>
          </div>
          <div className="max-w-4xl mx-auto bg-zinc-950 border border-zinc-800 rounded-2xl p-8 flex flex-col items-center text-center">
            <div className="text-zinc-300 font-bold mb-4">AI AGENTS</div>
            <ArrowRight className="w-4 h-4 text-zinc-600 rotate-90 mb-4" />
            <div className="bg-indigo-600 text-white font-bold tracking-widest px-8 py-3 rounded mb-8 shadow-[0_0_20px_rgba(79,70,229,0.2)]">
              SENTINEL GATEWAY
            </div>
            <div className="flex gap-4 sm:gap-12 mb-8">
              <div className="bg-zinc-900 border border-zinc-800 px-6 py-3 rounded text-sm text-zinc-300">Identity</div>
              <div className="bg-zinc-900 border border-zinc-800 px-6 py-3 rounded text-sm text-zinc-300">Capability</div>
              <div className="bg-zinc-900 border border-zinc-800 px-6 py-3 rounded text-sm text-zinc-300">Policy</div>
            </div>
            <ArrowRight className="w-4 h-4 text-zinc-600 rotate-90 mb-4" />
            <div className="bg-zinc-900 border border-zinc-800 px-8 py-3 rounded text-sm text-amber-400 mb-4">Risk Evaluation</div>
            <ArrowRight className="w-4 h-4 text-zinc-600 rotate-90 mb-4" />
            <div className="bg-zinc-900 border border-zinc-800 px-8 py-3 rounded text-sm text-emerald-400 mb-8">Enforcement</div>
            <ArrowRight className="w-4 h-4 text-zinc-600 rotate-90 mb-4" />
            <div className="text-zinc-300 font-bold mb-8">TOOLS / APIs</div>
          </div>
        </section>

        {/* SEC-OPS PREVIEW */}
        <section className="max-w-7xl mx-auto px-6 py-24 border-t border-zinc-900">
          <div className="text-center mb-16">
            <h2 className="font-outfit text-3xl font-bold text-white uppercase tracking-wide">
              See what your agents are doing.
            </h2>
          </div>
          <div className="max-w-5xl mx-auto bg-zinc-950 rounded-2xl border border-zinc-800 shadow-2xl overflow-hidden flex flex-col md:flex-row h-[500px]">
            {/* Sidebar */}
            <div className="w-48 bg-zinc-900/50 border-r border-zinc-800 p-4 hidden md:block">
              <div className="text-xs font-bold text-zinc-500 mb-4 uppercase">Control Plane</div>
              {["Overview", "Agents", "Policies", "Capabilities", "Incidents", "Settings"].map(l => (
                <div key={l} className="text-sm text-zinc-400 py-1.5 hover:text-white cursor-pointer">{l}</div>
              ))}
            </div>
            {/* Content */}
            <div className="flex-1 p-6 overflow-y-auto">
              <div className="text-sm font-bold text-white mb-6 uppercase tracking-wider flex items-center justify-between">
                Security Activity
                <span className="bg-red-500/20 text-red-400 px-2 py-0.5 rounded text-[10px]">1 INCIDENT OPEN</span>
              </div>
              <div className="space-y-2 font-mono text-xs">
                <div className="flex items-center gap-4 bg-zinc-900/50 p-3 rounded border border-zinc-800/50">
                  <span className="text-zinc-500">09:42:03</span>
                  <span className="text-indigo-400 w-32">support-agent</span>
                  <span className="text-zinc-300 flex-1">crm.read</span>
                  <span className="text-emerald-400 font-bold">ALLOWED</span>
                </div>
                <div className="flex items-center gap-4 bg-zinc-900/50 p-3 rounded border border-zinc-800/50">
                  <span className="text-zinc-500">09:42:05</span>
                  <span className="text-indigo-400 w-32">support-agent</span>
                  <span className="text-zinc-300 flex-1">email.send</span>
                  <span className="text-emerald-400 font-bold">ALLOWED</span>
                </div>
                <div className="flex items-center gap-4 bg-red-950/20 p-3 rounded border border-red-900/30">
                  <span className="text-zinc-500">09:42:08</span>
                  <span className="text-indigo-400 w-32">support-agent</span>
                  <span className="text-zinc-300 flex-1">customer.delete</span>
                  <span className="text-red-400 font-bold">DENIED: POLICY</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* SECURITY PRINCIPLES */}
        <section className="max-w-7xl mx-auto px-6 py-24 border-t border-zinc-900">
          <h4 className="text-sm font-bold text-zinc-500 uppercase tracking-widest text-center mb-12">
            Built Around Security Invariants
          </h4>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-8 text-center">
            <div>
              <div className="text-white font-bold mb-2">IDENTITY</div>
              <div className="text-zinc-500 text-sm">Every agent has an identity.</div>
            </div>
            <div>
              <div className="text-white font-bold mb-2">TENANT ISOLATION</div>
              <div className="text-zinc-500 text-sm">Organizations remain isolated.</div>
            </div>
            <div>
              <div className="text-white font-bold mb-2">LEAST PRIVILEGE</div>
              <div className="text-zinc-500 text-sm">Capabilities constrain access.</div>
            </div>
            <div>
              <div className="text-white font-bold mb-2">DETERMINISTIC AUTHORIZATION</div>
              <div className="text-zinc-500 text-sm">Policies produce predictable decisions.</div>
            </div>
            <div>
              <div className="text-white font-bold mb-2">FAIL CLOSED</div>
              <div className="text-zinc-500 text-sm">Unknown security states are not allowed.</div>
            </div>
            <div>
              <div className="text-white font-bold mb-2">AUDITABILITY</div>
              <div className="text-zinc-500 text-sm">Security decisions leave traceable records.</div>
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="max-w-7xl mx-auto px-6 py-32 border-t border-zinc-900 relative overflow-hidden text-center">
          <div className="absolute inset-0 bg-[url('/hero.png')] bg-center opacity-5 bg-no-repeat bg-contain" />
          <div className="relative z-10">
            <h2 className="font-outfit text-4xl lg:text-5xl font-bold text-white mb-8 uppercase tracking-wide leading-tight">
              YOUR AGENTS ARE <br /> ALREADY TAKING ACTION. <br />
              <span className="text-indigo-400">MAKE SURE YOU KNOW <br /> WHAT THEY CAN DO.</span>
            </h2>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link href="/signup" className="bg-indigo-600 hover:bg-indigo-500 text-white px-8 py-4 rounded-lg font-bold transition-all shadow-[0_0_20px_rgba(79,70,229,0.3)] tracking-wider">
                CONNECT AN AGENT
              </Link>
              <Link href="mailto:contact@zorvak.com" className="bg-transparent hover:bg-zinc-900 border border-zinc-700 text-white px-8 py-4 rounded-lg font-bold transition-all tracking-wider">
                TALK TO ZORVAK
              </Link>
            </div>
          </div>
        </section>

      </main>

      {/* FOOTER */}
      <footer className="bg-[#050505] border-t border-zinc-900 pt-20 pb-12">
        <div className="max-w-7xl mx-auto px-6 grid grid-cols-1 md:grid-cols-12 gap-12 mb-16">
          {/* Brand Column */}
          <div className="md:col-span-5 lg:col-span-4 flex flex-col items-start">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-12 h-12 rounded relative overflow-hidden bg-zinc-950 flex items-center justify-center shrink-0">
                <Image src="/hero.png" alt="Zorvak Sentinel Logo" width={48} height={48} className="object-contain scale-[2] translate-y-[2px]" />
              </div>
              <div className="flex flex-col">
                <span className="font-outfit font-bold text-white tracking-[0.3em] text-sm">ZORVAK</span>
                <span className="font-outfit font-bold text-white tracking-[0.4em] text-xl uppercase mt-0.5">SENTINEL</span>
                <span className="text-[8px] text-zinc-500 font-bold tracking-widest uppercase mt-1">SECURITY FOR AI AGENTS</span>
              </div>
            </div>
            <p className="text-[13px] text-zinc-400 leading-relaxed max-w-[280px] mb-8">
              ZORVAK SENTINEL provides the security control plane for autonomous AI agents. Know. Control. Protect.
            </p>
            {/* Social links removed as requested */}
          </div>

          {/* Nav Columns */}
          <div className="md:col-span-7 lg:col-span-8 grid grid-cols-2 sm:grid-cols-4 gap-8">
            <div>
              <div className="text-white font-bold text-[13px] tracking-wide mb-6">Platform</div>
              <div className="flex flex-col gap-4 text-[13px] text-zinc-400">
                <Link href="/" className="hover:text-white transition-colors">Overview</Link>
                <Link href="/pricing" className="hover:text-white transition-colors">Pricing</Link>
              </div>
            </div>
            <div>
              <div className="text-white font-bold text-[13px] tracking-wide mb-6">Developers</div>
              <div className="flex flex-col gap-4 text-[13px] text-zinc-400">
                <Link href="/developers" className="hover:text-white transition-colors">Developer Portal</Link>
              </div>
            </div>
            <div>
              <div className="text-white font-bold text-[13px] tracking-wide mb-6">Legal</div>
              <div className="flex flex-col gap-4 text-[13px] text-zinc-400">
                <Link href="/privacy" className="hover:text-white transition-colors">Privacy</Link>
                <Link href="/terms" className="hover:text-white transition-colors">Terms</Link>
                <Link href="/security" className="hover:text-white transition-colors">Security</Link>
              </div>
            </div>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="max-w-7xl mx-auto px-6 pt-8 border-t border-zinc-900 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="text-[11px] text-zinc-500">
            &copy; 2026 ZORVAK STUDIOS. All rights reserved.
          </div>
          <div className="flex items-center gap-3 text-[10px] font-bold tracking-[0.2em] text-zinc-500">
            <span>KNOW</span>
            <span className="w-1 h-1 rounded-full bg-zinc-800" />
            <span>CONTROL</span>
            <span className="w-1 h-1 rounded-full bg-zinc-800" />
            <span>PROTECT</span>
          </div>
        </div>
      </footer >
    </div >
  );
}
