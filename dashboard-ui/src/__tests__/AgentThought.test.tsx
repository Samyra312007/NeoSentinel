import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { AgentThought } from '../components/AgentThought';
import type { AgentThoughtEvent } from '../types/telemetry';

describe('AgentThought Component', () => {
  it('renders idle state when thoughts list is empty', () => {
    render(<AgentThought thoughts={[]} />);
    expect(screen.getByText(/AGENT REASONING STREAM/i)).toBeInTheDocument();
    expect(screen.getByText(/AGENT IDLE/i)).toBeInTheDocument();
  });

  it('renders and combines streaming chunks by decision_id', () => {
    const events: AgentThoughtEvent[] = [
      {
        type: 'agent_thought',
        decision_id: 'dec-101',
        node_id: 'node-graviton-01',
        timestamp: '14:00:01',
        chunk: 'Analyzing high SVE2 ',
        done: false,
      },
      {
        type: 'agent_thought',
        decision_id: 'dec-101',
        node_id: 'node-graviton-01',
        timestamp: '14:00:02',
        chunk: 'underutilization anomalies.',
        done: false,
      },
    ];

    render(<AgentThought thoughts={events} />);
    expect(screen.getByText('dec-101')).toBeInTheDocument();
    expect(screen.getByText('node-graviton-01')).toBeInTheDocument();
    expect(screen.getByText(/Analyzing high SVE2 underutilization anomalies\./i)).toBeInTheDocument();
    expect(screen.getByText(/STREAMING\.\.\./i)).toBeInTheDocument();
  });

  it('renders done status badge when done is true', () => {
    const events: AgentThoughtEvent[] = [
      {
        type: 'agent_thought',
        decision_id: 'dec-102',
        node_id: 'node-graviton-02',
        timestamp: '14:05:00',
        chunk: 'Decision reached: Trigger cluster healing.',
        done: true,
      },
    ];

    render(<AgentThought thoughts={events} />);
    expect(screen.getByText('dec-102')).toBeInTheDocument();
    expect(screen.getByText(/Decision reached: Trigger cluster healing\./i)).toBeInTheDocument();
    expect(screen.getByText(/DONE/i)).toBeInTheDocument();
  });
});
