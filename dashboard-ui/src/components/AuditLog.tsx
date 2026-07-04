import React from 'react';
import type { AuditEvent } from '../types/telemetry';

interface AuditLogProps {
  events: AuditEvent[];
}

export const AuditLog: React.FC<AuditLogProps> = ({ events }) => {
  return (
    <div className="border border-[var(--border-color)] bg-[var(--card-bg)] p-4 font-mono">
      <div className="flex items-center justify-between border-b border-[var(--border-color)] pb-3 mb-4">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-[var(--accent-violet, #8b5cf6)] animate-pulse" />
          <h2 className="text-sm font-bold tracking-wider uppercase text-[var(--text-main)]">
            [ GITOPS AUDIT LOG // <span className="text-[var(--accent-violet, #8b5cf6)]">S3.4 IMMUTABLE TRAIL</span> ]
          </h2>
        </div>
        <span className="text-xs text-[var(--text-muted)]">
          COMMIT HISTORY
        </span>
      </div>

      {events.length === 0 ? (
        <div className="py-8 text-center border border-dashed border-[var(--border-color)] bg-black/20">
          <p className="text-xs text-[var(--text-muted)] tracking-widest uppercase">
            [ NO GITOPS AUDIT COMMIT ENTRIES RECORDED // LOG CLEAN ]
          </p>
        </div>
      ) : (
        <div className="space-y-3 max-h-96 overflow-y-auto pr-1">
          {events.slice().reverse().map((event) => (
            <div
              key={`${event.commit_sha}-${event.timestamp}`}
              className="border-l-2 border-[var(--accent-violet, #8b5cf6)] bg-black/30 p-3 hover:bg-black/50 transition-colors"
            >
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/5 pb-1 mb-2 text-xs">
                <div className="flex items-center gap-2">
                  <span className="px-1.5 py-0.5 bg-[var(--accent-violet, #8b5cf6)]/20 text-[var(--accent-violet, #8b5cf6)] border border-[var(--accent-violet, #8b5cf6)]/30 font-bold font-mono">
                    GIT: {event.commit_sha.slice(0, 7)}
                  </span>
                  <span className="text-[var(--text-muted)]">|</span>
                  <span className="text-[var(--text-main)] font-semibold uppercase">
                    {event.action}
                  </span>
                </div>
                <div className="flex items-center gap-3 text-[11px] text-[var(--text-muted)]">
                  <span>NODE: <strong className="text-white">{event.node_id}</strong></span>
                  <span>CHK: <code className="text-[var(--accent-cyan)]">{event.checkpoint_id}</code></span>
                  <span>{event.timestamp}</span>
                </div>
              </div>
              <p className="text-xs text-[var(--text-main)] font-mono leading-relaxed">
                {event.message}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
