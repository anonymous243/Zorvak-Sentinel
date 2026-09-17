'use client';
import { useEffect, useState } from 'react';
import { listAgents, listPolicies, type Agent, type Policy } from '@/lib/api';
import { Bot, FileText, AlertTriangle, Activity, Shield, TrendingUp, ArrowRight } from 'lucide-react';
import Link from 'next/link';
import clsx from 'clsx';

function MetricCard({ label, value, icon: Icon, color, href }: {
  label: string; value: string | number; icon: React.ElementType; color: string; href: string;
}) {
  return (
    <Link href={href} className="sentinel-card p-4 flex items-center gap-4 hover:border-zinc-700 transition-colors group">
      <div className={clsx('w-10 h-10 rounded-lg flex items-center justify-center shrink-0', color)}>
        <Icon size={18} className="text-white" />
      </div>
      <div className="min-w-0">
        <div className="text-2xl font-bold text-white">{value}</div>
        <div className="text-xs text-zinc-500">{label}</div>
      </div>
      <ArrowRight size={14} className="text-zinc-700 group-hover:text-zinc-400 ml-auto transition-colors" />
    </Link>
  );
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    active: 'bg-emerald-900/60 text-emerald-300 border border-emerald-800',
    inactive: 'bg-zinc-800 text-zinc-400 border border-zinc-700',
    disabled: 'bg-red-900/60 text-red-300 border border-red-800',
    suspended: 'bg-amber-900/60 text-amber-300 border border-amber-800',
  };
  return <span className={clsx('badge', map[status] || 'bg-zinc-800 text-zinc-400 border border-zinc-700')}>{status}</span>;
}

function EffectBadge({ effect }: { effect: string }) {
  return (
    <span className={clsx('badge', effect === 'allow'
      ? 'bg-emerald-900/60 text-emerald-300 border border-emerald-800'
      : 'bg-red-900/60 text-red-300 border border-red-800'
    )}>
      {effect.toUpperCase()}
    </span>
  );
}

export default function DashboardPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    async function load() {
      try {
        const [a, p] = await Promise.all([listAgents(), listPolicies()]);
        setAgents(a);
        setPolicies(p);
      } catch (e: unknown) {
        const err = e as { message?: string };
        setError(err?.message || 'Failed to load dashboard data.');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const activeAgents = agents.filter(a => a.status === 'active').length;
  const activePolicies = policies.filter(p => p.enabled).length;
  const denyPolicies = policies.filter(p => p.effect === 'deny').length;

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white">Security Overview</h1>
          <p className="text-sm text-zinc-500 mt-0.5">Real-time status of your AI agent security posture</p>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-emerald-400 bg-emerald-950/60 border border-emerald-900 rounded-full px-3 py-1">
          <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          SENTINEL Active
        </div>
      </div>

      {error && (
        <div className="sentinel-card p-4 border-red-800 bg-red-950/30">
          <p className="text-sm text-red-300">{error}</p>
        </div>
      )}

      {/* Metrics */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <MetricCard label="Protected Agents" value={loading ? '—' : activeAgents} icon={Bot} color="bg-indigo-600" href="/agents" />
        <MetricCard label="Active Policies" value={loading ? '—' : activePolicies} icon={FileText} color="bg-blue-600" href="/policies" />
        <MetricCard label="Deny Rules" value={loading ? '—' : denyPolicies} icon={Shield} color="bg-red-700" href="/policies" />
        <MetricCard label="Total Agents" value={loading ? '—' : agents.length} icon={TrendingUp} color="bg-violet-600" href="/agents" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Agents table */}
        <div className="sentinel-card overflow-hidden">
          <div className="px-4 py-3 border-b border-zinc-800 flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-medium text-white">
              <Bot size={14} className="text-indigo-400" /> Agents
            </div>
            <Link href="/agents" className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1">
              View all <ArrowRight size={12} />
            </Link>
          </div>
          {loading ? (
            <div className="p-8 text-center text-sm text-zinc-600">Loading…</div>
          ) : agents.length === 0 ? (
            <div className="p-8 text-center">
              <Bot size={32} className="text-zinc-700 mx-auto mb-2" />
              <p className="text-sm text-zinc-500">No agents connected yet.</p>
              <Link href="/agents" className="text-xs text-indigo-400 mt-1 inline-block hover:underline">Connect your first agent →</Link>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs text-zinc-500 border-b border-zinc-800">
                  <th className="px-4 py-2 text-left font-medium">Name</th>
                  <th className="px-4 py-2 text-left font-medium">Environment</th>
                  <th className="px-4 py-2 text-left font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/50">
                {agents.slice(0, 6).map(a => (
                  <tr key={a.id} className="table-row-hover">
                    <td className="px-4 py-2.5">
                      <Link href={`/agents/${a.id}`} className="text-zinc-200 hover:text-indigo-300 font-medium truncate block max-w-[140px]">{a.name}</Link>
                    </td>
                    <td className="px-4 py-2.5"><span className="badge bg-zinc-800 text-zinc-400 border border-zinc-700">{a.environment}</span></td>
                    <td className="px-4 py-2.5"><StatusBadge status={a.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Policies table */}
        <div className="sentinel-card overflow-hidden">
          <div className="px-4 py-3 border-b border-zinc-800 flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-medium text-white">
              <FileText size={14} className="text-blue-400" /> Policies
            </div>
            <Link href="/policies" className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1">
              View all <ArrowRight size={12} />
            </Link>
          </div>
          {loading ? (
            <div className="p-8 text-center text-sm text-zinc-600">Loading…</div>
          ) : policies.length === 0 ? (
            <div className="p-8 text-center">
              <FileText size={32} className="text-zinc-700 mx-auto mb-2" />
              <p className="text-sm text-zinc-500">No policies defined yet.</p>
              <Link href="/policies" className="text-xs text-indigo-400 mt-1 inline-block hover:underline">Create your first policy →</Link>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs text-zinc-500 border-b border-zinc-800">
                  <th className="px-4 py-2 text-left font-medium">Name</th>
                  <th className="px-4 py-2 text-left font-medium">Effect</th>
                  <th className="px-4 py-2 text-left font-medium">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/50">
                {policies.slice(0, 6).map(p => (
                  <tr key={p.id} className="table-row-hover">
                    <td className="px-4 py-2.5">
                      <Link href={`/policies/${p.id}`} className="text-zinc-200 hover:text-indigo-300 font-medium truncate block max-w-[130px]">{p.name}</Link>
                    </td>
                    <td className="px-4 py-2.5"><EffectBadge effect={p.effect} /></td>
                    <td className="px-4 py-2.5 text-zinc-500 font-mono text-xs truncate max-w-[120px]">{p.action}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Security posture bar */}
      <div className="sentinel-card p-4">
        <div className="flex items-center gap-2 mb-3">
          <Shield size={14} className="text-indigo-400" />
          <span className="text-sm font-medium text-white">Security Posture</span>
        </div>
        <div className="grid grid-cols-3 gap-4 text-center">
          {[
            { label: 'ALLOW Rules', value: policies.filter(p => p.effect === 'allow').length, color: 'text-emerald-400' },
            { label: 'DENY Rules', value: denyPolicies, color: 'text-red-400' },
            { label: 'Active Agents', value: activeAgents, color: 'text-indigo-400' },
          ].map(({ label, value, color }) => (
            <div key={label}>
              <div className={clsx('text-2xl font-bold', color)}>{loading ? '—' : value}</div>
              <div className="text-xs text-zinc-600 mt-0.5">{label}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
