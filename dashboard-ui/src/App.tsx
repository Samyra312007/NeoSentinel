import { useEffect, useMemo, useState } from 'react';
import { useWebSocket } from './hooks/useWebSocket';
import { useTheme } from './hooks/useTheme';
import { ThemeToggle } from './components/ThemeToggle';
import { StatCard } from './components/StatCard';
import { NodeCard } from './components/NodeCard';
import { EventStream } from './components/EventStream';
import {
  average,
  formatNumber,
  latestMetrics,
} from './lib/telemetry';

function App() {
  const { theme, toggleTheme } = useTheme();
  const { connected, error, messages } = useWebSocket('ws://localhost:8080/ws');

  // A slow tick so relative timestamps stay fresh without re-rendering per event.
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

  const nodes = metrics?.nodes ?? [];

  return (
    <div className="min-h-screen bg-bg font-sans text-content">
      <header className="sticky top-0 z-10 border-b border-line bg-surface/80 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <div className="flex items-center gap-3">
            <span className="relative flex h-3 w-3">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex h-3 w-3 rounded-full bg-emerald-500" />
            </span>
            <h1 className="text-lg font-bold tracking-tight text-content">NeoSentinel v2.0</h1>
            <span className="hidden rounded-md border border-line bg-surface-2/60 px-2 py-0.5 font-mono text-xs text-muted sm:inline">
              Graviton4 Control Plane
            </span>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 text-sm">
              <span className="hidden text-muted sm:inline">WebSocket</span>
              <span
                className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold ${
                  connected
                    ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300'
                    : 'border-red-500/30 bg-red-500/10 text-red-700 dark:text-red-300'
                }`}
              >
                <span className={`h-1.5 w-1.5 rounded-full ${connected ? 'bg-emerald-500' : 'bg-red-500'}`} />
                {connected ? 'CONNECTED' : 'DISCONNECTED'}
              </span>
            </div>
            <ThemeToggle theme={theme} onToggle={toggleTheme} />
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-6 px-4 py-6 sm:px-6">
        {error && (
          <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-2 text-sm text-red-700 dark:text-red-300">
            {error} — retrying connection to the control plane.
          </div>
        )}

        <section aria-labelledby="overview-heading">
          <div className="mb-3 flex items-baseline justify-between">
            <h2 id="overview-heading" className="text-base font-semibold text-content">
              Cluster Overview
            </h2>
            <p className="text-xs text-muted">
              Autonomous healing active ·{' '}
              <span className="tnum font-semibold text-brand">{messages.length}</span> events received
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
            <StatCard
              label="Nodes"
              value={summary.total}
              hint={`${summary.healthy} healthy · ${summary.degraded} attention`}
              accent="bg-brand"
            />
            <StatCard
              label="Healthy"
              value={summary.total > 0 ? summary.healthy : '—'}
              unit={summary.total > 0 ? `/ ${summary.total}` : undefined}
              accent="bg-emerald-500"
            />
            <StatCard
              label="Avg TTFT p99"
              value={summary.total > 0 ? formatNumber(summary.avgTtft, 0) : '—'}
              unit="ms"
              accent="bg-sky-500"
            />
            <StatCard
              label="Avg Throughput"
              value={summary.total > 0 ? formatNumber(summary.avgTokens, 1) : '—'}
              unit="tok/s"
              accent="bg-violet-500"
            />
            <StatCard
              label="Avg SVE2"
              value={summary.total > 0 ? formatNumber(summary.avgSve2, 0) : '—'}
              unit="%"
              accent="bg-cyan-500"
            />
          </div>
        </section>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <section aria-labelledby="nodes-heading" className="lg:col-span-2">
            <h2 id="nodes-heading" className="mb-3 text-base font-semibold text-content">
              Nodes
            </h2>
            {nodes.length > 0 ? (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                {nodes.map((node) => (
                  <NodeCard key={node.node_id} node={node} now={now} />
                ))}
              </div>
            ) : (
              <div className="flex min-h-[200px] items-center justify-center rounded-xl border border-dashed border-line bg-surface/50 text-sm text-muted">
                No node snapshots yet — awaiting first metrics event.
              </div>
            )}
          </section>

          <section aria-labelledby="stream-heading" className="lg:col-span-1">
            <div className="mb-3 flex items-center justify-between">
              <h2 id="stream-heading" className="text-base font-semibold text-content">
                Decision Stream
              </h2>
              <span className="font-mono text-xs text-subtle">real-time</span>
            </div>
            <div className="rounded-xl border border-line bg-surface p-3 shadow-card">
              <EventStream events={messages} now={now} />
            </div>
          </section>
        </div>
      </main>

      <footer className="mx-auto max-w-7xl px-4 py-6 text-center text-xs text-subtle sm:px-6">
        NeoSentinel · Graviton4 autonomous inference control plane
      </footer>
    </div>
  );
}

export default App;
