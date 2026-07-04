import React, { useMemo } from 'react';
import type { AgentThoughtEvent } from '../types/telemetry';

interface AgentThoughtProps {
  thoughts: AgentThoughtEvent[];
}

interface GroupedThought {
  decision_id: string;
  node_id: string;
  timestamp: string;
  text: string;
  done: boolean;
}

export const AgentThought: React.FC<AgentThoughtProps> = ({ thoughts }) => {
  const groupedThoughts = useMemo(() => {
    const map = new Map<string, GroupedThought>();
    for (const t of thoughts) {
      if (!t.decision_id) continue;
      const existing = map.get(t.decision_id);
      if (existing) {
        existing.text += t.chunk || '';
        if (t.done !== undefined) existing.done = t.done;
        existing.timestamp = t.timestamp || existing.timestamp;
      } else {
        map.set(t.decision_id, {
          decision_id: t.decision_id,
          node_id: t.node_id || 'UNKNOWN',
          timestamp: t.timestamp || '00:00:00',
          text: t.chunk || '',
          done: t.done ?? false,
        });
      }
    }
    return Array.from(map.values()).reverse();
  }, [thoughts]);

  return (
    <div className="border border-[var(--border-color)] bg-[var(--card-bg)] p-4 font-mono">
      <div className="flex items-center justify-between border-b border-[var(--border-color)] pb-3 mb-3">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-[var(--accent-amber)] animate-pulse" />
          <h2 className="text-sm font-bold tracking-wider uppercase text-[var(--accent-cyan)]">
            [ AGENT REASONING STREAM // LLAMA-3.2-70B ]
          </h2>
        </div>
        <span className="text-xs text-[var(--text-muted)]">
          S3.2 AUTONOMOUS BRAIN
        </span>
      </div>

      {groupedThoughts.length === 0 ? (
        <div className="py-8 text-center border border-dashed border-[var(--border-color)] bg-black/20">
          <p className="text-xs text-[var(--text-muted)] tracking-widest uppercase">
            [ AGENT IDLE // WAITING FOR ANOMALY TELEMETRY TRIGGERS ]
          </p>
        </div>
      ) : (
        <div className="space-y-4 max-h-96 overflow-y-auto pr-1">
          {groupedThoughts.map((group) => (
            <div
              key={group.decision_id}
              className="border-l-2 border-[var(--accent-cyan)] bg-black/30 p-3 relative"
            >
              <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-[var(--text-muted)] mb-2 border-b border-white/5 pb-1">
                <div className="flex items-center gap-3">
                  <span className="text-[var(--text-main)] font-bold">
                    DECISION: <span className="text-[var(--accent-amber)]">{group.decision_id}</span>
                  </span>
                  <span>
                    TARGET: <span className="text-[var(--accent-cyan)] font-semibold">{group.node_id}</span>
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span>{group.timestamp}</span>
                  {group.done ? (
                    <span className="px-1.5 py-0.5 text-[10px] bg-green-500/20 text-green-400 border border-green-500/30 uppercase font-bold">
                      DONE
                    </span>
                  ) : (
                    <span className="px-1.5 py-0.5 text-[10px] bg-[var(--accent-amber)]/20 text-[var(--accent-amber)] border border-[var(--accent-amber)]/30 uppercase font-bold animate-pulse">
                      STREAMING...
                    </span>
                  )}
                </div>
              </div>
              <p className="text-xs text-[var(--text-main)] leading-relaxed whitespace-pre-wrap font-mono">
                {group.text}
                {!group.done && (
                  <span className="inline-block w-1.5 h-3 ml-0.5 bg-[var(--accent-amber)] animate-pulse align-middle" />
                )}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
