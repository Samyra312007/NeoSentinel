import type { WebSocketEvent } from '../types/telemetry';
import {
  EVENT_TAG,
  eventSource,
  eventSummary,
  eventType,
  isoClock,
} from '../lib/telemetry';

interface EventsTableProps {
  events: WebSocketEvent[];
  now: number;
}

const TH = 'px-3 py-1.5 text-left font-medium border-r border-line/50 last:border-r-0';
const TD = 'px-3 py-1 border-r border-line/30 last:border-r-0 align-top';

export function EventsTable({ events }: EventsTableProps) {
  const ordered = [...events].reverse();

  return (
    <div className="scroll-slim max-h-[440px] overflow-auto border-b border-line">
      <table className="w-full min-w-[680px] text-[12px]">
        <thead className="sticky top-0 z-10">
          <tr className="border-b border-line bg-surface-2 text-[10px] uppercase tracking-wider text-accent">
            <th className={`${TH} w-24`}>Time</th>
            <th className={`${TH} w-24`}>Type</th>
            <th className={`${TH} w-36`}>Source</th>
            <th className={TH}>Detail</th>
          </tr>
        </thead>
        <tbody>
          {ordered.map((event, idx) => {
            const tag = EVENT_TAG[eventType(event)] ?? EVENT_TAG.unknown;
            const ts = 'timestamp' in event ? event.timestamp : undefined;
            return (
              <tr key={events.length - idx} className="border-b border-line/40 transition-colors last:border-b-0 hover:bg-surface-2/50">
                <td className={`${TD} tnum whitespace-nowrap text-muted`}>{isoClock(ts)}</td>
                <td className={`${TD} whitespace-nowrap font-bold ${tag.cls}`}>{tag.code}</td>
                <td className={`${TD} whitespace-nowrap text-brand`}>{eventSource(event)}</td>
                <td className={`${TD} text-content`}>{eventSummary(event)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {events.length === 0 && (
        <div className="flex items-center gap-2 px-3 py-8 text-[12px] uppercase tracking-wider text-subtle">
          <span className="h-1.5 w-1.5 animate-pulse bg-brand" />
          Awaiting telemetry stream…
        </div>
      )}
    </div>
  );
}
