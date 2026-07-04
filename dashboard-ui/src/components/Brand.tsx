/** Terminal live indicator: a blinking square + LIVE/RECONNECTING. */
export function StatusIndicator({ connected }: { connected: boolean }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 text-[11px] font-bold tracking-wider ${
        connected ? 'text-emerald-400' : 'text-red-400'
      }`}
      title={connected ? 'Telemetry stream connected' : 'Reconnecting to control plane'}
    >
      <span className={`h-1.5 w-1.5 ${connected ? 'animate-pulse bg-emerald-400' : 'bg-red-500'}`} />
      {connected ? 'LIVE' : 'RECONNECTING'}
    </span>
  );
}
