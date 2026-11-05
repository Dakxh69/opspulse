import React, { useEffect, useState } from 'react';
import {
  AlertCircle,
  Check,
  Plus,
  RefreshCw,
  Sliders,
  Trash2,
  X,
} from 'lucide-react';
import { api } from '../services/api';
import { AlertOperator, AlertRule, AlertSeverity } from '../types';

export const AlertRulesPage: React.FC = () => {
  const [rules, setRules] = useState<AlertRule[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState<boolean>(false);
  const [submitting, setSubmitting] = useState<boolean>(false);

  // New Rule Form State
  const [name, setName] = useState<string>('');
  const [metricKey, setMetricKey] = useState<string>('cpu_percent');
  const [operator, setOperator] = useState<AlertOperator>('>');
  const [threshold, setThreshold] = useState<number>(80);
  const [severity, setSeverity] = useState<AlertSeverity>('WARNING');
  const [windowSecs, setWindowSecs] = useState<number>(60);
  const [consecutiveBreaches, setConsecutiveBreaches] = useState<number>(1);
  const [cooldownSecs, setCooldownSecs] = useState<number>(300);
  const [dimensionFilter, setDimensionFilter] = useState<string>('');

  const loadRules = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getAlertRules();
      setRules(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load alert rules');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRules();
  }, []);

  const handleToggleEnable = async (rule: AlertRule) => {
    try {
      const updated = await api.updateAlertRule(rule.id, { enabled: !rule.enabled });
      setRules((prev) => prev.map((r) => (r.id === rule.id ? updated : r)));
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to update rule');
    }
  };

  const handleDeleteRule = async (ruleId: string) => {
    if (!confirm('Are you sure you want to delete this alert rule?')) return;
    try {
      await api.deleteAlertRule(ruleId);
      setRules((prev) => prev.filter((r) => r.id !== ruleId));
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to delete rule');
    }
  };

  const handleCreateRule = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    try {
      setSubmitting(true);
      const newRule = await api.createAlertRule({
        name: name.trim(),
        metric_key: metricKey,
        operator,
        threshold: Number(threshold),
        severity,
        evaluation_window_seconds: Number(windowSecs),
        consecutive_breaches: Number(consecutiveBreaches),
        cooldown_seconds: Number(cooldownSecs),
        dimension_filter: dimensionFilter.trim() || null,
        enabled: true,
      });
      setRules((prev) => [newRule, ...prev]);
      setModalOpen(false);
      setName('');
      setThreshold(80);
      setDimensionFilter('');
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to create alert rule');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Title & Action Buttons */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white">Alert Rules</h2>
          <p className="text-sm text-slate-400">
            Define infrastructure thresholds, sliding windows, and cooldown periods.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={loadRules}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin text-sky-400' : ''}`} />
            Refresh
          </button>
          <button
            onClick={() => setModalOpen(true)}
            className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-sky-500 hover:bg-sky-600 text-white shadow-sm transition"
          >
            <Plus className="h-4 w-4" /> New Rule
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm flex items-center gap-3">
          <AlertCircle className="h-5 w-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Rules Table */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/60 text-slate-400 border-b border-slate-800 font-medium">
              <tr>
                <th className="px-5 py-3">Rule Name</th>
                <th className="px-5 py-3">Metric & Condition</th>
                <th className="px-5 py-3">Severity</th>
                <th className="px-5 py-3">Window & Breaches</th>
                <th className="px-5 py-3">Cooldown</th>
                <th className="px-5 py-3">Status</th>
                <th className="px-5 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {rules.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-5 py-10 text-center text-slate-500">
                    No alert rules configured. Create one to begin monitoring metric breaches.
                  </td>
                </tr>
              ) : (
                rules.map((rule) => (
                  <tr key={rule.id} className="hover:bg-slate-800/30 transition">
                    <td className="px-5 py-3.5">
                      <div className="font-semibold text-slate-100">{rule.name}</div>
                      {rule.dimension_filter && (
                        <div className="text-[11px] text-slate-500 font-mono">
                          Filter: {rule.dimension_filter}
                        </div>
                      )}
                    </td>
                    <td className="px-5 py-3.5 font-mono text-slate-300">
                      <span className="text-sky-400 font-medium">{rule.metric_key}</span>{' '}
                      <span className="text-slate-400">{rule.operator}</span>{' '}
                      <span className="font-bold text-white">{rule.threshold}%</span>
                    </td>
                    <td className="px-5 py-3.5">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold border ${
                          rule.severity === 'CRITICAL'
                            ? 'bg-red-500/10 text-red-400 border-red-500/30'
                            : 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                        }`}
                      >
                        {rule.severity}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 text-slate-400 font-mono">
                      {rule.evaluation_window_seconds}s window • {rule.consecutive_breaches} sustained
                    </td>
                    <td className="px-5 py-3.5 text-slate-400 font-mono">{rule.cooldown_seconds}s</td>
                    <td className="px-5 py-3.5">
                      <button
                        onClick={() => handleToggleEnable(rule)}
                        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-medium border transition ${
                          rule.enabled
                            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                            : 'bg-slate-800 text-slate-500 border-slate-700'
                        }`}
                      >
                        <span
                          className={`h-1.5 w-1.5 rounded-full ${
                            rule.enabled ? 'bg-emerald-400' : 'bg-slate-500'
                          }`}
                        />
                        {rule.enabled ? 'Enabled' : 'Disabled'}
                      </button>
                    </td>
                    <td className="px-5 py-3.5 text-right">
                      <button
                        onClick={() => handleDeleteRule(rule.id)}
                        className="p-1 rounded text-slate-500 hover:text-red-400 transition"
                        title="Delete rule"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Create Rule Modal */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-2xl border border-slate-800 bg-slate-900 p-6 space-y-5 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <div className="flex items-center gap-2">
                <Sliders className="h-5 w-5 text-sky-400" />
                <h3 className="text-base font-bold text-white">Create Alert Rule</h3>
              </div>
              <button
                onClick={() => setModalOpen(false)}
                className="p-1 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleCreateRule} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-400 font-medium mb-1">Rule Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Host High CPU Sustained"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-sky-500"
                />
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-slate-400 font-medium mb-1">Metric</label>
                  <select
                    value={metricKey}
                    onChange={(e) => setMetricKey(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-100 focus:outline-none focus:border-sky-500"
                  >
                    <option value="cpu_percent">CPU Usage (%)</option>
                    <option value="memory_percent">Memory Usage (%)</option>
                    <option value="disk_percent">Disk Usage (%)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-slate-400 font-medium mb-1">Operator</label>
                  <select
                    value={operator}
                    onChange={(e) => setOperator(e.target.value as AlertOperator)}
                    className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-100 focus:outline-none focus:border-sky-500"
                  >
                    <option value=">">&gt; (Greater than)</option>
                    <option value=">=">&gt;= (Greater or eq)</option>
                    <option value="<">&lt; (Less than)</option>
                    <option value="<=">&lt;= (Less or eq)</option>
                    <option value="==">== (Equals)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-slate-400 font-medium mb-1">Threshold (%)</label>
                  <input
                    type="number"
                    required
                    step="0.1"
                    value={threshold}
                    onChange={(e) => setThreshold(Number(e.target.value))}
                    className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-100 focus:outline-none focus:border-sky-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-400 font-medium mb-1">Severity</label>
                  <select
                    value={severity}
                    onChange={(e) => setSeverity(e.target.value as AlertSeverity)}
                    className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-100 focus:outline-none focus:border-sky-500"
                  >
                    <option value="WARNING">WARNING</option>
                    <option value="CRITICAL">CRITICAL</option>
                  </select>
                </div>

                <div>
                  <label className="block text-slate-400 font-medium mb-1">Dimension Filter (Optional)</label>
                  <input
                    type="text"
                    placeholder="e.g. / or /data"
                    value={dimensionFilter}
                    onChange={(e) => setDimensionFilter(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-sky-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-slate-400 font-medium mb-1">Window (sec)</label>
                  <input
                    type="number"
                    min="10"
                    max="86400"
                    value={windowSecs}
                    onChange={(e) => setWindowSecs(Number(e.target.value))}
                    className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-100 focus:outline-none focus:border-sky-500"
                  />
                </div>

                <div>
                  <label className="block text-slate-400 font-medium mb-1">Breaches Req.</label>
                  <input
                    type="number"
                    min="1"
                    max="100"
                    value={consecutiveBreaches}
                    onChange={(e) => setConsecutiveBreaches(Number(e.target.value))}
                    className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-100 focus:outline-none focus:border-sky-500"
                  />
                </div>

                <div>
                  <label className="block text-slate-400 font-medium mb-1">Cooldown (sec)</label>
                  <input
                    type="number"
                    min="0"
                    max="86400"
                    value={cooldownSecs}
                    onChange={(e) => setCooldownSecs(Number(e.target.value))}
                    className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-100 focus:outline-none focus:border-sky-500"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="px-4 py-2 rounded-lg bg-slate-800 text-slate-300 hover:bg-slate-700 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-sky-500 hover:bg-sky-600 text-white font-semibold transition"
                >
                  <Check className="h-4 w-4" /> Save Rule
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
