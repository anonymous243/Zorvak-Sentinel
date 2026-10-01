import Link from "next/link";
import Image from "next/image";
import { Check } from "lucide-react";

export default function PricingPage() {
  return (
    <div className="min-h-screen bg-[#050505] text-zinc-300 font-sans">
      <nav className="border-b border-zinc-900 bg-[#050505]">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3 hover:opacity-80 transition-opacity">
            <div className="w-8 h-8 rounded relative overflow-hidden bg-zinc-950 flex items-center justify-center">
              <Image src="/hero.png" alt="Zorvak Sentinel Logo" width={32} height={32} className="object-contain scale-[2] translate-y-[2px]" />
            </div>
            <span className="font-outfit font-bold text-white tracking-widest text-sm">ZORVAK SENTINEL</span>
          </Link>
          <div className="flex items-center gap-4">
            <Link href="/login" className="text-sm font-bold tracking-wider uppercase text-zinc-400 hover:text-white transition-colors">
              Sign In
            </Link>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-6 py-24">
        
        {/* Header */}
        <div className="text-center max-w-3xl mx-auto mb-20 relative">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-[600px] h-[300px] bg-indigo-500/10 blur-[100px] rounded-full pointer-events-none" />
          <h1 className="relative z-10 font-outfit text-4xl lg:text-5xl font-bold text-white mb-6 tracking-wide uppercase leading-tight">
            SECURITY THAT SCALES <br /> WITH YOUR AGENTS.
          </h1>
          <p className="relative z-10 text-lg text-zinc-400 max-w-2xl mx-auto leading-relaxed">
            Start with the controls you need today. Expand protection as your autonomous systems take on more critical operations.
          </p>
        </div>

        {/* Pricing Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl mx-auto">
          
          {/* Starter Plan */}
          <div className="bg-[#0a0a0a] border border-zinc-800 rounded p-10 hover:border-zinc-700 transition-colors relative">
            <div className="flex items-center justify-between mb-8">
              <div>
                <h3 className="font-outfit text-xl font-bold text-white tracking-widest uppercase">STARTER</h3>
                <div className="text-[10px] font-bold text-zinc-500 tracking-widest uppercase mt-1">DEVELOPMENT</div>
              </div>
            </div>
            
            <div className="mb-8">
              <div className="text-3xl font-bold text-white">$0</div>
              <div className="text-xs text-zinc-500 font-medium uppercase tracking-wider mt-1">/ month</div>
            </div>
            
            <div className="border-t border-zinc-900 pt-8 mb-10">
              <div className="text-xs font-bold text-white tracking-widest uppercase mb-6">FEATURES</div>
              <ul className="space-y-4 text-sm text-zinc-400">
                <li className="flex items-center gap-3">
                  <Check className="w-4 h-4 text-zinc-600 shrink-0" /> 
                  <span>Up to 5 Active Agents</span>
                </li>
                <li className="flex items-center gap-3">
                  <Check className="w-4 h-4 text-zinc-600 shrink-0" /> 
                  <span>10,000 policy evaluations/mo</span>
                </li>
                <li className="flex items-center gap-3">
                  <Check className="w-4 h-4 text-zinc-600 shrink-0" /> 
                  <span>Basic Risk Engine</span>
                </li>
                <li className="flex items-center gap-3">
                  <Check className="w-4 h-4 text-zinc-600 shrink-0" /> 
                  <span>7-day Incident Retention</span>
                </li>
              </ul>
            </div>
            
            <Link href="/signup" className="block w-full text-center bg-zinc-900 border border-zinc-700 hover:bg-zinc-800 hover:text-white text-zinc-300 py-3 rounded text-sm font-bold tracking-widest uppercase transition-colors">
              GET STARTED
            </Link>
          </div>

          {/* Enterprise Plan */}
          <div className="bg-[#0a0a0a] border border-indigo-500/30 rounded p-10 relative overflow-hidden shadow-[0_0_30px_rgba(79,70,229,0.05)]">
            <div className="absolute top-0 right-0 bg-indigo-950/50 border-b border-l border-indigo-500/30 text-indigo-400 text-[10px] font-bold px-4 py-1.5 tracking-widest uppercase">
              RECOMMENDED
            </div>
            
            <div className="flex items-center justify-between mb-8">
              <div>
                <h3 className="font-outfit text-xl font-bold text-white tracking-widest uppercase">ENTERPRISE</h3>
                <div className="text-[10px] font-bold text-indigo-400 tracking-widest uppercase mt-1">PRODUCTION</div>
              </div>
            </div>
            
            <div className="mb-8">
              <div className="text-3xl font-bold text-white">Custom</div>
              <div className="text-xs text-zinc-500 font-medium uppercase tracking-wider mt-1 opacity-0">/ month</div>
            </div>
            
            <div className="border-t border-zinc-900 pt-8 mb-10">
              <div className="text-xs font-bold text-white tracking-widest uppercase mb-6">FEATURES</div>
              <ul className="space-y-4 text-sm text-zinc-400">
                <li className="flex items-center gap-3">
                  <Check className="w-4 h-4 text-indigo-500 shrink-0" /> 
                  <span>Unlimited Agents & Evaluations</span>
                </li>
                <li className="flex items-center gap-3">
                  <Check className="w-4 h-4 text-indigo-500 shrink-0" /> 
                  <span>Advanced Risk & Heuristic Engine</span>
                </li>
                <li className="flex items-center gap-3">
                  <Check className="w-4 h-4 text-indigo-500 shrink-0" /> 
                  <span>Unlimited Forensic Retention</span>
                </li>
                <li className="flex items-center gap-3">
                  <Check className="w-4 h-4 text-indigo-500 shrink-0" /> 
                  <span>Custom SIEM Integrations</span>
                </li>
                <li className="flex items-center gap-3">
                  <Check className="w-4 h-4 text-indigo-500 shrink-0" /> 
                  <span>24/7 Priority Support</span>
                </li>
              </ul>
            </div>
            
            <Link href="mailto:contact@zorvak.com" className="block w-full text-center bg-indigo-600 hover:bg-indigo-500 text-white py-3 rounded text-sm font-bold tracking-widest uppercase transition-colors shadow-[0_0_15px_rgba(79,70,229,0.2)]">
              CONTACT SALES
            </Link>
          </div>
          
        </div>
      </main>
    </div>
  );
}
