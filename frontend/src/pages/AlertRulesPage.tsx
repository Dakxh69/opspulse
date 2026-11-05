import React from 'react';
import { Bell } from 'lucide-react';

export const AlertRulesPage: React.FC = () => {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-white">Alert Rules</h2>
        <p className="text-sm text-slate-400">Configurable criteria, thresholds, and evaluation windows.</p>
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6">
        <div className="flex items-center gap-3">
          <Bell className="h-6 w-6 text-sky-400" />
          <div>
            <h3 className="text-base font-semibold text-white">Threshold Rules</h3>
            <p className="text-xs text-slate-400">Rules evaluated transactionally on incoming telemetry batches.</p>
          </div>
        </div>
      </div>
    </div>
  );
};
