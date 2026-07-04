import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { NodeCard } from '../components/NodeCard';
import type { NodeSnapshot } from '../types/telemetry';

describe('Cluster Status Panel (NodeCard)', () => {
  const mockNode: NodeSnapshot = {
    node_id: 'node-graviton4-01',
    status: 'healthy',
    timestamp: '2026-07-04T12:00:00Z',
    requests_per_min: 1540,
    tokens_per_sec: 245.5,
    ttft_p99_ms: 32,
    kv_eviction_rate: 0.2,
    sve2_utilization_pct: 78.4,
    dram_bandwidth_pct: 62.1,
    cache_miss_rate_pct: 4.5,
    hotspots: [
      {
        symbol: 'gemm_sve2_int4',
        samples_pct: 45.2,
      },
    ],
  };

  it('renders node status and requests per minute', () => {
    render(<NodeCard node={mockNode} now={Date.now()} />);

    expect(screen.getByText('node-graviton4-01')).toBeInTheDocument();
    expect(screen.getByText('Healthy')).toBeInTheDocument();
    expect(screen.getByText('1,540')).toBeInTheDocument();
    expect(screen.getByText('gemm_sve2_int4')).toBeInTheDocument();
  });
});
