import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { AuditLog } from '../components/AuditLog';
import type { AuditEvent } from '../types/telemetry';

describe('AuditLog Component', () => {
  it('renders clean status when events list is empty', () => {
    render(<AuditLog events={[]} />);
    expect(screen.getByText(/GITOPS AUDIT LOG/i)).toBeInTheDocument();
    expect(screen.getByText(/NO GITOPS AUDIT COMMIT ENTRIES RECORDED/i)).toBeInTheDocument();
  });

  it('renders commit entries with SHA, action, node_id, and message', () => {
    const events: AuditEvent[] = [
      {
        type: 'audit',
        commit_sha: '7e514c489ab32019c4d',
        action: 'UPDATE_VLLM_CONFIG',
        node_id: 'node-graviton-01',
        checkpoint_id: 'chk-8821',
        timestamp: '16:00:00',
        message: 'Auto-tuned max_num_seqs to 256 for SVE2 optimization.',
      },
    ];

    render(<AuditLog events={events} />);
    expect(screen.getByText(/GIT: 7e514c4/i)).toBeInTheDocument();
    expect(screen.getByText(/UPDATE_VLLM_CONFIG/i)).toBeInTheDocument();
    expect(screen.getByText(/node-graviton-01/i)).toBeInTheDocument();
    expect(screen.getByText(/chk-8821/i)).toBeInTheDocument();
    expect(screen.getByText(/Auto-tuned max_num_seqs to 256 for SVE2 optimization\./i)).toBeInTheDocument();
  });
});
