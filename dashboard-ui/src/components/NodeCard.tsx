import type { NodeSnapshot } from '../types/telemetry';
import { formatNumber, relativeTime, STATUS_STYLES } from '../lib/telemetry';

interface NodeCardProps {
  node: NodeSnapshot;
  now: number;
}

/** A horizontal utilization bar; colour shifts as it approaches saturation. */
function Meter({ label, pct }: { label: string; pct: number }) {
  const clamped = Math.max(0, Math.min(100, pct));
  const color =
    clamped >= 85 ? 'bg-red-500' : clamped >= 65 ? 'bg-amber-500' : 'bg-brand';
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-xs">
        <span className="text-muted">{label}</span>
        <span className="tnum font-medium text-content">{formatNumber(clamped, 0)}%</span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-2">
        <div className={`h-full rounded-full ${color} transition-all duration-500`} style={{ width: `${clamped}%` }} />
      </div>
    </div>
  );
}

function Stat({ label, value, unit }: { label: string; value: string; unit?: string }) {
  return (
    <div className="rounded-lg bg-surface-2/60 px-3 py-2">
      <p className="text-[11px] uppercase tracking-wide text-subtle">{label}</p>
      <p className="tnum mt-0.5 text-sm font-semibold text-content">
        {value}
        {unit && <span className="ml-1 text-xs font-normal text-muted">{unit}</span>}
      </p>
    </div>
  );
}

export function NodeCard({ node, now }: NodeCardProps) {
  const status = STATUS_STYLES[node.status] ?? STATUS_STYLES.unknown;

  return (
    <div className={`animate-fade-in rounded-xl border bg-surface p-4 shadow-card ${status.ring}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={`h-2.5 w-2.5 rounded-full ${status.dot}`} />
          <h3 className="font-mono text-sm font-semibold text-content">{node.node_id}</h3>
        </div>
        <span className={`rounded-full border px-2 py-0.5 text-[11px] font-semibold ${status.pill}`}>
          {status.label}
        </span>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2">
        <Stat label="TTFT p99" value={formatNumber(node.ttft_p99_ms, 0)} unit="ms" />
        <Stat label="Throughput" value={formatNumber(node.tokens_per_sec, 1)} unit="tok/s" />
        <Stat label="Req rate" value={formatNumber(node.requests_per_min, 0)} unit="/min" />
        <Stat label="KV evict" value={formatNumber(node.kv_eviction_rate, 1)} unit="/s" />
      </div>

      <div className="mt-3 space-y-2.5">
        <Meter label="SVE2 utilization" pct={node.sve2_utilization_pct} />
        <Meter label="DRAM bandwidth" pct={node.dram_bandwidth_pct} />
        <Meter label="Cache miss rate" pct={node.cache_miss_rate_pct} />
      </div>

      {node.hotspots.length > 0 && (
        <div className="mt-3 border-t border-line pt-3">
          <p className="text-[11px] uppercase tracking-wide text-subtle">Top hotspot</p>
          <div className="mt-1 flex items-center justify-between font-mono text-xs">
            <span className="truncate text-amber-600 dark:text-amber-400" title={node.hotspots[0].symbol}>
              {node.hotspots[0].symbol}
            </span>
            <span className="tnum ml-2 shrink-0 text-muted">
              {formatNumber(node.hotspots[0].samples_pct, 1)}%
            </span>
          </div>
        </div>
      )}

      <p className="mt-3 text-right text-[11px] text-subtle">{relativeTime(node.timestamp, now)}</p>
    </div>
  );
}
