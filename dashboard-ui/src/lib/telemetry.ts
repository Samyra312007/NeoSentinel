import type {
  MetricsEvent,
  NodeSnapshot,
  WebSocketEvent,
} from '../types/telemetry';

export type NodeStatus = NodeSnapshot['status'];

/** Border + text + dot classes for a node health status, tuned for both themes. */
export const STATUS_STYLES: Record<
  NodeStatus,
  { label: string; dot: string; pill: string; ring: string }
> = {
  healthy: {
    label: 'Healthy',
    dot: 'bg-emerald-500',
    pill: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/30',
    ring: 'border-emerald-500/40',
  },
  degraded: {
    label: 'Degraded',
    dot: 'bg-amber-500',
    pill: 'bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-500/30',
    ring: 'border-amber-500/50',
  },
  unhealthy: {
    label: 'Unhealthy',
    dot: 'bg-red-500',
    pill: 'bg-red-500/10 text-red-700 dark:text-red-300 border-red-500/30',
    ring: 'border-red-500/50',
  },
  unknown: {
    label: 'Unknown',
    dot: 'bg-slate-400',
    pill: 'bg-slate-500/10 text-slate-600 dark:text-slate-300 border-slate-500/30',
    ring: 'border-line',
  },
};

/** Badge classes per event type used in the decision stream. */
export const EVENT_STYLES: Record<
  string,
  { label: string; badge: string; accent: string }
> = {
  metrics: {
    label: 'Metrics',
    badge: 'bg-sky-500/10 text-sky-700 dark:text-sky-300 border-sky-500/30',
    accent: 'bg-sky-500',
  },
  agent_thought: {
    label: 'Agent',
    badge: 'bg-violet-500/10 text-violet-700 dark:text-violet-300 border-violet-500/30',
    accent: 'bg-violet-500',
  },
  flame_graph: {
    label: 'Flame Graph',
    badge: 'bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-500/30',
    accent: 'bg-amber-500',
  },
  healing: {
    label: 'Healing',
    badge: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/30',
    accent: 'bg-emerald-500',
  },
  audit: {
    label: 'Audit',
    badge: 'bg-cyan-500/10 text-cyan-700 dark:text-cyan-300 border-cyan-500/30',
    accent: 'bg-cyan-500',
  },
  unknown: {
    label: 'Event',
    badge: 'bg-slate-500/10 text-slate-600 dark:text-slate-300 border-slate-500/30',
    accent: 'bg-slate-400',
  },
};

export function eventType(event: WebSocketEvent): string {
  return 'type' in event && event.type ? event.type : 'unknown';
}

/** The most recent metrics snapshot in the stream, if any. */
export function latestMetrics(events: WebSocketEvent[]): MetricsEvent | null {
  for (let i = events.length - 1; i >= 0; i -= 1) {
    const e = events[i];
    if ('type' in e && e.type === 'metrics') return e as MetricsEvent;
  }
  return null;
}

export function formatNumber(value: number, digits = 1): string {
  if (!Number.isFinite(value)) return '—';
  return value.toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export function average(values: number[]): number {
  if (values.length === 0) return NaN;
  return values.reduce((sum, v) => sum + v, 0) / values.length;
}

/** Human-readable relative time (e.g. "3s ago"), tolerant of odd input. */
export function relativeTime(timestamp?: string, now: number = Date.now()): string {
  if (!timestamp) return '—';
  const then = Date.parse(timestamp);
  if (Number.isNaN(then)) return timestamp;
  const diffSec = Math.max(0, Math.round((now - then) / 1000));
  if (diffSec < 5) return 'just now';
  if (diffSec < 60) return `${diffSec}s ago`;
  const min = Math.floor(diffSec / 60);
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h ago`;
  return `${Math.floor(hr / 24)}d ago`;
}

/** Short summary text for one event, used in the stream row. */
export function eventSummary(event: WebSocketEvent): string {
  const type = eventType(event);
  switch (type) {
    case 'agent_thought':
      return 'chunk' in event && event.chunk ? event.chunk : 'Reasoning…';
    case 'healing':
      return 'action' in event && event.action
        ? `${event.action} → ${('status' in event && event.status) || 'pending'}`
        : 'Healing action';
    case 'audit':
      return 'message' in event && event.message ? event.message : 'Checkpoint committed';
    case 'metrics':
      return 'nodes' in event && Array.isArray(event.nodes)
        ? `Snapshot · ${event.nodes.length} node${event.nodes.length === 1 ? '' : 's'}`
        : 'Cluster snapshot';
    case 'flame_graph':
      return 'hotspots' in event && Array.isArray(event.hotspots)
        ? `${event.hotspots.length} hotspot${event.hotspots.length === 1 ? '' : 's'} sampled`
        : 'Flame graph captured';
    default:
      return JSON.stringify(event).slice(0, 100);
  }
}

export function eventSource(event: WebSocketEvent): string {
  if ('node_id' in event && event.node_id) return event.node_id;
  if ('cluster_id' in event && event.cluster_id) return event.cluster_id;
  return 'system';
}
