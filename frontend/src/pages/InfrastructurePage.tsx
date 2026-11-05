import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  AlertCircle,
  RefreshCw,
  Server,
} from 'lucide-react';
import { api } from '../services/api';
import { Agent, MetricSample } from '../types';

export const InfrastructurePage: React.FC = () => {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [latestMetrics, setLatestMetrics] = useState<Record<string, MetricSample | null>>({});
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadAgents = async () => {
    try {
      setLoading(true);
      setError(null);
      const list = await api.getAgents();
      setAgents(list);

      // Concurrently fetch latest metric sample for each agent
      const metricsMap: Record<string, MetricSample | null> = {};
      await Promise.all(
        list.map(async (ag) => {
          metricsMap[ag.id] = await api.getLatestMetric(ag.id);
        })
      );
      setLatestMetrics(metricsMap);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load infrastructure inventory');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAgents();
    const timer = setInterval(loadAgents, 15000);
    return () => clearInterval(timer);
  }, []);

  const formatRelativeTime = (isoString: string | null): string => {
    if (!isoString) return 'Never';
    const seconds = Math.floor((new Date().getTime() - new Date(isoString).getTime()) / 1000);
    if (seconds < 5) return 'Just now';
    if (seconds < 60) return `${seconds}s ago`;
    const mins = Math.floor(seconds / 60);
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    return `${hours}h ago`;
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white">Infrastructure</h2>
          <p className="text-sm text-slate-400">
            Registered monitoring agents, hardware specifications, and live health metrics.
          </p>
        </div>

        <button
          onClick={loadAgents}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin text-sky-400' : ''}`} />
          Refresh
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm flex items-center gap-3">
          <AlertCircle className="h-5 w-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Agents Listing Table */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/60 text-slate-400 border-b border-slate-800 font-medium">
              <tr>
                <th className="px-5 py-3">Host & Agent</th>
                <th className="px-5 py-3">Status</th>
                <th className="px-5 py-3">OS & Version</th>
                <th className="px-5 py-3">CPU Usage</th>
                <th className="px-5 py-3">RAM Usage</th>
                <th className="px-5 py-3">Last Heartbeat</th>
                <th className="px-5 py-3 text-right">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {agents.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-5 py-8 text-center text-slate-500">
                    No agents registered. Deploy the Ubuntu monitoring agent to begin ingestion.
                  </td>
                </tr>
              ) : (
                agents.map((ag) => {
                  const metric = latestMetrics[ag.id];
                  const cpu = metric ? metric.cpu_usage_percent.toFixed(1) : '—';
                  const mem = metric ? metric.memory_usage_percent.toFixed(1) : '—';

                  return (
                    <tr key={ag.id} className="hover:bg-slate-800/30 transition">
                      <td className="px-5 py-3.5">
                        <div className="flex items-center gap-2.5">
                          <Server className="h-4 w-4 text-sky-400 shrink-0" />
                          <div>
                            <div className="font-semibold text-slate-100">{ag.name || ag.hostname}</div>
                            <div className="text-[11px] text-slate-400 font-mono">{ag.hostname}</div>
                          </div>
                        </div>
                      </td>
                      <td className="px-5 py-3.5">
                        <span
                          className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-semibold border ${
                            ag.status === 'ONLINE'
                              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                              : ag.status === 'DEGRADED'
                              ? 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                              : 'bg-red-500/10 text-red-400 border-red-500/30'
                          }`}
                        >
                          <span
                            className={`h-1.5 w-1.5 rounded-full ${
                              ag.status === 'ONLINE'
                                ? 'bg-emerald-400 animate-pulse'
                                : ag.status === 'DEGRADED'
                                ? 'bg-amber-400'
                                : 'bg-red-400'
                            }`}
                          />
                          {ag.status}
                        </span>
                      </td>
                      <td className="px-5 py-3.5">
                        <div className="text-slate-300 font-medium">{ag.os_type || 'Linux'}</div>
                        <div className="text-[11px] text-slate-500">v{ag.agent_version || '0.1.0'}</div>
                      </td>
                      <td className="px-5 py-3.5">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-slate-200">{cpu}%</span>
                          {metric && (
                            <div className="w-16 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                              <div
                                className={`h-full ${
                                  metric.cpu_usage_percent > 80 ? 'bg-red-500' : 'bg-sky-400'
                                }`}
                                style={{ width: `${Math.min(100, metric.cpu_usage_percent)}%` }}
                              />
                            </div>
                          )}
                        </div>
                      </td>
                      <td className="px-5 py-3.5">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-slate-200">{mem}%</span>
                          {metric && (
                            <div className="w-16 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                              <div
                                className={`h-full ${
                                  metric.memory_usage_percent > 85 ? 'bg-amber-500' : 'bg-indigo-400'
                                }`}
                                style={{ width: `${Math.min(100, metric.memory_usage_percent)}%` }}
                              />
                            </div>
                          )}
                        </div>
                      </td>
                      <td className="px-5 py-3.5 text-slate-400 font-mono text-[11px]">
                        {formatRelativeTime(ag.last_heartbeat)}
                      </td>
                      <td className="px-5 py-3.5 text-right">
                        <Link
                          to={`/infrastructure/${ag.id}`}
                          className="px-2.5 py-1 text-[11px] font-medium rounded bg-sky-500/10 text-sky-400 hover:bg-sky-500/20 border border-sky-500/30 transition inline-block"
                        >
                          Inspect
                        </Link>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
