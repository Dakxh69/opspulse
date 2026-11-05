import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { IncidentsPage } from '../pages/IncidentsPage';
import { api } from '../services/api';

vi.mock('../services/api', () => ({
  api: {
    getIncidents: vi.fn(),
    getIncidentEvents: vi.fn(),
    acknowledgeIncident: vi.fn(),
    resolveIncident: vi.fn(),
  },
}));

describe('IncidentsPage Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders incidents list and allows selection to view details', async () => {
    const mockIncident = {
      id: 'inc-99',
      agent_id: 'agent-123',
      title: 'Disk Exhaustion Warning',
      dimension: 'disk',
      severity: 'WARNING',
      status: 'OPEN',
      summary: 'Disk root usage > 85%',
      started_at: new Date().toISOString(),
      resolved_at: null,
      events: [],
    };

    (api.getIncidents as any).mockResolvedValue({
      items: [mockIncident],
      total: 1,
      page: 1,
      limit: 50,
    });
    (api.getIncidentEvents as any).mockResolvedValue([
      {
        id: 'evt-1',
        incident_id: 'inc-99',
        event_type: 'DETECTED',
        description: 'Breached threshold',
        created_at: new Date().toISOString(),
      },
    ]);

    render(<IncidentsPage />);

    // Header
    expect(screen.getByText('Incidents')).toBeInTheDocument();

    // Incident in table
    await waitFor(() => {
      expect(screen.getByText('Disk Exhaustion Warning')).toBeInTheDocument();
    });

    // Click on the incident row to select it
    fireEvent.click(screen.getByText('Disk Exhaustion Warning'));

    // Detail panel should appear with Action buttons
    await waitFor(() => {
      expect(screen.getByText('ID: inc-99')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /^acknowledge$/i })).toBeInTheDocument();
    });
  });
});
