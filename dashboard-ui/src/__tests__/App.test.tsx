import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import App from '../App';

vi.mock('../hooks/useWebSocket', () => ({
  useWebSocket: () => ({
    connected: true,
    error: null,
    lastMessage: null,
    messages: [
      {
        type: 'metrics',
        cluster_id: 'cluster-graviton4',
        timestamp: '2026-07-04T12:00:00Z',
        nodes: []
      }
    ],
    sendMessage: vi.fn(),
  }),
}));

describe('App', () => {
  it('renders dashboard header and cluster overview', () => {
    render(<App />);
    expect(screen.getByRole('heading', { name: /NeoSentinel/i })).toBeInTheDocument();
    expect(screen.getByText(/Graviton4 Control Plane/i)).toBeInTheDocument();
    expect(screen.getByText(/Cluster Overview/i)).toBeInTheDocument();
    expect(screen.getByText(/Live/i)).toBeInTheDocument();
  });
});
