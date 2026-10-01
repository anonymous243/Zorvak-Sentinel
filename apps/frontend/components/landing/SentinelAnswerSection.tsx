import React from 'react';
import { ShieldCheck, ShieldAlert, CheckCircle2, XCircle } from 'lucide-react';

export function SentinelAnswerSection() {
  return (
    <section id="architecture" className="max-w-7xl mx-auto px-6 py-32 border-t border-zinc-900">
      
      <div className="text-center max-w-3xl mx-auto mb-24">
        <h2 className="font-outfit text-4xl lg:text-5xl font-bold text-white mb-6 tracking-wide leading-tight uppercase">
          PUT A SECURITY <br /> BOUNDARY AROUND <br /> YOUR AGENTS.
        </h2>
        <p className="text-zinc-400 text-lg leading-relaxed">
          SENTINEL sits between autonomous agents and the systems they can act on, applying identity, capability, policy, risk, and runtime enforcement before protected actions execute.
        </p>
      </div>

      {/* Sentinel Architecture Diagram */}
      <div className="relative bg-zinc-950 border border-zinc-800 rounded-2xl p-8 lg:p-16 mb-24 overflow-hidden">
        
        {/* Animated signal line background */}
        <div className="absolute top-[100px] left-0 right-0 h-[2px] bg-zinc-900 hidden lg:block" />
        <div className="absolute top-[100px] left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-blue-500 to-transparent hidden lg:block motion-safe:animate-[slideRight_3s_ease-in-out_infinite] opacity-50" />

        {/* Nodes */}
        <div className="relative z-10 flex flex-col lg:flex-row items-center justify-between gap-6 lg:gap-2">
          
          <div className="flex flex-col items-center min-w-[80px]">
            <div className="w-12 h-12 bg-zinc-900 border border-zinc-700 rounded-lg shadow-lg flex items-center justify-center text-xs font-bold text-white mb-3">AGT</div>
            <div className="text-[9px] text-zinc-500 tracking-[0.2em] font-bold">AGENT</div>
          </div>

          <div className="hidden lg:block w-8 h-[1px] bg-zinc-700" />
          <div className="lg:hidden h-8 w-[1px] bg-zinc-700" />

          <div className="flex flex-col items-center min-w-[80px]">
            <div className="w-12 h-12 bg-blue-950 border border-blue-900 rounded-lg shadow-lg flex items-center justify-center text-xs font-bold text-blue-400 mb-3">ID</div>
            <div className="text-[9px] text-zinc-500 tracking-[0.2em] font-bold">IDENTITY</div>
          </div>

          <div className="hidden lg:block w-8 h-[1px] bg-zinc-700" />
          <div className="lg:hidden h-8 w-[1px] bg-zinc-700" />

          <div className="flex flex-col items-center min-w-[80px]">
            <div className="w-12 h-12 bg-blue-950 border border-blue-900 rounded-lg shadow-lg flex items-center justify-center text-xs font-bold text-blue-400 mb-3">CAP</div>
            <div className="text-[9px] text-zinc-500 tracking-[0.2em] font-bold">CAPABILITY</div>
          </div>

          <div className="hidden lg:block w-8 h-[1px] bg-zinc-700" />
          <div className="lg:hidden h-8 w-[1px] bg-zinc-700" />

          <div className="flex flex-col items-center min-w-[80px]">
            <div className="w-12 h-12 bg-blue-950 border border-blue-900 rounded-lg shadow-lg flex items-center justify-center text-xs font-bold text-blue-400 mb-3">POL</div>
            <div className="text-[9px] text-zinc-500 tracking-[0.2em] font-bold">POLICY</div>
          </div>

          <div className="hidden lg:block w-8 h-[1px] bg-zinc-700" />
          <div className="lg:hidden h-8 w-[1px] bg-zinc-700" />

          <div className="flex flex-col items-center min-w-[80px]">
            <div className="w-12 h-12 bg-blue-950 border border-blue-900 rounded-lg shadow-lg flex items-center justify-center text-xs font-bold text-blue-400 mb-3">RSK</div>
            <div className="text-[9px] text-zinc-500 tracking-[0.2em] font-bold">RISK</div>
          </div>

          <div className="hidden lg:block w-8 h-[1px] bg-zinc-700" />
          <div className="lg:hidden h-8 w-[1px] bg-zinc-700" />

          <div className="flex flex-col items-center min-w-[80px]">
            <div className="w-12 h-12 bg-blue-900/50 border border-blue-500 rounded-lg shadow-[0_0_15px_rgba(59,130,246,0.2)] flex items-center justify-center text-xs font-bold text-white mb-3">DEC</div>
            <div className="text-[9px] text-zinc-500 tracking-[0.2em] font-bold">DECISION</div>
          </div>

          <div className="hidden lg:block w-8 h-[1px] bg-zinc-700" />
          <div className="lg:hidden h-8 w-[1px] bg-zinc-700" />

          <div className="flex flex-col items-center min-w-[80px]">
            <div className="w-12 h-12 bg-zinc-900 border border-zinc-700 rounded-lg shadow-lg flex items-center justify-center text-xs font-bold text-white mb-3">ENF</div>
            <div className="text-[9px] text-zinc-500 tracking-[0.2em] font-bold">ENFORCEMENT</div>
          </div>

          <div className="hidden lg:block w-8 h-[1px] bg-zinc-700" />
          <div className="lg:hidden h-8 w-[1px] bg-zinc-700" />

          <div className="flex flex-col items-center min-w-[80px]">
            <div className="w-12 h-12 bg-zinc-900 border border-zinc-700 rounded-lg shadow-lg flex items-center justify-center text-xs font-bold text-zinc-400 mb-3">API</div>
            <div className="text-[9px] text-zinc-500 tracking-[0.2em] font-bold">TOOL/API</div>
          </div>

        </div>

        {/* Security Events layer below */}
        <div className="mt-16 pt-16 border-t border-zinc-900 relative">
          <div className="absolute top-0 left-[60%] w-[1px] h-16 bg-zinc-900 hidden lg:block" />
          <div className="flex flex-col lg:flex-row items-center justify-center gap-6 lg:gap-12">
            
            <div className="flex items-center gap-3 text-zinc-500">
               <span className="text-[10px] font-bold tracking-[0.2em]">SECURITY EVENTS</span>
               <div className="w-4 h-[1px] bg-zinc-800 hidden lg:block" />
            </div>
            
            <div className="flex items-center gap-3 text-zinc-500">
               <span className="text-[10px] font-bold tracking-[0.2em]">INCIDENTS</span>
               <div className="w-4 h-[1px] bg-zinc-800 hidden lg:block" />
            </div>
            
            <div className="flex items-center gap-3 text-zinc-500">
               <span className="text-[10px] font-bold tracking-[0.2em]">EVIDENCE</span>
               <div className="w-4 h-[1px] bg-zinc-800 hidden lg:block" />
            </div>
            
            <div className="flex items-center gap-3 text-zinc-500">
               <span className="text-[10px] font-bold tracking-[0.2em]">INVESTIGATION</span>
               <div className="w-4 h-[1px] bg-zinc-800 hidden lg:block" />
            </div>
            
            <div className="flex items-center gap-3 text-zinc-500">
               <span className="text-[10px] font-bold tracking-[0.2em]">RESPONSE</span>
            </div>
          </div>
        </div>
      </div>

      {/* Allow / Deny Visuals */}
      <div className="text-center mb-8">
        <span className="text-[10px] text-zinc-500 tracking-[0.2em] font-bold uppercase">ILLUSTRATIVE REQUEST FLOW</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl mx-auto">
        
        {/* Allow Example */}
        <div className="bg-[#050505] border border-zinc-900 p-6 rounded-xl shadow-2xl flex flex-col">
          <div className="text-[10px] text-zinc-500 font-bold tracking-[0.2em] mb-4 uppercase">AGENT REQUEST</div>
          <div className="bg-zinc-950 border border-zinc-800 p-3 rounded text-xs font-mono text-zinc-400 mb-6">
            <span className="text-blue-400">action:</span> refund.create<br />
            <span className="text-blue-400">resource:</span> customer_482
          </div>
          
          <div className="flex justify-center mb-6">
            <div className="w-[1px] h-6 bg-zinc-800" />
          </div>

          <div className="text-[10px] text-blue-500 font-bold tracking-[0.2em] mb-4 uppercase font-outfit text-center">SENTINEL</div>
          <div className="bg-zinc-950 border border-zinc-800 p-4 rounded text-xs space-y-3 mb-6">
            <div className="flex justify-between text-zinc-300"><span>Identity</span> <CheckCircle2 className="w-4 h-4 text-emerald-500" /></div>
            <div className="flex justify-between text-zinc-300"><span>Capability</span> <CheckCircle2 className="w-4 h-4 text-emerald-500" /></div>
            <div className="flex justify-between text-zinc-300"><span>Policy</span> <CheckCircle2 className="w-4 h-4 text-emerald-500" /></div>
            <div className="flex justify-between text-zinc-300"><span>Risk</span> <span className="text-amber-500 font-bold tracking-wider">HIGH</span></div>
          </div>

          <div className="flex justify-center mb-6">
            <div className="w-[1px] h-6 bg-zinc-800" />
          </div>
          
          <div className="text-center mb-6">
             <div className="text-[10px] text-zinc-500 font-bold tracking-[0.2em] mb-2 uppercase">DECISION</div>
             <div className="inline-block bg-emerald-500/10 border border-emerald-500/50 text-emerald-400 px-4 py-1.5 rounded text-xs font-bold tracking-widest shadow-[0_0_10px_rgba(16,185,129,0.1)]">ALLOW</div>
          </div>

          <div className="flex justify-center mb-6">
            <div className="w-[1px] h-6 bg-zinc-800" />
          </div>

          <div className="text-center text-xs font-bold text-zinc-400 tracking-wider">PROTECTED TOOL</div>
        </div>

        {/* Deny Example */}
        <div className="bg-[#050505] border border-zinc-900 p-6 rounded-xl shadow-2xl flex flex-col">
          <div className="text-[10px] text-zinc-500 font-bold tracking-[0.2em] mb-4 uppercase">AGENT REQUEST</div>
          <div className="bg-zinc-950 border border-zinc-800 p-3 rounded text-xs font-mono text-zinc-400 mb-6">
            <span className="text-blue-400">action:</span> customer.delete<br />
            <br/>
          </div>
          
          <div className="flex justify-center mb-6">
            <div className="w-[1px] h-6 bg-zinc-800" />
          </div>

          <div className="text-[10px] text-blue-500 font-bold tracking-[0.2em] mb-4 uppercase font-outfit text-center">POLICY</div>
          <div className="bg-zinc-950 border border-zinc-800 p-4 rounded text-xs space-y-3 mb-6 h-[116px] flex items-center justify-center">
            <div className="flex items-center gap-2 text-red-400 font-bold tracking-wider"><ShieldAlert className="w-4 h-4" /> DENY</div>
          </div>

          <div className="flex justify-center mb-6">
            <div className="w-[1px] h-6 bg-zinc-800" />
          </div>
          
          <div className="text-center mb-6">
             <div className="text-[10px] text-zinc-500 font-bold tracking-[0.2em] mb-2 uppercase">DECISION</div>
             <div className="inline-block bg-red-500/10 border border-red-500/50 text-red-500 px-4 py-1.5 rounded text-xs font-bold tracking-widest shadow-[0_0_10px_rgba(239,68,68,0.1)]">BLOCKED</div>
          </div>

          <div className="flex justify-center mb-6">
            <div className="w-[1px] h-6 bg-zinc-800" />
          </div>

          <div className="text-center text-xs font-bold text-zinc-600 tracking-wider line-through">EXECUTION BLOCKED</div>
        </div>

      </div>

    </section>
  );
}
