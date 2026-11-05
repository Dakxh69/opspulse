import React, { useEffect, useState } from 'react';
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  MessageSquare,
  RefreshCw,
  RotateCcw,
  Send,
  UserCheck,
  X,
} from 'lucide-react';
import { api } from '../services/api';
import { Incident, IncidentEvent } from '../types';

export const IncidentsPage: React.FC = () => {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);
  const [events, setEvents] = useState<IncidentEvent[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [loading, setLoading] = useState<boolean>(true);
  const [eventsLoading, setEventsLoading] = useState<boolean>(false);
  const [noteMessage, setNoteMessage] = useState<string>('');
  const [actionLoading, setActionLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const loadIncidents = async () => {
    try {
      setLoading(true);
      setError(null);
      const params: { status?: string; severity?: string } = {};
      if (statusFilter !== 'ALL') params.status = statusFilter;
      if (severityFilter !== 'ALL') params.severity = severityFilter;

      const res = await api.getIncidents(params);
      setIncidents(res.items || []);

      if (selectedIncident) {
        const updated = res.items.find((i) => i.id === selectedIncident.id);
        if (updated) setSelectedIncident(updated);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load incidents');
    } finally {
      setLoading(false);
    }
  };

  const selectIncident = async (inc: Incident) => {
    setSelectedIncident(inc);
    try {
      setEventsLoading(true);
      const evs = await api.getIncidentEvents(inc.id);
      setEvents(evs);
    } catch (err: unknown) {
      console.error('Failed to load incident events', err);
    } finally {
      setEventsLoading(false);
    }
  };

  useEffect(() => {
    loadIncidents();
  }, [statusFilter, severityFilter]);

  const handleAcknowledge = async () => {
    if (!selectedIncident) return;
    try {
      setActionLoading(true);
      const updated = await api.acknowledgeIncident(selectedIncident.id);
      setSelectedIncident(updated);
      await loadIncidents();
      const evs = await api.getIncidentEvents(selectedIncident.id);
      setEvents(evs);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Action failed');
    } finally {
      setActionLoading(false);
    }
  };

  const handleResolve = async () => {
    if (!selectedIncident) return;
    try {
      setActionLoading(true);
      const updated = await api.resolveIncident(selectedIncident.id);
      setSelectedIncident(updated);
      await loadIncidents();
      const evs = await api.getIncidentEvents(selectedIncident.id);
      setEvents(evs);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Action failed');
    } finally {
      setActionLoading(false);
    }
  };

  const handleReopen = async () => {
    if (!selectedIncident) return;
    try {
      setActionLoading(true);
      const updated = await api.reopenIncident(selectedIncident.id);
      setSelectedIncident(updated);
      await loadIncidents();
      const evs = await api.getIncidentEvents(selectedIncident.id);
      setEvents(evs);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Action failed');
    } finally {
      setActionLoading(false);
    }
  };

  const handleAddNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedIncident || !noteMessage.trim()) return;
    try {
      setActionLoading(true);
      await api.addIncidentNote(selectedIncident.id, noteMessage.trim());
      setNoteMessage('');
      const evs = await api.getIncidentEvents(selectedIncident.id);
      setEvents(evs);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to add note');
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Title & Filter Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white">Incidents</h2>
          <p className="text-sm text-slate-400">
            Triage, acknowledge, investigate, and resolve operational breaches.
          </p>
        </div>

        <button
          onClick={loadIncidents}
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

      {/* Filters Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-3 rounded-xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm">
        {/* Status Filters */}
        <div className="flex items-center gap-1">
          {['ALL', 'OPEN', 'ACKNOWLEDGED', 'RESOLVED'].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1.5 text-xs font-medium rounded-lg transition ${
                statusFilter === st
                  ? 'bg-sky-500/20 text-sky-400 border border-sky-500/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
              }`}
            >
              {st}
            </button>
          ))}
        </div>

        {/* Severity Filters */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500">Severity:</span>
          {['ALL', 'CRITICAL', 'WARNING'].map((sev) => (
            <button
              key={sev}
              onClick={() => setSeverityFilter(sev)}
              className={`px-2.5 py-1 text-xs font-medium rounded-md transition ${
                severityFilter === sev
                  ? 'bg-slate-700 text-slate-100 font-semibold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {sev}
            </button>
          ))}
        </div>
      </div>

      {/* Incidents Master-Detail Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Incidents Table / List */}
        <div className={`rounded-xl border border-slate-800 bg-slate-900/60 overflow-hidden ${selectedIncident ? 'lg:col-span-7' : 'lg:col-span-12'}`}>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/60 text-slate-400 border-b border-slate-800 font-medium">
                <tr>
                  <th className="px-4 py-3">Severity</th>
                  <th className="px-4 py-3">Title</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Detected</th>
                  <th className="px-4 py-3 text-right">Inspect</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {incidents.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-4 py-10 text-center text-slate-500">
                      No incidents matching current criteria.
                    </td>
                  </tr>
                ) : (
                  incidents.map((inc) => {
                    const isSelected = selectedIncident?.id === inc.id;
                    return (
                      <tr
                        key={inc.id}
                        onClick={() => selectIncident(inc)}
                        className={`cursor-pointer transition ${
                          isSelected ? 'bg-sky-500/10' : 'hover:bg-slate-800/30'
                        }`}
                      >
                        <td className="px-4 py-3">
                          <span
                            className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold border ${
                              inc.severity === 'CRITICAL'
                                ? 'bg-red-500/10 text-red-400 border-red-500/30'
                                : 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                            }`}
                          >
                            {inc.severity}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <div className="font-semibold text-slate-200">{inc.title}</div>
                          <div className="text-[11px] text-slate-500 truncate max-w-xs">
                            {inc.dimension ? `[${inc.dimension}] ` : ''}
                            {inc.description}
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium border ${
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
                        <td className="px-4 py-3 text-slate-400 font-mono text-[11px]">
                          {new Date(inc.first_detected_at).toLocaleTimeString([], {
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </td>
                        <td className="px-4 py-3 text-right text-slate-400">
                          <ChevronRight className="h-4 w-4 ml-auto" />
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Selected Incident Detail Panel */}
        {selectedIncident && (
          <div className="lg:col-span-5 rounded-xl border border-slate-800 bg-slate-900/80 p-5 space-y-5 backdrop-blur-md sticky top-6">
            <div className="flex items-start justify-between">
              <div>
                <span
                  className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold border mb-1.5 ${
                    selectedIncident.severity === 'CRITICAL'
                      ? 'bg-red-500/10 text-red-400 border-red-500/30'
                      : 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                  }`}
                >
                  {selectedIncident.severity}
                </span>
                <h3 className="text-base font-bold text-white">{selectedIncident.title}</h3>
                <p className="text-xs text-slate-400 font-mono mt-0.5">ID: {selectedIncident.id}</p>
              </div>
              <button
                onClick={() => setSelectedIncident(null)}
                className="p-1 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <p className="text-xs text-slate-300 bg-slate-950/60 p-3 rounded-lg border border-slate-800">
              {selectedIncident.description}
            </p>

            {/* Lifecycle Action Buttons */}
            <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-800">
              {selectedIncident.status === 'OPEN' && (
                <button
                  onClick={handleAcknowledge}
                  disabled={actionLoading}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-500/10 text-indigo-400 hover:bg-indigo-500/20 border border-indigo-500/30 transition"
                >
                  <UserCheck className="h-3.5 w-3.5" /> Acknowledge
                </button>
              )}

              {selectedIncident.status !== 'RESOLVED' && (
                <button
                  onClick={handleResolve}
                  disabled={actionLoading}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 border border-emerald-500/30 transition"
                >
                  <CheckCircle2 className="h-3.5 w-3.5" /> Resolve Incident
                </button>
              )}

              {selectedIncident.status === 'RESOLVED' && (
                <button
                  onClick={handleReopen}
                  disabled={actionLoading}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-amber-500/10 text-amber-400 hover:bg-amber-500/20 border border-amber-500/30 transition"
                >
                  <RotateCcw className="h-3.5 w-3.5" /> Reopen Incident
                </button>
              )}
            </div>

            {/* Event Timeline */}
            <div className="space-y-3 pt-3 border-t border-slate-800">
              <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                Event Timeline
              </h4>

              {eventsLoading ? (
                <p className="text-xs text-slate-500 py-3 text-center">Loading timeline events...</p>
              ) : (
                <div className="space-y-3 max-h-60 overflow-y-auto pr-1">
                  {events.map((ev) => (
                    <div key={ev.id} className="text-xs flex items-start gap-2.5">
                      <div className="mt-0.5 p-1 rounded-full bg-slate-800 text-slate-400">
                        {ev.event_type === 'DETECTED' ? (
                          <AlertTriangle className="h-3 w-3 text-amber-400" />
                        ) : ev.event_type === 'RESOLVED' || ev.event_type === 'AUTO_CLEARED' ? (
                          <CheckCircle2 className="h-3 w-3 text-emerald-400" />
                        ) : (
                          <MessageSquare className="h-3 w-3 text-sky-400" />
                        )}
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center justify-between text-[11px]">
                          <span className="font-semibold text-slate-300">{ev.event_type}</span>
                          <span className="text-slate-500 font-mono">
                            {new Date(ev.created_at).toLocaleTimeString()}
                          </span>
                        </div>
                        <p className="text-slate-400 mt-0.5 text-[11px]">{ev.message}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Add Investigation Note */}
            <form onSubmit={handleAddNote} className="pt-3 border-t border-slate-800 flex items-center gap-2">
              <input
                type="text"
                placeholder="Add operator investigation note..."
                value={noteMessage}
                onChange={(e) => setNoteMessage(e.target.value)}
                className="flex-1 px-3 py-1.5 text-xs rounded-lg bg-slate-950 border border-slate-800 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-sky-500 transition"
              />
              <button
                type="submit"
                disabled={actionLoading || !noteMessage.trim()}
                className="p-1.5 rounded-lg bg-sky-500 hover:bg-sky-600 text-white disabled:opacity-50 transition"
              >
                <Send className="h-3.5 w-3.5" />
              </button>
            </form>
          </div>
        )}
      </div>
    </div>
  );
};
