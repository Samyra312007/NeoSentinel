import type { ReactNode } from 'react';

interface StatCardProps {
  label: string;
  value: ReactNode;
  unit?: string;
  hint?: string;
  accent?: string;
}

/** A single KPI field in the terminal header strip: accent tick, label, value. */
export function StatCard({ label, value, unit, hint, accent = 'bg-brand' }: StatCardProps) {
  return (
    <div className="flex min-w-[150px] flex-1 items-stretch">
      <span className={`w-[3px] shrink-0 ${accent}`} aria-hidden="true" />
      <div className="px-3 py-2">
        <p className="text-[10px] uppercase tracking-wider text-accent">{label}</p>
        <p className="mt-1 flex items-baseline gap-1">
          <span className="tnum text-xl font-bold leading-none text-content">{value}</span>
          {unit && <span className="text-[11px] text-muted">{unit}</span>}
        </p>
        {hint && <p className="mt-1 text-[10px] uppercase tracking-wide text-subtle">{hint}</p>}
      </div>
    </div>
  );
}
