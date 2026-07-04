import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { HealingFeed } from '../components/HealingFeed';
import type { HealingEvent } from '../types/telemetry';

describe('HealingFeed Component', () => {
  it('renders stable status when events list is empty', () => {
    render(<HealingFeed events={[]} />);
    expect(screen.getByText(/AUTONOMOUS HEALING FEED/i)).toBeInTheDocument();
    expect(screen.getByText(/NO AUTONOMOUS HEALING ACTIONS RECORDED/i)).toBeInTheDocument();
  });

  it('renders healing events with before/after metrics and badges', () => {
    const events: HealingEvent[] = [
      {
        type: 'healing',
        healing_id: 'heal-501',
        node_id: 'node-graviton-01',
        action: 'RESTART_VLLM_WORKER',
        status: 'success',
        duration_ms: 1250,
        timestamp: '15:10:00',
        before: {
          ttft_p99_ms: 450,
          tokens_per_sec: 25.0,
          sve2_utilization_pct: 12.4,
          dram_bandwidth_pct: 40.0,
          cache_miss_rate_pct: 5.0,
          kv_eviction_rate: 1.0,
          requests_per_min: 100,
        },
        after: {
          ttft_p99_ms: 42,
          tokens_per_sec: 185.3,
          sve2_utilization_pct: 88.5,
          dram_bandwidth_pct: 75.0,
          cache_miss_rate_pct: 1.2,
          kv_eviction_rate: 0.0,
          requests_per_min: 500,
        },
      },
    ];

    render(<HealingFeed events={events} />);
    expect(screen.getByText(/RESTART_VLLM_WORKER/i)).toBeInTheDocument();
    expect(screen.getByText(/node-graviton-01/i)).toBeInTheDocument();
    expect(screen.getByText(/success/i)).toBeInTheDocument();
    expect(screen.getByText(/1250ms/i)).toBeInTheDocument();
    expect(screen.getByText(/12\.4%/i)).toBeInTheDocument();
    expect(screen.getByText(/88\.5%/i)).toBeInTheDocument();
  });
});
