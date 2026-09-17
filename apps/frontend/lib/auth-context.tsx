'use client';

import { saveCredentials, clearCredentials, isAuthenticated } from '@/lib/api';
import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useRouter } from 'next/navigation';

type AuthContext = {
  authenticated: boolean;
  agentId: string;
  tenantId: string;
  login: (agentId: string, secret: string) => void;
  logout: () => void;
};

const Ctx = createContext<AuthContext>({
  authenticated: false,
  agentId: '',
  tenantId: '',
  login: () => {},
  logout: () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [authenticated, setAuthenticated] = useState(false);
  const [agentId, setAgentId] = useState('');
  const [tenantId, setTenantId] = useState('');
  const router = useRouter();

  useEffect(() => {
    const creds = isAuthenticated();
    if (creds) {
      setAuthenticated(true);
      setAgentId(sessionStorage.getItem('sentinel_agent_id') || '');
      setTenantId(sessionStorage.getItem('sentinel_tenant_id') || '');
    }
  }, []);

  function login(id: string, secret: string) {
    saveCredentials(id, secret);
    setAuthenticated(true);
    setAgentId(id);
    setTenantId(id);
    router.push('/dashboard');
  }

  function logout() {
    clearCredentials();
    setAuthenticated(false);
    setAgentId('');
    setTenantId('');
    router.push('/login');
  }

  return <Ctx.Provider value={{ authenticated, agentId, tenantId, login, logout }}>{children}</Ctx.Provider>;
}

export const useAuth = () => useContext(Ctx);
