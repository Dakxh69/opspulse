import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Activity,
  AlertOctagon,
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Clock,
  RefreshCw,
  Server,
  ShieldAlert,
} from 'lucide-react';
import { api } from '../services/api';
import { Agent, Incident } from '../types';

export const OverviewPage: React.FC = () => {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<Date>(new Date());

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [agentsData, incidentsData] = await Promise.all([
        api.getAgents().catch(() => []),
        api.getIncidents({ limit: 10 }).catch(() => ({ items: [], total: 0, page: 1, limit: 10 })),
      ]);
      setAgents(agentsData);
      setIncidents(incidentsData.items || []);
      setLastRefreshed(new Date());
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load telemetry overview');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 10000); // 10s live polling
    return () => clearInterval(interval);
  }, []);

  const onlineAgents = agents.filter((a) => a.status === 'ONLINE').length;
  const degradedAgents = agents.filter((a) => a.status === 'DEGRADED').length;
  const offlineAgents = agents.filter((a) => a.status === 'OFFLINE').length;

  const activeIncidents = incidents.filter(
    (i) => i.status === 'OPEN' || i.status === 'ACKNOWLEDGED' || i.status === 'INVESTIGATING'
  );
  const criticalIncidents = activeIncidents.filter((i) => i.severity === 'CRITICAL').length;

  return (
    <div className="space-y-6">
      {/* Page Title & Refresh */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white">System Overview</h2>
          <p className="text-sm text-slate-400">
            Real-time fleet health, active operational breaches, and ingestion pipeline status.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-xs text-slate-400 flex items-center gap-1.5">
            <Clock className="h-3.5 w-3.5 text-slate-500" />
            Updated {lastRefreshed.toLocaleTimeString()}
          </span>
          <button
            onClick={loadData}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin text-sky-400' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm flex items-center gap-3">
          <AlertOctagon className="h-5 w-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Top Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Agents */}
        <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Monitored Agents</span>
            <div className="p-2 rounded-lg bg-sky-500/10 text-sky-400 border border-sky-500/20">
              <Server className="h-4 w-4" />
            </div>
          </div>
          <p className="text-3xl font-bold text-white mt-2">{agents.length}</p>
          <div className="flex items-center gap-3 mt-3 text-xs">
            <span className="text-emerald-400 flex items-center gap-1">
              <span className="h-2 w-2 rounded-full bg-emerald-400"></span> {onlineAgents} Online
            </span>
            {degradedAgents > 0 && (
              <span className="text-amber-400 flex items-center gap-1">
                <span className="h-2 w-2 rounded-full bg-amber-400"></span> {degradedAgents} Degraded
              </span>
            )}
            {offlineAgents > 0 && (
              <span className="text-red-400 flex items-center gap-1">
                <span className="h-2 w-2 rounded-full bg-red-400"></span> {offlineAgents} Offline
              </span>
            )}
          </div>
        </div>

        {/* Active Incidents */}
        <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Active Incidents</span>
            <div className="p-2 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20">
              <AlertTriangle className="h-4 w-4" />
            </div>
          </div>
          <p className="text-3xl font-bold text-white mt-2">{activeIncidents.length}</p>
          <p className="text-xs text-slate-400 mt-3">
            {activeIncidents.length === 0 ? 'All metric thresholds nominal' : 'Awaiting operator triage'}
          </p>
        </div>

        {/* Critical Alerts */}
        <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Critical Breaches</span>
            <div className="p-2 rounded-lg bg-red-500/10 text-red-400 border border-red-500/20">
              <ShieldAlert className="h-4 w-4" />
            </div>
          </div>
          <p className="text-3xl font-bold text-white mt-2">{criticalIncidents}</p>
          <p className="text-xs text-slate-400 mt-3">
            {criticalIncidents > 0 ? 'Immediate resolution required' : 'Zero critical conditions'}
          </p>
        </div>

        {/* Ingestion Health */}
        <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Telemetry Pipeline</span>
            <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <Activity className="h-4 w-4" />
            </div>
          </div>
          <p className="text-lg font-bold text-emerald-400 mt-2 flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5" /> Operational
          </p>
          <p className="text-xs text-slate-400 mt-3">FastAPI • Redis 7 • Celery Worker</p>
        </div>
      </div>

      {/* Recent Incidents Table */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 backdrop-blur-sm shadow-sm overflow-hidden">
        <div className="p-5 border-b border-slate-800 flex items-center justify-between">
          <div>
            <h3 className="text-base font-semibold text-white">Recent Incident Activity</h3>
            <p className="text-xs text-slate-400">Live operational alerts generated by the evaluation engine.</p>
          </div>
          <Link
            to="/incidents"
            className="text-xs text-sky-400 hover:text-sky-300 font-medium flex items-center gap-1 transition"
          >
            View all incidents <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>

        {incidents.length === 0 ? (
          <div className="p-12 text-center">
            <CheckCircle2 className="h-10 w-10 text-emerald-500/40 mx-auto mb-3" />
            <h4 className="text-sm font-semibold text-slate-300">No Incidents Reported</h4>
            <p className="text-xs text-slate-500 mt-1">All monitored hosts are reporting healthy telemetry.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/60 text-slate-400 border-b border-slate-800 font-medium">
                <tr>
                  <th className="px-5 py-3">Severity</th>
                  <th className="px-5 py-3">Incident Title</th>
                  <th className="px-5 py-3">Status</th>
                  <th className="px-5 py-3">Detected</th>
                  <th className="px-5 py-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {incidents.slice(0, 5).map((inc) => (
                  <tr key={inc.id} className="hover:bg-slate-800/30 transition">
                    <td className="px-5 py-3">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold border ${
                          inc.severity === 'CRITICAL'
                            ? 'bg-red-500/10 text-red-400 border-red-500/30'
                            : 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                        }`}
                      >
                        {inc.severity}
                      </span>
                    </td>
                    <td className="px-5 py-3">
                      <div className="font-medium text-slate-200">{inc.title}</div>
                      <div className="text-slate-500 truncate max-w-md">{inc.description}</div>
                    </td>
                    <td className="px-5 py-3">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium border ${
                          inc.status === 'OPEN'
                            ? 'bg-sky-500/10 text-sky-400 border-sky-500/20'
                            : inc.status === 'ACKNOWLEDGED'
                            ? 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20'
                            : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                        }`}
                      >
                        {inc.status}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-slate-400">
                      {new Date(inc.first_detected_at).toLocaleTimeString([], {
                        hour: '2-digit',
                        minute: '2-digit',
                        second: '2-digit',
                      })}
                    </td>
                    <td className="px-5 py-3 text-right">
                      <Link
                        to={`/incidents`}
                        className="text-sky-400 hover:text-sky-300 font-medium text-xs hover:underline"
                      >
                        Manage
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
