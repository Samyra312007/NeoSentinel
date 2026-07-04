import { useWebSocket } from './hooks/useWebSocket';
import type { WebSocketEvent } from './types/telemetry';

function getBadgeStyle(type?: string) {
  switch (type) {
    case 'metrics':
      return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
    case 'agent_thought':
      return 'bg-purple-500/10 text-purple-400 border-purple-500/20';
    case 'flame_graph':
      return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
    case 'healing':
      return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
    case 'audit':
      return 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20';
    default:
      return 'bg-slate-500/10 text-slate-400 border-slate-500/20';
  }
}

function App() {
  const { connected, error, messages } = useWebSocket('ws://localhost:8080/ws');

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <header className="border-b border-slate-800 bg-slate-900/50 backdrop-blur px-6 py-4 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-3 h-3 rounded-full bg-emerald-500 animate-pulse"></div>
          <h1 className="text-xl font-bold tracking-tight bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent">
            NeoSentinel v2.0
          </h1>
          <span className="text-xs bg-slate-800 text-slate-400 px-2 py-0.5 rounded border border-slate-700 font-mono">
            Graviton4 Control Plane
          </span>
        </div>
        <div className="flex items-center space-x-4 text-sm font-mono">
          <div className="flex items-center space-x-2">
            <span className="text-slate-400">WebSocket:</span>
            <span className={`px-2 py-0.5 rounded text-xs ${connected ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-red-500/10 text-red-400 border border-red-500/20'}`}>
              {connected ? 'CONNECTED' : 'DISCONNECTED'}
            </span>
          </div>
          {error && <span className="text-xs text-red-400">{error}</span>}
        </div>
      </header>

      <main className="flex-1 p-6 grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="col-span-3 bg-slate-900/40 border border-slate-800 rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-2">Cluster Overview</h2>
          <p className="text-slate-400 text-sm">
            Autonomous cluster healing active. <span className="text-emerald-400 font-mono font-bold">{messages.length}</span> telemetry events received.
          </p>
        </div>

        {messages.length > 0 && (
          <div className="col-span-3 bg-slate-900/40 border border-slate-800 rounded-lg p-6">
            <h3 className="text-md font-semibold mb-4 flex items-center justify-between">
              <span>Live Telemetry &amp; Decision Stream</span>
              <span className="text-xs text-slate-400 font-mono">Real-time Feed</span>
            </h3>
            <div className="space-y-3 max-h-[500px] overflow-y-auto pr-2 font-mono text-sm">
              {[...messages].reverse().map((msg: WebSocketEvent, idx: number) => {
                const type = 'type' in msg ? msg.type : 'unknown';
                const source = ('node_id' in msg && msg.node_id) ? msg.node_id : (('cluster_id' in msg && msg.cluster_id) ? msg.cluster_id : 'system');
                const content = ('chunk' in msg && msg.chunk) ? msg.chunk : (('message' in msg && msg.message) ? msg.message : (('action' in msg && msg.action) ? `Action: ${msg.action} (${('status' in msg && msg.status) || ''})` : JSON.stringify(msg).slice(0, 80)));
                const ts = ('timestamp' in msg && msg.timestamp) ? msg.timestamp : 'just now';

                return (
                  <div key={idx} className="p-3 rounded bg-slate-950/60 border border-slate-800/80 flex flex-col md:flex-row md:items-center justify-between gap-2">
                    <div className="flex items-center space-x-3">
                      <span className={`px-2 py-0.5 rounded border text-xs uppercase font-bold ${getBadgeStyle(type)}`}>
                        {type}
                      </span>
                      <span className="text-slate-300">
                        {source}
                      </span>
                    </div>
                    <div className="text-slate-400 text-xs truncate max-w-xl">
                      {content}
                    </div>
                    <div className="text-slate-500 text-xs">
                      {ts}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
