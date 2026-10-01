import Link from "next/link";
import { Shield } from "lucide-react";

export default function PrivacyPage() {
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
        <h1 className="font-outfit text-4xl lg:text-5xl font-bold text-white mb-8">Privacy Policy</h1>
        <div className="space-y-8 text-zinc-400 leading-relaxed">
          <p>
            At ZORVAK STUDIOS, we take the privacy of your data and the operational security of your autonomous AI agents seriously. This Privacy Policy outlines our practices regarding data collection, usage, and protection when you use the ZORVAK SENTINEL Control Plane and Runtime Gateway.
          </p>
          
          <h2 className="font-outfit text-2xl font-bold text-white mt-12 mb-4">1. Information We Collect</h2>
          <p>
            When you create an organization on SENTINEL, we collect basic human administrator details (Name, Email). During runtime, our Gateway intercepts and logs agent action metadata, resource URIs, and identity payloads for the purpose of risk evaluation, authorization, and incident response. We do not inspect the payloads of encrypted end-to-end user data unless strictly required by policy definitions.
          </p>
          
          <h2 className="font-outfit text-2xl font-bold text-white mt-12 mb-4">2. How We Use Your Data</h2>
          <p>
            Metadata collected by the SENTINEL runtime is used exclusively for:
          </p>
          <ul className="list-disc pl-6 space-y-2 mt-4">
            <li>Enforcing cryptographic capability policies.</li>
            <li>Providing real-time audit logs and security analytics in your Control Plane.</li>
            <li>Detecting abnormal velocity, risk anomalies, and potential agent compromises.</li>
            <li>Improving the heuristic modeling of our threat detection engine.</li>
          </ul>

          <h2 className="font-outfit text-2xl font-bold text-white mt-12 mb-4">3. Data Retention and Deletion</h2>
          <p>
            Security telemetry, including incidents and evidence timelines, is retained for 90 days by default to aid in forensic investigation. Organization owners can configure custom data retention windows via the settings dashboard. You have the right to request full deletion of your organization's telemetry and metadata at any time.
          </p>
          
          <p className="text-sm mt-12 text-zinc-500">
            Last updated: September 2026. For privacy inquiries, contact privacy@zorvak.com.
          </p>
        </div>
      </main>
    </div>
  );
}
