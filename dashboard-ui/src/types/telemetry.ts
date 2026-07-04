export type WebSocketEventType =
  | 'metrics'
  | 'agent_thought'
  | 'healing'
  | 'audit'
  | 'flame_graph';

export interface HotspotEntry {
  symbol: string;
  samples_pct: number;
  module: string;
}

export interface BaselineMetrics {
  ttft_p99_ms: number;
  tokens_per_sec: number;
  sve2_utilization_pct: number;
  dram_bandwidth_pct: number;
  cache_miss_rate_pct: number;
  kv_eviction_rate: number;
  requests_per_min: number;
}

export interface NodeSnapshot extends BaselineMetrics {
  node_id: string;
  status: 'healthy' | 'degraded' | 'unhealthy' | 'unknown';
  timestamp: string;
  hotspots: HotspotEntry[];
}

export interface MetricsEvent {
  type: 'metrics';
  timestamp: string;
  cluster_id: string;
  nodes: NodeSnapshot[];
}

export interface AgentThoughtEvent {
  type: 'agent_thought';
  timestamp: string;
  decision_id: string;
  node_id: string;
  chunk: string;
  done?: boolean;
}

export interface HealingEvent {
  type: 'healing';
  timestamp: string;
  healing_id: string;
  node_id: string;
  action: string;
  status: 'success' | 'failed' | 'rolled_back';
  before: BaselineMetrics;
  after: BaselineMetrics;
  duration_ms: number;
}

export interface AuditEvent {
  type: 'audit';
  timestamp: string;
  commit_sha: string;
  message: string;
  node_id: string;
  action: string;
  checkpoint_id: string;
}

export interface FlameGraphEvent {
  type: 'flame_graph';
  timestamp: string;
  node_id: string;
  hotspots: HotspotEntry[];
}

export type WebSocketEvent =
  | MetricsEvent
  | AgentThoughtEvent
  | HealingEvent
  | AuditEvent
  | FlameGraphEvent
  | { type?: string; node_id?: string; cluster_id?: string; message?: string; chunk?: string; action?: string; status?: string; timestamp?: string };
