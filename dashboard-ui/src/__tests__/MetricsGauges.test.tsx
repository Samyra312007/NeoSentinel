import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { StatCard } from '../components/StatCard';

describe('Real-Time Metrics Gauges (StatCard)', () => {
  it('renders metric label, value, unit, and hint', () => {
    render(
      <StatCard
        label="Throughput"
        value="2,450"
        unit="tok/s"
        hint="Across 3 active nodes"
        accent="bg-emerald-500"
      />
    );

    expect(screen.getByText('Throughput')).toBeInTheDocument();
    expect(screen.getByText('2,450')).toBeInTheDocument();
    expect(screen.getByText('tok/s')).toBeInTheDocument();
    expect(screen.getByText('Across 3 active nodes')).toBeInTheDocument();
  });
});
