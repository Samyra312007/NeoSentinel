import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { FlameGraph } from '../components/FlameGraph';
import type { HotspotEntry } from '../types/telemetry';

describe('FlameGraph Component', () => {
  it('renders nominal status when hotspots list is empty', () => {
    render(<FlameGraph node_id="NODE-1" hotspots={[]} />);
    expect(screen.getByText(/TOP-5 HOTSPOT FLAME GRAPH/i)).toBeInTheDocument();
    expect(screen.getByText(/NODE-1/i)).toBeInTheDocument();
    expect(screen.getByText(/NO HOTSPOT TELEMETRY CAPTURED/i)).toBeInTheDocument();
  });

  it('renders top 5 hotspot bars and symbols', () => {
    const hotspots: HotspotEntry[] = [
      { symbol: 'ggml_vec_dot_f16', samples_pct: 45.2, module: 'vllm_sve2' },
      { symbol: 'rotary_embedding_kernel', samples_pct: 22.1, module: 'vllm_core' },
      { symbol: 'silu_and_mul_kernel', samples_pct: 15.0, module: 'vllm_core' },
      { symbol: 'paged_attention_v1', samples_pct: 10.5, module: 'vllm_attn' },
      { symbol: 'rmsnorm_kernel', samples_pct: 5.2, module: 'vllm_core' },
      { symbol: 'ignored_6th_kernel', samples_pct: 2.0, module: 'vllm_core' },
    ];

    const { container } = render(<FlameGraph node_id="GRAVITON-01" hotspots={hotspots} />);
    expect(screen.getByText(/GRAVITON-01/i)).toBeInTheDocument();
    
    // Verify top 5 symbol names appear in the SVG
    expect(screen.getByText(/ggml_vec_dot_f16/i)).toBeInTheDocument();
    expect(screen.getByText(/rotary_embedding/i)).toBeInTheDocument();
    expect(screen.getByText(/silu_and_mul_ker/i)).toBeInTheDocument();
    expect(screen.getByText(/paged_attention_v1/i)).toBeInTheDocument();
    expect(screen.getByText(/rmsnorm_kernel/i)).toBeInTheDocument();

    // Verify 6th kernel is excluded (top 5 only)
    expect(screen.queryByText('ignored_6th_kernel')).not.toBeInTheDocument();

    // Verify SVG rectangles are created for bars
    const rects = container.querySelectorAll('rect.bar');
    expect(rects.length).toBe(5);
  });
});
