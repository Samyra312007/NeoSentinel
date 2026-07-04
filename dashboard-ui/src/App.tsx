import { useWebSocket } from './hooks/useWebSocket';

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
            Autonomous cluster healing active. {messages.length} telemetry events received.
          </p>
        </div>
      </main>
    </div>
  );
}

export default App;
