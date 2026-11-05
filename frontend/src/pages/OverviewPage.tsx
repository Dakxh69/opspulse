import React from 'react';
import { Activity, AlertTriangle, CheckCircle2, Server } from 'lucide-react';

export const OverviewPage: React.FC = () => {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-white">System Overview</h2>
        <p className="text-sm text-slate-400">Real-time status of monitored hosts and incidents.</p>
      </div>

      {/* Metric Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Total Monitored Agents</span>
            <Server className="h-4 w-4 text-sky-400" />
          </div>
          <p className="text-2xl font-bold text-white mt-2">1</p>
          <span className="text-xs text-emerald-400 flex items-center gap-1 mt-1">
            <CheckCircle2 className="h-3 w-3" /> 1 Online
          </span>
        </div>

        <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Active Incidents</span>
            <AlertTriangle className="h-4 w-4 text-amber-400" />
          </div>
          <p className="text-2xl font-bold text-white mt-2">0</p>
          <span className="text-xs text-slate-400 mt-1">All rules within thresholds</span>
        </div>

        <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Average CPU</span>
            <Activity className="h-4 w-4 text-emerald-400" />
          </div>
          <p className="text-2xl font-bold text-white mt-2">14.2%</p>
          <span className="text-xs text-slate-400 mt-1">Non-blocking live delta</span>
        </div>

        <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Average Memory</span>
            <Activity className="h-4 w-4 text-emerald-400" />
          </div>
          <p className="text-2xl font-bold text-white mt-2">48.6%</p>
          <span className="text-xs text-slate-400 mt-1">Physical RAM usage</span>
        </div>
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-6">
        <h3 className="text-base font-semibold text-white mb-2">Platform Ingestion Pipeline</h3>
        <p className="text-sm text-slate-400">
          Agent metrics stream into FastAPI, publish to Redis, process asynchronously in Celery, and
          evaluate against alert rules transactionally.
        </p>
      </div>
    </div>
  );
};
