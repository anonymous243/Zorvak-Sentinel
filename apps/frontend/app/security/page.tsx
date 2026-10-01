import Link from "next/link";
import { Shield, Lock, ShieldCheck, Server } from "lucide-react";

export default function SecurityPage() {
  return (
    <div className="min-h-screen bg-[#050505] text-zinc-300 font-sans">
      <nav className="border-b border-zinc-900 bg-[#050505]">
        <div className="max-w-4xl mx-auto px-6 h-16 flex items-center">
          <Link href="/" className="flex items-center gap-3 hover:opacity-80 transition-opacity">
            <div className="w-8 h-8 rounded relative overflow-hidden bg-zinc-900 border border-zinc-800 flex items-center justify-center">
              <Shield className="w-4 h-4 text-white" />
            </div>
            <span className="font-outfit font-bold text-white tracking-widest text-sm">ZORVAK SENTINEL</span>
          </Link>
        </div>
      </nav>

      <main className="max-w-4xl mx-auto px-6 py-24">
        <h1 className="font-outfit text-4xl lg:text-5xl font-bold text-white mb-6">Our Security Architecture</h1>
        <p className="text-lg text-zinc-400 mb-12 max-w-2xl">
          ZORVAK SENTINEL was built by security engineers to secure the next generation of autonomous infrastructure. Here is how we protect your data and enforce policies deterministically.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-16">
          <div className="bg-zinc-900/30 border border-zinc-800 p-8 rounded-2xl">
            <Lock className="w-8 h-8 text-indigo-400 mb-6" />
            <h3 className="font-outfit text-xl font-bold text-white mb-4 uppercase">Cryptographic Identity</h3>
            <p className="text-sm text-zinc-400 leading-relaxed">
              Every request hitting our Runtime Gateway is verified via Ed25519 signatures. We never rely on static bearer tokens for critical execution paths, preventing replay attacks and token theft.
            </p>
          </div>
          
          <div className="bg-zinc-900/30 border border-zinc-800 p-8 rounded-2xl">
            <Server className="w-8 h-8 text-indigo-400 mb-6" />
            <h3 className="font-outfit text-xl font-bold text-white mb-4 uppercase">Strict Tenant Isolation</h3>
            <p className="text-sm text-zinc-400 leading-relaxed">
              Data, policies, and telemetry are rigidly segmented at the database and cache levels. Cross-tenant leakage is prevented via mandatory context-binding on every backend request.
            </p>
          </div>
          
          <div className="bg-zinc-900/30 border border-zinc-800 p-8 rounded-2xl">
            <ShieldCheck className="w-8 h-8 text-indigo-400 mb-6" />
            <h3 className="font-outfit text-xl font-bold text-white mb-4 uppercase">Fail-Closed Design</h3>
            <p className="text-sm text-zinc-400 leading-relaxed">
              If our risk engine encounters an unknown state, or if policy evaluation errors out, the action is automatically denied. We never fail open when securing autonomous behavior.
            </p>
          </div>
        </div>

        <h2 className="font-outfit text-2xl font-bold text-white mb-4">Vulnerability Disclosure</h2>
        <p className="text-zinc-400 leading-relaxed mb-6">
          We believe in working closely with the security research community. If you believe you have found a vulnerability in the ZORVAK SENTINEL control plane or runtime, please report it immediately to our security team. We will respond within 24 hours.
        </p>
        <a href="mailto:security@zorvak.com" className="inline-flex items-center gap-2 bg-zinc-900 hover:bg-zinc-800 border border-zinc-700 text-white px-6 py-3 rounded-lg font-medium transition-all">
          Contact Security Team
        </a>
      </main>
    </div>
  );
}
