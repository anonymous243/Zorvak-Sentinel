'use client';
import { useEffect, useState } from 'react';
import { listPolicies, createPolicy, getTenantId, type Policy, type PolicyCreate } from '@/lib/api';
import { FileText, Plus, AlertCircle, X, ChevronRight } from 'lucide-react';
import Link from 'next/link';
import clsx from 'clsx';

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

function EnabledBadge({ enabled }: { enabled: boolean }) {
  return (
    <span className={clsx('badge', enabled
      ? 'bg-indigo-900/60 text-indigo-300 border border-indigo-800'
      : 'bg-zinc-800 text-zinc-500 border border-zinc-700'
    )}>
      {enabled ? 'Active' : 'Disabled'}
    </span>
  );
}

export default function PoliciesPage() {
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [modal, setModal] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState<PolicyCreate>({ name: '', effect: 'allow', action: '', resource: '', priority: 100 });
  const [formError, setFormError] = useState('');
  const [filter, setFilter] = useState<'all' | 'allow' | 'deny'>('all');

  async function load() {
    try {
      setPolicies(await listPolicies());
    } catch (e: unknown) {
      const err = e as { message?: string };
      setError(err?.message || 'Failed to load policies.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setFormError('');
    if (!form.name.trim() || !form.action.trim() || !form.resource.trim()) {
      setFormError('Name, Action and Resource are required.');
      return;
    }
    setCreating(true);
    try {
      const policy = await createPolicy(form, getTenantId());
      setPolicies(prev => [policy, ...prev]);
      setModal(false);
      setForm({ name: '', effect: 'allow', action: '', resource: '', priority: 100 });
    } catch (e: unknown) {
      const err = e as { message?: string };
      setFormError(err?.message || 'Failed to create policy.');
    } finally {
      setCreating(false);
    }
  }

  const filtered = policies.filter(p =>
    filter === 'all' ? true : p.effect === filter
  );

  return (
    <div className="max-w-6xl mx-auto space-y-5">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-xl font-bold text-white">Policies</h1>
          <p className="text-sm text-zinc-500 mt-0.5">Security policies governing agent actions and resources</p>
        </div>
        <button onClick={() => setModal(true)} className="sentinel-btn-primary" id="create-policy-btn">
          <Plus size={15} /> Create Policy
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-1">
        {(['all', 'allow', 'deny'] as const).map(f => (
          <button key={f} onClick={() => setFilter(f)}
            className={clsx('px-3 py-1.5 text-xs rounded-lg font-medium transition-colors capitalize',
              filter === f ? 'bg-indigo-600 text-white' : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800'
            )}>
            {f === 'all' ? `All (${policies.length})` : f === 'allow' ? `Allow (${policies.filter(p => p.effect === 'allow').length})` : `Deny (${policies.filter(p => p.effect === 'deny').length})`}
          </button>
        ))}
      </div>

      {error && (
        <div className="sentinel-card p-4 border-red-800 bg-red-950/30 flex items-start gap-2">
          <AlertCircle size={15} className="text-red-400 shrink-0 mt-0.5" />
          <p className="text-sm text-red-300">{error}</p>
        </div>
      )}

      <div className="sentinel-card overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-sm text-zinc-600">Loading policies…</div>
        ) : filtered.length === 0 ? (
          <div className="p-12 text-center">
            <FileText size={40} className="text-zinc-700 mx-auto mb-3" />
            <p className="text-zinc-400 font-medium">No policies found</p>
            <p className="text-sm text-zinc-600 mt-1">Create your first security policy to start controlling agent behavior.</p>
            <button onClick={() => setModal(true)} className="sentinel-btn-primary mt-4"><Plus size={15} /> Create Policy</button>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-zinc-500 border-b border-zinc-800">
                <th className="px-4 py-3 text-left font-medium">Name</th>
                <th className="px-4 py-3 text-left font-medium">Effect</th>
                <th className="px-4 py-3 text-left font-medium hidden md:table-cell">Action</th>
                <th className="px-4 py-3 text-left font-medium hidden lg:table-cell">Resource</th>
                <th className="px-4 py-3 text-left font-medium hidden lg:table-cell">Priority</th>
                <th className="px-4 py-3 text-left font-medium">Status</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/50">
              {filtered.map(p => (
                <tr key={p.id} className="table-row-hover">
                  <td className="px-4 py-3">
                    <div className="font-medium text-zinc-200 truncate max-w-[160px]">{p.name}</div>
                    <div className="text-xs text-zinc-600 font-mono mt-0.5">{p.id.slice(0, 8)}…</div>
                  </td>
                  <td className="px-4 py-3"><EffectBadge effect={p.effect} /></td>
                  <td className="px-4 py-3 text-zinc-400 font-mono text-xs hidden md:table-cell truncate max-w-[120px]">{p.action}</td>
                  <td className="px-4 py-3 text-zinc-400 font-mono text-xs hidden lg:table-cell truncate max-w-[120px]">{p.resource}</td>
                  <td className="px-4 py-3 text-zinc-400 hidden lg:table-cell">{p.priority}</td>
                  <td className="px-4 py-3"><EnabledBadge enabled={p.enabled} /></td>
                  <td className="px-4 py-3 text-right">
                    <Link href={`/policies/${p.id}`} className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-0.5 justify-end">
                      View <ChevronRight size={12} />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Create modal */}
      {modal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70" role="dialog" aria-modal="true" aria-label="Create Policy">
          <div className="sentinel-card w-full max-w-md p-6 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-5">
              <h2 className="font-semibold text-white">Create Policy</h2>
              <button onClick={() => setModal(false)} className="text-zinc-500 hover:text-zinc-300"><X size={18} /></button>
            </div>

            {formError && (
              <div className="flex items-start gap-2 bg-red-950/60 border border-red-800 rounded-lg p-3 mb-4">
                <AlertCircle size={13} className="text-red-400 shrink-0 mt-0.5" />
                <span className="text-xs text-red-300">{formError}</span>
              </div>
            )}

            <form onSubmit={handleCreate} className="space-y-4" id="create-policy-form">
              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1.5">Policy Name <span className="text-red-400">*</span></label>
                <input className="sentinel-input" placeholder="e.g. Block Production Writes" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1.5">Effect <span className="text-red-400">*</span></label>
                <select className="sentinel-input" value={form.effect} onChange={e => setForm(f => ({ ...f, effect: e.target.value as 'allow' | 'deny' }))}>
                  <option value="allow">ALLOW</option>
                  <option value="deny">DENY</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1.5">Action <span className="text-red-400">*</span></label>
                <input className="sentinel-input" placeholder="e.g. database:write or *" value={form.action} onChange={e => setForm(f => ({ ...f, action: e.target.value }))} />
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1.5">Resource <span className="text-red-400">*</span></label>
                <input className="sentinel-input" placeholder="e.g. prod/* or *" value={form.resource} onChange={e => setForm(f => ({ ...f, resource: e.target.value }))} />
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1.5">Priority (0–9999)</label>
                <input type="number" className="sentinel-input" min={0} max={9999} value={form.priority} onChange={e => setForm(f => ({ ...f, priority: parseInt(e.target.value) || 100 }))} />
              </div>
              <div className="flex gap-2 pt-1">
                <button type="button" onClick={() => setModal(false)} className="sentinel-btn-secondary flex-1">Cancel</button>
                <button type="submit" className="sentinel-btn-primary flex-1" disabled={creating} id="submit-create-policy">
                  {creating ? 'Creating…' : 'Create Policy'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
