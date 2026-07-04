import type { ReactNode } from 'react';

interface StatCardProps {
  label: string;
  value: ReactNode;
  unit?: string;
  hint?: string;
  accent?: string;
}

/** Compact KPI tile used in the cluster summary row. */
export function StatCard({ label, value, unit, hint, accent = 'bg-brand' }: StatCardProps) {
  return (
    <div className="relative overflow-hidden rounded-xl border border-line bg-surface p-4 shadow-card">
      <span className={`absolute inset-y-0 left-0 w-1 ${accent}`} aria-hidden="true" />
      <p className="text-xs font-medium uppercase tracking-wide text-subtle">{label}</p>
      <p className="mt-2 flex items-baseline gap-1">
        <span className="tnum text-2xl font-semibold text-content">{value}</span>
        {unit && <span className="text-sm font-medium text-muted">{unit}</span>}
      </p>
      {hint && <p className="mt-1 text-xs text-muted">{hint}</p>}
    </div>
  );
}
