import React from 'react';
import { Database, CreditCard, MessageSquare, Briefcase, Activity, Settings, Workflow } from 'lucide-react';

export function ProblemSection() {
  return (
    <section id="problem" className="max-w-7xl mx-auto px-6 py-32 border-t border-zinc-900">
      <div className="text-center max-w-3xl mx-auto mb-20">
        <h2 className="font-outfit text-4xl lg:text-5xl font-bold text-white mb-6 tracking-wide leading-tight uppercase">
          AI AGENTS ARE <br /> BECOMING THE NEW <br /> ATTACK SURFACE.
        </h2>
        <p className="text-zinc-400 text-lg leading-relaxed">
          Autonomous agents don&apos;t just generate text. They can access tools, call APIs, retrieve data, execute workflows, and take actions on behalf of their operators.
        </p>
      </div>

      <div className="flex flex-col lg:flex-row items-stretch justify-center gap-12 lg:gap-24 mb-32">
        
        {/* Traditional */}
        <div className="flex-1 flex flex-col items-center">
          <div className="text-[11px] text-zinc-500 font-bold tracking-[0.2em] uppercase mb-8">Traditional Application</div>
          <div className="flex flex-col items-center space-y-3 relative">
            <div className="bg-zinc-900 border border-zinc-800 text-zinc-300 px-6 py-3 rounded text-sm w-48 text-center font-medium">Human</div>
            <div className="h-6 w-[1px] bg-zinc-800" />
            <div className="w-2 h-2 rounded-full border border-zinc-700 bg-zinc-900 absolute top-[44px]" />
            <div className="bg-zinc-900 border border-zinc-800 text-zinc-300 px-6 py-3 rounded text-sm w-48 text-center font-medium">Application</div>
            <div className="h-6 w-[1px] bg-zinc-800" />
            <div className="w-2 h-2 rounded-full border border-zinc-700 bg-zinc-900 absolute top-[108px]" />
            <div className="bg-blue-900/20 border border-blue-900/50 text-blue-400 px-6 py-3 rounded text-sm w-48 text-center font-medium shadow-[0_0_15px_rgba(59,130,246,0.1)]">Action</div>
          </div>
        </div>

        {/* Divider */}
        <div className="hidden lg:block w-[1px] bg-zinc-900 self-stretch" />

        {/* Autonomous */}
        <div className="flex-1 flex flex-col items-center">
          <div className="text-[11px] text-zinc-500 font-bold tracking-[0.2em] uppercase mb-8">Autonomous System</div>
          <div className="flex flex-col items-center space-y-3 relative">
            <div className="bg-zinc-900 border border-zinc-800 text-zinc-300 px-6 py-3 rounded text-sm w-48 text-center font-medium flex items-center justify-center gap-2">
              <Activity className="w-4 h-4 text-zinc-400" /> AI Agent
            </div>
            <div className="h-4 w-[1px] bg-zinc-800" />
            <div className="bg-zinc-900 border border-zinc-800 text-zinc-300 px-6 py-3 rounded text-sm w-48 text-center font-medium">Decision</div>
            <div className="h-4 w-[1px] bg-zinc-800" />
            <div className="bg-zinc-900 border border-zinc-800 text-zinc-300 px-6 py-3 rounded text-sm w-48 text-center font-medium">Tool</div>
            <div className="h-4 w-[1px] bg-zinc-800" />
            <div className="bg-zinc-900 border border-zinc-800 text-zinc-300 px-6 py-3 rounded text-sm w-48 text-center font-medium">API</div>
            <div className="h-4 w-[1px] bg-zinc-800" />
            <div className="bg-zinc-900 border border-zinc-800 text-zinc-300 px-6 py-3 rounded text-sm w-48 text-center font-medium">Data / Infrastructure</div>
            <div className="h-4 w-[1px] bg-zinc-800" />
            <div className="bg-red-900/20 border border-red-900/50 text-red-400 px-6 py-3 rounded text-sm w-48 text-center font-medium shadow-[0_0_15px_rgba(239,68,68,0.1)]">Real-world action</div>
          </div>
        </div>

      </div>

      {/* Problem Visualization (Architectural Diagram) */}
      <div className="relative max-w-4xl mx-auto h-[400px] flex items-center justify-center mb-32 bg-zinc-950/50 rounded-2xl border border-zinc-900 overflow-hidden">
        
        {/* Subtle grid bg */}
        <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:40px_40px]" />
        
        {/* Security boundary circle */}
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
           <div className="w-[340px] h-[340px] rounded-full border border-dashed border-red-900/50 bg-red-950/10 animate-[pulse_4s_ease-in-out_infinite]" />
        </div>

        <div className="relative z-10 w-full h-full">
            {/* Center Node */}
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-zinc-900 border border-zinc-700 p-4 rounded-xl shadow-2xl flex flex-col items-center">
              <Activity className="w-8 h-8 text-white mb-2" />
              <span className="font-outfit font-bold text-white tracking-wider text-xs">AI AGENT</span>
            </div>

            {/* Connecting lines - SVG */}
            <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{ zIndex: 0 }}>
               <line x1="50%" y1="50%" x2="50%" y2="25%" stroke="#27272a" strokeWidth="2" />
               <line x1="50%" y1="50%" x2="50%" y2="78%" stroke="#27272a" strokeWidth="2" />
               <line x1="50%" y1="50%" x2="25%" y2="50%" stroke="#27272a" strokeWidth="2" />
               <line x1="50%" y1="50%" x2="75%" y2="50%" stroke="#27272a" strokeWidth="2" />
               <line x1="50%" y1="50%" x2="32%" y2="25%" stroke="#27272a" strokeWidth="2" />
               <line x1="50%" y1="50%" x2="72%" y2="70%" stroke="#27272a" strokeWidth="2" />
            </svg>

            {/* Orbiting Nodes */}
            <div className="absolute top-[20%] left-1/2 -translate-x-1/2 flex items-center gap-2 bg-zinc-950 border border-zinc-800 px-4 py-2 rounded text-xs text-zinc-400">
               <Settings className="w-3 h-3" /> TOOLS
            </div>
            <div className="absolute top-[50%] left-[20%] -translate-y-1/2 flex items-center gap-2 bg-zinc-950 border border-zinc-800 px-4 py-2 rounded text-xs text-zinc-400">
               <Database className="w-3 h-3" /> DATABASES
            </div>
            <div className="absolute top-[50%] right-[20%] -translate-y-1/2 flex items-center gap-2 bg-zinc-950 border border-zinc-800 px-4 py-2 rounded text-xs text-zinc-400">
               <Briefcase className="w-3 h-3" /> APIs
            </div>
            <div className="absolute bottom-[17%] left-1/2 -translate-x-[60%] flex items-center gap-2 bg-zinc-950 border border-zinc-800 px-4 py-2 rounded text-xs text-zinc-400">
               <Workflow className="w-3 h-3" /> WORKFLOWS
            </div>
            <div className="absolute top-[20%] left-[25%] flex items-center gap-2 bg-zinc-950 border border-zinc-800 px-4 py-2 rounded text-xs text-zinc-400">
               <CreditCard className="w-3 h-3" /> PAYMENTS
            </div>
            <div className="absolute bottom-[26%] right-[18%] flex items-center gap-2 bg-zinc-950 border border-zinc-800 px-4 py-2 rounded text-xs text-zinc-400">
               <MessageSquare className="w-3 h-3" /> COMMUNICATION
            </div>
            
            <div className="absolute bottom-4 left-0 right-0 text-center text-[10px] text-red-500/70 tracking-[0.2em] uppercase font-bold">
              SECURITY BOUNDARY AT RISK
            </div>
        </div>
      </div>

      {/* Copy blocks */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-x-12 gap-y-16 max-w-5xl mx-auto mb-32">
        <div className="flex flex-col items-start text-left">
          <div className="text-white font-bold tracking-wider mb-4 text-sm flex items-center gap-3">
             <span className="w-2 h-2 bg-blue-500 rounded-full" /> AGENTS CAN ACT
          </div>
          <p className="text-zinc-400 text-sm leading-relaxed">
            Agents can execute actions rather than merely return information.
          </p>
        </div>
        <div className="flex flex-col items-start text-left">
          <div className="text-white font-bold tracking-wider mb-4 text-sm flex items-center gap-3">
             <span className="w-2 h-2 bg-blue-500 rounded-full" /> TOOLS CREATE PRIVILEGE
          </div>
          <p className="text-zinc-400 text-sm leading-relaxed">
            Every connected tool can expand what an agent is capable of doing.
          </p>
        </div>
        <div className="flex flex-col items-start text-left">
          <div className="text-white font-bold tracking-wider mb-4 text-sm flex items-center gap-3">
             <span className="w-2 h-2 bg-blue-500 rounded-full" /> CONTEXT CHANGES
          </div>
          <p className="text-zinc-400 text-sm leading-relaxed">
            The same action can carry different risk depending on context.
          </p>
        </div>
        <div className="flex flex-col items-start text-left">
          <div className="text-white font-bold tracking-wider mb-4 text-sm flex items-center gap-3">
             <span className="w-2 h-2 bg-blue-500 rounded-full" /> AUTONOMY CHANGES THE SECURITY MODEL
          </div>
          <p className="text-zinc-400 text-sm leading-relaxed">
            Security controls must operate at the point where agent actions are requested and executed.
          </p>
        </div>
      </div>

      {/* Transition */}
      <div className="flex flex-col items-center text-center">
        <div className="text-[10px] text-zinc-500 tracking-[0.2em] font-bold uppercase mb-4">THE QUESTION IS NO LONGER:</div>
        <div className="text-xl text-zinc-300 italic mb-12">&quot;What can the model generate?&quot;</div>
        <div className="text-[10px] text-zinc-500 tracking-[0.2em] font-bold uppercase mb-4">THE QUESTION IS:</div>
        <div className="text-2xl md:text-3xl font-outfit font-bold text-white tracking-wide mb-16">&quot;What is the agent allowed to do?&quot;</div>
        
        {/* Connection flow down to Sentinel Answer */}
        <div className="flex flex-col items-center">
           <div className="text-[9px] text-blue-500/50 font-bold tracking-[0.3em] uppercase mb-4">AI AGENT</div>
           <div className="w-[1px] h-12 bg-gradient-to-b from-blue-900/50 to-blue-500" />
           <div className="text-[9px] text-blue-400 font-bold tracking-[0.3em] uppercase my-4">EXPANDING ACTION SURFACE</div>
           <div className="w-[1px] h-12 bg-gradient-to-b from-blue-500 to-blue-500 shadow-[0_0_10px_rgba(59,130,246,0.5)]" />
           <div className="text-[9px] text-blue-300 font-bold tracking-[0.3em] uppercase my-4">SECURITY BOUNDARY</div>
           <div className="w-[1px] h-12 bg-gradient-to-b from-blue-500 to-white shadow-[0_0_15px_rgba(255,255,255,0.8)]" />
           <div className="text-xs text-white font-bold tracking-[0.4em] uppercase my-4 font-outfit">SENTINEL</div>
           <div className="w-[1px] h-12 bg-white" />
           <div className="text-[9px] text-zinc-400 font-bold tracking-[0.3em] uppercase mt-4">CONTROLLED ACTION</div>
        </div>
      </div>

    </section>
  );
}
