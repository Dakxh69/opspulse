import React from 'react';
import { AlertTriangle } from 'lucide-react';

export const IncidentsPage: React.FC = () => {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-white">Incidents</h2>
        <p className="text-sm text-slate-400">Operational incident state machine and lifecycle timeline.</p>
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6">
        <div className="flex items-center gap-3">
          <AlertTriangle className="h-6 w-6 text-amber-400" />
          <div>
            <h3 className="text-base font-semibold text-white">Active Incidents</h3>
            <p className="text-xs text-slate-400">Acknowledge, investigate, resolve, or inspect timeline events.</p>
          </div>
        </div>
      </div>
    </div>
  );
};
