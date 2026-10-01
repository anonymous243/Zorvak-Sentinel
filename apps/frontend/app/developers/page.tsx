import Link from "next/link";
import { Shield, Terminal, ArrowRight, Code } from "lucide-react";

export default function DevelopersPage() {
  return (
    <div className="min-h-screen bg-[#050505] text-zinc-300 font-sans">
      <nav className="border-b border-zinc-900 bg-[#050505]">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3 hover:opacity-80 transition-opacity">
            <div className="w-8 h-8 rounded relative overflow-hidden bg-zinc-900 border border-zinc-800 flex items-center justify-center">
              <Shield className="w-4 h-4 text-white" />
            </div>
            <span className="font-outfit font-bold text-white tracking-widest text-sm">ZORVAK SENTINEL</span>
          </Link>
          <div className="flex items-center gap-4">
            <Link href="/login" className="text-sm font-medium text-zinc-400 hover:text-white transition-colors">
              Sign In
            </Link>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-6 py-24">
        <div className="max-w-3xl mb-16">
          <h1 className="font-outfit text-5xl lg:text-6xl font-bold text-white mb-6 tracking-tight">
            Integrate security <br/> without rebuilding your agent.
          </h1>
          <p className="text-xl text-zinc-400 leading-relaxed">
            SENTINEL sits directly in the execution path. Your agents communicate with our Gateway, we evaluate the policy, and we either forward the request to your tools or block it immediately.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-start">
          <div className="space-y-8">
            <div className="bg-zinc-900/30 border border-zinc-800 p-6 rounded-2xl flex gap-4">
              <div className="w-8 h-8 rounded bg-indigo-500/20 text-indigo-400 flex items-center justify-center font-bold shrink-0">1</div>
              <div>
                <h3 className="font-bold text-white mb-2">Connect an Agent</h3>
                <p className="text-sm text-zinc-400">Generate Ed25519 keypairs and register your agent identity in the SENTINEL Control Plane.</p>
              </div>
            </div>
            
            <div className="bg-zinc-900/30 border border-zinc-800 p-6 rounded-2xl flex gap-4">
              <div className="w-8 h-8 rounded bg-indigo-500/20 text-indigo-400 flex items-center justify-center font-bold shrink-0">2</div>
              <div>
                <h3 className="font-bold text-white mb-2">Define Capabilities</h3>
                <p className="text-sm text-zinc-400">Map the specific API endpoints, database queries, and tools that your agent needs to operate.</p>
              </div>
            </div>
            
            <div className="bg-zinc-900/30 border border-zinc-800 p-6 rounded-2xl flex gap-4">
              <div className="w-8 h-8 rounded bg-indigo-500/20 text-indigo-400 flex items-center justify-center font-bold shrink-0">3</div>
              <div>
                <h3 className="font-bold text-white mb-2">Create Policy</h3>
                <p className="text-sm text-zinc-400">Write deterministic ALLOW/DENY rules that bind agents to capabilities with associated risk thresholds.</p>
              </div>
            </div>
          </div>

          <div className="bg-zinc-950 border border-zinc-800 rounded-2xl overflow-hidden shadow-2xl">
            <div className="bg-zinc-900 px-4 py-3 border-b border-zinc-800 flex items-center gap-2">
              <Code className="w-4 h-4 text-zinc-500" />
              <span className="text-xs font-mono text-zinc-400">example_request.py</span>
            </div>
            <div className="p-6 overflow-x-auto text-sm font-mono text-zinc-300">
              <pre className="text-emerald-400"># 1. Sign request with Agent Private Key</pre>
              <pre className="mt-2 text-zinc-300">payload = &#123;</pre>
              <pre className="text-zinc-300">  "agent_id": "agt_9f82...",</pre>
              <pre className="text-zinc-300">  "action": "refund.create",</pre>
              <pre className="text-zinc-300">  "resource": "cust_123"</pre>
              <pre className="text-zinc-300">&#125;</pre>
              <pre className="mt-4 text-emerald-400"># 2. Send through SENTINEL Gateway</pre>
              <pre className="mt-2 text-zinc-300">response = sentinel.execute(payload, signature)</pre>
              <pre className="mt-4 text-emerald-400"># 3. Handle Decision</pre>
              <pre className="mt-2 text-zinc-300">if response.decision == "DENIED":</pre>
              <pre className="text-zinc-300">    raise SecurityException(response.reason)</pre>
            </div>
          </div>
        </div>

        <div className="mt-24 text-center">
          <Link href="/signup" className="inline-flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-8 py-4 rounded-lg font-bold transition-all shadow-[0_0_20px_rgba(79,70,229,0.3)] tracking-wider">
            START BUILDING
          </Link>
        </div>
      </main>
    </div>
  );
}
