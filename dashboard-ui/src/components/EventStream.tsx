import type { WebSocketEvent } from '../types/telemetry';
import {
  EVENT_STYLES,
  eventSource,
  eventSummary,
  eventType,
  relativeTime,
} from '../lib/telemetry';

interface EventStreamProps {
  events: WebSocketEvent[];
  now: number;
}

function EventRow({ event, now }: { event: WebSocketEvent; now: number }) {
  const type = eventType(event);
  const style = EVENT_STYLES[type] ?? EVENT_STYLES.unknown;
  const ts = 'timestamp' in event ? event.timestamp : undefined;

  return (
    <li className="animate-fade-in flex gap-3">
      <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${style.accent}`} aria-hidden="true" />
      <div className="min-w-0 flex-1 rounded-lg border border-line bg-surface-2/50 px-3 py-2">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className={`rounded border px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${style.badge}`}>
              {style.label}
            </span>
            <span className="font-mono text-xs text-muted">{eventSource(event)}</span>
          </div>
          <span className="tnum shrink-0 text-[11px] text-subtle">{relativeTime(ts, now)}</span>
        </div>
        <p className="mt-1 break-words text-sm text-content">{eventSummary(event)}</p>
      </div>
    </li>
  );
}

export function EventStream({ events, now }: EventStreamProps) {
  if (events.length === 0) {
    return (
      <div className="flex h-full min-h-[200px] flex-col items-center justify-center gap-2 text-center text-muted">
        <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-brand" />
        <p className="text-sm">Waiting for telemetry…</p>
        <p className="text-xs text-subtle">Decisions will appear here as the agent reasons.</p>
      </div>
    );
  }

  const ordered = [...events].reverse();

  return (
    <ul className="scroll-slim max-h-[560px] space-y-2 overflow-y-auto pr-1">
      {ordered.map((event, idx) => (
        <EventRow key={events.length - idx} event={event} now={now} />
      ))}
    </ul>
  );
}
