import Link from "next/link";
import { Shield } from "lucide-react";

export default function TermsPage() {
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

      <main className="max-w-3xl mx-auto px-6 py-24">
        <h1 className="font-outfit text-4xl lg:text-5xl font-bold text-white mb-8">Terms of Service</h1>
        <div className="space-y-8 text-zinc-400 leading-relaxed">
          <p>
            These Terms of Service ("Terms") govern your access to and use of the ZORVAK SENTINEL platform, operated by ZORVAK STUDIOS. By connecting an agent to our Runtime Gateway or creating a Control Plane organization, you agree to abide by these Terms.
          </p>
          
          <h2 className="font-outfit text-2xl font-bold text-white mt-12 mb-4">1. Use of the Platform</h2>
          <p>
            SENTINEL is provided as a security infrastructure layer. You agree to use the platform only for lawful purposes and to secure autonomous systems you own or have the explicit authorization to manage. Attempting to bypass, reverse engineer, or intentionally overload the policy engine or Gateway is strictly prohibited.
          </p>
          
          <h2 className="font-outfit text-2xl font-bold text-white mt-12 mb-4">2. Identity & Credentials</h2>
          <p>
            You are entirely responsible for the secure storage and lifecycle management of your Agent credentials and Ed25519 signing keys. ZORVAK STUDIOS is not liable for unauthorized actions taken by an agent if the underlying cryptographic identity has been compromised due to negligence.
          </p>

          <h2 className="font-outfit text-2xl font-bold text-white mt-12 mb-4">3. Limitation of Liability</h2>
          <p>
            While SENTINEL provides deterministic policy enforcement and risk evaluation, no system is entirely foolproof. We do not claim absolute security, guarantee protection against all zero-day vulnerabilities, or promise to stop every attack. The platform is provided "as is" and your reliance on it for mission-critical infrastructure is at your own risk.
          </p>
          
          <p className="text-sm mt-12 text-zinc-500">
            Last updated: September 2026. Legal inquiries: legal@zorvak.com.
          </p>
        </div>
      </main>
    </div>
  );
}
