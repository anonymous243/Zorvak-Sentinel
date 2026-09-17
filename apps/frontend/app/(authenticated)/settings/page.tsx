'use client';
import { useAuth } from '@/lib/auth-context';
export default function SettingsPage() {
  const { agentId, logout } = useAuth();
  return (
    <div className="max-w-2xl mx-auto space-y-5">
      <h1 className="text-xl font-bold text-white">Settings</h1>
      <div className="sentinel-card p-5 space-y-4">
        <h2 className="text-sm font-semibold text-white">Session</h2>
        <div>
          <div className="text-xs text-zinc-500 mb-1">Agent Principal</div>
          <div className="text-sm font-mono text-zinc-300 bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2 break-all">{agentId}</div>
        </div>
        <button onClick={logout} className="sentinel-btn-danger" id="settings-logout-btn">Sign out of SENTINEL</button>
      </div>
      <div className="sentinel-card p-5">
        <h2 className="text-sm font-semibold text-white mb-2">API Configuration</h2>
        <div>
          <div className="text-xs text-zinc-500 mb-1">API Endpoint</div>
          <div className="text-sm font-mono text-zinc-300 bg-zinc-950 border border-zinc-800 rounded-lg px-3 py-2">{process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}</div>
        </div>
      </div>
    </div>
  );
}
