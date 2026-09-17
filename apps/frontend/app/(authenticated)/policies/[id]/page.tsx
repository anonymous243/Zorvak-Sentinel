'use client';
import { useEffect, useState } from 'react';
import { getPolicyAudit, simulatePolicy, rollbackPolicy, getTenantId, type AuditRecord, type SimulationResult } from '@/lib/api';
import { ArrowLeft, AlertCircle, Clock, RotateCcw, Play, FileText, CheckCircle2, XCircle } from 'lucide-react';
import Link from 'next/link';
import { use } from 'react';
import clsx from 'clsx';

export default function PolicyDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [tab, setTab] = useState<'audit' | 'simulate' | 'rollback'>('audit');
  const [audit, setAudit] = useState<AuditRecord[]>([]);
  const [auditLoading, setAuditLoading] = useState(false);
  const [auditError, setAuditError] = useState('');

  // Simulation
  const [simForm, setSimForm] = useState({ agent_id: '', tool_id: '', action: '', resource: '' });
  const [simResult, setSimResult] = useState<SimulationResult | null>(null);
  const [simLoading, setSimLoading] = useState(false);
  const [simError, setSimError] = useState('');

  // Rollback
  const [rbTarget, setRbTarget] = useState('');
  const [rbResult, setRbResult] = useState<{ changed: boolean; reason: string } | null>(null);
  const [rbLoading, setRbLoading] = useState(false);
  const [rbError, setRbError] = useState('');
  const [rbConfirm, setRbConfirm] = useState(false);

  useEffect(() => {
    if (tab === 'audit') {
      setAuditLoading(true);
      getPolicyAudit(id, getTenantId())
        .then(setAudit)
        .catch((e: { message?: string }) => setAuditError(e?.message || 'Failed to load audit.'))
        .finally(() => setAuditLoading(false));
    }
  }, [id, tab]);

  async function handleSimulate(e: React.FormEvent) {
    e.preventDefault();
    setSimError(''); setSimResult(null);
    setSimLoading(true);
    try {
      const result = await simulatePolicy({ ...simForm, context: {} }, getTenantId());
      setSimResult(result);
    } catch (e: unknown) {
      const err = e as { message?: string };
      setSimError(err?.message || 'Simulation failed.');
    } finally {
      setSimLoading(false);
    }
  }

  async function handleRollback() {
    setRbError(''); setRbResult(null);
    setRbLoading(true);
    try {
      const r = await rollbackPolicy(id, { target_version_id: rbTarget }, getTenantId());
      setRbResult({ changed: r.changed, reason: r.reason });
      setRbConfirm(false);
    } catch (e: unknown) {
      const err = e as { message?: string };
      setRbError(err?.message || 'Rollback failed.');
    } finally {
      setRbLoading(false);
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-5">
      <Link href="/policies" className="flex items-center gap-1.5 text-sm text-zinc-500 hover:text-zinc-300">
        <ArrowLeft size={14} /> Back to Policies
      </Link>

      <div className="sentinel-card p-4">
        <div className="flex items-center gap-2 mb-1">
          <FileText size={16} className="text-indigo-400" />
          <h1 className="font-bold text-white">Policy Detail</h1>
        </div>
        <p className="text-xs font-mono text-zinc-600">{id}</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-zinc-800 pb-0">
        {(['audit', 'simulate', 'rollback'] as const).map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={clsx('px-4 py-2 text-sm font-medium capitalize rounded-t-lg transition-colors',
              tab === t ? 'text-indigo-300 border-b-2 border-indigo-500 bg-indigo-950/30' : 'text-zinc-500 hover:text-zinc-300'
            )}>
            {t === 'audit' ? '📋 Audit Log' : t === 'simulate' ? '▶ Simulate' : '↩ Rollback'}
          </button>
        ))}
      </div>

      {/* Audit Tab */}
      {tab === 'audit' && (
        <div className="sentinel-card overflow-hidden">
          {auditLoading ? (
            <div className="p-8 text-center text-sm text-zinc-600">Loading audit log…</div>
          ) : auditError ? (
            <div className="p-6 flex items-start gap-2">
              <AlertCircle size={14} className="text-red-400 mt-0.5 shrink-0" />
              <span className="text-sm text-red-300">{auditError}</span>
            </div>
          ) : audit.length === 0 ? (
            <div className="p-10 text-center">
              <Clock size={32} className="text-zinc-700 mx-auto mb-2" />
              <p className="text-sm text-zinc-500">No audit records yet.</p>
            </div>
          ) : (
            <div className="divide-y divide-zinc-800/50">
              {audit.map(r => (
                <div key={r.id} className="px-4 py-3 text-sm">
                  <div className="flex items-center gap-3 flex-wrap">
                    <span className="font-mono text-xs text-zinc-600">{new Date(r.occurred_at).toLocaleString()}</span>
                    <span className="badge bg-indigo-900/60 text-indigo-300 border border-indigo-800">{r.operation}</span>
                    {r.policy_version_id && <span className="text-xs text-zinc-500 font-mono">v:{r.policy_version_id.slice(0, 8)}</span>}
                  </div>
                  {r.before_state && <div className="mt-1 text-xs text-zinc-600">Before: <span className="text-zinc-400">{r.before_state.slice(0, 80)}</span></div>}
                  {r.after_state && <div className="text-xs text-zinc-600">After: <span className="text-zinc-400">{r.after_state.slice(0, 80)}</span></div>}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Simulate Tab */}
      {tab === 'simulate' && (
        <div className="sentinel-card p-5 space-y-4">
          <div className="flex items-start gap-2 bg-zinc-800/60 border border-zinc-700 rounded-lg p-3">
            <Play size={13} className="text-indigo-400 shrink-0 mt-0.5" />
            <p className="text-xs text-zinc-400">Simulation is <strong className="text-zinc-200">non-mutating</strong> — it does not execute the action or modify policy state.</p>
          </div>

          {simError && (
            <div className="flex items-start gap-2 bg-red-950/60 border border-red-800 rounded-lg p-3">
              <AlertCircle size={13} className="text-red-400 shrink-0 mt-0.5" />
              <span className="text-sm text-red-300">{simError}</span>
            </div>
          )}

          <form onSubmit={handleSimulate} className="grid grid-cols-2 gap-3" id="simulate-form">
            {[
              { key: 'agent_id', label: 'Agent ID', placeholder: 'UUID of agent' },
              { key: 'tool_id', label: 'Tool ID', placeholder: 'UUID of tool' },
              { key: 'action', label: 'Action', placeholder: 'e.g. database:write' },
              { key: 'resource', label: 'Resource', placeholder: 'e.g. prod/users' },
            ].map(({ key, label, placeholder }) => (
              <div key={key}>
                <label className="block text-xs font-medium text-zinc-400 mb-1">{label}</label>
                <input className="sentinel-input" placeholder={placeholder}
                  value={(simForm as Record<string, string>)[key]}
                  onChange={e => setSimForm(f => ({ ...f, [key]: e.target.value }))} />
              </div>
            ))}
            <div className="col-span-2">
              <button type="submit" className="sentinel-btn-primary" disabled={simLoading} id="run-simulation-btn">
                <Play size={14} /> {simLoading ? 'Running…' : 'Run Simulation'}
              </button>
            </div>
          </form>

          {simResult && (
            <div className={clsx('sentinel-card p-4 mt-2', simResult.effect === 'ALLOW' ? 'border-emerald-800 bg-emerald-950/20' : 'border-red-800 bg-red-950/20')}>
              <div className="flex items-center gap-2 mb-3">
                {simResult.effect === 'ALLOW'
                  ? <CheckCircle2 size={18} className="text-emerald-400" />
                  : <XCircle size={18} className="text-red-400" />}
                <span className={clsx('text-lg font-bold', simResult.effect === 'ALLOW' ? 'text-emerald-300' : 'text-red-300')}>{simResult.effect}</span>
                <span className="text-xs text-zinc-500 ml-auto">{simResult.simulation_ms.toFixed(2)}ms</span>
              </div>
              <div className="text-sm text-zinc-300">{simResult.reason}</div>
              {simResult.risk_level && <div className="text-xs text-zinc-500 mt-1">Risk: <span className="text-zinc-300">{simResult.risk_level}</span></div>}
            </div>
          )}
        </div>
      )}

      {/* Rollback Tab */}
      {tab === 'rollback' && (
        <div className="sentinel-card p-5 space-y-4">
          <div className="flex items-start gap-2 bg-amber-950/40 border border-amber-800 rounded-lg p-3">
            <RotateCcw size={13} className="text-amber-400 shrink-0 mt-0.5" />
            <p className="text-xs text-zinc-400">Rollback activates a previous policy version. This is an irreversible state change that will be recorded in the audit log.</p>
          </div>

          {rbError && (
            <div className="flex items-start gap-2 bg-red-950/60 border border-red-800 rounded-lg p-3">
              <AlertCircle size={13} className="text-red-400 shrink-0 mt-0.5" />
              <span className="text-sm text-red-300">{rbError}</span>
            </div>
          )}

          {rbResult && (
            <div className="sentinel-card p-4 border-emerald-800 bg-emerald-950/20">
              <div className="flex items-center gap-2">
                <CheckCircle2 size={16} className="text-emerald-400" />
                <span className="text-sm text-emerald-300">{rbResult.reason}</span>
              </div>
              {!rbResult.changed && <p className="text-xs text-zinc-500 mt-1">No change — the target version was already active.</p>}
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-zinc-400 mb-1.5">Target Version ID</label>
            <input className="sentinel-input" placeholder="Enter policy version UUID to restore" value={rbTarget} onChange={e => setRbTarget(e.target.value)} />
          </div>

          {!rbConfirm ? (
            <button onClick={() => setRbConfirm(true)} className="sentinel-btn-danger" disabled={!rbTarget.trim()} id="initiate-rollback-btn">
              <RotateCcw size={14} /> Initiate Rollback
            </button>
          ) : (
            <div className="sentinel-card p-4 border-red-800 bg-red-950/20">
              <p className="text-sm text-red-300 mb-3">
                <strong>Confirm rollback</strong> to version <span className="font-mono">{rbTarget.slice(0, 16)}…</span>?
                This will immediately change the active policy version and be recorded in the audit log.
              </p>
              <div className="flex gap-2">
                <button onClick={() => setRbConfirm(false)} className="sentinel-btn-secondary flex-1">Cancel</button>
                <button onClick={handleRollback} className="sentinel-btn-danger flex-1" disabled={rbLoading} id="confirm-rollback-btn">
                  {rbLoading ? 'Rolling back…' : 'Confirm Rollback'}
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
