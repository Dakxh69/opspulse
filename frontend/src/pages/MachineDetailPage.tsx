import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  Activity,
  ArrowLeft,
  HardDrive,
  Network,
  RefreshCw,
  Server,
} from 'lucide-react';
import {
  AreaChart,
  Area,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { api } from '../services/api';
import { Agent, MetricSample } from '../types';

export const MachineDetailPage: React.FC = () => {
  const { agentId } = useParams<{ agentId: string }>();
  const [agent, setAgent] = useState<Agent | null>(null);
  const [history, setHistory] = useState<MetricSample[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [timeRange, setTimeRange] = useState<number>(30); // minutes

  const loadData = async () => {
    if (!agentId) return;
    try {
      setLoading(true);
      setError(null);
      const [ag, metrics] = await Promise.all([
        api.getAgent(agentId),
        api.getMetricHistory(agentId, timeRange),
      ]);
      setAgent(ag);
      setHistory(metrics);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load machine metrics');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 10000);
    return () => clearInterval(interval);
  }, [agentId, timeRange]);

  const formattedChartData = history.map((h) => ({
    time: new Date(h.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    cpu: Number(h.cpu_usage_percent.toFixed(1)),
    memory: Number(h.memory_usage_percent.toFixed(1)),
    networkTx: h.networks && h.networks[0] ? Number((h.networks[0].bytes_sent_per_sec / 1024).toFixed(1)) : 0,
    networkRx: h.networks && h.networks[0] ? Number((h.networks[0].bytes_recv_per_sec / 1024).toFixed(1)) : 0,
  }));

  const latestSample = history[history.length - 1];

  return (
    <div className="space-y-6">
      {/* Navigation & Header */}
      <div>
        <Link
          to="/infrastructure"
          className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-400 hover:text-slate-200 transition mb-3"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> Back to Infrastructure
        </Link>

        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-xl bg-sky-500/10 text-sky-400 border border-sky-500/20">
              <Server className="h-6 w-6" />
            </div>
            <div>
              <h2 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
                {agent?.name || agent?.hostname || 'Host Details'}
                {agent && (
                  <span
                    className={`text-xs px-2 py-0.5 rounded font-semibold border ${
                      agent.status === 'ONLINE'
                        ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                        : 'bg-red-500/10 text-red-400 border-red-500/30'
                    }`}
                  >
                    {agent.status}
                  </span>
                )}
              </h2>
              <p className="text-xs text-slate-400 font-mono">
                ID: {agentId} • Hostname: {agent?.hostname}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Time range buttons */}
            <div className="flex items-center rounded-lg bg-slate-900 border border-slate-800 p-0.5">
              {[15, 30, 60, 120].map((mins) => (
                <button
                  key={mins}
                  onClick={() => setTimeRange(mins)}
                  className={`px-2.5 py-1 text-xs font-medium rounded-md transition ${
                    timeRange === mins
                      ? 'bg-sky-500/20 text-sky-400 border border-sky-500/30'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {mins >= 60 ? `${mins / 60}h` : `${mins}m`}
                </button>
              ))}
            </div>

            <button
              onClick={loadData}
              disabled={loading}
              className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition"
              title="Refresh telemetry"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin text-sky-400' : ''}`} />
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Grid of Metric Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* CPU Utilization Chart */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 backdrop-blur-sm">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-sky-400" />
              <h3 className="text-sm font-semibold text-white">CPU Utilization</h3>
            </div>
            <span className="text-xs font-mono text-sky-400 font-bold">
              {latestSample ? `${latestSample.cpu_usage_percent.toFixed(1)}%` : '—'}
            </span>
          </div>

          <div className="h-60 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={formattedChartData}>
                <defs>
                  <linearGradient id="cpuGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#38bdf8" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#38bdf8" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="time" stroke="#64748b" fontSize={11} />
                <YAxis domain={[0, 100]} stroke="#64748b" fontSize={11} unit="%" />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px' }}
                />
                <Area type="monotone" dataKey="cpu" stroke="#38bdf8" fillOpacity={1} fill="url(#cpuGradient)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Memory Utilization Chart */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 backdrop-blur-sm">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-indigo-400" />
              <h3 className="text-sm font-semibold text-white">Memory Utilization</h3>
            </div>
            <span className="text-xs font-mono text-indigo-400 font-bold">
              {latestSample ? `${latestSample.memory_usage_percent.toFixed(1)}%` : '—'}
            </span>
          </div>

          <div className="h-60 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={formattedChartData}>
                <defs>
                  <linearGradient id="memGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#818cf8" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#818cf8" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="time" stroke="#64748b" fontSize={11} />
                <YAxis domain={[0, 100]} stroke="#64748b" fontSize={11} unit="%" />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px' }}
                />
                <Area type="monotone" dataKey="memory" stroke="#818cf8" fillOpacity={1} fill="url(#memGradient)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Network Throughput Chart */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 backdrop-blur-sm">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Network className="h-4 w-4 text-emerald-400" />
              <h3 className="text-sm font-semibold text-white">Network Rate (KB/s)</h3>
            </div>
          </div>

          <div className="h-60 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={formattedChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="time" stroke="#64748b" fontSize={11} />
                <YAxis stroke="#64748b" fontSize={11} unit=" KB/s" />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px' }}
                />
                <Line type="monotone" dataKey="networkTx" stroke="#34d399" strokeWidth={2} dot={false} name="TX (Outbound)" />
                <Line type="monotone" dataKey="networkRx" stroke="#38bdf8" strokeWidth={2} dot={false} name="RX (Inbound)" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Disk Mounts & Capacity */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 backdrop-blur-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 mb-4">
              <HardDrive className="h-4 w-4 text-amber-400" />
              <h3 className="text-sm font-semibold text-white">Disk Filesystems</h3>
            </div>

            {latestSample && latestSample.disks && latestSample.disks.length > 0 ? (
              <div className="space-y-4">
                {latestSample.disks.map((d) => (
                  <div key={d.mount_point} className="space-y-1.5">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-mono font-medium text-slate-200">{d.mount_point}</span>
                      <span className="font-mono text-slate-400">
                        {d.usage_percent.toFixed(1)}% ({(d.used_bytes / 1e9).toFixed(1)} GB /{' '}
                        {(d.total_bytes / 1e9).toFixed(1)} GB)
                      </span>
                    </div>
                    <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className={`h-full ${
                          d.usage_percent > 85
                            ? 'bg-red-500'
                            : d.usage_percent > 70
                            ? 'bg-amber-500'
                            : 'bg-emerald-400'
                        }`}
                        style={{ width: `${Math.min(100, d.usage_percent)}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-500 py-6 text-center">
                No filesystem metrics recorded in current sample.
              </p>
            )}
          </div>

          <div className="mt-4 pt-4 border-t border-slate-800 text-xs text-slate-400">
            Filtering pseudo-filesystems (`tmpfs`, `devtmpfs`, `squashfs`) automatically.
          </div>
        </div>
      </div>
    </div>
  );
};
