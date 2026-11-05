import React from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import {
  Activity,
  AlertTriangle,
  Bell,
  LayoutDashboard,
  Server,
  ShieldCheck,
  Radio,
} from 'lucide-react';

const navigation = [
  { name: 'Overview', href: '/', icon: LayoutDashboard },
  { name: 'Infrastructure', href: '/infrastructure', icon: Server },
  { name: 'Incidents', href: '/incidents', icon: AlertTriangle },
  { name: 'Alert Rules', href: '/alerts', icon: Bell },
  { name: 'Audit Logs', href: '/audit', icon: ShieldCheck },
];

export const DashboardLayout: React.FC = () => {
  return (
    <div className="flex h-screen bg-slate-950 text-slate-100 overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 flex flex-col border-r border-slate-800 bg-slate-900/60 backdrop-blur-md">
        <div className="flex items-center gap-3 px-6 h-16 border-b border-slate-800">
          <div className="h-9 w-9 rounded-lg bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-400">
            <Activity className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-base font-semibold tracking-tight text-white flex items-center gap-1.5">
              OpsPulse
              <span className="text-[10px] font-medium bg-sky-500/10 text-sky-400 border border-sky-500/20 px-1.5 py-0.5 rounded">
                MVP
              </span>
            </h1>
            <p className="text-xs text-slate-400">Host Telemetry & Alerting</p>
          </div>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {navigation.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.name}
                to={item.href}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-lg transition-colors ${
                    isActive
                      ? 'bg-sky-500/10 text-sky-400 border border-sky-500/20'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                  }`
                }
              >
                <Icon className="h-4 w-4 shrink-0" />
                {item.name}
              </NavLink>
            );
          })}
        </nav>

        <div className="p-4 border-t border-slate-800 text-xs text-slate-500 space-y-1">
          <div className="flex items-center gap-2 text-emerald-400">
            <Radio className="h-3 w-3 animate-pulse" />
            <span className="font-medium">Pipeline Active</span>
          </div>
          <p className="truncate">PostgreSQL 17 • Redis 7</p>
        </div>
      </aside>

      {/* Main Container */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="h-16 border-b border-slate-800 bg-slate-900/40 backdrop-blur-md flex items-center justify-between px-8">
          <div className="flex items-center gap-3">
            <span className="h-2.5 w-2.5 rounded-full bg-emerald-500 ring-4 ring-emerald-500/20"></span>
            <span className="text-sm font-medium text-slate-300">Environment: Localhost</span>
          </div>

          <div className="flex items-center gap-4">
            <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-sky-500/10 text-sky-400 border border-sky-500/20">
              OPERATOR
            </span>
            <div className="h-8 w-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-xs font-bold text-slate-200">
              OP
            </div>
          </div>
        </header>

        {/* Content Body */}
        <main className="flex-1 overflow-y-auto p-8 bg-gradient-to-b from-slate-950 to-slate-900">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
