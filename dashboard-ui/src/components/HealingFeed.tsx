import React from 'react';
import type { HealingEvent } from '../types/telemetry';

interface HealingFeedProps {
  events: HealingEvent[];
}

export const HealingFeed: React.FC<HealingFeedProps> = ({ events }) => {
  return (
    <div className="border border-[var(--border-color)] bg-[var(--card-bg)] p-4 font-mono">
      <div className="flex items-center justify-between border-b border-[var(--border-color)] pb-3 mb-4">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
          <h2 className="text-sm font-bold tracking-wider uppercase text-[var(--text-main)]">
            [ AUTONOMOUS HEALING FEED // <span className="text-green-400">S3.3 CLOSED-LOOP</span> ]
          </h2>
        </div>
        <span className="text-xs text-[var(--text-muted)]">
          RECOVERY ACTIONS
        </span>
      </div>

      {events.length === 0 ? (
        <div className="py-8 text-center border border-dashed border-[var(--border-color)] bg-black/20">
          <p className="text-xs text-[var(--text-muted)] tracking-widest uppercase">
            [ NO AUTONOMOUS HEALING ACTIONS RECORDED // CLUSTER STABLE ]
          </p>
        </div>
      ) : (
        <div className="space-y-3 max-h-96 overflow-y-auto pr-1">
          {events.slice().reverse().map((event) => {
            const isSuccess = event.status === 'success';
            const isRollback = event.status === 'rolled_back';
            const statusColor = isSuccess
              ? 'bg-green-500/20 text-green-400 border-green-500/30'
              : isRollback
              ? 'bg-[var(--accent-amber)]/20 text-[var(--accent-amber)] border-[var(--accent-amber)]/30'
              : 'bg-red-500/20 text-red-400 border-red-500/30';

            return (
              <div
                key={event.healing_id}
                className="border border-[var(--border-color)] bg-black/40 p-3 hover:border-white/20 transition-colors"
              >
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/5 pb-2 mb-2 text-xs">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-[var(--text-main)]">
                      ACTION: <span className="text-[var(--accent-cyan)] uppercase">{event.action}</span>
                    </span>
                    <span className="text-[var(--text-muted)]">|</span>
                    <span className="text-[var(--text-muted)]">
                      NODE: <span className="text-white font-semibold">{event.node_id}</span>
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[var(--text-muted)] text-[11px]">
                      {event.duration_ms}ms ({event.timestamp})
                    </span>
                    <span className={`px-1.5 py-0.5 text-[10px] border uppercase font-bold ${statusColor}`}>
                      {event.status}
                    </span>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2 mt-2 bg-black/20 p-2 border border-white/5 text-[11px]">
                  <div>
                    <span className="text-[var(--text-muted)] uppercase block text-[10px] mb-1">
                      [ BEFORE METRICS ]
                    </span>
                    <div className="text-[var(--accent-amber)] font-semibold">
                      SVE2: {event.before.sve2_utilization_pct.toFixed(1)}% | T/s: {event.before.tokens_per_sec.toFixed(1)}
                    </div>
                  </div>
                  <div className="border-l border-white/5 pl-2">
                    <span className="text-[var(--text-muted)] uppercase block text-[10px] mb-1">
                      [ AFTER METRICS ]
                    </span>
                    <div className="text-green-400 font-semibold">
                      SVE2: {event.after.sve2_utilization_pct.toFixed(1)}% | T/s: {event.after.tokens_per_sec.toFixed(1)}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
