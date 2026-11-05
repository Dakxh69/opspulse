import React from 'react';
import { ShieldCheck } from 'lucide-react';

export const AuditLogsPage: React.FC = () => {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-white">Audit Trail</h2>
        <p className="text-sm text-slate-400">Immutable security event history per spec Section 17.10.</p>
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6">
        <div className="flex items-center gap-3">
          <ShieldCheck className="h-6 w-6 text-emerald-400" />
          <div>
            <h3 className="text-base font-semibold text-white">Security Events</h3>
            <p className="text-xs text-slate-400">Logins, provisioning, rule mutations, and incident approvals.</p>
          </div>
        </div>
      </div>
    </div>
  );
};
