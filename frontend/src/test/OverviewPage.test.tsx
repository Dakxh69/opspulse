import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { OverviewPage } from '../pages/OverviewPage';
import { api } from '../services/api';

vi.mock('../services/api', () => ({
  api: {
    getAgents: vi.fn(),
    getIncidents: vi.fn(),
  },
}));

describe('OverviewPage Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading skeleton then displays fleet health metrics and recent incidents', async () => {
    (api.getAgents as any).mockResolvedValue([
      { id: '1', name: 'web-prod-1', hostname: 'web-1', status: 'ONLINE', last_heartbeat: new Date().toISOString() },
      { id: '2', name: 'db-prod-1', hostname: 'db-1', status: 'ONLINE', last_heartbeat: new Date().toISOString() },
      { id: '3', name: 'worker-1', hostname: 'w-1', status: 'DEGRADED', last_heartbeat: new Date().toISOString() },
    ]);
    (api.getIncidents as any).mockResolvedValue({
      items: [
        {
          id: 'inc-1',
          title: 'CPU Usage High',
          severity: 'CRITICAL',
          status: 'OPEN',
          started_at: new Date().toISOString(),
          agent_id: '1',
          events: [],
        },
      ],
      total: 1,
      page: 1,
      limit: 10,
    });

    render(
      <BrowserRouter>
        <OverviewPage />
      </BrowserRouter>
    );

    // Header title
    expect(screen.getByText('System Overview')).toBeInTheDocument();

    // Await fleet statistics cards
    await waitFor(() => {
      expect(screen.getByText('Monitored Agents')).toBeInTheDocument();
      expect(screen.getByText('2 Online')).toBeInTheDocument();
      expect(screen.getByText('1 Degraded')).toBeInTheDocument();
    });

    // Recent incident title
    expect(screen.getByText('CPU Usage High')).toBeInTheDocument();
  });
});
