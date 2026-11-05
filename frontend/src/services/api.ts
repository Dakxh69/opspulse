/**
 * OpsPulse Frontend — Centralized API Client
 *
 * Communicates with the FastAPI backend through the Vite reverse-proxy (/api/v1).
 * Credentials (HttpOnly cookies or Bearer token) are handled automatically.
 */

import {
  Agent,
  AlertRule,
  Incident,
  IncidentEvent,
  MetricSample,
} from '../types';

const BASE_URL = '/api/v1';

async function fetchJson<T>(url: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers || {});
  if (!headers.has('Content-Type') && options.body && typeof options.body === 'string') {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(`${BASE_URL}${url}`, {
    ...options,
    headers,
    credentials: 'include', // sends HttpOnly session cookies
  });

  if (!response.ok) {
    let errorDetail = `HTTP ${response.status} ${response.statusText}`;
    try {
      const err = await response.json();
      if (err.detail) {
        errorDetail = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail);
      }
    } catch {
      // Use fallback errorDetail
    }
    throw new Error(errorDetail);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

export const api = {
  // --- Agents ---
  async getAgents(): Promise<Agent[]> {
    return fetchJson<Agent[]>('/agents');
  },

  async getAgent(agentId: string): Promise<Agent> {
    return fetchJson<Agent>(`/agents/${agentId}`);
  },

  // --- Metrics ---
  async getLatestMetric(agentId: string): Promise<MetricSample | null> {
    try {
      return await fetchJson<MetricSample>(`/metrics/${agentId}/latest`);
    } catch {
      return null;
    }
  },

  async getMetricHistory(agentId: string, limit: number = 60): Promise<MetricSample[]> {
    const res = await fetchJson<{ items: MetricSample[] }>(`/metrics/${agentId}?limit=${limit}`);
    return res.items || [];
  },

  // --- Incidents ---
  async getIncidents(params: {
    status?: string;
    severity?: string;
    agent_id?: string;
    page?: number;
    limit?: number;
  } = {}): Promise<{ items: Incident[]; total: number; page: number; limit: number }> {
    const query = new URLSearchParams();
    if (params.status) query.set('status', params.status);
    if (params.severity) query.set('severity', params.severity);
    if (params.agent_id) query.set('agent_id', params.agent_id);
    if (params.page) query.set('page', params.page.toString());
    if (params.limit) query.set('limit', params.limit.toString());

    return fetchJson<{ items: Incident[]; total: number; page: number; limit: number }>(
      `/incidents?${query.toString()}`
    );
  },

  async getIncident(id: string): Promise<Incident> {
    return fetchJson<Incident>(`/incidents/${id}`);
  },

  async acknowledgeIncident(id: string, message?: string): Promise<Incident> {
    return fetchJson<Incident>(`/incidents/${id}/acknowledge`, {
      method: 'POST',
      body: JSON.stringify({ message }),
    });
  },

  async resolveIncident(id: string, message?: string): Promise<Incident> {
    return fetchJson<Incident>(`/incidents/${id}/resolve`, {
      method: 'POST',
      body: JSON.stringify({ message }),
    });
  },

  async reopenIncident(id: string, message?: string): Promise<Incident> {
    return fetchJson<Incident>(`/incidents/${id}/reopen`, {
      method: 'POST',
      body: JSON.stringify({ message }),
    });
  },

  async addIncidentNote(id: string, message: string): Promise<IncidentEvent> {
    return fetchJson<IncidentEvent>(`/incidents/${id}/notes`, {
      method: 'POST',
      body: JSON.stringify({ message }),
    });
  },

  async getIncidentEvents(id: string): Promise<IncidentEvent[]> {
    return fetchJson<IncidentEvent[]>(`/incidents/${id}/events`);
  },

  // --- Alert Rules ---
  async getAlertRules(): Promise<AlertRule[]> {
    return fetchJson<AlertRule[]>('/alerts/rules');
  },

  async createAlertRule(rule: Partial<AlertRule>): Promise<AlertRule> {
    return fetchJson<AlertRule>('/alerts/rules', {
      method: 'POST',
      body: JSON.stringify(rule),
    });
  },

  async updateAlertRule(id: string, patch: Partial<AlertRule>): Promise<AlertRule> {
    return fetchJson<AlertRule>(`/alerts/rules/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(patch),
    });
  },

  async deleteAlertRule(id: string): Promise<void> {
    return fetchJson<void>(`/alerts/rules/${id}`, {
      method: 'DELETE',
    });
  },
};
