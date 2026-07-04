import { useEffect, useMemo, useState } from 'react';
import { useWebSocket } from './hooks/useWebSocket';
import { useTheme } from './hooks/useTheme';
import { StatusIndicator } from './components/Brand';
import { ThemeToggle } from './components/ThemeToggle';
import { StatCard } from './components/StatCard';
import { NodesTable } from './components/NodesTable';
import { EventsTable } from './components/EventsTable';
import { AgentThought } from './components/AgentThought';
import { FlameGraph } from './components/FlameGraph';
import { HealingFeed } from './components/HealingFeed';
import { AuditLog } from './components/AuditLog';
import { average, formatClock, formatNumber, latestMetrics } from './lib/telemetry';
import type { AgentThoughtEvent, AuditEvent, FlameGraphEvent, HealingEvent } from './types/telemetry';

function PanelHeader({ id, title, meta }: { id: string; title: string; meta: string }) {
  return (
    <div className="flex items-center justify-between border-b border-line bg-surface-2/50 px-3 py-1.5">
      <h3 id={id} className="text-[11px] font-bold uppercase tracking-[0.15em] text-brand">
        {title}
      </h3>
      <span className="text-[10px] uppercase tracking-wider text-muted">{meta}</span>
    </div>
  );
}

function App() {
  const { theme, toggleTheme } = useTheme();
  const { connected, error, messages } = useWebSocket('ws://localhost:8080/ws');

  // Live clock + fresh relative timestamps, ticking once a second.
  const [now, setNow] = useState<number>(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  const metrics = useMemo(() => latestMetrics(messages), [messages]);

  const summary = useMemo(() => {
    const nodes = metrics?.nodes ?? [];
    const healthy = nodes.filter((n) => n.status === 'healthy').length;
    return {
      total: nodes.length,
      healthy,
      degraded: nodes.filter((n) => n.status !== 'healthy').length,
      avgTtft: average(nodes.map((n) => n.ttft_p99_ms)),
      avgTokens: average(nodes.map((n) => n.tokens_per_sec)),
      avgSve2: average(nodes.map((n) => n.sve2_utilization_pct)),
    };
  }, [metrics]);

  const agentThoughts = useMemo(
    () => messages.filter((m): m is AgentThoughtEvent => m.type === 'agent_thought'),
    [messages]
  );
  const flameGraphs = useMemo(
    () => messages.filter((m): m is FlameGraphEvent => m.type === 'flame_graph'),
    [messages]
  );
  const healingEvents = useMemo(
    () => messages.filter((m): m is HealingEvent => m.type === 'healing'),
    [messages]
  );
  const auditEvents = useMemo(
    () => messages.filter((m): m is AuditEvent => m.type === 'audit'),
    [messages]
  );

  const nodes = metrics?.nodes ?? [];
  const hasNodes = nodes.length > 0;

  return (
    <div className="min-h-screen bg-bg font-mono text-content" role="main" aria-label="NeoSentinel Control Plane Dashboard">
      {/* STATUS LINE */}
      <header className="sticky top-0 z-20 flex h-9 items-center gap-2 border-b border-line bg-surface px-3">
        <h1 className="shrink-0 text-[12px] font-bold tracking-[0.25em] text-brand">NEOSENTINEL</h1>
        <span className="hidden flex-1 select-none overflow-hidden whitespace-nowrap text-line sm:block" aria-hidden="true">
          ////////////////////////////////////////////////////////////////////////////
        </span>
        <span className="hidden shrink-0 text-[10px] uppercase tracking-wider text-muted md:inline">
          Graviton4 Control Plane
        </span>
        <div className="ml-auto flex shrink-0 items-center gap-3">
          <span className="tnum text-[11px] font-bold text-accent">{formatClock(now)}</span>
          <span className="text-subtle">·</span>
          <StatusIndicator connected={connected} />
          <ThemeToggle theme={theme} onToggle={toggleTheme} />
        </div>
      </header>

      {error && (
        <div className="border-b border-red-500/40 bg-red-500/10 px-3 py-1 text-[11px] uppercase tracking-wider text-red-400">
          ! {error} — retrying
        </div>
      )}

      {/* CLUSTER OVERVIEW */}
      <div className="flex items-center justify-between border-b border-line bg-surface-2/50 px-3 py-1.5">
        <h2 id="overview" className="text-[11px] font-bold uppercase tracking-[0.15em] text-brand">
          Cluster Overview
        </h2>
        <span className="text-[10px] uppercase tracking-wider text-muted">
          Autonomous healing active · <span className="tnum text-content">{messages.length}</span> events
        </span>
      </div>

      <div className="flex flex-wrap divide-x divide-line border-b border-line">
        <StatCard label="Nodes" value={summary.total} hint={`${summary.healthy} ok · ${summary.degraded} attn`} accent="bg-brand" />
        <StatCard label="Healthy" value={hasNodes ? summary.healthy : '—'} unit={hasNodes ? `/ ${summary.total}` : undefined} accent="bg-emerald-500" />
        <StatCard label="Avg TTFT p99" value={hasNodes ? formatNumber(summary.avgTtft, 0) : '—'} unit="ms" accent="bg-accent" />
        <StatCard label="Avg Throughput" value={hasNodes ? formatNumber(summary.avgTokens, 1) : '—'} unit="tok/s" accent="bg-violet-500" />
        <StatCard label="Avg SVE2" value={hasNodes ? formatNumber(summary.avgSve2, 0) : '—'} unit="%" accent="bg-cyan-500" />
      </div>

      {/* NODES */}
      <section aria-labelledby="nodes">
        <PanelHeader id="nodes" title="Nodes" meta={`${summary.total} monitored`} />
        <NodesTable nodes={nodes} />
      </section>

      {/* S3.2 FLAME GRAPH & S3.1 AGENT THOUGHTS */}
      <div className="grid grid-cols-1 lg:grid-cols-2 divide-y lg:divide-y-0 lg:divide-x divide-line border-b border-line">
        <section aria-labelledby="flame">
          <PanelHeader id="flame" title="Performance Hotspots" meta="SVE2 PMU" />
          <FlameGraph
            node_id={flameGraphs.length > 0 ? flameGraphs[flameGraphs.length - 1].node_id : undefined}
            hotspots={flameGraphs.length > 0 ? flameGraphs[flameGraphs.length - 1].hotspots : []}
          />
        </section>
        <section aria-labelledby="brain">
          <PanelHeader id="brain" title="Autonomous Agent Reasoning" meta="Llama-3.2-70B" />
          <AgentThought thoughts={agentThoughts} />
        </section>
      </div>

      {/* S3.3 HEALING FEED & S3.4 AUDIT LOG */}
      <div className="grid grid-cols-1 lg:grid-cols-2 divide-y lg:divide-y-0 lg:divide-x divide-line border-b border-line">
        <section aria-labelledby="healing">
          <PanelHeader id="healing" title="Autonomous Recovery Feed" meta="closed-loop" />
          <HealingFeed events={healingEvents} />
        </section>
        <section aria-labelledby="audit">
          <PanelHeader id="audit" title="GitOps Audit Log" meta="immutable trail" />
          <AuditLog events={auditEvents} />
        </section>
      </div>

      {/* DECISION STREAM */}
      <section aria-labelledby="stream">
        <PanelHeader id="stream" title="Decision Stream" meta="real-time" />
        <EventsTable events={messages} now={now} />
      </section>

      <footer className="px-3 py-3 text-[10px] uppercase tracking-wider text-subtle">
        NeoSentinel · Graviton4 autonomous inference control plane
      </footer>
    </div>
  );
}

export default App;
