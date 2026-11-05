import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { AlertRulesPage } from '../pages/AlertRulesPage';
import { api } from '../services/api';

vi.mock('../services/api', () => ({
  api: {
    getAlertRules: vi.fn(),
    createAlertRule: vi.fn(),
    toggleAlertRule: vi.fn(),
    deleteAlertRule: vi.fn(),
  },
}));

describe('AlertRulesPage Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders rules table and opens Create Rule modal', async () => {
    const mockRule = {
      id: 'rule-1',
      name: 'High CPU Sustained',
      metric_key: 'cpu_percent',
      operator: '>',
      threshold: 85.0,
      severity: 'CRITICAL',
      window_seconds: 60,
      consecutive_breaches: 3,
      cooldown_seconds: 300,
      enabled: true,
      created_at: new Date().toISOString(),
    };

    (api.getAlertRules as any).mockResolvedValue([mockRule]);

    render(<AlertRulesPage />);

    expect(screen.getByText('Alert Rules')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('High CPU Sustained')).toBeInTheDocument();
      expect(screen.getByText('cpu_percent')).toBeInTheDocument();
      expect(screen.getByText('85%')).toBeInTheDocument();
    });

    // Click "New Rule" button
    const createBtn = screen.getByRole('button', { name: /new rule/i });
    fireEvent.click(createBtn);

    // Modal should be visible
    expect(screen.getByText('Create Alert Rule')).toBeInTheDocument();
  });
});
