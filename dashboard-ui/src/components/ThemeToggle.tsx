import type { Theme } from '../hooks/useTheme';

interface ThemeToggleProps {
  theme: Theme;
  onToggle: () => void;
}

/** Bracketed terminal button to flip the light/dark palette. */
export function ThemeToggle({ theme, onToggle }: ThemeToggleProps) {
  const isDark = theme === 'dark';
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-label={`Switch to ${isDark ? 'light' : 'dark'} theme`}
      title={`Switch to ${isDark ? 'light' : 'dark'} theme`}
      className="border border-line px-2 py-0.5 text-[11px] uppercase tracking-wider text-muted transition-colors hover:border-brand hover:text-content focus:outline-none focus-visible:border-brand"
    >
      {isDark ? '☾ DARK' : '☀ LIGHT'}
    </button>
  );
}
