'use client';
import { useEffect, useState } from 'react';
import { getAgent, type Agent } from '@/lib/api';
import { Bot, AlertCircle, ArrowLeft, Calendar, Activity } from 'lucide-react';
import Link from 'next/link';
import { use } from 'react';
import clsx from 'clsx';

export default function AgentDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [agent, setAgent] = useState<Agent | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    getAgent(id)
      .then(setAgent)
      .catch((e: { message?: string }) => setError(e?.message || 'Agent not found.'))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="p-12 text-center text-sm text-zinc-600">Loading…</div>;

  if (error || !agent) return (
    <div className="max-w-2xl mx-auto">
      <Link href="/agents" className="flex items-center gap-1.5 text-sm text-zinc-500 hover:text-zinc-300 mb-4">
        <ArrowLeft size={14} /> Back to Agents
      </Link>
      <div className="sentinel-card p-6 text-center">
        <AlertCircle size={32} className="text-red-400 mx-auto mb-2" />
        <p className="text-zinc-400">{error || 'Agent not found.'}</p>
      </div>
    </div>
  );

  const statusColor: Record<string, string> = {
    active: 'bg-emerald-900/60 text-emerald-300 border border-emerald-800',
    inactive: 'bg-zinc-800 text-zinc-400 border border-zinc-700',
    disabled: 'bg-red-900/60 text-red-300 border border-red-800',
  };

  return (
    <div className="max-w-3xl mx-auto space-y-5">
      <Link href="/agents" className="flex items-center gap-1.5 text-sm text-zinc-500 hover:text-zinc-300">
        <ArrowLeft size={14} /> Back to Agents
      </Link>

      {/* Header */}
      <div className="sentinel-card p-5">
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 bg-indigo-900/60 border border-indigo-800 rounded-xl flex items-center justify-center shrink-0">
            <Bot size={22} className="text-indigo-400" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-3 flex-wrap">
              <h1 className="text-lg font-bold text-white">{agent.name}</h1>
              <span className={clsx('badge', statusColor[agent.status] || 'bg-zinc-800 text-zinc-400')}>{agent.status}</span>
            </div>
            {agent.description && <p className="text-sm text-zinc-400 mt-1">{agent.description}</p>}
            <div className="text-xs font-mono text-zinc-600 mt-1">{agent.id}</div>
          </div>
        </div>
      </div>

      {/* Details grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        {[
          { label: 'Environment', value: agent.environment, icon: Activity },
          { label: 'Provider', value: agent.provider || 'None', icon: Bot },
          { label: 'External ID', value: agent.external_id || 'None', icon: Bot },
          { label: 'Created', value: new Date(agent.created_at).toLocaleString(), icon: Calendar },
          { label: 'Updated', value: new Date(agent.updated_at).toLocaleString(), icon: Calendar },
        ].map(({ label, value, icon: Icon }) => (
          <div key={label} className="sentinel-card p-3">
            <div className="flex items-center gap-1.5 text-xs text-zinc-500 mb-1">
              <Icon size={11} /> {label}
            </div>
            <div className="text-sm text-zinc-200 font-medium truncate">{value}</div>
          </div>
        ))}
      </div>

      {/* Integration instructions */}
      <div className="sentinel-card p-5">
        <h2 className="text-sm font-semibold text-white mb-3">Integration</h2>
        <p className="text-xs text-zinc-500 mb-3">Use these details to authenticate requests from this agent to SENTINEL.</p>
        <div className="bg-zinc-950 border border-zinc-800 rounded-lg p-4 font-mono text-xs text-zinc-300 space-y-1 overflow-x-auto">
          <div><span className="text-indigo-400">Authorization:</span> Basic {'{'}agent_id:credential_secret{'}'} (Base64)</div>
          <div><span className="text-indigo-400">X-Tenant-ID:</span> {agent.id}</div>
        </div>
        <p className="text-xs text-zinc-600 mt-2">
          ⚠️ Never expose credential secrets in frontend code, logs, or version control.
        </p>
      </div>
    </div>
  );
}
