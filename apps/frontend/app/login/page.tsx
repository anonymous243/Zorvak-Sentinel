'use client';
import { useState } from 'react';
import { useAuth } from '@/lib/auth-context';
import { Shield, Eye, EyeOff, AlertCircle } from 'lucide-react';
import { AuthProvider } from '@/lib/auth-context';

function LoginForm() {
  const { login } = useAuth();
  const [agentId, setAgentId] = useState('');
  const [secret, setSecret] = useState('');
  const [show, setShow] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    if (!agentId.trim() || !secret.trim()) {
      setError('Agent ID and credential are required.');
      return;
    }
    setLoading(true);
    try {
      // Verify credentials against backend /policies (requires auth)
      const encoded = btoa(`${agentId.trim()}:${secret.trim()}`);
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/policies`, {
        headers: {
          Authorization: `Basic ${encoded}`,
          'X-Tenant-ID': agentId.trim(),
        },
      });
      if (res.status === 401 || res.status === 403) {
        setError('Invalid credentials. Please check your Agent ID and secret.');
        return;
      }
      login(agentId.trim(), secret.trim());
    } catch {
      setError('Could not reach the SENTINEL API. Check your connection.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="flex items-center gap-3 mb-8">
          <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center">
            <Shield size={20} className="text-white" />
          </div>
          <div>
            <div className="font-bold text-white tracking-tight">ZORVAK SENTINEL</div>
            <div className="text-xs text-zinc-500">AI Security Control Plane</div>
          </div>
        </div>

        <div className="sentinel-card p-6">
          <h1 className="text-lg font-semibold text-white mb-1">Sign in</h1>
          <p className="text-sm text-zinc-400 mb-6">Authenticate with your agent credentials</p>

          {error && (
            <div className="flex items-start gap-2 bg-red-950/60 border border-red-800 rounded-lg p-3 mb-4">
              <AlertCircle size={15} className="text-red-400 shrink-0 mt-0.5" />
              <span className="text-sm text-red-300">{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4" id="login-form">
            <div>
              <label className="block text-xs font-medium text-zinc-400 mb-1.5" htmlFor="agent-id">
                Agent ID
              </label>
              <input
                id="agent-id"
                className="sentinel-input"
                placeholder="Enter your agent ID"
                value={agentId}
                onChange={e => setAgentId(e.target.value)}
                autoComplete="username"
                autoFocus
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-zinc-400 mb-1.5" htmlFor="credential">
                Credential Secret
              </label>
              <div className="relative">
                <input
                  id="credential"
                  type={show ? 'text' : 'password'}
                  className="sentinel-input pr-10"
                  placeholder="Enter your credential secret"
                  value={secret}
                  onChange={e => setSecret(e.target.value)}
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300"
                  onClick={() => setShow(s => !s)}
                  aria-label={show ? 'Hide credential' : 'Show credential'}
                >
                  {show ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              className="sentinel-btn-primary w-full mt-2"
              disabled={loading}
              id="sign-in-btn"
            >
              {loading ? 'Authenticating…' : 'Sign in'}
            </button>
          </form>
        </div>

        <p className="text-center text-xs text-zinc-600 mt-6">
          Credentials are authenticated against the SENTINEL API and never stored locally.
        </p>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <AuthProvider>
      <LoginForm />
    </AuthProvider>
  );
}
