'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth-context';
import {
  Shield, LayoutDashboard, Bot, FileText, Wrench, Activity,
  AlertTriangle, Search, BarChart3, Settings, LogOut,
  ChevronRight, Menu, X, Layers
} from 'lucide-react';
import clsx from 'clsx';

const NAV = [
  { href: '/dashboard', label: 'Overview', icon: LayoutDashboard },
  { href: '/agents', label: 'Agents', icon: Bot },
  { href: '/policies', label: 'Policies', icon: FileText },
  { href: '/capabilities', label: 'Capabilities', icon: Layers },
  { href: '/activity', label: 'Activity', icon: Activity },
  { href: '/incidents', label: 'Incidents', icon: AlertTriangle },
  { href: '/investigations', label: 'Investigations', icon: Search },
  { href: '/analytics', label: 'Analytics', icon: BarChart3 },
  { href: '/settings', label: 'Settings', icon: Settings },
];

export default function AppShell({ children }: { children: React.ReactNode }) {
  const { user, organizations, activeTenantId, setActiveTenant, logout } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);

  // user check is handled in AuthProvider now (which redirects if no user).
  if (!user) return null;

  return (
    <div className="flex h-screen overflow-hidden bg-zinc-950">
      {/* Sidebar */}
      <aside className={clsx(
        'fixed inset-y-0 left-0 z-50 w-60 bg-zinc-900 border-r border-zinc-800 flex flex-col transition-transform duration-200',
        'md:relative md:translate-x-0',
        open ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
      )}>
        {/* Brand */}
        <div className="flex items-center gap-2.5 px-4 py-4 border-b border-zinc-800">
          <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center shrink-0">
            <Shield size={16} className="text-white" />
          </div>
          <div className="min-w-0">
            <div className="text-sm font-bold text-white truncate">SENTINEL</div>
            <div className="text-[10px] text-zinc-500 truncate">AI Security Control Plane</div>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto px-2 py-3 space-y-0.5">
          {NAV.map(({ href, label, icon: Icon }) => {
            const active = pathname === href || pathname.startsWith(href + '/');
            return (
              <Link
                key={href}
                href={href}
                onClick={() => setOpen(false)}
                className={clsx(
                  'flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors',
                  active
                    ? 'bg-indigo-600/20 text-indigo-300 font-medium'
                    : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800'
                )}
              >
                <Icon size={15} />
                {label}
              </Link>
            );
          })}
        </nav>

        {/* User */}
        <div className="px-2 py-3 border-t border-zinc-800">
          <div className="flex flex-col gap-2 px-3 py-2">
            {organizations.length > 0 && (
              <select
                value={activeTenantId || ''}
                onChange={(e) => setActiveTenant(e.target.value)}
                className="w-full bg-zinc-950 border border-zinc-800 text-xs text-white rounded p-1"
              >
                {organizations.map(org => (
                  <option key={org.id} value={org.id}>{org.name}</option>
                ))}
              </select>
            )}
            
            <div className="flex items-center gap-2 pt-2">
              <div className="w-6 h-6 bg-indigo-700 rounded-full flex items-center justify-center shrink-0">
                <span className="text-[10px] font-bold text-white">{user.name.charAt(0).toUpperCase()}</span>
              </div>
              <div className="min-w-0 flex-1">
                <div className="text-xs text-zinc-300 truncate font-medium">{user.name}</div>
                <div className="text-[10px] text-zinc-600 truncate">{user.email}</div>
              </div>
              <button onClick={logout} className="text-zinc-500 hover:text-red-400 transition-colors" aria-label="Sign out" id="logout-btn">
                <LogOut size={14} />
              </button>
            </div>
          </div>
        </div>
      </aside>

      {/* Mobile overlay */}
      {open && <div className="fixed inset-0 z-40 bg-black/50 md:hidden" onClick={() => setOpen(false)} />}

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top bar */}
        <header className="h-12 flex items-center gap-3 px-4 border-b border-zinc-800 bg-zinc-950 shrink-0">
          <button className="md:hidden text-zinc-400" onClick={() => setOpen(o => !o)} aria-label="Toggle menu">
            {open ? <X size={18} /> : <Menu size={18} />}
          </button>
          {/* Breadcrumb */}
          <div className="flex items-center gap-1 text-xs text-zinc-500 min-w-0">
            <span>SENTINEL</span>
            <ChevronRight size={12} />
            <span className="text-zinc-300 truncate capitalize">
              {pathname.split('/').filter(Boolean).join(' / ') || 'Overview'}
            </span>
          </div>
          <div className="ml-auto flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" title="API connected" />
            <span className="text-xs text-zinc-600">Live</span>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-4 md:p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
