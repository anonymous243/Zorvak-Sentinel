'use client';

import { getMe, logout as apiLogout } from '@/lib/api';
import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useRouter } from 'next/navigation';

export type User = {
  id: string;
  name: string;
  email: string;
};

export type Organization = {
  id: string;
  name: string;
  slug: string | null;
};

type AuthContext = {
  user: User | null;
  organizations: Organization[];
  activeTenantId: string | null;
  loading: boolean;
  logout: () => void;
  setActiveTenant: (id: string) => void;
};

const Ctx = createContext<AuthContext>({
  user: null,
  organizations: [],
  activeTenantId: null,
  loading: true,
  logout: () => {},
  setActiveTenant: () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [activeTenantId, setActiveTenantId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    getMe()
      .then((data: any) => {
        setUser(data.user);
        setOrganizations(data.organizations);
        if (data.organizations && data.organizations.length > 0) {
          const defaultOrg = data.organizations[0].id;
          setActiveTenantId(defaultOrg);
          if (typeof window !== 'undefined') {
            sessionStorage.setItem('sentinel_tenant_id', defaultOrg);
          }
        }
        setLoading(false);
      })
      .catch(() => {
        setLoading(false);
        router.push('/login');
      });
  }, [router]);

  function setActiveTenant(id: string) {
    setActiveTenantId(id);
    if (typeof window !== 'undefined') {
      sessionStorage.setItem('sentinel_tenant_id', id);
    }
  }

  async function logout() {
    try {
      await apiLogout();
    } catch (e) {
      // Ignore
    }
    setUser(null);
    setOrganizations([]);
    setActiveTenantId(null);
    if (typeof window !== 'undefined') {
      sessionStorage.removeItem('sentinel_tenant_id');
    }
    router.push('/login');
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-slate-500">Loading workspace...</div>
      </div>
    );
  }

  return <Ctx.Provider value={{ user, organizations, activeTenantId, logout, setActiveTenant }}>{children}</Ctx.Provider>;
}

export const useAuth = () => useContext(Ctx);
