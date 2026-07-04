import type { NodeSnapshot } from '../types/telemetry';
import {
  formatNumber,
  isoClock,
  meterColor,
  NODE_STATUS,
  utilBlocks,
} from '../lib/telemetry';

interface NodesTableProps {
  nodes: NodeSnapshot[];
}

const TH = 'px-3 py-1.5 text-left font-medium border-r border-line/50 last:border-r-0';
const TD = 'px-3 py-1 whitespace-nowrap border-r border-line/30 last:border-r-0';

function Gauge({ pct, higherBetter }: { pct: number; higherBetter?: boolean }) {
  return (
    <span className="inline-flex items-center gap-2">
      <span className={`${meterColor(pct, higherBetter)} tracking-tighter`}>{utilBlocks(pct)}</span>
      <span className="tnum w-9 text-right text-muted">{formatNumber(pct, 0)}%</span>
    </span>
  );
}

export function NodesTable({ nodes }: NodesTableProps) {
  return (
    <div className="scroll-slim overflow-x-auto border-b border-line">
      <table className="w-full min-w-[900px] text-[12px]">
        <thead>
          <tr className="border-b border-line bg-surface-2/60 text-[10px] uppercase tracking-wider text-accent">
            <th className={TH}>Node</th>
            <th className={TH}>Status</th>
            <th className={`${TH} text-right`}>TTFT</th>
            <th className={`${TH} text-right`}>Tok/s</th>
            <th className={`${TH} text-right`}>Req/m</th>
            <th className={`${TH} text-right`}>KVevict</th>
            <th className={TH}>SVE2</th>
            <th className={TH}>DRAM BW</th>
            <th className={TH}>Cache Miss</th>
            <th className={TH}>Top Hotspot</th>
          </tr>
        </thead>
        <tbody>
          {nodes.map((node) => {
            const st = NODE_STATUS[node.status] ?? NODE_STATUS.unknown;
            const hotspot = node.hotspots[0];
            return (
              <tr key={node.node_id} className="border-b border-line/40 transition-colors last:border-b-0 hover:bg-surface-2/50">
                <td className={TD}>
                  <span className="font-bold text-brand">{node.node_id}</span>
                  <span className="tnum ml-2 text-[10px] text-subtle">{isoClock(node.timestamp)}</span>
                </td>
                <td className={`${TD} font-bold ${st.cls}`}>{st.code}</td>
                <td className={`${TD} tnum text-right text-content`}>
                  {formatNumber(node.ttft_p99_ms, 0)}<span className="text-subtle">ms</span>
                </td>
                <td className={`${TD} tnum text-right text-content`}>{formatNumber(node.tokens_per_sec, 1)}</td>
                <td className={`${TD} tnum text-right text-content`}>{formatNumber(node.requests_per_min, 0)}</td>
                <td className={`${TD} tnum text-right text-content`}>{formatNumber(node.kv_eviction_rate, 1)}</td>
                <td className={TD}><Gauge pct={node.sve2_utilization_pct} higherBetter /></td>
                <td className={TD}><Gauge pct={node.dram_bandwidth_pct} /></td>
                <td className={TD}><Gauge pct={node.cache_miss_rate_pct} /></td>
                <td className={TD}>
                  {hotspot ? (
                    <span className="inline-flex items-center gap-2">
                      <span className="max-w-[220px] truncate text-amber-400" title={hotspot.symbol}>{hotspot.symbol}</span>
                      <span className="tnum text-subtle">{formatNumber(hotspot.samples_pct, 1)}%</span>
                    </span>
                  ) : (
                    <span className="text-subtle">—</span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {nodes.length === 0 && (
        <div className="px-3 py-8 text-center text-[12px] uppercase tracking-wider text-subtle">
          No node snapshots — awaiting first metrics event
        </div>
      )}
    </div>
  );
}
