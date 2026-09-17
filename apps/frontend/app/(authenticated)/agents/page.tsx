'use client';
import { useEffect, useState } from 'react';
import { listAgents, createAgent, type Agent, type AgentCreate } from '@/lib/api';
import { Bot, Plus, AlertCircle, X } from 'lucide-react';
import Link from 'next/link';
import clsx from 'clsx';

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    active: 'bg-emerald-900/60 text-emerald-300 border border-emerald-800',
    inactive: 'bg-zinc-800 text-zinc-400 border border-zinc-700',
    disabled: 'bg-red-900/60 text-red-300 border border-red-800',
  };
  return <span className={clsx('badge', map[status] || 'bg-zinc-800 text-zinc-400')}>{status}</span>;
}

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [modal, setModal] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState<AgentCreate>({ name: '', environment: 'development' });
  const [formError, setFormError] = useState('');

  async function load() {
    try {
      setAgents(await listAgents());
    } catch (e: unknown) {
      const err = e as { message?: string };
      setError(err?.message || 'Failed to load agents.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setFormError('');
    if (!form.name.trim()) { setFormError('Name is required.'); return; }
    setCreating(true);
    try {
      const agent = await createAgent(form);
      setAgents(prev => [agent, ...prev]);
      setModal(false);
      setForm({ name: '', environment: 'development' });
    } catch (e: unknown) {
      const err = e as { message?: string };
      setFormError(err?.message || 'Failed to create agent.');
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="max-w-5xl mx-auto space-y-5">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white">Agents</h1>
          <p className="text-sm text-zinc-500 mt-0.5">AI agents connected to SENTINEL</p>
        </div>
        <button onClick={() => setModal(true)} className="sentinel-btn-primary" id="register-agent-btn">
          <Plus size={15} /> Register Agent
        </button>
      </div>

      {error && (
        <div className="sentinel-card p-4 border-red-800 bg-red-950/30 flex items-start gap-2">
          <AlertCircle size={15} className="text-red-400 shrink-0 mt-0.5" />
          <p className="text-sm text-red-300">{error}</p>
        </div>
      )}

      <div className="sentinel-card overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-sm text-zinc-600">Loading agents…</div>
        ) : agents.length === 0 ? (
          <div className="p-12 text-center">
            <Bot size={40} className="text-zinc-700 mx-auto mb-3" />
            <p className="text-zinc-400 font-medium">No agents registered yet</p>
            <p className="text-sm text-zinc-600 mt-1">Register your first AI agent to start enforcing security policies.</p>
            <button onClick={() => setModal(true)} className="sentinel-btn-primary mt-4">
              <Plus size={15} /> Register Agent
            </button>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-zinc-500 border-b border-zinc-800">
                <th className="px-4 py-3 text-left font-medium">Name</th>
                <th className="px-4 py-3 text-left font-medium hidden md:table-cell">Environment</th>
                <th className="px-4 py-3 text-left font-medium">Status</th>
                <th className="px-4 py-3 text-left font-medium hidden lg:table-cell">Provider</th>
                <th className="px-4 py-3 text-left font-medium hidden lg:table-cell">Created</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/50">
              {agents.map(a => (
                <tr key={a.id} className="table-row-hover">
                  <td className="px-4 py-3">
                    <div className="font-medium text-zinc-200">{a.name}</div>
                    <div className="text-xs text-zinc-600 font-mono mt-0.5">{a.id.slice(0, 8)}…</div>
                  </td>
                  <td className="px-4 py-3 hidden md:table-cell">
                    <span className="badge bg-zinc-800 text-zinc-400 border border-zinc-700">{a.environment}</span>
                  </td>
                  <td className="px-4 py-3"><StatusBadge status={a.status} /></td>
                  <td className="px-4 py-3 text-zinc-500 hidden lg:table-cell">{a.provider || '—'}</td>
                  <td className="px-4 py-3 text-zinc-500 hidden lg:table-cell text-xs">{new Date(a.created_at).toLocaleDateString()}</td>
                  <td className="px-4 py-3 text-right">
                    <Link href={`/agents/${a.id}`} className="text-xs text-indigo-400 hover:text-indigo-300">View →</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Create modal */}
      {modal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70" role="dialog" aria-modal="true" aria-label="Register Agent">
          <div className="sentinel-card w-full max-w-md p-6">
            <div className="flex items-center justify-between mb-5">
              <h2 className="font-semibold text-white">Register Agent</h2>
              <button onClick={() => setModal(false)} className="text-zinc-500 hover:text-zinc-300"><X size={18} /></button>
            </div>

            {formError && (
              <div className="flex items-start gap-2 bg-red-950/60 border border-red-800 rounded-lg p-3 mb-4">
                <AlertCircle size={13} className="text-red-400 shrink-0 mt-0.5" />
                <span className="text-xs text-red-300">{formError}</span>
              </div>
            )}

            <form onSubmit={handleCreate} className="space-y-4" id="create-agent-form">
              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1.5">Agent Name <span className="text-red-400">*</span></label>
                <input className="sentinel-input" placeholder="e.g. Customer Support Agent" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1.5">Description</label>
                <input className="sentinel-input" placeholder="Optional description" value={form.description || ''} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} />
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1.5">Environment</label>
                <select className="sentinel-input" value={form.environment} onChange={e => setForm(f => ({ ...f, environment: e.target.value }))}>
                  <option value="development">Development</option>
                  <option value="staging">Staging</option>
                  <option value="production">Production</option>
                </select>
              </div>
              <div className="flex gap-2 pt-1">
                <button type="button" onClick={() => setModal(false)} className="sentinel-btn-secondary flex-1">Cancel</button>
                <button type="submit" className="sentinel-btn-primary flex-1" disabled={creating} id="submit-create-agent">
                  {creating ? 'Registering…' : 'Register Agent'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
