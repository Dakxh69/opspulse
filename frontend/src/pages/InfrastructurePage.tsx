import React from 'react';
import { Server } from 'lucide-react';

export const InfrastructurePage: React.FC = () => {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-white">Infrastructure</h2>
        <p className="text-sm text-slate-400">Inventory and health of registered host agents.</p>
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6">
        <div className="flex items-center gap-3">
          <Server className="h-6 w-6 text-sky-400" />
          <div>
            <h3 className="text-base font-semibold text-white">Monitored Hosts</h3>
            <p className="text-xs text-slate-400">Agent telemetry details and per-machine metrics view.</p>
          </div>
        </div>
      </div>
    </div>
  );
};
